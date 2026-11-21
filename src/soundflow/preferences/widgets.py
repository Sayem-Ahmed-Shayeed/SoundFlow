"""Building blocks shared by the Preferences tabs: scrolling tab, cards, rows."""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from soundflow.design import BODY_FONT, CONTROL_HEIGHT_SM, FONT_SMALL
from soundflow.hotkeys import canonical_hotkey, display_hotkey

_MODIFIER_TOKENS = (
    (Qt.KeyboardModifier.ControlModifier, "ctrl"),
    (Qt.KeyboardModifier.AltModifier, "alt"),
    (Qt.KeyboardModifier.ShiftModifier, "shift"),
    (Qt.KeyboardModifier.MetaModifier, "cmd"),
)
_NAMED_KEYS = {
    Qt.Key.Key_Space.value: "space",
    Qt.Key.Key_Return.value: "enter",
    Qt.Key.Key_Enter.value: "enter",
    Qt.Key.Key_Tab.value: "tab",
    Qt.Key.Key_Backspace.value: "backspace",
}
_MODIFIER_KEYS = frozenset(
    key.value
    for key in (
        Qt.Key.Key_Control,
        Qt.Key.Key_Shift,
        Qt.Key.Key_Alt,
        Qt.Key.Key_Meta,
        Qt.Key.Key_AltGr,
        Qt.Key.Key_CapsLock,
    )
)


def key_token(key: int) -> str | None:
    """Map a Qt key code to a hotkey token, or None when it cannot be used."""
    if Qt.Key.Key_A.value <= key <= Qt.Key.Key_Z.value:
        return chr(key).lower()
    if Qt.Key.Key_0.value <= key <= Qt.Key.Key_9.value:
        return chr(key)
    if Qt.Key.Key_F1.value <= key <= Qt.Key.Key_F12.value:
        return f"f{key - Qt.Key.Key_F1.value + 1}"
    return _NAMED_KEYS.get(key)


def _pill_font(size: int = FONT_SMALL) -> QFont:
    return QFont(BODY_FONT, size)


