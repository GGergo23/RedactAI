"""Shared data types for the AI module.

These types define the interface contract between:
  - T3.1 OCR  (produces TextDetection with full text + word-level bounding boxes)
  - T3.2 NLP  (consumes the plain text string, produces NLPEntity with char indices)
  - T2.1 Pipeline (maps NLP char indices back to pixel bounding boxes via OCRWord.char_offset)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box in pixel coordinates."""

    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class OCRWord:
    """A single word detected by OCR, with its position in both pixel and text space.

    Attributes:
        text: The word string as reported by Tesseract.
        bounding_box: Pixel-level location in the source image.
        confidence: Tesseract confidence score (0-100).
        char_offset: Start index of this word in the parent TextDetection.text string.
            Invariant: ``detection.text[word.char_offset:word.char_offset + len(word.text)] == word.text``
    """

    text: str
    bounding_box: BoundingBox
    confidence: float
    char_offset: int


@dataclass(frozen=True)
class TextDetection:
    """OCR result for a single image.

    ``text`` is the full reassembled string built from Tesseract's word-level output
    using the following join contract:

      - Words on the same line: joined by ``" "`` (single space)
      - Lines in the same block: joined by ``"\\n"``
      - Separate blocks: joined by ``"\\n\\n"``

    This is the exact string that the NLP module (T3.2) receives. Character indices
    produced by NLP (``NLPEntity.start`` / ``NLPEntity.end``) refer to positions in
    this string. The pipeline (T2.1) maps those indices back to pixel rectangles by
    scanning ``words`` and matching on ``OCRWord.char_offset``.
    """

    text: str
    words: list[OCRWord]


@dataclass(frozen=True)
class OCRResult:
    """Top-level return type from ``run_ocr``. One ``TextDetection`` per input image."""

    detections: list[TextDetection]
