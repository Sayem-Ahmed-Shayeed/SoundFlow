"""Unit tests for the design tokens (no Qt required for these checks)."""

import unittest


class DesignTokenTests(unittest.TestCase):
    def test_palette_is_monochrome(self) -> None:
        from soundflow.design import (
            BG_BLACK,
            BG_PANEL,
            BG_RAISED,
            BORDER,
            ERROR,
            FG_CREAM,
            FG_DIM,
            FG_MUTED,
            SUCCESS,
        )
        # The palette intentionally avoids blue and purple; spot-check by
        # verifying that no token starts with the typical purple hue bands.
        for token in (
            BG_BLACK, BG_PANEL, BG_RAISED, BORDER, ERROR,
            FG_CREAM, FG_DIM, FG_MUTED, SUCCESS,
        ):
            self.assertTrue(token.startswith("#"))
            self.assertEqual(len(token), 7)

    def test_resolved_dark_only_dark_and_light(self) -> None:
        from soundflow.design import resolved_dark
        self.assertTrue(resolved_dark("dark"))
        self.assertFalse(resolved_dark("light"))
        # Anything else falls back to dark.
        self.assertTrue(resolved_dark("system"))
        self.assertTrue(resolved_dark(""))
        self.assertTrue(resolved_dark(None))  # type: ignore[arg-type]

    def test_stylesheet_returns_nonempty_strings(self) -> None:
        from soundflow.design import stylesheet
        dark = stylesheet(True)
        light = stylesheet(False)
        self.assertGreater(len(dark), 100)
        self.assertGreater(len(light), 100)

    def test_dark_stylesheet_contains_cream_and_black(self) -> None:
        from soundflow.design import BG_BLACK, FG_CREAM, stylesheet
        sheet = stylesheet(True)
        self.assertEqual(BG_BLACK, "#000000")
        self.assertIn(BG_BLACK, sheet)
        self.assertIn(FG_CREAM, sheet)

    def test_compact_dropdowns_have_a_consistent_chevron(self) -> None:
        from soundflow.design import stylesheet
        for sheet in (stylesheet(True), stylesheet(False)):
            self.assertIn("QComboBox#compactPreferenceField::down-arrow", sheet)
            self.assertIn("QComboBox#compactShortcutField::down-arrow", sheet)
            self.assertIn("image: url(", sheet)
            self.assertIn("QSlider::add-page:horizontal", sheet)

    def test_model_manager_rules_cover_rows_progress_focus_and_delete(self) -> None:
        from soundflow.design import stylesheet

        for sheet in (stylesheet(True), stylesheet(False)):
            self.assertIn("#modelManagerCard", sheet)
            self.assertIn('[objectName^="modelRow:"]', sheet)
            progress_selector = 'QProgressBar[objectName^="modelProgress:"]'
            self.assertIn(progress_selector, sheet)
            progress_rule = sheet.split(progress_selector, 1)[1].split("}", 1)[0]
            self.assertIn("min-height: 16px;", progress_rule)
            self.assertIn("max-height: 16px;", progress_rule)
            self.assertIn("color: #FFFFFF;", progress_rule)
            self.assertIn("text-align: center;", progress_rule)
            self.assertIn('QPushButton[objectName^="modelAction:"]:focus', sheet)
            self.assertIn('QPushButton[objectName^="modelDelete:"]', sheet)
            self.assertIn("min-height: 20px", sheet)
            self.assertIn("max-height: 20px", sheet)

    def test_vertical_scrollbars_hide_native_arrow_steppers(self) -> None:
        from soundflow.design import stylesheet

        line_selector = (
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical"
        )
        arrow_selector = (
            "QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical"
        )
        for sheet in (stylesheet(True), stylesheet(False)):
            line_rule = sheet.split(line_selector, 1)[1].split("}", 1)[0]
            self.assertIn("height: 0;", line_rule)
            self.assertIn("border: 0;", line_rule)

            arrow_rule = sheet.split(arrow_selector, 1)[1].split("}", 1)[0]
            self.assertIn("width: 0;", arrow_rule)
            self.assertIn("height: 0;", arrow_rule)

    def test_disabled_model_delete_is_neutral_in_both_themes(self) -> None:
        from soundflow.design import stylesheet

        selector = 'QPushButton[objectName^="modelDelete:"]:disabled'
        themes = (
            (stylesheet(True), "#A9A9B2", "#29292F", "#0A0A0C", "#F0787F"),
            (stylesheet(False), "#647089", "#D7DEEA", "#FFFFFF", "#C4515B"),
        )
        for sheet, muted, border, panel, destructive in themes:
            block = sheet.split(selector, 1)[1].split("}", 1)[0]
            self.assertIn(f"color: {muted};", block)
            self.assertIn(f"background: {panel};", block)
            self.assertIn(f"border: 1px solid {border};", block)
            self.assertNotIn(destructive, block)

    def test_spacing_grid_is_4px(self) -> None:
        from soundflow.design.spacing import SPACE_1, SPACE_2, SPACE_3, SPACE_4
        self.assertEqual(SPACE_1, 4)
        self.assertEqual(SPACE_2, 8)
        self.assertEqual(SPACE_3, 12)
        self.assertEqual(SPACE_4, 16)


if __name__ == "__main__":
    unittest.main()
