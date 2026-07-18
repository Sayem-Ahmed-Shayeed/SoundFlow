"""Accessible custom-painted boolean switch."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QStyleOptionFocusRect, QStyle,
    QVBoxLayout, QWidget,
)


class ToggleSwitch(QCheckBox):
    """A compact pill switch retaining native checkbox semantics."""

    def __init__(self, accessible_name: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setText("")
        self.setAccessibleName(accessible_name)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(44, 32)

    def sizeHint(self) -> QSize:
        return QSize(44, 32)

    def hitButton(self, position) -> bool:
        return self.rect().contains(position)

    @staticmethod
    def color_tokens(*, dark: bool, checked: bool) -> tuple[str, str, str]:
        if checked:
            return (
                ("#9B72FF", "#A987FF", "#FFFFFF")
                if dark else ("#7657F6", "#6848E8", "#FFFFFF")
            )
        return (
            ("#242429", "#3A3A42", "#B7B7C0")
            if dark else ("#D9DBE2", "#B9BCC6", "#FFFFFF")
        )

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        appearance = self.window().property("darkAppearance")
        dark = bool(appearance) if appearance is not None else (
            self.palette().color(self.palette().ColorRole.Window).lightness() < 128
        )
        track_token, border_token, thumb_token = self.color_tokens(
            dark=dark, checked=self.isChecked()
        )
        track = QColor(track_token)
        border = QColor(border_token)
        thumb = QColor(thumb_token)
        if not self.isEnabled():
            painter.setOpacity(0.5)
        painter.setPen(QPen(border, 1))
        painter.setBrush(track)
        painter.drawRoundedRect(2, 5, 40, 22, 11, 11)
        x = 23 if self.isChecked() else 5
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(thumb)
        painter.drawEllipse(x, 8, 16, 16)
        if self.hasFocus():
            painter.setOpacity(1)
            option = QStyleOptionFocusRect()
            option.initFrom(self)
            option.rect = self.rect().adjusted(0, 0, -1, -1)
            self.style().drawPrimitive(
                QStyle.PrimitiveElement.PE_FrameFocusRect,
                option,
                painter,
                self,
            )


class PreferenceToggleRow(QWidget):
    """Label/description row with a right-aligned accessible switch."""

    def __init__(
        self,
        label: str,
        description: str = "",
        *,
        checked: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("toggleRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)
        copy = QVBoxLayout()
        copy.setSpacing(2)
        title = QLabel(label)
        title.setObjectName("toggleRowTitle")
        title.setWordWrap(True)
        copy.addWidget(title)
        if description:
            detail = QLabel(description)
            detail.setObjectName("mutedText")
            detail.setWordWrap(True)
            copy.addWidget(detail)
        layout.addLayout(copy, 1)
        self.switch = ToggleSwitch(label)
        self.switch.setAccessibleDescription(description)
        self.switch.setChecked(checked)
        layout.addWidget(self.switch)


__all__ = ["PreferenceToggleRow", "ToggleSwitch"]
