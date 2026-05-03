"""Homepage view with title, interactive drag target, and file open button."""

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QLabel,
    QStyle,
    QVBoxLayout,
    QWidget,
)


class DropTargetWidget(QWidget):
    """Interactive drop target that also supports click-to-open."""

    def __init__(self, on_click: Callable[[], None]) -> None:
        """Initialize the drop target widget.

        Args:
            on_click: Callback invoked when the target is clicked.
        """
        super().__init__()
        self._on_click = on_click
        self.setMinimumHeight(300)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("role", "drag-area")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create icon, title, and helper text inside the target area."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)

        icon = QLabel()
        icon.setProperty("role", "drag-icon")
        open_icon_kind = QStyle.StandardPixmap.SP_DialogOpenButton
        open_icon = self.style().standardIcon(open_icon_kind)
        icon_pixmap = open_icon.pixmap(52, 52)
        icon.setPixmap(icon_pixmap)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Drag Files Here")
        title.setProperty("role", "drag-title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("or click to browse from your device")
        subtitle.setProperty("role", "drag-subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Trigger file-open callback on left click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_click()
            event.accept()
            return
        super().mousePressEvent(event)


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
