"""Automatic detection pipeline orchestration."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Event
from uuid import uuid4

from PIL import Image

from src.ai.detector import NLPDetector
from src.ai.ocr import ocr
from src.ai.types import BoundingBox, NLPEntity, OCRResult, TextDetection
from src.businessLogic.pipeline_types import (
    CompletedCountProvider,
    DetectionCandidate,
    ImagePipelineResult,
    LoadedImage,
    NLPDetectorProtocol,
    ObjectDetectorProtocol,
    OCRCallable,
    PipelineProgress,
    PipelineRunResult,
    PipelineSettings,
    PipelineStage,
    PipelineStatus,
    ProgressCallback,
    ResultCallback,
)
from src.persistance import read_image


class PipelineTask:
    """Handle for a running non-blocking pipeline job."""

    def __init__(self, job_id: str, cancel_event: Event, future: Future) -> None:
        self.job_id = job_id
        self._cancel_event = cancel_event
        self._future = future

    def cancel(self) -> None:
        """Request cancellation of the running pipeline job."""

        self._cancel_event.set()

    @property
    def cancelled(self) -> bool:
        """Return whether cancellation has been requested."""

        return self._cancel_event.is_set()

    @property
    def done(self) -> bool:
        """Return whether the background pipeline job has finished."""

        return self._future.done()


class PipelineController:
    """Coordinate automatic OCR, NLP, and object-detection discovery."""

    def __init__(
        self,
        ocr_runner: OCRCallable = ocr,
        nlp_detector: NLPDetectorProtocol | None = None,
        object_detector: ObjectDetectorProtocol | None = None,
    ) -> None:
        self._ocr_runner = ocr_runner
        self._nlp_detector = nlp_detector if nlp_detector is not None else NLPDetector()
        self._object_detector = object_detector
        self._task_executor = ThreadPoolExecutor(max_workers=1)

    def start_detection(
        self,
        image_paths: list[str],
        progress_callback: ProgressCallback | None = None,
        result_callback: ResultCallback | None = None,
        settings: PipelineSettings | None = None,
    ) -> PipelineTask:
        """Start automatic detection in the background and return immediately."""

        active_settings = settings if settings is not None else PipelineSettings()
        self._validate_start_input(image_paths, active_settings)

        job_id = str(uuid4())
        cancel_event = Event()
        future = self._task_executor.submit(
            self._run_detection_job,
            job_id,
            list(image_paths),
            active_settings,
            progress_callback,
            result_callback,
            cancel_event,
        )
        return PipelineTask(job_id=job_id, cancel_event=cancel_event, future=future)

    def process_image_paths(
        self,
        image_paths: list[str],
        settings: PipelineSettings | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> PipelineRunResult:
        """Run detection synchronously for tests and non-UI callers."""

        active_settings = settings if settings is not None else PipelineSettings()
        self._validate_start_input(image_paths, active_settings)
        return self._run_detection_job(
            job_id=str(uuid4()),
            image_paths=list(image_paths),
            settings=active_settings,
            progress_callback=progress_callback,
            result_callback=None,
            cancel_event=Event(),
        )

    def _run_detection_job(
        self,
        job_id: str,
        image_paths: list[str],
        settings: PipelineSettings,
        progress_callback: ProgressCallback | None,
        result_callback: ResultCallback | None,
        cancel_event: Event,
    ) -> PipelineRunResult:
        total_images = len(image_paths)
        process_count = min(total_images, settings.max_images)
        skipped_count = total_images - process_count
        completed_images = 0
        results: list[ImagePipelineResult] = []

        for image_path in image_paths[:process_count]:
            self._emit(
                progress_callback,
                job_id,
                image_path,
                total_images,
                completed_images,
                PipelineStage.QUEUED,
                PipelineStatus.RUNNING,
            )

        worker_count = max(1, min(settings.worker_count, process_count or 1))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_item = {
                executor.submit(
                    self._process_single_path,
                    index,
                    image_path,
                    settings,
                    job_id,
                    total_images,
                    lambda: completed_images,
                    progress_callback,
                    cancel_event,
                ): (index, image_path)
                for index, image_path in enumerate(image_paths[:process_count])
                if not cancel_event.is_set()
            }

            for future in as_completed(future_to_item):
                index, image_path = future_to_item[future]
                try:
                    result = future.result()
                except Exception as exc:  # pragma: no cover - defensive boundary
                    result = ImagePipelineResult(
                        input_index=index,
                        image_path=image_path,
                        success=False,
                        detections=[],
                        error=str(exc),
                    )
                    self._emit(
                        progress_callback,
                        job_id,
                        image_path,
                        total_images,
                        completed_images,
                        PipelineStage.FAILED,
                        PipelineStatus.FAILED,
                        str(exc),
                    )
                completed_images += 1
                self._emit_completion(
                    progress_callback,
                    job_id,
                    result,
                    total_images,
                    completed_images,
                    cancel_event,
                )
                results.append(result)

        for index, image_path in enumerate(
            image_paths[process_count:],
            start=process_count,
        ):
            skipped_result = ImagePipelineResult(
                input_index=index,
                image_path=image_path,
                success=False,
                detections=[],
                error="Image skipped because the job exceeded the image limit.",
            )
            self._emit(
                progress_callback,
                job_id,
                image_path,
                total_images,
                completed_images,
                PipelineStage.SKIPPED,
                PipelineStatus.SKIPPED,
                skipped_result.error or "",
            )
            results.append(skipped_result)

        run_result = PipelineRunResult(
            job_id=job_id,
            total_images=total_images,
            processed_images=process_count,
            skipped_images=skipped_count,
            cancelled=cancel_event.is_set(),
            results=sorted(results, key=lambda result: result.input_index),
        )
        if result_callback is not None:
            result_callback(run_result)
        return run_result

    def _process_single_path(
        self,
        input_index: int,
        image_path: str,
        settings: PipelineSettings,
        job_id: str,
        total_images: int,
        completed_images_provider: CompletedCountProvider,
        progress_callback: ProgressCallback | None,
        cancel_event: Event,
    ) -> ImagePipelineResult:
        if cancel_event.is_set():
            return _cancelled_result(input_index, image_path)

        self._emit(
            progress_callback,
            job_id,
            image_path,
            total_images,
            completed_images_provider(),
            PipelineStage.STARTED,
            PipelineStatus.RUNNING,
        )

        loaded_image = LoadedImage(path=Path(image_path), image=read_image(image_path))
        self._emit(
            progress_callback,
            job_id,
            image_path,
            total_images,
            completed_images_provider(),
            PipelineStage.IMAGE_LOADED,
            PipelineStatus.RUNNING,
        )

        if cancel_event.is_set():
            return _cancelled_result(input_index, image_path)

        ocr_result = self._ocr_runner([loaded_image.image])[0]
        self._emit(
            progress_callback,
            job_id,
            image_path,
            total_images,
            completed_images_provider(),
            PipelineStage.OCR_COMPLETED,
            PipelineStatus.RUNNING,
        )

        if cancel_event.is_set():
            return _cancelled_result(input_index, image_path)

        text_detections = self._detect_text_candidates(ocr_result, settings)
        self._emit(
            progress_callback,
            job_id,
            image_path,
            total_images,
            completed_images_provider(),
            PipelineStage.NLP_COMPLETED,
            PipelineStatus.RUNNING,
        )

        if cancel_event.is_set():
            return _cancelled_result(input_index, image_path)

        object_detections = self._detect_object_candidates(loaded_image.image, settings)
        self._emit(
            progress_callback,
            job_id,
            image_path,
            total_images,
            completed_images_provider(),
            PipelineStage.OBJECT_DETECTION_COMPLETED,
            PipelineStatus.RUNNING,
        )

        detections = text_detections + object_detections
        self._emit(
            progress_callback,
            job_id,
            image_path,
            total_images,
            completed_images_provider(),
            PipelineStage.DETECTIONS_READY,
            PipelineStatus.RUNNING,
        )

        return ImagePipelineResult(
            input_index=input_index,
            image_path=image_path,
            success=True,
            detections=detections,
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

    def _validate_start_input(
        self,
        image_paths: list[str],
        settings: PipelineSettings,
    ) -> None:
        if settings.max_images < 1:
            raise ValueError("max_images must be at least 1")
        if settings.worker_count < 1:
            raise ValueError("worker_count must be at least 1")
        for image_path in image_paths:
            if not isinstance(image_path, str):
                raise TypeError(
                    f"Expected image path str, got {type(image_path).__name__}"
                )

    def _emit_completion(
        self,
        progress_callback: ProgressCallback | None,
        job_id: str,
        result: ImagePipelineResult,
        total_images: int,
        completed_images: int,
        cancel_event: Event,
    ) -> None:
        if cancel_event.is_set() and not result.success:
            stage = PipelineStage.CANCELLED
            status = PipelineStatus.CANCELLED
        else:
            stage = PipelineStage.COMPLETED if result.success else PipelineStage.FAILED
            status = PipelineStatus.SUCCESS if result.success else PipelineStatus.FAILED

        self._emit(
            progress_callback,
            job_id,
            result.image_path,
            total_images,
            completed_images,
            stage,
            status,
            result.error or "",
        )

    def _emit(
        self,
        progress_callback: ProgressCallback | None,
        job_id: str,
        image_path: str,
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
                image_path=image_path,
                total_images=total_images,
                completed_images=completed_images,
                stage=stage,
                status=status,
                message=message,
            )
        )


def _cancelled_result(input_index: int, image_path: str) -> ImagePipelineResult:
    return ImagePipelineResult(
        input_index=input_index,
        image_path=image_path,
        success=False,
        detections=[],
        error="Detection cancelled.",
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
