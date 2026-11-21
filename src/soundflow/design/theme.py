"""Soundflow theme: tokens for both appearances and one stylesheet.

Direction: editorial and calm. Cream paper (or deep green-black) surfaces,
one deep green for focus, links and the dictation card, lavender for the
main button, a live red only while recording. EB Garamond for headings and
big numbers, Figtree for every interface word.

The stylesheet is assembled from one file per area in
:mod:`soundflow.design.sheets`; each uses the ``${token}`` names below.
"""

from __future__ import annotations

from pathlib import Path
from string import Template

from .fonts import BODY_FONT, DISPLAY_FONT, MONO_FONT
from .sheets import SHEETS

# --- Tokens ----------------------------------------------------------------
DARK: dict[str, str] = {
    "canvas": "#0E1412",
    "sidebar": "#0B100E",
    "surface": "#151C19",
    "raised": "#1A2220",
    "surface_hover": "#1C2421",
    "surface_active": "#24302C",
    "field": "#151C19",
    "border": "#222B28",
    "border_strong": "#33403B",
    "text": "#F4F4E2",
    "text2": "#B5B8AA",
    "text3": "#9A9E90",
    "accent": "#7FD6BE",
    "accent_hover": "#9FE3D0",
    "accent_text": "#8FDCC6",
    "accent_soft": "rgba(127, 214, 190, 0.12)",
    "on_accent": "#04211C",
    "primary_bg": "#E2C2FA",
    "primary_hover": "#EDD5FF",
    "primary_text": "#1A1A1A",
    "brand": "#0E5A50",
    "brand_hover": "#167064",
    "on_brand": "#FFFFEB",
    "on_brand2": "#A9CFC4",
    "success": "#7FD6A0",
    "success_soft": "rgba(127, 214, 160, 0.14)",
    "warning": "#F2C14E",
    "warning_soft": "rgba(242, 193, 78, 0.14)",
    "danger": "#FF7A6E",
    "danger_soft": "rgba(255, 122, 110, 0.12)",
    "record": "#FF6A57",
    "record_soft": "rgba(255, 106, 87, 0.16)",
    "scroll": "#33403B",
    "selection": "rgba(127, 214, 190, 0.28)",
    "overlay": "rgba(14, 20, 18, 0.97)",
    "chart_bar": "#7FD6BE",
    "chart_bar_soft": "#234740",
    "heat0": "#1A2220",
    "heat1": "#1D4038",
    "heat2": "#24695B",
    "heat3": "#3C9C86",
    "heat4": "#7FD6BE",
    "spectrum_bg": "#06100D",
    "spectrum_border": "#16231F",
    "spectrum_text": "#8FA39B",
}

LIGHT: dict[str, str] = {
    "canvas": "#FFFFEB",
    "sidebar": "#F7F7E2",
    "surface": "#FFFFFF",
    "raised": "#F1F1DC",
    "surface_hover": "#EDEDD7",
    "surface_active": "#E4E4CE",
    "field": "#FFFFFF",
    "border": "#E4E4D0",
    "border_strong": "#D2D2BC",
    "text": "#1A1A1A",
    "text2": "#55554C",
    "text3": "#6F6F65",
    "accent": "#034F46",
    "accent_hover": "#0B6B5E",
    "accent_text": "#0B6B5E",
    "accent_soft": "rgba(3, 79, 70, 0.10)",
    "on_accent": "#FFFFEB",
    "primary_bg": "#F0D7FF",
    "primary_hover": "#E6C2FF",
    "primary_text": "#1A1A1A",
    "brand": "#034F46",
    "brand_hover": "#0B6B5E",
    "on_brand": "#FFFFEB",
    "on_brand2": "#B9D8CF",
    "success": "#1D7A4D",
    "success_soft": "rgba(29, 122, 77, 0.10)",
    "warning": "#8F6400",
    "warning_soft": "rgba(143, 100, 0, 0.10)",
    "danger": "#C4322D",
    "danger_soft": "rgba(196, 50, 45, 0.10)",
    "record": "#D9412F",
    "record_soft": "rgba(217, 65, 47, 0.12)",
    "scroll": "#D2D2BC",
    "selection": "rgba(3, 79, 70, 0.18)",
    "overlay": "rgba(255, 255, 235, 0.97)",
    "chart_bar": "#034F46",
    "chart_bar_soft": "#CFE3DB",
    "heat0": "#EDEDD7",
    "heat1": "#C9E2D8",
    "heat2": "#8CC2AF",
    "heat3": "#3F8E7C",
    "heat4": "#034F46",
    # The spectrogram keeps a dark field in both themes: it is a picture of
    # sound, like a photo, not a surface.
    "spectrum_bg": "#06100D",
    "spectrum_border": "#16231F",
    "spectrum_text": "#8FA39B",
}


