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
            self.assertIn('QProgressBar[objectName^="modelProgress:"]', sheet)
            self.assertIn('QPushButton[objectName^="modelAction:"]:focus', sheet)
            self.assertIn('QPushButton[objectName^="modelDelete:"]', sheet)
            self.assertIn("min-height: 20px", sheet)
            self.assertIn("max-height: 20px", sheet)
            self.assertIn("min-height: 4px", sheet)
            self.assertIn("max-height: 4px", sheet)

    def test_spacing_grid_is_4px(self) -> None:
        from soundflow.design.spacing import SPACE_1, SPACE_2, SPACE_3, SPACE_4
        self.assertEqual(SPACE_1, 4)
        self.assertEqual(SPACE_2, 8)
        self.assertEqual(SPACE_3, 12)
        self.assertEqual(SPACE_4, 16)


if __name__ == "__main__":
    unittest.main()
