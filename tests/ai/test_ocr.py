"""Tests for the OCR module."""

from __future__ import annotations

import shutil
from unittest.mock import patch

import pytest
from PIL import Image

from src.ai.ocr import ocr
from src.ai.types import BoundingBox, OCRResult, TextDetection

pytesseract_available = pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="Tesseract OCR not installed",
)


def _make_tesseract_dict(rows: list[dict]) -> dict:
    """Build a pytesseract-style output dict from a compact list of row dicts.

    Each row should have keys: block_num, par_num, line_num, word_num,
    left, top, width, height, conf, text.
    """
    keys = [
        "level",
        "page_num",
        "block_num",
        "par_num",
        "line_num",
        "word_num",
        "left",
        "top",
        "width",
        "height",
        "conf",
        "text",
    ]
    result: dict[str, list] = {k: [] for k in keys}
    for row in rows:
        result["level"].append(5)
        result["page_num"].append(1)
        for k in keys[2:]:
            result[k].append(row[k])
    return result


EMPTY_DICT = _make_tesseract_dict([])

TWO_WORDS_SAME_LINE = _make_tesseract_dict(
    [
        {
            "block_num": 1,
            "par_num": 1,
            "line_num": 1,
            "word_num": 1,
            "left": 10,
            "top": 20,
            "width": 50,
            "height": 15,
            "conf": 95.0,
            "text": "Hello",
        },
        {
            "block_num": 1,
            "par_num": 1,
            "line_num": 1,
            "word_num": 2,
            "left": 70,
            "top": 20,
            "width": 60,
            "height": 15,
            "conf": 92.0,
            "text": "World",
        },
    ]
)

TWO_LINES_SAME_BLOCK = _make_tesseract_dict(
    [
        {
            "block_num": 1,
            "par_num": 1,
            "line_num": 1,
            "word_num": 1,
            "left": 10,
            "top": 10,
            "width": 40,
            "height": 15,
            "conf": 90.0,
            "text": "Line1",
        },
        {
            "block_num": 1,
            "par_num": 1,
            "line_num": 2,
            "word_num": 1,
            "left": 10,
            "top": 40,
            "width": 40,
            "height": 15,
            "conf": 88.0,
            "text": "Line2",
        },
    ]
)

TWO_BLOCKS = _make_tesseract_dict(
    [
        {
            "block_num": 1,
            "par_num": 1,
            "line_num": 1,
            "word_num": 1,
            "left": 10,
            "top": 10,
            "width": 50,
            "height": 15,
            "conf": 93.0,
            "text": "BlockA",
        },
        {
            "block_num": 2,
            "par_num": 1,
            "line_num": 1,
            "word_num": 1,
            "left": 10,
            "top": 100,
            "width": 50,
            "height": 15,
            "conf": 91.0,
            "text": "BlockB",
        },
    ]
)

WITH_LOW_CONF = _make_tesseract_dict(
    [
        {
            "block_num": 1,
            "par_num": 1,
            "line_num": 1,
            "word_num": 1,
            "left": 10,
            "top": 10,
            "width": 50,
            "height": 15,
            "conf": -1,
            "text": "ghost",
        },
        {
            "block_num": 1,
            "par_num": 1,
            "line_num": 1,
            "word_num": 2,
            "left": 70,
            "top": 10,
            "width": 50,
            "height": 15,
            "conf": 90.0,
            "text": "real",
        },
    ]
)

WITH_EMPTY_TEXT = _make_tesseract_dict(
    [
        {
            "block_num": 1,
            "par_num": 1,
            "line_num": 1,
            "word_num": 1,
            "left": 10,
            "top": 10,
            "width": 50,
            "height": 15,
            "conf": 90.0,
            "text": "",
        },
        {
            "block_num": 1,
            "par_num": 1,
            "line_num": 1,
            "word_num": 2,
            "left": 70,
            "top": 10,
            "width": 50,
            "height": 15,
            "conf": 90.0,
            "text": "   ",
        },
        {
            "block_num": 1,
            "par_num": 1,
            "line_num": 1,
            "word_num": 3,
            "left": 130,
            "top": 10,
            "width": 50,
            "height": 15,
            "conf": 90.0,
            "text": "visible",
        },
    ]
)


# ---------------------------------------------------------------------------
# Unit tests (mocked, no Tesseract binary needed)
# ---------------------------------------------------------------------------


class TestOcrReturnType:
    @patch("src.ai.ocr.pytesseract.image_to_data", return_value=TWO_WORDS_SAME_LINE)
    def test_returns_list_of_ocr_results(self, mock_data):
        img = Image.new("RGB", (100, 50))
        result = ocr([img])
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], OCRResult)
        assert len(result[0].detections) == 1
        assert isinstance(result[0].detections[0], TextDetection)

    @patch("src.ai.ocr.pytesseract.image_to_data", return_value=TWO_WORDS_SAME_LINE)
    def test_multiple_images(self, mock_data):
        imgs = [Image.new("RGB", (100, 50)), Image.new("RGB", (100, 50))]
        result = ocr(imgs)
        assert len(result) == 2
        assert all(isinstance(r, OCRResult) for r in result)


