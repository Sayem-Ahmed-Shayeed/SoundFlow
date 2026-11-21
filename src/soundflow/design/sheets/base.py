"""Application-wide rules: type, sidebar, buttons, inputs, scrollbars, chrome.

Uses ``${token}`` names from :mod:`soundflow.design.theme`.

Type scale (px): 12 meta, 13 secondary, 14 body, 16 emphasis, 20 section and
transcript, 26 live words, 32 page titles, 56 timer. Titles and big numbers
use Inter Display, the tighter cut of Inter drawn for large sizes.
"""

SHEET = """
/* ---------- Base ---------------------------------------------------- */
QWidget {
    font-family: "${body}";
    font-size: 14px;
    color: ${text};
    selection-background-color: ${selection};
    selection-color: ${text};
}
QMainWindow, QDialog, #appSurface, #contentSurface, QStackedWidget,
#dictationPage, #historyPage, #playgroundPage, #preferencesPage,
#historyListHolder, #historyScroll, #generalTab, #dictationTab, #playbackTab,
#shortcutsTab, #systemTab, #aiPolishTab, #modelTab, #systemScroll, #systemScrollViewport,
#systemContent, #generalScroll, #generalScrollViewport, #generalContent,
#dictationScroll, #dictationScrollViewport, #dictationContent,
#preferencesTabs, #settingsPage {
    background: ${canvas};
}
#appSurface {
    border: 1px solid ${border_strong};
    border-radius: 14px;
}
QLabel, QCheckBox, QRadioButton { background: transparent; }
QToolTip {
    background: ${surface_active};
    color: ${text};
    border: 1px solid ${border_strong};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 12px;
}

/* ---------- Type scale ---------------------------------------------- */
#displayText, #pageTitle, #dictationTitle {
    font-family: "${display}";
    font-size: 40px;
    font-weight: 400;
    color: ${text};
}
#tabTitle {
    font-family: "${display}";
    font-size: 25px;
    font-weight: 500;
    color: ${text};
}
#headingText, #sectionTitle, #dialogTitle {
    font-size: 16px;
    font-weight: 600;
    color: ${text};
}
#groupTitle { font-size: 13px; font-weight: 600; color: ${text2}; }
#mutedText, #formHint, #captionText { font-size: 13px; color: ${text2}; }
#dimText, #railCaption, #fieldLabel { font-size: 12px; color: ${text3}; }
#fieldLabel { font-size: 13px; font-weight: 600; color: ${text}; }
#errorText { font-size: 13px; color: ${danger}; }
#noteText { font-size: 13px; color: ${text2}; }
#noteText[tone="warning"] { color: ${warning}; }

/* ---------- Sidebar ------------------------------------------------- */
#sideBar {
    background: ${sidebar};
    border-top-left-radius: 14px;
    border-bottom-left-radius: 14px;
}
#brand { font-size: 15px; font-weight: 600; color: ${text}; }
QPushButton#sideNavButton {
    text-align: left;
    padding: 0 11px;
    min-height: 38px;
    max-height: 38px;
    border: 0;
    border-radius: 8px;
    background: transparent;
    color: ${text2};
    font-size: 14px;
    font-weight: 500;
}
QPushButton#sideNavButton:hover { background: ${surface_hover}; color: ${text}; }
QPushButton#sideNavButton[active="true"] {
    background: ${raised};
    color: ${text};
}
QPushButton#sideNavButton:focus { outline: none; border: 1px solid ${accent}; }
#sideAccount {
    border-top: 1px solid ${border};
}
#accountAvatar {
    background: ${raised};
    color: ${text};
    border-radius: 16px;
    font-size: 12px;
    font-weight: 700;
}
#accountName { font-size: 13px; font-weight: 600; color: ${text}; }
#accountMeta { font-size: 12px; color: ${text2}; }
#syncDot[state="ok"] { color: ${success}; }
#syncDot[state="busy"] { color: ${accent}; }
#syncDot[state="warn"] { color: ${warning}; }
#syncDot[state="error"] { color: ${danger}; }
QPushButton#iconButton {
    border: 0;
    border-radius: 8px;
    background: transparent;
    min-width: 32px; max-width: 32px;
    min-height: 32px; max-height: 32px;
    padding: 0;
}
QPushButton#iconButton:hover { background: ${surface_hover}; }
QPushButton#iconButton:pressed { background: ${surface_active}; }
QPushButton#iconButton:focus { outline: none; border: 1px solid ${accent}; }

/* ---------- Buttons ------------------------------------------------- */
QPushButton {
    background: ${surface};
    color: ${text};
    border: 1px solid ${border_strong};
    border-radius: 8px;
    padding: 0 14px;
    min-height: 34px; /* 36px with borders */
    font-size: 14px;
    font-weight: 500;
}
QPushButton:hover { background: ${surface_hover}; }
QPushButton:pressed { background: ${surface_active}; }
QPushButton:focus { outline: none; border-color: ${accent}; }
QPushButton:disabled { color: ${text3}; background: ${surface}; border-color: ${border}; }
QPushButton#primaryButton, QPushButton#accentButton, QPushButton#systemCheckButton {
    background: ${primary_bg};
    color: ${primary_text};
    border: 1px solid ${primary_bg};
    font-weight: 600;
}
QPushButton#primaryButton:hover, QPushButton#accentButton:hover,
QPushButton#systemCheckButton:hover {
    background: ${primary_hover};
    border-color: ${primary_hover};
}
QPushButton#primaryButton:focus, QPushButton#accentButton:focus,
QPushButton#systemCheckButton:focus { border: 2px solid ${text}; }
QPushButton#primaryButton:disabled, QPushButton#accentButton:disabled {
    background: ${surface_active};
    color: ${text3};
    border-color: ${surface_active};
}
QPushButton#quietButton, QPushButton#actionButton, QPushButton#systemSecondaryButton,
QPushButton#compactBrowseButton {
    background: ${surface};
    color: ${text};
    border: 1px solid ${border_strong};
}
QPushButton#quietButton:hover, QPushButton#actionButton:hover,
QPushButton#systemSecondaryButton:hover, QPushButton#compactBrowseButton:hover {
    background: ${surface_hover};
}
QPushButton#ghostButton {
    background: transparent;
    border: 1px solid transparent;
    color: ${text2};
}
QPushButton#ghostButton:hover { background: ${surface_hover}; color: ${text}; }
QPushButton#ghostButton:focus { border-color: ${accent}; }
QPushButton#textActionButton, QPushButton#linkButton {
    background: transparent;
    border: 0;
    padding: 0 2px;
    min-height: 24px;
    color: ${accent_text};
    font-weight: 600;
    text-align: left;
}
QPushButton#textActionButton:hover, QPushButton#linkButton:hover { color: ${text}; }
QPushButton#textActionButton:focus, QPushButton#linkButton:focus { text-decoration: underline; }
QPushButton#destructiveButton {
    background: ${danger};
    color: #FFFFFF;
    border: 1px solid ${danger};
    font-weight: 600;
}
QPushButton#destructiveButton:hover { border-color: ${text}; }
QPushButton#deleteDialogCancel { background: ${surface}; }

/* Segmented controls: a raised track; the chosen option is a lifted tab */
QFrame#segmentedControl {
    background: ${raised};
    border: 0;
    border-radius: 9px;
}
QFrame#segmentedControl QPushButton {
    background: transparent;
    color: ${text2};
    border: 1px solid transparent;
    border-radius: 7px;
    min-height: 28px;
    max-height: 28px;
    padding: 0 13px;
    font-size: 13px;
    font-weight: 500;
}
QFrame#segmentedControl QPushButton:hover { color: ${text}; }
QFrame#segmentedControl QPushButton:checked {
    background: ${surface};
    color: ${text};
    border-color: ${border_strong};
}
QFrame#segmentedControl QPushButton:focus { border-color: ${accent}; }
QPushButton#presetChip {
    background: ${surface};
    color: ${text2};
    border: 1px solid ${border_strong};
    border-radius: 8px;
    min-height: 30px;
    max-height: 30px;
    padding: 0 14px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#presetChip:hover { color: ${text}; }
QPushButton#presetChip:checked {
    background: ${accent_soft};
    color: ${accent_text};
    border-color: ${accent};
}

/* Keycaps for shortcuts */
#keyCap, #shortcutSummaryCap, #overlayKeycap {
    font-family: "${body}";
    font-size: 12px;
    font-weight: 600;
    color: ${text};
    background: ${raised};
    border: 1px solid ${border_strong};
    border-bottom-width: 2px;
    border-radius: 6px;
    padding: 2px 7px;
}
#keyCap[size="large"] {
    font-size: 14px;
    padding: 6px 12px;
    border-radius: 8px;
}
#keyCap[listening="true"] { border-color: ${accent}; }

/* ---------- Inputs -------------------------------------------------- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background: ${field};
    color: ${text};
    border: 1px solid ${border_strong};
    border-radius: 8px;
    padding: 0 12px;
    min-height: 34px; /* 36px with borders */
    font-size: 14px;
}
QTextEdit, QPlainTextEdit { padding: 10px 12px; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: ${accent};
}
QLineEdit:read-only { color: ${text2}; background: ${surface}; }
QLineEdit#systemDataPath, QLineEdit#compactPathField, QLineEdit#systemModelPath {
    font-size: 13px;
    color: ${text2};
    background: ${surface};
}
#historySearch {
    min-height: 36px;
    padding-left: 12px;
}
QComboBox { padding-right: 32px; }
QComboBox::drop-down,
QComboBox#compactShortcutField::drop-down, QComboBox#compactPreferenceField::drop-down,
QComboBox#languagePicker::drop-down, QComboBox#historyFilter::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 30px;
    border: 0;
}
QComboBox::down-arrow,
QComboBox#compactShortcutField::down-arrow, QComboBox#compactPreferenceField::down-arrow,
QComboBox#languagePicker::down-arrow, QComboBox#historyFilter::down-arrow {
    image: url("${chevron}");
    width: 10px;
    height: 6px;
}
QComboBox QAbstractItemView,
QComboBox#compactShortcutField QAbstractItemView,
QComboBox#compactPreferenceField QAbstractItemView,
QComboBox#languagePicker QAbstractItemView, QComboBox#historyFilter QAbstractItemView {
    background: ${surface};
    color: ${text};
    border: 1px solid ${border_strong};
    border-radius: 10px;
    padding: 5px;
    outline: 0;
    selection-background-color: ${surface_hover};
    selection-color: ${text};
}
QMenu {
    background: ${surface};
    border: 1px solid ${border_strong};
    border-radius: 10px;
    padding: 5px;
}
QMenu::item { padding: 8px 12px; border-radius: 7px; color: ${text}; }
QMenu::item:selected { background: ${surface_hover}; }
QMenu::item:disabled { color: ${text3}; }
QMenu::separator { height: 1px; background: ${border}; margin: 4px 6px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid ${border_strong};
    border-radius: 4px;
    background: ${field};
}
QCheckBox::indicator:checked { background: ${accent}; border-color: ${accent}; }
QRadioButton { spacing: 12px; font-weight: 500; }
QRadioButton::indicator {
    width: 14px; height: 14px;
    border: 2px solid ${border_strong};
    border-radius: 9px;
    background: transparent;
}
QRadioButton::indicator:checked {
    border: 5px solid ${accent};
    width: 8px; height: 8px;
}

/* ---------- Slider -------------------------------------------------- */
QSlider::groove:horizontal { height: 4px; border-radius: 2px; background: ${surface_active}; }
QSlider::sub-page:horizontal { height: 4px; border-radius: 2px; background: ${accent}; }
QSlider::add-page:horizontal { height: 4px; border-radius: 2px; background: ${surface_active}; }
QSlider::handle:horizontal {
    width: 16px; height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: ${text};
    border: 0;
}

/* ---------- Scrollbars ---------------------------------------------- */
QScrollArea { background: transparent; border: 0; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: ${scroll}; border-radius: 3px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: ${text3}; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    border: 0;
    background: transparent;
}
QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
    width: 0;
    height: 0;
    background: transparent;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { height: 0; }

/* ---------- Window chrome ------------------------------------------- */
#windowChrome { background: transparent; }
QPushButton[objectName^="windowChrome"], #windowChrome QPushButton {
    background: transparent;
    border: 0;
    border-radius: 7px;
    min-width: 32px; max-width: 32px;
    min-height: 28px; max-height: 28px;
    padding: 0;
    color: ${text3};
}
QPushButton[objectName^="windowChrome"]:hover, #windowChrome QPushButton:hover {
    background: ${surface_hover};
    color: ${text};
}
QPushButton[objectName="windowChrome:close"]:hover { background: ${danger}; color: #FFFFFF; }

/* ---------- Toast and status bar ------------------------------------ */
#toast {
    background: ${text};
    color: ${canvas};
    border-radius: 10px;
    padding: 10px 16px;
    font-weight: 600;
}
#statusBar { background: ${sidebar}; border-top: 1px solid ${border}; }
#statusBarLabel { font-size: 12px; color: ${text2}; }
#statusBarAccent { font-size: 12px; color: ${accent_text}; }
#statusDot { font-size: 10px; color: ${success}; }
"""
