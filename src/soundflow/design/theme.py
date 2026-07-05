"""Theme tokens and stylesheet generator.

The design is intentionally monochrome:

* Dark mode  — deepest black background with **cream-white** text (NOT pure
  white, NOT blue/purple).
* Light mode — cream-white background with deepest black text.

There is exactly one neutral accent (cream) for active/selected states.
A subtle, desaturated green (``SUCCESS``) and terracotta (``ERROR``) are
reserved for status indicators — they are not used for buttons.
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
# Cream whites
FG_CREAM = "#F2EBDD"       # primary foreground (cream white)
FG_MUTED = "#A8A296"       # muted hints / labels
FG_DIM = "#6B6760"         # dimmer grey for inactive

# Deepest blacks
BG_BLACK = "#0A0A0A"       # window background
BG_PANEL = "#121110"       # card surface
BG_RAISED = "#1B1917"      # raised / hover / active

# Borders
BORDER = "#2A2724"         # standard hairline
BORDER_FOCUS = FG_CREAM    # focus ring matches foreground

# Status
SUCCESS = "#A8B5A0"        # desaturated cream-green for ready dot
ERROR = "#C97A6E"          # desaturated terracotta — not red

# Single neutral accent (the only accent in the design)
ACCENT = FG_CREAM

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
    bg = "#080D17" if dark else "#F5F6FB"
    sidebar = "#0D1422" if dark else "#ECEEF7"
    panel = "#111827" if dark else "#FFFFFF"
    raised = "#171F30" if dark else "#F0F1F7"
    text = "#F7F8FC" if dark else "#151826"
    muted = "#98A1B3" if dark else "#626B7B"
    border = "#263044" if dark else "#D7DAE5"
    accent = "#8B5CF6"
    active = "#241D45" if dark else "#EAE4FF"
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
    color: #C4A7FF;
    background: {active};
    border-left: 3px solid {accent};
}}
#privacyCard {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 8px;
}}
#privacyPill {{ color: #6EE7A8; font-weight: 600; }}
#privacyPill {{ font-size: 10px; }}
#railCaption {{ color: {muted}; font-size: 9px; }}
#dictationPage, #historyPage, #playgroundPage, #preferencesPage,
#historyListHolder, #historyScroll, #generalTab, #dictationTab,
#playbackTab, #shortcutsTab, #systemTab {{
    background: {bg};
}}
#displayText {{ color: {text}; }}
#headingText {{ color: {text}; }}
#mutedText, #captionText {{ color: {muted}; }}
#dimText {{ color: #737D90; }}
#historyCard, #preferencesCard,
QPushButton#quickActionCard {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 8px;
}}
#historyCard:hover, QPushButton#quickActionCard:hover {{
    background: {raised};
    border-color: #39455D;
}}
#historyBody {{
    color: {text};
    font-size: 13px;
    line-height: 1.45;
}}
#historyGroup {{
    color: #A78BFA;
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
#historyFeedback[state="error"] {{ color: #FB7185; }}
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
#systemStatusPill {{
    color: {muted};
    background: {raised};
    border: 1px solid {border};
    border-radius: 11px;
    padding: 4px 10px;
}}
#systemStatusPill[state="ready"],
QLabel[objectName^="systemStatus"][state="ready"] {{
    color: #6EE7A8;
}}
#systemStatusPill[state="warning"],
QLabel[objectName^="systemStatus"][state="warning"] {{
    color: #F2C879;
}}
#systemStatusPill[state="error"],
QLabel[objectName^="systemStatus"][state="error"] {{
    color: #FB7185;
}}
QPushButton#systemCheckButton {{
    color: #0B1020;
    background: {accent};
    border: 1px solid {accent};
    border-radius: 7px;
    padding: 7px 14px;
}}
QPushButton#systemCheckButton:hover {{
    background: #A78BFA;
    border-color: #A78BFA;
}}
QPushButton#systemSecondaryButton {{
    color: {text};
    background: {raised};
    border: 1px solid {border};
    border-radius: 7px;
    padding: 7px 14px;
}}
QPushButton#systemSecondaryButton:hover {{
    border-color: {accent};
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
    color: #B99AFF;
    border-bottom-color: {accent};
}}
#statusBar {{
    background: {sidebar};
    border-top: 1px solid {border};
    border-bottom-left-radius: 14px;
    border-bottom-right-radius: 14px;
}}
#statusBarLabel {{ color: {muted}; font-size: 10px; }}
#statusDot[state="ready"] {{ color: #4ADE80; }}
#statusDot[state="recording"] {{ color: {accent}; }}
#statusDot[state="error"] {{ color: #FB7185; }}
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
    min-height: 20px;
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
    color: white;
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
    border-radius: {RADIUS_MD}px;
    padding: {SPACE_2}px {SPACE_4}px;
    min-height: {CONTROL_HEIGHT_MD}px;
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
    background-color: {FG_CREAM};
    color: {BG_BLACK};
    border: 1px solid {FG_CREAM};
}}
QPushButton#primaryButton:hover, QPushButton#accentButton:hover {{
    background-color: {FG_CREAM};
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
    selection-background-color: {FG_CREAM};
    selection-color: {BG_BLACK};
    font-family: "{BODY_FONT}";
    font-size: {FONT_BODY}px;
    min-height: {CONTROL_HEIGHT_MD}px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QComboBox:focus {{
    border-color: {FG_CREAM};
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
    background: {FG_CREAM};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {FG_CREAM};
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
    background-color: {FG_CREAM};
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
    color: {FG_CREAM};
    border-bottom: 2px solid {FG_CREAM};
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
    background-color: {FG_CREAM};
    border-color: {FG_CREAM};
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
    background-color: {FG_CREAM};
    color: {BG_BLACK};
    border-color: {FG_CREAM};
}}

/* ---------- Status dot ---------- */
#statusDot[state="ready"] {{ color: {SUCCESS}; }}
#statusDot[state="recording"] {{ color: {FG_CREAM}; }}
#statusDot[state="draining"] {{ color: {FG_MUTED}; }}
#statusDot[state="error"] {{ color: {ERROR}; }}
#statusDot[state="setup"] {{ color: {FG_MUTED}; }}
#statusDot[state="connecting"] {{ color: {FG_MUTED}; }}
"""


