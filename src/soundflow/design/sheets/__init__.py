"""Stylesheet fragments, one per area of the app.

:func:`soundflow.design.theme.stylesheet` joins them in this order and fills
in the colour tokens, so later areas can refine base rules.
"""

from . import auth, base, dictation, history, playground, preferences

SHEETS = (
    base.SHEET,
    dictation.SHEET,
    history.SHEET,
    playground.SHEET,
    preferences.SHEET,
    auth.SHEET,
)

__all__ = ["SHEETS"]
