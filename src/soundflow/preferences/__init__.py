"""Preferences dialog — General / Dictation / Playback / Shortcuts / System.

The dialog is intentionally thin: each tab is a separate widget that
reads from and writes back into a :class:`Settings` instance.
"""

try:
    from soundflow.preferences.dialog import PreferencesDialog
    from soundflow.preferences.page import PreferencesPage
except ImportError as exc:
    if "PySide6" not in str(exc):
        raise
    PreferencesDialog = PreferencesPage = None

__all__ = ["PreferencesDialog", "PreferencesPage"]
