"""About card — right-side panel in the Preferences dialog.

Mirrors the reference layout: logo, app name, version, three tagline
pills (Offline · Private · Secure), description, and a ``Check system``
action. Plus a System card underneath showing live model + status.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from soundflow.design import (
    BODY_FONT,
    DISPLAY_FONT,
    FONT_BODY,
    FONT_HEADING,
    FONT_SMALL,
    FONT_TITLE,
    SPACE_2,
    SPACE_3,
    SPACE_4,
)


class _Pill(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("aboutPill")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont(BODY_FONT, FONT_SMALL))


class AboutCard(QWidget):
    """Right-side About card shown next to Preferences tabs."""

    check_system_clicked = Signal()

    def __init__(
        self,
        app_name: str = "Soundflow",
        version: str = "1.0.0",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("aboutCard")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setFixedWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        layout.setSpacing(SPACE_3)

        # Logo (rendered as a styled glyph to avoid bundling an asset)
        logo = QLabel("\u2742")  # eight-teardrop-spoked asterisk
        logo.setFont(QFont(DISPLAY_FONT, 48))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setObjectName("aboutLogo")
        layout.addWidget(logo)

        # Title + version
        title = QLabel(app_name)
        title.setFont(QFont(DISPLAY_FONT, FONT_TITLE))
        title.setObjectName("headingText")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version_lbl = QLabel(f"Version {version}")
        version_lbl.setObjectName("mutedText")
        version_lbl.setFont(QFont(BODY_FONT, FONT_SMALL))
        version_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_lbl)

        # Pill row
        pills = QHBoxLayout()
        pills.setSpacing(SPACE_2)
        for label in ("Offline", "Private", "Secure"):
            pills.addWidget(_Pill(label))
        layout.addLayout(pills)

        # Description
        desc = QLabel("All processing happens locally on your device.")
        desc.setObjectName("mutedText")
        desc.setFont(QFont(BODY_FONT, FONT_SMALL))
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        layout.addStretch(1)

        # System mini-card
        sys_card = QWidget()
        sys_card.setObjectName("systemMiniCard")
        sl = QVBoxLayout(sys_card)
        sl.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        sl.setSpacing(SPACE_2)

        sys_title = QLabel("System")
        sys_title.setObjectName("headingText")
        sys_title.setFont(QFont(BODY_FONT, FONT_HEADING))
        sl.addWidget(sys_title)

        status_row = QHBoxLayout()
        status_dot = QLabel("\u25CF")
        status_dot.setObjectName("statusDot")
        status_dot.setProperty("state", "ready")
        status_row.addWidget(status_dot)
        status_row.addWidget(QLabel("Status"))
        status_row.addStretch(1)
        status_value = QLabel("Ready")
        status_value.setObjectName("mutedText")
        status_row.addWidget(status_value)
        sl.addLayout(status_row)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model"))
        model_row.addStretch(1)
        model_value = QLabel("Local Model")
        model_value.setObjectName("mutedText")
        model_row.addWidget(model_value)
        sl.addLayout(model_row)

        check_btn = QPushButton("Check system")
        check_btn.setObjectName("primaryButton")
        check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        check_btn.clicked.connect(self.check_system_clicked)
        sl.addWidget(check_btn)

        layout.addWidget(sys_card)


__all__ = ["AboutCard"]