def palette(dark: bool) -> dict[str, str]:
    """Colour tokens for custom-painted widgets."""
    return DARK if dark else LIGHT


# Names other modules import. Values follow the dark appearance.
FG_CREAM = DARK["text"]
FG_MUTED = DARK["text2"]
FG_DIM = DARK["text3"]
BG_BLACK = DARK["canvas"]
BG_PANEL = DARK["surface"]
BG_RAISED = DARK["surface_hover"]
BORDER = DARK["border"]
ACCENT = DARK["accent"]
PINK = DARK["record"]
TEAL = DARK["success"]
AMBER = DARK["warning"]
SKY = "#5AC8FA"
ORCHID = "#C98BBD"
MINT = DARK["success"]
BORDER_FOCUS = ACCENT
SUCCESS = DARK["success"]
WARNING = DARK["warning"]
ERROR = DARK["danger"]
PRIMARY_TEXT = FG_CREAM
PRIMARY_BG = BG_BLACK
SUCCESS_GREEN = SUCCESS


def current_palette() -> dict[str, str]:
    """Tokens for the appearance the running app last applied."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    value = app.property("soundflowDark") if app is not None else None
    return palette(True if value is None else bool(value))


def resolved_dark(appearance: str) -> bool:
    """Only "light" selects the light theme; anything else is dark."""
    if not isinstance(appearance, str):
        return True
    return appearance.strip().lower() != "light"


def _chevron(dark: bool) -> str:
    name = "chevron-down-dark.svg" if dark else "chevron-down-light.svg"
    return (Path(__file__).resolve().parents[1] / "assets" / "icons" / name).as_posix()


def stylesheet(dark: bool) -> str:
    """Return the full Qt stylesheet for the requested appearance."""
    tokens = dict(palette(dark))
    tokens.update(
        body=BODY_FONT,
        display=DISPLAY_FONT,
        mono=MONO_FONT,
        chevron=_chevron(dark),
        model_delete_disabled_text=tokens["text2"],
    )
    return Template("\n".join(SHEETS)).substitute(tokens)


def apply_stylesheet(app, dark: bool) -> None:
    """Switch the whole application to ``dark`` or light, quickly.

    Replacing one application stylesheet with another makes Qt work through
    every widget against both sheets, which takes about 170 ms here. Clearing
    the sheet first and then setting the new one gives the same pixels in
    about 35 ms. Both calls run before the next paint, so nothing flashes.
    """
    sheet = stylesheet(dark)
    if app.styleSheet() == sheet:
        return
    if app.styleSheet():
        app.setStyleSheet("")
    app.setStyleSheet(sheet)


__all__ = [
    "ACCENT",
    "AMBER",
    "BG_BLACK",
    "BG_PANEL",
    "BG_RAISED",
    "BORDER",
    "BORDER_FOCUS",
    "DARK",
    "ERROR",
    "FG_CREAM",
    "FG_DIM",
    "FG_MUTED",
    "LIGHT",
    "MINT",
    "ORCHID",
    "PINK",
    "SKY",
    "SUCCESS",
    "TEAL",
    "WARNING",
    "current_palette",
    "palette",
    "resolved_dark",
    "stylesheet",
]
