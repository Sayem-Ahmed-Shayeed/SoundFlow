import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QAbstractAnimation, QEasingCurve, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    HAS_QT = True
except ImportError:
    HAS_QT = False

if HAS_QT:
    from soundflow.design.spacing import ANIMATION_CONTROL
    from soundflow.ui.widgets import ToggleSwitch


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

    def test_visible_switch_animates_thumb_to_checked_endpoint(self):
        switch = ToggleSwitch("Auto-save transcripts")
        switch.show()
        self.app.processEvents()

        switch.setChecked(True)

        self.assertEqual(switch._thumb_animation.duration(), ANIMATION_CONTROL)
        self.assertEqual(
            switch._thumb_animation.easingCurve().type(),
            QEasingCurve.Type.OutCubic,
        )
        self.assertEqual(
            switch._thumb_animation.state(),
            QAbstractAnimation.State.Running,
        )
        QTest.qWait(ANIMATION_CONTROL + 30)
        self.assertAlmostEqual(switch.thumbPosition, 1.0)

    def test_rapid_toggle_continues_from_visible_thumb_position(self):
        switch = ToggleSwitch("Auto-save transcripts")
        switch.show()
        self.app.processEvents()

        switch.setChecked(True)
        QTest.qWait(ANIMATION_CONTROL // 2)
        midpoint = switch.thumbPosition
        self.assertGreater(midpoint, 0.0)
        self.assertLess(midpoint, 1.0)

        switch.setChecked(False)
        self.assertAlmostEqual(
            float(switch._thumb_animation.startValue()),
            midpoint,
            delta=0.08,
        )
        QTest.qWait(ANIMATION_CONTROL + 30)
        self.assertAlmostEqual(switch.thumbPosition, 0.0)


if __name__ == "__main__":
    unittest.main()
