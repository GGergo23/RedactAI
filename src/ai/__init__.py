"""AI module for RedactAI -- ML models for detecting sensitive information."""

from src.ai.ocr import ocr
from src.ai.types import BoundingBox, OCRResult, OCRWord, TextDetection

__all__ = [
    "BoundingBox",
    "OCRResult",
    "OCRWord",
    "TextDetection",
    "ocr",
]
