"""Tests for OpenCV-based redaction operations."""

from __future__ import annotations

import numpy as np
from PIL import Image

from src.ai.types import BoundingBox
from src.redactEngine.redactor import RedactionTarget, RedactionType, apply_redactions


def _make_gradient_image(width: int = 64, height: int = 64) -> Image.Image:
    """Create a deterministic image with high local detail for pixelation tests."""
    x = np.arange(width, dtype=np.uint16)
    y = np.arange(height, dtype=np.uint16)[:, None]
    red = ((x + y) % 256).astype(np.uint8)
    green = ((x * 3 + y * 5) % 256).astype(np.uint8)
    blue = ((x * 7 + y * 11) % 256).astype(np.uint8)
    rgb = np.stack([red, green, blue], axis=-1)
    return Image.fromarray(rgb, mode="RGB")


def test_black_bar_only_affects_target_region() -> None:
    image = _make_gradient_image()
    original = np.array(image)

    target = RedactionTarget(
        location=BoundingBox(x=10, y=12, width=20, height=16),
        type=RedactionType.BLACK_BAR,
    )
    redacted = np.array(apply_redactions(image, [target]))

    assert np.array_equal(redacted[12:28, 10:30], np.zeros((16, 20, 3), dtype=np.uint8))

    outside_original = original.copy()
    outside_redacted = redacted.copy()
    outside_original[12:28, 10:30] = 0
    outside_redacted[12:28, 10:30] = 0
    assert np.array_equal(outside_original, outside_redacted)


def test_pixelation_permanently_changes_target_region_only() -> None:
    image = _make_gradient_image()
    original = np.array(image)

    target = RedactionTarget(
        location=BoundingBox(x=8, y=8, width=40, height=40),
        type=RedactionType.PIXELATE,
    )
    redacted = np.array(apply_redactions(image, [target]))

    original_region = original[8:48, 8:48]
    redacted_region = redacted[8:48, 8:48]

    assert not np.array_equal(original_region, redacted_region)

    outside_original = original.copy()
    outside_redacted = redacted.copy()
    outside_original[8:48, 8:48] = 0
    outside_redacted[8:48, 8:48] = 0
    assert np.array_equal(outside_original, outside_redacted)


def test_out_of_bounds_bbox_is_clamped() -> None:
    image = _make_gradient_image(width=16, height=16)
    original = np.array(image)

    target = RedactionTarget(
        location=BoundingBox(x=12, y=12, width=20, height=20),
        type=RedactionType.BLACK_BAR,
    )
    redacted = np.array(apply_redactions(image, [target]))

    assert np.array_equal(redacted[12:16, 12:16], np.zeros((4, 4, 3), dtype=np.uint8))
    assert np.array_equal(redacted[0:12, :], original[0:12, :])
    assert np.array_equal(redacted[:, 0:12], original[:, 0:12])
