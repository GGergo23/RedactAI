"""Interactive drop target widget used on the homepage."""

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QLabel, QStyle, QVBoxLayout, QWidget


class DropTargetWidget(QWidget):
    """Interactive drop target that also supports click-to-open."""

    def __init__(self, on_click: Callable[[], None], on_result: Callable[[list[str]], None]) -> None:
        """Initialize the drop target widget.

        Args:
            on_click: Callback invoked when the target is clicked.
            on_result: Callback invoked with the list of dropped files.
        """
        super().__init__()
        self._on_click = on_click
        self.on_result = on_result
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
            result = self._on_click()
            if result:
                self.on_result(result)
            event.accept()
            return
        super().mousePressEvent(event)
