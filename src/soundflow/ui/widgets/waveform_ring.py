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
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

class WaveformRing(QWidget):
    """A ring of small vertical bars driven by an audio level."""

    BAR_COUNT = 64
    FRAME_MS = 30

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("waveformRing")
        self.setMinimumSize(420, 190)
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

        accent = QColor("#8B5CF6")
        quiet = QColor("#55427D")
        # Central microphone control and glow.
        centre_radius = 52
        painter.setPen(QPen(QColor(139, 92, 246, 75), 2))
        painter.setBrush(QColor(139, 92, 246, 18))
        painter.drawEllipse(
            int(cx - centre_radius), int(cy - centre_radius),
            centre_radius * 2, centre_radius * 2,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#111827"))
        painter.drawEllipse(int(cx - 44), int(cy - 44), 88, 88)

        painter.setPen(QPen(accent, 4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        mic_w, mic_h = 14, 30
        painter.drawRoundedRect(int(cx - mic_w / 2), int(cy - mic_h / 2),
                                int(mic_w), int(mic_h), 7, 7)
        painter.drawArc(int(cx - 15), int(cy - 9), 30, 30, 180 * 16, 180 * 16)
        painter.drawLine(int(cx), int(cy + 21), int(cx), int(cy + 29))
        painter.drawLine(int(cx - 9), int(cy + 29), int(cx + 9), int(cy + 29))

        # Mirrored horizontal waveform from the central control.
        bar_width = 2
        bar_color = accent if self._state == "recording" else quiet
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bar_color)
        span = min(170.0, max(90.0, w / 2.0 - 70.0))
        for side in (-1, 1):
            for i in range(32):
                level = self._levels[(i * 2) % len(self._levels)]
                pulse = 3 + level * 28
                x = cx + side * (64 + (i / 31.0) * span)
                painter.drawRoundedRect(
                    int(x - bar_width / 2), int(cy - pulse / 2),
                    bar_width, int(pulse), 1, 1,
                )

        painter.end()


__all__ = ["WaveformRing"]
