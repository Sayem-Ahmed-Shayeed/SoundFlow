"""Preferences dialog — General / Dictation / Playback / Shortcuts / System.

The dialog is intentionally thin: each tab is a separate widget that
reads from and writes back into a :class:`Settings` instance.
"""

from soundflow.preferences.about_card import AboutCard
from soundflow.preferences.dialog import PreferencesDialog

__all__ = ["AboutCard", "PreferencesDialog"]