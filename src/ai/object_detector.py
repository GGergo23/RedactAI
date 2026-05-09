"""Object detection utilities for faces and license plates.

The module exposes a small, testable object-detection API that returns
axis-aligned bounding boxes plus labels and confidence scores.

It is designed around two pretrained YOLO-based models:
- YOLOv8-face for face detection
- YOLOv11 fine-tuned license plate detector

The real backends are loaded lazily from model files under assets/models/.
Tests can inject fake backends to validate the orchestration logic without
requiring model weights to be present.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Protocol

from PIL import Image

from src.ai.types import BoundingBox, DetectedObject
from src.persistance.resource_loader import ResourceLoader

FACE_MODEL_FILENAME = "yolov8n-face.pt"
LICENSE_PLATE_MODEL_FILENAME = "license-plate-finetune-v1n.pt"

FACE_MODEL_URL = (
    "https://github.com/akanametov/yolo-face/releases/download/1.0.0/yolov8n-face.pt"
)

LICENSE_PLATE_MODEL_URL = (
    "https://huggingface.co/morsetechlab/yolov11-license-plate-detection/"
    "resolve/main/license-plate-finetune-v1n.pt"
)

DEFAULT_MODELS_DIR = "assets/models"


class ModelLoadError(RuntimeError):
    """Raised when an object-detection model cannot be loaded."""


class ObjectDetectionBackend(Protocol):
    """Backend contract for object detection models."""

    def infer(self, image: Image.Image) -> list[DetectedObject]:
        """Infer detected objects from a single image."""


def _load_yolo_class() -> type[Any]:
    try:
        from ultralytics import YOLO
    except Exception as exc:  # pragma: no cover - wrapped failure path
        raise ModelLoadError(
            "Ultralytics is required for object-detection backends. "
            "Install dependencies and try again."
        ) from exc
    return YOLO


def _default_download_dir() -> Path:
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache_home:
        return Path(xdg_cache_home) / "redactai" / "models"
    return Path.home() / ".cache" / "redactai" / "models"


@dataclass(slots=True)
class ObjectDetector:
    """High-level orchestrator for face and license plate detection."""

    face_backend: ObjectDetectionBackend | None = None
    license_plate_backend: ObjectDetectionBackend | None = None
    face_model_path: Path | None = None
    license_plate_model_path: Path | None = None

    def _resolve_model_path(self, filename: str, configured: Path | None) -> Path:
        if configured is not None:
            return configured
        resource_path = ResourceLoader.get_resource_path(
            f"{DEFAULT_MODELS_DIR}/{filename}"
        )
        if resource_path.exists():
            return resource_path
        cached_path = _default_download_dir() / filename
        if cached_path.exists():
            return cached_path
        return resource_path

    def _ensure_backends(self) -> None:
        if self.face_backend is None:
            face_model_path = self._resolve_model_path(
                FACE_MODEL_FILENAME, self.face_model_path
            )
            if not face_model_path.exists():
                raise ModelLoadError(
                    f"Face model not found at {face_model_path}. "
                    "Download it or call download_default_models()."
                )
            self.face_backend = FaceYOLOv8Backend(face_model_path)

        if self.license_plate_backend is None:
            plate_model_path = self._resolve_model_path(
                LICENSE_PLATE_MODEL_FILENAME, self.license_plate_model_path
            )
            if not plate_model_path.exists():
                raise ModelLoadError(
                    f"License plate model not found at {plate_model_path}. "
                    "Download it or call download_default_models()."
                )
            self.license_plate_backend = LicensePlateYOLOv11Backend(plate_model_path)

    def detect(self, images: list[Image.Image]) -> list[list[DetectedObject]]:
        """Detect faces and license plates in a list of PIL images."""
        for image in images:
            if not isinstance(image, Image.Image):
                raise TypeError(f"Expected PIL.Image.Image, got {type(image).__name__}")

        self._ensure_backends()

        results: list[list[DetectedObject]] = []
        for image in images:
            image_detections: list[DetectedObject] = []
            if self.face_backend is not None:
                image_detections.extend(self.face_backend.infer(image))
            if self.license_plate_backend is not None:
                image_detections.extend(self.license_plate_backend.infer(image))

            image_detections.sort(
                key=lambda det: (
                    det.label,
                    det.bounding_box.y,
                    det.bounding_box.x,
                    -det.confidence,
                )
            )
            results.append(image_detections)
        return results


class FaceYOLOv8Backend:
    """YOLOv8-face backend for face detection."""

    def __init__(
        self,
        model_path: Path,
        confidence_threshold: float = 0.5,
    ) -> None:
        self._model_path = model_path
        self._confidence_threshold = confidence_threshold

        try:
            self._model = _load_yolo_class()(str(model_path))
        except Exception as exc:  # pragma: no cover - wrapped failure path
            raise ModelLoadError(
                f"Unable to load face model from {model_path}."
            ) from exc

    def infer(self, image: Image.Image) -> list[DetectedObject]:
        results = self._model.predict(
            image, conf=self._confidence_threshold, verbose=False
        )

        detections: list[DetectedObject] = []
        for result in results:
            if result.boxes is None or len(result.boxes) == 0:
                continue

            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                x, y = int(x1), int(y1)
                width = int(x2 - x1)
                height = int(y2 - y1)
                confidence = float(box.conf[0].cpu().numpy())

                detections.append(
                    DetectedObject(
                        label="face",
                        bounding_box=BoundingBox(x=x, y=y, width=width, height=height),
                        confidence=confidence,
                    )
                )
        return detections


class LicensePlateYOLOv11Backend:
    """YOLOv11-based backend for license plate detection."""

    def __init__(
        self,
        model_path: Path,
        confidence_threshold: float = 0.5,
    ) -> None:
        self._model_path = model_path
        self._confidence_threshold = confidence_threshold

        try:
            self._model = _load_yolo_class()(str(model_path))
        except Exception as exc:  # pragma: no cover - wrapped failure path
            raise ModelLoadError(
                f"Unable to load license plate model from {model_path}."
            ) from exc

    def infer(self, image: Image.Image) -> list[DetectedObject]:
        results = self._model.predict(
            image, conf=self._confidence_threshold, verbose=False
        )

        detections: list[DetectedObject] = []
        for result in results:
            if result.boxes is None or len(result.boxes) == 0:
                continue

            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                x, y = int(x1), int(y1)
                width = int(x2 - x1)
                height = int(y2 - y1)
                confidence = float(box.conf[0].cpu().numpy())

                detections.append(
                    DetectedObject(
                        label="license_plate",
                        bounding_box=BoundingBox(x=x, y=y, width=width, height=height),
                        confidence=confidence,
                    )
                )
        return detections


def default_model_paths() -> dict[str, Path]:
    """Return the default filesystem locations for the detector weights."""
    return {
        "face": ResourceLoader.get_resource_path(
            f"{DEFAULT_MODELS_DIR}/{FACE_MODEL_FILENAME}"
        ),
        "license_plate": ResourceLoader.get_resource_path(
            f"{DEFAULT_MODELS_DIR}/{LICENSE_PLATE_MODEL_FILENAME}"
        ),
    }


def download_default_models(destination_dir: Path | None = None) -> dict[str, Path]:
    """Ensure the model directory exists and download face + plate weights."""
    from urllib.request import urlretrieve

    model_dir = (
        destination_dir if destination_dir is not None else _default_download_dir()
    )
    model_dir.mkdir(parents=True, exist_ok=True)

    face_target = model_dir / FACE_MODEL_FILENAME
    plate_target = model_dir / LICENSE_PLATE_MODEL_FILENAME

    if not face_target.exists():
        urlretrieve(FACE_MODEL_URL, face_target)

    if not plate_target.exists():
        urlretrieve(LICENSE_PLATE_MODEL_URL, plate_target)

    return {
        FACE_MODEL_FILENAME: face_target,
        LICENSE_PLATE_MODEL_FILENAME: plate_target,
    }
