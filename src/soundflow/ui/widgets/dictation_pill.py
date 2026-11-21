"""Floating dictation pill shown while dictating from any app.

A small ink-black capsule near the bottom of the screen, the same in both
themes so it reads on any app behind it::

    ( ●  ılıIlıIılı  0:07 )

* ``recording`` - a red dot, your voice as cream bars scrolling right to
  left, and the elapsed time.
* ``processing`` - a turning mint arc; the bars stop and dim while a light
  sweeps across them, and the time stops.
* ``done`` - a mint check and "Pasted" (or "Copied"), then it hides itself.

It is summoned by a shortcut many times a day, so it appears and leaves
instantly. It paints everything itself (no child widgets or opacity effects
on a translucent always-on-top window), and draws no shadow: a soft shadow
on a translucent window shows as a grey halo on desktops that don't blend
it. It repaints when audio arrives; its timer runs only to turn the spinner,
move the sweep and tick the clock.
"""

from __future__ import annotations

from collections import deque

import numpy as np
from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QWidget

from soundflow.design.fonts import BODY_FONT, tabular
from soundflow.design.motion import reduced_motion

PILL_BG = "#141414"
PILL_BORDER = "#3A3A36"
PILL_TEXT = "#FFFFEB"
PILL_DIM = "#A3A396"
PILL_OK = "#7FD6BE"
PILL_ON_OK = "#04211C"
PILL_RECORD = "#FF6A57"


