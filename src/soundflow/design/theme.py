"""Professional layered theme tokens and stylesheet generator.

True-black surfaces, neutral typography, and a focused violet accent give
the app a crisp desktop-tool character without sacrificing readability.
"""

from __future__ import annotations

from pathlib import Path

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
# Dark theme: true-black canvas with subtly lifted neutral surfaces.
FG_CREAM = "#F4F7FF"
FG_MUTED = "#A9A9B2"
FG_DIM = "#777781"
BG_BLACK = "#000000"
BG_PANEL = "#0A0A0C"
BG_RAISED = "#151519"
BORDER = "#29292F"

# Shared semantic colors.
ACCENT = "#9B72FF"
BORDER_FOCUS = ACCENT
SUCCESS = "#55D68B"
WARNING = "#E9B96E"
ERROR = "#F0787F"

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
    bg = BG_BLACK if dark else "#F5F7FB"
    sidebar = "#050506" if dark else "#EDF1F7"
    panel = BG_PANEL if dark else "#FFFFFF"
    raised = BG_RAISED if dark else "#E8ECF4"
    text = FG_CREAM if dark else "#172033"
    muted = FG_MUTED if dark else "#647089"
    border = BORDER if dark else "#D7DEEA"
    accent = ACCENT if dark else "#7657F6"
    active = "#211B3D" if dark else "#E9E4FF"
    dim = FG_DIM if dark else "#8791A6"
    hover_border = "#45454D" if dark else "#BAC4D5"
    error = ERROR if dark else "#C4515B"
    warning = WARNING if dark else "#A8762F"
    button_ink = "#0A0F1A" if dark else "#FFFFFF"
    chevron = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "icons"
        / "chevron-down.svg"
    ).as_posix()
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
    border-radius: 16px;
}}
#sideBar {{
    background: {sidebar};
    border-right: 1px solid {border};
    border-top-left-radius: 16px;
    border-bottom-left-radius: 16px;
}}
#brandMark {{
    color: {accent};
    font-size: 25px;
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
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 10px 12px;
    text-align: left;
    min-height: 24px;
}}
QPushButton#sideNavButton:hover {{
    color: {text};
    background: {raised};
    border-color: {border};
}}
QPushButton#sideNavButton[active="true"] {{
    color: {text};
    background: {active};
    border: 1px solid {accent};
}}
#railSection {{ color: {dim}; font-size: 9px; font-weight: 700; }}
#privacyCard {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 10px;
}}
#privacyPill {{ color: {SUCCESS}; font-weight: 600; }}
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
#dictationHero {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 16px;
}}
#dictationStateBadge {{
    color: {SUCCESS};
    background: {raised};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 4px 11px;
    font-size: 10px;
    font-weight: 700;
}}
#dictationStateBadge[state="recording"] {{ color: {accent}; border-color: {accent}; }}
#dictationStateBadge[state="draining"] {{ color: {warning}; border-color: {warning}; }}
#historyCard, #preferencesCard, #localDataCard,
QPushButton#quickActionCard {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 12px;
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
#resultCount {{
    color: {muted};
    background: {raised};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 3px 9px;
    font-size: 10px;
    min-height: 18px;
    max-height: 18px;
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
QDialog#deleteTranscriptDialog {{
    background: transparent;
}}
QFrame#deleteDialogSurface {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 14px;
}}
QLabel#deleteDialogTitle {{
    color: {text};
    font-size: 16px;
    font-weight: 700;
}}
QLabel#deleteDialogCopy {{
    color: {text};
    font-size: 12px;
}}
QLabel#deleteDialogWarning {{
    color: {muted};
    font-size: 11px;
}}
QPushButton#deleteDialogCancel,
QPushButton#destructiveButton {{
    border-radius: 7px;
    padding: 4px 14px;
    min-height: 24px;
    max-height: 24px;
}}
QPushButton#deleteDialogCancel {{
    color: {text};
    background: {raised};
    border: 1px solid {border};
}}
QPushButton#deleteDialogCancel:hover,
QPushButton#deleteDialogCancel:focus {{
    background: {panel};
    border-color: {accent};
}}
QPushButton#destructiveButton {{
    color: #FFFFFF;
    background: {error};
    border: 1px solid {error};
}}
QPushButton#destructiveButton:hover {{
    background: #A93F49;
    border-color: #A93F49;
}}
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
    min-height: 20px;
    max-height: 20px;
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
#modelManagerCard {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 12px;
}}
QWidget[objectName^="modelRow:"] {{
    background: {raised};
    border: 1px solid {border};
    border-radius: 7px;
}}
QLabel[objectName^="modelName:"] {{
    color: {text};
    font-weight: 600;
}}
QLabel[objectName^="modelGuidance:"],
QLabel[objectName^="modelPhase:"] {{
    color: {muted};
    font-size: 10px;
}}
QLabel[objectName^="modelStatus:"] {{
    color: {muted};
    font-size: 10px;
    font-weight: 600;
}}
QLabel[objectName^="modelRecommended:"] {{
    color: {accent};
    background: {active};
    border: 1px solid {accent};
    border-radius: 7px;
    padding: 1px 6px;
    font-size: 9px;
    font-weight: 700;
}}
QLabel[objectName^="modelError:"] {{
    color: {error};
    font-size: 10px;
}}
QPushButton[objectName^="modelAction:"],
QPushButton[objectName^="modelDelete:"] {{
    border-radius: 4px;
    padding: 3px 9px;
    min-height: 20px;
    max-height: 20px;
}}
QPushButton[objectName^="modelAction:"] {{
    color: {button_ink};
    background: {accent};
    border: 1px solid {accent};
}}
QPushButton[objectName^="modelAction:"]:hover,
QPushButton[objectName^="modelAction:"]:focus {{
    background: {panel};
    color: {accent};
    border-color: {accent};
}}
QPushButton[objectName^="modelAction:"]:disabled {{
    color: {dim};
    background: {panel};
    border-color: {border};
}}
QPushButton[objectName^="modelDelete:"] {{
    color: {error};
    background: transparent;
    border: 1px solid {error};
}}
QPushButton[objectName^="modelDelete:"]:hover,
QPushButton[objectName^="modelDelete:"]:focus {{
    color: #FFFFFF;
    background: {error};
    border-color: {error};
}}
QProgressBar[objectName^="modelProgress:"] {{
    background: {border};
    border: 0;
    border-radius: 2px;
    min-height: 4px;
    max-height: 4px;
    color: transparent;
    text-align: center;
}}
QProgressBar[objectName^="modelProgress:"]::chunk {{
    background: {accent};
    border-radius: 2px;
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
    color: {text};
    background: {panel};
    border: 1px solid {border};
    padding: 3px 30px 3px 9px;
    min-height: 20px;
    max-height: 20px;
    border-radius: 7px;
}}
QComboBox#compactShortcutField:hover,
QComboBox#compactPreferenceField:hover {{
    border-color: {hover_border};
}}
QComboBox#compactShortcutField:focus,
QComboBox#compactPreferenceField:focus {{
    border-color: {accent};
}}
QComboBox#compactShortcutField::drop-down,
QComboBox#compactPreferenceField::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border: 0;
    background: transparent;
}}
QComboBox#compactShortcutField::down-arrow,
QComboBox#compactPreferenceField::down-arrow {{
    image: url("{chevron}");
    width: 9px;
    height: 6px;
}}
QComboBox#compactShortcutField QAbstractItemView,
QComboBox#compactPreferenceField QAbstractItemView {{
    background: {panel};
    color: {text};
    border: 1px solid {border};
    border-radius: 7px;
    padding: 5px;
    selection-background-color: {raised};
    selection-color: {text};
    outline: 0;
}}
QPushButton#compactBrowseButton {{
    color: {text};
    background: {raised};
    border: 1px solid {border};
    border-radius: 7px;
    padding: 3px 12px;
    min-height: 20px;
    max-height: 20px;
}}
QPushButton#compactBrowseButton:hover {{
    border-color: {accent};
    background: {panel};
}}
QPushButton#textActionButton {{
    color: {accent};
    background: transparent;
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 4px 9px;
    min-height: 22px;
}}
QPushButton#textActionButton:hover,
QPushButton#textActionButton:focus {{
    color: {text};
    background: {raised};
    border-color: {border};
}}
QFrame#segmentedControl {{
    background: {raised};
    border: 1px solid {border};
    border-radius: 9px;
}}
QFrame#segmentedControl QPushButton {{
    color: {muted};
    background: transparent;
    border: 0;
    border-radius: 7px;
    padding: 2px 18px;
    min-height: 22px;
    max-height: 22px;
}}
QFrame#segmentedControl QPushButton:hover {{
    color: {text};
    background: {panel};
}}
QFrame#segmentedControl QPushButton:checked {{
    color: {button_ink};
    background: {accent};
}}
#recordingOverlay {{
    background: transparent;
}}
QFrame#overlayPanel {{
    background: #101012;
    border: 1px solid #34343A;
    border-radius: 16px;
}}
QLabel#overlayTitle {{
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 700;
}}
QLabel#overlayHint {{
    color: #9A9AA3;
    font-size: 9px;
}}
QLabel#overlayKeycap {{
    color: #D9D9E0;
    background: #1C1C20;
    border: 1px solid #38383F;
    border-radius: 6px;
    padding: 3px 6px;
    font-family: "{MONO_FONT}";
    font-size: 8px;
    font-weight: 700;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {border};
    border: 0;
    border-radius: 2px;
}}
QSlider::add-page:horizontal {{
    background: {border};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {accent};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px;
    height: 14px;
    margin: -5px 0;
    background: {accent};
    border: 0;
    border-radius: 7px;
}}
#historySearch, #playgroundCommand {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 10px;
    color: {text};
}}
#preferencesTabs::pane {{ border: 0; background: transparent; }}
#preferencesTabs QTabBar::tab {{
    color: {muted};
    background: transparent;
    border: 0;
    border-bottom: 2px solid transparent;
    padding: 10px 14px;
}}
#preferencesTabs QTabBar::tab:selected {{
    color: {accent};
    border-bottom-color: {accent};
}}
#statusBar {{
    background: {sidebar};
    border-top: 1px solid {border};
    border-bottom-left-radius: 16px;
    border-bottom-right-radius: 16px;
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
QPushButton[objectName^="windowChrome"]:hover {{
    color: {text};
    background: {raised};
    border-radius: 7px;
}}
QPushButton[objectName="windowChrome:close"]:hover {{
    color: #FFFFFF;
    background: {error};
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
    min-height: 20px;
    max-height: 20px;
    border-radius: 7px;
    padding: 2px 14px;
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
    border-radius: 8px;
    padding: 6px 12px;
    min-height: 28px;
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
    background-color: #F5F7FB;
    color: #172033;
    font-family: "{BODY_FONT}";
    font-size: {FONT_BODY}px;
}}
QMainWindow, QDialog {{
    background-color: #F5F7FB;
}}
#sideBar, #topBar, #statusBar {{
    background-color: #EDF1F7;
    border: none;
}}
#panel {{
    background-color: #FFFFFF;
    border: 1px solid #D7DEEA;
    border-radius: {RADIUS_LG}px;
}}
#displayText {{
    font-family: "{DISPLAY_FONT}";
    font-size: {FONT_DISPLAY}px;
    color: #172033;
    background: transparent;
}}
#titleText {{
    font-family: "{DISPLAY_FONT}";
    font-size: {FONT_TITLE}px;
    color: #172033;
    background: transparent;
}}
#headingText {{
    font-family: "{BODY_FONT}";
    font-size: {FONT_HEADING}px;
    color: #172033;
    background: transparent;
}}
#mutedText, #captionText {{
    color: #647089;
    font-size: {FONT_SMALL}px;
    background: transparent;
}}
#dimText {{
    color: #8791A6;
    font-size: {FONT_TINY}px;
    background: transparent;
}}
QPushButton, #actionButton {{
    background-color: #FFFFFF;
    color: #172033;
    border: 1px solid #D7DEEA;
    border-radius: 8px;
    padding: 6px 12px;
    min-height: 28px;
    font-family: "{BODY_FONT}";
    font-size: {FONT_BODY}px;
}}
QPushButton:hover {{
    background-color: #E8ECF4;
    border-color: #BAC4D5;
}}
QPushButton:primary, QPushButton#accentButton, QPushButton#primaryButton {{
    background-color: #7657F6;
    color: #FFFFFF;
    border: 1px solid #7657F6;
}}
QPushButton#quietButton {{
    background-color: transparent;
    border: 1px solid transparent;
    color: #647089;
}}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{
    background-color: #FFFFFF;
    color: #172033;
    border: 1px solid #D7DEEA;
    border-radius: {RADIUS_MD}px;
    padding: {SPACE_2}px {SPACE_3}px;
    selection-background-color: #7657F6;
    selection-color: #FFFFFF;
    font-family: "{BODY_FONT}";
    font-size: {FONT_BODY}px;
    min-height: {CONTROL_HEIGHT_MD}px;
}}
QCheckBox::indicator {{
    background-color: #FFFFFF;
    border: 1px solid #D7DEEA;
}}
QCheckBox::indicator:checked {{
    background-color: #7657F6;
    border-color: #7657F6;
}}
QSlider::sub-page:horizontal {{ background: #7657F6; }}
QSlider::handle:horizontal {{ background: #7657F6; }}
QProgressBar::chunk {{ background-color: #7657F6; }}
QTabBar::tab {{ color: #647089; }}
QTabBar::tab:selected {{ color: #7657F6; border-bottom: 2px solid #7657F6; }}
#statusBar {{ border-top: 1px solid #D7DEEA; color: #647089; }}
#keyCap {{
    background-color: #FFFFFF;
    color: #172033;
    border: 1px solid #D7DEEA;
}}
#keyCap[held="true"] {{
    background-color: #7657F6;
    color: #FFFFFF;
    border-color: #7657F6;
}}
#statusDot[state="ready"] {{ color: #31B86B; }}
#statusDot[state="recording"] {{ color: #7657F6; }}
#statusDot[state="draining"] {{ color: #647089; }}
#statusDot[state="error"] {{ color: #C4515B; }}
#statusDot[state="setup"] {{ color: #647089; }}
#statusDot[state="connecting"] {{ color: #647089; }}
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
