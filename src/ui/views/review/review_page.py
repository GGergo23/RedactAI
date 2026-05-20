"""Review page for inspecting and approving AI-detected redaction targets."""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt

from src.ai.types import BoundingBox
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.views.review.image_canvas import ImageCanvas
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
        self._current_index: int = 0
        # Per-image AI-box toggle state: {image_index: [accepted_flag, ...]}
        self._image_review_state: dict[int, list[bool]] = {}
        # Per-image manual boxes: {image_index: [(BoundingBox, accepted), ...]}
        self._image_manual_state: dict[int, list[tuple[BoundingBox, bool]]] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Title
        title = QLabel("Review Detections")
        title.setProperty("role", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # "Image X of Y — <filename>" or fallback message
        self.status_label = QLabel("No images loaded.")
        self.status_label.setProperty("role", "subtitle")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)

        # Banner shown when some paths failed to load
        self.failed_banner = QLabel("")
        self.failed_banner.setProperty("role", "body")
        self.failed_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.failed_banner.setWordWrap(True)
        self.failed_banner.setVisible(False)

        # Main image canvas
        self.canvas = ImageCanvas(self)

        # Shown instead of canvas when there are no images to review
        self.empty_state = QLabel("No images to review.")
        self.empty_state.setProperty("role", "body")
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state.setVisible(False)

        # Navigation row: [< Previous]  [Next >]  [Apply Redactions]
        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(12)

        self.prev_button = QPushButton("< Previous")
        self.prev_button.clicked.connect(self._go_prev)
        self.prev_button.setEnabled(False)

        self.next_button = QPushButton("Next >")
        self.next_button.clicked.connect(self._go_next)
        self.next_button.setEnabled(False)

        self.apply_button = QPushButton("Apply Redactions")
        self.apply_button.setProperty("role", "primary")
        self.apply_button.setEnabled(False)  # wired in Phase 5

        nav_layout.addWidget(self.prev_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.apply_button)

        back_button = QPushButton("Back to Home")
        back_button.setProperty("role", "primary")
        back_button.setMinimumWidth(220)
        back_button.clicked.connect(self._go_home)

        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addWidget(self.failed_banner)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.empty_state, 1)
        layout.addWidget(nav_widget)
        layout.addWidget(back_button, 0, Qt.AlignmentFlag.AlignHCenter)

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
            self._show_no_input_state()
            return

        failed_count = len(self._input.failed_paths)
        if failed_count > 0:
            noun = "image" if failed_count == 1 else "images"
            self.failed_banner.setText(
                f"{failed_count} {noun} failed to load and will be skipped."
            )
            self.failed_banner.setVisible(True)
        else:
            self.failed_banner.setVisible(False)

        image_count = len(self._input.loaded_images)
        print(
            f"[ReviewPageView] received {image_count} image(s), "
            f"{failed_count} failed path(s)"
        )

        if image_count == 0:
            self._show_empty_state()
        else:
            self._current_index = 0
            self._image_review_state = {}
            self._image_manual_state = {}
            self._show_image(self._current_index)

    def _show_no_input_state(self) -> None:
        """Render the page when no input has been set."""
        self.status_label.setText("No images loaded.")
        self.canvas.setVisible(False)
        self.empty_state.setVisible(True)
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.apply_button.setEnabled(False)

    def _show_empty_state(self) -> None:
        """Render the page when the batch contains zero loaded images."""
        self.status_label.setText("No images to review.")
        self.canvas.setVisible(False)
        self.empty_state.setVisible(True)
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.apply_button.setEnabled(False)

    def _snapshot_current(self) -> None:
        """Save the current image's AI toggle and manual-box state before navigating."""
        if self._input and self._input.loaded_images:
            self._image_review_state[self._current_index] = (
                self.canvas.get_detection_flags()
            )
            self._image_manual_state[self._current_index] = (
                self.canvas.get_manual_box_states()
            )

    def _show_image(self, index: int) -> None:
        """Render image *index* in the canvas and update navigation state.

        Restores previously saved toggle flags if this image has been visited.
        """
        images = self._input.loaded_images  # type: ignore[union-attr]
        item = images[index]
        total = len(images)

        self.canvas.setVisible(True)
        self.empty_state.setVisible(False)

        self.status_label.setText(f"Image {index + 1} of {total} — {item.path.name}")
        self.canvas.set_image(item.image, item.detections)

        if index in self._image_review_state:
            self.canvas.apply_detection_flags(self._image_review_state[index])

        if index in self._image_manual_state:
            self.canvas.restore_manual_boxes(self._image_manual_state[index])

        self.prev_button.setEnabled(index > 0)
        self.next_button.setEnabled(index < total - 1)

    def _go_prev(self) -> None:
        """Navigate to the previous image."""
        if self._input and self._current_index > 0:
            self._snapshot_current()
            self._current_index -= 1
            self._show_image(self._current_index)

    def _go_next(self) -> None:
        """Navigate to the next image."""
        if self._input and self._current_index < len(self._input.loaded_images) - 1:
            self._snapshot_current()
            self._current_index += 1
            self._show_image(self._current_index)

    def _go_home(self) -> None:
        """Navigate back to the home page."""
        from src.ui.main_window import Page

        self.transition_page_fn(Page.HOME)
