"""Preferences in a dialog: the same page as the main window, with Save and Cancel."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QWidget

from soundflow.preferences.page import PreferencesPage


class _NullStore:
    """Stands in for a settings store when the dialog is given none."""

    def save(self, settings) -> None:
        del settings


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
        self._on_save = on_save

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self._page = PreferencesPage(settings, store or _NullStore(), self)
        outer.addWidget(self._page, 1)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save)
        button_box.rejected.connect(self.reject)
        outer.addWidget(button_box)

    @property
    def page(self) -> PreferencesPage:
        return self._page

    def _save(self) -> None:
        self._page.save()
        if self._on_save is not None:
            self._on_save(self._settings)
        self.accept()

    def reject(self) -> None:
        self._page.shutdown()
        super().reject()


__all__ = ["PreferencesDialog"]
