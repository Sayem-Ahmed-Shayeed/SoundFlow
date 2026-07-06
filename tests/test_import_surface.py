import os
import subprocess
import sys
import unittest


class ImportSurfaceTests(unittest.TestCase):
    def test_preferences_can_import_before_public_ui(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from soundflow.preferences.system_check import "
                    "run_system_check; from soundflow.ui import MainWindow; "
                    "print(MainWindow.__name__)"
                ),
            ],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("MainWindow", result.stdout)


if __name__ == "__main__":
    unittest.main()
