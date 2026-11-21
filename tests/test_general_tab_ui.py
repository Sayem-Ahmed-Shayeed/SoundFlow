import gc
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QScrollArea, QWidget

    from soundflow.core.settings import Settings
    from soundflow.design import stylesheet
    from soundflow.preferences.tabs.general import GeneralTab
    from soundflow.ui.widgets import ToggleSwitch

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class GeneralTabUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def tearDown(self):
        for widget in QApplication.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()

    def test_theme_offers_dark_first_and_is_written_back(self):
        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(stylesheet(True))
        try:
            tab = GeneralTab(Settings(appearance="dark"))
            tab.resize(700, 480)
            tab.show()
            self.application.processEvents()

            buttons = tab._theme.findChildren(QPushButton)
            self.assertEqual(
                [button.text() for button in buttons],
                ["Dark", "Light"],
            )
            self.assertEqual(sum(button.isChecked() for button in buttons), 1)

            tab._theme.button("light").click()
            updated = Settings(appearance="dark")
            tab.write_back(updated)
            self.assertEqual(updated.appearance, "light")
        finally:
            self.application.setStyleSheet(previous_stylesheet)

    def test_theme_change_emits_appearance_changed_immediately(self):
        tab = GeneralTab(Settings(appearance="dark"))
        changes = []
        tab.appearance_changed.connect(changes.append)
        tab._theme.button("light").click()
        self.assertEqual(changes, ["light"])

    def test_refresh_sets_theme_without_emitting(self):
        tab = GeneralTab(Settings(appearance="dark"))
        changes = []
        tab.appearance_changed.connect(changes.append)
        tab._theme.set_value("light", emit=False)
        tab.refresh_from_settings(Settings(appearance="dark"))
        self.assertEqual(tab._theme.value(), "dark")
        self.assertEqual(changes, [])

    def test_startup_and_pill_toggles_round_trip(self):
        tab = GeneralTab(Settings(open_at_login=True, show_dictation_widget=True))
        switches = tab.findChildren(ToggleSwitch)
        self.assertEqual(len(switches), 2)
        self.assertTrue(all(switch.isChecked() for switch in switches))

        tab._login.setChecked(False)
        tab._pill.setChecked(False)
        updated = Settings()
        tab.write_back(updated)
        self.assertFalse(updated.open_at_login)
        self.assertFalse(updated.show_dictation_widget)

    def test_copy_matches_the_approved_wording(self):
        tab = GeneralTab(Settings())
        texts = [label.text() for label in tab.findChildren(QLabel)]
        self.assertIn("Light is cream paper; Dark is a deep green-black.", texts)
        self.assertIn("Open Soundflow when you log in", texts)
        self.assertIn("Show the floating pill", texts)

    def test_layout_scrolls_and_cards_fit_the_viewport(self):
        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(stylesheet(True))
        try:
            tab = GeneralTab(Settings())
            tab.resize(700, 300)
            tab.show()
            self.application.processEvents()
            scroll = tab.findChild(QScrollArea, "generalTabScroll")
            self.assertIsNotNone(scroll)
            cards = tab.findChildren(QWidget, "preferencesCard")
            self.assertEqual(len(cards), 3)
            for card in cards:
                self.assertLessEqual(card.width(), scroll.viewport().width())
        finally:
            self.application.setStyleSheet(previous_stylesheet)


if __name__ == "__main__":
    unittest.main()
