"""Warm minimal theme tokens and stylesheet generator.

Stone surfaces and ink typography keep the interface quiet, while a muted
sage accent identifies selection, focus, recording, and ready states.
"""

from __future__ import annotations

from .fonts import BODY_FONT, DISPLAY_FONT, MONO_FONT
from .spacing import (
    CONTROL_HEIGHT_MD,
    CONTROL_HEIGHT_LG,
    CONTROL_HEIGHT_SM,
    FONT_BODY,
    FONT_DISPLAY,
    FONT_HEADING,
    FONT_SMALL,
    FONT_TINY,
    FONT_TITLE,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_PILL,
    RADIUS_SM,
    SPACE_2,
    SPACE_3,
    SPACE_4,
)

# --- Palette ---------------------------------------------------------------
# Dark theme: warm charcoal stone with soft limestone type.
FG_CREAM = "#EEEADF"
FG_MUTED = "#A6A094"
FG_DIM = "#76746B"
BG_BLACK = "#161713"
BG_PANEL = "#1E201B"
BG_RAISED = "#292B25"
BORDER = "#383A32"

# Shared semantic colors.
ACCENT = "#91A187"
BORDER_FOCUS = ACCENT
SUCCESS = "#91A187"
WARNING = "#C4A46B"
ERROR = "#C47C70"

# Backwards-compatibility aliases used by the legacy stylesheet generator.
PRIMARY_TEXT = FG_CREAM
PRIMARY_BG = BG_BLACK
SUCCESS_GREEN = SUCCESS


# --- Appearance resolution -------------------------------------------------
def resolved_dark(appearance: str) -> bool:
    """Return True if the requested appearance resolves to the dark theme.

    Only ``"dark"`` and ``"light"`` are accepted. Any other value falls back
    to dark. This replaces the old three-way ``"system"`` resolution.
    """
    if not isinstance(appearance, str):
        return True
    return appearance.strip().lower() != "light"


# --- Stylesheet ------------------------------------------------------------
def stylesheet(dark: bool) -> str:
    """Return the full Qt stylesheet for the requested appearance."""
    if dark:
        return _dark_stylesheet() + _shell_stylesheet(True)
    return _light_stylesheet() + _shell_stylesheet(False)


