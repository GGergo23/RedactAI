"""Export orchestration for approved redactions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image

from src.ai.types import BoundingBox
from src.persistance import save_image, submit_analytics
from src.redactEngine import RedactionTarget, RedactionType, apply_redactions

ImageSaver = Callable[[Image.Image, str | Path, str | None], Path]
RedactionApplier = Callable[[Image.Image, list[RedactionTarget]], Image.Image]
AnalyticsSubmitter = Callable[[int, bool], bool]


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
    analytics_submitted: bool = False


class ExportOrchestrator:
    """Apply approved redactions, persist outputs, and trigger KPI tracking."""

    def __init__(
        self,
        redaction_applier: RedactionApplier = apply_redactions,
        image_saver: ImageSaver = save_image,
        analytics_submitter: AnalyticsSubmitter = submit_analytics,
        analytics_consent: bool = False,
    ) -> None:
        self._redaction_applier = redaction_applier
        self._image_saver = image_saver
        self._analytics_submitter = analytics_submitter
        self._analytics_consent = analytics_consent

    def export(self, commands: list[ExportCommand]) -> ExportRunResult:
        """Export a batch of images and return per-image status."""

        results: list[ExportImageResult] = []
        for index, command in enumerate(commands):
            results.append(self._export_one(index, command))

        successful_images = sum(1 for result in results if result.success)
        analytics_submitted = self._submit_export_analytics(results)
        return ExportRunResult(
            total_images=len(commands),
            successful_images=successful_images,
            failed_images=len(commands) - successful_images,
            results=results,
            analytics_submitted=analytics_submitted,
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
            return result
        except Exception as exc:
            return ExportImageResult(
                image_index=image_index,
                success=False,
                output_path=_safe_output_path(command.output_path),
                redaction_count=len(command.redactions),
                error=str(exc),
            )

    def _submit_export_analytics(self, results: list[ExportImageResult]) -> bool:
        successful_redactions = sum(
            result.redaction_count for result in results if result.success
        )
        try:
            return self._analytics_submitter(
                successful_redactions,
                self._analytics_consent,
            )
        except Exception:
            return False

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
