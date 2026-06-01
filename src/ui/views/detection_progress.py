"""Detection progress view showing pipeline execution status."""

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

from src.ai.types import DetectedObject
from src.businessLogic.pipeline_controller import PipelineController, PipelineTask
from src.businessLogic.pipeline_types import (
    PipelineProgress,
    PipelineRunResult,
    PipelineStage,
)
from src.persistance.image_reader import read_images
from src.ui.views.review.types import LoadedImageDetections, ReviewPageInput

_STAGE_TEXT: dict[PipelineStage, str] = {
    PipelineStage.QUEUED: "Queued",
    PipelineStage.STARTED: "Starting",
    PipelineStage.IMAGE_LOADED: "Image loaded",
    PipelineStage.OCR_COMPLETED: "OCR complete",
    PipelineStage.NLP_COMPLETED: "Text analysis complete",
    PipelineStage.OBJECT_DETECTION_COMPLETED: "Object detection complete",
    PipelineStage.DETECTIONS_READY: "Finalizing",
    PipelineStage.COMPLETED: "Image complete",
    PipelineStage.CANCELLED: "Cancelled",
    PipelineStage.SKIPPED: "Skipped",
    PipelineStage.FAILED: "Failed",
}


class DetectionProgressView(QWidget):
    """View displaying the progress of the detection pipeline."""

    # Pipeline callbacks fire from a worker thread; these signals marshal
    # the payload back onto the GUI thread before touching widgets.
    _progress_signal = pyqtSignal(object)
    _result_signal = pyqtSignal(object)

    def __init__(
        self,
        transition_page_fn: Callable,
        pipeline: PipelineController,
    ) -> None:
        """
        Initialize the detection progress view.

        Args:
            transition_page_fn: Function for transitioning to other pages.
            pipeline: Shared pipeline controller used to run detection jobs.
        """
        super().__init__()
        self.transition_page_fn = transition_page_fn
        self._pipeline = pipeline
        self.files: list[str] = []
        self.current_progress = 0
        self._task: PipelineTask | None = None
        self._setup_ui()

        self._progress_signal.connect(self._on_progress)
        self._result_signal.connect(self._on_complete)

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # Title
        title = QLabel("Processing Images")
        title.setProperty("role", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Status text
        self.status_label = QLabel("Initializing detection pipeline...")
        self.status_label.setProperty("role", "body")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(self.current_progress)
        self.progress_bar.setTextVisible(False)  # use custom label for percentage

        # Progress percentage label
        self.progress_percentage_label = QLabel(f"{self.current_progress}%")
        self.progress_percentage_label.setProperty("role", "body")
        self.progress_percentage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Bottom action
        self.cancel_button = QPushButton("Cancel and Return to Home")
        self.cancel_button.setProperty("role", "primary")
        self.cancel_button.setMinimumWidth(240)
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)

        # Add components to layout
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_percentage_label)
        layout.addWidget(self.cancel_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

    def setLaunchExtra(self, **kwargs: object) -> None:
        """Set extra launch parameters for this page.

        Args:
            **kwargs: Additional parameters passed from navigation.
                Expected: files (list[str]) - paths to files to process.
        """
        if "files" in kwargs:
            self.files = kwargs["files"]

    def on_page_become_current(self) -> None:
        """Start the detection process when this page becomes active."""
        self.start_detection()

    def start_detection(self) -> None:
        """Submit the current files to the pipeline and update UI state."""
        if self._task is not None and not self._task.done:
            return  # Prevent starting multiple tasks

        self.on_progress_update(0)
        self.status_label.setText("Starting detection pipeline...")

        self._task = self._pipeline.start_detection(
            image_paths=list(self.files),
            progress_callback=self._progress_signal.emit,
            result_callback=self._result_signal.emit,
        )
        self.cancel_button.setEnabled(True)

    def on_progress_update(self, progress: int) -> None:
        """Update the progress bar and percentage label."""
        self.current_progress = progress
        self.progress_bar.setValue(self.current_progress)
        self.progress_percentage_label.setText(f"{self.current_progress}%")

    def _on_progress(self, event: PipelineProgress) -> None:
        """Handle a progress event marshalled from the pipeline worker."""
        if self._task is None:
            return  # cancelled and navigated away — drop late callbacks
        if event.total_images > 0:
            pct = int(event.completed_images / event.total_images * 100)
        else:
            pct = 0
        self.on_progress_update(pct)
        label = _STAGE_TEXT.get(event.stage, "Processing")
        current_index = min(event.completed_images + 1, event.total_images)
        self.status_label.setText(
            f"{label} — image {current_index} of {event.total_images}"
        )

    def _on_complete(self, result: PipelineRunResult) -> None:
        """Handle pipeline completion and transition to the review page."""
        if self._task is None or result.cancelled:
            return  # cancelled job — UI already returned home

        self.status_label.setText("Detection complete!")
        self.cancel_button.setEnabled(False)
        self.on_progress_update(100)

        review_input = self._build_review_input(result)
        self._task = None

        # Import here to avoid circular dependency
        from src.ui.main_window import Page

        self.transition_page_fn(Page.REVIEW, input=review_input)

    def _build_review_input(self, result: PipelineRunResult) -> ReviewPageInput:
        """Convert a pipeline run result into the review page's input format."""
        successful = [r for r in result.results if r.success]
        pipeline_failed_paths = [
            Path(r.image_path) for r in result.results if not r.success
        ]

        batch = read_images([Path(r.image_path) for r in successful])
        detections_by_path: dict[Path, list[DetectedObject]] = {
            Path(r.image_path): [
                DetectedObject(
                    label=c.label,
                    bounding_box=c.bounding_box,
                    confidence=c.confidence,
                )
                for c in r.detections
            ]
            for r in successful
        }

        loaded_images = [
            LoadedImageDetections(
                path=path,
                image=image,
                detections=detections_by_path.get(path, []),
            )
            for path, image in batch.loaded_images
        ]
        return ReviewPageInput(
            failed_paths=pipeline_failed_paths + batch.failed_paths,
            loaded_images=loaded_images,
        )

    def cancel(self) -> None:
        """Cancel the running task and return to the homepage."""
        if self._task is None or self._task.done:
            return

        self.cancel_button.setEnabled(False)
        self.status_label.setText("Cancelling...")

        self._task.cancel()
        # Drop our handle so late progress/result callbacks become no-ops.
        self._task = None

        # Import here to avoid circular dependency
        from src.ui.main_window import Page

        self.transition_page_fn(Page.HOME)