def _shell_stylesheet(dark: bool) -> str:
    """Screenshot-specific shell rules layered over the shared controls."""
    bg = BG_BLACK if dark else "#F3F0E8"
    sidebar = "#1A1B17" if dark else "#EAE6DC"
    panel = BG_PANEL if dark else "#FBF9F4"
    raised = BG_RAISED if dark else "#E4E1D8"
    text = FG_CREAM if dark else "#22231F"
    muted = FG_MUTED if dark else "#6E7067"
    border = BORDER if dark else "#D4CFC3"
    accent = ACCENT if dark else "#74836A"
    active = "#30372C" if dark else "#DCE3D7"
    dim = FG_DIM if dark else "#85857D"
    hover_border = "#55594C" if dark else "#B9B6AA"
    error = ERROR if dark else "#9A584D"
    warning = WARNING if dark else "#8B6D3D"
    button_ink = "#171914" if dark else "#F8F6F0"
    return f"""
QMainWindow, #appSurface, #contentSurface, QStackedWidget {{
    background: {bg};
    color: {text};
}}
QLabel, QCheckBox, QRadioButton {{
    background: transparent;
    color: {text};
}}
#appSurface {{
    border: 1px solid {border};
    border-radius: 14px;
}}
#sideBar {{
    background: {sidebar};
    border-right: 1px solid {border};
    border-top-left-radius: 14px;
}}
#brandMark {{
    color: {accent};
    font-size: 23px;
    font-weight: 700;
}}
#brand {{
    color: {text};
    font-size: 15px;
    font-weight: 700;
}}
QPushButton#sideNavButton {{
    color: {muted};
    background: transparent;
    border: 0;
    border-radius: 7px;
    padding: 10px 12px;
    text-align: left;
    min-height: 22px;
}}
QPushButton#sideNavButton:hover {{
    color: {text};
    background: {raised};
}}
QPushButton#sideNavButton[active="true"] {{
    color: {accent};
    background: {active};
    border-left: 3px solid {accent};
}}
#privacyCard {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 8px;
}}
#privacyPill {{ color: {accent}; font-weight: 600; }}
#privacyPill {{ font-size: 10px; }}
#railCaption {{ color: {muted}; font-size: 9px; }}
#dictationPage, #historyPage, #playgroundPage, #preferencesPage,
#historyListHolder, #historyScroll, #generalTab, #dictationTab,
#playbackTab, #shortcutsTab, #systemTab {{
    background: {bg};
}}
#systemScroll, #systemScrollViewport, #systemContent,
#generalScroll, #generalScrollViewport, #generalContent {{
    background: {bg};
    border: 0;
}}
#displayText {{ color: {text}; }}
#headingText {{ color: {text}; }}
#mutedText, #captionText {{ color: {muted}; }}
#dimText, #systemLastChecked {{ color: {dim}; }}
#historyCard, #preferencesCard, #localDataCard,
QPushButton#quickActionCard {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 8px;
}}
QPushButton#quickActionCard {{
    padding: 0;
    min-height: 50px;
    max-height: 50px;
}}
#historyCard:hover, QPushButton#quickActionCard:hover {{
    background: {raised};
    border-color: {hover_border};
}}
#historyBody {{
    color: {text};
    font-size: 13px;
    line-height: 1.45;
}}
#historyGroup {{
    color: {accent};
    font-weight: 600;
    padding: 8px 2px 2px 2px;
}}
QPushButton#historyAction {{
    color: {muted};
    background: transparent;
    border: 1px solid {border};
    border-radius: 5px;
    min-height: 26px;
    padding: 3px 9px;
}}
QPushButton#historyAction:hover {{
    color: {text};
    background: {raised};
}}
#historyFeedback[state="error"] {{ color: {error}; }}
#toggleRow {{ background: transparent; min-height: 44px; }}
#toggleRowTitle {{ color: {text}; font-size: 13px; }}
#systemCheckRow, #systemPathBlock {{
    background: {raised};
    border: 1px solid {border};
    border-radius: 7px;
}}
#systemRowTitle {{ color: {text}; font-weight: 600; }}
#systemPathBlock QLabel[role="path"] {{
    color: {text};
    font-family: "{MONO_FONT}";
}}
QLineEdit#systemModelPath {{
    color: {text};
    background: transparent;
    border: 0;
    border-radius: 0;
    padding: 3px 7px;
    font-family: "{MONO_FONT}";
    min-height: 22px;
    max-height: 28px;
}}
#systemStatusPill {{
    color: {muted};
    background: {raised};
    border: 1px solid {border};
    border-radius: 11px;
    padding: 4px 10px;
}}
#systemStatusPill[state="ready"],
QLabel[objectName^="systemStatus"][state="ready"] {{
    color: {accent};
}}
#systemStatusPill[state="warning"],
QLabel[objectName^="systemStatus"][state="warning"] {{
    color: {warning};
}}
#systemStatusPill[state="error"],
QLabel[objectName^="systemStatus"][state="error"] {{
    color: {error};
}}
QPushButton#systemCheckButton {{
    color: {button_ink};
    background: {accent};
    border: 1px solid {accent};
    border-radius: 4px;
    padding: 3px 7px;
    min-height: 20px;
    max-height: 20px;
}}
QPushButton#systemCheckButton:hover {{
    background: {SUCCESS};
    border-color: {SUCCESS};
}}
QPushButton#systemSecondaryButton {{
    color: {text};
    background: {raised};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 3px 7px;
    min-height: 20px;
    max-height: 20px;
}}
QPushButton#systemSecondaryButton:hover {{
    border-color: {accent};
}}
QLineEdit#systemDataPath, QLineEdit#compactPathField {{
    color: {text};
    background: {raised};
    border: 1px solid {border};
    border-radius: 7px;
    padding: 3px 7px;
    font-family: "{MONO_FONT}";
    min-height: 20px;
    max-height: 20px;
}}
QComboBox#compactShortcutField, QComboBox#compactPreferenceField {{
    padding: 3px 7px;
    min-height: 20px;
    max-height: 20px;
    border-radius: 4px;
}}
#historySearch, #playgroundCommand {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 7px;
    color: {text};
}}
#preferencesTabs::pane {{ border: 0; background: transparent; }}
#preferencesTabs QTabBar::tab {{
    color: {muted};
    background: transparent;
    border: 0;
    border-bottom: 2px solid transparent;
    padding: 9px 13px;
}}
#preferencesTabs QTabBar::tab:selected {{
    color: {accent};
    border-bottom-color: {accent};
}}
#statusBar {{
    background: {sidebar};
    border-top: 1px solid {border};
    border-bottom-left-radius: 14px;
    border-bottom-right-radius: 14px;
}}
#statusBarLabel {{ color: {muted}; font-size: 10px; }}
#statusDot[state="ready"] {{ color: {accent}; }}
#statusDot[state="recording"] {{ color: {accent}; }}
#statusDot[state="error"] {{ color: {error}; }}
#statusBarAccent, #quickActionIcon, #aboutLogo, #savedStatus {{ color: {accent}; }}
#keyCap {{
    color: {text};
    background: {raised};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 3px 7px;
}}
#windowChrome QPushButton, QPushButton[objectName^="windowChrome"] {{
    color: {muted};
    background: transparent;
    border: 0;
}}
QPushButton[chrome="true"] {{
    color: {muted};
    background: transparent;
    border: 0;
    min-height: 28px;
    max-height: 28px;
    padding: 0;
}}
#windowChrome {{ background: transparent; }}
#statusBarGear {{
    color: {muted};
    background: transparent;
    border: 0;
    padding: 0;
}}
QPushButton#presetChip {{
    color: {muted};
    background: {panel};
    border: 1px solid {border};
    min-height: 26px;
}}
QPushButton#presetChip:checked {{
    color: {button_ink};
    background: {accent};
    border-color: {accent};
}}
QComboBox, QLineEdit, QTextEdit, QPlainTextEdit {{
    background: {panel};
    color: {text};
    border-color: {border};
}}
QCheckBox::indicator:checked {{
    background: {accent};
    border-color: {accent};
}}
"""


