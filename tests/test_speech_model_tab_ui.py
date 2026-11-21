import gc
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import (
        QApplication,
        QLabel,
        QPushButton,
        QScrollArea,
        QToolButton,
        QWidget,
    )

    from soundflow.core.settings import Settings
    from soundflow.design import stylesheet
    from soundflow.models.catalog import MODEL_CATALOG
    from soundflow.preferences.tabs.speech_model import SpeechModelTab
    from soundflow.ui.widgets import SegmentedControl

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class SpeechModelTabUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def tearDown(self):
        for widget in QApplication.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()

    def test_one_row_per_catalog_model(self):
        tab = SpeechModelTab(Settings())
        rows = [
            child for child in tab.findChildren(QWidget)
            if child.objectName().startswith("modelRow:")
        ]
        self.assertEqual(len(rows), len(MODEL_CATALOG))

    def test_processing_offers_automatic_gpu_and_processor(self):
        tab = SpeechModelTab(Settings(inference_device="auto"))
        control = tab.findChild(SegmentedControl)
        self.assertEqual(
            [button.text() for button in control.findChildren(QPushButton)],
            ["Automatic", "GPU", "Processor"],
        )
        self.assertEqual(control.value(), "auto")
        self.assertIn("NVIDIA GPU", tab._device_row.description_label.text())

        tab._device.set_value("cpu")
        tab._sync_device_text("cpu")
        self.assertIn("Works on every computer", tab._device_row.description_label.text())
        updated = Settings()
        tab.write_back(updated)
        self.assertEqual(updated.inference_device, "cpu")

    def test_old_cpu_setting_still_selects_the_processor(self):
        tab = SpeechModelTab(Settings(inference_device="cpu"))
        self.assertEqual(tab._device.value(), "cpu")

    def test_advanced_folder_picker_is_collapsed_by_default(self):
        tab = SpeechModelTab(Settings())
        toggle = tab.findChild(QToolButton, "disclosureButton")
        self.assertIsNotNone(toggle)
        self.assertTrue(tab._advanced_body.isHidden())
        toggle.click()
        self.assertFalse(tab._advanced_body.isHidden())
        self.assertTrue(toggle.isChecked())

    def test_browsed_folder_becomes_the_model_and_refreshes_the_rows(self):
        managed_path = "/tmp/faster-whisper-base"
        custom_path = "/tmp/custom-whisper-model"
        tab = SpeechModelTab(Settings(model_path=managed_path))
        manager = tab._model_manager
        changes = []
        tab.model_path_changed.connect(changes.append)

        with patch.object(
            manager._service,
            "installed_path",
            side_effect=lambda model_id: managed_path if model_id == "base" else None,
        ):
            manager._refresh_rows()
            self.assertFalse(manager.findChild(QLabel, "modelStatus:base").isHidden())
            with patch(
                "soundflow.preferences.tabs.speech_model.QFileDialog.getExistingDirectory",
                return_value=custom_path,
            ):
                tab._browse_model()

            self.assertEqual(tab._settings.model_path, custom_path)
            self.assertEqual(changes, [custom_path])
            self.assertTrue(manager.findChild(QLabel, "modelStatus:base").isHidden())
            use = manager.findChild(QPushButton, "modelAction:base")
            self.assertEqual(use.text(), "Use")
            self.assertTrue(use.isEnabled())
            self.assertIn(custom_path, tab._folder_row.description_label.text())

    def test_cancelled_folder_picker_changes_nothing(self):
        tab = SpeechModelTab(Settings(model_path="/tmp/kept"))
        changes = []
        tab.model_path_changed.connect(changes.append)
        with patch(
            "soundflow.preferences.tabs.speech_model.QFileDialog.getExistingDirectory",
            return_value="",
        ):
            tab._browse_model()
        self.assertEqual(tab._settings.model_path, "/tmp/kept")
        self.assertEqual(changes, [])

    def test_rows_stay_readable_at_the_minimum_window_size(self):
        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(stylesheet(True))
        try:
            tab = SpeechModelTab(Settings())
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
            scroll = tab.findChild(QScrollArea, "speechModelTabScroll")
            self.assertIsNotNone(scroll)
            scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
            self.application.processEvents()
        finally:
            self.application.setStyleSheet(previous_stylesheet)

    def test_note_says_voice_stays_on_this_computer(self):
        tab = SpeechModelTab(Settings())
        texts = [label.text() for label in tab.findChildren(QLabel)]
        self.assertIn(
            "Models run on this computer. Your voice is never sent anywhere.",
            texts,
        )


if __name__ == "__main__":
    unittest.main()
