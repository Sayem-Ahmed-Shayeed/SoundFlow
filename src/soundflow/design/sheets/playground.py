"""Playground page.

Uses ``${token}`` names from :mod:`soundflow.design.theme`.
"""

SHEET = """
/* ---------- Playground ---------------------------------------------- */
QPushButton#playAction {
    background: ${surface};
    border: 1px solid ${border};
    border-radius: 10px;
    text-align: left;
    padding: 0;
}
QPushButton#playAction:hover { background: ${surface_hover}; border-color: ${border_strong}; }
QPushButton#playAction:pressed { background: ${surface_active}; }
QPushButton#playAction:checked { border: 1px solid ${accent}; background: ${accent_soft}; }
QPushButton#playAction:disabled { color: ${text3}; }
#playActionTitle { font-size: 14px; font-weight: 600; color: ${text}; background: transparent; }
#playActionText { font-size: 12px; color: ${text2}; background: transparent; }
#playgroundCommand {
    font-size: 16px;
    padding: 16px 18px;
    border-radius: 12px;
    background: ${field};
    border: 1px solid ${border};
}
#playgroundCommand:focus { border-color: ${accent}; }
QScrollArea#playgroundPreview {
    background: ${surface};
    border: 1px dashed ${border_strong};
    border-radius: 12px;
}
QScrollArea#playgroundPreview > QWidget#qt_scrollarea_viewport { background: transparent; }
#playgroundPreviewText {
    font-size: 16px;
    color: ${text};
    background: transparent;
    padding: 16px 18px;
}
#playgroundPreviewText[state="placeholder"], #playgroundPreviewText[state="status"] { color: ${text3}; }
#playgroundPreviewText[state="error"] { color: ${danger}; }
"""
