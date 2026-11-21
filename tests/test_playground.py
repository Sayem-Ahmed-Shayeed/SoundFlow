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



class FormatRemovesHesitationsTests(unittest.TestCase):
    def test_format_drops_um_uh_erm_hmm(self):
        self.assertEqual(format_text("Um, the launch went great, uh."), "The launch went great.")
        self.assertEqual(format_text("hmm let me think. erm, ok"), "Let me think. Ok.")
        self.assertEqual(format_text("we shipped uhh today"), "We shipped today.")

    def test_format_keeps_real_words(self):
        self.assertEqual(format_text("uh-huh, that works"), "Uh-huh, that works.")
        self.assertEqual(format_text("the drum umpire rule"), "The drum umpire rule.")
        # "basically" is meaning-bearing enough to leave to Rewrite.
        self.assertEqual(format_text("basically it works"), "Basically it works.")

    def test_format_keeps_bangla(self):
        self.assertEqual(format_text("আমি um ভালো আছি"), "আমি ভালো আছি")


if __name__ == "__main__":
    unittest.main()
