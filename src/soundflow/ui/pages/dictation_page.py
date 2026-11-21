"""Home: a dashboard of your dictation, with the record button on top.

From the top: a greeting with today's words and the language; the green
dictation card (shortcut, record button, and your voice as moving bars while
you speak); four numbers for the week; words per day and an activity grid;
the most recent dictations.

States, as set by the main window:

* ``idle`` - the card shows the shortcut and "Start dictation". After a
  dictation the finished text stays in a result card under it until the
  next one starts.
* ``recording`` - "Listening" with a timer, your voice as bars, and the
  words as Whisper hears them.
* ``draining`` - "Transcribing": the bars stop and dim while a light sweeps
  across them.

Dictation is toggled many times a day, so states switch instantly; only the
finished transcript fades in.
"""

from __future__ import annotations

import html
from collections import deque
from datetime import date, datetime

import numpy as np
from PySide6.QtCore import (
    QEvent,
    QPropertyAnimation,
    QRectF,
    QSequentialAnimationGroup,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from soundflow.design import icon, icon_pixmap, icon_size
from soundflow.design.fonts import BODY_FONT, DISPLAY_FONT, tabular
from soundflow.design.motion import ease_out_curve, reduced_motion
from soundflow.design.spacing import ANIMATION_NORMAL
from soundflow.design.theme import current_palette
from soundflow.history.stats import (
    TYPING_WPM,
    DashboardStats,
    duration_text,
    heat_level,
)
from soundflow.hotkeys import display_hotkey
from soundflow.ui.widgets.spinner import Spinner

LANGUAGES = (
    ("Auto detect", "auto"),
    ("English or বাংলা", "auto:en+bn"),
    ("English or Hindi", "auto:en+hi"),
    ("English", "en"),
    ("বাংলা", "bn"),
    ("Hindi", "hi"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Japanese", "ja"),
)

_OUTCOMES = {
    "pasted": "Pasted where your cursor was",
    "copied": "Copied to the clipboard",
}
_WEEKDAYS = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
RECENT_LIMIT = 5


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _clock(seconds: float) -> str:
    minutes, secs = divmod(max(0, int(seconds)), 60)
    return f"{minutes}:{secs:02d}"


def _word_count(text: str) -> int:
    return len(text.split())


def _words(count: int) -> str:
    return "1 word" if count == 1 else f"{count:,} words"


def greeting(now: datetime | None = None) -> str:
    hour = (now or datetime.now()).hour
    if 5 <= hour < 12:
        return "Good morning"
    if 12 <= hour < 17:
        return "Good afternoon"
    return "Good evening"


def _number_font(pixels: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(DISPLAY_FONT)
    font.setPixelSize(pixels)
    font.setWeight(weight)
    return tabular(font)


def _day_name(day: date) -> str:
    return f"{day.strftime('%a')} {day.day} {day.strftime('%b')}"


_GLYPH_SIZES = {"record": 20, "stop": 14, "dot": 20, "check": 16}


class _Glyph(QWidget):
    """Tiny painted marks: the record dot, the stop square, the live dot."""

    def __init__(self, kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._kind = kind
        size = _GLYPH_SIZES[kind]
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_kind(self, kind: str) -> None:
        self._kind = kind
        size = _GLYPH_SIZES[kind]
        self.setFixedSize(size, size)
        self.update()

    def paintEvent(self, event) -> None:
        del event
        colors = current_palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        center = rect.center()
        if self._kind == "record":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(colors["record"]))
            painter.drawEllipse(center, 5.5, 5.5)
        elif self._kind == "stop":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(colors["primary_text"]))
            painter.drawRoundedRect(QRectF(1.5, 1.5, 11, 11), 2.5, 2.5)
        elif self._kind == "dot":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 138, 122, 70))
            painter.drawEllipse(center, 9.0, 9.0)
            painter.setBrush(QColor("#FF8A7A"))
            painter.drawEllipse(center, 4.5, 4.5)
        elif self._kind == "check":
            pen = QPen(QColor(colors["success"]), 2.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            path = QPainterPath()
            path.moveTo(3.3, 8.3)
            path.lineTo(6.6, 11.6)
            path.lineTo(12.8, 4.8)
            painter.drawPath(path)


class _ElidedLabel(QLabel):
    """One line of text that ends in an ellipsis when it doesn't fit."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.set_full_text(text)

    def set_full_text(self, text: str) -> None:
        self._full = " ".join(text.split())
        self._elide()

    def full_text(self) -> str:
        return self._full

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._elide()

    def _elide(self) -> None:
        width = max(40, self.width())
        super().setText(
            self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, width)
        )


class _BigButton(QPushButton):
    """The lavender record button: a glyph (or spinner) and a label."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("bigButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(48)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 0, 22, 0)
        row.setSpacing(8)
        self.glyph = _Glyph("record")
        self.spinner = Spinner(16, color="#1A1A1A")
        self.spinner.hide()
        self.label = QLabel("")
        self.label.setObjectName("bigButtonLabel")
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(self.glyph, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.label, 0, Qt.AlignmentFlag.AlignVCenter)
        self._mode = ""

    def mode(self) -> str:
        return self._mode

    def text_label(self) -> str:
        return self.label.text()

    def set_mode(self, mode: str, text: str) -> None:
        self._mode = mode
        self.label.setText(text)
        self.setAccessibleName(text)
        working = mode == "working"
        self.glyph.setVisible(not working)
        self.spinner.setVisible(working)
        if not working:
            self.glyph.set_kind("stop" if mode == "stop" else "record")
        self.setEnabled(not working)
        self.setProperty("mode", mode)
        _repolish(self)
        _repolish(self.label)
        self.label.ensurePolished()
        self.setFixedWidth(self.layout().sizeHint().width())


