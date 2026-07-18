import os
import tempfile
import threading
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QProgressBar, QPushButton

from soundflow.core.settings import Settings
from soundflow.models.catalog import MODEL_CATALOG, managed_model_path, model_spec
from soundflow.models.service import ModelDownloadCancelled, ModelManagerError
from soundflow.preferences.model_manager import (
    ModelDownloadThread,
    ModelManagerWidget,
)


class FakeService:
    def __init__(self, root, installed=(), bundled_small=False):
        self.root = Path(root)
        self.installed = set(installed)
        self.bundled_small = bundled_small
        self.deleted = []

    def installed_path(self, model_id):
        if model_id not in self.installed:
            return None
        path = managed_model_path(model_spec(model_id), self.root)
        if model_id == "small" and self.bundled_small:
            return self.root.parent / "bundle" / path.name
        return path

    def delete(self, model_id, *, active_path):
        self.deleted.append((model_id, Path(active_path)))
        self.installed.discard(model_id)


class ModelManagerUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_five_rows_map_active_installed_and_missing_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            active = managed_model_path(model_spec("small"), root)
            widget = ModelManagerWidget(
                Settings(model_path=str(active)),
                service=FakeService(root, ("base", "small")),
            )

            self.assertEqual(
                widget.findChild(QLabel, "modelStatus:small").text(), "Active"
            )
            self.assertEqual(
                widget.findChild(QPushButton, "modelAction:base").text(), "Use"
            )
            self.assertEqual(
                widget.findChild(QPushButton, "modelAction:tiny").text(),
                "Download",
            )
            self.assertEqual(len(widget.findChildren(QProgressBar)), 5)
            for spec in MODEL_CATALOG:
                row = widget.findChild(QLabel, f"modelGuidance:{spec.model_id}")
                self.assertIn(spec.guidance, row.text())
                self.assertIn(spec.download_size, row.text())
            self.assertEqual(
                widget.findChild(QLabel, "modelRecommended:small").text(),
                "Recommended",
            )

    def test_use_selects_installed_path_and_protects_new_active_row(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = FakeService(root, ("base", "small"))
            settings = Settings()
            widget = ModelManagerWidget(settings, service=service)
            selected = []
            widget.model_path_selected.connect(selected.append)

            widget.findChild(QPushButton, "modelAction:base").click()

            expected = str(managed_model_path(model_spec("base"), root))
            self.assertEqual(selected, [expected])
            self.assertEqual(settings.model_path, expected)
            self.assertEqual(
                widget.findChild(QLabel, "modelStatus:base").text(), "Active"
            )
            self.assertFalse(
                widget.findChild(QPushButton, "modelDelete:base").isVisible()
            )

    def test_progress_and_errors_are_inline(self):
        with tempfile.TemporaryDirectory() as directory:
            widget = ModelManagerWidget(
                Settings(), service=FakeService(directory)
            )
            widget._show_progress("tiny", "Downloading", 42)
            progress = widget.findChild(QProgressBar, "modelProgress:tiny")
            self.assertEqual(progress.value(), 42)
            self.assertEqual(
                widget.findChild(QLabel, "modelPhase:tiny").text(),
                "Downloading",
            )

            widget._show_error("tiny", "Network unavailable")

            self.assertIn(
                "Network unavailable",
                widget.findChild(QLabel, "modelError:tiny").text(),
            )

    def test_success_automatically_selects_the_downloaded_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = FakeService(root)
            settings = Settings()
            widget = ModelManagerWidget(settings, service=service)
            selected = []
            widget.model_path_selected.connect(selected.append)
            path = managed_model_path(model_spec("tiny"), root)
            service.installed.add("tiny")

            widget._download_succeeded("tiny", str(path))

            self.assertEqual(settings.model_path, str(path))
            self.assertEqual(selected, [str(path)])

    def test_delete_visibility_distinguishes_managed_and_bundled_models(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = FakeService(
                root, ("base", "small"), bundled_small=True
            )
            widget = ModelManagerWidget(Settings(), service=service)

            self.assertTrue(
                widget.findChild(QPushButton, "modelDelete:base").isVisibleTo(
                    widget
                )
            )
            self.assertFalse(
                widget.findChild(QPushButton, "modelDelete:small").isVisible()
            )

            widget.findChild(QPushButton, "modelDelete:base").click()

            self.assertEqual(service.deleted[0][0], "base")
            self.assertEqual(
                service.deleted[0][1], Path(widget._active_path())
            )
            self.assertEqual(
                widget.findChild(QLabel, "modelStatus:base").text(),
                "Not downloaded",
            )

    def test_delete_failure_is_rendered_inline(self):
        class FailingDeleteService(FakeService):
            def delete(self, model_id, *, active_path):
                raise ModelManagerError("Delete was refused")

        with tempfile.TemporaryDirectory() as directory:
            widget = ModelManagerWidget(
                Settings(), service=FailingDeleteService(directory, ("base",))
            )

            widget.findChild(QPushButton, "modelDelete:base").click()

            self.assertIn(
                "Delete was refused",
                widget.findChild(QLabel, "modelError:base").text(),
            )

    def test_only_one_download_runs_and_shutdown_cancels_it(self):
        class BlockingService(FakeService):
            def __init__(self, root):
                super().__init__(root)
                self.started = threading.Event()
                self.install_calls = []

            def install(self, model_id, *, progress, cancel_event):
                self.install_calls.append(model_id)
                self.started.set()
                cancel_event.wait(2)
                if cancel_event.is_set():
                    raise ModelDownloadCancelled("cancelled")
                return managed_model_path(model_spec(model_id), self.root)

        with tempfile.TemporaryDirectory() as directory:
            service = BlockingService(directory)
            widget = ModelManagerWidget(Settings(), service=service)
            tiny_action = widget.findChild(QPushButton, "modelAction:tiny")
            base_action = widget.findChild(QPushButton, "modelAction:base")

            tiny_action.click()
            self.assertTrue(service.started.wait(1))
            self.assertEqual(tiny_action.text(), "Cancel")
            self.assertFalse(base_action.isEnabled())
            base_action.click()
            self.assertEqual(service.install_calls, ["tiny"])
            worker = widget._worker

            widget.shutdown()

            self.assertIsNotNone(worker)
            self.assertFalse(worker.isRunning())


class ModelDownloadThreadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _run(self, service):
        thread = ModelDownloadThread(service, "tiny")
        result = {"phase": [], "installed": [], "cancelled": [], "failed": []}
        thread.phase_changed.connect(lambda *args: result["phase"].append(args))
        thread.installed.connect(result["installed"].append)
        thread.cancelled.connect(lambda: result["cancelled"].append(True))
        thread.failed.connect(result["failed"].append)
        thread.start()
        self.assertTrue(thread.wait(2000))
        self.app.processEvents()
        return result

    def test_worker_forwards_progress_and_installed_path(self):
        class Service:
            def install(self, model_id, *, progress, cancel_event):
                progress("Downloading", 37)
                return Path("/models") / model_id

        result = self._run(Service())

        self.assertEqual(result["phase"], [("Downloading", 37)])
        self.assertEqual(result["installed"], ["/models/tiny"])
        self.assertFalse(result["failed"])

    def test_worker_reports_expected_and_unexpected_errors_safely(self):
        class ExpectedFailure:
            def install(self, model_id, *, progress, cancel_event):
                raise ModelManagerError("Disk full")

        class UnexpectedFailure:
            def install(self, model_id, *, progress, cancel_event):
                raise ValueError("sensitive detail")

        self.assertEqual(self._run(ExpectedFailure())["failed"], ["Disk full"])
        self.assertEqual(
            self._run(UnexpectedFailure())["failed"],
            ["The model download failed unexpectedly."],
        )

    def test_cancel_sets_event_and_emits_cancelled(self):
        entered = threading.Event()

        class Service:
            def install(self, model_id, *, progress, cancel_event):
                entered.set()
                cancel_event.wait(1)
                if cancel_event.is_set():
                    raise ModelDownloadCancelled("cancelled")
                raise AssertionError("cancellation event was not set")

        service = Service()
        thread = ModelDownloadThread(service, "tiny")
        cancelled = []
        thread.cancelled.connect(lambda: cancelled.append(True))
        thread.start()
        self.assertTrue(entered.wait(1))

        thread.cancel()

        self.assertTrue(thread.wait(2000))
        self.app.processEvents()
        self.assertEqual(cancelled, [True])


if __name__ == "__main__":
    unittest.main()
