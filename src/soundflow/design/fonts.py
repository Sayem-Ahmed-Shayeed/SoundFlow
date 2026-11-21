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


_FONT_FILES = (
    "Figtree-Regular.ttf",
    "Figtree-Medium.ttf",
    "Figtree-SemiBold.ttf",
    "Figtree-Bold.ttf",
    "EBGaramond-Regular.ttf",
    "EBGaramond-Medium.ttf",
    "EBGaramond-Italic.ttf",
    "NotoSansBengali-Variable.ttf",
    "NotoSerifBengali-Regular.ttf",
    "NotoSerifBengali-Medium.ttf",
    "BodoniModa-Medium.ttf",
    "BodoniModa-Italic.ttf",
)


def register_application_fonts() -> tuple[int, ...]:
    """Register the bundled Figtree, EB Garamond, Bodoni Moda and Noto Bengali faces.

    Neither Latin face has Bangla letters, so Noto Sans Bengali is set as its
    substitute: mixed text such as "English or বাংলা" draws each script from
    the face designed for it.
    """

    global _REGISTERED_FONT_IDS
    if _REGISTERED_FONT_IDS is not None:
        return _REGISTERED_FONT_IDS

    try:
        from PySide6.QtGui import QFont, QFontDatabase
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
            for filename in _FONT_FILES
        )
        if font_id >= 0
    )
    # Bangla in headings uses the serif cut, so it sits with EB Garamond.
    QFont.insertSubstitutions(BODY_FONT, [BANGLA_FONT])
    QFont.insertSubstitutions(DISPLAY_FONT, [BANGLA_SERIF_FONT, BANGLA_FONT])
    _REGISTERED_FONT_IDS = font_ids
    return font_ids


def tabular(font):
    """Return *font* with equal-width digits, for timers and counts."""
    from PySide6.QtGui import QFont

    font.setFeature(QFont.Tag("tnum"), 1)
    return font


# Figtree for every interface word; EB Garamond, a book serif, for page
# titles, headings and big numbers. Digits use the tnum feature instead of a
# monospace face.
BODY_FONT = "Figtree"
DISPLAY_FONT = "EB Garamond"
HOME_DISPLAY_FONT = DISPLAY_FONT
MONO_FONT = BODY_FONT
BANGLA_FONT = "Noto Sans Bengali"
BANGLA_SERIF_FONT = "Noto Serif Bengali"
# A high-contrast fashion serif, only for the sign-in window's magazine cover.
COVER_FONT = "Bodoni Moda"

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
