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
        QScrollArea,
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

    def test_browse_refreshes_the_model_manager_active_row(self):
        managed_path = "/tmp/faster-whisper-base"
        custom_path = "/tmp/custom-whisper-model"
        with patch(
            "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices",
            return_value=[],
        ):
            tab = DictationTab(Settings(model_path=managed_path))
        manager = tab._model_manager

        with patch.object(
            manager._service,
            "installed_path",
            side_effect=(
                lambda model_id: managed_path if model_id == "base" else None
            ),
        ):
            manager._refresh_rows()
            self.assertEqual(
                manager.findChild(QLabel, "modelStatus:base").text(),
                "Active",
            )
            with patch(
                "soundflow.preferences.tabs.dictation.QFileDialog.getExistingDirectory",
                return_value=custom_path,
            ):
                tab._browse_model()

            self.assertEqual(tab._settings.model_path, custom_path)
            self.assertEqual(
                manager.findChild(QLabel, "modelStatus:base").text(),
                "Installed",
            )
            use = manager.findChild(QPushButton, "modelAction:base")
            self.assertEqual(use.text(), "Use")
            self.assertTrue(use.isEnabled())

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
        scroll = tab.findChild(QScrollArea, "dictationScroll")
        browse = tab.findChild(QPushButton, "compactBrowseButton")
        self.assertIsNotNone(scroll)
        self.assertIsNotNone(browse)
        self.assertGreater(scroll.verticalScrollBar().maximum(), 0)
        scroll.verticalScrollBar().setValue(
            scroll.verticalScrollBar().maximum()
        )
        self.application.processEvents()
        self.assertTrue(browse.isVisibleTo(scroll.viewport()))


if __name__ == "__main__":
    unittest.main()
