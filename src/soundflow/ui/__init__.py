"""Soundflow UI package — public surface.

This package hosts the redesigned UI (top tab bar, status bar,
Dictation / History / Playground pages, redesigned Preferences).
During the incremental migration the bulk of the widget code still lives
in :mod:`soundflow._legacy.ui_module` and is re-exported from here so
existing call sites (``soundflow.app`` and tests) keep working.

New code should prefer:

* :mod:`soundflow.design` — visual tokens (colours, fonts, spacing, theme).
* :mod:`soundflow.ui.widgets` — small reusable widgets.
* :mod:`soundflow.ui.pages` — top-level pages hosted by ``MainWindow``.
* :mod:`soundflow.preferences` — the redesigned preferences dialog.
"""

from __future__ import annotations

# Load the legacy module under a private name first, then re-export its
# public symbols. Doing it this way avoids a circular import between
# ``soundflow.ui`` (this package) and the legacy ``soundflow.ui`` module
# (which used to be a single file at ``soundflow/ui.py``).
from soundflow._legacy import ui_module as _legacy_module

ShortcutPicker = _legacy_module.ShortcutPicker
UiBridge = _legacy_module.UiBridge
resolved_dark_appearance = _legacy_module.resolved_dark_appearance
macos_style_sheet = _legacy_module.macos_style_sheet
preferred_font = _legacy_module.preferred_font
DISPLAY_FONT = _legacy_module.DISPLAY_FONT
BODY_FONT = _legacy_module.BODY_FONT
MONO_FONT = _legacy_module.MONO_FONT

# Sub-modules for incremental migration
from soundflow.ui import (  # noqa: F401  (re-export submodules)
    widgets as widgets,
)
from soundflow.ui.widgets import AppearanceSelector, RecordingOverlay


def __getattr__(name: str):
    """Load the main window lazily so Preferences may import UI widgets first."""
    if name == "MainWindow":
        from soundflow.ui.main_window import MainWindow

        return MainWindow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BODY_FONT",
    "AppearanceSelector",
    "DISPLAY_FONT",
    "MainWindow",
    "MONO_FONT",
    "RecordingOverlay",
    "ShortcutPicker",
    "UiBridge",
    "macos_style_sheet",
    "preferred_font",
    "resolved_dark_appearance",
]
