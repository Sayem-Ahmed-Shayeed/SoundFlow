import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QEasingCurve, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QPushButton

    HAS_QT = True
except ImportError:
    HAS_QT = False

if HAS_QT:
    from soundflow.design.motion import install_button_motion
    from soundflow.design.spacing import ANIMATION_FAST


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class ButtonMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.motion = install_button_motion(cls.app)

    def _button(self) -> QPushButton:
        button = QPushButton("Download")
        button.resize(120, 36)
        button.show()
        self.app.processEvents()
        return button

    def test_enabled_button_click_starts_short_feedback(self):
        button = self._button()
        clicks = []
        button.clicked.connect(lambda: clicks.append(True))

        QTest.mouseClick(button, Qt.MouseButton.LeftButton)

        self.assertEqual(clicks, [True])
        animation = self.motion.animation_for(button)
        self.assertIsNotNone(animation)
        self.assertEqual(animation.duration(), ANIMATION_FAST)
        self.assertEqual(
            animation.easingCurve().type(),
            QEasingCurve.Type.OutCubic,
        )
        QTest.qWait(ANIMATION_FAST + 30)
        self.assertIsNone(button.graphicsEffect())
        self.assertIsNone(self.motion.animation_for(button))

    def test_disabled_button_does_not_animate_or_click(self):
        button = self._button()
        clicks = []
        button.clicked.connect(lambda: clicks.append(True))
        button.setEnabled(False)

        QTest.mouseClick(button, Qt.MouseButton.LeftButton)

        self.assertEqual(clicks, [])
        self.assertIsNone(self.motion.animation_for(button))
        self.assertIsNone(button.graphicsEffect())

    def test_rapid_click_replaces_feedback_without_losing_clicks(self):
        button = self._button()
        clicks = []
        button.clicked.connect(lambda: clicks.append(True))

        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        first = self.motion.animation_for(button)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        second = self.motion.animation_for(button)

        self.assertEqual(clicks, [True, True])
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertIsNot(first, second)
        QTest.qWait(ANIMATION_FAST + 30)
        self.assertIsNone(button.graphicsEffect())


if __name__ == "__main__":
    unittest.main()
