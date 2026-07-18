import os
import unittest
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton
    import soundflow.history.page as history_page
    from soundflow.history.models import TranscriptEntry
    from soundflow.history.page import TranscriptCard
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class HistoryCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_shows_full_body_and_emits_inline_edit(self):
        body = "First sentence. Complete second sentence remains visible."
        entry = TranscriptEntry(
            id=7,
            created_at=datetime.now(),
            duration_s=3.0,
            title="First sentence",
            summary="First sentence",
            body=body,
        )
        card = TranscriptCard(entry)
        self.assertEqual(card.body_label.text(), body)
        changes = []
        card.save_requested.connect(lambda entry_id, text: changes.append((entry_id, text)))
        card.begin_edit()
        card.editor.setPlainText("Edited full transcript.")
        card.save_edit()
        self.assertEqual(changes, [(7, "Edited full transcript.")])
        card.cancel_edit()
        self.assertFalse(card.body_label.isHidden())

    def test_edit_mode_has_no_insert_action_and_copies_current_editor_text(self):
        entry = TranscriptEntry(
            id=8,
            created_at=datetime.now(),
            duration_s=2.0,
            title="Original",
            summary="Original",
            body="Original transcript.",
        )
        card = TranscriptCard(entry)
        card.begin_edit()
        self.assertFalse(hasattr(card, "insert_button"))
        self.assertTrue(card.copy_button.isEnabled())

        card.editor.setPlainText("Edited but not saved yet.")
        card.copy_text()
        self.assertEqual(
            self.app.clipboard().text(),
            "Edited but not saved yet.",
        )

        card.cancel_edit()
        self.assertFalse(hasattr(card, "insert_button"))

    def test_delete_confirmation_is_compact_and_uses_clear_actions(self):
        dialog_class = getattr(history_page, "DeleteTranscriptDialog", None)
        self.assertIsNotNone(dialog_class)

        dialog = dialog_class("What's up, man")
        dialog.show()
        self.app.processEvents()

        self.assertEqual(dialog.objectName(), "deleteTranscriptDialog")
        self.assertLessEqual(dialog.width(), 420)
        title = dialog.findChild(QLabel, "deleteDialogTitle")
        copy = dialog.findChild(QLabel, "deleteDialogCopy")
        cancel = dialog.findChild(QPushButton, "deleteDialogCancel")
        delete = dialog.findChild(QPushButton, "destructiveButton")
        self.assertEqual(title.text(), "Delete transcript?")
        self.assertIn("What's up, man", copy.text())
        self.assertEqual(cancel.text(), "Cancel")
        self.assertEqual(delete.text(), "Delete")
        self.assertTrue(cancel.isDefault())
        self.assertFalse(delete.isDefault())

        delete.click()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)


if __name__ == "__main__":
    unittest.main()
