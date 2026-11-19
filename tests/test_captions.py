import unittest

from streamer_generator.captions import parse_srt, to_ass


class CaptionTests(unittest.TestCase):
    def test_srt_cues_render_as_large_green_pop_captions_at_the_join(self):
        cues = parse_srt("""1
00:00:00,000 --> 00:00:02,000
This is a test!
""")

        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].text, "This is a test!")
        ass = to_ass(cues, style="bold")
        self.assertIn("PlayResX: 1080", ass)
        self.assertIn("THIS", ass)
        self.assertIn("\nPlayResY: 1920", ass)
        self.assertIn("Style: Default,Georgia,104,", ass)
        self.assertIn("\\pos(540,760)", ass)
        self.assertIn("&H0000FF00", ass)
        self.assertNotIn("{\\k", ass)

    def test_invalid_srt_is_rejected_with_a_useful_error(self):
        with self.assertRaisesRegex(ValueError, "subtitle cue"):
            parse_srt("this is not an SRT cue")


if __name__ == "__main__":
    unittest.main()
