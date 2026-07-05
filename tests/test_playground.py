import unittest

from soundflow.playground.actions import format_text, smart_rewrite


class PlaygroundTransformTests(unittest.TestCase):
    def test_format_text_normalizes_spacing_and_capitalization(self):
        self.assertEqual(
            format_text("  hello   world.this is\na test  "),
            "Hello world. This is a test.",
        )

    def test_format_text_preserves_unicode(self):
        self.assertEqual(format_text("  আমি   ভালো আছি  "), "আমি ভালো আছি")

    def test_smart_rewrite_removes_fillers_without_inventing_content(self):
        self.assertEqual(
            smart_rewrite("Um, I think, you know, this is actually useful."),
            "I think this is useful.",
        )

    def test_transforms_accept_empty_text(self):
        self.assertEqual(format_text(""), "")
        self.assertEqual(smart_rewrite(""), "")


if __name__ == "__main__":
    unittest.main()
