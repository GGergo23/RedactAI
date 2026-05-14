"""Automatic detection pipeline orchestration.

The controller coordinates OCR, NLP, optional object detection, and progress
reporting without depending on the UI layer. PyQt callers can connect the
``progress_callback`` argument to a signal emitter.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Protocol
from uuid import uuid4

from PIL import Image

from src.ai.detector import NLPDetector
from src.ai.ocr import ocr
from src.ai.types import (
    BoundingBox,
    DetectedObject,
    NLPEntity,
    OCRResult,
    TextDetection,
)
from src.redactEngine import RedactionTarget, RedactionType

MAX_IMAGES_PER_JOB = 50


class PipelineStage(str, Enum):
    """High-level pipeline stage reported to the UI."""

    QUEUED = "queued"
    STARTED = "started"
    OCR_COMPLETED = "ocr_completed"
    NLP_COMPLETED = "nlp_completed"
    OBJECT_DETECTION_COMPLETED = "object_detection_completed"
    REDACTION_TARGETS_READY = "redaction_targets_ready"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class PipelineStatus(str, Enum):
    """Progress status for a pipeline update."""

    RUNNING = "running"
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


class NLPDetectorProtocol(Protocol):
    """Minimal NLP detector contract used by the pipeline."""

    def detect(self, text: str) -> list[NLPEntity]:
        """Detect sensitive entities in OCR text."""


class ObjectDetectorProtocol(Protocol):
    """Minimal object detector contract used by the pipeline."""

    def detect(self, images: list[Image.Image]) -> list[list[DetectedObject]]:
        """Detect sensitive visual objects for each image."""


OCRCallable = Callable[[list[Image.Image]], list[OCRResult]]
ProgressCallback = Callable[["PipelineProgress"], None]
CompletedCountProvider = Callable[[], int]


@dataclass(frozen=True, slots=True)
class PipelineSettings:
    """Configuration for one automatic detection run."""

    redaction_type: RedactionType = RedactionType.BLACK_BAR
    enabled_text_labels: frozenset[str] = field(default_factory=frozenset)
    enabled_object_labels: frozenset[str] = field(default_factory=frozenset)
    max_images: int = MAX_IMAGES_PER_JOB
    worker_count: int = 4


@dataclass(frozen=True, slots=True)
class DetectionCandidate:
    """One automatically detected region that can be redacted."""

    bounding_box: BoundingBox
    source: str
    label: str
    confidence: float
    text: str | None = None

    def to_redaction_target(self, redaction_type: RedactionType) -> RedactionTarget:
        """Convert this candidate into a redaction engine instruction."""

        return RedactionTarget(
            location=self.bounding_box,
            redaction_type=redaction_type,
        )


@dataclass(frozen=True, slots=True)
class ImagePipelineResult:
    """Pipeline outcome for one input image."""

    image_index: int
    success: bool
    candidates: list[DetectionCandidate]
    redaction_targets: list[RedactionTarget]
    error: str | None = None


@dataclass(frozen=True, slots=True)
class PipelineRunResult:
    """Aggregate result for a full pipeline job."""

    job_id: str
    total_images: int
    processed_images: int
    skipped_images: int
    results: list[ImagePipelineResult]


@dataclass(frozen=True, slots=True)
class PipelineProgress:
    """Progress event emitted by the pipeline controller."""

    job_id: str
    image_index: int
    total_images: int
    completed_images: int
    stage: PipelineStage
    status: PipelineStatus
    message: str = ""


class PipelineController:
    """Coordinate automatic OCR, NLP, and object-detection redaction discovery."""

    def __init__(
        self,
        ocr_runner: OCRCallable = ocr,
        nlp_detector: NLPDetectorProtocol | None = None,
        object_detector: ObjectDetectorProtocol | None = None,
    ) -> None:
        self._ocr_runner = ocr_runner
        self._nlp_detector = nlp_detector if nlp_detector is not None else NLPDetector()
        self._object_detector = object_detector

    def process_images(
        self,
        images: list[Image.Image],
        settings: PipelineSettings | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> PipelineRunResult:
        """Run automatic detection for a batch of images.

        Images above ``settings.max_images`` are reported as skipped instead of
        causing the job to fail.
        """

        active_settings = settings if settings is not None else PipelineSettings()
        self._validate_inputs(images, active_settings)

        job_id = str(uuid4())
        total_images = len(images)
        process_count = min(total_images, active_settings.max_images)
        skipped_count = total_images - process_count
        completed_images = 0

        for index in range(process_count):
            self._emit(
                progress_callback,
                job_id,
                index,
                total_images,
                completed_images,
                PipelineStage.QUEUED,
                PipelineStatus.RUNNING,
            )

        results: list[ImagePipelineResult] = []
        worker_count = max(1, min(active_settings.worker_count, process_count or 1))

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_index = {
                executor.submit(
                    self._process_single_image,
                    index,
                    image,
                    active_settings,
                    job_id,
                    total_images,
                    lambda: completed_images,
                    progress_callback,
                ): index
                for index, image in enumerate(images[:process_count])
            }

            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                except Exception as exc:  # pragma: no cover - defensive boundary
                    result = ImagePipelineResult(
                        image_index=index,
                        success=False,
                        candidates=[],
                        redaction_targets=[],
                        error=str(exc),
                    )
                    self._emit(
                        progress_callback,
                        job_id,
                        index,
                        total_images,
                        completed_images,
                        PipelineStage.FAILED,
                        PipelineStatus.FAILED,
                        str(exc),
                    )
                completed_images += 1
                self._emit(
                    progress_callback,
                    job_id,
                    index,
                    total_images,
                    completed_images,
                    PipelineStage.COMPLETED if result.success else PipelineStage.FAILED,
                    PipelineStatus.SUCCESS if result.success else PipelineStatus.FAILED,
                    result.error or "",
                )
                results.append(result)

        for index in range(process_count, total_images):
            skipped_result = ImagePipelineResult(
                image_index=index,
                success=False,
                candidates=[],
                redaction_targets=[],
                error="Image skipped because the job exceeded the image limit.",
            )
            self._emit(
                progress_callback,
                job_id,
                index,
                total_images,
                completed_images,
                PipelineStage.SKIPPED,
                PipelineStatus.SKIPPED,
                skipped_result.error or "",
            )
            results.append(skipped_result)

        results.sort(key=lambda result: result.image_index)
        return PipelineRunResult(
            job_id=job_id,
            total_images=total_images,
            processed_images=process_count,
            skipped_images=skipped_count,
            results=results,
        )

    def _process_single_image(
        self,
        image_index: int,
        image: Image.Image,
        settings: PipelineSettings,
        job_id: str,
        total_images: int,
        completed_images_provider: CompletedCountProvider,
        progress_callback: ProgressCallback | None,
    ) -> ImagePipelineResult:
        self._emit(
            progress_callback,
            job_id,
            image_index,
            total_images,
            completed_images_provider(),
            PipelineStage.STARTED,
            PipelineStatus.RUNNING,
        )

        ocr_result = self._ocr_runner([image])[0]
        self._emit(
            progress_callback,
            job_id,
            image_index,
            total_images,
            completed_images_provider(),
            PipelineStage.OCR_COMPLETED,
            PipelineStatus.RUNNING,
        )

        text_candidates = self._detect_text_candidates(ocr_result, settings)
        self._emit(
            progress_callback,
            job_id,
            image_index,
            total_images,
            completed_images_provider(),
            PipelineStage.NLP_COMPLETED,
            PipelineStatus.RUNNING,
        )

        object_candidates = self._detect_object_candidates(image, settings)
        self._emit(
            progress_callback,
            job_id,
            image_index,
            total_images,
            completed_images_provider(),
            PipelineStage.OBJECT_DETECTION_COMPLETED,
            PipelineStatus.RUNNING,
        )

        candidates = text_candidates + object_candidates
        redaction_targets = [
            candidate.to_redaction_target(settings.redaction_type)
            for candidate in candidates
        ]
        self._emit(
            progress_callback,
            job_id,
            image_index,
            total_images,
            completed_images_provider(),
            PipelineStage.REDACTION_TARGETS_READY,
            PipelineStatus.RUNNING,
        )

        return ImagePipelineResult(
            image_index=image_index,
            success=True,
            candidates=candidates,
            redaction_targets=redaction_targets,
        )

    def _detect_text_candidates(
        self,
        ocr_result: OCRResult,
        settings: PipelineSettings,
    ) -> list[DetectionCandidate]:
        candidates: list[DetectionCandidate] = []
        for detection in ocr_result.detections:
            entities = self._nlp_detector.detect(detection.text)
            for entity in entities:
                if not _label_enabled(entity.label, settings.enabled_text_labels):
                    continue
                bounding_box = _entity_bounding_box(detection, entity)
                if bounding_box is None:
                    continue
                candidates.append(
                    DetectionCandidate(
                        bounding_box=bounding_box,
                        source=f"nlp:{entity.source}",
                        label=entity.label,
                        confidence=entity.confidence,
                        text=entity.text,
                    )
                )
        return candidates

    def _detect_object_candidates(
        self,
        image: Image.Image,
        settings: PipelineSettings,
    ) -> list[DetectionCandidate]:
        if self._object_detector is None:
            return []

        detected_objects = self._object_detector.detect([image])[0]
        candidates: list[DetectionCandidate] = []
        for detected_object in detected_objects:
            if not _label_enabled(
                detected_object.label,
                settings.enabled_object_labels,
            ):
                continue
            candidates.append(
                DetectionCandidate(
                    bounding_box=detected_object.bounding_box,
                    source="object_detection",
                    label=detected_object.label,
                    confidence=detected_object.confidence,
                )
            )
        return candidates

    def _validate_inputs(
        self,
        images: list[Image.Image],
        settings: PipelineSettings,
    ) -> None:
        if settings.max_images < 1:
            raise ValueError("max_images must be at least 1")
        if settings.worker_count < 1:
            raise ValueError("worker_count must be at least 1")
        for image in images:
            if not isinstance(image, Image.Image):
                raise TypeError(f"Expected PIL.Image.Image, got {type(image).__name__}")

    def _emit(
        self,
        progress_callback: ProgressCallback | None,
        job_id: str,
        image_index: int,
        total_images: int,
        completed_images: int,
        stage: PipelineStage,
        status: PipelineStatus,
        message: str = "",
    ) -> None:
        if progress_callback is None:
            return
        progress_callback(
            PipelineProgress(
                job_id=job_id,
                image_index=image_index,
                total_images=total_images,
                completed_images=completed_images,
                stage=stage,
                status=status,
                message=message,
            )
        )


def _label_enabled(label: str, enabled_labels: frozenset[str]) -> bool:
    return not enabled_labels or label in enabled_labels


def _entity_bounding_box(
    detection: TextDetection,
    entity: NLPEntity,
) -> BoundingBox | None:
    matched_boxes: list[BoundingBox] = []
    for word in detection.words:
        word_start = word.char_offset
        word_end = word_start + len(word.text)
        if word_start < entity.end and entity.start < word_end:
            matched_boxes.append(word.bounding_box)

    if not matched_boxes:
        return None

    return _union_bounding_boxes(matched_boxes)


def _union_bounding_boxes(boxes: list[BoundingBox]) -> BoundingBox:
    left = min(box.x for box in boxes)
    top = min(box.y for box in boxes)
    right = max(box.x + box.width for box in boxes)
    bottom = max(box.y + box.height for box in boxes)
    return BoundingBox(
        x=left,
        y=top,
        width=right - left,
        height=bottom - top,
    )
