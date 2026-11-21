import gc
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication, QLabel

    from soundflow.core.settings import Settings, SettingsStore
    from soundflow.preferences.page import SECTIONS, PreferencesPage

    HAS_QT = True
except ImportError:
    HAS_QT = False

_LIST_DEVICES = "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices"
_LOGIN = "soundflow.preferences.page.set_open_at_login"


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class PreferencesPageUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.store = SettingsStore(Path(self._directory.name) / "settings.json")

    def tearDown(self):
        for widget in QApplication.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()
        self._directory.cleanup()

    def make_page(self, settings=None):
        with patch(_LIST_DEVICES, return_value=[]):
            return PreferencesPage(settings or Settings(), self.store)

    def test_five_sections_in_the_approved_order(self):
        self.assertEqual(
            SECTIONS, ("General", "Dictation", "Speech model", "AI Polish", "System")
        )
        page = self.make_page()
        labels = [button.text() for button in page._nav_buttons]
        self.assertEqual(labels, list(SECTIONS))
        self.assertEqual(page.tabs.count(), 5)

    def test_save_writes_every_tab_and_stores_the_file(self):
        page = self.make_page()
        page.general_tab._theme.button("light").click()
        page.general_tab._pill.setChecked(False)
        page.save()
        loaded = self.store.load()
        self.assertEqual(loaded.appearance, "light")
        self.assertFalse(loaded.show_dictation_widget)

    def test_login_setting_is_applied_only_when_it_changes(self):
        page = self.make_page(Settings(open_at_login=True))
        with patch(_LOGIN, return_value=True) as apply:
            page.save()
            apply.assert_not_called()
            page.general_tab._login.setChecked(False)
            page.save()
            apply.assert_called_once_with(False)
            page.save()
            apply.assert_called_once()

    def test_a_failing_login_change_never_fails_the_save(self):
        page = self.make_page(Settings(open_at_login=True))
        saved = []
        page.settings_saved.connect(lambda: saved.append(True))
        page.general_tab._login.setChecked(False)
        with patch(_LOGIN, side_effect=OSError("systemctl missing")):
            page.save()
        self.assertEqual(saved, [True])
        self.assertFalse(self.store.load().open_at_login)

    def test_browsed_model_folder_is_saved_immediately(self):
        page = self.make_page()
        with patch(
            "soundflow.preferences.tabs.speech_model.QFileDialog.getExistingDirectory",
            return_value="/tmp/new-model",
        ):
            page.model_tab._browse_model()
        self.assertEqual(self.store.load().model_path, "/tmp/new-model")

    def test_system_fix_opens_the_matching_section(self):
        page = self.make_page()
        page._open_section("speech_model")
        self.assertEqual(page.tabs.currentIndex(), 2)
        page._open_section("dictation")
        self.assertEqual(page.tabs.currentIndex(), 1)

    def test_refresh_follows_settings_changed_elsewhere(self):
        settings = Settings(language="en")
        page = self.make_page(settings)
        settings.language = "bn"
        settings.open_at_login = False
        page.refresh_from_settings()
        self.assertEqual(page.dictation_tab._language.currentData(), "bn")
        self.assertFalse(page.general_tab._login.isChecked())

    def test_shutdown_stops_a_running_microphone_test(self):
        page = self.make_page()
        with patch("soundflow.preferences.tabs.dictation.AudioCapture") as capture_cls:
            page.dictation_tab._toggle_mic_test()
            page.shutdown()
            capture_cls.return_value.stop.assert_called_once()

    def test_title_and_nav_are_present(self):
        page = self.make_page()
        texts = [label.text() for label in page.findChildren(QLabel)]
        self.assertIn("Preferences", texts)


if __name__ == "__main__":
    unittest.main()
