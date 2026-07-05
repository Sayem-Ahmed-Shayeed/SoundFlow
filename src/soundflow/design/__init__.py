"""Design tokens for Soundflow.

This package is the single source of truth for visual constants:

- :mod:`soundflow.design.theme` — colours, appearance resolution, stylesheet generator
- :mod:`soundflow.design.fonts` — preferred font families and helpers
- :mod:`soundflow.design.spacing` — spacing scale, radii, control heights, font sizes

No magic numbers should appear in widget code. Import from this package.
"""

from .fonts import BODY_FONT, DISPLAY_FONT, MONO_FONT, preferred_font
from .spacing import (
    BORDER_FOCUS,
    BORDER_THIN,
    CONTROL_HEIGHT_LG,
    CONTROL_HEIGHT_MD,
    CONTROL_HEIGHT_SM,
    FONT_BODY,
    FONT_DISPLAY,
    FONT_HEADING,
    FONT_SMALL,
    FONT_TINY,
    FONT_TITLE,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    SPACE_0,
    SPACE_1,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_5,
    SPACE_6,
    SPACE_8,
    SPACE_10,
)
from .theme import (
    ACCENT,
    BG_BLACK,
    BG_PANEL,
    BG_RAISED,
    BORDER,
    ERROR,
    FG_CREAM,
    FG_DIM,
    FG_MUTED,
    SUCCESS,
    resolved_dark,
    stylesheet,
)

__all__ = [
    "BODY_FONT",
    "DISPLAY_FONT",
    "MONO_FONT",
    "preferred_font",
    "BORDER_FOCUS",
    "BORDER_THIN",
    "CONTROL_HEIGHT_LG",
    "CONTROL_HEIGHT_MD",
    "CONTROL_HEIGHT_SM",
    "FONT_BODY",
    "FONT_DISPLAY",
    "FONT_HEADING",
    "FONT_SMALL",
    "FONT_TINY",
    "FONT_TITLE",
    "RADIUS_LG",
    "RADIUS_MD",
    "RADIUS_SM",
    "SPACE_0",
    "SPACE_1",
    "SPACE_2",
    "SPACE_3",
    "SPACE_4",
    "SPACE_5",
    "SPACE_6",
    "SPACE_8",
    "SPACE_10",
    "ACCENT",
    "BG_BLACK",
    "BG_PANEL",
    "BG_RAISED",
    "BORDER",
    "ERROR",
    "FG_CREAM",
    "FG_DIM",
    "FG_MUTED",
    "SUCCESS",
    "resolved_dark",
    "stylesheet",
]