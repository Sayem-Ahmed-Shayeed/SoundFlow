"""Waveform ring — animated dotted-bar visualisation around the centre.

Replaces the legacy :class:`VoiceOrb`. The widget draws a fixed-size ring
of small vertical bars whose heights are driven by ``UiBridge.level``. A
small concentric dot marks the centre. No face, no smile — just geometry.

States:

* ``idle`` — ring at rest height.
* ``recording`` — bars animate from a 24-frame rolling buffer of levels.
* ``draining`` — bars decay back toward rest.
"""

from __future__ import annotations

from collections import deque
from math import cos, sin

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from soundflow.design import (
    BG_PANEL,
    FG_CREAM,
    FG_MUTED,
    FONT_HEADING,
    DISPLAY_FONT,
    SPACE_2,
)


class WaveformRing(QWidget):
    """A ring of small vertical bars driven by an audio level."""

    BAR_COUNT = 64
    FRAME_MS = 30

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("waveformRing")
        self.setMinimumSize(280, 100)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        self._levels: deque[float] = deque([0.0] * self.BAR_COUNT, maxlen=self.BAR_COUNT)
        self._state = "idle"

        self._timer = QTimer(self)
        self._timer.setInterval(self.FRAME_MS)
        self._timer.timeout.connect(self._decay)
        self._timer.start()

    # ------------------------------------------------------------------
    def set_state(self, state: str) -> None:
        if state not in {"idle", "recording", "draining"}:
            state = "idle"
        self._state = state
        self.update()

    def push_level(self, level: float) -> None:
        if self._state == "recording":
            clamped = max(0.0, min(1.0, float(level)))
            self._levels.append(clamped)
            self.update()

    def _decay(self) -> None:
        # Smooth decay back toward rest so the ring looks alive even between updates.
        if self._state == "recording":
            return
        if any(abs(v) > 0.01 for v in self._levels):
            for i in range(self.BAR_COUNT):
                self._levels[i] *= 0.92
            self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: D401, N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0

        # Centre dot
        centre_radius = 18
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(FG_CREAM))
        painter.drawEllipse(int(cx - centre_radius), int(cy - centre_radius),
                            centre_radius * 2, centre_radius * 2)

        # Inner mic glyph
        painter.setPen(QPen(QColor("#0A0A0A"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        mic_w, mic_h = 6, 14
        painter.drawRoundedRect(int(cx - mic_w / 2), int(cy - mic_h / 2),
                                int(mic_w), int(mic_h), 3, 3)

        # Ring of bars
        ring_radius = min(w, h) / 2.0 - 12
        bar_width = 2
        bar_color = QColor(FG_CREAM if self._state == "recording" else FG_MUTED)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bar_color)

        for i in range(self.BAR_COUNT):
            angle = (2 * 3.14159265) * (i / self.BAR_COUNT) - 3.14159265 / 2
            bar_x = cx + ring_radius * cos(angle) - bar_width / 2
            base_h = 4
            level = self._levels[i] if i < len(self._levels) else 0.0
            extra = level * 18  # max extra height
            bar_h = base_h + extra
            bar_y = cy + ring_radius * sin(angle) - bar_h / 2
            painter.drawRoundedRect(int(bar_x), int(bar_y),
                                    int(bar_width), int(bar_h), 1, 1)

        painter.end()


__all__ = ["WaveformRing"]