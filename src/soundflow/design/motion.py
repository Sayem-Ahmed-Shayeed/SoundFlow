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