class TestTextAssembly:
    @patch("src.ai.ocr.pytesseract.image_to_data", return_value=TWO_WORDS_SAME_LINE)
    def test_space_between_words_on_same_line(self, mock_data):
        result = ocr([Image.new("RGB", (100, 50))])
        assert result[0].detections[0].text == "Hello World"

    @patch("src.ai.ocr.pytesseract.image_to_data", return_value=TWO_LINES_SAME_BLOCK)
    def test_newline_between_lines(self, mock_data):
        result = ocr([Image.new("RGB", (100, 50))])
        assert result[0].detections[0].text == "Line1\nLine2"

    @patch("src.ai.ocr.pytesseract.image_to_data", return_value=TWO_BLOCKS)
    def test_double_newline_between_blocks(self, mock_data):
        result = ocr([Image.new("RGB", (100, 50))])
        assert result[0].detections[0].text == "BlockA\n\nBlockB"


class TestCharOffsets:
    @patch("src.ai.ocr.pytesseract.image_to_data", return_value=TWO_WORDS_SAME_LINE)
    def test_offsets_on_same_line(self, mock_data):
        result = ocr([Image.new("RGB", (100, 50))])
        words = result[0].detections[0].words
        assert words[0].char_offset == 0  # "Hello" starts at 0
        assert words[1].char_offset == 6  # "World" starts at 6 (after "Hello ")

    @patch("src.ai.ocr.pytesseract.image_to_data", return_value=TWO_LINES_SAME_BLOCK)
    def test_offsets_across_lines(self, mock_data):
        result = ocr([Image.new("RGB", (100, 50))])
        words = result[0].detections[0].words
        assert words[0].char_offset == 0  # "Line1"
        assert words[1].char_offset == 6  # "Line2" (after "Line1\n")

    @patch("src.ai.ocr.pytesseract.image_to_data", return_value=TWO_BLOCKS)
    def test_offsets_across_blocks(self, mock_data):
        result = ocr([Image.new("RGB", (100, 50))])
        words = result[0].detections[0].words
        assert words[0].char_offset == 0  # "BlockA"
        assert words[1].char_offset == 8  # "BlockB" (after "BlockA\n\n")

    @patch("src.ai.ocr.pytesseract.image_to_data", return_value=TWO_WORDS_SAME_LINE)
    def test_char_offset_invariant(self, mock_data):
        """The fundamental contract: text[offset:offset+len] == word.text."""
        result = ocr([Image.new("RGB", (100, 50))])
        det = result[0].detections[0]
        for word in det.words:
            assert det.text[word.char_offset : word.char_offset + len(word.text)] == word.text


class TestBoundingBoxes:
    @patch("src.ai.ocr.pytesseract.image_to_data", return_value=TWO_WORDS_SAME_LINE)
    def test_bounding_box_values_preserved(self, mock_data):
        result = ocr([Image.new("RGB", (100, 50))])
        box = result[0].detections[0].words[0].bounding_box
        assert box == BoundingBox(x=10, y=20, width=50, height=15)


class TestFiltering:
    @patch("src.ai.ocr.pytesseract.image_to_data", return_value=WITH_LOW_CONF)
    def test_filters_negative_confidence(self, mock_data):
        result = ocr([Image.new("RGB", (100, 50))])
        words = result[0].detections[0].words
        assert len(words) == 1
        assert words[0].text == "real"

    @patch("src.ai.ocr.pytesseract.image_to_data", return_value=WITH_EMPTY_TEXT)
    def test_filters_empty_and_whitespace_text(self, mock_data):
        result = ocr([Image.new("RGB", (100, 50))])
        words = result[0].detections[0].words
        assert len(words) == 1
        assert words[0].text == "visible"

    @patch("src.ai.ocr.pytesseract.image_to_data", return_value=EMPTY_DICT)
    def test_empty_image_returns_empty_detection(self, mock_data):
        result = ocr([Image.new("RGB", (100, 50))])
        det = result[0].detections[0]
        assert det.text == ""
        assert det.words == []


class TestOcrTextContent:
    @patch("src.ai.ocr.pytesseract.image_to_data", return_value=TWO_WORDS_SAME_LINE)
    def test_detection_contains_expected_text(self, mock_data):
        result = ocr([Image.new("RGB", (100, 50))])
        assert result[0].detections[0].text == "Hello World"


class TestInputValidation:
    def test_non_image_raises_type_error(self):
        with pytest.raises(TypeError, match="Expected PIL.Image.Image"):
            ocr(["not_an_image"])


# ---------------------------------------------------------------------------
# Integration tests (require Tesseract binary)
# ---------------------------------------------------------------------------


@pytesseract_available
@pytest.mark.integration
class TestOCRIntegration:
    def test_ocr_on_generated_image(self, sample_ocr_image):
        result = ocr([sample_ocr_image])
        det = result[0].detections[0]
        text_lower = det.text.lower()
        assert "hello" in text_lower
        assert "world" in text_lower
        assert len(det.words) >= 2
        for word in det.words:
            assert word.bounding_box.width > 0
            assert word.bounding_box.height > 0

    def test_multiline_ocr(self, multiline_ocr_image):
        result = ocr([multiline_ocr_image])
        det = result[0].detections[0]
        assert "\n" in det.text

    def test_char_offset_contract(self, sample_ocr_image):
        """Every word's char_offset must correctly index into the full text."""
        result = ocr([sample_ocr_image])
        det = result[0].detections[0]
        for word in det.words:
            actual = det.text[word.char_offset : word.char_offset + len(word.text)]
            assert actual == word.text, (
                f"Contract violation: text[{word.char_offset}:{word.char_offset + len(word.text)}] "
                f"== {actual!r}, expected {word.text!r}"
            )
