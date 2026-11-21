import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from soundflow.core import autostart
from soundflow.core.autostart import AutostartPaths, default_paths, set_open_at_login

DESKTOP = (
    "[Desktop Entry]\n"
    "Type=Application\n"
    "Name=Soundflow Background\n"
    "Exec=/opt/soundflow/Soundflow --background\n"
)


class _Runner:
    def __init__(self, code=0, error=None):
        self.code = code
        self.error = error
        self.calls: list[list[str]] = []

    def __call__(self, args):
        self.calls.append(list(args))
        if self.error is not None:
            raise self.error
        return self.code


class AutostartTests(unittest.TestCase):
    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.paths = AutostartPaths(config_home=Path(self._directory.name) / "config")
        self._platform = patch.object(autostart.sys, "platform", "linux")
        self._platform.start()

    def tearDown(self):
        self._platform.stop()
        self._directory.cleanup()

    def _install_service(self):
        self.paths.service_file.parent.mkdir(parents=True)
        self.paths.service_file.write_text("[Unit]\n", encoding="utf-8")

    def _install_desktop_entry(self):
        self.paths.autostart_file.parent.mkdir(parents=True)
        self.paths.autostart_file.write_text(DESKTOP, encoding="utf-8")

    def test_nothing_installed_is_a_quiet_no_op(self):
        run = _Runner()
        self.assertTrue(set_open_at_login(False, paths=self.paths, run=run))
        self.assertTrue(set_open_at_login(True, paths=self.paths, run=run))
        self.assertEqual(run.calls, [])
        self.assertFalse(self.paths.autostart_file.exists())

    def test_enabling_and_disabling_the_systemd_service(self):
        self._install_service()
        run = _Runner()
        self.assertTrue(set_open_at_login(True, paths=self.paths, run=run))
        self.assertTrue(set_open_at_login(False, paths=self.paths, run=run))
        self.assertEqual(
            run.calls,
            [
                ["enable", "soundflow.service"],
                ["disable", "soundflow.service"],
            ],
        )

    def test_service_failure_is_reported_not_raised(self):
        self._install_service()
        self.assertFalse(
            set_open_at_login(True, paths=self.paths, run=_Runner(code=1))
        )
        self.assertFalse(
            set_open_at_login(
                True,
                paths=self.paths,
                run=_Runner(error=subprocess.TimeoutExpired("systemctl", 10)),
            )
        )
        self.assertFalse(
            set_open_at_login(
                True, paths=self.paths, run=_Runner(error=FileNotFoundError("systemctl"))
            )
        )

    def test_autostart_entry_is_hidden_when_disabled_and_restored_when_enabled(self):
        self._install_desktop_entry()
        run = _Runner()
        self.assertTrue(set_open_at_login(False, paths=self.paths, run=run))
        text = self.paths.autostart_file.read_text(encoding="utf-8")
        self.assertIn("Hidden=true", text.splitlines())
        self.assertEqual(text.count("[Desktop Entry]"), 1)
        self.assertEqual(run.calls, [])

        self.assertTrue(set_open_at_login(True, paths=self.paths, run=run))
        text = self.paths.autostart_file.read_text(encoding="utf-8")
        self.assertNotIn("Hidden=", text)
        self.assertIn("Exec=/opt/soundflow/Soundflow --background", text)

    def test_hiding_twice_does_not_duplicate_the_flag(self):
        self._install_desktop_entry()
        set_open_at_login(False, paths=self.paths, run=_Runner())
        set_open_at_login(False, paths=self.paths, run=_Runner())
        text = self.paths.autostart_file.read_text(encoding="utf-8")
        self.assertEqual(text.count("Hidden=true"), 1)

    def test_unreadable_autostart_entry_fails_without_raising(self):
        self._install_desktop_entry()
        with patch.object(Path, "read_text", side_effect=OSError("denied")):
            self.assertFalse(set_open_at_login(False, paths=self.paths, run=_Runner()))

    def test_other_platforms_are_left_alone(self):
        self._install_service()
        run = _Runner()
        with patch.object(autostart.sys, "platform", "win32"):
            self.assertTrue(set_open_at_login(False, paths=self.paths, run=run))
        self.assertEqual(run.calls, [])

    def test_default_paths_follow_xdg_config_home(self):
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/tmp/xdg-test"}):
            paths = default_paths()
        self.assertEqual(paths.autostart_file, Path("/tmp/xdg-test/autostart/soundflow.desktop"))
        self.assertEqual(
            paths.service_file, Path("/tmp/xdg-test/systemd/user/soundflow.service")
        )


if __name__ == "__main__":
    unittest.main()
