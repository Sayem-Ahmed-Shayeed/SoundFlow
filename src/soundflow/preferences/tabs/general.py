"""General tab: appearance, login start, and the floating pill."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from soundflow.preferences.widgets import PreferenceTab, SettingsRow
from soundflow.ui.widgets import AppearanceSelector, ToggleSwitch


class GeneralTab(PreferenceTab):
    """General preferences tab."""

    appearance_changed = Signal(str)

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__("generalTab", "General", parent)
        self._settings = settings

        appearance = self.add_group("Appearance")
        self._theme = AppearanceSelector(settings.appearance)
        self._theme.changed.connect(self.appearance_changed)
        appearance.add_row(
            SettingsRow(
                "Theme",
                "Light is cream paper; Dark is a deep green-black.",
                self._theme,
            )
        )

        startup = self.add_group("Startup")
        self._login = ToggleSwitch("Open Soundflow when you log in")
        self._login.setChecked(bool(settings.open_at_login))
        startup.add_row(
            SettingsRow(
                "Open Soundflow when you log in",
                "It starts hidden, so your shortcut works right away. Opening it "
                "from the app menu always shows this window.",
                self._login,
            )
        )

        dictating = self.add_group("While you dictate")
        self._pill = ToggleSwitch("Show the floating pill")
        self._pill.setChecked(bool(settings.show_dictation_widget))
        dictating.add_row(
            SettingsRow(
                "Show the floating pill",
                "A small indicator above your other apps shows when Soundflow is "
                "listening.",
                self._pill,
            )
        )
        self.finish()

    def write_back(self, settings) -> None:
        settings.appearance = self._theme.value()
        settings.open_at_login = self._login.isChecked()
        settings.show_dictation_widget = self._pill.isChecked()

    def refresh_from_settings(self, settings=None) -> None:
        source = settings if settings is not None else self._settings
        self._theme.set_value(source.appearance, emit=False)
        for switch, value in (
            (self._login, source.open_at_login),
            (self._pill, source.show_dictation_widget),
        ):
            switch.blockSignals(True)
            switch.setChecked(bool(value))
            switch.blockSignals(False)


__all__ = ["GeneralTab"]
