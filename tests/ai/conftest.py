"""Shared fixtures for AI module tests."""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw, ImageFont


def _get_large_font(size: int = 36) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Return a font large enough for reliable OCR."""
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


@pytest.fixture
def sample_ocr_image() -> Image.Image:
    """A 400x100 white image with 'Hello World' in large black text."""
    img = Image.new("RGB", (400, 100), color="white")
    draw = ImageDraw.Draw(img)
    font = _get_large_font(36)
    draw.text((10, 30), "Hello World", fill="black", font=font)
    return img


@pytest.fixture
def multiline_ocr_image() -> Image.Image:
    """A 400x200 white image with two lines of text on separate lines."""
    img = Image.new("RGB", (400, 200), color="white")
    draw = ImageDraw.Draw(img)
    font = _get_large_font(36)
    draw.text((10, 20), "First Line", fill="black", font=font)
    draw.text((10, 110), "Second Line", fill="black", font=font)
    return img
