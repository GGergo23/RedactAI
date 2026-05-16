"""Detection progress view showing pipeline execution status."""

from typing import Callable

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QLabel,
    QProgressBar,
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
        self.progress_bar.setTextVisible(False) # use custom label for percentage

        # Progress percentage label
        self.progress_percentage_label = QLabel(f"{self.current_progress}%")
        self.progress_percentage_label.setProperty("role", "body")
        self.progress_percentage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add components to layout
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_percentage_label)
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

        # Reset progress state
        self.status_label.setText("Starting detection pipeline...")
        self.update_progress(0)

        # start detection task
        # mock for now
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(lambda: self.on_detection_complete() if self.current_progress >= 100 else self.update_progress(min(100, self.current_progress + 12)))
        self.progress_timer.start(300)

    def update_progress(self, progress: int) -> None:
        """Update the progress bar and status text."""
        self.current_progress = progress
        self.progress_bar.setValue(self.current_progress)
        self.progress_percentage_label.setText(f"{self.current_progress}%")

    def on_detection_complete(self) -> None:
        """Handle detection completion and transition to results."""
        # TODO: results
        ...
        
        # DEBUG: Stop current progress simulation
        self.progress_timer.stop()
        
        # Import here to avoid circular dependency
        from src.ui.main_window import Page

        self.transition_page_fn(Page.PLACEHOLDER, results=None)
