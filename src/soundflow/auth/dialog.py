"""Sign-in / create-account window shown before the main window."""

from __future__ import annotations

import html
import re
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QByteArray, QObject, QPointF, QRectF, Qt, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QFontMetricsF,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from soundflow.cloud.account import GENDERS, Account
from soundflow.cloud.client import AuthError, CloudError
from soundflow.design import (
    BODY_FONT,
    CONTROL_HEIGHT_LG,
    CONTROL_HEIGHT_MD,
    COVER_FONT,
    FONT_BODY,
    FONT_SMALL,
    SPACE_2,
    SPACE_3,
    SPACE_5,
    SPACE_6,
    SPACE_10,
    icon,
    icon_pixmap,
    palette,
    resolved_dark,
    stylesheet,
)
from soundflow.ui.widgets.segmented import SegmentedControl
from soundflow.ui.widgets.spinner import Spinner

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8

ART_IMAGE = Path(__file__).resolve().parents[1] / "assets" / "art" / "auth-flowers.jpg"
ART_RADIUS = 18
ART_PADDING = 32
MASTHEAD = "Soundflow"
COVER_LINE = ("Delulu ideas,", "perfectly spelled.")
EYE_COLOR = "#8A8A80"  # reads on the white field in light and the dark field in dark
FORM_WIDTH = 470
FORM_SIDE_MARGIN = 52
MAIL_TILE = 52
MAIL_ICON = 26

MAIL_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="5.5" width="18" height="13" rx="2.5"/>'
    '<path d="m4.5 7.5 7.5 5.5 7.5-5.5"/></svg>'
)


class _Relay(QObject):
    """Moves worker-thread results onto the GUI thread (queued slots)."""

    succeeded = Signal(object)
    failed = Signal(object)

    def __init__(self, on_ok: Callable[[Any], None], on_error: Callable[[Exception], None]):
        super().__init__()
        self._on_ok = on_ok
        self._on_error = on_error
        self.succeeded.connect(self._ok)
        self.failed.connect(self._err)

    @Slot(object)
    def _ok(self, value: Any) -> None:
        self._on_ok(value)

    @Slot(object)
    def _err(self, exc: Exception) -> None:
        self._on_error(exc)


def run_in_background(
    work: Callable[[], Any],
    on_ok: Callable[[Any], None],
    on_error: Callable[[Exception], None],
    keep: list,
) -> None:
    relay = _Relay(on_ok, on_error)
    keep.append(relay)  # keep the QObject alive until it fires

    def target() -> None:
        try:
            result = work()
        except Exception as exc:  # delivered to on_error on the GUI thread
            relay.failed.emit(exc)
        else:
            relay.succeeded.emit(result)

    threading.Thread(target=target, name="soundflow-auth", daemon=True).start()


def _label(text: str, name: str, size: int, family: str = BODY_FONT) -> QLabel:
    label = QLabel(text)
    label.setObjectName(name)
    label.setFont(QFont(family, size))
    label.setWordWrap(True)
    return label


def _password_field() -> QLineEdit:
    """A password field with an eye at its end that shows or hides what you typed."""
    field = _field("", password=True)
    field.setObjectName("passwordField")
    toggle = QAction(icon("eye", EYE_COLOR), "Show password", field)
    toggle.setCheckable(True)
    toggle.setToolTip("Show password")

    def flip(shown: bool) -> None:
        field.setEchoMode(QLineEdit.EchoMode.Normal if shown else QLineEdit.EchoMode.Password)
        label = "Hide password" if shown else "Show password"
        toggle.setIcon(icon("eye-off" if shown else "eye", EYE_COLOR))
        toggle.setText(label)
        toggle.setToolTip(label)

    toggle.toggled.connect(flip)
    field.addAction(toggle, QLineEdit.ActionPosition.TrailingPosition)
    field.reveal_action = toggle
    return field


def _field(placeholder: str, password: bool = False) -> QLineEdit:
    field = QLineEdit()
    field.setPlaceholderText(placeholder)
    field.setFixedHeight(CONTROL_HEIGHT_MD)
    field.setFont(QFont(BODY_FONT, FONT_BODY))
    if password:
        field.setEchoMode(QLineEdit.EchoMode.Password)
    return field


