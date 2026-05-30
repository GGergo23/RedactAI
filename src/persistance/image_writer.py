"""Image export utilities for RedactAI."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


class ImageWriteError(Exception):
    """Raised when an image cannot be written to disk."""

    def __init__(
        self,
        message: str,
        path: Path,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.path = path
        self.cause = cause


def save_image(
    image: Image.Image,
    path: str | Path,
    image_format: str | None = None,
) -> Path:
    """Save a PIL image to disk and return the written path."""

    if not isinstance(image, Image.Image):
        raise TypeError(f"Expected PIL.Image.Image, got {type(image).__name__}")

    output_path = Path(path)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format=image_format)
    except OSError as exc:
        raise ImageWriteError(
            f"Could not write image: {output_path} - {exc}",
            path=output_path,
            cause=exc,
        ) from exc
    except ValueError as exc:
        raise ImageWriteError(
            f"Unsupported image export format for {output_path}: {exc}",
            path=output_path,
            cause=exc,
        ) from exc

    return output_path
