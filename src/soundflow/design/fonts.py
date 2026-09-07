"""Font families and helpers.

All fonts are picked at runtime from the set of installed families; the first
candidate that resolves wins. We never rely on a font that is not installed.
"""

from __future__ import annotations

from pathlib import Path


_REGISTERED_FONT_IDS: tuple[int, ...] | None = None


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


def register_application_fonts() -> tuple[int, ...]:
    """Register Soundflow's bundled Geist and Outfit faces with the active Qt app."""

    global _REGISTERED_FONT_IDS
    if _REGISTERED_FONT_IDS is not None:
        return _REGISTERED_FONT_IDS

    try:
        from PySide6.QtGui import QFontDatabase
        from PySide6.QtWidgets import QApplication
    except ImportError:
        return ()
    if QApplication.instance() is None:
        return ()

    font_directory = Path(__file__).resolve().parents[1] / "assets" / "fonts"
    font_ids = tuple(
        font_id
        for font_id in (
            QFontDatabase.addApplicationFont(str(font_directory / filename))
            for filename in (
                "Geist-Regular.ttf",
                "Geist-Medium.ttf",
                "Geist-SemiBold.ttf",
                "Geist-Bold.ttf",
                "GeistMono-Regular.ttf",
                "GeistMono-Medium.ttf",
                "Outfit-Variable.ttf",
            )
        )
        if font_id >= 0
    )
    _REGISTERED_FONT_IDS = font_ids
    return font_ids


DISPLAY_FONT = "Geist"
HOME_DISPLAY_FONT = "Outfit"
BODY_FONT = "Geist"
MONO_FONT = "Geist Mono"

SERIF_CANDIDATES = (
    "Iowan Old Style",
    "Palatino Linotype",
    "Book Antiqua",
    "Palatino",
    "Georgia",
    "Noto Serif",
    "DejaVu Serif",
    "Serif",
)


def serif_font() -> str:
    """Resolve the editorial serif family for page titles at call time."""
    return preferred_font(SERIF_CANDIDATES)
