import gc
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication, QLabel

    from soundflow.core.settings import Settings
    from soundflow.design import apply_stylesheet, register_application_fonts
    from soundflow.playground.page import PlaygroundPage

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class PlaygroundUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])
        register_application_fonts()
        apply_stylesheet(cls.application, True)
        cls.application.setProperty("soundflowDark", True)

    def setUp(self):
        self.page = PlaygroundPage()
        self.page.resize(960, 700)
        self.page.show()
        self.application.processEvents()

    def tearDown(self):
        self.page.close()
        self.page.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()

    def _settle(self):
        for _ in range(3):
            self.application.processEvents()

    def test_layout_shows_three_text_actions_and_insert(self):
        page = self.page
        for card in (page._format_card, page._rewrite_card, page._polish_card):
            self.assertTrue(card.isCheckable())
            labels = card.findChildren(QLabel)
            self.assertEqual(len(labels), 3)
            self.assertGreaterEqual(labels[2].height(), labels[2].fontMetrics().height())
        self.assertFalse(page._insert_card.isCheckable())
        self.assertGreaterEqual(page._command.height(), 180)
        self.assertFalse(page._run_button.isEnabled())

    def test_format_shows_result_and_insert_emits_it(self):
        page = self.page
        page._command.setPlainText("hello   world.this is a test")
        inserted = []
        page.insert_requested.connect(inserted.append)
        page._format_card.click()
        self._settle()

        self.assertTrue(page._format_card.isChecked())
        self.assertEqual(page._result, "Hello world. This is a test.")
        self.assertTrue(page._run_button.isEnabled())
        self.assertEqual(page._command.toPlainText(), "hello   world.this is a test")

        page._run_button.click()
        self.assertEqual(inserted, ["Hello world. This is a test."])

    def test_empty_input_does_not_run_an_action(self):
        page = self.page
        page._rewrite_card.click()
        self._settle()
        self.assertFalse(page._rewrite_card.isChecked())
        self.assertEqual(page._result, "")
        self.assertEqual(page._preview.text(), "Type or paste some text first.")

    def test_insert_card_inserts_typed_text_without_clearing(self):
        page = self.page
        page._command.setPlainText("  raw text  ")
        inserted = []
        page.insert_requested.connect(inserted.append)
        page._insert_card.click()
        self.assertEqual(inserted, ["raw text"])
        self.assertEqual(page._command.toPlainText(), "  raw text  ")

    def test_polish_is_refused_while_ai_polish_is_off(self):
        page = self.page
        page.set_settings(Settings(ai_cleanup_enabled=False))
        page._command.setPlainText("some text")
        with patch("soundflow.core.llm.polish_in_background") as polish:
            page._polish_card.click()
            self._settle()
        polish.assert_not_called()
        self.assertIn("AI Polish is off", page._preview.text())
        self.assertFalse(page._run_button.isEnabled())

    def test_polish_result_comes_from_the_provider_call(self):
        page = self.page
        page.set_settings(Settings(ai_cleanup_enabled=True))
        page._command.setPlainText("some text")

        def fake_polish(text, settings, done, failed, parent=None):
            self.assertEqual(text, "some text")
            done("Some text, polished.\n")

        with patch("soundflow.core.llm.polish_in_background", side_effect=fake_polish):
            page._polish_card.click()
            self._settle()
        self.assertEqual(page._result, "Some text, polished.")
        self.assertTrue(page._run_button.isEnabled())

    def test_polish_failure_is_shown_and_reported(self):
        page = self.page
        page.set_settings(Settings(ai_cleanup_enabled=True))
        page._command.setPlainText("some text")
        failures = []
        page.transformation_failed.connect(failures.append)

        def fake_polish(text, settings, done, failed, parent=None):
            failed("Gemini rejected the key")

        with patch("soundflow.core.llm.polish_in_background", side_effect=fake_polish):
            page._polish_card.click()
            self._settle()
        self.assertEqual(failures, ["Gemini rejected the key"])
        self.assertEqual(page._preview.property("state"), "error")
        self.assertFalse(page._run_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
