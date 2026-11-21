"""Record control: an audio-reactive orb flanked by a mirrored waveform.

The waveform is the one expressive element in the app. The newest audio
level sits next to the button and older levels travel outward, so speech
reads as sound leaving the microphone.

Visual states:

* ``idle`` - violet button with a microphone and low resting bars. Hover
  lifts a soft glow; pressing sinks the button.
* ``recording`` - red button with a stop square inside a living orb whose
  edge moves with your voice. Bars run red near the button to violet at
  the ends.
* ``draining`` - quiet button with three pulsing dots and a comet ring
  orbiting it while the model works.
* ``success`` - after a transcript lands: green button and a check that
  draws in, then it settles back to idle.

Motion budget (used tens of times a day; purpose: feedback and state):

* State changes crossfade colours and glyphs for 160 ms on the strong
  ease-out token, starting from whatever is on screen, so rapid toggles
  retarget instead of jumping.
* Starting with a mouse click adds a 400 ms ripple and a pulse that runs
  out along the bars. Keyboard and shortcut starts skip it: they happen
  many times a day and should feel instant.
* Hover, press and levels follow their targets exponentially, so they can
  change direction at any moment.
* Reduced motion keeps the colour changes and the level meter, and drops
  the ripple, the moving orb edge and the orbiting ring.
* The frame timer only runs while something moves; idle and hidden
  widgets cost nothing.
"""

from __future__ import annotations

import math
from collections import deque
from itertools import pairwise

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from soundflow.design.icons import icon_pixmap
from soundflow.design.motion import ease_out, follow, reduced_motion
from soundflow.design.spacing import ANIMATION_CONTROL
from soundflow.design.theme import palette

_STATES = {"idle", "recording", "draining"}


def _mix(a: QColor, b: QColor, t: float) -> QColor:
    return QColor.fromRgbF(
        a.redF() + (b.redF() - a.redF()) * t,
        a.greenF() + (b.greenF() - a.greenF()) * t,
        a.blueF() + (b.blueF() - a.blueF()) * t,
        a.alphaF() + (b.alphaF() - a.alphaF()) * t,
    )


def _faded(color: QColor, alpha: float) -> QColor:
    result = QColor(color)
    result.setAlphaF(max(0.0, min(1.0, color.alphaF() * alpha)))
    return result


