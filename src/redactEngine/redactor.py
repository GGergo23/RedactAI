"""Image redaction helpers implemented with OpenCV."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np
from PIL import Image

from src.ai.types import BoundingBox


class RedactionType(str, Enum):
    """Supported redaction styles."""

    BLACK_BAR = "black_bar"
    PIXELATE = "pixelate"


@dataclass(frozen=True, slots=True)
class RedactionTarget:
    """Single redaction instruction for a rectangular image region."""

    location: BoundingBox
    type: RedactionType


def _clamp_bbox(
    location: BoundingBox, width: int, height: int
) -> tuple[int, int, int, int] | None:
    """Clamp a bounding box to image dimensions and return x1, y1, x2, y2."""
    if location.width <= 0 or location.height <= 0:
        return None

    x1 = max(0, location.x)
    y1 = max(0, location.y)
    x2 = min(width, location.x + location.width)
    y2 = min(height, location.y + location.height)

    if x1 >= x2 or y1 >= y2:
        return None
    return x1, y1, x2, y2


def _apply_heavy_pixelation(region: np.ndarray) -> np.ndarray:
    """Apply strong pixelation by aggressive downscale/upscale."""
    region_height, region_width = region.shape[:2]
    downscale_width = max(1, region_width // 16)
    downscale_height = max(1, region_height // 16)

    small = cv2.resize(
        region,
        (downscale_width, downscale_height),
        interpolation=cv2.INTER_LINEAR,
    )
    return cv2.resize(
        small,
        (region_width, region_height),
        interpolation=cv2.INTER_NEAREST,
    )


def apply_redactions(image: Image.Image, targets: list[RedactionTarget]) -> Image.Image:
    """Apply rectangle-based redactions and return a new image.

    Args:
        image: Source image.
        targets: Redaction instructions with location and type.

    Returns:
        A new ``PIL.Image`` with the requested regions permanently modified.
    """
    rgb_array = np.array(image.convert("RGB"), copy=True)
    bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
    image_height, image_width = bgr_array.shape[:2]

    for target in targets:
        clamped = _clamp_bbox(target.location, image_width, image_height)
        if clamped is None:
            continue

        x1, y1, x2, y2 = clamped

        if target.type == RedactionType.BLACK_BAR:
            bgr_array[y1:y2, x1:x2] = (0, 0, 0)
            continue

        if target.type == RedactionType.PIXELATE:
            region = bgr_array[y1:y2, x1:x2]
            bgr_array[y1:y2, x1:x2] = _apply_heavy_pixelation(region)
            continue

        raise ValueError(f"Unsupported redaction type: {target.type}")

    redacted_rgb = cv2.cvtColor(bgr_array, cv2.COLOR_BGR2RGB)
    return Image.fromarray(redacted_rgb)