def _light_stylesheet() -> str:
    return f"""
QWidget {{
    background-color: {FG_CREAM};
    color: {BG_BLACK};
    font-family: "{BODY_FONT}";
    font-size: {FONT_BODY}px;
}}
QMainWindow, QDialog {{
    background-color: {FG_CREAM};
}}
#sideBar, #topBar, #statusBar {{
    background-color: {FG_CREAM};
    border: none;
}}
#panel {{
    background-color: #FFFFFF;
    border: 1px solid #E6DFD1;
    border-radius: {RADIUS_LG}px;
}}
#displayText {{
    font-family: "{DISPLAY_FONT}";
    font-size: {FONT_DISPLAY}px;
    color: {BG_BLACK};
    background: transparent;
}}
#titleText {{
    font-family: "{DISPLAY_FONT}";
    font-size: {FONT_TITLE}px;
    color: {BG_BLACK};
    background: transparent;
}}
#headingText {{
    font-family: "{BODY_FONT}";
    font-size: {FONT_HEADING}px;
    color: {BG_BLACK};
    background: transparent;
}}
#mutedText, #captionText {{
    color: #6E665B;
    font-size: {FONT_SMALL}px;
    background: transparent;
}}
#dimText {{
    color: #8A8275;
    font-size: {FONT_TINY}px;
    background: transparent;
}}
QPushButton, #actionButton {{
    background-color: #FFFFFF;
    color: {BG_BLACK};
    border: 1px solid #D8D0C0;
    border-radius: {RADIUS_MD}px;
    padding: {SPACE_2}px {SPACE_4}px;
    min-height: {CONTROL_HEIGHT_MD}px;
    font-family: "{BODY_FONT}";
    font-size: {FONT_BODY}px;
}}
QPushButton:hover {{
    background-color: #F2EBDD;
    border-color: #B8AE9C;
}}
QPushButton:primary, QPushButton#accentButton, QPushButton#primaryButton {{
    background-color: {BG_BLACK};
    color: {FG_CREAM};
    border: 1px solid {BG_BLACK};
}}
QPushButton#quietButton {{
    background-color: transparent;
    border: 1px solid transparent;
    color: #6E665B;
}}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{
    background-color: #FFFFFF;
    color: {BG_BLACK};
    border: 1px solid #D8D0C0;
    border-radius: {RADIUS_MD}px;
    padding: {SPACE_2}px {SPACE_3}px;
    selection-background-color: {BG_BLACK};
    selection-color: {FG_CREAM};
    font-family: "{BODY_FONT}";
    font-size: {FONT_BODY}px;
    min-height: {CONTROL_HEIGHT_MD}px;
}}
QCheckBox::indicator {{
    background-color: #FFFFFF;
    border: 1px solid #D8D0C0;
}}
QCheckBox::indicator:checked {{
    background-color: {BG_BLACK};
    border-color: {BG_BLACK};
}}
QSlider::sub-page:horizontal {{ background: {BG_BLACK}; }}
QSlider::handle:horizontal {{ background: {BG_BLACK}; }}
QProgressBar::chunk {{ background-color: {BG_BLACK}; }}
QTabBar::tab {{ color: #6E665B; }}
QTabBar::tab:selected {{ color: {BG_BLACK}; border-bottom: 2px solid {BG_BLACK}; }}
#statusBar {{ border-top: 1px solid #D8D0C0; color: #6E665B; }}
#keyCap {{
    background-color: #FFFFFF;
    color: {BG_BLACK};
    border: 1px solid #D8D0C0;
}}
#keyCap[held="true"] {{
    background-color: {BG_BLACK};
    color: {FG_CREAM};
    border-color: {BG_BLACK};
}}
#statusDot[state="ready"] {{ color: #4F5E47; }}
#statusDot[state="recording"] {{ color: {BG_BLACK}; }}
#statusDot[state="draining"] {{ color: #6E665B; }}
#statusDot[state="error"] {{ color: #8E4A3E; }}
#statusDot[state="setup"] {{ color: #6E665B; }}
#statusDot[state="connecting"] {{ color: #6E665B; }}
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
    "resolved_dark",
    "stylesheet",
]
