import gc
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QTextEdit

    from soundflow.core.settings import Settings
    from soundflow.preferences.tabs.ai_polish import AiPolishTab
    from soundflow.ui.widgets import SegmentedControl, ToggleSwitch

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class AiPolishTabUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def tearDown(self):
        for widget in QApplication.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()

    def test_off_by_default_and_shows_only_the_privacy_line(self):
        tab = AiPolishTab(Settings())
        tab.show()
        self.application.processEvents()
        self.assertFalse(tab._enable.isChecked())
        self.assertFalse(tab._service.parentWidget().isVisibleTo(tab))
        self.assertFalse(tab._style_group.parentWidget().isVisibleTo(tab))
        texts = [label.text() for label in tab.findChildren(QLabel)]
        self.assertIn(
            "Rewrites the text of a dictation with an online AI service. Only the "
            "text is sent, never your voice.",
            texts,
        )

    def test_turning_it_on_reveals_service_and_style(self):
        tab = AiPolishTab(Settings())
        tab.show()
        tab._enable.setChecked(True)
        self.application.processEvents()
        self.assertTrue(tab._service.parentWidget().isVisibleTo(tab))
        self.assertTrue(tab._style_group.parentWidget().isVisibleTo(tab))

    def test_each_provider_keeps_its_own_key_and_model(self):
        tab = AiPolishTab(
            Settings(gemini_api_key="AIza-one", openrouter_api_key="sk-two",
                     openrouter_model="openai/gpt-oss-20b:free")
        )
        tab._key.setText("AIza-changed")
        tab._provider.button("openrouter").click()
        self.assertEqual(tab._key.text(), "sk-two")
        self.assertEqual(tab._openrouter_model.text(), "openai/gpt-oss-20b:free")
        tab._key.setText("sk-changed")
        tab._provider.button("gemini").click()
        self.assertEqual(tab._key.text(), "AIza-changed")

        updated = Settings()
        tab.write_back(updated)
        self.assertEqual(updated.ai_provider, "gemini")
        self.assertEqual(updated.gemini_api_key, "AIza-changed")
        self.assertEqual(updated.openrouter_api_key, "sk-changed")
        self.assertEqual(updated.openrouter_model, "openai/gpt-oss-20b:free")

    def test_gemini_models_offer_flash_and_pro_and_keep_other_values(self):
        tab = AiPolishTab(Settings(gemini_model="gemini-2.5-pro"))
        labels = [tab._gemini_model.itemText(i) for i in range(tab._gemini_model.count())]
        self.assertEqual(labels[:2], ["Gemini 2.5 Flash", "Gemini 2.5 Pro"])
        self.assertEqual(tab._gemini_model.currentData(), "gemini-2.5-pro")

        other = AiPolishTab(Settings(gemini_model="gemini-experimental"))
        self.assertEqual(other._gemini_model.currentData(), "gemini-experimental")
        updated = Settings()
        other.write_back(updated)
        self.assertEqual(updated.gemini_model, "gemini-experimental")

    def test_custom_style_shows_the_instruction_box(self):
        tab = AiPolishTab(Settings(ai_preset="custom", ai_custom_instruction="Bullets"))
        tab._enable.setChecked(True)
        tab.show()
        self.application.processEvents()
        self.assertTrue(tab._custom_row.isVisibleTo(tab))
        self.assertEqual(tab._custom.toPlainText(), "Bullets")
        tab._style.button("clean").click()
        self.assertFalse(tab._custom_row.isVisibleTo(tab))

    def test_style_description_matches_the_choice(self):
        tab = AiPolishTab(Settings(ai_preset="concise"))
        self.assertEqual(tab._style_row.description_label.text(), "Says the same thing in fewer words.")
        tab._style.button("clean").click()
        self.assertEqual(
            tab._style_row.description_label.text(),
            "Fixes punctuation, capitals and filler words. Keeps your words.",
        )

    def test_check_key_reports_success_under_the_field(self):
        tab = AiPolishTab(Settings(gemini_api_key="AIza-one"))
        tab.show()

        def fake_polish(text, settings, done, failed, parent=None):
            done("ok")

        with patch("soundflow.core.llm.polish_in_background", side_effect=fake_polish):
            tab._check.click()
        self.assertEqual(tab._key_result.text(), "The key works.")
        self.assertFalse(tab._key_result.isHidden())
        self.assertTrue(tab._check.isEnabled())

    def test_check_key_reports_failure_under_the_field(self):
        tab = AiPolishTab(Settings(gemini_api_key="AIza-bad"))

        def fake_polish(text, settings, done, failed, parent=None):
            failed("The key was rejected.")

        with patch("soundflow.core.llm.polish_in_background", side_effect=fake_polish):
            tab._check.click()
        self.assertEqual(tab._key_result.text(), "The key was rejected.")
        self.assertEqual(tab._key_result.property("tone"), "error")

    def test_polish_every_dictation_round_trips(self):
        tab = AiPolishTab(Settings(ai_auto_clean=False))
        tab._auto.setChecked(True)
        updated = Settings()
        tab.write_back(updated)
        self.assertTrue(updated.ai_auto_clean)
        self.assertEqual(len(tab.findChildren(ToggleSwitch)), 2)
        self.assertIsInstance(tab.findChild(SegmentedControl), SegmentedControl)
        self.assertIsInstance(tab.findChild(QTextEdit, "historyEditor"), QTextEdit)
        self.assertIsInstance(tab.findChild(QLineEdit, "compactPathField"), QLineEdit)


if __name__ == "__main__":
    unittest.main()
