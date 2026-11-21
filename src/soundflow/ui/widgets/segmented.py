"""Segmented control: a few mutually exclusive options on one raised track."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QPushButton, QWidget


class SegmentedControl(QFrame):
    """Pick one of ``options`` (``(value, label)`` pairs).

    ``changed`` fires only when the user picks a different option, or when
    :meth:`set_value` is called with ``emit=True``.
    """

    changed = Signal(str)

    def __init__(
        self,
        options: list[tuple[str, str]] | tuple[tuple[str, str], ...],
        value: str | None = None,
        parent: QWidget | None = None,
        *,
        accessible_name: str = "",
    ) -> None:
        super().__init__(parent)
        self.setObjectName("segmentedControl")
        if accessible_name:
            self.setAccessibleName(accessible_name)
        self._buttons: dict[str, QPushButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        for token, label in options:
            button = QPushButton(label, self)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setAccessibleName(label)
            button.clicked.connect(lambda _checked=False, v=token: self._picked(v))
            self._group.addButton(button)
            self._buttons[token] = button
            layout.addWidget(button)
        self._value = ""
        first = options[0][0] if options else ""
        self.set_value(value if value in self._buttons else first, emit=False)

    def value(self) -> str:
        return self._value

    def button(self, value: str) -> QPushButton:
        return self._buttons[value]

    def set_value(self, value: str, *, emit: bool = False) -> None:
        if value not in self._buttons:
            return
        changed = value != self._value
        self._value = value
        self._buttons[value].setChecked(True)
        if emit and changed:
            self.changed.emit(value)

    def _picked(self, value: str) -> None:
        self.set_value(value, emit=True)


__all__ = ["SegmentedControl"]