class VoiceBars(QWidget):
    """Your voice as level bars scrolling right to left, on the green card.

    ``state`` is ``idle`` (nothing recorded), ``live``, ``scanning`` (the
    recording is being transcribed: dimmed while the activity indicator
    beside it turns) or ``frozen`` (the last recording, still). Only live
    audio repaints it; it has no timer of its own.
    """

    BAR = 3
    GAP = 3
    CHUNK = 480  # 30 ms of 16 kHz audio per bar

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(48)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._levels: deque[float] = deque(maxlen=480)
        self._pending = np.zeros(0, dtype=np.float32)
        self._state = "idle"

    @property
    def state(self) -> str:
        return self._state

    def levels(self) -> list[float]:
        return list(self._levels)

    def start_live(self) -> None:
        self._levels.clear()
        self._pending = np.zeros(0, dtype=np.float32)
        self._set_state("live")

    def push_audio(self, pcm: bytes) -> None:
        if self._state != "live" or not pcm:
            return
        samples = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").astype(np.float32) / 32768
        self._pending = np.concatenate([self._pending, samples])
        added = False
        while self._pending.size >= self.CHUNK:
            chunk, self._pending = self._pending[: self.CHUNK], self._pending[self.CHUNK :]
            rms = float(np.sqrt(np.mean(chunk * chunk)))
            db = 20 * np.log10(rms + 1e-7)
            self._levels.append(float(np.clip((db + 58) / 46, 0.0, 1.0)))
            added = True
        if added:
            self.update()

    def freeze(self) -> None:
        self._set_state("frozen")

    def set_scanning(self, scanning: bool) -> None:
        self._set_state("scanning" if scanning else "frozen")

    def reset(self) -> None:
        self._levels.clear()
        self._set_state("idle")

    def _set_state(self, state: str) -> None:
        self._state = state
        self.update()

    def paintEvent(self, event) -> None:
        del event
        colors = current_palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        ink = QColor(colors["on_brand"])
        step = self.BAR + self.GAP
        count = max(1, (self.width() + self.GAP) // step)
        levels = list(self._levels)[-count:]
        levels = [0.0] * (count - len(levels)) + levels
        height = self.height()
        middle = height / 2
        span = count * step - self.GAP
        left = (self.width() - span) / 2
        for index, level in enumerate(levels):
            x = left + index * step
            bar = max(3.0, level * (height - 4))
            ink.setAlphaF(0.4 if self._state in {"frozen", "scanning"} else 0.92)
            painter.setBrush(ink)
            painter.drawRoundedRect(QRectF(x, middle - bar / 2, self.BAR, bar), 1.5, 1.5)


class DailyWords(QWidget):
    """Words per day as bars; today's bar is solid, hover shows the number."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(190)
        self.setMouseTracking(True)
        self._days: list[tuple[date, int]] = []
        self._hover = -1

    def set_days(self, days: list[tuple[date, int]]) -> None:
        self._days = list(days)
        self.update()

    def values(self) -> list[int]:
        return [words for _day, words in self._days]

    def _geometry(self) -> tuple[float, float, float]:
        count = max(1, len(self._days))
        gap = 8.0
        width = (self.width() - gap * (count - 1)) / count
        return width, gap, self.height() - 22.0

    def _index_at(self, x: float) -> int:
        width, gap, _ = self._geometry()
        index = int(x // (width + gap))
        return index if 0 <= index < len(self._days) else -1

    def mouseMoveEvent(self, event) -> None:
        index = self._index_at(event.position().x())
        if index != self._hover:
            self._hover = index
            self.update()
        if index >= 0:
            day, words = self._days[index]
            QToolTip.showText(event.globalPosition().toPoint(), f"{_day_name(day)}: {_words(words)}", self)
        else:
            QToolTip.hideText()

    def leaveEvent(self, event) -> None:
        self._hover = -1
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        del event
        if not self._days:
            return
        colors = current_palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, gap, chart = self._geometry()
        top = max(1, max(self.values()))
        font = QFont(BODY_FONT)
        font.setPixelSize(11)
        painter.setFont(font)
        last = len(self._days) - 1
        for index, (day, words) in enumerate(self._days):
            x = index * (width + gap)
            bar = max(2.0, words / top * (chart - 6)) if words else 2.0
            solid = index == last or index == self._hover
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(colors["chart_bar"] if solid else colors["chart_bar_soft"]))
            path = QPainterPath()
            path.addRoundedRect(QRectF(x, chart - bar, width, bar), 4, 4)
            painter.drawPath(path)
            painter.setPen(QColor(colors["text3"]))
            label = "Today" if index == last else _WEEKDAYS[day.weekday()]
            painter.drawText(
                QRectF(x - 8, chart + 6, width + 16, 16), Qt.AlignmentFlag.AlignCenter, label
            )


class ActivityGrid(QWidget):
    """Weeks as columns, Monday at the top; darker days have more words."""

    CELL_GAP = 4

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(120)
        self._weeks: list[list[tuple[date, int] | None]] = []

    def set_weeks(self, weeks: list[list[tuple[date, int] | None]]) -> None:
        self._weeks = [list(column) for column in weeks]
        self.updateGeometry()
        self.update()

    def levels(self) -> list[list[int | None]]:
        return [
            [None if cell is None else heat_level(cell[1]) for cell in column]
            for column in self._weeks
        ]

    def _cell(self) -> float:
        columns = max(1, len(self._weeks))
        return (self.width() - self.CELL_GAP * (columns - 1)) / columns

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        columns = max(1, len(self._weeks) or 18)
        cell = (width - self.CELL_GAP * (columns - 1)) / columns
        return int(cell * 7 + self.CELL_GAP * 6)

    def mouseMoveEvent(self, event) -> None:
        step = self._cell() + self.CELL_GAP
        column = int(event.position().x() // step)
        row = int(event.position().y() // step)
        if 0 <= column < len(self._weeks) and 0 <= row < 7 and self._weeks[column][row]:
            day, words = self._weeks[column][row]
            QToolTip.showText(event.globalPosition().toPoint(), f"{_day_name(day)}: {_words(words)}", self)
        else:
            QToolTip.hideText()

    def paintEvent(self, event) -> None:
        del event
        colors = current_palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        cell = self._cell()
        step = cell + self.CELL_GAP
        for column, days in enumerate(self._weeks):
            for row, value in enumerate(days):
                if value is None:
                    continue
                painter.setBrush(QColor(colors[f"heat{heat_level(value[1])}"]))
                painter.drawRoundedRect(QRectF(column * step, row * step, cell, cell), 3, 3)


class _Swatches(QWidget):
    """The five shades of the activity grid, for its legend."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(5 * 11 + 4 * 4, 11)

    def paintEvent(self, event) -> None:
        del event
        colors = current_palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        for level in range(5):
            painter.setBrush(QColor(colors[f"heat{level}"]))
            painter.drawRoundedRect(QRectF(level * 15, 0, 11, 11), 3, 3)


class _StatTile(QFrame):
    """One number with its name and a line of context."""

    def __init__(self, icon_name: str, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statTile")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(4)
        head = QHBoxLayout()
        head.setSpacing(8)
        self.icon_name = icon_name
        self.badge = QLabel()
        self.badge.setObjectName("statBadge")
        self.badge.setFixedSize(28, 28)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.paint_icon()
        head.addWidget(self.badge)
        title = QLabel(name)
        title.setObjectName("statName")
        head.addWidget(title, 1)
        layout.addLayout(head)
        layout.addSpacing(4)
        values = QHBoxLayout()
        values.setSpacing(5)
        self.value = QLabel("0")
        self.value.setObjectName("statValue")
        self.value.setFont(_number_font(40))
        values.addWidget(self.value, 0, Qt.AlignmentFlag.AlignBaseline)
        self.unit = QLabel("")
        self.unit.setObjectName("statUnit")
        values.addWidget(self.unit, 0, Qt.AlignmentFlag.AlignBaseline)
        values.addStretch(1)
        layout.addLayout(values)
        layout.addStretch(1)
        self.note = QLabel("")
        self.note.setObjectName("statNote")
        self.note.setWordWrap(True)
        self.note.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.note)

    def paint_icon(self) -> None:
        self.badge.setPixmap(icon_pixmap(self.icon_name, current_palette()["accent_text"], 16))

    def set(self, value: str, unit: str = "", note: str = "") -> None:
        self.value.setText(value)
        self.unit.setText(unit)
        self.unit.setVisible(bool(unit))
        self.note.setText(note)


class _RecentRow(QFrame):
    """One recent dictation: time, the first line, and Copy."""

    copy_requested = Signal(int)
    open_requested = Signal(int)

    def __init__(self, entry_id: int, when: str, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("recentRow")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Open in History")
        self.entry_id = entry_id
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 4, 4, 4)
        row.setSpacing(14)
        time_label = QLabel(when)
        time_label.setObjectName("recentTime")
        time_label.setFixedWidth(76)
        time_label.setFont(tabular(time_label.font()))
        row.addWidget(time_label)
        self.text_label = _ElidedLabel(text)
        self.text_label.setObjectName("recentText")
        row.addWidget(self.text_label, 1)
        self.copy_button = QPushButton()
        self.copy_button.setObjectName("iconButton")
        self.copy_button.setFixedSize(32, 32)
        self.copy_button.setIconSize(icon_size(16))
        self.copy_button.setToolTip("Copy transcript")
        self.copy_button.setAccessibleName("Copy transcript")
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_button.clicked.connect(self._copy)
        row.addWidget(self.copy_button)
        self._paint_icon("copy")

    def _paint_icon(self, name: str) -> None:
        colors = current_palette()
        color = colors["success"] if name == "check" else colors["text2"]
        self.copy_button.setIcon(icon(name, color, 16))

    def _copy(self) -> None:
        self.copy_requested.emit(self.entry_id)
        self._paint_icon("check")
        self.copy_button.setToolTip("Copied")
        QTimer.singleShot(1200, self._restore_icon)

    def _restore_icon(self) -> None:
        try:
            self._paint_icon("copy")
            self.copy_button.setToolTip("Copy transcript")
        except RuntimeError:  # the row was rebuilt meanwhile
            pass

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            event.position().toPoint()
        ):
            self.open_requested.emit(self.entry_id)
            event.accept()
            return
        super().mouseReleaseEvent(event)




