"""Tests for the object detection module."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from src.ai.object_detector import (
    FACE_MODEL_FILENAME,
    LICENSE_PLATE_MODEL_FILENAME,
    ObjectDetector,
    default_model_paths,
    download_default_models,
)
from src.ai.types import BoundingBox, DetectedObject


class _FakeBackend:
    def __init__(self, detections: list[DetectedObject]) -> None:
        self._detections = detections
        self.calls = 0

    def infer(self, image: Image.Image) -> list[DetectedObject]:
        self.calls += 1
        return list(self._detections)


def _make_object(label: str, x: int, y: int, width: int, height: int, confidence: float) -> DetectedObject:
    return DetectedObject(
        label=label,
        bounding_box=BoundingBox(x=x, y=y, width=width, height=height),
        confidence=confidence,
    )


def test_detect_merges_face_and_plate_backends() -> None:
    image = Image.new("RGB", (128, 128), color="white")
    face_backend = _FakeBackend([_make_object("face", 10, 12, 20, 22, 0.98)])
    plate_backend = _FakeBackend([
        _make_object("license_plate", 48, 64, 30, 12, 0.91)
    ])

    detector = ObjectDetector(
        face_backend=face_backend,
        license_plate_backend=plate_backend,
    )

    detections = detector.detect([image])

    assert len(detections) == 1
    assert detections[0] == [
        _make_object("face", 10, 12, 20, 22, 0.98),
        _make_object("license_plate", 48, 64, 30, 12, 0.91),
    ]
    assert face_backend.calls == 1
    assert plate_backend.calls == 1


def test_detect_rejects_non_images() -> None:
    detector = ObjectDetector(
        face_backend=_FakeBackend([]),
        license_plate_backend=_FakeBackend([]),
    )

    with pytest.raises(TypeError, match="PIL.Image.Image"):
        detector.detect(["not-an-image"])  # type: ignore[list-item]


def test_default_model_paths_point_under_assets_models() -> None:
    paths = default_model_paths()

    assert paths["face"].as_posix().endswith(FACE_MODEL_FILENAME)
    assert paths["license_plate"].as_posix().endswith(LICENSE_PLATE_MODEL_FILENAME)
    assert "assets/models" in paths["face"].as_posix()
    assert "assets/models" in paths["license_plate"].as_posix()


def test_download_default_models_uses_target_directory(monkeypatch, tmp_path) -> None:
    calls: list[tuple[str, Path]] = []

    def fake_urlretrieve(url: str, filename: str | Path):
        target_path = Path(filename)
        target_path.write_text(url, encoding="utf-8")
        calls.append((url, target_path))
        return str(target_path), None

    monkeypatch.setattr("urllib.request.urlretrieve", fake_urlretrieve)

    downloaded = download_default_models(tmp_path)

    assert downloaded[FACE_MODEL_FILENAME] == tmp_path / FACE_MODEL_FILENAME
    assert downloaded[FACE_MODEL_FILENAME].exists()
    assert downloaded[FACE_MODEL_FILENAME].read_text(encoding="utf-8")
    assert downloaded[LICENSE_PLATE_MODEL_FILENAME].exists()
    assert downloaded[LICENSE_PLATE_MODEL_FILENAME].read_text(encoding="utf-8")
    assert len(calls) == 2
