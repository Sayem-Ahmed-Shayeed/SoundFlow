"""Home: the green dictation card and the dashboard. The floating pill
paints itself and needs no rules.

Uses ``${token}`` names from :mod:`soundflow.design.theme`.
"""

SHEET = """
/* ---------- Home ------------------------------------------------------ */
#homeScroll, #homeScrollViewport, #homeHolder, #homeColumn {
    background: ${canvas};
    border: none;
}
#todayLine { font-size: 14px; color: ${text2}; }
#shortcutBanner {
    background: ${warning_soft};
    border: 1px solid ${warning};
    border-radius: 10px;
}
#shortcutBannerText { font-size: 13px; color: ${text}; }

/* The dictation card: deep green in both themes. */
QFrame#dictateCard {
    background: ${brand};
    border: none;
    border-radius: 18px;
}
QFrame#dictateCard QLabel { background: transparent; }
#cardTitle {
    font-family: "${display}";
    font-size: 30px;
    font-weight: 400;
    color: ${on_brand};
}
#cardTimer {
    font-family: "${display}";
    font-size: 30px;
    color: ${on_brand};
}
#cardNote { font-size: 14px; color: ${on_brand2}; }
#cardKey {
    font-family: "${body}";
    font-size: 13px;
    font-weight: 600;
    color: ${on_brand};
    background: rgba(255, 255, 235, 0.08);
    border: 1px solid rgba(255, 255, 235, 0.30);
    border-radius: 6px;
    padding: 2px 9px;
    min-height: 20px;
}
#liveText { font-size: 18px; color: ${on_brand}; }
#liveText[dim="true"] { color: ${on_brand2}; }

QPushButton#bigButton {
    background: ${primary_bg};
    border: 1px solid ${primary_bg};
    border-radius: 12px;
    padding: 0;
}
QPushButton#bigButton:hover { background: ${primary_hover}; border-color: ${primary_hover}; }
QPushButton#bigButton:focus { border: 2px solid ${on_brand}; }
QPushButton#bigButton[mode="working"] { background: ${primary_bg}; border-color: ${primary_bg}; }
#bigButtonLabel {
    font-size: 15px;
    font-weight: 600;
    color: ${primary_text};
    background: transparent;
}

/* The finished transcript. */
QFrame#resultCard {
    background: ${surface};
    border: 1px solid ${border};
    border-radius: 14px;
}
#resultText { font-size: 18px; color: ${text}; }
#resultOutcome { font-size: 13px; font-weight: 600; color: ${success}; }
#resultFact { font-size: 13px; color: ${text3}; }
QPushButton#smallButton {
    min-height: 30px;
    max-height: 30px;
    padding: 0 12px;
    font-size: 13px;
    border-radius: 8px;
}

/* Dashboard tiles and cards. */
QFrame#statTile, QFrame#dashCard {
    background: ${surface};
    border: 1px solid ${border};
    border-radius: 14px;
}
QFrame#statTile QLabel, QFrame#dashCard QLabel { background: transparent; }
#statBadge {
    font-size: 13px;
    background: ${raised};
    border-radius: 8px;
}
#statName { font-size: 14px; font-weight: 500; color: ${text2}; }
#statValue {
    font-family: "${display}";
    font-size: 40px;
    font-weight: 400;
    color: ${text};
}
#statUnit { font-size: 14px; font-weight: 500; color: ${text2}; }
#statNote { font-size: 12px; color: ${text3}; }
#dashCardTitle {
    font-family: "${display}";
    font-size: 22px;
    font-weight: 500;
    color: ${text};
}
#dashCaption { font-size: 12px; color: ${text3}; }
#totalValue {
    font-family: "${display}";
    font-size: 26px;
    font-weight: 400;
    color: ${text};
}
QFrame#dashRule { background: ${border}; border: none; }

#recentRow { background: transparent; border-radius: 10px; }
#recentRow:hover { background: ${raised}; }
#recentTime { font-size: 13px; color: ${text3}; background: transparent; }
#recentText { font-size: 14px; color: ${text}; background: transparent; }
#recordingOverlay { background: transparent; }
"""
