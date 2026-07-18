"""Screenshot-matched shell backed by the proven dictation runtime."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QElapsedTimer,
    QPoint,
    QPropertyAnimation,
    QTimer,
    Qt,
    Slot,
)
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtWidgets import (
    QApplication, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QStackedWidget, QStyle, QSystemTrayIcon, QTextEdit,
    QVBoxLayout, QWidget,
)

from soundflow._legacy.ui_module import (
    AnimatedRecordButton, MainWindow as LegacyMainWindow,
    RecordingOverlay, VoiceOrb,
)
from soundflow.core.settings import SettingsStore, default_model_path
from soundflow.core.state import DictationState
from soundflow.design import ANIMATION_NORMAL, BODY_FONT
from soundflow.history import HistoryPage, HistoryStore
from soundflow.playground import PlaygroundPage
from soundflow.preferences import PreferencesPage
from soundflow.preferences.system_check import run_system_check
from soundflow.ui.pages import DictationPage
from soundflow.ui.widgets import AppSidebar, StatusBar, WindowChrome


class MainWindow(LegacyMainWindow):
    """Four-page interface retaining audio, hotkey, tray and paste behavior."""

    def __init__(self, *args, **kwargs) -> None:
        store = args[1] if len(args) > 1 else kwargs.get("store")
        settings = args[0] if args else kwargs.get("settings")
        if settings is not None:
            result = run_system_check(settings)
            if settings.inference_device == "cuda" and result.effective_device == "cpu":
                settings.inference_device = "cpu"
                if isinstance(store, SettingsStore):
                    store.save(settings)
        history_path = None
        if isinstance(store, SettingsStore) and store.path != SettingsStore().path:
            history_path = store.path.parent / "history.db"
        self._history_store = HistoryStore(history_path)
        self._session_elapsed = QElapsedTimer()
        self._pending_runtime_rebuild = False
        self._drag_origin: QPoint | None = None
        self._current_page = "dictation"
        self._page_effect: QGraphicsOpacityEffect | None = None
        self._page_animation: QPropertyAnimation | None = None
        super().__init__(*args, **kwargs)
        self._last_runtime_signature = self._runtime_settings_signature()
        self.playground_page.set_injector(self.injector)
        self.dictation_page.set_language(self.settings.language)
        self._update_meta()

    def _build_ui(self) -> None:
        self.setWindowTitle("Soundflow")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(900, 600)
        self.resize(1120, 720)
        QApplication.instance().setFont(QFont(BODY_FONT, 10))

        surface = QWidget()
        surface.setObjectName("appSurface")
        outer = QVBoxLayout(surface)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.sidebar = AppSidebar()
        body.addWidget(self.sidebar)

        content = QWidget()
        content.setObjectName("contentSurface")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        chrome_row = QHBoxLayout()
        chrome_row.setContentsMargins(0, 8, 10, 0)
        chrome_row.addStretch(1)
        self.window_chrome = WindowChrome()
        chrome_row.addWidget(self.window_chrome)
        content_layout.addLayout(chrome_row)

        self.pages = QStackedWidget()
        self.dictation_page = DictationPage()
        self.history_page = HistoryPage(self._history_store)
        self.playground_page = PlaygroundPage()
        self.preferences_page = PreferencesPage(self.settings, self.store)
        self.preferences_page.settings_saved.connect(self._preferences_saved)
        self._page_indices = {
            "dictation": self.pages.addWidget(self.dictation_page),
            "history": self.pages.addWidget(self.history_page),
            "playground": self.pages.addWidget(self.playground_page),
            "preferences": self.pages.addWidget(self.preferences_page),
        }
        content_layout.addWidget(self.pages, 1)
        body.addWidget(content, 1)
        outer.addLayout(body, 1)
        self.persistent_status = StatusBar()
        self.persistent_status.hide()
        self.setCentralWidget(surface)

        self.sidebar.page_requested.connect(self.navigate)
        self.dictation_page.language_changed.connect(self._language_changed)
        self.dictation_page.dictation_toggled.connect(self.toggle_dictation)
        self.playground_page.insert_requested.connect(self._insert_at_cursor)
        self.window_chrome.minimize.connect(self.showMinimized)
        self.window_chrome.maximize.connect(self._toggle_maximized)
        self.window_chrome.close.connect(self.close)
        self._build_runtime_compatibility_widgets()

    def _build_runtime_compatibility_widgets(self) -> None:
        self.editor = QTextEdit(self)
        self.editor.hide()
        self.meter = QProgressBar(self)
        self.meter.hide()
        self.voice_orb = VoiceOrb(self)
        self.voice_orb.hide()
        self.record_button = AnimatedRecordButton("", self)
        self.record_button.hide()
        for name in (
            "status", "status_caption", "status_dot", "word_count",
            "model_status", "device_status", "microphone_status",
            "hotkey_indicator",
        ):
            widget = QLabel(self)
            widget.hide()
            setattr(self, name, widget)
        self.hotkey_retry_button = QPushButton("Set up global shortcut", self)
        self.hotkey_retry_button.clicked.connect(self.retry_setup)
        self.hotkey_retry_button.hide()
        self.ptt_keycaps, self.ptt_pluses = [], []
        self.language_picker = self.dictation_page.language_picker
        self.overlay = RecordingOverlay()

    def apply_appearance(self, appearance: str) -> None:
        """Apply the palette and keep the Preferences selector synchronized."""
        super().apply_appearance(appearance)
        preferences = getattr(self, "preferences_page", None)
        if preferences is not None:
            preferences.general_tab._theme.set_value(
                self.settings.appearance, emit=False
            )

    @Slot(str)
    def navigate(self, key: str) -> None:
        index = self._page_indices.get(key)
        if index is None:
            return
        if key == self._current_page and self.pages.currentIndex() == index:
            return
        if self._current_page == "preferences" and key != "preferences":
            self._save_preferences()
        self._current_page = key
        self.sidebar.select(key)
        self.pages.setCurrentIndex(index)
        self._animate_page_in(self.pages.currentWidget())
        if key == "history":
            self.history_page.refresh()
        elif key == "dictation":
            self.dictation_page.setFocus()

    def _animate_page_in(self, page: QWidget) -> None:
        """Give navigation a restrained fade rather than an abrupt swap."""
        if self._page_animation is not None:
            self._page_animation.stop()
        if self._page_effect is not None:
            try:
                owner = self._page_effect.parent()
            except RuntimeError:
                owner = None
            if isinstance(owner, QWidget) and owner.graphicsEffect() is self._page_effect:
                owner.setGraphicsEffect(None)
            self._page_effect = None

        effect = QGraphicsOpacityEffect(page)
        effect.setOpacity(0.18)
        page.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(ANIMATION_NORMAL)
        animation.setStartValue(0.18)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        def finish() -> None:
            if self._page_effect is effect:
                self._page_effect = None
            if self._page_animation is animation:
                self._page_animation = None
            if page.graphicsEffect() is effect:
                page.setGraphicsEffect(None)

        animation.finished.connect(finish)
        self._page_effect = effect
        self._page_animation = animation
        animation.start()

    @Slot(str)
    def _language_changed(self, language: str) -> None:
        if not language or language == self.settings.language:
            return
        if self.state.state not in {DictationState.IDLE, DictationState.ERROR}:
            self.dictation_page.set_language(self.settings.language)
            self.persistent_status.set_status("Stop dictation first", "error")
            return
        self.settings.language = language
        self.store.save(self.settings)
        self._rebuild_runtime()
        self._update_meta()

    @Slot()
    def toggle_dictation(self) -> None:
        if self.state.state in {DictationState.IDLE, DictationState.ERROR}:
            self._start_dictation(auto_insert=self.settings.auto_insert)
        elif self.state.state in {DictationState.RECORDING, DictationState.PAUSED}:
            self._stop_dictation()

    def _ptt_down(self) -> None:
        if self.state.state in {DictationState.IDLE, DictationState.ERROR}:
            self._start_dictation(auto_insert=self.settings.auto_insert)

    def _start_dictation(self, *, auto_insert: bool) -> None:
        self._session_elapsed.start()
        super()._start_dictation(auto_insert=auto_insert)

    def _apply_state(self, state: DictationState, reason: str) -> None:
        del reason
        visual = {
            DictationState.RECORDING: "recording",
            DictationState.DRAINING: "draining",
        }.get(state, "idle")
        self.dictation_page.set_state(visual)
        label, indicator = {
            DictationState.IDLE: ("System Ready", "ready"),
            DictationState.RECORDING: ("Listening", "recording"),
            DictationState.PAUSED: ("Paused", "ready"),
            DictationState.DRAINING: ("Transcribing", "recording"),
            DictationState.ERROR: ("Setup needs attention", "error"),
        }[state]
        self.persistent_status.set_status(label, indicator)
        if state is DictationState.RECORDING:
            if self.settings.show_dictation_widget:
                self.overlay.show_recording(self.settings.push_to_talk_hotkey)
            self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        elif state is DictationState.DRAINING:
            if self.settings.show_dictation_widget:
                self.overlay.show_processing()
        else:
            self.overlay.hide_animated()
            self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

    @Slot(float)
    def _set_level(self, level: float) -> None:
        self.dictation_page.push_level(level)
        if self.settings.show_dictation_widget:
            self.overlay.set_level(level)

    @Slot(str)
    def _append_text(self, text: str) -> None:
        cleaned = text.strip()
        if cleaned:
            self._session_fragments.append(cleaned)
            if self.settings.auto_copy:
                QApplication.clipboard().setText(" ".join(self._session_fragments))

    @Slot()
    def _pipeline_finished(self) -> None:
        text = " ".join(self._session_fragments).strip()
        duration = (
            max(0.0, self._session_elapsed.elapsed() / 1000.0)
            if self._session_elapsed.isValid() else 0.0
        )
        if text and self.settings.auto_save_transcripts:
            self._history_store.add(text, duration)
            self.history_page.refresh()
        if self.state.state is DictationState.DRAINING:
            self.state.drained()
        if (
            self._pending_runtime_rebuild
            and self.state.state in {DictationState.IDLE, DictationState.ERROR}
        ):
            self._rebuild_runtime()
            self._last_runtime_signature = self._runtime_settings_signature()
            self._pending_runtime_rebuild = False
        if text and self._auto_insert_after_drain:
            QApplication.clipboard().setText(text)
            QTimer.singleShot(80, self._paste_now)
        self._auto_insert_after_drain = False

    def _insert_at_cursor(self, text: str) -> None:
        if text:
            QApplication.clipboard().setText(text)
            self._paste_now()

    def _set_hotkey_indicator(
        self, state: str, text: str, *, retry: str | None = None
    ) -> None:
        self.hotkey_indicator.setText(text)
        self._setup_retry_target = retry or "hotkey"
        self.hotkey_retry_button.setText(
            "Set up automatic paste" if retry == "injector"
            else "Set up global shortcut"
        )
        self.hotkey_retry_button.setVisible(retry is not None)
        status = "error" if state == "error" else (
            "recording" if state == "recording" else "ready"
        )
        self.persistent_status.set_status(text.replace("●", "").strip(), status)

    def _refresh_shortcut_display(self) -> None:
        self._update_meta()

    def _show_runtime_error(self, message: str) -> None:
        self.persistent_status.set_status(message, "error")
        self.overlay.hide_animated()
        self._auto_insert_after_drain = False
        if self.state.state is DictationState.DRAINING:
            self.state.drained()

    def open_settings(self) -> None:
        self.navigate("preferences")

    def _save_preferences(self) -> None:
        self.preferences_page.save()

    @Slot()
    def _preferences_saved(self) -> None:
        self.apply_appearance(self.settings.appearance)
        self.dictation_page.set_language(self.settings.language)
        signature = self._runtime_settings_signature()
        if (
            signature != self._last_runtime_signature
            and self.state.state in {DictationState.IDLE, DictationState.ERROR}
        ):
            self._rebuild_runtime()
            self._last_runtime_signature = signature
            self._pending_runtime_rebuild = False
        elif signature != self._last_runtime_signature:
            self._pending_runtime_rebuild = True
        self._update_meta()

    def _runtime_settings_signature(self) -> tuple:
        return (
            self.settings.model_path, self.settings.language,
            self.settings.inference_device, self.settings.microphone,
            self.settings.global_hotkeys, self.settings.push_to_talk_hotkey,
            self.settings.silence_duration_ms,
        )

    def _update_meta(self) -> None:
        model = Path(self.settings.model_path or default_model_path()).name
        model = model.replace("faster-whisper-", "").replace("-", " ").title()
        self.dictation_page.set_meta(
            f"{model or 'Whisper Small'} · INT8 · "
            f"{self.settings.inference_device.upper()} · System microphone"
        )
        self.dictation_page.set_shortcut(
            self.settings.push_to_talk_hotkey
        )
        labels = {
            "auto": "Auto detect", "en": "English (US)", "bn": "বাংলা",
            "hi": "Hindi", "es": "Spanish", "fr": "French",
            "de": "German", "ja": "Japanese",
        }
        self.persistent_status.set_language(
            labels.get(self.settings.language, self.settings.language)
        )

    def _toggle_maximized(self) -> None:
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 46:
            self._drag_origin = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_origin)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_origin = None
        super().mouseReleaseEvent(event)

    def closeEvent(self, event) -> None:
        if self.tray.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            self.tray.showMessage(
                "Soundflow is still running",
                "Use the tray menu to quit.",
                QSystemTrayIcon.MessageIcon.Information,
                2500,
            )
        else:
            event.accept()

    def shutdown(self) -> None:
        self._history_store.close()
        super().shutdown()


__all__ = ["MainWindow"]
