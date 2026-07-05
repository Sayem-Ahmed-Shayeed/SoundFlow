import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    from soundflow.core.settings import Settings, SettingsStore
    from soundflow.ui import MainWindow
    from soundflow.ui.pages import DictationPage
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class ModularWindowTests(unittest.TestCase):
    _windows = []
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])
        cls.application.setQuitOnLastWindowClosed(False)

    def test_hosts_and_navigates_four_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            window = MainWindow(Settings(), store, demo_mode=True, no_hotkeys=True)
            self._windows.append(window)
            self.assertIsInstance(window.dictation_page, DictationPage)
            self.assertEqual(
                set(window._page_indices),
                {"dictation", "history", "playground", "preferences"},
            )
            window.navigate("history")
            self.assertEqual(window.pages.currentWidget(), window.history_page)


if __name__ == "__main__":
    unittest.main()
