import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from soundflow.ui.widgets import ToggleSwitch
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class ToggleSwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_mouse_and_space_toggle_native_checked_state(self):
        switch = ToggleSwitch("Auto-save transcripts")
        switch.show()
        self.app.processEvents()
        self.assertFalse(switch.isChecked())
        QTest.mouseClick(switch, Qt.MouseButton.LeftButton)
        self.assertTrue(switch.isChecked())
        switch.setFocus()
        QTest.keyClick(switch, Qt.Key.Key_Space)
        self.assertFalse(switch.isChecked())
        self.assertEqual(switch.accessibleName(), "Auto-save transcripts")

    def test_switch_palette_uses_neutral_off_and_violet_on_states(self):
        self.assertEqual(
            ToggleSwitch.color_tokens(dark=False, checked=False),
            ("#D9DBE2", "#B9BCC6", "#FFFFFF"),
        )
        self.assertEqual(
            ToggleSwitch.color_tokens(dark=True, checked=True),
            ("#9B72FF", "#A987FF", "#FFFFFF"),
        )


if __name__ == "__main__":
    unittest.main()