def _card(name: str) -> tuple[QFrame, QVBoxLayout, QHBoxLayout]:
    """A white panel with a serif heading row; returns (frame, body, heading row)."""
    frame = QFrame()
    frame.setObjectName("dashCard")
    body = QVBoxLayout(frame)
    body.setContentsMargins(20, 16, 20, 18)
    body.setSpacing(12)
    head = QHBoxLayout()
    head.setSpacing(12)
    title = QLabel(name)
    title.setObjectName("dashCardTitle")
    head.addWidget(title, 0, Qt.AlignmentFlag.AlignBaseline)
    head.addStretch(1)
    body.addLayout(head)
    return frame, body, head


class DictationPage(QWidget):
    """Home page: dictation card and dashboard."""

    language_changed = Signal(str)
    dictation_toggled = Signal()
    cancel_requested = Signal()
    history_requested = Signal()
    setup_requested = Signal()
    recent_copy_requested = Signal(int)
    recent_open_requested = Signal(int)
    polish_requested = Signal(str)

    MAX_WIDTH = 1040

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dictationPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._state = "idle"
        self._shortcut_display = "Ctrl + Alt + Space"
        self._name = ""
        self._paste_on_stop = True
        self._polish_available = False
        self._polishing = False
        self._result_text = ""
        self._elapsed = 0
        self._meta = ""
        self._engine = ""
        self._today_words = 0
        self._reveals: list[QSequentialAnimationGroup] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._scroll = QScrollArea()
        self._scroll.setObjectName("homeScroll")
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.viewport().setObjectName("homeScrollViewport")
        outer.addWidget(self._scroll)

        holder = QWidget()
        holder.setObjectName("homeHolder")
        centre = QHBoxLayout(holder)
        centre.setContentsMargins(0, 0, 0, 0)
        column = QWidget()
        column.setObjectName("homeColumn")
        column.setMaximumWidth(self.MAX_WIDTH)
        centre.addWidget(column, 1)
        self._scroll.setWidget(holder)

        layout = QVBoxLayout(column)
        layout.setContentsMargins(40, 10, 44, 36)
        layout.setSpacing(0)

        # --- Greeting, today's words, language --------------------------------
        head = QHBoxLayout()
        head.setSpacing(16)
        titles = QVBoxLayout()
        titles.setSpacing(4)
        self._prompt = QLabel(greeting())
        self._prompt.setObjectName("pageTitle")
        titles.addWidget(self._prompt)
        self._today_line = QLabel("")
        self._today_line.setObjectName("todayLine")
        self._today_line.setTextFormat(Qt.TextFormat.RichText)
        titles.addWidget(self._today_line)
        head.addLayout(titles, 1)
        self._language = QComboBox()
        self._language.setObjectName("languagePicker")
        self._language.setAccessibleName("Spoken language")
        self._language.setToolTip("Spoken language")
        self._language.setCursor(Qt.CursorShape.PointingHandCursor)
        self._language.setMinimumWidth(180)
        self._language.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        for label, code in LANGUAGES:
            self._language.addItem(label, code)
        self._language.currentIndexChanged.connect(self._emit_language)
        head.addWidget(self._language, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(head)
        layout.addSpacing(22)

        # --- Shortcut setup banner (only when something needs approval) -------
        self._banner = QFrame()
        self._banner.setObjectName("shortcutBanner")
        banner = QHBoxLayout(self._banner)
        banner.setContentsMargins(14, 10, 10, 10)
        banner.setSpacing(12)
        self._banner_text = QLabel("")
        self._banner_text.setObjectName("shortcutBannerText")
        self._banner_text.setWordWrap(True)
        banner.addWidget(self._banner_text, 1)
        self.setup_button = QPushButton("Allow shortcut")
        self.setup_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setup_button.clicked.connect(self.setup_requested.emit)
        banner.addWidget(self.setup_button, 0, Qt.AlignmentFlag.AlignVCenter)
        self._banner.hide()
        layout.addWidget(self._banner)
        self._banner_gap = QWidget()
        self._banner_gap.setFixedHeight(14)
        self._banner_gap.hide()
        layout.addWidget(self._banner_gap)

        # --- The green dictation card -------------------------------------------
        self._card = QFrame()
        self._card.setObjectName("dictateCard")
        card = QVBoxLayout(self._card)
        card.setContentsMargins(28, 22, 24, 22)
        card.setSpacing(14)
        top = QHBoxLayout()
        top.setSpacing(24)
        words = QVBoxLayout()
        words.setSpacing(6)
        self._title_box = QWidget()
        self._title_row = QHBoxLayout(self._title_box)
        self._title_row.setContentsMargins(0, 0, 0, 0)
        self._title_row.setSpacing(8)
        words.addWidget(self._title_box)
        self._live_box = QWidget()
        live = QHBoxLayout(self._live_box)
        live.setContentsMargins(0, 0, 0, 0)
        live.setSpacing(10)
        self._live_dot = _Glyph("dot")
        self._live_spinner = Spinner(16, color="#FFFFEB")
        live.addWidget(self._live_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        live.addWidget(self._live_spinner, 0, Qt.AlignmentFlag.AlignVCenter)
        self._hero = QLabel("Listening")
        self._hero.setObjectName("cardTitle")
        self._hero.setProperty("state", "recording")
        live.addWidget(self._hero, 0, Qt.AlignmentFlag.AlignVCenter)
        self._timer_label = QLabel("0:00")
        self._timer_label.setObjectName("cardTimer")
        self._timer_label.setFont(_number_font(30))
        live.addWidget(self._timer_label, 0, Qt.AlignmentFlag.AlignVCenter)
        live.addStretch(1)
        words.addWidget(self._live_box)
        self._card_note = QWidget()
        self._hint_row = QHBoxLayout(self._card_note)
        self._hint_row.setContentsMargins(0, 0, 0, 0)
        self._hint_row.setSpacing(5)
        words.addWidget(self._card_note)
        top.addLayout(words, 1)
        self.record_button = _BigButton()
        self.record_button.clicked.connect(self.dictation_toggled.emit)
        top.addWidget(self.record_button, 0, Qt.AlignmentFlag.AlignVCenter)
        card.addLayout(top)

        self.ribbon = VoiceBars()
        self.ribbon.setFixedHeight(56)
        self.ribbon.setAccessibleName("Your voice level")
        card.addWidget(self.ribbon)

        self._interim = QLabel("")
        self._interim.setObjectName("liveText")
        self._interim.setWordWrap(True)
        self._interim.setTextFormat(Qt.TextFormat.RichText)
        self._interim.setMinimumHeight(30)
        self._interim.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._interim.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._interim.setProperty("dim", False)
        self._interim_plain = ""
        self._caret_on = True
        self._caret = QTimer(self)
        self._caret.setInterval(550)
        self._caret.timeout.connect(self._blink)
        self._interim_gap = QWidget()  # kept for the shared show/hide helper
        self._interim_gap.setFixedHeight(0)
        card.addWidget(self._interim)
        self._interim.hide()
        layout.addWidget(self._card)

        self._error = QLabel("")
        self._error.setObjectName("errorText")
        self._error.setWordWrap(True)
        self._error.hide()
        self._error_gap = QWidget()
        self._error_gap.setFixedHeight(12)
        self._error_gap.hide()
        layout.addWidget(self._error_gap)
        layout.addWidget(self._error)

        # --- The finished transcript ------------------------------------------
        self._result = QFrame()
        self._result.setObjectName("resultCard")
        result = QVBoxLayout(self._result)
        result.setContentsMargins(22, 20, 22, 16)
        result.setSpacing(16)
        self._result_label = QLabel("")
        self._result_label.setObjectName("resultText")
        self._result_label.setWordWrap(True)
        self._result_label.setTextFormat(Qt.TextFormat.RichText)
        self._result_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        result.addWidget(self._result_label)
        foot = QHBoxLayout()
        foot.setSpacing(18)
        self._outcome_box = QWidget()
        outcome = QHBoxLayout(self._outcome_box)
        outcome.setContentsMargins(0, 0, 0, 0)
        outcome.setSpacing(6)
        outcome.addWidget(_Glyph("check"))
        self._outcome = QLabel("")
        self._outcome.setObjectName("resultOutcome")
        outcome.addWidget(self._outcome)
        foot.addWidget(self._outcome_box)
        self._result_length = QLabel("")
        self._result_length.setObjectName("resultFact")
        self._result_length.setFont(tabular(self._result_length.font()))
        foot.addWidget(self._result_length)
        self._result_words = QLabel("")
        self._result_words.setObjectName("resultFact")
        self._result_words.setFont(tabular(self._result_words.font()))
        foot.addWidget(self._result_words)
        foot.addStretch(1)
        self.copy_result_button = QPushButton("Copy")
        self.copy_result_button.setObjectName("smallButton")
        self.copy_result_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_result_button.setIconSize(icon_size(16))
        self.copy_result_button.clicked.connect(self._copy_result)
        foot.addWidget(self.copy_result_button)
        self.polish_button = QPushButton("Polish with AI")
        self.polish_button.setObjectName("smallButton")
        self.polish_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.polish_button.setIconSize(icon_size(16))
        self.polish_button.clicked.connect(self._request_polish)
        self.polish_button.hide()
        foot.addWidget(self.polish_button)
        result.addLayout(foot)
        self._result_gap = QWidget()
        self._result_gap.setFixedHeight(16)
        layout.addWidget(self._result_gap)
        layout.addWidget(self._result)
        self._result_gap.hide()
        self._result.hide()

        # --- The dashboard ------------------------------------------------------
        self._lower = QWidget()
        lower = QVBoxLayout(self._lower)
        lower.setContentsMargins(0, 18, 0, 0)
        lower.setSpacing(16)

        tiles = QGridLayout()
        tiles.setHorizontalSpacing(14)
        tiles.setVerticalSpacing(14)
        self._week_tile = _StatTile("pen", "Words this week")
        self._speed_tile = _StatTile("gauge", "Speaking speed")
        self._saved_tile = _StatTile("clock", "Time saved")
        self._streak_tile = _StatTile("flame", "Day streak")
        self._tiles = [self._week_tile, self._speed_tile, self._saved_tile, self._streak_tile]
        for index, tile in enumerate(self._tiles):
            tiles.addWidget(tile, 0, index)
            tiles.setColumnStretch(index, 1)
        self._tile_grid = tiles
        lower.addLayout(tiles)

        charts = QHBoxLayout()
        charts.setSpacing(14)
        daily_card, daily_body, daily_head = _card("Words per day")
        caption = QLabel("Last 14 days")
        caption.setObjectName("dashCaption")
        daily_head.addWidget(caption, 0, Qt.AlignmentFlag.AlignBaseline)
        self.daily_chart = DailyWords()
        self.daily_chart.setAccessibleName("Words per day, last 14 days")
        daily_body.addWidget(self.daily_chart, 1)
        charts.addWidget(daily_card, 5)

        heat_card, heat_body, heat_head = _card("Activity")
        caption = QLabel("Last 18 weeks")
        caption.setObjectName("dashCaption")
        heat_head.addWidget(caption, 0, Qt.AlignmentFlag.AlignBaseline)
        self.activity_grid = ActivityGrid()
        self.activity_grid.setAccessibleName("Days you dictated, last 18 weeks")
        heat_body.addWidget(self.activity_grid)
        legend = QHBoxLayout()
        legend.setSpacing(6)
        legend.addStretch(1)
        less = QLabel("Less")
        less.setObjectName("dashCaption")
        legend.addWidget(less)
        legend.addWidget(_Swatches(), 0, Qt.AlignmentFlag.AlignVCenter)
        more = QLabel("More")
        more.setObjectName("dashCaption")
        legend.addWidget(more)
        heat_body.addLayout(legend)
        totals_line = QFrame()
        totals_line.setObjectName("dashRule")
        totals_line.setFixedHeight(1)
        heat_body.addWidget(totals_line)
        totals = QHBoxLayout()
        totals.setSpacing(26)
        self._total_dictations = self._total(totals, "Dictations, all time")
        self._total_words = self._total(totals, "Words, all time")
        totals.addStretch(1)
        heat_body.addLayout(totals)
        heat_body.addStretch(1)
        charts.addWidget(heat_card, 4)
        lower.addLayout(charts)

        recent_card, recent_body, recent_head = _card("Recent")
        self._open_history = QPushButton("See all history")
        self._open_history.setObjectName("linkButton")
        self._open_history.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_history.clicked.connect(self.history_requested.emit)
        recent_head.addWidget(self._open_history)
        recent_body.setSpacing(4)
        self._recent_box = QVBoxLayout()
        self._recent_box.setContentsMargins(0, 0, 0, 0)
        self._recent_box.setSpacing(0)
        recent_body.addLayout(self._recent_box)
        self._recent_empty = QLabel("Your dictations show up here.")
        self._recent_empty.setObjectName("mutedText")
        recent_body.addWidget(self._recent_empty)
        self._recent: list[tuple[int, str, str]] = []
        self._recent_rows: list[_RecentRow] = []
        lower.addWidget(recent_card)
        layout.addWidget(self._lower)
        layout.addStretch(1)

        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._on_tick)

        self.set_dashboard(DashboardStats())
        self._apply_state("idle")
        self.refresh_icons()

    def _total(self, row: QHBoxLayout, caption: str) -> QLabel:
        column = QVBoxLayout()
        column.setSpacing(0)
        value = QLabel("0")
        value.setObjectName("totalValue")
        value.setFont(_number_font(26))
        column.addWidget(value)
        label = QLabel(caption)
        label.setObjectName("dashCaption")
        column.addWidget(label)
        row.addLayout(column)
        return value

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Two rows of two tiles when the window is narrow.
        narrow = self.width() < 860
        for index, tile in enumerate(self._tiles):
            row, column = (index // 2, index % 2) if narrow else (0, index)
            self._tile_grid.addWidget(tile, row, column)
        for column in range(4):
            self._tile_grid.setColumnStretch(column, 1 if (column < 2 or not narrow) else 0)

    # -- appearance -------------------------------------------------------------
    def refresh_icons(self) -> None:
        """Re-tint icons after the theme changes."""
        colors = current_palette()
        self.copy_result_button.setIcon(icon("copy", colors["text2"], 16))
        self.polish_button.setIcon(icon("sparkle", colors["text2"], 16))
        for row in self._recent_rows:
            row._paint_icon("copy")
        for tile in self._tiles:
            tile.paint_icon()
        self.update()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.StyleChange:
            QTimer.singleShot(0, self.refresh_icons)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._update_greeting()

    # -- account and numbers -------------------------------------------------------
    def set_user_name(self, name: str) -> None:
        """Greet by first name (an email address is not a name)."""
        first = (name or "").strip().split(" ")[0] if name and "@" not in name else ""
        self._name = first
        self._update_greeting()

    def _update_greeting(self) -> None:
        text = greeting()
        self._prompt.setText(f"{text}, {self._name}" if self._name else text)

    def set_today(self, words: int, dictations: int, wpm: int | None = None) -> None:
        """Today's words, for the line under the greeting."""
        del dictations, wpm
        self._today_words = words
        if words:
            self._today_line.setText(f"You've dictated <b>{_words(words)}</b> today.")
        else:
            self._today_line.setText("Nothing dictated yet today.")

    def set_stats(self, words: int, dictations: int) -> None:
        """Older entry point."""
        self.set_today(words, dictations)

    def set_dashboard(self, stats: DashboardStats) -> None:
        """Fill the tiles, charts and totals."""
        self.set_today(stats.today_words, stats.today_dictations)
        change = stats.week_change
        if change is None:
            note = "In the last 7 days"
        else:
            sign = "+" if change >= 0 else "−"
            note = f'<span style="font-weight:600">{sign}{abs(change)}%</span> on the week before'
        self._week_tile.set(f"{stats.week_words:,}", "", note)
        if stats.wpm:
            self._speed_tile.set(
                f"{stats.wpm:,}", "wpm",
                f"{stats.speedup:.1f}× faster than typing at {TYPING_WPM} wpm",
            )
        else:
            self._speed_tile.set("–", "", "Shows after a little more speaking")
        self._saved_tile.set(
            duration_text(stats.week_minutes_saved), "", "This week, compared with typing"
        )
        self._streak_tile.set(
            f"{stats.streak:,}", "day" if stats.streak == 1 else "days",
            f"Longest: {stats.longest_streak:,} "
            f"{'day' if stats.longest_streak == 1 else 'days'}",
        )
        self.daily_chart.set_days(stats.daily)
        self.activity_grid.set_weeks(stats.heat)
        self._total_dictations.setText(f"{stats.total_dictations:,}")
        self._total_words.setText(f"{stats.total_words:,}")

    def set_recent(self, items: list[tuple[int, str, str]]) -> None:
        """``(id, time, text)`` for the latest dictations, newest first."""
        self._recent = list(items)
        self._rebuild_recent()

    def _rebuild_recent(self) -> None:
        for row in self._recent_rows:
            self._recent_box.removeWidget(row)
            row.deleteLater()
        self._recent_rows = []
        for entry_id, when, text in self._recent[:RECENT_LIMIT]:
            row = _RecentRow(entry_id, when, text)
            row.copy_requested.connect(self.recent_copy_requested.emit)
            row.open_requested.connect(self.recent_open_requested.emit)
            self._recent_box.addWidget(row)
            self._recent_rows.append(row)
        self._recent_empty.setVisible(not self._recent_rows)

    def set_last(self, preview: str, meta: str = "") -> None:
        """Kept for older callers; the Recent list replaces it."""
        del preview, meta

    def set_meta(self, text: str) -> None:
        self._meta = text
        self._card.setToolTip(text.replace(" · ", ", "))

    def set_engine_sub(self, text: str) -> None:
        self._engine = text

    # -- shortcut setup -------------------------------------------------------------
    def set_setup_notice(self, text: str | None, action: str = "Allow shortcut") -> None:
        """Show or hide the banner asking the person to approve the shortcut."""
        if not text:
            self._banner.hide()
            self._banner_gap.hide()
            return
        self._banner_text.setText(text)
        self.setup_button.setText(action)
        self.setup_button.setVisible(bool(action))
        self._banner.show()
        self._banner_gap.show()

    def set_paste_on_stop(self, paste: bool) -> None:
        """Whether stopping pastes the text or only copies it."""
        self._paste_on_stop = paste
        self._apply_state(self._state)

    def set_polish_available(self, available: bool) -> None:
        self._polish_available = available
        self.polish_button.setVisible(available and bool(self._result_text))

    # -- live state ----------------------------------------------------------------
    @property
    def state(self) -> str:
        return self._state

    def set_state(self, state: str) -> None:
        state = state if state in {"recording", "draining"} else "idle"
        if state == self._state:
            return
        previous = self._state
        self._state = state
        if state == "recording":
            self._elapsed = 0
            self._polishing = False
            self.clear_error()
            self._hide_result()
            self.ribbon.start_live()
        elif state == "draining":
            self.ribbon.freeze()
            self.ribbon.set_scanning(True)
        else:
            self._polishing = False
            if previous == "draining":
                self.ribbon.set_scanning(False)
            else:
                self.ribbon.reset()
        self._apply_state(state)

    def _apply_state(self, state: str) -> None:
        recording = state == "recording"
        working = state == "draining"
        idle = not recording and not working
        self._title_box.setVisible(idle)
        self._live_box.setVisible(not idle)
        self._live_dot.setVisible(recording)
        self._live_spinner.setVisible(working)
        self.ribbon.setVisible(not idle)
        self._timer_label.setVisible(recording)
        if recording:
            self._hero.setText("Listening")
            self._timer_label.setText(_clock(self._elapsed))
            self._tick.start()
            self._caret.start()
            self._caret_on = True
            stop = "Stop and paste" if self._paste_on_stop else "Stop and copy"
            self.record_button.set_mode("stop", stop)
            cancel = "to cancel without pasting" if self._paste_on_stop else (
                "to cancel without copying"
            )
            self._set_hint([("text", "Press"), ("key", "Esc"), ("text", cancel)])
            self._show_interim(True)
        elif working:
            self._hero.setText("Polishing" if self._polishing else "Transcribing")
            self._tick.stop()
            self._caret.stop()
            self.record_button.set_mode(
                "working",
                "Polishing the text" if self._polishing else "Turning speech into text",
            )
            self._set_hint([("text", "Your voice stays on this computer.")])
            self._show_interim(bool(self._interim_plain))
        else:
            self._tick.stop()
            self._caret.stop()
            self._update_greeting()
            self.record_button.set_mode("start", "Start dictation")
            self._set_title()
            then = "the text is pasted where your cursor is." if self._paste_on_stop else (
                "the text is copied to your clipboard."
            )
            self._set_hint([("text", f"Speak, let go, and {then}")])
            self._interim_plain = ""
            self._show_interim(False)
        self._hero.setProperty("state", state)
        _repolish(self._hero)
        self._interim.setProperty("dim", working)
        _repolish(self._interim)
        self._render_interim()

    def set_polishing(self) -> None:
        """AI Polish is rewriting the transcript (still before it lands)."""
        self._polishing = True
        if self._state == "draining":
            self._apply_state("draining")

    def _keys(self) -> list[str]:
        keys = []
        for part in (p.strip() for p in self._shortcut_display.split("+")):
            keys.append(part.capitalize() if part.isupper() and len(part) > 1 else part)
        return keys

    @staticmethod
    def _fill(row: QHBoxLayout, parts: list[tuple[str, str]], text_name: str) -> None:
        while row.count():
            item = row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for kind, text in parts:
            label = QLabel(text)
            label.setObjectName("cardKey" if kind == "key" else text_name)
            if kind == "key":
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(label, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)

    def _set_title(self) -> None:
        parts: list[tuple[str, str]] = [("text", "Hold")]
        parts += [("key", key) for key in self._keys()]
        parts.append(("text", "to dictate in any app"))
        self._fill(self._title_row, parts, "cardTitle")

    def _set_hint(self, parts: list[tuple[str, str]]) -> None:
        self._fill(self._hint_row, parts, "cardNote")

    @staticmethod
    def _row_text(row: QHBoxLayout) -> list[str]:
        words = []
        for index in range(row.count()):
            widget = row.itemAt(index).widget()
            if isinstance(widget, QLabel):
                words.append(widget.text())
        return words

    def hint_text(self) -> str:
        """The card's text in idle (shortcut and what happens), keys joined with spaces."""
        words = self._row_text(self._title_row) if self._state == "idle" else []
        return " ".join(words + self._row_text(self._hint_row))

    def _on_tick(self) -> None:
        self._elapsed += 1
        self._timer_label.setText(_clock(self._elapsed))

    def push_level(self, level: float) -> None:
        """Older level feed; the bars draw from :meth:`push_audio`."""
        del level

    def push_audio(self, pcm: bytes) -> None:
        if self._state == "recording":
            self.ribbon.push_audio(pcm)

    def reset_ribbon(self) -> None:
        self.ribbon.reset()

    # -- words ---------------------------------------------------------------------
    def interim_text(self) -> str:
        return self._interim_plain

    def set_interim(self, text: str) -> None:
        cleaned = " ".join(text.split())
        if cleaned and cleaned != self._interim_plain:
            self._interim_plain = cleaned
            self._show_interim(True)
            self._render_interim()

    def clear_interim(self) -> None:
        self._interim_plain = ""
        self._render_interim()
        if self._state != "recording":
            self._show_interim(False)

    def _show_interim(self, visible: bool) -> None:
        self._interim.setVisible(visible and (bool(self._interim_plain) or self._state == "recording"))
        self._interim_gap.setVisible(False)

    def _blink(self) -> None:
        self._caret_on = not self._caret_on
        self._render_interim()

    def _render_interim(self) -> None:
        caret = ""
        if self._state == "recording":
            tint = "#FFFFEB" if self._caret_on or reduced_motion() else "transparent"
            caret = f'<span style="color:{tint}">&#x258F;</span>'
        body = html.escape(self._interim_plain)
        if not body and self._state == "recording":
            body = '<span style="color:rgba(255,255,235,0.55)">Start speaking…</span>'
        self._interim.setText(f'<p style="line-height:138%;margin:0">{body}{caret}</p>')

    # -- result --------------------------------------------------------------------
    def set_result(self, text: str, duration: float = 0.0, outcome: str = "") -> None:
        """Show the finished transcript until the next dictation starts."""
        cleaned = " ".join((text or "").split())
        if not cleaned:
            return
        self._result_text = cleaned
        shown = cleaned if len(cleaned) <= 600 else cleaned[:600].rstrip() + "…"
        self._result_label.setText(
            f'<p style="line-height:150%;margin:0">{html.escape(shown)}</p>'
        )
        self._outcome.setText(_OUTCOMES.get(outcome, ""))
        self._outcome_box.setVisible(outcome in _OUTCOMES)
        self._result_length.setText(_clock(duration))
        self._result_length.setVisible(duration > 0)
        words = _word_count(cleaned)
        self._result_words.setText("1 word" if words == 1 else f"{words:,} words")
        self.copy_result_button.setText("Copy")
        self.polish_button.setText("Polish with AI")
        self.polish_button.setEnabled(True)
        self.polish_button.setVisible(self._polish_available)
        self._interim_plain = ""
        self._show_interim(False)
        self._result.show()
        self._result_gap.show()
        self._rebuild_recent()
        self._stop_reveals()
        self._reveal(self._result)

    def result_text(self) -> str:
        return self._result_text

    def set_polish_busy(self, busy: bool) -> None:
        self.polish_button.setEnabled(not busy)
        self.polish_button.setText("Polishing…" if busy else "Polish with AI")

    def _hide_result(self) -> None:
        self._stop_reveals()
        self._result_text = ""
        self._result.hide()
        self._result_gap.hide()
        self._rebuild_recent()

    def _reveal(self, widget: QWidget) -> None:
        if reduced_motion():
            return
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)
        fade = QPropertyAnimation(effect, b"opacity")
        fade.setDuration(ANIMATION_NORMAL)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(ease_out_curve())
        group = QSequentialAnimationGroup(self)
        group.addAnimation(fade)
        # Drop the effect afterwards so the card renders normally again.
        group.finished.connect(lambda: self._end_reveal(group, widget))
        self._reveals.append(group)
        group.start()

    def _end_reveal(self, group: QSequentialAnimationGroup, widget: QWidget) -> None:
        if group in self._reveals:
            self._reveals.remove(group)
            widget.setGraphicsEffect(None)
            group.deleteLater()

    def _stop_reveals(self) -> None:
        for group in self._reveals:
            group.stop()
            group.deleteLater()
        self._reveals.clear()
        if self._result.graphicsEffect() is not None:
            self._result.setGraphicsEffect(None)

    def _copy_result(self) -> None:
        QApplication.clipboard().setText(self._result_text)
        self.copy_result_button.setText("Copied")
        QTimer.singleShot(1200, lambda: self.copy_result_button.setText("Copy"))

    def _request_polish(self) -> None:
        if self._result_text:
            self.polish_requested.emit(self._result_text)

    # -- errors ----------------------------------------------------------------------
    def show_error(self, message: str) -> None:
        """Show what went wrong; cleared when the next dictation starts."""
        self._error.setText(message)
        self._error.setVisible(bool(message))
        self._error_gap.setVisible(bool(message))

    def clear_error(self) -> None:
        self._error.clear()
        self._error.hide()
        self._error_gap.hide()

    # -- shortcut keycaps -----------------------------------------------------------
    def set_shortcut(self, shortcut: str) -> None:
        try:
            self._shortcut_display = display_hotkey(shortcut)
        except ValueError:
            self._shortcut_display = "Ctrl + Alt + Space"
        if self._state == "idle":
            self._apply_state("idle")

    # -- language ---------------------------------------------------------------------
    def set_language(self, language: str) -> None:
        index = self._language.findData(language)
        self._language.blockSignals(True)
        self._language.setCurrentIndex(max(0, index))
        self._language.blockSignals(False)

    def set_language_locked(self, language: str | None, reason: str = "") -> None:
        """Pin the picker to ``language`` while a single-language model is active."""
        if language:
            self._unlocked_language = getattr(self, "_unlocked_language", None) or (
                self._language.currentData()
            )
            self.set_language(language)
            self._language.setEnabled(False)
            self._language.setToolTip(reason)
        elif not self._language.isEnabled():
            self._language.setEnabled(True)
            self._language.setToolTip("Spoken language")
            if getattr(self, "_unlocked_language", None):
                self.set_language(self._unlocked_language)
            self._unlocked_language = None

    @property
    def language_picker(self) -> QComboBox:
        return self._language

    def _emit_language(self, _index: int) -> None:
        self.language_changed.emit(self._language.currentData() or "auto")

    # -- input -----------------------------------------------------------------------
    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key.Key_Escape and self._state == "recording":
            self.cancel_requested.emit()
            event.accept()
            return
        if (
            key == Qt.Key.Key_Space
            and not event.isAutoRepeat()
            and not self._language.hasFocus()
        ):
            self.dictation_toggled.emit()
            event.accept()
            return
        super().keyPressEvent(event)
