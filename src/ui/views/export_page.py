"""Export view for showing and executing export functionality."""

from typing import Callable

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from src.ui.views.review.types import ReviewPageOutput


class ExportPageView(QWidget):
    """Export view for showing and executing export functionality."""

    def __init__(self, transition_page_fn: Callable) -> None:
        """
        Initialize the export view.

        Args:
            transition_page_fn: Function to transition to another page.
        """
        super().__init__()
        self.transition_page_fn = transition_page_fn
        self.launch_extra: dict[str, object] = {}
        self._setup_ui()
        self.is_done = False
        self.export_timer: QTimer | None = None  # Timer to simulate export process

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

        # Title
        title = QLabel("Exporting step")
        title.setProperty("role", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Description
        self.description = QLabel(
            "All redaction targets have been approved. "
            "Click the button below to start exporting."
        )
        self.description.setProperty("role", "subtitle")
        self.description.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Main button
        self.main_button = QPushButton("Start Export")
        self.main_button.setProperty("role", "primary")
        self.main_button.setMinimumWidth(220)
        self.main_button.clicked.connect(self.main_button_clicked)

        # Add components to layout
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(self.description)
        layout.addStretch()
        layout.addWidget(self.main_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

    def main_button_clicked(self) -> None:
        if self.is_done:
            # Export already finished, return to home page
            # import here to avoid circular import
            from src.ui.main_window import Page

            self.transition_page_fn(Page.HOME)
            return

        # Start export process
        self.main_button.setEnabled(False)
        self.main_button.setText("Exporting...")
        self.description.setText(
            "Exporting in progress. This may take a few moments..."
        )

        self.start_export_process()

    def start_export_process(self) -> None:
        """Start the export process."""

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
        # TODO: start export logic here
        self.export_timer = QTimer()
        self.export_timer.setSingleShot(True)
        self.export_timer.timeout.connect(self.on_export_finished)
        self.export_timer.start(2000)  # slight delay to allow UI update

    def on_export_finished(self) -> None:
        """Called when the export process is finished."""
        self.description.setText(
            "Export complete! Click the button below to return to the home page."
        )
        self.main_button.setText("Go back to Home")
        self.main_button.setEnabled(True)
        self.is_done = True
        self.export_timer = None

    def on_page_become_current(self) -> None:
        """Called when this page becomes the current page in the stack."""

        self.main_button.setEnabled(True)
        self.main_button.setText("Start Export")
        self.description.setText(
            "All redaction targets have been approved. "
            "Click the button below to start exporting."
        )
        self.is_done = False
