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

        # Summary shown when Apply Redactions forwards output here
        self._summary_label = QLabel("")
        self._summary_label.setProperty("role", "body")
        self._summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._summary_label.setWordWrap(True)
        self._summary_label.setVisible(False)

        # Back button
        back_button = QPushButton("Back to Home")
        back_button.setProperty("role", "primary")
        back_button.setMinimumWidth(220)
        back_button.clicked.connect(self.on_back)

        # Add components to layout
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self._summary_label)
        layout.addStretch()
        layout.addWidget(back_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

    def on_page_become_current(self) -> None:
        """Called when this page becomes the current page in the stack."""
        from src.ui.views.review.types import ReviewPageOutput

        output = self.launch_extra.get("output")
        if not isinstance(output, ReviewPageOutput):
            self._summary_label.setVisible(False)
            return

        total = sum(len(img.approved_targets) for img in output.loaded_images)
        lines = [
            f"  Image {i + 1} ({img.path.name}): "
            f"{len(img.approved_targets)} target(s)"
            for i, img in enumerate(output.loaded_images)
        ]
        print(
            f"[PlaceholderView] received {total} redaction target(s) "
            f"across {len(output.loaded_images)} image(s):"
        )
        for line in lines:
            print(line)

        summary_text = f"{total} redaction target(s) ready.\n" + "\n".join(lines)
        self._summary_label.setText(summary_text)
        self._summary_label.setVisible(True)
