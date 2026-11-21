"""Compatibility widgets retained on the public UI surface."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from soundflow.ui.widgets.segmented import SegmentedControl


class AppearanceSelector(SegmentedControl):
    """Dark or Light. Keeps the original API: ``set_value`` emits by default."""

    def __init__(self, value: str = "dark", parent: QWidget | None = None) -> None:
        super().__init__(
            (("dark", "Dark"), ("light", "Light")),
            value if value in {"light", "dark"} else "dark",
            parent,
            accessible_name="Theme",
        )
        for token, button in self._buttons.items():
            button.setAccessibleName(f"Use {token} appearance")

    def set_value(self, value: str, *, emit: bool = True) -> None:
        super().set_value(value if value in {"light", "dark"} else "dark", emit=emit)
