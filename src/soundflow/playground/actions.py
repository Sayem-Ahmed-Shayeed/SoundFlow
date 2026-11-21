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
    value = re.sub(r"\s+([,.;:!?।])", r"\1", value)
    # Space after a sentence end only when a new sentence clearly starts, so
    # "3.14", "main.py" and "example.com" stay intact.
    value = re.sub(r"([.!?])(?=[A-Z\"'\u201C])", r"\1 ", value)
    value = re.sub(r"(?<=[A-Za-z])([.!?])([a-z]+)", _split_joined_sentence, value)
    value = re.sub(r"(।)(?=\S)", r"\1 ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    parts = re.split(r"([.!?।]\s+|\n+)", value)
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


# Endings that make "word.word" a file name or address, not two sentences.
_NOT_SENTENCES = {
    "com", "org", "net", "io", "dev", "app", "ai", "co", "edu", "gov", "bd", "in",
    "py", "js", "ts", "tsx", "jsx", "md", "txt", "pdf", "json", "html", "css",
    "csv", "doc", "docx", "png", "jpg", "jpeg", "yaml", "yml", "toml", "sh", "rs",
    "go", "java", "cpp", "h", "c", "zip", "mp3", "mp4", "wav", "exe",
}


def _split_joined_sentence(match: re.Match) -> str:
    mark, word = match.group(1), match.group(2)
    if mark == "." and word.lower() in _NOT_SENTENCES:
        return match.group(0)
    return f"{mark} {word}"


def smart_rewrite(text: str) -> str:
    """Remove common spoken fillers, then apply deterministic formatting."""
    value = text.strip()
    if not value:
        return ""
    # Fillers only where they are clearly fillers: sentence-initial, or set
    # off by commas. "Do you know the answer?" keeps its meaning.
    previous = None
    while previous != value:  # "um, basically, ..." needs more than one pass
        previous = value
        value = re.sub(
            r"(?i)(?:^|(?<=[,.;!?।])\s*)(?:um+|uh+|erm+|basically|actually)\b\s*,?\s*",
            "",
            value,
        )
    value = re.sub(r"(?i),\s*(?:you know|i mean|um+|uh+)\s*,", ",", value)
    value = re.sub(r"(?i)\b(?:um+|uh+)\b\s*,?\s*", "", value)
    value = re.sub(r"(?i)\s+actually\s+", " ", value)
    # "I think, this ..." -> "I think this ..." (only after verbs of opinion).
    value = re.sub(
        r"(?i)\b(think|guess|mean|believe|feel|hope),\s*(?=(?:this|that|it|they|we|you|he|she)\b)",
        r"\1 ",
        value,
    )
    value = re.sub(r"\s*,\s*,+", ", ", value)
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
