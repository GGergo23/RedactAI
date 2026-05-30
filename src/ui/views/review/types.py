"""Data contracts for the redaction review page."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from src.ai.types import DetectedObject
from src.redactEngine.redactor import RedactionTarget


@dataclass(frozen=True, slots=True)
class LoadedImageDetections:
    """One image that loaded successfully, with its automatic detections."""

    path: Path
    image: Image.Image
    detections: list[DetectedObject]


@dataclass(frozen=True, slots=True)
class ReviewPageInput:
    """Launch-extra payload for the review page."""

    failed_paths: list[Path]
    loaded_images: list[LoadedImageDetections]


@dataclass(frozen=True, slots=True)
class ApprovedImageRedactions:
    """One image with its user-approved redaction targets."""

    path: Path
    image: Image.Image
    approved_targets: list[RedactionTarget]


@dataclass(frozen=True, slots=True)
class ReviewPageOutput:
    """Launch-extra payload forwarded to the next page (export/processing)."""

    failed_paths: list[Path]
    loaded_images: list[ApprovedImageRedactions]
