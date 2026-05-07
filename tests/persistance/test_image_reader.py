"""Unit tests for src/persistance/image_reader.py.

Uses real temporary files via pytest's ``tmp_path`` fixture — no mocking.
All test scenarios from the T5.2 test matrix are covered here.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest
from PIL import Image

from src.persistance.image_reader import (
    ImageBatchReadResult,
    ImageReadError,
    read_image,
    read_images,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_image(
    tmp_path: Path,
    filename: str,
    mode: str = "RGB",
    size: tuple[int, int] = (10, 10),
) -> Path:
    """Save a minimal valid image to *tmp_path* and return its path."""
    p = tmp_path / filename
    Image.new(mode, size, color=0).save(p)
    return p


def _make_corrupt(tmp_path: Path, suffix: str = ".jpg") -> Path:
    """Create a file with garbage bytes but a valid image extension."""
    p = tmp_path / f"corrupt{suffix}"
    p.write_bytes(b"\x00\xff\xab\xcd" * 16)
    return p


def _make_empty(tmp_path: Path, suffix: str = ".png") -> Path:
    """Create a zero-byte file with a valid image extension."""
    p = tmp_path / f"empty{suffix}"
    p.write_bytes(b"")
    return p


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestHappyPath:
    """read_image returns a fully loaded Image for every supported format."""

    def test_reads_png(self, tmp_path: Path) -> None:
        p = _make_image(tmp_path, "img.png")
        result = read_image(p)
        assert isinstance(result, Image.Image)

    def test_reads_jpeg(self, tmp_path: Path) -> None:
        p = _make_image(tmp_path, "img.jpg")
        result = read_image(p)
        assert isinstance(result, Image.Image)

    def test_reads_bmp(self, tmp_path: Path) -> None:
        p = _make_image(tmp_path, "img.bmp")
        result = read_image(p)
        assert isinstance(result, Image.Image)

    def test_reads_tiff(self, tmp_path: Path) -> None:
        p = _make_image(tmp_path, "img.tiff")
        result = read_image(p)
        assert isinstance(result, Image.Image)

    def test_reads_webp(self, tmp_path: Path) -> None:
        p = _make_image(tmp_path, "img.webp")
        result = read_image(p)
        assert isinstance(result, Image.Image)

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        p = _make_image(tmp_path, "img.png")
        result = read_image(str(p))  # pass as str, not Path
        assert isinstance(result, Image.Image)

    def test_preserves_dimensions(self, tmp_path: Path) -> None:
        p = _make_image(tmp_path, "img.png", size=(200, 300))
        result = read_image(p)
        assert result.size == (200, 300)

    def test_preserves_mode_rgb(self, tmp_path: Path) -> None:
        p = _make_image(tmp_path, "img.png", mode="RGB")
        result = read_image(p)
        assert result.mode == "RGB"

    def test_preserves_mode_rgba(self, tmp_path: Path) -> None:
        p = _make_image(tmp_path, "img.png", mode="RGBA")
        result = read_image(p)
        assert result.mode == "RGBA"

    def test_image_pixels_loaded(self, tmp_path: Path) -> None:
        """Returned image must have pixels fully in memory (not lazy)."""
        p = _make_image(tmp_path, "img.png")
        result = read_image(p)
        p.unlink()
        data = result.tobytes()
        assert len(data) > 0

    def test_wrapper_reads_multiple_paths(self, tmp_path: Path) -> None:
        p1 = _make_image(tmp_path, "a.png")
        p2 = _make_image(tmp_path, "b.jpg")
        result = read_images([p1, str(p2)])
        assert isinstance(result, ImageBatchReadResult)
        assert result.failed_paths == []
        assert [path for path, _ in result.loaded_images] == [p1, p2]
        assert all(isinstance(img, Image.Image) for _, img in result.loaded_images)


# ---------------------------------------------------------------------------
# Error-path tests
# ---------------------------------------------------------------------------


class TestErrorCases:
    """read_image raises ImageReadError for every failure mode."""

    def test_nonexistent_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ImageReadError):
            read_image(tmp_path / "ghost.png")

    def test_nonexistent_sets_path_attr(self, tmp_path: Path) -> None:
        missing = tmp_path / "ghost.png"
        with pytest.raises(ImageReadError) as exc_info:
            read_image(missing)
        assert exc_info.value.path == missing

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        p = _make_empty(tmp_path, suffix=".png")
        with pytest.raises(ImageReadError):
            read_image(p)

    def test_corrupt_file_raises(self, tmp_path: Path) -> None:
        p = _make_corrupt(tmp_path, suffix=".jpg")
        with pytest.raises(ImageReadError):
            read_image(p)

    def test_unsupported_format_raises(self, tmp_path: Path) -> None:
        """A text file renamed to .pdf must raise ImageReadError."""
        p = tmp_path / "document.pdf"
        p.write_text("not an image at all")
        with pytest.raises(ImageReadError):
            read_image(p)

    def test_error_exposes_path(self, tmp_path: Path) -> None:
        p = tmp_path / "ghost.png"
        with pytest.raises(ImageReadError) as exc_info:
            read_image(p)
        assert exc_info.value.path == p

    def test_corrupt_error_wraps_cause(self, tmp_path: Path) -> None:
        p = _make_corrupt(tmp_path, suffix=".jpg")
        with pytest.raises(ImageReadError) as exc_info:
            read_image(p)
        assert exc_info.value.cause is not None

    def test_empty_file_error_wraps_cause(self, tmp_path: Path) -> None:
        p = _make_empty(tmp_path, suffix=".png")
        with pytest.raises(ImageReadError) as exc_info:
            read_image(p)
        assert exc_info.value.cause is not None

    def test_nonexistent_error_wraps_file_not_found(self, tmp_path: Path) -> None:
        """Missing-file errors are wrapped with the source cause."""
        p = tmp_path / "ghost.png"
        with pytest.raises(ImageReadError) as exc_info:
            read_image(p)
        assert isinstance(exc_info.value.cause, FileNotFoundError)

    def test_error_message_contains_path(self, tmp_path: Path) -> None:
        p = tmp_path / "ghost.png"
        with pytest.raises(ImageReadError) as exc_info:
            read_image(p)
        assert str(p) in str(exc_info.value)

    def test_wrapper_collects_failed_paths(self, tmp_path: Path) -> None:
        ok = _make_image(tmp_path, "ok.png")
        missing = tmp_path / "missing.png"
        result = read_images([ok, missing])
        assert result.failed_paths == [missing]
        assert [path for path, _ in result.loaded_images] == [ok]

    @pytest.mark.skipif(
        os.name == "nt",
        reason="chmod-based permission test is POSIX-only",
    )
    def test_permission_denied_raises(self, tmp_path: Path) -> None:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            pytest.skip("permission-denied semantics are unreliable as root")

        p = _make_image(tmp_path, "no_read.png")
        p.chmod(0)
        try:
            with pytest.raises(ImageReadError) as exc_info:
                read_image(p)
            assert isinstance(exc_info.value.cause, PermissionError)
            assert "permission denied" in str(exc_info.value).lower()
        finally:
            p.chmod(stat.S_IRUSR | stat.S_IWUSR)
