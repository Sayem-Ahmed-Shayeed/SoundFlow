"""Action handlers for the Playground quick-action cards.

* :class:`InsertTextAction` — copies ``text`` to the clipboard and asks the
  available :class:`TextInjector` to paste at the focused cursor.
* :class:`SmartRewriteAction` — placeholder that always reports the
  feature as disabled.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from soundflow.injector import TextInjector


def format_text(text: str) -> str:
    """Conservatively normalize dictated prose without changing its meaning."""
    value = text.strip()
    if not value:
        return ""
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\s*\n\s*\n+\s*", "\n\n", value)
    value = re.sub(r"\s*\n\s*", " ", value)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = re.sub(r"([.!?])(?=[^\s\n])", r"\1 ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    parts = re.split(r"([.!?]\s+|\n+)", value)
    for index in range(0, len(parts), 2):
        segment = parts[index]
        first = re.search(r"\w", segment, flags=re.UNICODE)
        if first:
            pos = first.start()
            parts[index] = segment[:pos] + segment[pos].upper() + segment[pos + 1 :]
    value = "".join(parts).strip()
    if value and value[-1] not in ".!?।":
        if re.search(r"[A-Za-z]", value):
            value += "."
    return value


def smart_rewrite(text: str) -> str:
    """Remove common spoken fillers, then apply deterministic formatting."""
    value = text.strip()
    if not value:
        return ""
    value = re.sub(
        r"(?i)(?:^|(?<=[,.;!?])\s+)(?:um+|uh+|you know|basically|actually)\s*,?\s*",
        "",
        value,
    )
    value = re.sub(r"(?i),?\s+you know\s*,?\s*", " ", value)
    value = re.sub(r"(?i)\s+actually\s+", " ", value)
    value = re.sub(r"\s*,\s*,+", ", ", value)
    value = re.sub(r",\s*(?=(?:this|that|it|they|we|you|he|she)\b)", " ", value, flags=re.I)
    return format_text(value)


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
    """Deterministic, offline rewrite action."""

    text: str = ""

    def is_available(self) -> bool:
        return bool(self.text.strip())

    def run(self) -> str:
        return smart_rewrite(self.text)


__all__ = [
    "InsertTextAction",
    "SmartRewriteAction",
    "format_text",
    "smart_rewrite",
]
