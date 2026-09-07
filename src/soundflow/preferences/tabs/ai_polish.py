"""AI Polish tab — optional OpenRouter cleanup for transcripts."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from soundflow.ui.widgets import PreferenceToggleRow

from soundflow.design import (
    BODY_FONT,
    CONTROL_HEIGHT_SM,
    FONT_BODY,
    FONT_HEADING,
    FONT_SMALL,
    SPACE_2,
    SPACE_3,
    SPACE_4,
)


class AiPolishTab(QWidget):
    """AI Polish tab. Disabled by default; local-first stays the default."""

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("aiPolishTab")
        self._settings = settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        outer.setSpacing(SPACE_4)

        card = QWidget()
        card.setObjectName("preferencesCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        layout.setSpacing(SPACE_2)

        title = QLabel("AI Polish")
        title.setFont(QFont(BODY_FONT, FONT_HEADING))
        title.setObjectName("headingText")
        layout.addWidget(title)

        note = QLabel(
            "Off by default. When enabled, transcript text is sent to the selected "
            "provider for grammar, punctuation, and filler-word cleanup. Audio never "
            "leaves this machine — only the text you choose to polish."
        )
        note.setObjectName("mutedText")
        note.setFont(QFont(BODY_FONT, FONT_SMALL))
        note.setWordWrap(True)
        layout.addWidget(note)

        self._enable = PreferenceToggleRow(
            "Enable AI Polish",
            "Allow transcripts to be sent to the selected provider for cleanup.",
            checked=bool(getattr(settings, "ai_cleanup_enabled", False)),
        )
        layout.addWidget(self._enable)
        self._auto = PreferenceToggleRow(
            "Polish automatically after dictation",
            "Clean each transcript before it is saved and inserted.",
            checked=bool(getattr(settings, "ai_auto_clean", False)),
        )
        layout.addWidget(self._auto)

        form = QFormLayout()
        form.setSpacing(SPACE_2)

        self._provider = QComboBox()
        self._provider.setObjectName("compactPreferenceField")
        self._provider.setFixedHeight(CONTROL_HEIGHT_SM)
        self._provider.addItem("Gemini (fast)", "gemini")
        self._provider.addItem("OpenRouter", "openrouter")
        self._keys = {
            "gemini": getattr(settings, "gemini_api_key", ""),
            "openrouter": getattr(settings, "openrouter_api_key", ""),
        }
        self._models = {
            "gemini": getattr(settings, "gemini_model", "") or "gemini-2.5-flash",
            "openrouter": getattr(settings, "openrouter_model", ""),
        }
        provider = getattr(settings, "ai_provider", "gemini")
        self._provider.setCurrentIndex(max(0, self._provider.findData(provider)))
        self._provider.currentIndexChanged.connect(self._on_provider_changed)
        form.addRow("Provider", self._provider)

        self._key = QLineEdit(self._keys[self._current_provider()])
        self._key.setObjectName("compactPathField")
        self._key.setEchoMode(QLineEdit.EchoMode.Password)
        self._key.setFont(QFont(BODY_FONT, FONT_BODY))
        self._key.setFixedHeight(CONTROL_HEIGHT_SM)
        self._key.editingFinished.connect(self._stash_fields)
        form.addRow("API key", self._key)

        self._model = QLineEdit(self._models[self._current_provider()])
        self._model.setObjectName("compactPathField")
        self._model.setFont(QFont(BODY_FONT, FONT_BODY))
        self._model.setFixedHeight(CONTROL_HEIGHT_SM)
        self._model.editingFinished.connect(self._stash_fields)
        form.addRow("Model", self._model)
        self._sync_placeholders()

        self._preset = QComboBox()
        self._preset.setObjectName("compactPreferenceField")
        self._preset.setFixedHeight(CONTROL_HEIGHT_SM)
        for label, value in (
            ("Clean up", "clean"),
            ("Concise rewrite", "concise"),
            ("Custom instruction", "custom"),
        ):
            self._preset.addItem(label, value)
        current = getattr(settings, "ai_preset", "clean")
        index = self._preset.findData(current)
        self._preset.setCurrentIndex(max(0, index))
        form.addRow("Style", self._preset)

        layout.addLayout(form)

        self._custom = QTextEdit(getattr(settings, "ai_custom_instruction", ""))
        self._custom.setObjectName("historyEditor")
        self._custom.setPlaceholderText(
            "Custom instruction, e.g. 'Turn this into bullet points in Bangla…'"
        )
        self._custom.setFixedHeight(72)
        layout.addWidget(self._custom)

        row = QHBoxLayout()
        row.setSpacing(SPACE_2)
        self._test_button = QPushButton("Send test polish")
        self._test_button.setObjectName("compactBrowseButton")
        self._test_button.setFixedHeight(CONTROL_HEIGHT_SM)
        self._test_button.clicked.connect(self._on_test)
        row.addWidget(self._test_button)
        self._test_result = QLabel("")
        self._test_result.setObjectName("mutedText")
        self._test_result.setFont(QFont(BODY_FONT, FONT_SMALL))
        self._test_result.setWordWrap(True)
        row.addWidget(self._test_result, 1)
        layout.addLayout(row)
        outer.addWidget(card)
        outer.addStretch(1)

    def _current_provider(self) -> str:
        return self._provider.currentData() or "gemini"

    def _stash_fields(self) -> None:
        provider = self._current_provider()
        self._keys[provider] = self._key.text()
        self._models[provider] = self._model.text()

    def _sync_placeholders(self) -> None:
        if self._current_provider() == "gemini":
            self._key.setPlaceholderText(
                "AIza… from Google AI Studio (stored only on this machine)"
            )
            self._model.setPlaceholderText("e.g. gemini-2.5-flash")
        else:
            self._key.setPlaceholderText("sk-or-v1-… (stored only on this machine)")
            self._model.setPlaceholderText("e.g. openai/gpt-oss-20b:free")

    def _on_provider_changed(self) -> None:
        previous = (
            "openrouter" if self._current_provider() == "gemini" else "gemini"
        )
        self._keys[previous] = self._key.text()
        self._models[previous] = self._model.text()
        provider = self._current_provider()
        self._key.setText(self._keys[provider])
        self._model.setText(self._models[provider])
        self._sync_placeholders()

    def _snapshot(self):
        from soundflow.core.settings import Settings

        base = self._settings
        self._stash_fields()
        return Settings(
            ai_cleanup_enabled=self._enable.switch.isChecked(),
            ai_auto_clean=self._auto.switch.isChecked(),
            ai_provider=self._current_provider(),
            gemini_api_key=self._keys["gemini"],
            gemini_model=self._models["gemini"],
            openrouter_api_key=self._keys["openrouter"],
            openrouter_model=self._models["openrouter"],
            ai_preset=self._preset.currentData() or "clean",
            ai_custom_instruction=self._custom.toPlainText(),
            language=getattr(base, "language", "auto"),
        )

    def _on_test(self) -> None:
        from soundflow.core.llm import LlmError, polish_in_background

        self._test_button.setEnabled(False)
        self._test_result.setText("Polishing…")
        snapshot = self._snapshot()

        def done(cleaned: str) -> None:
            self._test_button.setEnabled(True)
            self._test_result.setText(f"OK: {cleaned[:160]}")

        def failed(message: str) -> None:
            self._test_button.setEnabled(True)
            self._test_result.setText(message)

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

    def write_back(self, settings) -> None:
        self._stash_fields()
        settings.ai_cleanup_enabled = self._enable.switch.isChecked()
        settings.ai_auto_clean = self._auto.switch.isChecked()
        settings.ai_provider = self._current_provider()
        settings.gemini_api_key = self._keys["gemini"].strip()
        settings.gemini_model = self._models["gemini"].strip()
        settings.openrouter_api_key = self._keys["openrouter"].strip()
        settings.openrouter_model = self._models["openrouter"].strip()
        settings.ai_preset = self._preset.currentData() or "clean"
        settings.ai_custom_instruction = self._custom.toPlainText().strip()

    def refresh_from_settings(self, settings=None) -> None:
        source = settings if settings is not None else self._settings
        for switch, value in (
            (self._enable.switch, source.ai_cleanup_enabled),
            (self._auto.switch, source.ai_auto_clean),
        ):
            switch.blockSignals(True)
            switch.setChecked(bool(value))
            switch.blockSignals(False)
        self._keys = {
            "gemini": source.gemini_api_key,
            "openrouter": source.openrouter_api_key,
        }
        self._models = {
            "gemini": source.gemini_model or "gemini-2.5-flash",
            "openrouter": source.openrouter_model,
        }
        index = self._provider.findData(source.ai_provider)
        self._provider.blockSignals(True)
        self._provider.setCurrentIndex(max(0, index))
        self._provider.blockSignals(False)
        self._key.setText(self._keys[self._current_provider()])
        self._model.setText(self._models[self._current_provider()])
        self._sync_placeholders()
        index = self._preset.findData(source.ai_preset)
        self._preset.blockSignals(True)
        self._preset.setCurrentIndex(max(0, index))
        self._preset.blockSignals(False)
        self._custom.setPlainText(source.ai_custom_instruction)


__all__ = ["AiPolishTab"]