def _dark_stylesheet() -> str:
    return f"""
QWidget {{
    background-color: {BG_BLACK};
    color: {FG_CREAM};
    font-family: "{BODY_FONT}";
    font-size: {FONT_BODY}px;
}}

QMainWindow, QDialog {{
    background-color: {BG_BLACK};
}}

/* ---------- Sidebar / panels ---------- */
#sideBar, #topBar, #statusBar {{
    background-color: {BG_BLACK};
    border: none;
}}

#panel {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_LG}px;
}}

/* ---------- Typography ---------- */
#displayText {{
    font-family: "{DISPLAY_FONT}";
    font-size: {FONT_DISPLAY}px;
    color: {FG_CREAM};
    background: transparent;
}}
#titleText {{
    font-family: "{DISPLAY_FONT}";
    font-size: {FONT_TITLE}px;
    color: {FG_CREAM};
    background: transparent;
}}
#headingText {{
    font-family: "{BODY_FONT}";
    font-size: {FONT_HEADING}px;
    color: {FG_CREAM};
    background: transparent;
}}
#mutedText, #captionText {{
    color: {FG_MUTED};
    font-size: {FONT_SMALL}px;
    background: transparent;
}}
#dimText {{
    color: {FG_DIM};
    font-size: {FONT_TINY}px;
    background: transparent;
}}

/* ---------- Buttons ---------- */
QPushButton, #actionButton {{
    background-color: {BG_PANEL};
    color: {FG_CREAM};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 3px 7px;
    min-height: 20px;
    font-family: "{BODY_FONT}";
    font-size: {FONT_BODY}px;
}}
QPushButton:hover {{
    background-color: {BG_RAISED};
    border-color: {FG_DIM};
}}
QPushButton:pressed {{
    background-color: {BG_RAISED};
}}
QPushButton:disabled {{
    color: {FG_DIM};
    border-color: {BORDER};
    background-color: {BG_BLACK};
}}
QPushButton#primaryButton, QPushButton#accentButton {{
    background-color: {ACCENT};
    color: {BG_BLACK};
    border: 1px solid {ACCENT};
}}
QPushButton#primaryButton:hover, QPushButton#accentButton:hover {{
    background-color: {SUCCESS};
    color: {BG_BLACK};
    opacity: 0.92;
}}
QPushButton#quietButton {{
    background-color: transparent;
    border: 1px solid transparent;
    color: {FG_MUTED};
}}
QPushButton#quietButton:hover {{
    color: {FG_CREAM};
    background-color: {BG_PANEL};
}}

/* ---------- Inputs ---------- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{
    background-color: {BG_PANEL};
    color: {FG_CREAM};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_MD}px;
    padding: {SPACE_2}px {SPACE_3}px;
    selection-background-color: {ACCENT};
    selection-color: {BG_BLACK};
    font-family: "{BODY_FONT}";
    font-size: {FONT_BODY}px;
    min-height: {CONTROL_HEIGHT_MD}px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QComboBox:focus {{
    border-color: {BORDER_FOCUS};
}}
QComboBox::drop-down {{
    border: none;
    width: {CONTROL_HEIGHT_MD}px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_PANEL};
    color: {FG_CREAM};
    border: 1px solid {BORDER};
    selection-background-color: {BG_RAISED};
    selection-color: {FG_CREAM};
    outline: 0;
}}

/* ---------- Sliders ---------- */
QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    border: none;
}}
QSlider::handle:horizontal:hover {{
    background: {FG_MUTED};
}}

/* ---------- Progress bar (mic level) ---------- */
QProgressBar {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    text-align: center;
    color: transparent;
    min-height: 6px;
    max-height: 6px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: {RADIUS_SM}px;
}}

/* ---------- Tabs ---------- */
QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar {{
    background: transparent;
    border: none;
}}
QTabBar::tab {{
    background: transparent;
    color: {FG_MUTED};
    padding: {SPACE_3}px {SPACE_4}px;
    border: none;
    font-family: "{BODY_FONT}";
    font-size: {FONT_BODY}px;
    min-height: {CONTROL_HEIGHT_MD}px;
}}
QTabBar::tab:hover {{
    color: {FG_CREAM};
}}
QTabBar::tab:selected {{
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
}}

/* ---------- Checkboxes ---------- */
QCheckBox {{
    background: transparent;
    color: {FG_CREAM};
    spacing: {SPACE_2}px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    background-color: {BG_PANEL};
}}
QCheckBox::indicator:hover {{
    border-color: {FG_MUTED};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    image: none;
}}

/* ---------- Status bar ---------- */
#statusBar {{
    border-top: 1px solid {BORDER};
    color: {FG_MUTED};
}}
#statusBar QLabel {{
    background: transparent;
    color: {FG_MUTED};
    padding: 0 {SPACE_3}px;
}}

/* ---------- Tooltips ---------- */
QToolTip {{
    background-color: {BG_PANEL};
    color: {FG_CREAM};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    padding: {SPACE_2}px {SPACE_3}px;
}}

/* ---------- Scrollbars ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {FG_DIM};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 5px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {FG_DIM};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    height: 0;
    background: transparent;
}}

/* ---------- System tray menu ---------- */
QMenu {{
    background-color: {BG_PANEL};
    color: {FG_CREAM};
    border: 1px solid {BORDER};
    padding: {SPACE_2}px;
}}
QMenu::item {{
    padding: {SPACE_2}px {SPACE_4}px;
    border-radius: {RADIUS_SM}px;
}}
QMenu::item:selected {{
    background-color: {BG_RAISED};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: {SPACE_2}px 0;
}}

/* ---------- Keycap ---------- */
#keyCap {{
    background-color: {BG_PANEL};
    color: {FG_CREAM};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 4px 10px;
    font-family: "{MONO_FONT}";
    font-size: {FONT_SMALL}px;
    min-width: 28px;
    qproperty-alignment: AlignCenter;
}}
#keyCap[held="true"] {{
    background-color: {ACCENT};
    color: {BG_BLACK};
    border-color: {ACCENT};
}}

/* ---------- Status dot ---------- */
#statusDot[state="ready"] {{ color: {SUCCESS}; }}
#statusDot[state="recording"] {{ color: {ACCENT}; }}
#statusDot[state="draining"] {{ color: {FG_MUTED}; }}
#statusDot[state="error"] {{ color: {ERROR}; }}
#statusDot[state="setup"] {{ color: {FG_MUTED}; }}
#statusDot[state="connecting"] {{ color: {FG_MUTED}; }}
"""


