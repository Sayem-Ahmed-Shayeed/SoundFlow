"""Playground page: try text actions on pasted or typed text before using them elsewhere."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from soundflow.design import current_palette, icon_pixmap
from soundflow.injector import TextInjector
from soundflow.playground.actions import format_text, smart_rewrite

PLACEHOLDER = "Pick an action to see the result here."
EMPTY_INPUT = "Type or paste some text first."
ACTION_WIDTH = 216


class _ActionCard(QPushButton):
    """Action card: icon and title on one line, a short description below."""

    def __init__(
        self,
        glyph: str,
        title: str,
        hint: str,
        *,
        checkable: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("playAction")
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(title)
        self.setAccessibleDescription(hint)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(2)

        head = QHBoxLayout()
        head.setSpacing(8)
        icon_lbl = QLabel()
        icon_lbl.setObjectName("playActionIcon")
        icon_lbl.setFixedSize(16, 16)
        self._glyph = glyph
        self._icon = icon_lbl
        self._paint_icon()
        head.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("playActionTitle")
        head.addWidget(title_lbl, 1)
        layout.addLayout(head)

        hint_lbl = QLabel(hint)
        hint_lbl.setObjectName("playActionText")
        hint_lbl.setWordWrap(True)
        layout.addWidget(hint_lbl)
        for label in (icon_lbl, title_lbl, hint_lbl):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def _paint_icon(self) -> None:
        self._icon.setPixmap(icon_pixmap(self._glyph, current_palette()["text"], 16))

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        # The theme can change after the card is built: tint the icon again.
        if event.type() == QEvent.Type.StyleChange:
            self._paint_icon()

    def sizeHint(self) -> QSize:
        # The description wraps, so the height comes from the layout at the card width.
        return QSize(ACTION_WIDTH, self.layout().totalHeightForWidth(ACTION_WIDTH))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()


class PlaygroundPage(QWidget):
    """Run Format, Rewrite or Polish on a text and insert the result."""

    insert_requested = Signal(str)
    transformation_failed = Signal(str)

    def __init__(
        self,
        injector: TextInjector | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("playgroundPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._injector = injector
        self._settings = None
        self._result = ""
        self._run_id = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 6, 44, 26)
        outer.setSpacing(0)

        title = QLabel("Playground")
        title.setObjectName("pageTitle")
        outer.addWidget(title)
        outer.addSpacing(4)
        subtitle = QLabel(
            "Try a text action here before using it on your dictation in other apps."
        )
        subtitle.setObjectName("mutedText")
        outer.addWidget(subtitle)
        outer.addSpacing(20)

        columns = QHBoxLayout()
        columns.setSpacing(16)

        # Left: the text to work on.
        left = QVBoxLayout()
        left.setSpacing(8)
        input_label = QLabel("Your text")
        input_label.setObjectName("fieldLabel")
        left.addWidget(input_label)
        self._command = QPlainTextEdit()
        self._command.setObjectName("playgroundCommand")
        self._command.setPlaceholderText("Paste or dictate some text, then pick an action.")
        self._command.setMinimumHeight(180)
        left.addWidget(self._command, 1)
        submit = QShortcut(QKeySequence("Ctrl+Return"), self._command)
        submit.activated.connect(self._on_submit)
        columns.addLayout(left, 1)

        # Middle: the actions, in a fixed-width column.
        actions_host = QWidget()
        actions_host.setFixedWidth(ACTION_WIDTH)
        actions = QVBoxLayout(actions_host)
        actions.setContentsMargins(0, 27, 0, 0)
        actions.setSpacing(8)
        self._action_group = QButtonGroup(self)
        self._action_group.setExclusive(True)
        self._format_card = _ActionCard(
            "check", "Format", "Fix punctuation, capitals and fillers.", checkable=True
        )
        self._format_card.clicked.connect(self._run_format)
        self._rewrite_card = _ActionCard(
            "edit", "Rewrite", "Clearer wording, same meaning.", checkable=True
        )
        self._rewrite_card.clicked.connect(self._run_smart_rewrite)
        self._polish_card = _ActionCard(
            "sparkle", "Polish with AI", "Uses your AI Polish settings.", checkable=True
        )
        self._polish_card.clicked.connect(self._run_polish)
        self._insert_card = _ActionCard(
            "keyboard", "Insert", "Type it into the last app you used.", checkable=False
        )
        self._insert_card.clicked.connect(self._run_insert)
        for card in (self._format_card, self._rewrite_card, self._polish_card):
            self._action_group.addButton(card)
            actions.addWidget(card)
        actions.addWidget(self._insert_card)
        actions.addStretch(1)
        columns.addWidget(actions_host, 0)

        # Right: the result.
        right = QVBoxLayout()
        right.setSpacing(8)
        result_label = QLabel("Result")
        result_label.setObjectName("fieldLabel")
        right.addWidget(result_label)
        self._preview = QLabel()
        self._preview.setObjectName("playgroundPreviewText")
        self._preview.setWordWrap(True)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._scroll = QScrollArea()
        self._scroll.setObjectName("playgroundPreview")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.viewport().setAutoFillBackground(False)
        self._scroll.setWidget(self._preview)
        self._scroll.setMinimumHeight(180)
        right.addWidget(self._scroll, 1)
        columns.addLayout(right, 1)
        outer.addLayout(columns, 1)

        # Footer: where the text goes, and the insert button.
        foot = QHBoxLayout()
        foot.setSpacing(10)
        hint = QLabel(
            "Format and Rewrite run on this computer. "
            "Polish with AI sends the text to your AI provider."
        )
        hint.setObjectName("dimText")
        hint.setWordWrap(True)
        foot.addWidget(hint, 1)
        self._run_button = QPushButton("Insert result")
        self._run_button.setObjectName("primaryButton")
        self._run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_button.setEnabled(False)
        self._run_button.clicked.connect(self._insert_result)
        foot.addWidget(self._run_button)
        foot.addSpacing(6)
        for key in ("Ctrl", "Enter"):
            cap = QLabel(key)
            cap.setObjectName("keyCap")
            cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            foot.addWidget(cap, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addSpacing(16)
        outer.addLayout(foot)

        self._show_message(PLACEHOLDER)

    # -- inserting ------------------------------------------------------------
    def _on_submit(self) -> None:
        """Ctrl+Enter: insert the result, or the typed text when there is no result."""
        if self._result:
            self._insert_result()
            return
        text = self._command.toPlainText().strip()
        if not text:
            return
        self._command.clear()
        self._run_insert_with(text)

    def _insert_result(self) -> None:
        if self._result:
            self.insert_requested.emit(self._result)

    def _run_insert(self) -> None:
        self._run_insert_with(self._command.toPlainText())

    def _run_insert_with(self, text: str) -> None:
        text = text.strip()
        if text:
            self.insert_requested.emit(text)

    # -- actions --------------------------------------------------------------
    def _begin(self, card: _ActionCard | None) -> int:
        """Start a new run: cancel whatever was pending and show the choice."""
        self._run_id += 1
        self._result = ""
        self._run_button.setEnabled(False)
        self._polish_card.setEnabled(True)
        # Checkable buttons check themselves on click, so a refused run clears them.
        self._action_group.setExclusive(False)
        for button in self._action_group.buttons():
            button.setChecked(button is card)
        self._action_group.setExclusive(True)
        return self._run_id

    def _run_smart_rewrite(self) -> None:
        self._run_local(smart_rewrite, self._rewrite_card)

    def _run_format(self) -> None:
        self._run_local(format_text, self._format_card)

    def _run_local(self, transform, card: _ActionCard) -> None:
        original = self._command.toPlainText()
        if not original.strip():
            self._begin(None)
            self._show_message(EMPTY_INPUT)
            return
        run_id = self._begin(card)
        self._show_message("Working…")

        def run() -> None:
            if run_id != self._run_id:
                return
            try:
                result = transform(original)
            except Exception as exc:  # noqa: BLE001 - any transform error is shown to the user
                self._show_message(f"Could not run this action: {exc}", error=True)
                self.transformation_failed.emit(str(exc))
                return
            self._show_result(result)

        QTimer.singleShot(0, run)

    def _run_polish(self) -> None:
        from soundflow.core.settings import SettingsStore

        original = self._command.toPlainText()
        if not original.strip():
            self._begin(None)
            self._show_message(EMPTY_INPUT)
            return
        try:
            settings = self._settings if self._settings is not None else SettingsStore().load()
        except Exception as exc:  # noqa: BLE001 - unreadable settings are shown, not raised
            self._begin(None)
            self._show_message(f"Could not read your settings: {exc}", error=True)
            return
        if not settings.ai_cleanup_enabled:
            self._begin(None)
            self._show_message(
                "AI Polish is off. Turn it on in Preferences, under AI Polish.", error=True
            )
            return

        from soundflow.core.llm import polish_in_background

        run_id = self._begin(self._polish_card)
        self._polish_card.setEnabled(False)
        self._show_message("Polishing…")

        def done(cleaned: str) -> None:
            if run_id != self._run_id:
                return
            self._polish_card.setEnabled(True)
            self._show_result(cleaned.strip())

        def failed(message: str) -> None:
            if run_id != self._run_id:
                return
            self._polish_card.setEnabled(True)
            self._show_message(message, error=True)
            self.transformation_failed.emit(message)

        polish_in_background(original, settings, done, failed, parent=self)

    # -- result pane ------------------------------------------------------------
    def _show_result(self, text: str) -> None:
        if not text.strip():
            self._show_message("There is nothing to show for this text.")
            return
        self._result = text
        self._preview.setProperty("state", "result")
        self._refresh_preview(text)
        self._run_button.setEnabled(True)

    def _show_message(self, text: str, error: bool = False) -> None:
        self._result = ""
        self._run_button.setEnabled(False)
        state = "error" if error else ("placeholder" if text == PLACEHOLDER else "status")
        self._preview.setProperty("state", state)
        self._refresh_preview(text)

    def _refresh_preview(self, text: str) -> None:
        self._preview.setText(text)
        # Re-polish so the state selector in the sheet takes effect.
        self._preview.style().unpolish(self._preview)
        self._preview.style().polish(self._preview)

    def set_injector(self, injector: TextInjector | None) -> None:
        self._injector = injector

    def set_settings(self, settings) -> None:
        """Use these settings for Polish; without them the saved settings are read."""
        self._settings = settings


__all__ = ["PlaygroundPage"]