def _button(text: str, name: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName(name)
    button.setFixedHeight(CONTROL_HEIGHT_LG)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def _link(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("textActionButton")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFlat(True)
    return button


def _email_sentence(before: str, email: str, after: str) -> str:
    """A sentence with the address in bold, escaped for a rich-text label."""
    return f"{before} <b>{html.escape(email)}</b> {after}"


def _mail_mark(color: str) -> QLabel:
    """The mail icon on an accent tile, for the confirm and reset screens."""
    renderer = QSvgRenderer(QByteArray(MAIL_SVG.format(color=color).encode("utf-8")))
    scale = 2.0
    pixels = round(MAIL_ICON * scale)
    pixmap = QPixmap(pixels, pixels)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, pixels, pixels))
    painter.end()
    pixmap.setDevicePixelRatio(scale)
    mark = QLabel()
    mark.setObjectName("mailMark")
    mark.setFixedSize(MAIL_TILE, MAIL_TILE)
    mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
    mark.setPixmap(pixmap)
    return mark


class _ArtPanel(QFrame):
    """A magazine cover: the flower picture, "Soundflow" as the masthead and
    one cover line. Painted, not animated, and the same in both themes."""

    def __init__(self, dark: bool, parent: QWidget | None = None) -> None:
        del dark  # the picture is the same in both themes
        super().__init__(parent)
        self.setObjectName("authArt")
        self.picture = QPixmap(str(ART_IMAGE))
        self.masthead = MASTHEAD
        self.cover_line = COVER_LINE
        self._mast_font = QFont(COVER_FONT)
        self._mast_font.setWeight(QFont.Weight.Medium)
        self._line_font = QFont(COVER_FONT)
        self._line_font.setItalic(True)

    def _cover_rect(self) -> QRectF:
        """Where the picture lands: it fills the panel, cropped from the centre."""
        if self.picture.isNull():
            return QRectF(self.rect())
        scale = max(self.width() / self.picture.width(), self.height() / self.picture.height())
        width, height = self.picture.width() * scale, self.picture.height() * scale
        return QRectF((self.width() - width) / 2, (self.height() - height) / 2, width, height)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        width, height = float(self.width()), float(self.height())
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, width, height), ART_RADIUS, ART_RADIUS)
        painter.setClipPath(clip)
        painter.fillRect(self.rect(), QColor("#06100D"))
        if not self.picture.isNull():
            painter.drawPixmap(self._cover_rect(), self.picture, QRectF(self.picture.rect()))

        # Shade the top and the bottom so cream type reads on any part of it.
        top = QLinearGradient(0, 0, 0, height * 0.34)
        top.setColorAt(0.0, QColor(6, 16, 13, 140))
        top.setColorAt(1.0, QColor(6, 16, 13, 0))
        painter.fillRect(QRectF(0, 0, width, height * 0.34), top)
        bottom = QLinearGradient(0, height * 0.4, 0, height)
        bottom.setColorAt(0.0, QColor(6, 16, 13, 0))
        bottom.setColorAt(0.47, QColor(6, 16, 13, 166))
        bottom.setColorAt(1.0, QColor(6, 16, 13, 230))
        painter.fillRect(QRectF(0, height * 0.4, width, height * 0.6), bottom)

        painter.setPen(QColor("#FFFFEB"))
        # Masthead across the top, sized to the panel like a magazine title.
        mast_px = max(40, min(76, round(width * 0.135)))
        self._mast_font.setPixelSize(mast_px)
        self._mast_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -mast_px * 0.033)
        painter.setFont(self._mast_font)
        mast_metrics = QFontMetricsF(self._mast_font)
        painter.drawText(
            QRectF(0, 22, width, mast_metrics.height()),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            self.masthead,
        )

        # The cover line, bottom left, two italic lines set tight.
        line_px = max(30, min(46, round(width * 0.078)))
        self._line_font.setPixelSize(line_px)
        self._line_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -line_px * 0.018)
        painter.setFont(self._line_font)
        metrics = QFontMetricsF(self._line_font)
        leading = line_px * 1.04
        baseline = height - ART_PADDING - metrics.descent()
        for index, text in enumerate(reversed(self.cover_line)):
            painter.drawText(QPointF(ART_PADDING, baseline - index * leading), text)
        painter.end()


