"""Compatibility widgets retained on the public UI surface."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QWidget


class AppearanceSelector(QFrame):
    changed = Signal(str)

    def __init__(self, value: str = "dark", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("segmentedControl")
        self._value = value if value in {"system", "light", "dark"} else "dark"
        self._buttons: dict[str, QPushButton] = {}
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        for label, token in (
            ("System", "system"),
            ("Light", "light"),
            ("Dark", "dark"),
        ):
            button = QPushButton(label)
            button.setCheckable(True)
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
