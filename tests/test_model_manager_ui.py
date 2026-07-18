import os
import subprocess
import sys
import tempfile
import threading
import textwrap
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import (
    QAbstractAnimation,
    QCoreApplication,
    QEasingCurve,
    QEvent,
)
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QProgressBar, QPushButton

from soundflow.core.settings import Settings
from soundflow.design import ANIMATION_CONTROL
from soundflow.models.catalog import MODEL_CATALOG, managed_model_path, model_spec
from soundflow.models.service import (
    ModelDownloadCancelled,
    ModelManagerError,
    ModelService,
)
from soundflow.preferences import model_manager
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
                widget.findChild(QPushButton, "modelDelete:base").isVisibleTo(
                    widget
                )
            )

    def test_progress_and_errors_are_inline(self):
        with tempfile.TemporaryDirectory() as directory:
            widget = ModelManagerWidget(
                Settings(), service=FakeService(directory)
            )
            widget._show_progress(
                "tiny",
                "Downloading",
                45,
                225_000_000,
                500_000_000,
            )
            progress = widget.findChild(QProgressBar, "modelProgress:tiny")
            animation = widget._rows["tiny"].progress_animation
            self.assertEqual(animation.duration(), ANIMATION_CONTROL)
            self.assertEqual(
                animation.easingCurve().type(),
                QEasingCurve.Type.OutCubic,
            )
            self.assertEqual(
                animation.state(),
                QAbstractAnimation.State.Running,
            )
            self.assertTrue(progress.isTextVisible())
            self.assertEqual(progress.format(), "225.0 MB / 500.0 MB")
            self.assertEqual(progress.text(), "225.0 MB / 500.0 MB")
            self.assertNotIn("%", progress.text())
            self.assertEqual(
                widget.findChild(QLabel, "modelPhase:tiny").text(),
                "Downloading",
            )
            QTest.qWait(ANIMATION_CONTROL + 30)
            self.assertEqual(progress.value(), 45)

            widget._show_progress(
                "tiny",
                "Downloading",
                80,
                400_000_000,
                500_000_000,
            )
            QTest.qWait(ANIMATION_CONTROL // 2)
            widget._show_progress(
                "tiny",
                "Downloading",
                65,
                325_000_000,
                500_000_000,
            )
            QTest.qWait(ANIMATION_CONTROL + 30)
            self.assertEqual(progress.value(), 65)
            self.assertEqual(progress.format(), "325.0 MB / 500.0 MB")

            widget._show_progress("tiny", "Downloading", 0, 0, 0)
            self.assertEqual(
                animation.state(),
                QAbstractAnimation.State.Stopped,
            )
            self.assertEqual(
                (progress.minimum(), progress.maximum()),
                (0, 0),
            )
            self.assertEqual(progress.format(), "")

            widget._show_progress("tiny", "Verifying", 100, 0, 0)
            self.assertEqual(
                animation.state(),
                QAbstractAnimation.State.Stopped,
            )
            self.assertEqual(
                (progress.minimum(), progress.maximum()),
                (0, 100),
            )
            self.assertEqual(progress.value(), 100)
            self.assertEqual(progress.format(), "")

            widget._show_error("tiny", "Network unavailable")
            self.assertEqual(
                animation.state(),
                QAbstractAnimation.State.Stopped,
            )

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

    def test_symlinked_catalog_model_never_exposes_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "models"
            custom = Path(directory) / "custom-model"
            custom.mkdir()
            (custom / "model.bin").write_bytes(b"model")
            (custom / "config.json").write_text("{}", encoding="utf-8")
            root.mkdir()
            managed = managed_model_path(model_spec("base"), root)
            managed.symlink_to(custom, target_is_directory=True)

            widget = ModelManagerWidget(
                Settings(model_path=str(Path(directory) / "other-model")),
                service=ModelService(root),
            )

            self.assertEqual(
                widget.findChild(QLabel, "modelStatus:base").text(),
                "Installed",
            )
            self.assertFalse(
                widget.findChild(QPushButton, "modelDelete:base").isVisibleTo(
                    widget
                )
            )
            self.assertTrue(custom.is_dir())
            self.assertTrue((custom / "model.bin").is_file())

    def test_managed_parent_of_active_custom_model_never_exposes_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "models"
            target = managed_model_path(model_spec("base"), root)
            target.mkdir(parents=True)
            (target / "model.bin").write_bytes(b"parent model")
            (target / "config.json").write_text("{}", encoding="utf-8")
            active = target / "custom-active"
            active.mkdir()
            (active / "model.bin").write_bytes(b"active model")
            (active / "config.json").write_text("{}", encoding="utf-8")

            widget = ModelManagerWidget(
                Settings(model_path=str(active)),
                service=ModelService(root),
            )

            delete = widget.findChild(QPushButton, "modelDelete:base")
            self.assertFalse(delete.isVisibleTo(widget))
            self.assertTrue((target / "model.bin").is_file())
            self.assertTrue((active / "model.bin").is_file())

    def test_managed_parent_containing_active_alias_never_exposes_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "models"
            target = managed_model_path(model_spec("base"), root)
            target.mkdir(parents=True)
            (target / "model.bin").write_bytes(b"parent model")
            (target / "config.json").write_text("{}", encoding="utf-8")
            external = Path(directory) / "external-active"
            external.mkdir()
            (external / "model.bin").write_bytes(b"active model")
            (external / "config.json").write_text("{}", encoding="utf-8")
            alias = target / "active-alias"
            alias.symlink_to(external, target_is_directory=True)

            widget = ModelManagerWidget(
                Settings(model_path=str(alias)),
                service=ModelService(root),
            )

            delete = widget.findChild(QPushButton, "modelDelete:base")
            self.assertFalse(delete.isVisibleTo(widget))
            self.assertTrue((target / "model.bin").is_file())
            self.assertTrue(alias.is_symlink())
            self.assertTrue((external / "model.bin").is_file())

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

    def test_non_cooperative_worker_is_retained_without_forced_termination(self):
        class NonCooperativeService(FakeService):
            def __init__(self, root):
                super().__init__(root)
                self.started = threading.Event()

            def install(self, model_id, *, progress, cancel_event):
                self.started.set()
                time.sleep(0.25)
                return managed_model_path(model_spec(model_id), self.root)

        with tempfile.TemporaryDirectory() as directory:
            service = NonCooperativeService(directory)
            widget = ModelManagerWidget(Settings(), service=service)
            widget.findChild(QPushButton, "modelAction:tiny").click()
            self.assertTrue(service.started.wait(1))
            worker = widget._worker

            with (
                patch.object(ModelDownloadThread, "SHUTDOWN_WAIT_MS", 10),
                patch.object(
                    ModelDownloadThread, "terminate", autospec=True
                ) as terminate,
            ):
                started = time.monotonic()
                widget.shutdown()
                elapsed = time.monotonic() - started

            self.assertLess(elapsed, 0.15)
            self.assertIsNotNone(worker)
            terminate.assert_not_called()
            self.assertTrue(worker.isRunning())
            self.assertIsNone(worker.parent())
            self.assertIn(worker, model_manager._LIVE_WORKERS)
            self.assertTrue(worker.wait(1000))
            self.app.processEvents()
            self.assertNotIn(worker, model_manager._LIVE_WORKERS)

    def test_shutdown_retains_worker_until_late_worker_exits(self):
        class TerminationDisabledService(FakeService):
            def __init__(self, root):
                super().__init__(root)
                self.started = threading.Event()
                self.release = threading.Event()

            def install(self, model_id, *, progress, cancel_event):
                self.started.set()
                self.release.wait(0.25)
                return managed_model_path(model_spec(model_id), self.root)

        with tempfile.TemporaryDirectory() as directory:
            service = TerminationDisabledService(directory)
            widget = ModelManagerWidget(Settings(), service=service)
            widget.findChild(QPushButton, "modelAction:tiny").click()
            self.assertTrue(service.started.wait(1))
            worker = widget._worker

            with patch.object(ModelDownloadThread, "SHUTDOWN_WAIT_MS", 10):
                started = time.monotonic()
                widget.shutdown()
                elapsed = time.monotonic() - started

            self.assertLess(elapsed, 0.1)
            self.assertIsNone(widget._worker)
            self.assertIsNotNone(worker)
            self.assertTrue(worker.isRunning())
            self.assertIsNone(worker.parent())
            self.assertIn(worker, model_manager._LIVE_WORKERS)

            widget.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.app.processEvents()
            self.assertTrue(worker.isRunning())
            self.assertIn(worker, model_manager._LIVE_WORKERS)

            service.release.set()
            self.assertTrue(worker.wait(1000))
            self.app.processEvents()
            self.assertNotIn(worker, model_manager._LIVE_WORKERS)

    def test_destroying_widget_with_active_worker_does_not_abort(self):
        script = textwrap.dedent(
            """
            import os
            import threading
            from pathlib import Path

            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

            from PySide6.QtCore import QCoreApplication, QEvent
            from PySide6.QtWidgets import QApplication, QPushButton
            from shiboken6 import isValid
            from soundflow.core.settings import Settings
            from soundflow.models.service import ModelDownloadCancelled
            from soundflow.preferences.model_manager import ModelManagerWidget

            class Service:
                def __init__(self):
                    self.root = Path("/tmp/soundflow-widget-destroy-test")
                    self.started = threading.Event()

                def installed_path(self, model_id):
                    return None

                def install(self, model_id, *, progress, cancel_event):
                    self.started.set()
                    cancel_event.wait(1)
                    if cancel_event.is_set():
                        raise ModelDownloadCancelled("cancelled")
                    return self.root / model_id

                def delete(self, model_id, *, active_path):
                    raise AssertionError("delete is not part of this test")

            app = QApplication.instance() or QApplication([])
            service = Service()
            widget = ModelManagerWidget(Settings(), service=service)
            widget.findChild(QPushButton, "modelAction:tiny").click()
            assert service.started.wait(1)
            worker = widget._worker
            widget.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()
            assert worker is not None
            assert not worker.isRunning()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()
            assert not isValid(worker)
            print("widget_destroyed_worker_stopped")
            """
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONPATH": ".vendor/python:src"},
            capture_output=True,
            text=True,
            timeout=5,
        )

        self.assertEqual(
            result.returncode,
            0,
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("widget_destroyed_worker_stopped", result.stdout)
        self.assertNotIn("QThread: Destroyed", result.stderr)

    def test_routed_quit_keeps_event_loop_responsive_until_worker_finishes(self):
        script = textwrap.dedent(
            """
            import os
            import threading
            import time
            from pathlib import Path

            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QApplication, QPushButton
            from shiboken6 import isValid
            from soundflow.core.settings import Settings
            from soundflow.models.service import ModelDownloadCancelled
            from soundflow.preferences.model_manager import (
                ModelManagerWidget,
                request_application_quit,
            )

            class TemporarilyNonCooperativeService:
                def __init__(self):
                    self.root = Path("/tmp/soundflow-routed-quit-test")
                    self.started = threading.Event()

                def installed_path(self, model_id):
                    return None

                def install(self, model_id, *, progress, cancel_event):
                    self.started.set()
                    deadline = time.monotonic() + 0.25
                    while time.monotonic() < deadline:
                        time.sleep(0.01)
                    if cancel_event.is_set():
                        raise ModelDownloadCancelled("cancelled")
                    return self.root / model_id

                def delete(self, model_id, *, active_path):
                    raise AssertionError("delete is not part of this test")

            app = QApplication.instance() or QApplication([])
            service = TemporarilyNonCooperativeService()
            widget = ModelManagerWidget(Settings(), service=service)
            widget.findChild(QPushButton, "modelAction:tiny").click()
            assert service.started.wait(1)
            worker = widget._worker
            heartbeats = []
            quit_emissions = []
            app.aboutToQuit.connect(lambda: quit_emissions.append(True))
            QTimer.singleShot(40, lambda: heartbeats.append(True))
            QTimer.singleShot(0, request_application_quit)
            QTimer.singleShot(10, request_application_quit)
            result = app.exec()
            assert worker is not None
            assert not isValid(worker) or not worker.isRunning()
            assert heartbeats == [True]
            assert quit_emissions == [True]
            print(f"routed_quit_responsive:{result}")
            """
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONPATH": ".vendor/python:src"},
            capture_output=True,
            text=True,
            timeout=5,
        )

        self.assertEqual(
            result.returncode,
            0,
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("routed_quit_responsive:0", result.stdout)
        self.assertNotIn("QThread: Destroyed", result.stderr)

    def test_direct_quit_fallback_remains_responsive_and_safe(self):
        script = textwrap.dedent(
            """
            import os
            import threading
            import time
            from pathlib import Path

            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QApplication, QPushButton
            from shiboken6 import isValid
            from soundflow.core.settings import Settings
            from soundflow.models.service import ModelDownloadCancelled
            from soundflow.preferences.model_manager import ModelManagerWidget

            class TemporarilyNonCooperativeService:
                def __init__(self):
                    self.root = Path("/tmp/soundflow-direct-quit-test")
                    self.started = threading.Event()

                def installed_path(self, model_id):
                    return None

                def install(self, model_id, *, progress, cancel_event):
                    self.started.set()
                    deadline = time.monotonic() + 0.25
                    while time.monotonic() < deadline:
                        time.sleep(0.01)
                    if cancel_event.is_set():
                        raise ModelDownloadCancelled("cancelled")
                    return self.root / model_id

                def delete(self, model_id, *, active_path):
                    raise AssertionError("delete is not part of this test")

            app = QApplication.instance() or QApplication([])
            service = TemporarilyNonCooperativeService()
            widget = ModelManagerWidget(Settings(), service=service)
            widget.findChild(QPushButton, "modelAction:tiny").click()
            assert service.started.wait(1)
            worker = widget._worker
            heartbeats = []
            shutdown_states = []

            def late_widget_shutdown():
                shutdown_states.append(
                    app.property("soundflowModelQuitStatus")
                )
                widget.shutdown()

            app.aboutToQuit.connect(late_widget_shutdown)
            QTimer.singleShot(40, lambda: heartbeats.append(True))
            QTimer.singleShot(0, app.quit)
            result = app.exec()
            assert worker is not None
            assert not isValid(worker) or not worker.isRunning()
            assert heartbeats == [True]
            assert shutdown_states == ["ready-to-quit"]
            print(f"direct_quit_responsive:{result}")
            """
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONPATH": ".vendor/python:src"},
            capture_output=True,
            text=True,
            timeout=5,
        )

        self.assertEqual(
            result.returncode,
            0,
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("direct_quit_responsive:0", result.stdout)
        self.assertNotIn("QThread: Destroyed", result.stderr)

    def test_routed_quit_exits_promptly_for_cooperative_worker(self):
        script = textwrap.dedent(
            """
            import os
            import threading
            import time
            from pathlib import Path

            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QApplication, QPushButton
            from shiboken6 import isValid
            from soundflow.core.settings import Settings
            from soundflow.models.service import ModelDownloadCancelled
            from soundflow.preferences.model_manager import (
                ModelManagerWidget,
                request_application_quit,
            )

            class CooperativeService:
                def __init__(self):
                    self.root = Path("/tmp/soundflow-fast-quit-test")
                    self.started = threading.Event()

                def installed_path(self, model_id):
                    return None

                def install(self, model_id, *, progress, cancel_event):
                    self.started.set()
                    cancel_event.wait(2)
                    raise ModelDownloadCancelled("cancelled")

                def delete(self, model_id, *, active_path):
                    raise AssertionError("delete is not part of this test")

            app = QApplication.instance() or QApplication([])
            service = CooperativeService()
            widget = ModelManagerWidget(Settings(), service=service)
            widget.findChild(QPushButton, "modelAction:tiny").click()
            assert service.started.wait(1)
            worker = widget._worker
            QTimer.singleShot(0, request_application_quit)
            started = time.monotonic()
            result = app.exec()
            elapsed = time.monotonic() - started
            assert worker is not None
            assert not isValid(worker) or not worker.isRunning()
            assert elapsed < 0.5
            print(f"cooperative_quit_fast:{result}")
            """
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONPATH": ".vendor/python:src"},
            capture_output=True,
            text=True,
            timeout=5,
        )

        self.assertEqual(
            result.returncode,
            0,
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("cooperative_quit_fast:0", result.stdout)
        self.assertNotIn("QThread: Destroyed", result.stderr)


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

        self.assertEqual(result["phase"], [("Downloading", 37, 0, 0)])
        self.assertEqual(result["installed"], ["/models/tiny"])
        self.assertFalse(result["failed"])

    def test_worker_forwards_exact_download_byte_counts(self):
        class Service:
            def install(self, model_id, *, progress, cancel_event):
                progress(
                    "Downloading",
                    45,
                    225_000_000,
                    500_000_000,
                )
                return Path("/models") / model_id

        result = self._run(Service())

        self.assertEqual(
            result["phase"],
            [("Downloading", 45, 225_000_000, 500_000_000)],
        )

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
