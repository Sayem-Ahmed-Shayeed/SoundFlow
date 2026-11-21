"""Sign-in and account dialogs.

Uses ``${token}`` names from :mod:`soundflow.design.theme`.
"""

SHEET = """
/* ---------- Auth ---------------------------------------------------- */
QDialog#authDialog { background: ${canvas}; }
#authBrand { font-size: 15px; font-weight: 600; color: ${text}; }
QWidget#authForm { background: ${canvas}; }
QFrame#authArt { background: ${spectrum_bg}; border-radius: 12px; }
#authHeadline {
    font-family: "${display}";
    font-size: 42px;
    font-weight: 400;
    color: #FFFFEB;
    background: transparent;
}
#mailMark { background: ${accent_soft}; border: 0; border-radius: 14px; }
"""