class PreferenceTab(QWidget):
    """A scrolling page: a large title, then cards grouped under small headings."""

    def __init__(self, object_name: str, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName(f"{object_name}Scroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        content.setObjectName(f"{object_name}Content")
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.body = QVBoxLayout(content)
        self.body.setContentsMargins(0, 0, 24, 40)
        self.body.setSpacing(0)
        heading = QLabel(title)
        heading.setObjectName("tabTitle")
        self.body.addWidget(heading)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.title_label = heading

    def add_group(self, title: str = "", *, note: str = "") -> SettingsCard:
        """Start a group: an optional heading, a card, and an optional note."""
        block = QWidget()
        block.setObjectName("prefsGroup")
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        if title:
            label = QLabel(title)
            label.setObjectName("groupTitle")
            layout.addWidget(label)
        card = SettingsCard()
        layout.addWidget(card)
        if note:
            card.note = note_label(note)
            layout.addWidget(card.note)
        self.body.addSpacing(24)
        self.body.addWidget(block)
        return card

    def finish(self) -> None:
        self.body.addStretch(1)


class SettingsCard(QWidget):
    """A bordered card whose rows are separated by hairlines."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("preferencesCard")
        self.note: QLabel | None = None  # set by PreferenceTab.add_group
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._slots = 0

    def add_row(self, widget: QWidget) -> QWidget:
        """Add a row (or any widget) with a hairline above it, except the first."""
        slot = QWidget()
        slot.setObjectName("prefsSlot")
        layout = QVBoxLayout(slot)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        if self._slots:
            divider = QFrame()
            divider.setObjectName("prefsDivider")
            divider.setFixedHeight(1)
            layout.addWidget(divider)
        layout.addWidget(widget)
        self._layout.addWidget(slot)
        self._slots += 1
        return slot


class SettingsRow(QWidget):
    """Title and description on the left, one control on the right."""

    def __init__(
        self,
        title: str,
        description: str = "",
        control: QWidget | None = None,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("prefsRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(24)
        self._copy = QVBoxLayout()
        self._copy.setContentsMargins(0, 0, 0, 0)
        self._copy.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("prefsRowTitle")
        self.title_label.setWordWrap(True)
        self.title_label.setVisible(bool(title))
        self._copy.addWidget(self.title_label)
        self.description_label = QLabel(description)
        self.description_label.setObjectName("mutedText")
        self.description_label.setWordWrap(True)
        self.description_label.setVisible(bool(description))
        self._copy.addWidget(self.description_label)
        layout.addLayout(self._copy, 1)
        self.control = control
        if control is not None:
            layout.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_description(self, text: str) -> None:
        self.description_label.setText(text)
        self.description_label.setVisible(bool(text))

    def add_below_description(self, widget: QWidget) -> None:
        self._copy.addWidget(widget)


class ChoiceRow(QWidget):
    """A radio option with a title and a description; the whole row is clickable."""

    def __init__(self, value: str, title: str, description: str, *, parent=None) -> None:
        super().__init__(parent)
        self.value = value
        self.setObjectName("prefsChoice")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        self.radio = QRadioButton()
        self.radio.setAccessibleName(title)
        self.radio.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.radio, 0, Qt.AlignmentFlag.AlignTop)
        copy = QVBoxLayout()
        copy.setContentsMargins(0, 0, 0, 0)
        copy.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("prefsRowTitle")
        copy.addWidget(title_label)
        if description:
            detail = QLabel(description)
            detail.setObjectName("mutedText")
            detail.setWordWrap(True)
            copy.addWidget(detail)
        layout.addLayout(copy, 1)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        self.radio.setChecked(True)
        super().mousePressEvent(event)


class ChoiceSet(QObject):
    """Exclusive radio rows; ``changed`` fires when the user picks a row."""

    changed = Signal(str)

    def __init__(self, options, value: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self.rows: list[ChoiceRow] = []
        for option_value, title, description in options:
            row = ChoiceRow(option_value, title, description)
            self._group.addButton(row.radio)
            row.radio.toggled.connect(
                lambda checked, v=option_value: checked and self.changed.emit(v)
            )
            self.rows.append(row)
        self.set_value(value)

    def value(self) -> str:
        for row in self.rows:
            if row.radio.isChecked():
                return row.value
        return self.rows[0].value

    def set_value(self, value: str) -> None:
        for row in self.rows:
            row.radio.blockSignals(True)
            row.radio.setChecked(row.value == value)
            row.radio.blockSignals(False)
        if value not in {row.value for row in self.rows}:
            self.rows[0].radio.setChecked(True)


class ShortcutRecorder(QWidget):
    """Shows the push-to-talk keys; "Change" records a new combination.

    While recording, the next key combination with a modifier is taken. Esc
    cancels, and leaving the field cancels too.
    """

    changed = Signal(str)
    recording_changed = Signal(bool)

    def __init__(self, shortcut: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("shortcutRecorder")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._shortcut = shortcut
        self._recording = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._caps = QHBoxLayout()
        self._caps.setSpacing(6)
        layout.addLayout(self._caps)
        self._button = QPushButton("Change")
        self._button.setObjectName("quietButton")
        self._button.setFixedHeight(CONTROL_HEIGHT_SM)
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        # Keep focus on the recorder, so clicking Cancel is not read as losing focus.
        self._button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._button.clicked.connect(self._toggle)
        layout.addWidget(self._button)
        self._hint = QLabel("")
        self._hint.setObjectName("noteText")
        self._hint.setVisible(False)
        self._refresh()

    @property
    def recording(self) -> bool:
        return self._recording

    def shortcut(self) -> str:
        return self._shortcut

    def set_shortcut(self, shortcut: str) -> None:
        self._shortcut = shortcut
        self._refresh()

    def _toggle(self) -> None:
        if self._recording:
            self.cancel()
        else:
            self.start()

    def start(self) -> None:
        self._recording = True
        self._hint.setVisible(False)
        self._refresh()
        self.setFocus()
        self.recording_changed.emit(True)

    def cancel(self) -> None:
        if not self._recording:
            return
        self._recording = False
        self._hint.setVisible(False)
        self._refresh()
        self.recording_changed.emit(False)

    def _refresh(self) -> None:
        while self._caps.count():
            item = self._caps.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        if self._recording:
            texts = ["Press keys…"]
        else:
            texts = display_hotkey(self._shortcut).split(" + ")
        for text in texts:
            cap = QLabel(text)
            cap.setObjectName("keyCap")
            cap.setProperty("size", "large")
            cap.setProperty("listening", self._recording)
            cap.style().unpolish(cap)
            cap.style().polish(cap)
            self._caps.addWidget(cap)
        self._button.setText("Cancel" if self._recording else "Change")

    def keyPressEvent(self, event) -> None:
        if not self._recording:
            super().keyPressEvent(event)
            return
        key = event.key()
        if key == Qt.Key.Key_Escape.value:
            self.cancel()
            return
        if key in _MODIFIER_KEYS:
            return
        token = key_token(key)
        if token is None:
            self._show_hint("That key can't be used. Try a letter, number, Space or F-key.")
            return
        modifiers = [name for flag, name in _MODIFIER_TOKENS if event.modifiers() & flag]
        try:
            value = canonical_hotkey("+".join([*modifiers, token]))
        except ValueError:
            self._show_hint("Hold Ctrl, Alt, Shift or Super with the key.")
            return
        self._recording = False
        self._shortcut = value
        self._hint.setVisible(False)
        self._refresh()
        self.recording_changed.emit(False)
        self.changed.emit(value)

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.cancel()

    def _show_hint(self, text: str) -> None:
        self._hint.setText(text)
        self._hint.setVisible(True)


def note_label(text: str, *, warning: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName("noteText")
    label.setWordWrap(True)
    if warning:
        label.setProperty("tone", "warning")
    return label


def section_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("groupTitle")
    return label


__all__ = [
    "ChoiceRow",
    "ChoiceSet",
    "PreferenceTab",
    "SettingsCard",
    "SettingsRow",
    "ShortcutRecorder",
    "key_token",
    "note_label",
    "section_label",
]
