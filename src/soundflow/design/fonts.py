"""Font families and helpers.

All fonts are picked at runtime from the set of installed families; the first
candidate that resolves wins. We never rely on a font that is not installed.
"""

from __future__ import annotations


def preferred_font(candidates: tuple[str, ...]) -> str:
    """Return the first installed family from *candidates*.

    Falls back to ``"Sans Serif"`` if the application has not been built yet
    (so the constants are importable without a ``QApplication`` instance) and
    to ``"Sans Serif"`` if no candidate is installed.
    """
    try:
        from PySide6.QtGui import QFontDatabase
        from PySide6.QtWidgets import QApplication
    except ImportError:  # PySide6 not installed (e.g. some unit tests)
        return candidates[-1]
    if QApplication.instance() is None:
        return candidates[-1]
    installed = set(QFontDatabase.families())
    return next((family for family in candidates if family in installed), "Sans Serif")


DISPLAY_FONT = preferred_font(("Lato Heavy", "Lato", "Noto Sans Display", "Segoe UI"))
BODY_FONT = preferred_font(("Lato", "Noto Sans", "Segoe UI", "Cantarell"))
MONO_FONT = preferred_font(
    ("JetBrains Mono", "Cascadia Mono", "Noto Sans Mono", "DejaVu Sans Mono")
)