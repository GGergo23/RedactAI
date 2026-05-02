"""AI module for RedactAI -- ML models for detecting sensitive information."""

from src.ai.ocr import extract_text, run_ocr
from src.ai.types import BoundingBox, OCRResult, OCRWord, TextDetection

__all__ = [
    "BoundingBox",
    "OCRResult",
    "OCRWord",
    "TextDetection",
    "extract_text",
    "run_ocr",
]
