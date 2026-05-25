from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from src.ai.object_detector import ObjectDetector, default_model_paths
from src.ai.types import DetectedObject

SAMPLES_DIR = Path("tests/assets/images")


def _resolve_sample_image(*candidates: str) -> Path:
    for candidate in candidates:
        path = SAMPLES_DIR / candidate
        if path.exists():
            return path
    raise AssertionError(f"Missing sample image. Looked for: {candidates!r}")


def _load_detector() -> ObjectDetector:
    pytest.importorskip("ultralytics")

    model_paths = default_model_paths()
    missing = [name for name, path in model_paths.items() if not path.exists()]
    if missing:
        pytest.skip(
            "Object-detection model weights are not available locally; "
            "the workflow downloads them into assets/models before CI runs."
        )

    return ObjectDetector()


def _load_image(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.copy()


def _label_map(detections: list[DetectedObject]) -> dict[str, list[DetectedObject]]:
    grouped: dict[str, list[DetectedObject]] = {}
    for detection in detections:
        grouped.setdefault(detection.label, []).append(detection)
    return grouped


def _assert_center_close(
    detection: DetectedObject,
    expected_center_x: float,
    expected_center_y: float,
    tolerance_x: float,
    tolerance_y: float,
) -> None:
    center_x = detection.bounding_box.x + detection.bounding_box.width / 2
    center_y = detection.bounding_box.y + detection.bounding_box.height / 2

    assert abs(center_x - expected_center_x) <= tolerance_x
    assert abs(center_y - expected_center_y) <= tolerance_y


def _print_detections(image_name: str, detections: list[DetectedObject]) -> None:
    print(f"\n{image_name} detections:")
    if not detections:
        print("  (none)")
        return

    for detection in detections:
        box = detection.bounding_box
        print(
            "  "
            f"{detection.label} "
            f"conf={detection.confidence:.3f} "
            f"box=(x={box.x}, y={box.y}, w={box.width}, h={box.height})"
        )


def test_face_image_detects_face() -> None:
    detector = _load_detector()
    image_path = _resolve_sample_image("face.jpg")
    image = _load_image(image_path)

    results = detector.detect([image])
    detections = results[0]
    _print_detections(image_path.name, detections)

    grouped = _label_map(detections)
    face_detections = grouped.get("face", [])
    plate_detections = grouped.get("license_plate", [])

    assert len(face_detections) == 1
    assert len(plate_detections) == 0

    _assert_center_close(
        face_detections[0], 270.0, 115.0, tolerance_x=75, tolerance_y=75
    )


def test_plate_image_detects_license_plate() -> None:
    detector = _load_detector()
    image_path = _resolve_sample_image("plate.jpg")
    image = _load_image(image_path)

    results = detector.detect([image])
    detections = results[0]
    _print_detections(image_path.name, detections)

    grouped = _label_map(detections)
    face_detections = grouped.get("face", [])
    plate_detections = grouped.get("license_plate", [])

    assert len(face_detections) == 0
    assert len(plate_detections) == 1

    _assert_center_close(
        plate_detections[0], 690.0, 620.0, tolerance_x=100, tolerance_y=100
    )


def test_car_and_plate_image_detects_face_and_plate() -> None:
    detector = _load_detector()
    image_path = _resolve_sample_image("Car_and_plate.png")
    image = _load_image(image_path)

    results = detector.detect([image])
    detections = results[0]
    _print_detections(image_path.name, detections)

    grouped = _label_map(detections)
    face_detections = grouped.get("face", [])
    plate_detections = grouped.get("license_plate", [])

    assert len(face_detections) == 1
    assert len(plate_detections) == 1

    _assert_center_close(face_detections[0], 68.0, 68.0, tolerance_x=75, tolerance_y=75)
    _assert_center_close(
        plate_detections[0], 180.0, 194.0, tolerance_x=100, tolerance_y=100
    )