class GenderPicker(SegmentedControl):
    """Male / Female with nothing picked until the person chooses one."""

    def __init__(self, parent: QWidget | None = None) -> None:
        options = tuple((value, value.capitalize()) for value in GENDERS)
        super().__init__(options, None, parent, accessible_name="Gender")
        # The control always selects its first option; sign-up needs an explicit choice.
        self._group.setExclusive(False)
        for button in self._group.buttons():
            button.setChecked(False)
        self._group.setExclusive(True)
        self._value = ""

    def value(self) -> str:
        return self._value



class _Page(QWidget):
    """One screen of the form column, vertically centred in its space."""

    def __init__(self, title: str, subtitle: str, mark: QWidget | None = None) -> None:
        super().__init__()
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(0)
        self.layout_.addStretch(1)
        if mark is not None:
            self.layout_.addWidget(mark, 0, Qt.AlignmentFlag.AlignLeft)
            self.layout_.addSpacing(SPACE_5)
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        heading.setWordWrap(True)
        self.layout_.addWidget(heading)
        self.layout_.addSpacing(SPACE_2)
        self.subtitle = _label(subtitle, "mutedText", FONT_SMALL)
        self.layout_.addWidget(self.subtitle)
        self.layout_.addSpacing(SPACE_6)

    def add(self, widget: QWidget, gap: int = SPACE_3) -> QWidget:
        self.layout_.addWidget(widget)
        if gap:
            self.layout_.addSpacing(gap)
        return widget

    def labelled(self, text: str, widget: QWidget) -> QWidget:
        caption = QLabel(text)
        caption.setObjectName("fieldLabel")
        self.layout_.addWidget(caption)
        self.layout_.addSpacing(SPACE_2)
        return self.add(widget, gap=SPACE_5)

    def label_line(self, text: str, link_text: str) -> QPushButton:
        """A field caption with a link on the same line, on the right."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        caption = QLabel(text)
        caption.setObjectName("fieldLabel")
        row.addWidget(caption)
        row.addStretch(1)
        link = _link(link_text)
        row.addWidget(link)
        self.layout_.addLayout(row)
        self.layout_.addSpacing(SPACE_2)
        return link

    def switch_line(self, text: str, link_text: str) -> QPushButton:
        """A centred line such as 'New to Soundflow? Create an account'."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        caption = QLabel(text)
        caption.setObjectName("mutedText")
        row.addWidget(caption)
        link = _link(link_text)
        row.addWidget(link)
        row.addStretch(1)
        self.layout_.addLayout(row)
        return link

    def finish(self) -> None:
        self.layout_.addStretch(1)