def _light_stylesheet() -> str:
    return f"""
QWidget {{
    background-color: #F3F0E8;
    color: #22231F;
    font-family: "{BODY_FONT}";
    font-size: {FONT_BODY}px;
}}
QMainWindow, QDialog {{
    background-color: #F3F0E8;
}}
#sideBar, #topBar, #statusBar {{
    background-color: #EAE6DC;
    border: none;
}}
#panel {{
    background-color: #FBF9F4;
    border: 1px solid #D4CFC3;
    border-radius: {RADIUS_LG}px;
}}
#displayText {{
    font-family: "{DISPLAY_FONT}";
    font-size: {FONT_DISPLAY}px;
    color: #22231F;
    background: transparent;
}}
#titleText {{
    font-family: "{DISPLAY_FONT}";
    font-size: {FONT_TITLE}px;
    color: #22231F;
    background: transparent;
}}
#headingText {{
    font-family: "{BODY_FONT}";
    font-size: {FONT_HEADING}px;
    color: #22231F;
    background: transparent;
}}
#mutedText, #captionText {{
    color: #6E7067;
    font-size: {FONT_SMALL}px;
    background: transparent;
}}
#dimText {{
    color: #85857D;
    font-size: {FONT_TINY}px;
    background: transparent;
}}
QPushButton, #actionButton {{
    background-color: #FBF9F4;
    color: #22231F;
    border: 1px solid #D4CFC3;
    border-radius: 4px;
    padding: 3px 7px;
    min-height: 20px;
    font-family: "{BODY_FONT}";
    font-size: {FONT_BODY}px;
}}
QPushButton:hover {{
    background-color: #E4E1D8;
    border-color: #B9B6AA;
}}
QPushButton:primary, QPushButton#accentButton, QPushButton#primaryButton {{
    background-color: #74836A;
    color: #F8F6F0;
    border: 1px solid #74836A;
}}
QPushButton#quietButton {{
    background-color: transparent;
    border: 1px solid transparent;
    color: #6E7067;
}}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{
    background-color: #FBF9F4;
    color: #22231F;
    border: 1px solid #D4CFC3;
    border-radius: {RADIUS_MD}px;
    padding: {SPACE_2}px {SPACE_3}px;
    selection-background-color: #74836A;
    selection-color: #F8F6F0;
    font-family: "{BODY_FONT}";
    font-size: {FONT_BODY}px;
    min-height: {CONTROL_HEIGHT_MD}px;
}}
QCheckBox::indicator {{
    background-color: #FBF9F4;
    border: 1px solid #D4CFC3;
}}
QCheckBox::indicator:checked {{
    background-color: #74836A;
    border-color: #74836A;
}}
QSlider::sub-page:horizontal {{ background: #74836A; }}
QSlider::handle:horizontal {{ background: #74836A; }}
QProgressBar::chunk {{ background-color: #74836A; }}
QTabBar::tab {{ color: #6E7067; }}
QTabBar::tab:selected {{ color: #74836A; border-bottom: 2px solid #74836A; }}
#statusBar {{ border-top: 1px solid #D4CFC3; color: #6E7067; }}
#keyCap {{
    background-color: #FBF9F4;
    color: #22231F;
    border: 1px solid #D4CFC3;
}}
#keyCap[held="true"] {{
    background-color: #74836A;
    color: #F8F6F0;
    border-color: #74836A;
}}
#statusDot[state="ready"] {{ color: #74836A; }}
#statusDot[state="recording"] {{ color: #74836A; }}
#statusDot[state="draining"] {{ color: #6E7067; }}
#statusDot[state="error"] {{ color: #9A584D; }}
#statusDot[state="setup"] {{ color: #6E7067; }}
#statusDot[state="connecting"] {{ color: #6E7067; }}
"""


__all__ = [
    "ACCENT",
    "BG_BLACK",
    "BG_PANEL",
    "BG_RAISED",
    "BORDER",
    "BORDER_FOCUS",
    "ERROR",
    "FG_CREAM",
    "FG_DIM",
    "FG_MUTED",
    "PRIMARY_BG",
    "PRIMARY_TEXT",
    "SUCCESS",
    "SUCCESS_GREEN",
    "WARNING",
    "resolved_dark",
    "stylesheet",
]
