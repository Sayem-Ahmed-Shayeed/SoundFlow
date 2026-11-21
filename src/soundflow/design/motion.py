"""Shared, non-blocking motion feedback for standard controls."""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    Qt,
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QPushButton,
)

from .spacing import ANIMATION_FAST


class ButtonMotionFilter(QObject):
    """Give enabled push buttons brief opacity recovery after activation."""

    def __init__(self, application: QApplication) -> None:
        super().__init__(application)
        self._animations: dict[QPushButton, QPropertyAnimation] = {}
        self._effects: dict[QPushButton, QGraphicsOpacityEffect] = {}

    def animation_for(
        self,
        button: QPushButton,
    ) -> QPropertyAnimation | None:
        return self._animations.get(button)

    def eventFilter(self, watched, event) -> bool:
        if not isinstance(watched, QPushButton) or not watched.isEnabled():
            return False

        activate = False
        if event.type() == QEvent.Type.MouseButtonRelease:
            activate = (
                event.button() == Qt.MouseButton.LeftButton
                and watched.rect().contains(event.position().toPoint())
            )
        elif event.type() == QEvent.Type.KeyRelease:
            activate = (
                not event.isAutoRepeat()
                and event.key()
                in {
                    Qt.Key.Key_Space,
                    Qt.Key.Key_Return,
                    Qt.Key.Key_Enter,
                }
            )

        if activate:
            self._animate(watched)
        return False

    def _animate(self, button: QPushButton) -> None:
        current_effect = button.graphicsEffect()
        known_effect = self._effects.get(button)
        if current_effect is not None and current_effect is not known_effect:
            return
        self._clear_button(button)

        effect = QGraphicsOpacityEffect(button)
        effect.setOpacity(0.72)
        button.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(ANIMATION_FAST)
        animation.setStartValue(0.72)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._effects[button] = effect
        self._animations[button] = animation

        def finish() -> None:
            if self._animations.get(button) is not animation:
                return
            self._animations.pop(button, None)
            self._effects.pop(button, None)
            if button.graphicsEffect() is effect:
                button.setGraphicsEffect(None)
            animation.deleteLater()

        animation.finished.connect(finish)
        button.destroyed.connect(
            lambda _object=None, target=button: self._forget(target)
        )
        animation.start()

    def _clear_button(self, button: QPushButton) -> None:
        animation = self._animations.pop(button, None)
        if animation is not None:
            animation.stop()
            animation.deleteLater()
        effect = self._effects.pop(button, None)
        if effect is not None and button.graphicsEffect() is effect:
            button.setGraphicsEffect(None)

    def _forget(self, button: QPushButton) -> None:
        animation = self._animations.pop(button, None)
        if animation is not None:
            animation.stop()
            animation.deleteLater()
        self._effects.pop(button, None)


def install_button_motion(
    application: QApplication,
) -> ButtonMotionFilter:
    """Install and return the application's singleton button-motion filter."""

    existing = getattr(application, "_soundflow_button_motion", None)
    if isinstance(existing, ButtonMotionFilter):
        return existing
    motion = ButtonMotionFilter(application)
    application.installEventFilter(motion)
    application._soundflow_button_motion = motion
    return motion


__all__ = ["ButtonMotionFilter", "install_button_motion"]


_REDUCED_MOTION: bool | None = None


def reduced_motion() -> bool:
    """True when the desktop asks for fewer animations (GNOME 'Animations' off).

    Set SOUNDFLOW_REDUCED_MOTION=1 to force it. The answer is read once.
    """
    global _REDUCED_MOTION
    if _REDUCED_MOTION is not None:
        return _REDUCED_MOTION
    import os
    import shutil
    import subprocess

    forced = os.environ.get("SOUNDFLOW_REDUCED_MOTION")
    if forced is not None:
        _REDUCED_MOTION = forced.strip() not in {"", "0", "false", "no"}
        return _REDUCED_MOTION
    _REDUCED_MOTION = False
    if shutil.which("gsettings"):
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "enable-animations"],
                capture_output=True, text=True, timeout=0.5,
            )
            _REDUCED_MOTION = result.stdout.strip() == "false"
        except (OSError, subprocess.SubprocessError):
            pass
    return _REDUCED_MOTION


# Strong ease-out for UI state changes: cubic-bezier(0.23, 1, 0.32, 1).
def ease_out(t: float) -> float:
    """Evaluate cubic-bezier(0.23, 1, 0.32, 1) at time fraction ``t``."""
    t = min(max(t, 0.0), 1.0)
    x1, y1, x2, y2 = 0.23, 1.0, 0.32, 1.0
    # Solve x(u) = t for the curve parameter u with Newton steps.
    u = t
    for _ in range(6):
        x = 3 * (1 - u) ** 2 * u * x1 + 3 * (1 - u) * u * u * x2 + u ** 3 - t
        dx = 3 * (1 - u) ** 2 * x1 + 6 * (1 - u) * u * (x2 - x1) + 3 * u * u * (1 - x2)
        if abs(dx) < 1e-6:
            break
        u = min(max(u - x / dx, 0.0), 1.0)
    return 3 * (1 - u) ** 2 * u * y1 + 3 * (1 - u) * u * u * y2 + u ** 3


def ease_out_curve():
    """The strong ease-out token as a QEasingCurve, for QPropertyAnimation."""
    from PySide6.QtCore import QPointF

    curve = QEasingCurve(QEasingCurve.Type.BezierSpline)
    curve.addCubicBezierSegment(QPointF(0.23, 1.0), QPointF(0.32, 1.0), QPointF(1.0, 1.0))
    return curve


def follow(current: float, target: float, dt_ms: float, tau_ms: float) -> float:
    """Move ``current`` toward ``target`` with time constant ``tau_ms``.

    Frame-rate independent, and it retargets mid-flight, so hover, press and
    audio levels can change direction at any moment without a jump.
    """
    import math

    if tau_ms <= 0.0:
        return target
    return target + (current - target) * math.exp(-max(0.0, dt_ms) / tau_ms)
