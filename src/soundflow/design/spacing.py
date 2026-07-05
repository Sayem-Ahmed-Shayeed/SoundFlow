"""Spacing, radii, control heights, and font-size scale.

A 4-px grid plus a small set of named constants keeps widget code free of
magic numbers. Bump these values in one place to scale the entire UI.
"""

# --- Spacing scale (4-px grid) ----------------------------------------------
SPACE_0 = 0
SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 20
SPACE_6 = 24
SPACE_8 = 32
SPACE_10 = 40
SPACE_12 = 48
SPACE_16 = 64

# --- Border radii -----------------------------------------------------------
RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 16
RADIUS_PILL = 999

# --- Border widths ----------------------------------------------------------
BORDER_THIN = 1
BORDER_FOCUS = 2

# --- Standard control heights ----------------------------------------------
CONTROL_HEIGHT_SM = 28
CONTROL_HEIGHT_MD = 36
CONTROL_HEIGHT_LG = 44

# --- Font sizes (pixels) ---------------------------------------------------
FONT_DISPLAY = 32
FONT_TITLE = 22
FONT_HEADING = 16
FONT_BODY = 14
FONT_SMALL = 12
FONT_TINY = 11

# --- Window sizing ---------------------------------------------------------
WINDOW_MIN_WIDTH = 960
WINDOW_MIN_HEIGHT = 640
SIDEBAR_WIDTH = 216  # retained for any future use; current design drops the sidebar

# --- Common durations (ms) -------------------------------------------------
ANIMATION_FAST = 120
ANIMATION_NORMAL = 200
ANIMATION_SLOW = 320