class AuthDialog(QDialog):
    """Modal gate: accepted once the account holds a valid session."""

    def __init__(self, account: Account, appearance: str = "dark", parent=None) -> None:
        super().__init__(parent)
        self.account = account
        self._tasks: list = []
        self._pending_email = ""
        dark = resolved_dark(appearance)
        self._dark = dark
        self.setWindowTitle("Sign in to Soundflow")
        self.setObjectName("authDialog")
        self.setMinimumSize(880, 580)
        self.resize(1000, 640)
        self.setStyleSheet(stylesheet(dark))
        # Painted widgets (the activity indicator) read the theme from here.
        app = QApplication.instance()
        if app is not None and app.property("soundflowDark") is None:
            app.setProperty("soundflowDark", dark)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        art_column = QWidget()
        art_layout = QVBoxLayout(art_column)
        art_layout.setContentsMargins(SPACE_3 + 2, SPACE_3 + 2, 0, SPACE_3 + 2)
        self.art = _ArtPanel(dark)
        art_layout.addWidget(self.art)
        root.addWidget(art_column, 1)

        form = QWidget()
        form.setObjectName("authForm")
        form.setFixedWidth(FORM_WIDTH)
        column = QVBoxLayout(form)
        column.setContentsMargins(FORM_SIDE_MARGIN, SPACE_6, FORM_SIDE_MARGIN, SPACE_10)
        column.setSpacing(0)
        brand_row = QHBoxLayout()
        brand_row.setSpacing(SPACE_2)
        mark = QLabel()
        mark.setPixmap(icon_pixmap("brand", palette(dark)["accent"], 22))
        brand_row.addWidget(mark)
        brand = QLabel("Soundflow")
        brand.setObjectName("authBrand")
        brand_row.addWidget(brand)
        brand_row.addStretch(1)
        column.addLayout(brand_row)

        self.pages = QStackedWidget()
        column.addWidget(self.pages, 1)
        self._build_sign_in()
        self._build_sign_up()
        self._build_check_email()
        self._build_reset()

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(SPACE_2)
        self.spinner = Spinner(14)
        self.spinner.hide()
        status_row.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignVCenter)
        self.status = _label("", "captionText", FONT_SMALL)
        self.status.setMinimumHeight(18)
        status_row.addWidget(self.status, 1)
        column.addLayout(status_row)
        root.addWidget(form)
        self._show(self.sign_in_page)

    # -- pages ------------------------------------------------------------
    def _build_sign_in(self) -> None:
        page = _Page("Sign in to Soundflow", "Your transcripts sync to every computer you sign in on.")
        self.in_email = page.labelled("Email", _field("you@example.com"))
        forgot = page.label_line("Password", "Forgot password?")
        forgot.clicked.connect(self._forgot_password)
        self.in_password = page.add(_password_field(), gap=SPACE_5)
        self.in_password.returnPressed.connect(self._sign_in)
        self.in_submit = page.add(_button("Sign in", "primaryButton"), gap=SPACE_5)
        self.in_submit.clicked.connect(self._sign_in)
        switch = page.switch_line("New to Soundflow?", "Create an account")
        switch.clicked.connect(lambda: self._show(self.sign_up_page))
        page.finish()
        self.sign_in_page = page
        self.pages.addWidget(page)

    def _build_sign_up(self) -> None:
        page = _Page(
            "Create your account",
            "Every dictation is saved to it, so History follows you between computers.",
        )
        self.up_name = page.labelled("Full name", _field(""))
        self.up_email = page.labelled("Email", _field("you@example.com"))
        self.up_gender = page.labelled("Gender", GenderPicker())

        self.up_password = _password_field()
        self.up_confirm = _password_field()
        split = QHBoxLayout()
        split.setContentsMargins(0, 0, 0, 0)
        split.setSpacing(SPACE_3)
        split.addLayout(_column("Password", self.up_password, "At least 8 characters."), 1)
        split.addLayout(_column("Confirm password", self.up_confirm), 1)
        page.layout_.addLayout(split)
        page.layout_.addSpacing(SPACE_5)

        self.up_submit = page.add(_button("Create account", "primaryButton"), gap=SPACE_5)
        self.up_submit.clicked.connect(self._sign_up)
        switch = page.switch_line("Already have an account?", "Sign in")
        switch.clicked.connect(lambda: self._show(self.sign_in_page))
        page.finish()
        self.sign_up_page = page
        self.pages.addWidget(page)

    def _build_check_email(self) -> None:
        page = _Page(
            "Confirm your email",
            "We sent a link to your email. Open it on this computer, then come back and sign in.",
            mark=_mail_mark(palette(self._dark)["accent"]),
        )
        self.check_email_label = page.subtitle
        self.check_email_label.setTextFormat(Qt.TextFormat.RichText)
        confirmed = page.add(_button("I've confirmed it, sign in", "primaryButton"), gap=SPACE_5)
        confirmed.clicked.connect(lambda: self._show(self.sign_in_page))
        resend = page.switch_line("No email after a minute?", "Send it again")
        resend.clicked.connect(self._resend)
        page.finish()
        self.check_email_page = page
        self.pages.addWidget(page)

    def _build_reset(self) -> None:
        page = _Page(
            "Check your email",
            "If your email has an account, a link to reset the password is on its way.",
            mark=_mail_mark(palette(self._dark)["accent"]),
        )
        self.reset_email_label = page.subtitle
        self.reset_email_label.setTextFormat(Qt.TextFormat.RichText)
        back = page.add(_button("Back to sign in", "primaryButton"), gap=0)
        back.clicked.connect(lambda: self._show(self.sign_in_page))
        page.finish()
        self.reset_page = page
        self.pages.addWidget(page)

    # -- helpers ----------------------------------------------------------
    def _show(self, page: QWidget) -> None:
        self.pages.setCurrentWidget(page)
        self._set_status("")

    def _set_status(self, text: str, error: bool = False) -> None:
        self.status.setObjectName("errorText" if error else "captionText")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.status.setText(text)

    def _busy(self, busy: bool, text: str = "") -> None:
        self.pages.setEnabled(not busy)
        self.spinner.setVisible(busy)
        if text:
            self._set_status(text)

    def _fail(self, exc: Exception) -> None:
        self._busy(False)
        if isinstance(exc, AuthError) and exc.code == "email_not_confirmed":
            self._pending_email = self.in_email.text().strip()
        message = str(exc) if isinstance(exc, CloudError) else f"Unexpected error: {exc}"
        self._set_status(message, True)

    def _signed_in(self, session) -> None:
        self.account.set_session(session)
        self.accept()

    # -- actions ----------------------------------------------------------
    def _sign_in(self) -> None:
        email = self.in_email.text().strip().lower()
        password = self.in_password.text()
        if not EMAIL_RE.match(email) or not password:
            self._set_status("Enter your email and password.", True)
            return
        self._busy(True, "Signing in…")
        run_in_background(
            lambda: self.account.client.sign_in_with_password(email, password),
            self._signed_in,
            self._fail,
            self._tasks,
        )

    def _sign_up(self) -> None:
        name = " ".join(self.up_name.text().split())
        email = self.up_email.text().strip().lower()
        password = self.up_password.text()
        gender = self.up_gender.value()
        if not name:
            return self._set_status("Enter your name.", True)
        if not EMAIL_RE.match(email):
            return self._set_status("Enter a valid email address.", True)
        if len(password) < MIN_PASSWORD:
            return self._set_status(
                f"Password must be at least {MIN_PASSWORD} characters.", True
            )
        if password != self.up_confirm.text():
            return self._set_status("Passwords don't match.", True)
        if gender not in GENDERS:
            return self._set_status("Choose male or female.", True)
        self._busy(True, "Creating your account…")

        def done(result) -> None:
            self._busy(False)
            if result.session is not None:
                self._signed_in(result.session)
                return
            if result.already_registered:
                self.in_email.setText(email)
                self._show(self.sign_in_page)
                self._set_status("That email already has an account. Sign in instead.", True)
                return
            self._pending_email = email
            self.in_email.setText(email)
            self.check_email_label.setText(
                _email_sentence(
                    "We sent a link to", email, "Open it on this computer, then come back and sign in."
                )
            )
            self._show(self.check_email_page)

        run_in_background(
            lambda: self.account.client.sign_up(email, password, name, gender),
            done,
            self._fail,
            self._tasks,
        )

    def _resend(self) -> None:
        email = self._pending_email
        if not email:
            return
        self._busy(True, "Sending…")
        run_in_background(
            lambda: self.account.client.resend_confirmation(email),
            lambda _r: (self._busy(False), self._set_status(f"Sent again to {email}.")),
            self._fail,
            self._tasks,
        )

    def _forgot_password(self) -> None:
        email = self.in_email.text().strip().lower()
        if not EMAIL_RE.match(email):
            self._set_status("Type your email above first, then press Forgot password.", True)
            return
        self._busy(True, "Sending reset link…")

        def done(_result) -> None:
            self._busy(False)
            self.reset_email_label.setText(
                _email_sentence(
                    "If", email, "has an account, a link to reset the password is on its way."
                )
            )
            self._show(self.reset_page)

        run_in_background(
            lambda: self.account.client.send_password_reset(email),
            done,
            self._fail,
            self._tasks,
        )


def _column(caption: str, field: QWidget, helper: str = "") -> QVBoxLayout:
    """A caption over a field, with a helper line under it (empty when unused)."""
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(SPACE_2)
    label = QLabel(caption)
    label.setObjectName("fieldLabel")
    layout.addWidget(label)
    layout.addWidget(field)
    # Always a helper line, so the two columns line up even when only one has text.
    note = QLabel(helper)
    note.setObjectName("dimText")
    layout.addWidget(note)
    return layout


__all__ = ["AuthDialog", "run_in_background"]
