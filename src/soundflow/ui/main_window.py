"""Screenshot-matched shell backed by the proven dictation runtime."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QElapsedTimer,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
    Slot,
)
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from soundflow.design import app_icon
from soundflow._legacy.ui_module import (
    AnimatedRecordButton,
    VoiceOrb,
)
from soundflow._legacy.ui_module import (
    MainWindow as LegacyMainWindow,
)
from soundflow.cloud.account import Account
from soundflow.cloud.sync import SyncService
from soundflow.core.settings import SettingsStore, default_model_path
from soundflow.core.state import DictationState
from soundflow.design import ANIMATION_NORMAL, BODY_FONT
from soundflow.history import HistoryPage, HistoryStore
from soundflow.hotkeys import display_hotkey
from soundflow.playground import PlaygroundPage
from soundflow.preferences import PreferencesPage
from soundflow.preferences.system_check import run_system_check
from soundflow.ui.pages import DictationPage
from soundflow.ui.widgets import AppSidebar, RecordingOverlay, StatusBar, WindowChrome
from soundflow.ui.widgets.message_dialog import ask, inform

_LOG = logging.getLogger(__name__)


class MainWindow(LegacyMainWindow):
    """Four-page interface retaining audio, hotkey, tray and paste behavior."""

    def __init__(self, *args, account: Account | None = None, **kwargs) -> None:
        self.account = account
        self._sync: SyncService | None = None
        store = args[1] if len(args) > 1 else kwargs.get("store")
        settings = args[0] if args else kwargs.get("settings")
        if settings is not None:
            # Only the GPU answer is needed here; skip the microphone scan,
            # which can take over a second while PortAudio probes devices.
            result = run_system_check(settings, list_inputs=list)
            # A GPU choice with no usable GPU would stop the model loading;
            # Automatic uses the GPU when there is one and the processor otherwise.
            if settings.inference_device == "cuda" and result.effective_device == "cpu":
                settings.inference_device = "auto"
                if isinstance(store, SettingsStore):
                    store.save(settings)
        history_path = None
        if isinstance(store, SettingsStore) and store.path != SettingsStore().path:
            history_path = store.path.parent / "history.db"
        user_id = account.user_id if account is not None else None
        self._history_store = HistoryStore(history_path, user_id=user_id)
        if user_id:
            # Transcripts saved before accounts existed belong to whoever
            # signs in first on this machine; they upload on the first sync.
            self._history_store.claim_unowned(user_id)
        self._session_elapsed = QElapsedTimer()
        self._pending_runtime_rebuild = False
        self._drag_origin: QPoint | None = None
        self._current_page = "dictation"
        self._page_effect: QGraphicsOpacityEffect | None = None
        self._page_animation: QPropertyAnimation | None = None
        self._cancelled = False
        self._last_entry_id: int | None = None
        self._last_duration = 0.0
        super().__init__(*args, **kwargs)
        self._last_runtime_signature = self._runtime_settings_signature()
        self.playground_page.set_injector(self.injector)
        self.playground_page.set_settings(self.settings)
        self.bridge.audio.connect(self._audio_frame)
        self.dictation_page.set_language(self.settings.language)
        self._update_meta()
        self._refresh_home_stats()
        self._start_cloud()
        self.dictation_page.setFocus()

    # -- account & cloud sync ------------------------------------------------
    def _start_cloud(self) -> None:
        if self.account is None or self.account.user is None:
            return
        user = self.account.user
        self.sidebar.set_account(user.display_name, user.email)
        self.dictation_page.set_user_name(user.display_name)
        self.sidebar.sign_out_requested.connect(self._confirm_sign_out)
        self._sync = SyncService(self.account, self._history_store.path, parent=self)
        self._sync.status_changed.connect(self.sidebar.set_sync_status)
        self._sync.pulled.connect(self._cloud_pulled)
        self._sync.auth_lost.connect(self._cloud_auth_lost)
        self._history_store.on_change = self._sync.request_sync
        self._sync.start()

    @Slot(int)
    def _cloud_pulled(self, _count: int) -> None:
        self._history_store.generation += 1
        if self._current_page == "history":
            self.history_page.refresh()
        self._refresh_home_stats()

    @Slot(str)
    def _cloud_auth_lost(self, message: str) -> None:
        self._show_window()
        inform(
            self,
            "You've been signed out",
            f"{message}\n\nSoundflow will restart so you can sign in again.",
            kind="warning",
        )
        self._restart_for_sign_in()

    @Slot()
    def _confirm_sign_out(self) -> None:
        if not ask(
            self,
            "Sign out of Soundflow?",
            "Transcripts that haven't synced yet stay on this computer and "
            "upload when you sign back in to this account.",
            accept_text="Sign out",
            reject_text="Stay signed in",
            kind="sign-out",
            destructive=True,
        ):
            return
        if self._sync is not None:
            self._sync.stop(timeout=1.0)
            self._sync = None
        if self.account is None:
            self._restart_for_sign_in()
            return
        # The local session is forgotten immediately; the server call runs off
        # the GUI thread so the window never freezes on a slow network.
        from soundflow.auth.dialog import run_in_background

        self.sidebar.set_sync_status("Signing out…")
        self._background_tasks = getattr(self, "_background_tasks", [])
        run_in_background(
            self.account.sign_out,
            lambda _result: self._restart_for_sign_in(),
            lambda _exc: self._restart_for_sign_in(),
            self._background_tasks,
        )

    def _restart_for_sign_in(self) -> None:
        from soundflow.app import relaunch_after_exit

        relaunch_after_exit()
        self._request_application_quit()

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
        self.history_page.ai_polish_settings_requested.connect(self._open_ai_polish_settings)
        self.playground_page = PlaygroundPage()
        self.preferences_page = PreferencesPage(self.settings, self.store)
        self.preferences_page.settings_saved.connect(self._preferences_saved)
        self.preferences_page.shortcut_permission_requested.connect(
            self._allow_shortcut
        )
        # Switch the theme on click; the debounced save follows and finds it
        # already applied.
        self.preferences_page.general_tab.appearance_changed.connect(
            self.apply_appearance
        )
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
        self.dictation_page.history_requested.connect(lambda: self.navigate("history"))
        self.dictation_page.cancel_requested.connect(self._cancel_dictation)
        self.dictation_page.recent_copy_requested.connect(self._copy_entry)
        self.dictation_page.recent_open_requested.connect(self._open_entry)
        self.dictation_page.polish_requested.connect(self._polish_result)
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
        # The setup action lives in the Dictation page banner, not floating
        # over the window.
        self.hotkey_retry_button = self.dictation_page.setup_button
        self.dictation_page.setup_requested.connect(self.retry_setup)
        self.ptt_keycaps, self.ptt_pluses = [], []
        self.language_picker = self.dictation_page.language_picker
        self.overlay = RecordingOverlay()

    def apply_appearance(self, appearance: str) -> None:
        """Apply the palette and keep the Preferences selector synchronized."""
        requested = appearance if appearance in {"light", "dark"} else "dark"
        if getattr(self, "_applied_appearance", None) == requested:
            # Re-applying the app stylesheet repolishes every widget; skip it
            # when the theme didn't change (e.g. leaving Preferences).
            self.settings.appearance = requested
            return
        self._applied_appearance = requested
        super().apply_appearance(appearance)
        dark = bool(self.property("darkAppearance"))
        QApplication.instance().setProperty("soundflowDark", dark)
        sidebar = getattr(self, "sidebar", None)
        if sidebar is not None:
            sidebar.set_dark(dark)
        history = getattr(self, "history_page", None)
        if history is not None:
            history.refresh(reset=True)
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
        if key == "preferences":
            self.preferences_page.refresh_from_settings()
        self.pages.setCurrentIndex(index)
        self._animate_page_in(self.pages.currentWidget())
        if key == "history":
            self.history_page.refresh()
        elif key == "dictation":
            self._refresh_home_stats()
            self.dictation_page.setFocus()

    def _refresh_home_stats(self) -> None:
        from soundflow.history.stats import dashboard_stats

        try:
            activity = self._history_store.activity()
            recent, _cut = self._history_store.list_previews(limit=5)
        except Exception:
            return
        self.dictation_page.set_dashboard(dashboard_stats(activity))
        self.dictation_page.set_recent([
            (entry.id, _entry_time(entry.created_at), entry.body) for entry in recent
        ])

    @Slot(int)
    def _copy_entry(self, entry_id: int) -> None:
        entry = self._history_store.get(entry_id)
        if entry is not None:
            QApplication.clipboard().setText(entry.body)

    @Slot(int)
    def _open_entry(self, entry_id: int) -> None:
        self.navigate("history")
        select = getattr(self.history_page, "select_entry", None)
        if callable(select):
            select(entry_id)

    def _animate_page_in(self, page: QWidget) -> None:
        """Pages switch instantly.

        Navigation happens many times a day; a fade only delays the content
        and renders the whole page through an offscreen buffer each frame.
        """
        del page

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
        self.preferences_page.dictation_tab.refresh_from_settings(self.settings)
        self._apply_language()
        self._update_meta()

    def _apply_language(self) -> None:
        """Switch language on the loaded model instead of rebuilding the runtime."""
        transcriber = getattr(self.pipeline, "transcriber", None)
        setter = getattr(transcriber, "set_language", None)
        if callable(setter):
            setter(self.settings.language)
        else:
            self._rebuild_runtime()
        self._last_runtime_signature = self._runtime_settings_signature()

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
        self._cancelled = False
        self.dictation_page.clear_interim()
        super()._start_dictation(auto_insert=auto_insert)

    @Slot()
    def _cancel_dictation(self) -> None:
        """Stop listening and throw the recording away: no paste, no copy."""
        if self.state.state is not DictationState.RECORDING:
            return
        self._cancelled = True
        self._auto_insert_after_drain = False
        self._stop_dictation()

    @Slot(bytes)
    def _audio_frame(self, pcm: bytes) -> None:
        self.dictation_page.push_audio(pcm)
        if self.settings.show_dictation_widget:
            self.overlay.push_audio(pcm)

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
            self.tray.setIcon(app_icon(recording=True))
        elif state is DictationState.DRAINING:
            if self.settings.show_dictation_widget:
                self.overlay.show_processing()
        else:
            self.overlay.hide_animated()
            self.tray.setIcon(app_icon())

    @Slot(float)
    def _set_level(self, level: float) -> None:
        self.dictation_page.push_level(level)
        if self.settings.show_dictation_widget:
            self.overlay.set_level(level)

    @Slot(str)
    def _append_text(self, text: str) -> None:
        cleaned = text.strip()
        self.dictation_page.clear_interim()
        if cleaned and not self._cancelled:
            self._session_fragments.append(cleaned)
            if self.settings.auto_copy:
                QApplication.clipboard().setText(" ".join(self._session_fragments))

    @Slot(str)
    def _interim_text(self, text: str) -> None:
        if self.state.state in {DictationState.RECORDING, DictationState.DRAINING}:
            self.dictation_page.set_interim(text)

    @Slot()
    def _pipeline_finished(self) -> None:
        text = "" if self._cancelled else " ".join(self._session_fragments).strip()
        duration = (
            max(0.0, self._session_elapsed.elapsed() / 1000.0)
            if self._session_elapsed.isValid() else 0.0
        )
        if (
            text
            and self.settings.ai_cleanup_enabled
            and self.settings.ai_auto_clean
        ):
            self._polish_after_dictation(text, duration)
            return
        self._finish_transcript(text, duration)

    def _polish_after_dictation(self, text: str, duration: float) -> None:
        from soundflow.core.llm import polish_in_background

        self.persistent_status.set_status("Polishing transcript…", "draining")
        self.dictation_page.set_polishing()
        if self.settings.show_dictation_widget:
            self.overlay.show_processing()

        def done(cleaned: str) -> None:
            self._finish_transcript(cleaned.strip() or text, duration)

        def failed(message: str) -> None:
            self.persistent_status.set_status(
                f"AI Polish failed — kept raw text ({message[:80]})", "error"
            )
            self._finish_transcript(text, duration)

        polish_in_background(text, self.settings, done, failed, parent=self)

    def _finish_transcript(self, text: str, duration: float) -> None:
        # Nothing here may strand the app on "Transcribing" or lose the text:
        # if saving or the pill fails, log it and still finish and paste.
        paste = bool(text) and self._auto_insert_after_drain
        outcome = "pasted" if paste else ("copied" if self.settings.auto_copy else "")
        self._last_entry_id = None
        self._last_duration = duration
        try:
            if text and self.settings.auto_save_transcripts:
                entry = self._history_store.add(text, duration)
                self._last_entry_id = getattr(entry, "id", None)
                # History rebuilds itself when opened; only refresh it now if
                # it is on screen, so pasting isn't delayed by hidden widget work.
                if self.pages.currentWidget() is self.history_page:
                    self.history_page.refresh(reset=True)
                self._refresh_home_stats()
            if text and self.settings.show_dictation_widget:
                # Before drained(): the pill confirms, then hides itself.
                self.overlay.show_done("Pasted" if paste else "Copied")
        except Exception:  # noqa: BLE001
            _LOG.exception("Finishing the transcript failed; keeping the text")
        if self.state.state is DictationState.DRAINING:
            self.state.drained()
        if text:
            self.dictation_page.set_result(text, duration, outcome)
        else:
            # Cancelled, or nothing was heard: clear the frozen recording.
            self.dictation_page.reset_ribbon()
        self._cancelled = False
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

    @Slot(str)
    def _polish_result(self, text: str) -> None:
        """Polish the finished transcript on request, then copy it."""
        from soundflow.core.llm import polish_in_background

        page = self.dictation_page
        page.set_polish_busy(True)

        def done(cleaned: str) -> None:
            polished = cleaned.strip() or text
            page.set_polish_busy(False)
            if self._last_entry_id is not None:
                try:
                    self._history_store.update(self._last_entry_id, polished)
                except Exception:  # noqa: BLE001
                    _LOG.exception("Saving the polished transcript failed")
            QApplication.clipboard().setText(polished)
            page.set_result(polished, self._last_duration, "copied")
            self._refresh_home_stats()

        def failed(message: str) -> None:
            page.set_polish_busy(False)
            page.show_error(f"AI Polish didn't finish: {message[:160]}")

        polish_in_background(text, self.settings, done, failed, parent=self)

    def _insert_at_cursor(self, text: str) -> None:
        if text:
            QApplication.clipboard().setText(text)
            self._paste_now()

    def _set_hotkey_indicator(
        self, state: str, text: str, *, retry: str | None = None
    ) -> None:
        message = _readable_status(text, self.settings.push_to_talk_hotkey)
        self.hotkey_indicator.setText(message)
        self._setup_retry_target = retry or "hotkey"
        notice = None
        if retry == "injector":
            notice = (
                "Automatic paste isn't set up yet. Allow it once and Soundflow "
                "can type into the app you're using."
            )
            action = "Allow paste"
        elif retry is not None:
            notice = (
                f"The {display_hotkey(self.settings.push_to_talk_hotkey)} shortcut "
                "needs your desktop's permission. Approve it once and it stays on."
            )
            action = "Allow shortcut"
        elif "approval" in message.lower():
            notice = "Approve the shortcut in the dialog your desktop just opened."
            action = ""
        if notice:
            self.dictation_page.set_setup_notice(notice, action)
        else:
            self.dictation_page.set_setup_notice(None)
        status = "error" if state == "error" else (
            "recording" if state == "recording" else "ready"
        )
        self.persistent_status.set_status(message, status)

    def _refresh_shortcut_display(self) -> None:
        self._update_meta()

    def _show_runtime_error(self, message: str) -> None:
        self.persistent_status.set_status(message, "error")
        self.dictation_page.clear_interim()
        self.dictation_page.show_error(message)
        self.dictation_page.reset_ribbon()
        self.overlay.hide_animated()
        self._auto_insert_after_drain = False
        if self.state.state is DictationState.DRAINING:
            self.state.drained()

    def open_settings(self) -> None:
        self.navigate("preferences")

    def _open_ai_polish_settings(self) -> None:
        self.navigate("preferences")
        self.preferences_page._open_section("ai_polish")

    def _save_preferences(self) -> None:
        self.preferences_page.save()

    @Slot()
    def _preferences_saved(self) -> None:
        self.apply_appearance(self.settings.appearance)
        self.dictation_page.set_language(self.settings.language)
        signature = self._runtime_settings_signature()
        language_only = (
            signature[:1] + signature[2:] == self._last_runtime_signature[:1]
            + self._last_runtime_signature[2:]
        )
        if language_only and signature != self._last_runtime_signature:
            if self.state.state in {DictationState.IDLE, DictationState.ERROR}:
                self._apply_language()
                signature = self._last_runtime_signature
        if signature == self._last_runtime_signature:
            self._pending_runtime_rebuild = False
        elif self.state.state in {DictationState.IDLE, DictationState.ERROR}:
            self._rebuild_runtime()
            self._last_runtime_signature = signature
            self._pending_runtime_rebuild = False
        else:
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
        from soundflow.models.catalog import MODEL_CATALOG

        folder = Path(self.settings.model_path or default_model_path()).name
        spec = next((s for s in MODEL_CATALOG if s.directory_name == folder), None)
        model = (
            spec.display_name
            if spec
            else folder.replace("faster-whisper-", "").replace("-", " ").title()
        )
        # A Bangla-only model always transcribes Bangla; show that.
        self.dictation_page.set_language_locked(
            spec.language if spec else None,
            f"{model} only understands Bangla. Choose another model in "
            "Preferences to dictate in other languages.",
        )
        self.dictation_page.set_meta(
            f"{model or 'Whisper Small'} · {self._device_label()}"
        )
        self.dictation_page.set_engine_sub("Local Whisper · INT8")
        self.dictation_page.set_shortcut(
            self.settings.push_to_talk_hotkey
        )
        self.dictation_page.set_paste_on_stop(bool(self.settings.auto_insert))
        key = (
            self.settings.gemini_api_key
            if self.settings.ai_provider == "gemini"
            else self.settings.openrouter_api_key
        )
        self.dictation_page.set_polish_available(
            bool(self.settings.ai_cleanup_enabled and key)
        )
        labels = {
            "auto": "Auto detect", "auto:en+bn": "English or বাংলা",
            "auto:en+hi": "English or Hindi", "en": "English (US)", "bn": "বাংলা",
            "hi": "Hindi", "es": "Spanish", "fr": "French",
            "de": "German", "ja": "Japanese",
        }
        self.persistent_status.set_language(
            labels.get(self.settings.language, self.settings.language)
        )

    @Slot()
    def _allow_shortcut(self) -> None:
        """System tab "Allow": ask the desktop to approve the dictation shortcut."""
        self._setup_retry_target = "hotkey"
        self.retry_setup()

    def _device_label(self) -> str:
        transcriber = getattr(getattr(self, "pipeline", None), "transcriber", None)
        active = getattr(transcriber, "active_device", None)
        if active in {"cuda", "cpu"}:
            return "GPU" if active == "cuda" else "Processor"
        return {"cuda": "GPU", "cpu": "Processor"}.get(
            self.settings.inference_device, "Automatic"
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
            event.ignore()
            self.hide()
            self._request_application_quit()

    def shutdown(self) -> None:
        if self._sync is not None:
            # Don't hold up quitting for a slow request; the sync thread is a
            # daemon and SQLite keeps each write atomic.
            self._sync.stop(timeout=1.0)
            self._sync = None
        self.preferences_page.shutdown()
        self._history_store.close()
        super().shutdown()


__all__ = ["MainWindow"]


def _entry_time(created: datetime) -> str:
    """9:21 PM today; Yesterday; Tue; or 12 Nov for older dictations."""
    today = datetime.now().date()
    day = created.date()
    if day == today:
        return created.strftime("%I:%M %p").lstrip("0")
    if (today - day).days == 1:
        return "Yesterday"
    if (today - day).days < 7:
        return created.strftime("%a")
    return f"{created.day} {created.strftime('%b')}"


def _readable_status(text: str, hotkey: str) -> str:
    """Turn legacy all-caps status strings into sentence case."""
    cleaned = text.replace("●", "").strip()
    keys = display_hotkey(hotkey)
    marker = "\x00"
    for variant in (keys, keys.upper(), "CTRL + ALT + SPACE"):
        cleaned = cleaned.replace(variant, marker)
    cleaned = cleaned.replace(" · ", ", ").lower()
    cleaned = cleaned[:1].upper() + cleaned[1:]
    return cleaned.replace(marker, keys)
