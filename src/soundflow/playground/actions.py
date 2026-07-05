"""Action handlers for the Playground quick-action cards.

* :class:`InsertTextAction` — copies ``text`` to the clipboard and asks the
  available :class:`TextInjector` to paste at the focused cursor.
* :class:`SmartRewriteAction` — placeholder that always reports the
  feature as disabled.
"""

from __future__ import annotations

from dataclasses import dataclass

from soundflow.injector import TextInjector


@dataclass
class InsertTextAction:
    """Paste ``text`` at the focused cursor using the given injector."""

    text: str
    injector: TextInjector | None = None

    def is_available(self) -> bool:
        return bool(self.text) and self.injector is not None

    def run(self) -> bool:
        if not self.is_available():
            return False
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.text)
        self.injector.paste()
        return True


@dataclass
class SmartRewriteAction:
    """Stub — full rewrite is not yet implemented."""

    text: str = ""

    def is_available(self) -> bool:
        return False

    def run(self) -> bool:
        return False


__all__ = ["InsertTextAction", "SmartRewriteAction"]