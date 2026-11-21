"""Soundflow's own message window, in place of the desktop's QMessageBox.

Same surface as the History delete dialog: a rounded card in the app's
colours, a tinted icon tile from the app's line icons, a serif title, and
the app's buttons. ``inform`` shows a note with one button; ``ask`` asks a
question and returns True when the person picks the main action.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from soundflow.design import current_palette, icon_pixmap

# kind -> (icon, colour token, tint token)
_KINDS = {
    "info": ("info", "accent_text", "accent_soft"),
    "warning": ("alert", "warning", "warning_soft"),
    "error": ("alert", "danger", "danger_soft"),
    "question": ("info", "accent_text", "accent_soft"),
    "sign-out": ("logout", "danger", "danger_soft"),
}
DIALOG_WIDTH = 420


class MessageDialog(QDialog):
    def __init__(
        self,
        title: str,
        text: str,
        *,
        kind: str = "info",
        accept_text: str = "OK",
        reject_text: str = "",
        destructive: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("messageDialog")
        self.setModal(True)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(DIALOG_WIDTH)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        surface = QFrame()
        surface.setObjectName("messageDialogSurface")
        surface.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content = QVBoxLayout(surface)
        content.setContentsMargins(22, 22, 22, 18)
        content.setSpacing(0)

        name, ink, tint = _KINDS.get(kind, _KINDS["info"])
        colors = current_palette()
        self.badge = QLabel()
        self.badge.setObjectName("messageDialogBadge")
        self.badge.setFixedSize(40, 40)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setStyleSheet(f"background: {colors[tint]}; border-radius: 12px;")
        self.badge.setPixmap(icon_pixmap(name, colors[ink], 20))
        self.icon_name = name
        content.addWidget(self.badge)
        content.addSpacing(14)

        self.title = QLabel(title)
        self.title.setObjectName("messageDialogTitle")
        self.title.setWordWrap(True)
        content.addWidget(self.title)
        content.addSpacing(6)

        self.message = QLabel(text)
        self.message.setObjectName("messageDialogCopy")
        self.message.setWordWrap(True)
        self.message.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content.addWidget(self.message)
        content.addSpacing(20)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addStretch(1)
        self.reject_button: QPushButton | None = None
        if reject_text:
            self.reject_button = QPushButton(reject_text)
            self.reject_button.setObjectName("messageDialogCancel")
            self.reject_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.reject_button.clicked.connect(self.reject)
            actions.addWidget(self.reject_button)
        self.accept_button = QPushButton(accept_text)
        self.accept_button.setObjectName("destructiveButton" if destructive else "primaryButton")
        self.accept_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.accept_button.clicked.connect(self.accept)
        actions.addWidget(self.accept_button)
        # A destructive choice is never the Enter-key default.
        default = self.reject_button if (destructive and self.reject_button) else self.accept_button
        default.setDefault(True)
        default.setAutoDefault(True)
        content.addLayout(actions)
        outer.addWidget(surface)


def inform(parent: QWidget | None, title: str, text: str, *, kind: str = "info") -> None:
    MessageDialog(title, text, kind=kind, parent=parent).exec()


def ask(
    parent: QWidget | None,
    title: str,
    text: str,
    *,
    accept_text: str,
    reject_text: str = "Cancel",
    kind: str = "question",
    destructive: bool = False,
) -> bool:
    dialog = MessageDialog(
        title,
        text,
        kind=kind,
        accept_text=accept_text,
        reject_text=reject_text,
        destructive=destructive,
        parent=parent,
    )
    return dialog.exec() == QDialog.DialogCode.Accepted


__all__ = ["MessageDialog", "ask", "inform"]
