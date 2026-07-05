"""UI pages — top-level surfaces hosted by ``MainWindow``.

Currently houses the redesigned Dictation page. History and Playground
will be added in subsequent phases; Preferences lives in
:mod:`soundflow.preferences`.
"""

from soundflow.ui.pages.dictation_page import DictationPage

__all__ = ["DictationPage"]