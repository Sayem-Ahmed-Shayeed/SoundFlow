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

import math
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
        self._phase = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(self.FRAME_MS)
        self._timer.timeout.connect(self._tick)
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

    def _tick(self) -> None:
        # Keep the hero subtly alive and decay audio energy between sessions.
        self._phase += 0.075
        if self._state != "recording" and any(
            abs(v) > 0.01 for v in self._levels
        ):
            for i in range(self.BAR_COUNT):
                self._levels[i] *= 0.92
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: D401, N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0

        appearance = self.window().property("darkAppearance")
        dark = bool(appearance) if appearance is not None else (
            self.palette().color(self.palette().ColorRole.Window).lightness() < 128
        )
        accent = QColor("#9B72FF" if dark else "#7657F6")
        if self._state == "recording":
            accent = QColor("#FF6EC7" if dark else "#D6336C")
        elif self._state == "draining":
            accent = QColor("#FFC24B" if dark else "#B7791F")
        quiet = QColor("#47516A" if dark else "#CBD1DF")
        centre = QColor("#111A2B" if dark else "#FFFFFF")
        # Central microphone control and glow.
        ambient = (math.sin(self._phase) + 1.0) / 2.0
        centre_radius = 54 + int(ambient * (3 if self._state != "idle" else 1))
        glow = QColor(accent)
        glow.setAlpha(54 + int(ambient * (72 if self._state != "idle" else 20)))
        fill = QColor(accent)
        fill.setAlpha(18)
        painter.setPen(QPen(glow, 2))
        painter.setBrush(fill)
        painter.drawEllipse(
            int(cx - centre_radius), int(cy - centre_radius),
            centre_radius * 2, centre_radius * 2,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(centre)
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
                idle_wave = (math.sin(self._phase + i * 0.52) + 1.0) * 0.9
                pulse = 3 + level * 28 + idle_wave
                x = cx + side * (64 + (i / 31.0) * span)
                painter.drawRoundedRect(
                    int(x - bar_width / 2), int(cy - pulse / 2),
                    bar_width, int(pulse), 1, 1,
                )

        painter.end()


__all__ = ["WaveformRing"]
