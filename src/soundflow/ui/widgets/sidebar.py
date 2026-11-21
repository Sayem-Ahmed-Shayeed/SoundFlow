"""Persistent application sidebar used by every Soundflow page."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from soundflow.design import icon, icon_size, palette
from soundflow.design.spacing import SIDEBAR_WIDTH

_PAGES = (
    ("dictation", "home", "Home"),
    ("history", "history", "History"),
    ("playground", "playground", "Playground"),
    ("preferences", "settings", "Preferences"),
)

# Sync status text -> dot state.
_SYNC_STATES = {
    "Synced": "ok",
    "Syncing…": "busy",
    "Offline · will sync later": "warn",
    "Cloud setup needed": "warn",
    "Sync failed · retrying": "error",
    "Signed out": "error",
}
_SYNC_LABELS = {
    "Offline · will sync later": "Offline",
    "Sync failed · retrying": "Sync failed",
    "Cloud setup needed": "Setup needed",
}
_SYNC_TIPS = {
    "Offline · will sync later": "Offline. Transcripts are saved here and sync when you reconnect.",
    "Sync failed · retrying": "Sync failed. Soundflow will retry in a couple of minutes.",
    "Cloud setup needed": "The Supabase tables are missing. See the README.",
}


def brand_mark(size: int = 22, scale: float = 2.0, color: str = "#1A1A1A") -> QPixmap:
    """Five bars of a sound level, in one ink colour: Soundflow's logo."""
    pixmap = QPixmap(round(size * scale), round(size * scale))
    pixmap.setDevicePixelRatio(scale)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    unit = size / 24
    heights = (7, 13, 19, 11, 15)
    painter.setBrush(QColor(color))
    for index, height in enumerate(heights):
        painter.drawRoundedRect(
            QRectF((3 + index * 4) * unit, (12 - height / 2) * unit, 2.6 * unit, height * unit),
            1.3 * unit,
            1.3 * unit,
        )
    painter.end()
    return pixmap


def _initials(name: str) -> str:
    parts = [p for p in name.replace("@", " ").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:1].upper()
    return (parts[0][:1] + parts[-1][:1]).upper()


class AppSidebar(QFrame):
    page_requested = Signal(str)
    sign_out_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sideBar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self._dark = True
        self._active = "dictation"
        self._buttons: dict[str, QPushButton] = {}
        self._icons: dict[str, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 18, 12, 12)
        layout.setSpacing(2)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(8, 0, 0, 0)
        brand_row.setSpacing(8)
        self._brand_mark = QLabel()
        self._brand_mark.setFixedSize(22, 22)
        brand_row.addWidget(self._brand_mark)
        brand = QLabel("Soundflow")
        brand.setObjectName("brand")
        brand_row.addWidget(brand)
        brand_row.addStretch(1)
        layout.addLayout(brand_row)
        layout.addSpacing(22)

        for key, glyph, label in _PAGES:
            button = QPushButton(label)
            button.setObjectName("sideNavButton")
            button.setProperty("active", False)
            button.setIconSize(icon_size(18))
            button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, selected=key: self.page_requested.emit(selected)
            )
            self._buttons[key] = button
            self._icons[key] = glyph
            layout.addWidget(button)

        layout.addStretch(1)

        # Account: avatar, name, sync state, sign out.
        self.account_box = QWidget()
        self.account_box.setObjectName("sideAccount")
        account = QHBoxLayout(self.account_box)
        account.setContentsMargins(6, 12, 0, 0)
        account.setSpacing(10)
        self.avatar = QLabel("")
        self.avatar.setObjectName("accountAvatar")
        self.avatar.setFixedSize(32, 32)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        account.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignTop)

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(1)
        self.account_name = QLabel("")
        self.account_name.setObjectName("accountName")
        text.addWidget(self.account_name)
        sync_row = QHBoxLayout()
        sync_row.setSpacing(5)
        self.sync_dot = QLabel("●")
        self.sync_dot.setObjectName("syncDot")
        self.sync_dot.setProperty("state", "busy")
        self.sync_dot.setStyleSheet("font-size: 8px;")
        sync_row.addWidget(self.sync_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self.sync_status = QLabel("")
        self.sync_status.setObjectName("accountMeta")
        sync_row.addWidget(self.sync_status, 1)
        text.addLayout(sync_row)
        account.addLayout(text, 1)

        self.sign_out_button = QPushButton()
        self.sign_out_button.setObjectName("iconButton")
        self.sign_out_button.setToolTip("Sign out")
        self.sign_out_button.setAccessibleName("Sign out")
        self.sign_out_button.setIconSize(icon_size(16))
        self.sign_out_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sign_out_button.clicked.connect(self.sign_out_requested.emit)
        account.addWidget(self.sign_out_button, 0, Qt.AlignmentFlag.AlignTop)
        self.account_box.hide()
        layout.addWidget(self.account_box)

        # Kept for callers that read it; the account row replaces the old footer.
        self.account_email = QLabel("")
        self.account_email.hide()

        self.set_dark(True)
        self.select("dictation")

    # -- theming ----------------------------------------------------------
    def set_dark(self, dark: bool) -> None:
        self._dark = dark
        colors = palette(dark)
        self._brand_mark.setPixmap(brand_mark(22, color=colors["text"]))
        self.sign_out_button.setIcon(icon("logout", colors["text3"], 16))
        self._paint_icons()

    def _paint_icons(self) -> None:
        colors = palette(self._dark)
        for key, button in self._buttons.items():
            color = colors["accent"] if key == self._active else colors["text3"]
            button.setIcon(icon(self._icons[key], color, 18))

    # -- account ----------------------------------------------------------
    def set_account(self, name: str, email: str) -> None:
        # Sidebar minus its padding, the avatar, the gaps and Sign out.
        width = self.width() - 24 - 6 - 32 - 20 - 32
        self.avatar.setText(_initials(name or email))
        self.account_name.setText(
            self.account_name.fontMetrics().elidedText(
                name or email, Qt.TextElideMode.ElideRight, max(width, 60)
            )
        )
        self.account_name.setToolTip(f"{name}\n{email}" if name != email else email)
        self.avatar.setToolTip(email)
        self.account_email.setText(email)
        self.account_box.setVisible(bool(email))

    def set_sync_status(self, text: str) -> None:
        self.sync_status.setText(_SYNC_LABELS.get(text, text))
        self.sync_status.setToolTip(_SYNC_TIPS.get(text, ""))
        self.sync_dot.setProperty("state", _SYNC_STATES.get(text, "busy"))
        self.sync_dot.style().unpolish(self.sync_dot)
        self.sync_dot.style().polish(self.sync_dot)

    # -- navigation -------------------------------------------------------
    def select(self, key: str) -> None:
        self._active = key
        for token, button in self._buttons.items():
            button.setProperty("active", token == key)
            button.style().unpolish(button)
            button.style().polish(button)
        self._paint_icons()


__all__ = ["AppSidebar"]
