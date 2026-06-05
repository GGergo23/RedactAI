"""Tests for ExportPageView's orchestrator integration."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from PyQt6.QtWidgets import QApplication

from src.ai.types import BoundingBox
from src.businessLogic.export_orchestrator import (
    ExportCommand,
    ExportImageResult,
    ExportProgress,
    ExportRunResult,
)
from src.persistance.config_manager import ConfigManager
from src.redactEngine.redactor import RedactionTarget, RedactionType
from src.ui.views.export_page import ExportPageView, _build_export_commands
from src.ui.views.review.types import ApprovedImageRedactions, ReviewPageOutput


@pytest.fixture(scope="module")
def qt_app():
    # "-platform offscreen" lets the fixture work in headless CI (no X server)
    # without requiring xvfb. setdefault avoids overriding if another fixture
    # already constructed a QApplication.
    app = QApplication.instance() or QApplication(["", "-platform", "offscreen"])
    yield app


def _image() -> Image.Image:
    return Image.new("RGB", (20, 20), color=(255, 255, 255))


def _approved(path: Path, *targets: RedactionTarget) -> ApprovedImageRedactions:
    return ApprovedImageRedactions(
        path=path,
        image=_image(),
        approved_targets=list(targets),
    )


def _target(x: int, y: int, w: int, h: int, mode: RedactionType) -> RedactionTarget:
    return RedactionTarget(
        location=BoundingBox(x=x, y=y, width=w, height=h),
        redaction_type=mode,
    )


class _FakeOrchestrator:
    """Records commands and exposes callbacks for the test to flush manually.

    Real callbacks fire from a worker thread *after* start_export returns and
    the page stores the task handle. Firing them synchronously here would race
    that assignment and the page would treat them as late no-ops.
    """

    def __init__(self, run_result: ExportRunResult) -> None:
        self._run_result = run_result
        self.commands: list[ExportCommand] = []
        self.cancelled = False
        self._result_callback = None
        self._progress_callback = None

    def start_export(
        self,
        commands,
        result_callback=None,
        progress_callback=None,
    ):
        self.commands = list(commands)
        self._result_callback = result_callback
        self._progress_callback = progress_callback
        return _StubTask(self)

    def flush(self) -> None:
        if self._progress_callback is not None:
            total = len(self.commands)
            for index, command in enumerate(self.commands):
                self._progress_callback(
                    ExportProgress(
                        total_images=total,
                        completed_images=index + 1,
                        current_image_index=index,
                        current_output_path=Path(command.output_path),
                        success=True,
                    )
                )
        if self._result_callback is not None:
            self._result_callback(self._run_result)


class _StubTask:
    def __init__(self, orchestrator: _FakeOrchestrator) -> None:
        self._orchestrator = orchestrator
        self.done = True

    def cancel(self) -> None:
        self._orchestrator.cancelled = True


def test_build_export_commands_uses_default_save_directory_with_suffix() -> None:
    review_output = ReviewPageOutput(
        failed_paths=[],
        loaded_images=[
            _approved(Path("/inbox/photo.jpg")),
            _approved(Path("/inbox/scan.PNG")),
        ],
    )

    commands = _build_export_commands(review_output)

    save_dir = ConfigManager.get_default_save_directory()
    assert [c.output_path for c in commands] == [
        save_dir / "photo_redacted.jpg",
        save_dir / "scan_redacted.PNG",
    ]


def test_build_export_commands_converts_redaction_targets() -> None:
    target = _target(4, 5, 6, 7, RedactionType.PIXELATE)
    review_output = ReviewPageOutput(
        failed_paths=[],
        loaded_images=[_approved(Path("/inbox/a.png"), target)],
    )

    commands = _build_export_commands(review_output)

    assert len(commands) == 1
    [redaction] = commands[0].redactions
    assert (redaction.x, redaction.y) == (4, 5)
    assert (redaction.width, redaction.height) == (6, 7)
    assert redaction.mode == RedactionType.PIXELATE


def test_export_page_invokes_orchestrator_and_summarizes_result(qt_app) -> None:
    run_result = ExportRunResult(
        total_images=2,
        successful_images=2,
        failed_images=0,
        results=[
            ExportImageResult(image_index=0, success=True, redaction_count=1),
            ExportImageResult(image_index=1, success=True, redaction_count=0),
        ],
    )
    orchestrator = _FakeOrchestrator(run_result)

    def transition(*_args, **_kwargs):
        return None

    page = ExportPageView(transition, orchestrator)  # type: ignore[arg-type]
    page.setLaunchExtra(
        output=ReviewPageOutput(
            failed_paths=[],
            loaded_images=[
                _approved(
                    Path("/inbox/a.png"), _target(1, 2, 3, 4, RedactionType.BLACK_BAR)
                ),
                _approved(Path("/inbox/b.png")),
            ],
        )
    )

    page.start_export_process()
    orchestrator.flush()
    qt_app.processEvents()

    assert len(orchestrator.commands) == 2
    save_dir = ConfigManager.get_default_save_directory()
    assert orchestrator.commands[0].output_path == save_dir / "a_redacted.png"
    assert orchestrator.commands[1].output_path == save_dir / "b_redacted.png"

    text = page.description.text()
    assert "2 of 2" in text
    assert page.main_button.text() == "Go back to Home"
    assert page.is_done is True


def test_export_page_cancel_invokes_orchestrator_and_drops_task(qt_app) -> None:
    transitions: list[object] = []

    def transition(page, **_kwargs):
        transitions.append(page)

    run_result = ExportRunResult(
        total_images=1,
        successful_images=0,
        failed_images=1,
        results=[],
        cancelled=True,
    )
    orchestrator = _FakeOrchestrator(run_result)
    page = ExportPageView(transition, orchestrator)  # type: ignore[arg-type]
    page.setLaunchExtra(
        output=ReviewPageOutput(
            failed_paths=[],
            loaded_images=[_approved(Path("/inbox/a.png"))],
        )
    )

    page.start_export_process()
    qt_app.processEvents()
    # Pretend the export is still running so cancel takes the cancel branch.
    in_flight = _StubTask(orchestrator)
    in_flight.done = False
    page._task = in_flight

    page._cancel_export()

    assert orchestrator.cancelled is True
    assert transitions  # navigated home
    assert page._task is None
