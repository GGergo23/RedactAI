"""Review page for inspecting and approving AI-detected redaction targets."""

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from src.ui.views.review.types import ReviewPageInput


class ReviewPageView(QWidget):
    """Page where the user reviews AI detections before applying redactions."""

    def __init__(self, transition_page_fn: Callable) -> None:
        """
        Initialize the review page.

        Args:
            transition_page_fn: Function for transitioning to other pages.
        """
        super().__init__()
        self.transition_page_fn = transition_page_fn
        self._input: ReviewPageInput | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        title = QLabel("Review Detections")
        title.setProperty("role", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel("No images loaded.")
        self.status_label.setProperty("role", "body")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)

        back_button = QPushButton("Back to Home")
        back_button.setProperty("role", "primary")
        back_button.setMinimumWidth(220)
        back_button.clicked.connect(self._go_home)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(back_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

    def setLaunchExtra(self, **kwargs: object) -> None:
        """Store the review input passed from the detection progress page.

        Args:
            **kwargs: Expected key: ``input`` — a :class:`ReviewPageInput`
                describing images and their detections.
        """
        if "input" in kwargs:
            self._input = kwargs["input"]  # type: ignore[assignment]

    def on_page_become_current(self) -> None:
        """Called when this page becomes the active page in the stack."""
        if self._input is None:
            self.status_label.setText("No images loaded.")
            return

        image_count = len(self._input.loaded_images)
        failed_count = len(self._input.failed_paths)
        print(
            f"[ReviewPageView] received {image_count} image(s), "
            f"{failed_count} failed path(s)"
        )

        if image_count == 0:
            self.status_label.setText("No images to review.")
        else:
            plural = "image" if image_count == 1 else "images"
            self.status_label.setText(
                f"Ready to review {image_count} {plural}. "
                "(Full canvas coming in Phase 2.)"
            )

    def _go_home(self) -> None:
        """Navigate back to the home page."""
        from src.ui.main_window import Page

        self.transition_page_fn(Page.HOME)
