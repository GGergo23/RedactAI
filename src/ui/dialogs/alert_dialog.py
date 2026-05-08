"""Reusable alert dialog for informational and warning messages."""

from dataclasses import dataclass
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


class AlertButtonRole(str, Enum):
    """Supported action roles for alert dialog buttons."""

    CONFIRM = "confirm"
    CANCEL = "cancel"


@dataclass(frozen=True, slots=True)
class AlertDialogButtonSpec:
    """Configuration for a single alert dialog button."""

    role: AlertButtonRole
    text: str


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
        buttons: list[AlertDialogButtonSpec] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._severity = self._coerce_severity(severity)
        self.setWindowTitle(title or self._DEFAULT_TITLES[self._severity])
        self.setModal(True)
        self.setObjectName("alertDialog")
        self.setProperty("role", "alert-dialog")
        self.setProperty("severity", self._severity.value)
        self._setup_ui(message, buttons or self._default_buttons())

    @staticmethod
    def _default_buttons() -> list[AlertDialogButtonSpec]:
        """Return the default single-button layout."""

        return [
            AlertDialogButtonSpec(
                role=AlertButtonRole.CANCEL,
                text="Cancel",
            )
        ]

    @classmethod
    def _coerce_severity(cls, severity: AlertSeverity | str) -> AlertSeverity:
        if isinstance(severity, AlertSeverity):
            return severity

        normalized = str(severity).strip().lower()
        return AlertSeverity(normalized)

    def _setup_ui(self, message: str, buttons: list[AlertDialogButtonSpec]) -> None:
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
        for index, button_spec in enumerate(buttons):
            if button_spec.role is AlertButtonRole.CONFIRM:
                qt_role = QDialogButtonBox.ButtonRole.AcceptRole
                handler = self.accept
                role_style = "confirm"
            elif button_spec.role is AlertButtonRole.CANCEL:
                qt_role = QDialogButtonBox.ButtonRole.RejectRole
                handler = self.reject
                role_style = "cancel"
            else:  # pragma: no cover - defensive guard for future roles
                raise ValueError(f"Unsupported button role: {button_spec.role!r}")

            button = button_box.addButton(button_spec.text, qt_role)
            button.setProperty("role", f"alert-{role_style}")
            if index == 0:
                button.setDefault(True)
            button.clicked.connect(handler)

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
    """Display an alert dialog and return the modal result code.

    Return the result code of the dialog.
    """

    dialog = AlertDialog(
        message,
        severity=severity,
        title=title,
        parent=parent,
    )
    return dialog.exec()


def show_confirmation_dialog(
    parent: QWidget | None,
    message: str,
    *,
    severity: AlertSeverity | str = AlertSeverity.INFO,
    title: str | None = None,
) -> int:
    """Display a confirmation dialog with 2 buttons.

    Returns the result code of the dialog.
    """

    buttons = [
        AlertDialogButtonSpec(
            role=AlertButtonRole.CONFIRM,
            text="Allow",
        ),
        AlertDialogButtonSpec(
            role=AlertButtonRole.CANCEL,
            text="Decline",
        ),
    ]

    dialog = AlertDialog(
        message,
        severity=severity,
        buttons=buttons,
        title=title,
        parent=parent,
    )
    return dialog.exec()
