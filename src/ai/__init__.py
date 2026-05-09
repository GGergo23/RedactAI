"""AI module for RedactAI -- ML models for detecting sensitive information."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

from src.ai.ocr import ocr
from src.ai.types import BoundingBox, DetectedObject, OCRResult, OCRWord, TextDetection

if TYPE_CHECKING:
    from src.ai.object_detector import (
        FACE_MODEL_FILENAME,
        LICENSE_PLATE_MODEL_FILENAME,
        FaceYOLOv8Backend,
        LicensePlateYOLOv11Backend,
        ModelLoadError,
        ObjectDetector,
        default_model_paths,
        download_default_models,
    )

__all__ = [
    "BoundingBox",
    "DetectedObject",
    "FACE_MODEL_FILENAME",
    "FaceYOLOv8Backend",
    "LICENSE_PLATE_MODEL_FILENAME",
    "LicensePlateYOLOv11Backend",
    "ModelLoadError",
    "OCRResult",
    "OCRWord",
    "ObjectDetector",
    "TextDetection",
    "default_model_paths",
    "download_default_models",
    "ocr",
]

_OBJECT_DETECTOR_EXPORTS = {
    "FACE_MODEL_FILENAME",
    "LICENSE_PLATE_MODEL_FILENAME",
    "FaceYOLOv8Backend",
    "LicensePlateYOLOv11Backend",
    "ModelLoadError",
    "ObjectDetector",
    "default_model_paths",
    "download_default_models",
}


def __getattr__(name: str) -> Any:
    if name in _OBJECT_DETECTOR_EXPORTS:
        module = import_module("src.ai.object_detector")
        return getattr(module, name)
    if name in __all__ and name in globals():
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
