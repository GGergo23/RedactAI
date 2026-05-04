"""Placeholder view for content in development."""

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class PlaceholderView(QWidget):
    """Placeholder view for pages in development."""

    def __init__(self, on_back: Callable[[], None]) -> None:
        """
        Initialize the placeholder view.

        Args:
            on_back: Callback function when back button is clicked.
        """
        super().__init__()
        self.on_back = on_back
        self.launch_extra: dict[str, object] = {}
        self._setup_ui()

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
        title = QLabel("Coming Soon")
        title.setProperty("role", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Description
        description = QLabel("This feature is coming soon...")
        description.setProperty("role", "subtitle")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Back button
        back_button = QPushButton("Back to Home")
        back_button.setProperty("role", "primary")
        back_button.setMinimumWidth(220)
        back_button.clicked.connect(self.on_back)

        # Add components to layout
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch()
        layout.addWidget(back_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
