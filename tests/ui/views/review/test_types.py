"""Smoke tests for the review page data contracts."""

from pathlib import Path

import pytest
from PIL import Image

from src.ai.types import BoundingBox, DetectedObject
from src.redactEngine.redactor import RedactionTarget, RedactionType
from src.ui.views.review.types import (
    ApprovedImageRedactions,
    LoadedImageDetections,
    ReviewPageInput,
    ReviewPageOutput,
)


def _img() -> Image.Image:
    return Image.new("RGB", (10, 10))


def test_loaded_image_detections_constructs() -> None:
    det = DetectedObject(
        label="face", bounding_box=BoundingBox(0, 0, 5, 5), confidence=0.9
    )
    lid = LoadedImageDetections(path=Path("a.jpg"), image=_img(), detections=[det])
    assert lid.path == Path("a.jpg")
    assert lid.detections == [det]


def test_loaded_image_detections_is_frozen() -> None:
    lid = LoadedImageDetections(path=Path("a.jpg"), image=_img(), detections=[])
    with pytest.raises((AttributeError, TypeError)):
        lid.path = Path("other.jpg")  # type: ignore[misc]


def test_review_page_input_constructs() -> None:
    inp = ReviewPageInput(failed_paths=[Path("bad.jpg")], loaded_images=[])
    assert inp.failed_paths == [Path("bad.jpg")]
    assert inp.loaded_images == []


def test_approved_image_redactions_constructs() -> None:
    target = RedactionTarget(
        location=BoundingBox(0, 0, 5, 5), redaction_type=RedactionType.BLACK_BAR
    )
    air = ApprovedImageRedactions(
        path=Path("a.jpg"), image=_img(), approved_targets=[target]
    )
    assert air.approved_targets[0].redaction_type == RedactionType.BLACK_BAR


def test_review_page_output_constructs() -> None:
    out = ReviewPageOutput(failed_paths=[], loaded_images=[])
    assert out.failed_paths == []
    assert out.loaded_images == []
