"""History page: transcript list on the left, the selected transcript on the right.

Uses ``${token}`` names from :mod:`soundflow.design.theme`.
"""

SHEET = """
/* ---------- History ------------------------------------------------- */
#historyList {
    border-right: 1px solid ${border};
}
#historyList QFrame#segmentedControl QPushButton { padding: 0 9px; }
#historySearch { min-height: 36px; }
#historyGroup { font-size: 12px; font-weight: 600; color: ${text3}; }
#resultCount { font-size: 12px; color: ${text3}; background: transparent; border: 0; }

#historyItem {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 10px;
}
#historyItem:hover { background: ${surface}; }
#historyItem[selected="true"] { background: ${raised}; }
#historyItem:focus { border-color: ${accent}; }
#historyMeta { font-size: 12px; color: ${text3}; }
#historyPreview { font-size: 14px; color: ${text2}; }
#historyItem[selected="true"] #historyPreview { color: ${text}; }

#historyEmpty { background: transparent; }
#emptyTitle { font-size: 16px; font-weight: 600; color: ${text}; }
#emptyBody { font-size: 14px; color: ${text2}; }

#historyDetail, #detailEmpty, #detailContent { background: ${canvas}; }
#detailScroll, #detailScroll > QWidget { background: ${canvas}; }
#historyDetail QLabel#tabTitle { padding-top: 6px; }
QPushButton#ghostButton { color: ${text2}; padding: 0 10px; }
QPushButton#ghostButton:hover { color: ${text}; }
#factValue { font-size: 16px; font-weight: 600; color: ${text}; }
#factLabel { font-size: 12px; color: ${text2}; }
#detailText {
    background: transparent;
    border: 0;
    font-size: 20px;
    color: ${text};
    selection-background-color: ${selection};
}
#historyEditor {
    background: ${field};
    color: ${text};
    border: 1px solid ${accent};
    border-radius: 10px;
    padding: 14px 16px;
    font-size: 20px;
    selection-background-color: ${selection};
}
#historyEditorHint { font-size: 13px; color: ${text2}; }
#historyFeedback { font-size: 12px; color: ${success}; }
#historyFeedback[state="error"] { color: ${danger}; }

QFrame#historyMenu {
    background: ${surface};
    border: 1px solid ${border_strong};
    border-radius: 10px;
}
QPushButton#menuItem {
    background: transparent;
    color: ${text};
    border: 0;
    border-radius: 7px;
    min-height: 34px;
    max-height: 34px;
    padding: 0 10px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
}
QPushButton#menuItem:hover { background: ${surface_hover}; }
QPushButton#menuItem[danger="true"] { color: ${danger}; }

QDialog#deleteTranscriptDialog { background: transparent; }
QFrame#deleteDialogSurface {
    background: ${surface};
    border: 1px solid ${border_strong};
    border-radius: 14px;
}
QLabel#deleteDialogTitle {
    font-family: "${display}";
    font-size: 25px;
    font-weight: 500;
    color: ${text};
}
QLabel#deleteDialogCopy { font-size: 13px; color: ${text2}; }
QLabel#deleteDialogQuote {
    font-size: 13px;
    color: ${text};
    background: ${raised};
    border-radius: 8px;
    padding: 10px 12px;
}
QPushButton#deleteDialogCancel { background: ${surface}; }
"""
