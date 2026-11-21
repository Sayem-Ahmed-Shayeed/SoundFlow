import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from soundflow.ui.widgets.spinner import SPOKES, STEP_MS, Spinner, activity_step, paint_activity


class ActivityIndicatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_steps_eight_times_a_second_and_wraps(self):
        self.assertEqual(SPOKES, 8)
        self.assertEqual(STEP_MS, 125)
        self.assertEqual(activity_step(0), 0)
        self.assertEqual(activity_step(124), 0)
        self.assertEqual(activity_step(125), 1)
        self.assertEqual(activity_step(1000), 0)

    def test_runs_only_while_visible(self):
        with mock.patch("soundflow.ui.widgets.spinner.reduced_motion", return_value=False):
            spinner = Spinner(16)
            self.assertFalse(spinner.is_turning())
            spinner.show()
            self.assertTrue(spinner.is_turning())
            spinner.hide()
            self.assertFalse(spinner.is_turning())

    def test_holds_still_with_reduced_motion(self):
        with mock.patch("soundflow.ui.widgets.spinner.reduced_motion", return_value=True):
            spinner = Spinner(16)
            spinner.show()
            self.assertFalse(spinner.is_turning())
            spinner.hide()

    def test_brightest_spoke_follows_the_step(self):
        def top_alpha(step):
            image = QImage(40, 40, QImage.Format.Format_ARGB32)
            image.fill(0)
            painter = QPainter(image)
            paint_activity(painter, QPointF(20, 20), 18, QColor("#000000"), step)
            painter.end()
            return image.pixelColor(20, 5).alpha()  # the spoke pointing up

        self.assertGreater(top_alpha(0), top_alpha(4))


class SidebarSyncIndicatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_syncing_shows_the_indicator_instead_of_the_dot(self):
        from soundflow.ui.widgets.sidebar import AppSidebar as Sidebar

        sidebar = Sidebar()
        sidebar.set_account("Test", "test@example.com")
        sidebar.show()
        sidebar.set_sync_status("Syncing…")
        self.assertTrue(sidebar.sync_spinner.isVisibleTo(sidebar))
        self.assertFalse(sidebar.sync_dot.isVisibleTo(sidebar))
        sidebar.set_sync_status("Synced")
        self.assertFalse(sidebar.sync_spinner.isVisibleTo(sidebar))
        self.assertTrue(sidebar.sync_dot.isVisibleTo(sidebar))


if __name__ == "__main__":
    unittest.main()
