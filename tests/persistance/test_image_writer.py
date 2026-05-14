"""Tests for image export persistence."""

from __future__ import annotations

from PIL import Image

from src.persistance.image_writer import ImageWriteError, save_image


def test_save_image_writes_file_and_creates_parent_directory(tmp_path) -> None:
    image = Image.new("RGB", (8, 8), color=(255, 0, 0))
    output_path = tmp_path / "nested" / "redacted.png"

    written_path = save_image(image, output_path)

    assert written_path == output_path
    assert output_path.exists()


def test_save_image_rejects_non_image(tmp_path) -> None:
    output_path = tmp_path / "redacted.png"

    try:
        save_image("not-an-image", output_path)
    except TypeError as exc:
        assert "Expected PIL.Image.Image" in str(exc)
    else:  # pragma: no cover - defensive assertion branch
        raise AssertionError("Expected TypeError")


def test_save_image_wraps_unsupported_format_error(tmp_path) -> None:
    image = Image.new("RGB", (8, 8))
    output_path = tmp_path / "redacted.invalid"

    try:
        save_image(image, output_path)
    except ImageWriteError as exc:
        assert exc.path == output_path
        assert exc.cause is not None
    else:  # pragma: no cover - defensive assertion branch
        raise AssertionError("Expected ImageWriteError")
