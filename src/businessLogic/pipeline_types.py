"""Shared types for the automatic detection pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Protocol

from PIL import Image

from src.ai.types import BoundingBox, DetectedObject, NLPEntity, OCRResult
from src.redactEngine import RedactionType

MAX_IMAGES_PER_JOB = 50


class PipelineStage(str, Enum):
    """High-level pipeline stage reported to the UI."""

    QUEUED = "queued"
    STARTED = "started"
    IMAGE_LOADED = "image_loaded"
    OCR_COMPLETED = "ocr_completed"
    NLP_COMPLETED = "nlp_completed"
    OBJECT_DETECTION_COMPLETED = "object_detection_completed"
    DETECTIONS_READY = "detections_ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    FAILED = "failed"


class PipelineStatus(str, Enum):
    """Progress status for a pipeline update."""

    RUNNING = "running"
    SUCCESS = "success"
    CANCELLED = "cancelled"
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
ResultCallback = Callable[["PipelineRunResult"], None]
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
    """One automatically detected sensitive region."""

    bounding_box: BoundingBox
    source: str
    label: str
    confidence: float
    text: str | None = None


@dataclass(frozen=True, slots=True)
class ImagePipelineResult:
    """Pipeline outcome for one input image path."""

    input_index: int
    image_path: str
    success: bool
    detections: list[DetectionCandidate]
    error: str | None = None


@dataclass(frozen=True, slots=True)
class PipelineRunResult:
    """Aggregate result for a full pipeline job."""

    job_id: str
    total_images: int
    processed_images: int
    skipped_images: int
    cancelled: bool
    results: list[ImagePipelineResult]


@dataclass(frozen=True, slots=True)
class PipelineProgress:
    """Progress event emitted by the pipeline controller."""

    job_id: str
    image_path: str
    total_images: int
    completed_images: int
    stage: PipelineStage
    status: PipelineStatus
    message: str = ""


@dataclass(frozen=True, slots=True)
class LoadedImage:
    """Input image loaded from a file path."""

    path: Path
    image: Image.Image
