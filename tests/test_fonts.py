import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from soundflow.design.fonts import (
    BODY_FONT,
    DISPLAY_FONT,
    register_application_fonts,
)


class FontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_roboto_is_the_shared_application_font(self):
        font_ids = register_application_fonts()

        self.assertEqual(BODY_FONT, "Roboto")
        self.assertEqual(DISPLAY_FONT, "Roboto")
        self.assertGreaterEqual(len(font_ids), 3)
        self.assertIn("Roboto", QFontDatabase.families())


if __name__ == "__main__":
    unittest.main()
