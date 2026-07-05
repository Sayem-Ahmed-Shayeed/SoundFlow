"""Preferences page embedded in the main Soundflow shell."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QSlider,
    QTabWidget, QVBoxLayout, QWidget,
)

from soundflow.design import DISPLAY_FONT, FONT_TITLE
from soundflow.preferences.about_card import AboutCard
from soundflow.preferences.tabs import (
    DictationTab,
    GeneralTab,
    PlaybackTab,
    ShortcutsTab,
    SystemTab,
)


class PreferencesPage(QWidget):
    settings_saved = Signal()

    def __init__(self, settings, store, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("preferencesPage")
        self._settings = settings
        self._store = store
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)
        title = QLabel("Preferences")
        title.setObjectName("displayText")
        title.setFont(QFont(DISPLAY_FONT, FONT_TITLE))
        layout.addWidget(title)
        body = QHBoxLayout()
        body.setSpacing(14)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("preferencesTabs")
        self._tab_widgets = [
            GeneralTab(settings),
            DictationTab(settings),
            PlaybackTab(settings),
            ShortcutsTab(settings),
            SystemTab(settings),
        ]
        self.system_tab = self._tab_widgets[-1]
        for widget, label in zip(
            self._tab_widgets,
            ("General", "Dictation", "Playback", "Shortcuts", "System"),
        ):
            self.tabs.addTab(widget, label)
        body.addWidget(self.tabs, 1)
        self.about_card = AboutCard()
        self.about_card.check_system_clicked.connect(self.system_tab.run_check)
        body.addWidget(self.about_card)
        layout.addLayout(body, 1)
        saved = QLabel("✓  Changes are saved automatically")
        saved.setObjectName("savedStatus")
        layout.addWidget(saved)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(120)
        self._save_timer.timeout.connect(self.save)
        for combo in self.findChildren(QComboBox):
            combo.currentIndexChanged.connect(self._queue_save)
        for checkbox in self.findChildren(QCheckBox):
            checkbox.toggled.connect(self._queue_save)
        for slider in self.findChildren(QSlider):
            slider.valueChanged.connect(self._queue_save)
        for line_edit in self.findChildren(QLineEdit):
            line_edit.editingFinished.connect(self._queue_save)

    def _queue_save(self, *args) -> None:
        del args
        self._save_timer.start()

    def save(self) -> None:
        for widget in self._tab_widgets:
            writer = getattr(widget, "write_back", None)
            if callable(writer):
                writer(self._settings)
        self._settings.normalized()
        self._store.save(self._settings)
        self.settings_saved.emit()


__all__ = ["PreferencesPage"]
