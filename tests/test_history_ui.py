import os
import unittest
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
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


if __name__ == "__main__":
    unittest.main()
