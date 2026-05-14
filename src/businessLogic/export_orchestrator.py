"""Export orchestration for approved redactions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from PIL import Image

from src.ai.types import BoundingBox
from src.persistance import save_image
from src.redactEngine import RedactionTarget, RedactionType, apply_redactions


class KPITrackerProtocol(Protocol):
    """Minimal KPI module contract used after successful exports."""

    def record_export(self, result: "ExportImageResult") -> None:
        """Record a successful image export."""


ImageSaver = Callable[[Image.Image, str | Path, str | None], Path]
RedactionApplier = Callable[[Image.Image, list[RedactionTarget]], Image.Image]


@dataclass(frozen=True, slots=True)
class ApprovedRedaction:
    """User-approved redaction rectangle and rendering mode."""

    x: int
    y: int
    width: int
    height: int
    mode: RedactionType | str = RedactionType.BLACK_BAR

    def to_target(self) -> RedactionTarget:
        """Convert the approved rectangle into a redaction engine target."""

        return RedactionTarget(
            location=BoundingBox(
                x=self.x,
                y=self.y,
                width=self.width,
                height=self.height,
            ),
            redaction_type=RedactionType(self.mode),
        )


@dataclass(frozen=True, slots=True)
class ExportCommand:
    """One image export request from the application layer."""

    image: Image.Image
    output_path: str | Path
    redactions: list[ApprovedRedaction]
    image_format: str | None = None


@dataclass(frozen=True, slots=True)
class ExportImageResult:
    """Per-image export outcome."""

    image_index: int
    success: bool
    output_path: Path | None = None
    redaction_count: int = 0
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ExportRunResult:
    """Aggregate export outcome for a batch."""

    total_images: int
    successful_images: int
    failed_images: int
    results: list[ExportImageResult]


class ExportOrchestrator:
    """Apply approved redactions, persist outputs, and trigger KPI tracking."""

    def __init__(
        self,
        redaction_applier: RedactionApplier = apply_redactions,
        image_saver: ImageSaver = save_image,
        kpi_tracker: KPITrackerProtocol | None = None,
    ) -> None:
        self._redaction_applier = redaction_applier
        self._image_saver = image_saver
        self._kpi_tracker = kpi_tracker

    def export(self, commands: list[ExportCommand]) -> ExportRunResult:
        """Export a batch of images and return per-image status."""

        results: list[ExportImageResult] = []
        for index, command in enumerate(commands):
            results.append(self._export_one(index, command))

        successful_images = sum(1 for result in results if result.success)
        return ExportRunResult(
            total_images=len(commands),
            successful_images=successful_images,
            failed_images=len(commands) - successful_images,
            results=results,
        )

    def _export_one(
        self,
        image_index: int,
        command: ExportCommand,
    ) -> ExportImageResult:
        try:
            self._validate_command(command)
            targets = [redaction.to_target() for redaction in command.redactions]
            redacted_image = self._redaction_applier(command.image, targets)
            requested_path = Path(command.output_path)
            output_path = self._image_saver(
                redacted_image,
                requested_path,
                command.image_format,
            )
            result = ExportImageResult(
                image_index=image_index,
                success=True,
                output_path=output_path,
                redaction_count=len(targets),
            )
            self._record_kpi(result)
            return result
        except Exception as exc:
            return ExportImageResult(
                image_index=image_index,
                success=False,
                output_path=_safe_output_path(command.output_path),
                redaction_count=len(command.redactions),
                error=str(exc),
            )

    def _record_kpi(self, result: ExportImageResult) -> None:
        if self._kpi_tracker is None:
            return
        self._kpi_tracker.record_export(result)

    def _validate_command(self, command: ExportCommand) -> None:
        if not isinstance(command.image, Image.Image):
            raise TypeError(
                f"Expected PIL.Image.Image, got {type(command.image).__name__}"
            )
        if not isinstance(command.output_path, (str, Path)):
            raise TypeError(
                "Expected str or pathlib.Path, "
                f"got {type(command.output_path).__name__}"
            )


def _safe_output_path(path: str | Path) -> Path | None:
    if not isinstance(path, (str, Path)):
        return None
    return Path(path)
