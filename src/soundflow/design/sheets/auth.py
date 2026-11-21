"""Sign-in and account dialogs.

Uses ``${token}`` names from :mod:`soundflow.design.theme`.
"""

SHEET = """
/* ---------- Auth ---------------------------------------------------- */
QDialog#authDialog { background: ${canvas}; }
#authBrand { font-size: 15px; font-weight: 600; color: ${text}; }
QWidget#authForm { background: ${canvas}; }
QFrame#authArt { background: #06100D; border-radius: 18px; }
/* The form's title matches the Bodoni of the cover beside it. */
QDialog#authDialog QLabel#pageTitle {
    font-family: "${cover}";
    font-size: 31px;
    font-weight: 500;
    letter-spacing: -0.8px;
}
QLineEdit#passwordField { padding-right: 4px; }
#mailMark { background: ${accent_soft}; border: 0; border-radius: 14px; }
"""
