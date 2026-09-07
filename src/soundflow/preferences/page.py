"""Preferences page embedded in the main Soundflow shell."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider,
    QStackedWidget, QVBoxLayout, QWidget,
)

from soundflow.design import BODY_FONT, DISPLAY_FONT, FONT_BODY, FONT_TITLE
from soundflow.preferences.tabs import (
    AiPolishTab,
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
        subtitle = QLabel(
            "Tune recognition, behavior, shortcuts, privacy, and system readiness."
        )
        subtitle.setObjectName("mutedText")
        subtitle.setFont(QFont(BODY_FONT, FONT_BODY))
        layout.addWidget(subtitle)
        body = QHBoxLayout()
        body.setSpacing(14)
        nav = QVBoxLayout()
        nav.setSpacing(4)
        nav_holder = QWidget()
        nav_holder.setFixedWidth(190)
        nav_holder.setLayout(nav)
        self.tabs = QStackedWidget()
        self.tabs.setObjectName("preferencesTabs")
        self.general_tab = GeneralTab(settings)
        self.dictation_tab = DictationTab(settings)
        self.dictation_tab.model_path_changed.connect(self._persist_model_path)
        self._tab_widgets = [
            self.general_tab,
            self.dictation_tab,
            PlaybackTab(settings),
            ShortcutsTab(settings),
            AiPolishTab(settings),
            SystemTab(settings),
        ]
        self._nav_buttons: list[QPushButton] = []
        for index, (widget, label) in enumerate(
            zip(
                self._tab_widgets,
                ("General", "Dictation", "Playback", "Shortcuts", "AI Polish", "System"),
            )
        ):
            self.tabs.addWidget(widget)
            button = QPushButton(label)
            button.setObjectName("prefsNavButton")
            button.setProperty("active", False)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, target=index: self._select_section(target)
            )
            self._nav_buttons.append(button)
            nav.addWidget(button)
        nav.addStretch(1)
        self.system_tab = self._tab_widgets[-1]
        body.addWidget(nav_holder)
        body.addWidget(self.tabs, 1)
        layout.addLayout(body, 1)
        self._select_section(1)
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
        self.general_tab.appearance_changed.connect(self._queue_save)

    def _select_section(self, index: int) -> None:
        self.tabs.setCurrentIndex(index)
        for position, button in enumerate(self._nav_buttons):
            button.setProperty("active", position == index)
            button.style().unpolish(button)
            button.style().polish(button)

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

    def _persist_model_path(self, path: str) -> None:
        self._save_timer.stop()
        self.dictation_tab._model.setText(path)
        self.save()

    def refresh_from_settings(self) -> None:
        for widget in self._tab_widgets:
            refresh = getattr(widget, "refresh_from_settings", None)
            if callable(refresh):
                refresh(self._settings)

    def shutdown(self) -> None:
        self.dictation_tab.shutdown()


__all__ = ["PreferencesPage"]
