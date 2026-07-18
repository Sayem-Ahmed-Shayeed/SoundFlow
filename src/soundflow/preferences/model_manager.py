"""Compact, non-blocking controls for Soundflow's local Whisper models."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEventLoop, QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from soundflow.core.settings import Settings, default_model_path
from soundflow.design import SPACE_1, SPACE_2, SPACE_3, SPACE_4
from soundflow.models.catalog import MODEL_CATALOG, managed_model_path
from soundflow.models.service import (
    ModelDownloadCancelled,
    ModelManagerError,
    ModelService,
)

LOGGER = logging.getLogger(__name__)
_LIVE_WORKERS: set[ModelDownloadThread] = set()
_QUIT_COORDINATOR_ATTRIBUTE = "_soundflow_model_quit_coordinator"
_QUIT_STATUS_PROPERTY = "soundflowModelQuitStatus"
_QUIT_POLL_MS = 20
_QUIT_PENDING_NOTICE_MS = 5000


def _running_workers() -> tuple[ModelDownloadThread, ...]:
    return tuple(worker for worker in _LIVE_WORKERS if worker.isRunning())


class _ApplicationQuitCoordinator(QObject):
    """Keep Qt responsive while model workers finish before final quit."""

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._app = app
        self._pending = False
        self._final_quit_started = False
        self._pending_since = 0.0
        self._pending_notice_logged = False
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(_QUIT_POLL_MS)
        self._poll_timer.timeout.connect(self._poll)
        app.aboutToQuit.connect(self._finish_direct_quit_safely)

    def request_quit(self) -> None:
        if self._pending or self._final_quit_started:
            return
        self._pending = True
        self._pending_since = time.monotonic()
        self._pending_notice_logged = False
        self._app.setProperty(_QUIT_STATUS_PROPERTY, "waiting-for-model-workers")
        self._cancel_running_workers()
        if _running_workers():
            self._poll_timer.start()
        else:
            self._finish_routed_quit()

    def worker_registered(self, worker: ModelDownloadThread) -> None:
        if self._pending or self._final_quit_started:
            worker.cancel()

    def _cancel_running_workers(self) -> None:
        for worker in _running_workers():
            worker.cancel()

    def _report_pending_if_needed(self) -> None:
        elapsed_ms = (time.monotonic() - self._pending_since) * 1000
        if not self._pending_notice_logged and elapsed_ms >= _QUIT_PENDING_NOTICE_MS:
            self._pending_notice_logged = True
            LOGGER.warning(
                "Soundflow is still waiting for a model download worker to stop"
            )

    @Slot()
    def _poll(self) -> None:
        self._cancel_running_workers()
        if not _running_workers():
            self._finish_routed_quit()
            return
        self._report_pending_if_needed()

    def _finish_routed_quit(self) -> None:
        if self._final_quit_started:
            return
        self._poll_timer.stop()
        self._pending = False
        self._final_quit_started = True
        self._app.setProperty(_QUIT_STATUS_PROPERTY, "ready-to-quit")
        self._app.quit()

    @Slot()
    def _finish_direct_quit_safely(self) -> None:
        """Fallback for external quit requests that bypass the coordinator."""
        if not _running_workers():
            return
        self._pending = True
        self._pending_since = time.monotonic()
        self._pending_notice_logged = False
        self._app.setProperty(_QUIT_STATUS_PROPERTY, "waiting-for-model-workers")
        self._cancel_running_workers()

        fallback_loop = QEventLoop()
        fallback_poll = QTimer()
        fallback_poll.setInterval(_QUIT_POLL_MS)

        def poll_until_safe() -> None:
            self._cancel_running_workers()
            if not _running_workers():
                fallback_loop.quit()
                return
            self._report_pending_if_needed()

        fallback_poll.timeout.connect(poll_until_safe)
        fallback_poll.start()
        poll_until_safe()
        if _running_workers():
            fallback_loop.exec()
        fallback_poll.stop()
        self._pending = False
        self._app.setProperty(_QUIT_STATUS_PROPERTY, "ready-to-quit")


def _quit_coordinator() -> _ApplicationQuitCoordinator | None:
    app = QApplication.instance()
    if app is None:
        return None
    coordinator = getattr(app, _QUIT_COORDINATOR_ATTRIBUTE, None)
    if coordinator is None:
        coordinator = _ApplicationQuitCoordinator(app)
        setattr(app, _QUIT_COORDINATOR_ATTRIBUTE, coordinator)
    return coordinator


def request_application_quit() -> None:
    """Begin the responsive, cooperative application shutdown handshake."""
    coordinator = _quit_coordinator()
    if coordinator is not None:
        coordinator.request_quit()


def install_application_quit_coordinator() -> None:
    """Install the direct-quit fallback before other teardown slots."""
    _quit_coordinator()


def _register_worker(worker: ModelDownloadThread) -> None:
    _LIVE_WORKERS.add(worker)
    coordinator = _quit_coordinator()
    if coordinator is not None:
        coordinator.worker_registered(worker)


class ModelDownloadThread(QThread):
    """Install one model without blocking Qt's main thread."""

    SHUTDOWN_WAIT_MS = 5000

    phase_changed = Signal(str, int)
    installed = Signal(str)
    cancelled = Signal()
    failed = Signal(str)

    def __init__(self, service, model_id: str, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._model_id = model_id
        self._cancel_event = threading.Event()
        self.finished.connect(self._release_retained)

    def cancel(self) -> None:
        self._cancel_event.set()

    @Slot()
    def stop(self) -> None:
        """Cooperatively cancel, retaining a slow worker until it exits."""
        self.cancel()
        if not self.isRunning() or self.wait(self.SHUTDOWN_WAIT_MS):
            return
        self.requestInterruption()
        self.setParent(None)
        _LIVE_WORKERS.add(self)

    @Slot()
    def _release_retained(self) -> None:
        _LIVE_WORKERS.discard(self)

    def run(self) -> None:
        try:
            path = self._service.install(
                self._model_id,
                progress=self.phase_changed.emit,
                cancel_event=self._cancel_event,
            )
        except ModelDownloadCancelled:
            self.cancelled.emit()
        except ModelManagerError as exc:
            self.failed.emit(str(exc))
        except Exception:
            self.failed.emit("The model download failed unexpectedly.")
        else:
            self.installed.emit(str(path))


@dataclass(slots=True)
class _ModelRow:
    container: QWidget
    status: QLabel
    action: QPushButton
    delete: QPushButton
    progress: QProgressBar
    phase: QLabel
    error: QLabel


class ModelManagerWidget(QWidget):
    """Show and manage the five supported local Whisper models."""

    model_path_selected = Signal(str)

    def __init__(
        self,
        settings: Settings,
        *,
        service: ModelService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("modelManagerCard")
        self.setAccessibleName("Whisper model manager")
        self._settings = settings
        self._service = service or ModelService()
        self._rows: dict[str, _ModelRow] = {}
        self._worker: ModelDownloadThread | None = None
        self._worker_model_id: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        layout.setSpacing(SPACE_2)

        heading = QLabel("Speech recognition model")
        heading.setObjectName("headingText")
        layout.addWidget(heading)

        description = QLabel(
            "Choose a local Whisper model. Larger models download more data "
            "and generally trade speed for accuracy."
        )
        description.setObjectName("mutedText")
        description.setWordWrap(True)
        layout.addWidget(description)

        for spec in MODEL_CATALOG:
            row = self._create_row(spec)
            self._rows[spec.model_id] = row
            layout.addWidget(row.container)

        self._refresh_rows()

    def _create_row(self, spec) -> _ModelRow:
        container = QWidget()
        container.setObjectName(f"modelRow:{spec.model_id}")
        container.setAccessibleName(f"{spec.display_name} model")
        outer = QVBoxLayout(container)
        outer.setContentsMargins(SPACE_3, SPACE_2, SPACE_3, SPACE_2)
        outer.setSpacing(SPACE_1)

        main = QHBoxLayout()
        main.setSpacing(SPACE_2)

        copy = QVBoxLayout()
        copy.setSpacing(SPACE_1)
        title_row = QHBoxLayout()
        title_row.setSpacing(SPACE_2)
        title = QLabel(spec.display_name)
        title.setObjectName(f"modelName:{spec.model_id}")
        title_row.addWidget(title)
        if spec.recommended:
            badge = QLabel("Recommended")
            badge.setObjectName(f"modelRecommended:{spec.model_id}")
            badge.setAccessibleName(f"{spec.display_name} is recommended")
            title_row.addWidget(badge)
        title_row.addStretch(1)
        copy.addLayout(title_row)

        guidance = QLabel(f"{spec.guidance} · approximately {spec.download_size}")
        guidance.setObjectName(f"modelGuidance:{spec.model_id}")
        guidance.setWordWrap(True)
        copy.addWidget(guidance)
        main.addLayout(copy, 1)

        status = QLabel()
        status.setObjectName(f"modelStatus:{spec.model_id}")
        status.setAccessibleName(f"{spec.display_name} model status")
        status.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        main.addWidget(status)

        delete = QPushButton("Delete")
        delete.setObjectName(f"modelDelete:{spec.model_id}")
        delete.setAccessibleName(f"Delete {spec.display_name} model")
        delete.setCursor(Qt.CursorShape.PointingHandCursor)
        delete.clicked.connect(
            lambda _checked=False, model_id=spec.model_id: self._delete(model_id)
        )
        main.addWidget(delete)

        action = QPushButton()
        action.setObjectName(f"modelAction:{spec.model_id}")
        action.setAccessibleName(f"{spec.display_name} model action")
        action.setCursor(Qt.CursorShape.PointingHandCursor)
        action.clicked.connect(
            lambda _checked=False, model_id=spec.model_id: self._act(model_id)
        )
        main.addWidget(action)
        outer.addLayout(main)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(SPACE_2)
        progress = QProgressBar()
        progress.setObjectName(f"modelProgress:{spec.model_id}")
        progress.setAccessibleName(f"{spec.display_name} download progress")
        progress.setRange(0, 100)
        progress.setFormat("%p%")
        progress.setTextVisible(True)
        progress.hide()
        progress_row.addWidget(progress, 1)

        phase = QLabel()
        phase.setObjectName(f"modelPhase:{spec.model_id}")
        phase.setAccessibleName(f"{spec.display_name} download phase")
        phase.hide()
        progress_row.addWidget(phase)
        outer.addLayout(progress_row)

        error = QLabel()
        error.setObjectName(f"modelError:{spec.model_id}")
        error.setAccessibleName(f"{spec.display_name} model error")
        error.setWordWrap(True)
        error.hide()
        outer.addWidget(error)

        return _ModelRow(container, status, action, delete, progress, phase, error)

    def _active_path(self) -> str:
        return str(Path(self._settings.model_path or default_model_path()).expanduser())

    @staticmethod
    def _same_path(first: str | Path, second: str | Path) -> bool:
        return Path(first).expanduser().resolve() == Path(second).expanduser().resolve()

    @staticmethod
    def _same_lexical_path(first: str | Path, second: str | Path) -> bool:
        return Path(first).expanduser().absolute() == Path(second).expanduser().absolute()

    @staticmethod
    def _contains_path(parent: str | Path, child: str | Path) -> bool:
        lexical_parent = Path(parent).expanduser().absolute()
        lexical_child = Path(child).expanduser().absolute()
        lexically_contained = (
            lexical_child == lexical_parent
            or lexical_child.is_relative_to(lexical_parent)
        )
        resolved_parent = lexical_parent.resolve()
        resolved_child = lexical_child.resolve()
        resolved_contained = (
            resolved_child == resolved_parent
            or resolved_child.is_relative_to(resolved_parent)
        )
        return lexically_contained or resolved_contained

    def _managed_path(self, model_id: str) -> Path:
        return managed_model_path(
            next(item for item in MODEL_CATALOG if item.model_id == model_id),
            self._service.root,
        )

    def _refresh_rows(self) -> None:
        active_path = self._active_path()
        busy = self._worker is not None
        for spec in MODEL_CATALOG:
            row = self._rows[spec.model_id]
            installed = self._service.installed_path(spec.model_id)
            active = installed is not None and self._same_path(installed, active_path)
            managed_path = self._managed_path(spec.model_id)
            managed = (
                installed is not None
                and not managed_path.is_symlink()
                and self._same_lexical_path(installed, managed_path)
            )
            protects_active = (
                installed is not None
                and self._contains_path(installed, active_path)
            )

            if active:
                row.status.setText("Active")
                row.action.setText("Active")
                row.action.setEnabled(False)
            elif installed is not None:
                row.status.setText("Installed")
                row.action.setText("Use")
                row.action.setEnabled(not busy)
            else:
                row.status.setText("Not downloaded")
                row.action.setText("Download")
                row.action.setEnabled(not busy)

            row.delete.setVisible(bool(managed and not protects_active))
            row.delete.setEnabled(not busy)
            if busy and self._worker_model_id == spec.model_id:
                row.action.setText("Cancel")
                row.action.setEnabled(True)

    def _act(self, model_id: str) -> None:
        if self._worker is not None:
            if self._worker_model_id == model_id:
                self._worker.cancel()
                row = self._rows[model_id]
                row.action.setText("Cancelling…")
                row.action.setEnabled(False)
                row.phase.setText("Cancelling")
                row.phase.show()
            return

        installed = self._service.installed_path(model_id)
        if installed is not None:
            self._select(installed)
            return
        self._start_download(model_id)

    def _select(self, path: str | Path) -> None:
        final_path = str(Path(path).expanduser())
        self._settings.model_path = final_path
        self._refresh_rows()
        self.model_path_selected.emit(final_path)

    def _start_download(self, model_id: str) -> None:
        if self._worker is not None:
            return
        row = self._rows[model_id]
        row.error.clear()
        row.error.hide()
        self._show_progress(model_id, "Preparing", 0)

        worker = ModelDownloadThread(
            self._service, model_id, QApplication.instance()
        )
        self._worker = worker
        self._worker_model_id = model_id
        worker.phase_changed.connect(self._worker_phase_changed)
        worker.installed.connect(self._worker_installed)
        worker.cancelled.connect(self._worker_cancelled)
        worker.failed.connect(self._worker_failed)
        worker.finished.connect(self._worker_finished)
        worker.finished.connect(worker.deleteLater)
        self.destroyed.connect(worker.stop)
        _register_worker(worker)
        self._refresh_rows()
        worker.start()

    def _worker_phase_changed(self, phase: str, percent: int) -> None:
        if self.sender() is self._worker and self._worker_model_id is not None:
            self._show_progress(self._worker_model_id, phase, percent)

    def _worker_installed(self, path: str) -> None:
        if self.sender() is self._worker and self._worker_model_id is not None:
            self._download_succeeded(self._worker_model_id, path)

    def _worker_cancelled(self) -> None:
        if self.sender() is self._worker and self._worker_model_id is not None:
            self._download_cancelled(self._worker_model_id)

    def _worker_failed(self, message: str) -> None:
        if self.sender() is self._worker and self._worker_model_id is not None:
            self._download_failed(self._worker_model_id, message)

    def _show_progress(self, model_id: str, phase: str, percent: int) -> None:
        row = self._rows[model_id]
        row.progress.setValue(max(0, min(100, int(percent))))
        row.progress.show()
        row.phase.setText(phase)
        row.phase.show()
        row.error.clear()
        row.error.hide()

    def _show_error(self, model_id: str, message: str) -> None:
        row = self._rows[model_id]
        row.progress.hide()
        row.phase.hide()
        row.error.setText(message)
        row.error.show()

    def _download_succeeded(self, model_id: str, path: str) -> None:
        row = self._rows[model_id]
        row.progress.setValue(100)
        row.progress.hide()
        row.phase.hide()
        self._select(path)

    def _download_cancelled(self, model_id: str) -> None:
        row = self._rows[model_id]
        row.progress.hide()
        row.phase.setText("Download cancelled")
        row.phase.show()

    def _download_failed(self, model_id: str, message: str) -> None:
        self._show_error(model_id, message)

    def _worker_finished(self) -> None:
        if self.sender() is not self._worker:
            return
        self._worker = None
        self._worker_model_id = None
        self._refresh_rows()

    def _delete(self, model_id: str) -> None:
        if self._worker is not None:
            return
        row = self._rows[model_id]
        row.error.clear()
        row.error.hide()
        try:
            self._service.delete(
                model_id, active_path=Path(self._active_path())
            )
        except ModelManagerError as exc:
            self._show_error(model_id, str(exc))
        except Exception:
            self._show_error(model_id, "The model could not be deleted.")
        else:
            self._refresh_rows()

    def shutdown(self) -> None:
        """Cancel a worker without allowing shutdown to block indefinitely."""
        worker = self._worker
        if worker is None:
            return
        worker.stop()
        self.destroyed.disconnect(worker.stop)
        if self._worker is worker:
            self._worker = None
            self._worker_model_id = None


__all__ = [
    "install_application_quit_coordinator",
    "ModelDownloadThread",
    "ModelManagerWidget",
    "request_application_quit",
]
