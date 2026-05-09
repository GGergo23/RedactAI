"""AI module for RedactAI -- ML models for detecting sensitive information."""

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
from src.ai.ocr import ocr
from src.ai.types import BoundingBox, DetectedObject, OCRResult, OCRWord, TextDetection

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