class DictationPill(QWidget):
    """Always-on-top recording indicator for dictation outside the app."""

    WINDOW_W = 216
    WINDOW_H = 56
    PILL_W = 200
    PILL_H = 40
    BAR = 2.5
    GAP = 2.5
    BARS_W = 104
    BARS_H = 20
    CHUNK = 480  # 30 ms of 16 kHz audio per bar
    SPIN_MS = 33
    CLOCK_MS = 250
    TURN_MS = 800
    SWEEP_MS = 1400
    DONE_MS = 900

    def __init__(self) -> None:
        super().__init__(None)
        self.setObjectName("recordingOverlay")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(self.WINDOW_W, self.WINDOW_H)

        self._state = "hidden"
        self._done_text = "Pasted"
        self._started_at = 0.0
        self._frozen_ms = 0.0
        self._heard_audio = False
        self._levels: deque[float] = deque(maxlen=self._bar_count())
        self._pending = np.zeros(0, dtype=np.float32)

        self._clock = QElapsedTimer()
        self._clock.start()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._done_timer = QTimer(self)
        self._done_timer.setSingleShot(True)
        self._done_timer.setInterval(self.DONE_MS)
        self._done_timer.timeout.connect(self._hide_now)

        self._time_font = QFont(BODY_FONT)
        self._time_font.setPixelSize(13)
        self._time_font.setWeight(QFont.Weight.DemiBold)
        tabular(self._time_font)

    # -- public API (called by the main window) -----------------------------------
    @property
    def state(self) -> str:
        return self._state

    def show_recording(self, shortcut: str = "") -> None:
        del shortcut  # the pill shows time, not the chord
        self._done_timer.stop()
        self._state = "recording"
        self._started_at = self._now()
        self._frozen_ms = 0.0
        self._heard_audio = False
        self._levels.clear()
        self._pending = np.zeros(0, dtype=np.float32)
        self._show_near_cursor_screen()
        self._run_timer(self.CLOCK_MS)

    def show_processing(self) -> None:
        if self._state == "recording":
            self._frozen_ms = self._now() - self._started_at
        self._done_timer.stop()
        self._state = "processing"
        if reduced_motion():
            self._timer.stop()
        else:
            self._run_timer(self.SPIN_MS)
        self.update()

    def show_done(self, text: str = "Pasted") -> None:
        """Confirm the transcript landed, then hide after a moment."""
        if not self.isVisible():
            return
        self._state = "done"
        self._done_text = text or "Pasted"
        self._timer.stop()
        self._done_timer.start()
        self.update()

    def push_audio(self, pcm: bytes) -> None:
        if self._state != "recording" or not pcm:
            return
        samples = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").astype(np.float32)
        self._pending = np.concatenate([self._pending, samples / 32768])
        added = False
        while self._pending.size >= self.CHUNK:
            chunk, self._pending = self._pending[: self.CHUNK], self._pending[self.CHUNK :]
            rms = float(np.sqrt(np.mean(chunk * chunk)))
            db = 20 * np.log10(rms + 1e-7)
            self._levels.append(float(np.clip((db + 58) / 46, 0.0, 1.0)))
            added = True
        if added:
            self._heard_audio = True
            self.update()

    def set_level(self, level: float) -> None:
        """Fallback when no raw audio reaches the pill: one bar per level."""
        if self._state != "recording" or self._heard_audio:
            return
        self._levels.append(max(0.0, min(1.0, float(level))))
        self.update()

    def levels(self) -> list[float]:
        return list(self._levels)

    def hide_animated(self) -> None:
        # A confirmation in progress hides itself when it finishes.
        if self._state == "done" and self._done_timer.isActive():
            return
        self._hide_now()

    def elapsed_text(self) -> str:
        elapsed = self._frozen_ms if self._state != "recording" else (
            self._now() - self._started_at
        )
        minutes, seconds = divmod(int(elapsed // 1000), 60)
        return f"{minutes}:{seconds:02d}"

    # -- window ------------------------------------------------------------------------
    def _bar_count(self) -> int:
        return int((self.BARS_W + self.GAP) // (self.BAR + self.GAP))

    def _hide_now(self) -> None:
        self._done_timer.stop()
        self._timer.stop()
        self._state = "hidden"
        self.hide()

    def _show_near_cursor_screen(self) -> None:
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        self.move(
            area.x() + (area.width() - self.width()) // 2,
            area.y() + area.height() - self.height() - 28,
        )
        self.show()
        self.raise_()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._timer.stop()

    # -- frames ------------------------------------------------------------------------
    def _now(self) -> float:
        return float(self._clock.elapsed())

    def _run_timer(self, interval: int) -> None:
        self._timer.setInterval(interval)
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def _tick(self) -> None:
        if not self.isVisible():
            self._timer.stop()
            return
        self.update()

    # -- painting ----------------------------------------------------------------------
    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pill = QRectF(
            (self.width() - self.PILL_W) / 2,
            (self.height() - self.PILL_H) / 2,
            self.PILL_W,
            self.PILL_H,
        )
        radius = self.PILL_H / 2
        painter.setBrush(QColor(PILL_BG))
        painter.setPen(QPen(QColor(PILL_BORDER), 1))
        painter.drawRoundedRect(pill.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)

        self._paint_mark(painter, QPointF(pill.left() + 22, pill.center().y()))
        bars = QRectF(
            pill.left() + 40, pill.center().y() - self.BARS_H / 2, self.BARS_W, self.BARS_H
        )
        painter.setFont(self._time_font)
        if self._state == "done":
            # The words replace the bars: "Pasted" beside the check.
            painter.setPen(QColor(PILL_TEXT))
            text_rect = QRectF(bars.left(), pill.top(), pill.right() - 16 - bars.left(), pill.height())
            painter.drawText(
                text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._done_text
            )
            return
        self._paint_bars(painter, bars)
        painter.setPen(QColor(PILL_DIM if self._state == "processing" else PILL_TEXT))
        text_rect = QRectF(bars.right() + 8, pill.top(), 0, pill.height())
        text_rect.setRight(pill.right() - 16)
        painter.drawText(
            text_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.elapsed_text()
        )

    def _paint_bars(self, painter: QPainter, area: QRectF) -> None:
        count = self._bar_count()
        levels = list(self._levels)[-count:]
        levels = [0.0] * (count - len(levels)) + levels
        step = self.BAR + self.GAP
        sweep = (self._now() % self.SWEEP_MS) / self.SWEEP_MS
        sweeping = self._state == "processing" and not reduced_motion()
        ink = QColor(PILL_TEXT)
        painter.setPen(Qt.PenStyle.NoPen)
        for index, level in enumerate(levels):
            alpha = 0.95 if self._state == "recording" else 0.35
            if sweeping:
                distance = abs(index / max(1, count - 1) - sweep)
                alpha += max(0.0, 0.55 * (1 - distance / 0.14))
            ink.setAlphaF(min(1.0, alpha))
            painter.setBrush(ink)
            height = max(2.5, level * area.height())
            painter.drawRoundedRect(
                QRectF(area.left() + index * step, area.center().y() - height / 2, self.BAR, height),
                self.BAR / 2,
                self.BAR / 2,
            )

    def _paint_mark(self, painter: QPainter, center: QPointF) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        if self._state == "recording":
            painter.setBrush(QColor(255, 106, 87, 60))
            painter.drawEllipse(center, 8.0, 8.0)
            painter.setBrush(QColor(PILL_RECORD))
            painter.drawEllipse(center, 4.5, 4.5)
        elif self._state == "processing":
            angle = 0.0 if reduced_motion() else (self._now() / self.TURN_MS * 360.0) % 360.0
            ring = QRectF(center.x() - 6, center.y() - 6, 12, 12)
            pen = QPen(QColor(127, 214, 190, 64), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(ring)
            pen.setColor(QColor(PILL_OK))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(ring, int((90 - angle) * 16), -90 * 16)
        elif self._state == "done":
            painter.setBrush(QColor(PILL_OK))
            painter.drawEllipse(center, 8.5, 8.5)
            pen = QPen(QColor(PILL_ON_OK), 2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            path = QPainterPath()
            path.moveTo(center.x() - 3.6, center.y() + 0.2)
            path.lineTo(center.x() - 1.0, center.y() + 2.8)
            path.lineTo(center.x() + 3.8, center.y() - 2.5)
            painter.drawPath(path)


# The legacy window and older callers know the pill by this name.
RecordingOverlay = DictationPill

__all__ = ["DictationPill", "RecordingOverlay"]
