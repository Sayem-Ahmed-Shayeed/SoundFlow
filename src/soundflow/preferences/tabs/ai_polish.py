"""AI Polish tab: optional online cleanup of dictated text. Off by default."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from soundflow.preferences.widgets import PreferenceTab, SettingsRow
from soundflow.ui.widgets import SegmentedControl, ToggleSwitch

PROVIDERS = (("gemini", "Gemini"), ("openrouter", "OpenRouter"))
GEMINI_MODELS = (("gemini-2.5-flash", "Gemini 2.5 Flash"), ("gemini-2.5-pro", "Gemini 2.5 Pro"))
STYLES = (("clean", "Clean up"), ("concise", "Shorter"), ("custom", "Custom"))
STYLE_DESCRIPTIONS = {
    "clean": "Fixes punctuation, capitals and filler words. Keeps your words.",
    "concise": "Says the same thing in fewer words.",
    "custom": "",
}
PRIVACY_TEXT = (
    "Rewrites the text of a dictation with an online AI service. Only the text is "
    "sent, never your voice."
)
KEY_HINTS = {
    "gemini": "Stored only on this computer. Get a free key from Google AI Studio.",
    "openrouter": "Stored only on this computer. Create one at openrouter.ai/keys.",
}
KEY_PLACEHOLDERS = {"gemini": "AIza…", "openrouter": "sk-or-v1-…"}
OPENROUTER_MODEL_PLACEHOLDER = "For example openai/gpt-oss-20b:free"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


class AiPolishTab(PreferenceTab):
    """AI Polish tab. Disabled by default; local-first stays the default."""

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__("aiPolishTab", "AI Polish", parent)
        self._settings = settings
        self._keys = {
            "gemini": settings.gemini_api_key,
            "openrouter": settings.openrouter_api_key,
        }
        self._models = {
            "gemini": settings.gemini_model or DEFAULT_GEMINI_MODEL,
            "openrouter": settings.openrouter_model,
        }
        # The provider whose fields are on screen. The segmented control has
        # already changed by the time its signal arrives, so it can't be used
        # to decide where the typed values belong.
        self._shown_provider = settings.ai_provider

        switch = self.add_group()
        self._enable = ToggleSwitch("Use AI Polish")
        self._enable.setChecked(bool(settings.ai_cleanup_enabled))
        self._enable.toggled.connect(self._sync_visibility)
        switch.add_row(SettingsRow("Use AI Polish", PRIVACY_TEXT, self._enable))

        # Service: provider, key, model
        self._service = self.add_group("Service")
        self._provider = SegmentedControl(
            PROVIDERS, settings.ai_provider, accessible_name="Provider"
        )
        self._provider.changed.connect(self._on_provider_changed)
        self._service.add_row(SettingsRow("Provider", "", self._provider))

        self._key = QLineEdit()
        self._key.setObjectName("compactPathField")
        self._key.setEchoMode(QLineEdit.EchoMode.Password)
        self._key.setFixedHeight(36)
        self._key.editingFinished.connect(self._stash_fields)
        self._check = QPushButton("Check key")
        self._check.setObjectName("quietButton")
        self._check.setFixedHeight(36)
        self._check.setCursor(Qt.CursorShape.PointingHandCursor)
        self._check.clicked.connect(self._check_key)
        key_block = QWidget()
        key_layout = QVBoxLayout(key_block)
        key_layout.setContentsMargins(0, 4, 0, 0)
        key_layout.setSpacing(8)
        key_row = QHBoxLayout()
        key_row.setContentsMargins(0, 0, 0, 0)
        key_row.setSpacing(8)
        key_row.addWidget(self._key, 1)
        key_row.addWidget(self._check)
        key_layout.addLayout(key_row)
        self._key_result = QLabel("")
        self._key_result.setObjectName("aiKeyResult")
        self._key_result.setWordWrap(True)
        self._key_result.setVisible(False)
        key_layout.addWidget(self._key_result)
        self._key_row = SettingsRow("API key", KEY_HINTS["gemini"])
        self._key_row.add_below_description(key_block)
        self._service.add_row(self._key_row)

        self._gemini_model = QComboBox()
        self._gemini_model.setObjectName("compactPreferenceField")
        self._gemini_model.setFixedHeight(36)
        self._gemini_model.setMinimumContentsLength(18)
        self._model_row = SettingsRow(
            "Model", "Flash is fast and free for light use.", self._gemini_model
        )
        self._openrouter_model = QLineEdit()
        self._openrouter_model.setObjectName("compactPathField")
        self._openrouter_model.setPlaceholderText(OPENROUTER_MODEL_PLACEHOLDER)
        self._openrouter_model.setFixedHeight(36)
        self._openrouter_model.setMinimumWidth(280)
        self._openrouter_model.editingFinished.connect(self._stash_fields)
        self._openrouter_row = SettingsRow("Model", "", self._openrouter_model)
        self._service.add_row(self._model_row)
        self._service.add_row(self._openrouter_row)

        # Style
        self._style_group = self.add_group("How to polish")
        self._style = SegmentedControl(STYLES, settings.ai_preset, accessible_name="Style")
        self._style.changed.connect(self._sync_style)
        self._style_row = SettingsRow("Style", "", self._style)
        self._style_group.add_row(self._style_row)
        self._custom_row = SettingsRow("Your instruction", "", None)
        self._custom = QTextEdit(settings.ai_custom_instruction)
        self._custom.setObjectName("historyEditor")
        self._custom.setPlaceholderText(
            "For example: turn this into bullet points in Bangla"
        )
        self._custom.setFixedHeight(72)
        self._custom_row.add_below_description(self._custom)
        self._style_group.add_row(self._custom_row)

        self._auto = ToggleSwitch("Polish every dictation")
        self._auto.setChecked(bool(settings.ai_auto_clean))
        self._style_group.add_row(
            SettingsRow(
                "Polish every dictation",
                "Runs before the text is pasted and adds a second or two. When off, "
                "use Polish on a single transcript.",
                self._auto,
            )
        )

        self._fill_gemini_models(settings.gemini_model or DEFAULT_GEMINI_MODEL)
        self._load_provider_fields(settings.ai_provider)
        self._sync_style(settings.ai_preset)
        self._sync_visibility(self._enable.isChecked())
        self.finish()

    # -- helpers ------------------------------------------------------------
    def _current_provider(self) -> str:
        return self._shown_provider

    def _fill_gemini_models(self, current: str) -> None:
        self._gemini_model.blockSignals(True)
        self._gemini_model.clear()
        for value, label in GEMINI_MODELS:
            self._gemini_model.addItem(label, value)
        if current and self._gemini_model.findData(current) < 0:
            # Keep a model stored from elsewhere selectable rather than lose it.
            self._gemini_model.addItem(current, current)
        self._gemini_model.setCurrentIndex(max(0, self._gemini_model.findData(current)))
        self._gemini_model.blockSignals(False)

    def _load_provider_fields(self, provider: str) -> None:
        self._key.blockSignals(True)
        self._key.setText(self._keys[provider])
        self._key.blockSignals(False)
        self._openrouter_model.blockSignals(True)
        self._openrouter_model.setText(self._models["openrouter"])
        self._openrouter_model.blockSignals(False)
        self._key_row.set_description(KEY_HINTS[provider])
        self._key.setPlaceholderText(KEY_PLACEHOLDERS[provider])
        self._model_row.setVisible(provider == "gemini")
        self._openrouter_row.setVisible(provider == "openrouter")
        self._key_result.setVisible(False)

    def _stash_fields(self, *_args) -> None:
        provider = self._shown_provider
        self._keys[provider] = self._key.text().strip()
        if provider == "gemini":
            self._models["gemini"] = self._gemini_model.currentData() or DEFAULT_GEMINI_MODEL
        else:
            self._models["openrouter"] = self._openrouter_model.text().strip()

    def _on_provider_changed(self, provider: str) -> None:
        self._stash_fields()
        self._shown_provider = provider
        self._load_provider_fields(provider)
        self._sync_visibility(self._enable.isChecked())

    def _sync_visibility(self, enabled: bool) -> None:
        self._service.parentWidget().setVisible(bool(enabled))
        self._style_group.parentWidget().setVisible(bool(enabled))

    def _sync_style(self, style: str) -> None:
        self._style_row.set_description(STYLE_DESCRIPTIONS.get(style, ""))
        self._custom_row.setVisible(style == "custom")

    # -- key check ------------------------------------------------------------
    def _set_key_result(self, text: str, *, ok: bool) -> None:
        self._key_result.setText(text)
        self._key_result.setProperty("tone", "ok" if ok else "error")
        self._key_result.style().unpolish(self._key_result)
        self._key_result.style().polish(self._key_result)
        self._key_result.setVisible(True)

    def _snapshot(self):
        from soundflow.core.settings import Settings

        self._stash_fields()
        base = self._settings
        return Settings(
            ai_cleanup_enabled=self._enable.isChecked(),
            ai_auto_clean=self._auto.isChecked(),
            ai_provider=self._current_provider(),
            gemini_api_key=self._keys["gemini"],
            gemini_model=self._models["gemini"],
            openrouter_api_key=self._keys["openrouter"],
            openrouter_model=self._models["openrouter"],
            ai_preset=self._style.value(),
            ai_custom_instruction=self._custom.toPlainText(),
            language=getattr(base, "language", "auto"),
        )

    def _check_key(self) -> None:
        from soundflow.core.llm import LlmError, polish_in_background

        self._check.setEnabled(False)
        self._set_key_result("Checking the key…", ok=True)
        snapshot = self._snapshot()

        def done(_cleaned: str) -> None:
            self._check.setEnabled(True)
            self._set_key_result("The key works.", ok=True)

        def failed(message: str) -> None:
            self._check.setEnabled(True)
            self._set_key_result(message, ok=False)

        try:
            polish_in_background(
                "um this is a test of the ai polish feature you know",
                snapshot,
                done,
                failed,
                parent=self,
            )
        except LlmError as exc:
            failed(str(exc))

    # -- settings -------------------------------------------------------------
    def write_back(self, settings) -> None:
        self._stash_fields()
        settings.ai_cleanup_enabled = self._enable.isChecked()
        settings.ai_auto_clean = self._auto.isChecked()
        settings.ai_provider = self._current_provider()
        settings.gemini_api_key = self._keys["gemini"]
        settings.gemini_model = self._models["gemini"]
        settings.openrouter_api_key = self._keys["openrouter"]
        settings.openrouter_model = self._models["openrouter"]
        settings.ai_preset = self._style.value()
        settings.ai_custom_instruction = self._custom.toPlainText().strip()

    def refresh_from_settings(self, settings=None) -> None:
        source = settings if settings is not None else self._settings
        self._keys = {
            "gemini": source.gemini_api_key,
            "openrouter": source.openrouter_api_key,
        }
        self._models = {
            "gemini": source.gemini_model or DEFAULT_GEMINI_MODEL,
            "openrouter": source.openrouter_model,
        }
        for switch, value in (
            (self._enable, source.ai_cleanup_enabled),
            (self._auto, source.ai_auto_clean),
        ):
            switch.blockSignals(True)
            switch.setChecked(bool(value))
            switch.blockSignals(False)
        self._provider.set_value(source.ai_provider)
        self._shown_provider = source.ai_provider
        self._fill_gemini_models(self._models["gemini"])
        self._load_provider_fields(source.ai_provider)
        self._style.set_value(source.ai_preset)
        self._sync_style(source.ai_preset)
        self._custom.setPlainText(source.ai_custom_instruction)
        self._sync_visibility(self._enable.isChecked())


__all__ = ["AiPolishTab"]
