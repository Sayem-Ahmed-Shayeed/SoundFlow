import gc
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QCoreApplication, QEvent, Qt
    from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton

    import soundflow.history.page as history_page
    from soundflow.history.models import TranscriptEntry
    from soundflow.history.page import DeleteTranscriptDialog
    from soundflow.history.store import HistoryStore
    from soundflow.history.widgets import TranscriptDetail, TranscriptItem, day_label

    HAS_QT = True
except ImportError:
    HAS_QT = False


def _entry(body: str, entry_id: int = 7) -> TranscriptEntry:
    return TranscriptEntry(
        id=entry_id,
        created_at=datetime.now(),
        duration_s=65.0,
        title=TranscriptEntry.make_title(body),
        summary=body,
        body=body,
    )


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class HistoryWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._widgets = []

    def tearDown(self):
        for widget in self._widgets:
            widget.close()
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self._widgets = []
        gc.collect()

    def _track(self, widget):
        self._widgets.append(widget)
        return widget

    def test_item_shows_meta_and_selection_property(self):
        item = self._track(TranscriptItem(_entry("One two three four"), False))
        meta = [label.text() for label in item.findChildren(QLabel, "historyMeta")]
        self.assertEqual(meta, [datetime.now().strftime("%I:%M %p").lstrip("0"), "1:05", "4 words"])
        self.assertFalse(item.property("selected"))
        item.set_selected(True)
        self.assertTrue(item.property("selected"))

    def test_item_click_emits_entry_id(self):
        item = self._track(TranscriptItem(_entry("Click me"), False))
        seen = []
        item.activated.connect(seen.append)
        item.show()
        self.app.processEvents()
        from PySide6.QtCore import QEvent as QE
        from PySide6.QtGui import QMouseEvent
        press = QMouseEvent(
            QE.Type.MouseButtonPress,
            item.rect().center().toPointF(),
            item.rect().center().toPointF(),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        self.app.sendEvent(item, press)
        self.assertEqual(seen, [7])

    def test_day_label_names_today_and_yesterday(self):
        from datetime import timedelta

        today = datetime.now()
        self.assertEqual(day_label(today), "Today")
        self.assertEqual(day_label(today - timedelta(days=1)), "Yesterday")
        self.assertNotIn(day_label(today - timedelta(days=9)), ("Today", "Yesterday"))

    def test_detail_edit_saves_and_cancels_with_clear_actions(self):
        detail = self._track(TranscriptDetail())
        detail.show_entry(_entry("Original text."), ("Local only", "Sync is off"))
        changes = []
        detail.save_requested.connect(lambda entry_id, text: changes.append((entry_id, text)))

        detail.begin_edit()
        self.assertTrue(detail.is_editing())
        self.assertEqual(detail.editor.toPlainText(), "Original text.")
        self.assertTrue(detail.save_button.isVisibleTo(detail) or not detail.isVisible())
        self.assertEqual(detail.save_button.text(), "Save changes")
        self.assertEqual(detail.cancel_button.text(), "Cancel")

        detail.editor.setPlainText("Edited full transcript.")
        detail.save_edit()
        self.assertEqual(changes, [(7, "Edited full transcript.")])

        detail.cancel_edit()
        self.assertFalse(detail.is_editing())
        self.assertFalse(detail.edit_block.isVisibleTo(detail))

    def test_empty_edit_is_refused_with_message(self):
        detail = self._track(TranscriptDetail())
        detail.show_entry(_entry("Something"), ("Local only", "Sync is off"))
        changes = []
        detail.save_requested.connect(lambda *args: changes.append(args))
        detail.begin_edit()
        detail.editor.setPlainText("   ")
        detail.save_edit()
        self.assertEqual(changes, [])
        self.assertEqual(detail.feedback.text(), "Transcript text cannot be empty.")

    def test_copy_uses_editor_text_while_editing(self):
        detail = self._track(TranscriptDetail())
        detail.show_entry(_entry("Original transcript."), ("Local only", "Sync is off"))
        detail.begin_edit()
        detail.editor.setPlainText("Edited but not saved yet.")
        detail.copy_text()
        self.assertEqual(self.app.clipboard().text(), "Edited but not saved yet.")
        detail.cancel_edit()

    def test_more_menu_offers_export_and_danger_delete(self):
        detail = self._track(TranscriptDetail())
        detail.show_entry(_entry("Menu test"), ("Local only", "Sync is off"))
        exported, deleted = [], []
        detail.export_requested.connect(exported.append)
        detail.delete_requested.connect(deleted.append)
        names = {button.text(): button for button in detail._menu.findChildren(QPushButton, "menuItem")}
        self.assertEqual(set(names), {"Export as text", "Delete transcript"})
        self.assertTrue(names["Delete transcript"].property("danger"))
        names["Export as text"].click()
        self.assertEqual(exported, [7])
        names["Delete transcript"].click()
        self.assertEqual(deleted, [7])

    def test_delete_dialog_asks_first_and_drops_sync_copy_when_local(self):
        local = self._track(DeleteTranscriptDialog("What's up, man", synced=False))
        local.show()
        self.app.processEvents()
        self.assertEqual(local.objectName(), "deleteTranscriptDialog")
        self.assertLessEqual(local.width(), 420)
        self.assertEqual(local.findChild(QLabel, "deleteDialogTitle").text(), "Delete this transcript?")
        copy = local.findChild(QLabel, "deleteDialogCopy").text()
        self.assertEqual(copy, "It's removed from this computer. You can't undo this.")
        self.assertIn("What's up, man", local.quote.text())
        cancel = local.findChild(QPushButton, "deleteDialogCancel")
        delete = local.findChild(QPushButton, "destructiveButton")
        self.assertEqual(cancel.text(), "Keep it")
        self.assertEqual(delete.text(), "Delete transcript")
        self.assertTrue(cancel.isDefault())
        self.assertFalse(delete.isDefault())
        delete.click()
        self.assertEqual(local.result(), QDialog.DialogCode.Accepted)

        synced = self._track(DeleteTranscriptDialog("Synced text", synced=True))
        self.assertIn("from your other computers", synced.findChild(QLabel, "deleteDialogCopy").text())

    def test_page_empty_states_use_the_design_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HistoryStore(Path(directory) / "history.db")
            try:
                page = self._track(history_page.HistoryPage(store))
                titles = [label.text() for label in page.findChildren(QLabel, "emptyTitle")]
                bodies = [label.text() for label in page.findChildren(QLabel, "emptyBody")]
                self.assertEqual(titles, ["No dictations yet"])
                self.assertEqual(bodies, ["Hold Ctrl Alt Space in any app and start speaking."])

                store.add("Invoice reminder for Lisbon", 4.0)
                page.search.setText("zzz")
                page.refresh(reset=True)
                self.app.processEvents()
                titles = [label.text() for label in page.findChildren(QLabel, "emptyTitle")]
                self.assertEqual(titles, ["No transcripts match “zzz”"])
                clear = page.findChild(QPushButton)
                clear_buttons = [b for b in page.findChildren(QPushButton) if b.text() == "Clear search"]
                self.assertEqual(len(clear_buttons), 1)
                clear_buttons[0].click()
                self.assertEqual(page.search.text(), "")
                self.assertIsNotNone(clear)
            finally:
                store.close()

    def test_delete_from_menu_removes_entry_and_selects_next(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HistoryStore(Path(directory) / "history.db")
            try:
                first = store.add("First transcript", 3.0)
                second = store.add("Second transcript", 3.0)
                page = self._track(history_page.HistoryPage(store))
                page.show()
                self.app.processEvents()
                self.assertEqual(page.detail.entry_id(), second.id)
                original = history_page.DeleteTranscriptDialog.exec
                history_page.DeleteTranscriptDialog.exec = lambda self_: QDialog.DialogCode.Accepted
                try:
                    page._delete_entry(second.id)
                finally:
                    history_page.DeleteTranscriptDialog.exec = original
                self.app.processEvents()
                self.assertIsNone(store.get(second.id))
                self.assertEqual(page.detail.entry_id(), first.id)
            finally:
                store.close()

    def test_select_entry_clears_search_and_shows_that_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HistoryStore(Path(directory) / "history.db")
            try:
                first = store.add("Lisbon invoice", 3.0)
                store.add("Berlin notes", 3.0)
                page = self._track(history_page.HistoryPage(store))
                page.show()
                page.search.setText("Berlin")
                page.refresh(reset=True)
                self.app.processEvents()
                page.select_entry(first.id)
                self.app.processEvents()
                self.assertEqual(page.search.text(), "")
                self.assertEqual(page.detail.entry_id(), first.id)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
