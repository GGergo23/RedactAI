"""Tesseract OCR integration for RedactAI.

Extracts word-level text and bounding boxes from images using pytesseract.
Requires the Tesseract binary to be installed on the system
(e.g. ``brew install tesseract`` on macOS, ``apt-get install tesseract-ocr`` on Ubuntu).

## OCR string format contract (for T3.2 NLP and T2.1 Pipeline)

The full text string returned in ``TextDetection.text`` is assembled as follows:

  - Words on the **same line**: joined by a single space ``" "``
  - **Lines** within the same block: joined by ``"\\n"``
  - Separate **blocks**: joined by ``"\\n\\n"``

Every ``OCRWord`` records its ``char_offset`` — the exact start index of that word
in the assembled string. This allows the pipeline to map NLP character indices
back to pixel-level bounding boxes.
"""

from __future__ import annotations

from itertools import groupby
from operator import itemgetter

import pytesseract
from PIL import Image

from src.ai.types import BoundingBox, OCRResult, OCRWord, TextDetection


def run_ocr(images: list[Image.Image], lang: str = "eng") -> OCRResult:
    """Run Tesseract OCR on a list of images.

    Args:
        images: PIL Image objects to process.
        lang: Tesseract language code (default ``"eng"``).

    Returns:
        An ``OCRResult`` containing one ``TextDetection`` per input image.

    Raises:
        TypeError: If any element in *images* is not a ``PIL.Image.Image``.
        pytesseract.TesseractNotFoundError: If the Tesseract binary is not installed.
    """
    for img in images:
        if not isinstance(img, Image.Image):
            raise TypeError(f"Expected PIL.Image.Image, got {type(img).__name__}")

    detections = [_process_single_image(img, lang) for img in images]
    return OCRResult(detections=detections)


def extract_text(images: list[Image.Image], lang: str = "eng") -> list[str]:
    """Convenience wrapper that returns only the assembled text strings.

    Args:
        images: PIL Image objects to process.
        lang: Tesseract language code (default ``"eng"``).

    Returns:
        A list of strings, one per input image.
    """
    result = run_ocr(images, lang=lang)
    return [d.text for d in result.detections]


def _process_single_image(image: Image.Image, lang: str) -> TextDetection:
    """Extract text and word-level bounding boxes from a single image."""
    data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)

    n_entries = len(data["text"])

    rows = []
    for i in range(n_entries):
        text = data["text"][i].strip()
        conf = float(data["conf"][i])
        if not text or conf == -1:
            continue
        rows.append(
            {
                "block_num": data["block_num"][i],
                "par_num": data["par_num"][i],
                "line_num": data["line_num"][i],
                "word_num": data["word_num"][i],
                "left": data["left"][i],
                "top": data["top"][i],
                "width": data["width"][i],
                "height": data["height"][i],
                "conf": conf,
                "text": text,
            }
        )

    if not rows:
        return TextDetection(text="", words=[])

    rows.sort(key=lambda r: (r["block_num"], r["par_num"], r["line_num"], r["word_num"]))

    text_parts: list[str] = []
    words: list[OCRWord] = []
    char_pos = 0

    block_line_key = itemgetter("block_num", "par_num", "line_num")

    prev_block: int | None = None
    prev_line_key: tuple | None = None

    for line_key, line_words_iter in groupby(rows, key=block_line_key):
        line_words = list(line_words_iter)
        current_block = line_words[0]["block_num"]

        if prev_line_key is not None:
            if current_block != prev_block:
                separator = "\n\n"
            else:
                separator = "\n"
            text_parts.append(separator)
            char_pos += len(separator)

        for j, w in enumerate(line_words):
            if j > 0:
                text_parts.append(" ")
                char_pos += 1

            text_parts.append(w["text"])
            words.append(
                OCRWord(
                    text=w["text"],
                    bounding_box=BoundingBox(x=w["left"], y=w["top"], width=w["width"], height=w["height"]),
                    confidence=w["conf"],
                    char_offset=char_pos,
                )
            )
            char_pos += len(w["text"])

        prev_block = current_block
        prev_line_key = line_key

    full_text = "".join(text_parts)
    return TextDetection(text=full_text, words=words)