class WaveformRing(QWidget):
    """Round record button inside a voice orb, flanked by a waveform."""

    BAR_COUNT = 64
    FRAME_MS = 16
    BUTTON_RADIUS = 34
    BAR_WIDTH = 3
    BAR_GAP = 4
    CROSSFADE_MS = ANIMATION_CONTROL
    RIPPLE_MS = 400
    RIPPLE_STAGGER_MS = 110
    CHECK_DRAW_MS = 220
    SUCCESS_HOLD_MS = 900
    CLICK_WINDOW_MS = 600
    ORB_POINTS = 96

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("waveformRing")
        self.setMinimumSize(420, 200)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        self._levels: deque[float] = deque([0.0] * self.BAR_COUNT, maxlen=self.BAR_COUNT)
        self._heights: list[float] = []
        self._bars_moving = False
        self._state = "idle"
        self._visual = "idle"
        self._prev_visual = "idle"
        self._phase = 0.0
        self._latest = 0.0
        self._env = 0.0
        self._hover = False
        self._hover_t = 0.0
        self._pressed = False
        self._press_t = 0.0
        self._armed_at = -1e9
        self._fade_from: tuple[QColor, QColor, QColor] | None = None
        self._fade_started = -1e9
        self._ripple_started: float | None = None
        self._success_started: float | None = None

        self._clock = QElapsedTimer()
        self._clock.start()
        self._last_frame = 0.0
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(self.FRAME_MS)
        self._timer.timeout.connect(self._tick)

    # -- public API -------------------------------------------------------------
    def set_state(self, state: str) -> None:
        if state not in _STATES:
            state = "idle"
        if state == self._state:
            return
        now = self._now()
        clicked = now - self._armed_at < self.CLICK_WINDOW_MS
        self._armed_at = -1e9
        self._state = state
        self._success_started = None
        if state == "recording":
            self._latest = 0.0
            if clicked and not reduced_motion():
                self._ripple_started = now
        self._set_visual(state)

    def push_level(self, level: float) -> None:
        if self._state == "recording":
            value = max(0.0, min(1.0, float(level)))
            self._levels.append(value)
            self._latest = value
            self._wake()

    def flash_success(self) -> None:
        """Briefly show a check after a transcript lands, then settle to idle."""
        if self._state != "idle":
            return
        self._success_started = self._now()
        self._set_visual("success")

    def release_press(self) -> None:
        """Lift the button; the page consumes the release to toggle dictation."""
        if self._pressed:
            self._pressed = False
            self._wake()

    # -- timing -------------------------------------------------------------------
    def _now(self) -> float:
        return float(self._clock.elapsed())

    def _set_visual(self, visual: str) -> None:
        if visual == self._visual:
            self._wake()
            return
        if reduced_motion():
            self._fade_from = None
        else:
            self._fade_from = self._colors(self._fade_t())
            self._fade_started = self._now()
        self._prev_visual = self._visual
        self._visual = visual
        self._wake()

    def _fade_t(self) -> float:
        if self._fade_from is None:
            return 1.0
        return ease_out((self._now() - self._fade_started) / self.CROSSFADE_MS)

    def _weight(self, visual: str, t: float) -> float:
        """How much of ``visual`` is on screen during a crossfade."""
        weight = t if self._visual == visual else 0.0
        if self._fade_from is not None and self._prev_visual == visual:
            weight += 1.0 - t
        return weight

    def _needs_frames(self) -> bool:
        if not self.isVisible():
            return False
        if self._state in {"recording", "draining"}:
            return True
        if self._fade_from is not None:
            return True
        if self._ripple_started is not None or self._success_started is not None:
            return True
        if abs(self._hover_t - (1.0 if self._hover else 0.0)) > 0.002:
            return True
        if abs(self._press_t - (1.0 if self._pressed else 0.0)) > 0.002:
            return True
        return self._env > 0.002 or self._bars_moving

    def _wake(self) -> None:
        self._sync_timer()
        self.update()

    def _sync_timer(self) -> None:
        if self._needs_frames():
            if not self._timer.isActive():
                self._last_frame = self._now()
                self._timer.start()
        else:
            self._timer.stop()

    def _tick(self) -> None:
        now = self._now()
        dt = min(50.0, max(0.0, now - self._last_frame))
        self._last_frame = now
        self._phase += dt / 1000.0

        if self._fade_from is not None and now - self._fade_started >= self.CROSSFADE_MS:
            self._fade_from = None
        if (
            self._ripple_started is not None
            and now - self._ripple_started >= self.RIPPLE_MS + self.RIPPLE_STAGGER_MS
        ):
            self._ripple_started = None
        if (
            self._success_started is not None
            and now - self._success_started >= self.SUCCESS_HOLD_MS
        ):
            self._success_started = None
            self._set_visual("idle")

        self._hover_t = self._settle(
            follow(self._hover_t, 1.0 if self._hover else 0.0, dt, 45.0),
            1.0 if self._hover else 0.0,
        )
        self._press_t = self._settle(
            follow(self._press_t, 1.0 if self._pressed else 0.0, dt, 30.0),
            1.0 if self._pressed else 0.0,
        )

        recording = self._state == "recording"
        target = self._latest if recording else 0.0
        self._env = self._settle(
            follow(self._env, target, dt, 50.0 if target > self._env else 160.0), target
        )
        if not recording:
            decay = math.exp(-dt / 80.0)
            for i, value in enumerate(self._levels):
                self._levels[i] = value * decay if value > 0.002 else 0.0

        self._update_bars(dt, now)
        self.update()
        self._sync_timer()

    @staticmethod
    def _settle(value: float, target: float) -> float:
        return target if abs(value - target) < 0.002 else value

    # -- bars -----------------------------------------------------------------------
    def _bar_layout(self) -> tuple[float, float, int, float]:
        radius = float(self.BUTTON_RADIUS)
        step = float(self.BAR_WIDTH + self.BAR_GAP)
        start = radius + 38.0
        reach = min(self.width() / 2.0 - start - 8.0, 300.0)
        count = max(0, int(reach // step))
        return start, step, count, self.height() * 0.6

    def _bar_targets(self, count: int, max_height: float, now: float) -> list[float]:
        recent = self._levels
        size = len(recent)
        launch = None if self._ripple_started is None else now - self._ripple_started
        targets = []
        for i in range(count):
            # Bars further out show older audio and shrink with distance.
            level = recent[size - 1 - i] if i < size else 0.0
            taper = 1.0 - (i / max(count, 1)) ** 1.6
            if launch is not None:
                # The click sends one pulse out along the bars.
                d = (launch - i * 7.0) / 55.0
                level += 0.4 * taper * math.exp(-d * d)
            rest = 4.0 + 3.0 * taper * (0.5 + 0.5 * math.cos(i * 0.9))
            targets.append(max(rest, 4.0 + level * max_height * (0.35 + 0.65 * taper)))
        return targets

    def _update_bars(self, dt: float, now: float) -> None:
        _start, _step, count, max_height = self._bar_layout()
        targets = self._bar_targets(count, max_height, now)
        if len(self._heights) != count:
            self._heights = list(targets)
        moving = False
        for i, target in enumerate(targets):
            current = self._heights[i]
            value = follow(current, target, dt, 35.0 if target > current else 90.0)
            if abs(value - target) < 0.4:
                value = target
            else:
                moving = True
            self._heights[i] = value
        self._bars_moving = moving or any(v > 0.002 for v in self._levels)

    # -- input ----------------------------------------------------------------------
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._armed_at = self._now()
            self._wake()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self.release_press()
        super().mouseReleaseEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._sync_timer()

    def hideEvent(self, event) -> None:  # noqa: N802
        super().hideEvent(event)
        self._timer.stop()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self._wake()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self._pressed = False
        self._wake()
        super().leaveEvent(event)

    # -- colours --------------------------------------------------------------------
    def _is_dark(self) -> bool:
        appearance = self.window().property("darkAppearance")
        if appearance is not None:
            return bool(appearance)
        return self.palette().color(self.palette().ColorRole.Window).lightness() < 128

    def _target_colors(self) -> tuple[QColor, QColor, QColor]:
        """(bar colour by the button, bar colour at the ends, button fill)."""
        colors = palette(self._is_dark())
        if self._visual == "recording":
            return QColor(colors["record"]), QColor(colors["accent"]), QColor(colors["record"])
        if self._visual == "draining":
            accent = QColor(colors["accent"])
            return accent, accent, QColor(colors["surface_active"])
        rest = QColor(colors["border_strong"])
        if self._visual == "success":
            return rest, rest, QColor(colors["success"])
        fill = _mix(QColor(colors["accent"]), QColor(colors["accent_hover"]), self._hover_t)
        return rest, rest, fill

    def _colors(self, t: float) -> tuple[QColor, QColor, QColor]:
        target = self._target_colors()
        if self._fade_from is None or t >= 1.0:
            return target
        return tuple(_mix(a, b, t) for a, b in zip(self._fade_from, target))  # type: ignore[return-value]

    # -- painting -------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        del event
        colors = palette(self._is_dark())
        now = self._now()
        reduce = reduced_motion()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        cx, cy = self.width() / 2.0, self.height() / 2.0
        center = QPointF(cx, cy)
        radius = float(self.BUTTON_RADIUS)
        t = self._fade_t()
        near, far, fill = self._colors(t)
        recording_w = self._weight("recording", t)
        draining_w = self._weight("draining", t)
        idle_w = self._weight("idle", t)

        self._paint_bars(painter, cx, cy, near, far, now)

        record = QColor(colors["record"])
        accent = QColor(colors["accent"])
        env = self._env

        # Glow behind the button: red while listening, violet on hover.
        if recording_w > 0.0:
            self._paint_glow(
                painter, center, radius + 46.0 + env * 34.0,
                _faded(record, 0.30 * recording_w * (0.55 + 0.45 * env)),
            )
        if idle_w > 0.0 and self._hover_t > 0.0:
            self._paint_glow(painter, center, radius + 26.0,
                             _faded(accent, 0.22 * self._hover_t * idle_w))

        if recording_w > 0.0:
            if reduce:
                ring = radius + 6.0 + env * 14.0
                painter.setBrush(_faded(record, 0.18 * recording_w))
                painter.drawEllipse(center, ring, ring)
            else:
                self._paint_orb(painter, cx, cy, radius, record, accent, recording_w)

        self._paint_ripple(painter, center, radius, record, now)

        if draining_w > 0.0:
            self._paint_orbit(painter, center, radius + 9.0, accent, draining_w, reduce)

        # Button, sunk slightly while pressed.
        painter.save()
        painter.translate(cx, cy)
        scale = 1.0 - 0.06 * self._press_t
        painter.scale(scale, scale)
        painter.setBrush(fill)
        painter.drawEllipse(QPointF(0.0, 0.0), radius, radius)
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(accent, 2))
            painter.drawEllipse(QPointF(0.0, 0.0), radius + 4.0, radius + 4.0)
            painter.setPen(Qt.PenStyle.NoPen)
        for visual in ("idle", "recording", "draining", "success"):
            weight = self._weight(visual, t)
            if weight > 0.01:
                self._paint_glyph(painter, visual, weight, colors, now, reduce)
        painter.restore()
        painter.end()

    def _paint_bars(
        self, painter: QPainter, cx: float, cy: float, near: QColor, far: QColor, now: float
    ) -> None:
        start, step, count, max_height = self._bar_layout()
        if len(self._heights) != count:
            self._heights = self._bar_targets(count, max_height, now)
        for i in range(count):
            taper = 1.0 - (i / max(count, 1)) ** 1.6
            height = self._heights[i]
            color = _mix(near, far, i / max(count - 1, 1))
            painter.setBrush(_faded(color, 0.25 + 0.75 * taper))
            offset = start + i * step
            for x in (cx - offset - self.BAR_WIDTH, cx + offset):
                painter.drawRoundedRect(
                    QRectF(x, cy - height / 2.0, self.BAR_WIDTH, height), 1.5, 1.5
                )

    @staticmethod
    def _paint_glow(painter: QPainter, center: QPointF, reach: float, color: QColor) -> None:
        gradient = QRadialGradient(center, reach)
        gradient.setColorAt(0.0, color)
        gradient.setColorAt(0.45, color)
        gradient.setColorAt(1.0, _faded(color, 0.0))
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(center, reach, reach)

    def _paint_orb(
        self,
        painter: QPainter,
        cx: float,
        cy: float,
        radius: float,
        record: QColor,
        accent: QColor,
        weight: float,
    ) -> None:
        """Three soft layers whose edges ripple with the voice."""
        env = self._env
        phase = self._phase
        layers = (
            (record, 0.30, 1.0, 0.0),
            (accent, 0.24, -0.8, 2.1),
            (_mix(record, accent, 0.5), 0.18, 1.3, 4.2),
        )
        points = self.ORB_POINTS
        for k, (color, alpha, speed, offset) in enumerate(layers):
            base = radius + 5.0 + k * 2.5 + env * (9.0 + k * 3.0)
            amplitude = (1.2 + env * 8.5) * (1.0 - k * 0.15)
            path = QPainterPath()
            for j in range(points + 1):
                theta = 2.0 * math.pi * j / points
                noise = (
                    0.55 * math.sin(3.0 * theta + phase * 1.6 * speed + offset)
                    + 0.30 * math.sin(5.0 * theta - phase * 1.1 * speed + offset * 1.7)
                    + 0.15 * math.sin(7.0 * theta + phase * 2.3)
                )
                r = base + amplitude * noise
                point = QPointF(cx + r * math.cos(theta), cy + r * math.sin(theta))
                if j == 0:
                    path.moveTo(point)
                else:
                    path.lineTo(point)
            path.closeSubpath()
            painter.setBrush(_faded(color, alpha * weight))
            painter.drawPath(path)

    def _paint_ripple(
        self, painter: QPainter, center: QPointF, radius: float, color: QColor, now: float
    ) -> None:
        if self._ripple_started is None:
            return
        elapsed = now - self._ripple_started
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for delay in (0.0, float(self.RIPPLE_STAGGER_MS)):
            progress = (elapsed - delay) / self.RIPPLE_MS
            if not 0.0 <= progress < 1.0:
                continue
            eased = ease_out(progress)
            ring = radius + 4.0 + eased * 78.0
            painter.setPen(QPen(_faded(color, 0.45 * (1.0 - progress) ** 1.5), 2.0 - eased))
            painter.drawEllipse(center, ring, ring)
        painter.setPen(Qt.PenStyle.NoPen)

    def _paint_orbit(
        self,
        painter: QPainter,
        center: QPointF,
        ring: float,
        accent: QColor,
        weight: float,
        reduce: bool,
    ) -> None:
        """A comet circling the button while the model works."""
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(_faded(accent, 0.12 * weight), 3))
        painter.drawEllipse(center, ring, ring)
        if reduce:
            breathe = 0.5 + 0.5 * math.sin(self._phase * 2.0 * math.pi * 0.6)
            painter.setPen(QPen(_faded(accent, (0.25 + 0.3 * breathe) * weight), 3))
            painter.drawEllipse(center, ring, ring)
        else:
            gradient = QConicalGradient(center, (-self._phase * 300.0) % 360.0)
            gradient.setColorAt(0.0, _faded(accent, weight))
            gradient.setColorAt(0.6, _faded(accent, 0.0))
            gradient.setColorAt(1.0, _faded(accent, 0.0))
            pen = QPen(QBrush(gradient), 3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawEllipse(center, ring, ring)
        painter.setPen(Qt.PenStyle.NoPen)

    def _paint_glyph(
        self,
        painter: QPainter,
        visual: str,
        weight: float,
        colors: dict[str, str],
        now: float,
        reduce: bool,
    ) -> None:
        """Draw one state's glyph at the button centre; glyphs crossfade."""
        painter.save()
        grow = 0.82 + 0.18 * weight
        painter.scale(grow, grow)
        painter.setOpacity(weight)
        white = QColor("#FFFFFF")
        if visual == "recording":
            painter.setBrush(white)
            painter.drawRoundedRect(QRectF(-9.0, -9.0, 18.0, 18.0), 4.0, 4.0)
        elif visual == "draining":
            dot = QColor(colors["accent_text"])
            for k in range(3):
                if reduce:
                    level = 0.8
                else:
                    wave = math.sin(self._phase * 2.0 * math.pi * 1.2 - k * 0.9)
                    level = 0.35 + 0.65 * (0.5 + 0.5 * wave)
                painter.setBrush(_faded(dot, level))
                painter.drawEllipse(QPointF((k - 1) * 9.0, 0.0), 2.6, 2.6)
        elif visual == "success":
            progress = 1.0
            if self._success_started is not None and not reduce:
                progress = ease_out((now - self._success_started) / self.CHECK_DRAW_MS)
            self._paint_check(painter, white, progress)
        else:
            painter.drawPixmap(QPointF(-14.0, -14.0), icon_pixmap("mic", "#FFFFFF", 28))
        painter.restore()

    @staticmethod
    def _paint_check(painter: QPainter, color: QColor, progress: float) -> None:
        points = (QPointF(-8.5, 0.5), QPointF(-2.5, 6.5), QPointF(9.0, -6.0))
        lengths = [
            math.dist((a.x(), a.y()), (b.x(), b.y())) for a, b in pairwise(points)
        ]
        remaining = progress * sum(lengths)
        path = QPainterPath(points[0])
        for (a, b), length in zip(pairwise(points), lengths, strict=True):
            if remaining <= 0.0:
                break
            share = min(1.0, remaining / length)
            path.lineTo(a + (b - a) * share)
            remaining -= length
        pen = QPen(color, 3.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        painter.setPen(Qt.PenStyle.NoPen)


__all__ = ["WaveformRing"]
