import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from soundflow.ui.widgets.message_dialog import MessageDialog


class MessageDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_note_has_one_primary_button_and_an_app_icon(self):
        dialog = MessageDialog("Export failed", "Disk full.", kind="error")
        self.assertIsNone(dialog.reject_button)
        self.assertEqual(dialog.accept_button.objectName(), "primaryButton")
        self.assertEqual(dialog.icon_name, "alert")
        self.assertFalse(dialog.badge.pixmap().isNull())

    def test_destructive_question_defaults_to_the_safe_choice(self):
        dialog = MessageDialog(
            "Sign out of Soundflow?",
            "…",
            kind="sign-out",
            accept_text="Sign out",
            reject_text="Stay signed in",
            destructive=True,
        )
        self.assertEqual(dialog.accept_button.objectName(), "destructiveButton")
        self.assertTrue(dialog.reject_button.isDefault())
        self.assertFalse(dialog.accept_button.isDefault())


class NoStockIconsTests(unittest.TestCase):
    def test_app_code_uses_no_system_dialogs_stock_icons_or_emoji(self):
        import re
        from pathlib import Path

        root = Path(__file__).resolve().parents[1] / "src" / "soundflow"
        emoji = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
        offenders = []
        for path in root.rglob("*.py"):
            if "_legacy" in path.parts or path.name == "message_dialog.py":
                continue
            text = path.read_text(encoding="utf-8")
            for needle in ("QMessageBox", "standardIcon(", "QIcon.fromTheme"):
                if needle in text:
                    offenders.append(f"{path.name}: {needle}")
            if emoji.search(text):
                offenders.append(f"{path.name}: emoji")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
