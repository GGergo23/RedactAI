"""Image file reading utilities for RedactAI.

Provides a safe interface for loading image files from disk into
PIL.Image objects, with structured error handling for all failure
modes (missing file, unsupported format, corrupt data, permissions).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError


class ImageReadError(Exception):
    """Raised when an image cannot be read from disk.

    Wraps the underlying OS / Pillow error so callers never need to
    catch raw ``IOError``, ``FileNotFoundError``, or
    ``PIL.UnidentifiedImageError`` directly.

    Attributes:
        path: The path that was attempted.
        cause: The original exception, if any.
    """

    def __init__(
        self,
        message: str,
        path: Path,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.path = path
        self.cause = cause


@dataclass(frozen=True, slots=True)
class ImageBatchReadResult:
    """Structured result of reading a batch of image paths."""

    failed_paths: list[Path]
    loaded_images: list[tuple[Path, Image.Image]]


def read_image(path: str | Path) -> Image.Image:
    """Load an image from disk into a PIL Image object.

    The returned image is fully decoded (pixels materialised in
    memory) before this function returns, so callers can safely
    close the source file and work with the image immediately.

    Args:
        path: Absolute or relative path to the image file.
              Supported formats: PNG, JPEG, BMP, TIFF, WebP.

    Returns:
        A ``PIL.Image.Image`` loaded in its native colour mode.
        The caller is responsible for converting the mode if needed.

    Raises:
        ImageReadError: If the file does not exist, is not a
            supported image format, is corrupt or empty, or cannot
            be read due to a permission error.
    """
    image_path = Path(path)

    try:
        img = Image.open(image_path)
        img.load()  # force full decode — catches corrupt/truncated files
        return img
    except FileNotFoundError as exc:
        raise ImageReadError(
            f"File not found: {image_path}",
            path=image_path,
            cause=exc,
        ) from exc
    except PermissionError as exc:
        raise ImageReadError(
            f"Permission denied while reading image: {image_path}",
            path=image_path,
            cause=exc,
        ) from exc
    except UnidentifiedImageError as exc:
        raise ImageReadError(
            f"Unsupported or unrecognised image format: {image_path}",
            path=image_path,
            cause=exc,
        ) from exc
    except OSError as exc:
        raise ImageReadError(
            f"Could not read image: {image_path} — {exc}",
            path=image_path,
            cause=exc,
        ) from exc


def read_images(paths: list[str | Path]) -> ImageBatchReadResult:
    """Read multiple images and return loaded images plus failures."""
    failed_paths: list[Path] = []
    loaded_images: list[tuple[Path, Image.Image]] = []

    for path in paths:
        image_path = Path(path)
        try:
            image = read_image(image_path)
        except ImageReadError:
            failed_paths.append(image_path)
            continue
        loaded_images.append((image_path, image))

    return ImageBatchReadResult(
        failed_paths=failed_paths,
        loaded_images=loaded_images,
    )
