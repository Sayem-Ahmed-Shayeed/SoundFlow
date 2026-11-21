"""A small turning arc for "working" states (Transcribing, Polishing)."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from soundflow.design.motion import reduced_motion
from soundflow.design.theme import current_palette


class Spinner(QWidget):
    """Accent arc on a faint ring; turns only while visible.

    With reduced motion it stays still: the label beside it already says
    that work is happening.
    """

    TURN_MS = 800

    def __init__(self, size: int = 14, parent: QWidget | None = None, *, color: str = "") -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._color = color
        self._angle = 0.0
        self._turn = QVariantAnimation(self)
        self._turn.setStartValue(0.0)
        self._turn.setEndValue(360.0)
        self._turn.setDuration(self.TURN_MS)
        self._turn.setEasingCurve(QEasingCurve.Type.Linear)
        self._turn.setLoopCount(-1)
        self._turn.valueChanged.connect(self._set_angle)

    def is_turning(self) -> bool:
        return self._turn.state() == QVariantAnimation.State.Running

    def _set_angle(self, value) -> None:
        self._angle = float(value)
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not reduced_motion():
            self._turn.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._turn.stop()

    def paintEvent(self, event) -> None:
        del event
        color = QColor(self._color or current_palette()["accent"])
        faint = QColor(color)
        faint.setAlphaF(0.25)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = max(1.5, self.width() / 7)
        rect = QRectF(self.rect()).adjusted(width / 2, width / 2, -width / 2, -width / 2)
        pen = QPen(faint, width)
        painter.setPen(pen)
        painter.drawEllipse(rect)
        pen.setColor(color)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, int((90 - self._angle) * 16), -90 * 16)


__all__ = ["Spinner"]
