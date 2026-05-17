"""Detection progress view showing pipeline execution status."""

from typing import Callable

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DetectionProgressView(QWidget):
    """View displaying the progress of the detection pipeline."""

    def __init__(self, transition_page_fn: Callable) -> None:
        """
        Initialize the detection progress view.

        Args:
            transition_page_fn: Function for transitioning to other pages.
        """
        super().__init__()
        self.transition_page_fn = transition_page_fn
        self.files: list[str] = []
        self.current_progress = 0
        self.progress_timer: QTimer | None = None  # debug progress simulation
        self._setup_ui()

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
        """Start the mock detection pipeline simulation."""
        if self._is_detection_task_running():
            return  # Prevent starting multiple tasks

        # Reset progress state
        self.status_label.setText("Starting detection pipeline...")
        self.on_progress_update(0)

        # start detection task
        # mock for now
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(
            lambda: (
                self.on_detection_complete(None)
                if self.current_progress >= 100
                else self.on_progress_update(min(100, self.current_progress + 12))
            )
        )
        self.progress_timer.start(300)
        self.cancel_button.setEnabled(True)

        # Update status text
        self.status_label.setText("Running detection pipeline...")

    def on_progress_update(self, progress: int) -> None:
        """Update the progress bar and status text."""
        self.current_progress = progress
        self.progress_bar.setValue(self.current_progress)
        self.progress_percentage_label.setText(f"{self.current_progress}%")

    # TODO: Replace type with real detection results object
    def on_detection_complete(self, detection_results: object) -> None:
        """Handle detection completion and transition to results."""
        self.status_label.setText("Detection complete!")
        self.cancel_button.setEnabled(False)

        # Debug: stop the progress timer if it's still running
        self.progress_timer.stop()

        # Import here to avoid circular dependency
        from src.ui.main_window import Page

        self.transition_page_fn(Page.PLACEHOLDER, results=detection_results)

    def cancel(self) -> None:
        """Cancel the running task and return to the homepage."""
        if not self._is_detection_task_running():
            return

        # update UI state
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Cancelling...")

        # Cancel the task
        self.progress_timer.stop()

        # Import here to avoid circular dependency
        from src.ui.main_window import Page

        self.transition_page_fn(Page.HOME)

    def _is_detection_task_running(self) -> bool:
        """Check if the detection task is currently running."""
        return self.progress_timer is not None and self.progress_timer.isActive()
