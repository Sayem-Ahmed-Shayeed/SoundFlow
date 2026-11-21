"""Preferences page and the model manager.

Uses ``${token}`` names from :mod:`soundflow.design.theme`.
"""

SHEET = """
/* ---------- Preferences --------------------------------------------- */
#prefsNavButton {
    text-align: left;
    padding: 0 12px;
    min-height: 32px;
    max-height: 32px;
    border: 0;
    border-radius: 8px;
    background: transparent;
    color: ${text2};
    font-size: 14px;
}
#prefsNavButton:hover { background: ${surface_hover}; color: ${text}; }
#prefsNavButton[active="true"] { background: ${surface_active}; color: ${text}; font-weight: 500; }
#preferencesCard, #localDataCard, #settingsCard {
    background: ${surface};
    border: 1px solid ${border};
    border-radius: 12px;
}
#modelManagerCard, #prefsGroup, #prefsSlot, #prefsRow, #prefsChoice {
    background: transparent;
    border: 0;
}
#prefsRow, #prefsChoice { padding: 0; }
#prefsChoice:hover { background: ${surface_hover}; border-radius: 12px; }
#prefsDivider {
    background: ${border};
    border: 0;
    min-height: 1px;
    max-height: 1px;
}
#prefsRowTitle, #toggleRowTitle, #systemRowTitle {
    font-size: 14px;
    font-weight: 500;
    color: ${text};
}
#prefsNav QLabel#pageTitle { margin: 0 0 0 8px; }
QScrollArea[objectName$$="Scroll"] { background: transparent; border: 0; }
QWidget[objectName$$="Content"] { background: transparent; }
#aiKeyResult { font-size: 13px; color: ${text2}; }
#aiKeyResult[tone="ok"] { color: ${success}; }
#aiKeyResult[tone="error"] { color: ${danger}; }
#disclosureButton {
    background: transparent;
    border: 0;
    border-radius: 7px;
    padding: 4px 8px 4px 4px;
    color: ${text2};
    font-size: 13px;
    font-weight: 500;
}
#disclosureButton:hover { background: ${surface_hover}; color: ${text}; }
QProgressBar#micLevel {
    background: ${raised};
    border: 0;
    border-radius: 3px;
}
QProgressBar#micLevel::chunk { background: ${success}; border-radius: 3px; }
#systemStatusPill, QLabel[objectName^="systemStatus"] { min-height: 22px; }
#systemPathBlock QLabel[role="path"] { font-family: "${mono}"; font-size: 12px; color: ${text2}; }
#systemLastChecked { font-size: 12px; color: ${text3}; }
#systemStatusPill, QLabel[objectName^="systemStatus"] {
    font-size: 12px;
    font-weight: 500;
    color: ${text2};
    background: ${surface_hover};
    border: 0;
    border-radius: 10px;
    padding: 3px 10px;
}
#systemStatusPill[state="ready"], QLabel[objectName^="systemStatus"][state="ready"] {
    color: ${success};
    background: ${success_soft};
}
#systemStatusPill[state="warning"], QLabel[objectName^="systemStatus"][state="warning"] {
    color: ${warning};
    background: ${warning_soft};
}
#systemStatusPill[state="error"], QLabel[objectName^="systemStatus"][state="error"] {
    color: ${danger};
    background: ${danger_soft};
}

/* Model manager */
QWidget[objectName^="modelRow:"] {
    background: transparent;
    border-bottom: 1px solid ${border};
}
QLabel[objectName^="modelName:"] { font-size: 14px; font-weight: 600; color: ${text}; }
QLabel[objectName^="modelGuidance:"], QLabel[objectName^="modelPhase:"] {
    font-size: 12px;
    color: ${text2};
}
QLabel[objectName^="modelStatus:"] {
    font-size: 12px;
    font-weight: 600;
    color: ${accent_text};
    background: ${accent_soft};
    border-radius: 8px;
    padding: 3px 10px;
}
QLabel[objectName^="modelSize:"] { font-size: 13px; color: ${text2}; }
QLabel[objectName^="modelRecommended:"] {
    font-size: 11px;
    font-weight: 600;
    color: ${accent_text};
    background: ${accent_soft};
    border-radius: 8px;
    padding: 1px 8px;
}
QLabel[objectName^="modelError:"] { font-size: 12px; color: ${danger}; }
QPushButton[objectName^="modelAction:"] {
    min-height: 30px;
    max-height: 30px;
    padding: 0 14px;
    font-size: 13px;
    border-radius: 8px;
}
QPushButton[objectName^="modelAction:"] {
    background: ${primary_bg};
    color: ${primary_text};
    border: 1px solid ${primary_bg};
}
QPushButton[objectName^="modelAction:"]:hover, QPushButton[objectName^="modelAction:"]:focus {
    background: ${primary_hover};
    border-color: ${accent};
}
QPushButton[objectName^="modelAction:"]:disabled {
    background: ${surface_active};
    color: ${text3};
    border-color: ${surface_active};
}
QPushButton[objectName^="modelDelete:"] {
    background: transparent;
    border: 0;
    border-radius: 8px;
    padding: 0;
}
QPushButton[objectName^="modelDelete:"]:hover, QPushButton[objectName^="modelDelete:"]:focus {
    background: ${surface_hover};
}
QPushButton[objectName^="modelDelete:"]:disabled { background: transparent; }
QProgressBar[objectName^="modelProgress:"] {
    min-height: 16px;
    max-height: 16px;
    border: 0;
    border-radius: 8px;
    background: ${surface_active};
    color: #FFFFFF;
    text-align: center;
    font-family: "${body}";
    font-size: 11px;
}
QProgressBar[objectName^="modelProgress:"]::chunk { background: ${accent}; border-radius: 8px; }
"""
