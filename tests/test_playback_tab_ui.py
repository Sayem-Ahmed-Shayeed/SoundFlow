import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QLabel, QWidget

    from soundflow.core.settings import Settings
    from soundflow.design import stylesheet
    from soundflow.ui import MainWindow  # Load the public UI surface first.
    from soundflow.preferences.tabs.playback import PlaybackTab

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class PlaybackTabUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_playback_rows_are_visible_and_persist(self):
        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(stylesheet(True))
        try:
            settings = Settings()
            tab = PlaybackTab(settings)
            tab.resize(700, 360)
            tab.show()
            self.application.processEvents()

            card = tab.findChild(QWidget, "preferencesCard")
            labels = [
                label for label in card.findChildren(QLabel)
                if label.isVisible()
            ]
            self.assertTrue(labels)
            self.assertTrue(
                all(label.height() >= label.fontMetrics().height() for label in labels)
            )
            for switch in (tab._auto_insert, tab._show_widget, tab._auto_save):
                self.assertTrue(
                    card.rect().contains(
                        switch.mapTo(card, switch.rect().center())
                    )
                )
                switch.setChecked(False)
            tab.write_back(settings)
            self.assertFalse(settings.auto_insert)
            self.assertFalse(settings.show_dictation_widget)
            self.assertFalse(settings.auto_save_transcripts)
        finally:
            self.application.setStyleSheet(previous_stylesheet)


if __name__ == "__main__":
    unittest.main()
