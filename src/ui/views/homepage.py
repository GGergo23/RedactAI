"""Homepage view with title, interactive drag target, and file open button."""

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.views.drop_target_widget import DropTargetWidget


class HomePage(QWidget):
    """Homepage view component."""

    def __init__(self, transition_page_fn: Callable) -> None:
        """
        Initialize the homepage view.

        Args:
            transition_page: Function for transitioning to other pages.
        """
        super().__init__()
        self.transition_page_fn = transition_page_fn
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI components with responsive layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(18)

        # Logo title
        logo_recat = '<span style="color: #FFFFFF;">Redact</span>'
        logo_ai = '<span style="color: #C62828;">AI</span>'
        title = QLabel(f"{logo_recat}{logo_ai}")
        title.setProperty("role", "title")
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Subtitle
        subtitle = QLabel("Your AI-powered redaction assistant")
        subtitle.setProperty("role", "subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Drag area
        file_drag_area = DropTargetWidget(self.open_files, self.handle_files)

        # Add components to layout with responsive spacing
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        layout.addWidget(file_drag_area)
        layout.addStretch(2)

    def open_files(self) -> list[str]:
        """Open a native file picker for selecting one or more image files."""
        image_extensions = "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp"
        image_filter = f"Images ({image_extensions});;All Files (*)"
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Images",
            "",
            image_filter,
        )
        return files

    def handle_files(self, files: list[str]) -> None:
        """Process the file paths obtained from drag-n-drop or file picker."""
        # Import here to avoid circular dependency
        from src.ui.main_window import Page

        self.transition_page_fn(Page.PLACEHOLDER, files=files)
