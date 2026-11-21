"""Preferences page embedded in the main Soundflow shell."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from soundflow.core.autostart import set_open_at_login
from soundflow.preferences.tabs import (
    AiPolishTab,
    DictationTab,
    GeneralTab,
    SpeechModelTab,
    SystemTab,
)
from soundflow.preferences.widgets import ChoiceSet, ShortcutRecorder
from soundflow.ui.widgets import SegmentedControl

LOGGER = logging.getLogger(__name__)
# Nav label and the tab shown for it, in order.
SECTIONS = ("General", "Dictation", "Speech model", "AI Polish", "System")


class PreferencesPage(QWidget):
    settings_saved = Signal()
    # The user asked to allow the global shortcut from the System tab.
    shortcut_permission_requested = Signal()

    def __init__(self, settings, store, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("preferencesPage")
        self._settings = settings
        self._store = store
        self._login_applied = bool(settings.open_at_login)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(40, 14, 40, 0)
        outer.setSpacing(0)

        nav_holder = QWidget()
        nav_holder.setObjectName("prefsNav")
        nav_holder.setFixedWidth(204)
        nav = QVBoxLayout(nav_holder)
        nav.setContentsMargins(0, 6, 12, 20)
        nav.setSpacing(2)
        title = QLabel("Preferences")
        title.setObjectName("pageTitle")
        nav.addWidget(title)
        nav.addSpacing(18)

        self.tabs = QStackedWidget()
        self.tabs.setObjectName("preferencesTabs")
        self.general_tab = GeneralTab(settings)
        self.dictation_tab = DictationTab(settings)
        self.model_tab = SpeechModelTab(settings)
        self.ai_tab = AiPolishTab(settings)
        self.system_tab = SystemTab(settings)
        self._tab_widgets = [
            self.general_tab,
            self.dictation_tab,
            self.model_tab,
            self.ai_tab,
            self.system_tab,
        ]
        self._nav_buttons: list[QPushButton] = []
        for index, (widget, label) in enumerate(zip(self._tab_widgets, SECTIONS)):
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

        self.model_tab.model_path_changed.connect(self._persist_model_path)
        self.system_tab.section_requested.connect(self._open_section)
        self.system_tab.shortcut_permission_requested.connect(
            self.shortcut_permission_requested
        )

        outer.addWidget(nav_holder)
        outer.addSpacing(28)
        outer.addWidget(self.tabs, 1)
        self._select_section(0)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(120)
        self._save_timer.timeout.connect(self.save)
        self._connect_autosave()

    def _connect_autosave(self) -> None:
        for combo in self.findChildren(QComboBox):
            # Long device names must not widen the whole page.
            combo.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            combo.setMinimumContentsLength(14)
            combo.currentIndexChanged.connect(self._queue_save)
        for checkbox in self.findChildren(QCheckBox):
            checkbox.toggled.connect(self._queue_save)
        for line_edit in self.findChildren(QLineEdit):
            line_edit.editingFinished.connect(self._queue_save)
        for text_edit in self.findChildren(QTextEdit):
            text_edit.textChanged.connect(self._queue_save)
        for segmented in self.findChildren(SegmentedControl):
            segmented.changed.connect(self._queue_save)
        for choice in self.findChildren(ChoiceSet):
            choice.changed.connect(self._queue_save)
        for recorder in self.findChildren(ShortcutRecorder):
            recorder.changed.connect(self._queue_save)
        self.general_tab.appearance_changed.connect(self._queue_save)

    def _select_section(self, index: int) -> None:
        self.tabs.setCurrentIndex(index)
        for position, button in enumerate(self._nav_buttons):
            button.setProperty("active", position == index)
            button.style().unpolish(button)
            button.style().polish(button)

    def _open_section(self, name: str) -> None:
        index = {"dictation": 1, "speech_model": 2, "ai_polish": 3}.get(name)
        if index is not None:
            self._select_section(index)

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
        self._apply_login_setting()
        self.settings_saved.emit()

    def _apply_login_setting(self) -> None:
        """Change login start only when the setting changed; never fail the save."""
        wanted = bool(self._settings.open_at_login)
        if wanted == self._login_applied:
            return
        self._login_applied = wanted
        try:
            if not set_open_at_login(wanted):
                LOGGER.warning("Could not change whether Soundflow opens at login")
        except Exception:
            LOGGER.warning("Could not change whether Soundflow opens at login", exc_info=True)

    def _persist_model_path(self, path: str) -> None:
        self._save_timer.stop()
        self._settings.model_path = path
        self.save()

    def refresh_from_settings(self) -> None:
        for widget in self._tab_widgets:
            refresh = getattr(widget, "refresh_from_settings", None)
            if callable(refresh):
                refresh(self._settings)

    def shutdown(self) -> None:
        for widget in self._tab_widgets:
            stop = getattr(widget, "shutdown", None)
            if callable(stop):
                stop()


__all__ = ["PreferencesPage"]
