"""Tests for the assemble_output free function."""

from pathlib import Path

from PIL import Image

from src.ai.types import BoundingBox, DetectedObject
from src.redactEngine.redactor import RedactionType
from src.ui.views.review.review_page import assemble_output
from src.ui.views.review.types import LoadedImageDetections, ReviewPageInput


def _img() -> Image.Image:
    return Image.new("RGB", (100, 100))


def _det(x: int, y: int, w: int, h: int) -> DetectedObject:
    return DetectedObject(
        label="face", bounding_box=BoundingBox(x, y, w, h), confidence=0.9
    )


def _input(*det_lists: list[DetectedObject]) -> ReviewPageInput:
    images = [
        LoadedImageDetections(
            path=Path(f"img{i}.jpg"),
            image=_img(),
            detections=list(dets),
        )
        for i, dets in enumerate(det_lists)
    ]
    return ReviewPageInput(failed_paths=[], loaded_images=images)


def test_all_ai_accepted_no_manual() -> None:
    det = _det(0, 0, 10, 10)
    result = assemble_output(_input([det]), {}, {})
    targets = result.loaded_images[0].approved_targets
    assert len(targets) == 1
    assert targets[0].location == det.bounding_box
    assert targets[0].redaction_type == RedactionType.BLACK_BAR


def test_all_ai_rejected() -> None:
    result = assemble_output(_input([_det(0, 0, 10, 10)]), {0: [False]}, {})
    assert result.loaded_images[0].approved_targets == []


def test_mix_accepted_rejected_ai_plus_manual() -> None:
    det1 = _det(0, 0, 10, 10)
    det2 = _det(20, 20, 5, 5)
    manual_bb = BoundingBox(50, 50, 20, 20)
    discarded_bb = BoundingBox(1, 1, 1, 1)

    result = assemble_output(
        _input([det1, det2]),
        {0: [True, False]},
        {0: [(manual_bb, True), (discarded_bb, False)]},
    )
    targets = result.loaded_images[0].approved_targets
    # det1 accepted + manual_bb accepted; det2 rejected + discarded_bb rejected
    assert len(targets) == 2
    assert targets[0].location == det1.bounding_box
    assert targets[1].location == manual_bb


def test_unvisited_image_defaults_all_accepted() -> None:
    det = _det(5, 5, 10, 10)
    # Empty ai_state and manual_state — image was never visited
    result = assemble_output(_input([det]), {}, {})
    assert len(result.loaded_images[0].approved_targets) == 1


def test_empty_loaded_images() -> None:
    inp = ReviewPageInput(failed_paths=[], loaded_images=[])
    result = assemble_output(inp, {}, {})
    assert result.loaded_images == []
    assert result.failed_paths == []


def test_failed_paths_passed_through() -> None:
    inp = ReviewPageInput(failed_paths=[Path("bad.jpg")], loaded_images=[])
    result = assemble_output(inp, {}, {})
    assert result.failed_paths == [Path("bad.jpg")]


def test_multiple_images_independent() -> None:
    det_a = _det(0, 0, 10, 10)
    det_b = _det(5, 5, 8, 8)
    result = assemble_output(
        _input([det_a], [det_b]),
        {0: [False], 1: [True]},
        {},
    )
    assert result.loaded_images[0].approved_targets == []
    assert len(result.loaded_images[1].approved_targets) == 1
