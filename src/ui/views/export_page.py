"""Export view that drives the real ExportOrchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.businessLogic.export_orchestrator import (
    ApprovedRedaction,
    ExportCommand,
    ExportOrchestrator,
    ExportProgress,
    ExportRunResult,
    ExportTask,
)
from src.persistance.config_manager import ConfigManager
from src.ui.views.review.types import ApprovedImageRedactions, ReviewPageOutput


class ExportPageView(QWidget):
    """Export view that runs the real export pipeline asynchronously."""

    # Export orchestrator callbacks fire from a worker thread; these signals
    # marshal the payload back onto the GUI thread before touching widgets.
    _progress_signal = pyqtSignal(object)
    _result_signal = pyqtSignal(object)

    def __init__(
        self,
        transition_page_fn: Callable,
        orchestrator: ExportOrchestrator,
    ) -> None:
        """
        Initialize the export view.

        Args:
            transition_page_fn: Function to transition to another page.
            orchestrator: Shared export orchestrator used to run export jobs.
        """
        super().__init__()
        self.transition_page_fn = transition_page_fn
        self._orchestrator = orchestrator
        self.launch_extra: dict[str, object] = {}
        self.is_done = False
        self._task: ExportTask | None = None
        self._setup_ui()

        self._progress_signal.connect(self._on_progress)
        self._result_signal.connect(self._on_complete)

    def setLaunchExtra(self, **kwargs: object) -> None:
        """Set extra launch parameters for this page.

        Args:
            **kwargs: Additional parameters passed from navigation.
        """
        self.launch_extra = kwargs

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        title = QLabel("Exporting step")
        title.setProperty("role", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.description = QLabel(
            "All redaction targets have been approved. "
            "Click the button below to start exporting."
        )
        self.description.setProperty("role", "subtitle")
        self.description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description.setWordWrap(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)

        self.progress_percentage_label = QLabel("0%")
        self.progress_percentage_label.setProperty("role", "body")
        self.progress_percentage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.main_button = QPushButton("Start Export")
        self.main_button.setProperty("role", "primary")
        self.main_button.setMinimumWidth(220)
        self.main_button.clicked.connect(self.main_button_clicked)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(self.description)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_percentage_label)
        layout.addStretch()
        layout.addWidget(self.main_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

    def main_button_clicked(self) -> None:
        """Dispatch the button click based on the current state."""
        if self.is_done:
            self._go_home()
            return

        if self._task is not None and not self._task.done:
            self._cancel_export()
            return

        self.start_export_process()

    def start_export_process(self) -> None:
        """Start the export process by invoking the orchestrator."""
        review_page_output: ReviewPageOutput | None = self.launch_extra.get(
            "output", None
        )
        if review_page_output is None:
            # This should never happen, but handle it gracefully just in case
            self.description.setText(
                "Error: Missing review output. Please return "
                "to the home page and try again."
            )
            self.main_button.setText("Go back to Home")
            self.main_button.setEnabled(True)
            self.is_done = True
            return

        commands = _build_export_commands(review_page_output)
        if not commands:
            self.description.setText("Nothing to export. Returning to the home page.")
            self.main_button.setText("Go back to Home")
            self.is_done = True
            return

        self._set_progress(0)
        self.description.setText(f"Exporting 0 of {len(commands)} images...")
        self.main_button.setText("Cancel")

        self._task = self._orchestrator.start_export(
            commands,
            result_callback=self._result_signal.emit,
            progress_callback=self._progress_signal.emit,
        )

    def _cancel_export(self) -> None:
        """Cancel the running export and return to the homepage."""
        task = self._task
        if task is None:
            return

        self.main_button.setEnabled(False)
        self.description.setText("Cancelling...")
        task.cancel()
        # Drop the handle so late progress/result callbacks become no-ops.
        self._task = None
        self._go_home()

    def _on_progress(self, event: ExportProgress) -> None:
        """Handle a progress event marshalled from the export worker."""
        if self._task is None:
            return  # cancelled and navigated away — drop late callbacks
        if event.total_images > 0:
            pct = int(event.completed_images / event.total_images * 100)
        else:
            pct = 0
        self._set_progress(pct)
        self.description.setText(
            f"Exporting image {event.completed_images} of {event.total_images}..."
        )

    def _on_complete(self, result: ExportRunResult) -> None:
        """Handle export completion and surface a summary."""
        if self._task is None or result.cancelled:
            return  # cancelled job — UI already returned home

        self._set_progress(100)
        self.description.setText(_summary_text(result))
        self.main_button.setText("Go back to Home")
        self.main_button.setEnabled(True)
        self.is_done = True
        self._task = None

    def on_page_become_current(self) -> None:
        """Reset the page to its idle state on activation."""
        self._task = None
        self.is_done = False
        self.main_button.setEnabled(True)
        self.main_button.setText("Start Export")
        self.description.setText(
            "All redaction targets have been approved. "
            "Click the button below to start exporting."
        )
        self._set_progress(0)

    def _set_progress(self, percent: int) -> None:
        self.progress_bar.setValue(percent)
        self.progress_percentage_label.setText(f"{percent}%")

    def _go_home(self) -> None:
        # Import here to avoid circular dependency.
        from src.ui.main_window import Page

        self.transition_page_fn(Page.HOME)


def _build_export_commands(
    review_output: ReviewPageOutput,
) -> list[ExportCommand]:
    """Convert review-page output into orchestrator export commands."""
    output_dir = ConfigManager.get_default_save_directory()
    return [
        _command_for_image(image, output_dir) for image in review_output.loaded_images
    ]


def _command_for_image(
    image_record: ApprovedImageRedactions,
    output_dir: Path,
) -> ExportCommand:
    output_path = output_dir / (
        f"{image_record.path.stem}_redacted{image_record.path.suffix}"
    )
    redactions = [
        ApprovedRedaction(
            x=target.location.x,
            y=target.location.y,
            width=target.location.width,
            height=target.location.height,
            mode=target.redaction_type,
        )
        for target in image_record.approved_targets
    ]
    return ExportCommand(
        image=image_record.image,
        output_path=output_path,
        redactions=redactions,
    )


def _summary_text(result: ExportRunResult) -> str:
    """Build the post-export description text."""
    parts = [
        f"Export complete: {result.successful_images} of "
        f"{result.total_images} images exported."
    ]
    if result.failed_images:
        parts.append(f"{result.failed_images} failed.")
    if result.successful_images:
        output_dir = ConfigManager.get_default_save_directory()
        parts.append(f"Saved to {output_dir}.")
    return " ".join(parts)
