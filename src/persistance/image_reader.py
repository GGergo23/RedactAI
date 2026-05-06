"""Image file reading utilities for RedactAI.

Provides a safe interface for loading image files from disk into
PIL.Image objects, with structured error handling for all failure
modes (missing file, unsupported format, corrupt data, permissions).
"""

from __future__ import annotations

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
    resolved = Path(path)

    if not resolved.exists():
        raise ImageReadError(
            f"File not found: {resolved}",
            path=resolved,
        )

    try:
        img = Image.open(resolved)
        img.load()  # force full decode — catches corrupt/truncated files
        return img
    except UnidentifiedImageError as exc:
        raise ImageReadError(
            f"Unsupported or unrecognised image format: {resolved}",
            path=resolved,
            cause=exc,
        ) from exc
    except OSError as exc:
        raise ImageReadError(
            f"Could not read image: {resolved} — {exc}",
            path=resolved,
            cause=exc,
        ) from exc
