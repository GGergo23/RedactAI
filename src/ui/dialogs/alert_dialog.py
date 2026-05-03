"""Reusable alert dialog for informational and warning messages."""

from enum import Enum

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QStyle,
    QVBoxLayout,
    QWidget,
)


class AlertSeverity(str, Enum):
    """Supported alert severity levels."""

    INFO = "info"
    WARNING = "warning"


class AlertDialog(QDialog):
    """Small reusable popup for displaying alert messages."""

    _DEFAULT_TITLES = {
        AlertSeverity.INFO: "Information",
        AlertSeverity.WARNING: "Warning",
    }

    def __init__(
        self,
        message: str,
        *,
        severity: AlertSeverity | str = AlertSeverity.INFO,
        title: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._severity = self._coerce_severity(severity)
        self.setWindowTitle(title or self._DEFAULT_TITLES[self._severity])
        self.setModal(True)
        self.setObjectName("alertDialog")
        self.setProperty("role", "alert-dialog")
        self.setProperty("severity", self._severity.value)
        self._setup_ui(message)

    @classmethod
    def _coerce_severity(cls, severity: AlertSeverity | str) -> AlertSeverity:
        if isinstance(severity, AlertSeverity):
            return severity

        normalized = str(severity).strip().lower()
        return AlertSeverity(normalized)

    def _setup_ui(self, message: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(14)

        icon_label = QLabel()
        icon_label.setProperty("role", "alert-icon")
        icon_label.setProperty("severity", self._severity.value)
        icon_kind = (
            QStyle.StandardPixmap.SP_MessageBoxWarning
            if self._severity is AlertSeverity.WARNING
            else QStyle.StandardPixmap.SP_MessageBoxInformation
        )
        icon = self.style().standardIcon(icon_kind)
        icon_label.setPixmap(icon.pixmap(40, 40))
        icon_align = Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter
        icon_label.setAlignment(icon_align)

        text_column = QVBoxLayout()
        text_column.setSpacing(8)

        title_label = QLabel(self.windowTitle())
        title_label.setProperty("role", "alert-title")
        title_label.setWordWrap(True)

        message_label = QLabel(message)
        message_label.setProperty("role", "alert-message")
        message_label.setWordWrap(True)

        text_column.addWidget(title_label)
        text_column.addWidget(message_label)

        header_layout.addWidget(icon_label, 0)
        header_layout.addLayout(text_column, 1)

        button_box = QDialogButtonBox()
        close_button = button_box.addButton(
            "Close",
            QDialogButtonBox.ButtonRole.RejectRole,
        )
        close_button.setProperty("role", "alert-close")
        close_button.clicked.connect(self.close)

        layout.addLayout(header_layout)
        layout.addWidget(button_box, alignment=Qt.AlignmentFlag.AlignRight)

        self.setMinimumWidth(360)


def show_alert(
    parent: QWidget | None,
    message: str,
    *,
    severity: AlertSeverity | str = AlertSeverity.INFO,
    title: str | None = None,
) -> int:
    """Display an alert dialog and return the modal result code."""

    dialog = AlertDialog(
        message,
        severity=severity,
        title=title,
        parent=parent,
    )
    return dialog.exec()
