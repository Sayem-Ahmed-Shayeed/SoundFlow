"""The Cupertino activity indicator, for "working" states.

Eight rounded spokes around a centre. The brightest spoke steps one place
clockwise eight times a second with the next ones trailing off behind it,
the way iOS shows loading. Because it moves in steps, it repaints only
eight times a second, not sixty: cheap enough to leave on while the app
transcribes.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from soundflow.design.motion import reduced_motion
from soundflow.design.theme import current_palette

SPOKES = 8
STEP_MS = 125  # one turn a second
# Opacity of each spoke, from the brightest backwards (as iOS draws it).
SPOKE_ALPHA = (1.0, 0.86, 0.72, 0.58, 0.44, 0.32, 0.32, 0.32)


def paint_activity(
    painter: QPainter, center: QPointF, radius: float, color: QColor, step: int
) -> None:
    """Draw the indicator at ``center``; ``step`` is which spoke is brightest."""
    width = max(1.4, radius / 4.5)
    inner = radius * 0.42
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.translate(center)
    spoke = QRectF(-width / 2, -radius, width, radius - inner)
    ink = QColor(color)
    for index in range(SPOKES):
        behind = (step - index) % SPOKES
        ink.setAlphaF(color.alphaF() * SPOKE_ALPHA[behind])
        painter.setBrush(ink)
        painter.save()
        painter.rotate(index * 360.0 / SPOKES)
        painter.drawRoundedRect(spoke, width / 2, width / 2)
        painter.restore()
    painter.restore()


def activity_step(elapsed_ms: float) -> int:
    """Which spoke is brightest after ``elapsed_ms``."""
    return int(elapsed_ms // STEP_MS) % SPOKES


class Spinner(QWidget):
    """A Cupertino activity indicator that runs only while it is visible.

    With reduced motion it holds still: the label beside it already says
    that work is happening.
    """

    def __init__(self, size: int = 14, parent: QWidget | None = None, *, color: str = "") -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._color = color
        self._step = 0
        self._timer = QTimer(self)
        self._timer.setInterval(STEP_MS)
        self._timer.setTimerType(Qt.TimerType.CoarseTimer)
        self._timer.timeout.connect(self._advance)

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def is_turning(self) -> bool:
        return self._timer.isActive()

    def _advance(self) -> None:
        self._step = (self._step + 1) % SPOKES
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not reduced_motion():
            self._timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._timer.stop()

    def paintEvent(self, event) -> None:
        del event
        color = QColor(self._color or current_palette()["text2"])
        painter = QPainter(self)
        side = min(self.width(), self.height())
        paint_activity(painter, QPointF(self.width() / 2, self.height() / 2), side / 2, color, self._step)
        painter.end()


ActivityIndicator = Spinner
__all__ = ["SPOKES", "STEP_MS", "ActivityIndicator", "Spinner", "activity_step", "paint_activity"]
