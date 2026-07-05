"""Preferences dialog — 5-tab redesign with side About card."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from soundflow.design import (
    BODY_FONT,
    DISPLAY_FONT,
    FONT_BODY,
    FONT_HEADING,
    FONT_SMALL,
    FONT_TITLE,
    SPACE_3,
    SPACE_4,
    SPACE_6,
)
from soundflow.preferences.about_card import AboutCard
from soundflow.preferences.tabs import (
    DictationTab,
    GeneralTab,
    PlaybackTab,
    ShortcutsTab,
    SystemTab,
)


_TABS = (
    ("general", "General", GeneralTab),
    ("dictation", "Dictation", DictationTab),
    ("playback", "Playback", PlaybackTab),
    ("shortcuts", "Shortcuts", ShortcutsTab),
    ("system", "System", SystemTab),
)


class PreferencesDialog(QDialog):
    """Top-level preferences dialog."""

    def __init__(
        self,
        settings,
        store=None,
        on_save: Callable[[object], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("preferencesDialog")
        self.setWindowTitle("Preferences")
        self.setMinimumSize(900, 600)
        self._settings = settings
        self._store = store
        self._on_save = on_save

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Top bar with title
        top = QHBoxLayout()
        top.setContentsMargins(SPACE_6, SPACE_6, SPACE_6, 0)
        title = QLabel("Preferences")
        title.setFont(QFont(DISPLAY_FONT, FONT_TITLE))
        title.setObjectName("displayText")
        top.addWidget(title)
        top.addStretch(1)
        outer.addLayout(top)

        # Body: tabs (left) + About card (right)
        body = QHBoxLayout()
        body.setContentsMargins(SPACE_6, SPACE_4, SPACE_6, SPACE_4)
        body.setSpacing(SPACE_6)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("preferencesTabs")
        self._tab_widgets: list[tuple[str, QWidget]] = []
        for key, label, factory in _TABS:
            w = factory(settings)
            self._tab_widgets.append((key, w))
            self._tabs.addTab(w, label)

        body.addWidget(self._tabs, 1)

        self._about = AboutCard()
        body.addWidget(self._about, 0, Qt.AlignmentFlag.AlignTop)
        outer.addLayout(body, 1)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save)
        button_box.rejected.connect(self.reject)
        outer.addWidget(button_box)

    # ------------------------------------------------------------------
    def _save(self) -> None:
        for _, widget in self._tab_widgets:
            write = getattr(widget, "write_back", None)
            if callable(write):
                write(self._settings)
        self._settings.normalized()
        if self._store is not None:
            self._store.save(self._settings)
        if self._on_save is not None:
            self._on_save(self._settings)
        self.accept()


__all__ = ["PreferencesDialog"]