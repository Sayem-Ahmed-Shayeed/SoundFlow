import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QLabel,
        QLineEdit,
        QProgressBar,
        QPushButton,
        QWidget,
    )

    from soundflow.core.settings import Settings
    from soundflow.design import CONTROL_HEIGHT_SM, stylesheet
    from soundflow.ui import MainWindow  # Load the public UI surface first.
    from soundflow.preferences.tabs.dictation import DictationTab

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class DictationTabUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_recognition_fields_are_compact_and_decorative_meter_is_hidden(self):
        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(stylesheet(True))
        try:
            with patch(
                "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices",
                return_value=[],
            ):
                tab = DictationTab(Settings())
            tab.resize(1000, 500)
            tab.show()
            self.application.processEvents()

            fields = tab.findChildren(QComboBox, "compactPreferenceField")
            self.assertEqual(len(fields), 3)
            self.assertTrue(
                all(field.height() <= CONTROL_HEIGHT_SM for field in fields)
            )
            path = tab.findChild(QLineEdit, "compactPathField")
            browse = tab.findChild(QPushButton, "compactBrowseButton")
            self.assertIsNotNone(path)
            self.assertIsNotNone(browse)
            self.assertEqual(path.height(), CONTROL_HEIGHT_SM)
            self.assertEqual(browse.height(), CONTROL_HEIGHT_SM)
            self.assertTrue(all(field.height() == path.height() for field in fields))
            self.assertFalse(
                any(
                    progress.isVisibleTo(tab)
                    for progress in tab.findChildren(QProgressBar)
                )
            )
            card = tab.findChild(QWidget, "preferencesCard")
            labels = [
                label for label in card.findChildren(QLabel)
                if label.isVisible()
            ]
            self.assertTrue(labels)
            self.assertTrue(
                all(label.height() >= label.fontMetrics().height() for label in labels)
            )
        finally:
            self.application.setStyleSheet(previous_stylesheet)

    def test_dictation_tab_embeds_five_model_rows(self):
        with patch(
            "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices",
            return_value=[],
        ):
            tab = DictationTab(Settings())
        rows = [
            child for child in tab.findChildren(QWidget)
            if child.objectName().startswith("modelRow:")
        ]
        self.assertEqual(len(rows), 5)

    def test_model_selection_updates_custom_path_field(self):
        with patch(
            "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices",
            return_value=[],
        ):
            tab = DictationTab(Settings())
        changes = []
        tab.model_path_changed.connect(changes.append)
        tab._model_manager.model_path_selected.emit("/tmp/faster-whisper-base")
        self.assertEqual(tab._model.text(), "/tmp/faster-whisper-base")
        self.assertEqual(changes, ["/tmp/faster-whisper-base"])

    def test_model_rows_remain_readable_at_minimum_window_geometry(self):
        with patch(
            "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices",
            return_value=[],
        ):
            tab = DictationTab(Settings())
        tab.resize(664, 379)
        tab.show()
        self.application.processEvents()

        rows = [
            child for child in tab.findChildren(QWidget)
            if child.objectName().startswith("modelRow:")
        ]
        self.assertTrue(rows)
        self.assertTrue(
            all(row.height() >= row.minimumSizeHint().height() for row in rows)
        )
        self.assertIsNotNone(tab.findChild(QPushButton, "compactBrowseButton"))


if __name__ == "__main__":
    unittest.main()
