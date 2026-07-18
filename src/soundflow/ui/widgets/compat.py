"""Compatibility widgets retained on the public UI surface."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QWidget

from soundflow.design import CONTROL_HEIGHT_SM


class AppearanceSelector(QFrame):
    changed = Signal(str)

    def __init__(self, value: str = "dark", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("segmentedControl")
        self._value = value if value in {"light", "dark"} else "dark"
        self._buttons: dict[str, QPushButton] = {}
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        for label, token in (("Light", "light"), ("Dark", "dark")):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setFixedHeight(CONTROL_HEIGHT_SM)
            button.setAccessibleName(f"Use {label.lower()} appearance")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, selected=token: self.set_value(selected)
            )
            self._buttons[token] = button
            layout.addWidget(button)
        self.set_value(self._value, emit=False)

    def value(self) -> str:
        return self._value

    def set_value(self, value: str, *, emit: bool = True) -> None:
        value = value if value in self._buttons else "dark"
        changed = value != self._value
        self._value = value
        for token, button in self._buttons.items():
            button.setChecked(token == value)
        if emit and changed:
            self.changed.emit(value)
