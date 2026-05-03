"""Homepage view with title, interactive drag target, and file open button."""

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.ui.views.drop_target_widget import DropTargetWidget


class HomePage(QWidget):
    """Homepage view component."""

    def __init__(self, on_open_files: Callable[[], None]) -> None:
        """
        Initialize the homepage view.

        Args:
            on_open_files: Callback function when open files button is clicked.
        """
        super().__init__()
        self.on_open_files = on_open_files
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
        file_drag_area = DropTargetWidget(self.on_open_files)

        # Add components to layout with responsive spacing
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        layout.addWidget(file_drag_area, 2)
        layout.addStretch()
