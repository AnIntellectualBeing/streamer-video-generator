import unittest
import tempfile
from pathlib import Path

from streamer_generator.render import build_filter_graph, render_video


class RenderGraphTests(unittest.TestCase):
    def test_filter_graph_uses_split_screen_karaoke_captions_and_audio_mix(self):
        graph = build_filter_graph(
            duration=12.5,
            facecam_height=768,
            fps=60,
            streamer_volume=1.0,
            gameplay_volume=0.25,
            facecam_focus=(0.5, 0.25),
            gameplay_focus=(0.5, 0.6),
            has_streamer_audio=True,
            has_gameplay_audio=False,
        )

        self.assertIn("scale=1080:768", graph)
        self.assertIn("scale=1080:1152", graph)
        self.assertIn("fps=60", graph)
        self.assertIn("subtitles=filename='captions.ass'", graph)
        self.assertIn("volume=0.25", graph)
        self.assertIn("anullsrc=r=48000:cl=stereo", graph)
        self.assertIn("amix=inputs=2", graph)

    def test_renderer_rejects_output_that_would_overwrite_source_footage(self):
        with tempfile.TemporaryDirectory() as directory:
            facecam = Path(directory) / "facecam.mp4"
            gameplay = Path(directory) / "gameplay.mp4"
            facecam.touch()
            gameplay.touch()
            with self.assertRaisesRegex(ValueError, "must be a new MP4 path"):
                render_video(facecam, gameplay, facecam)

    def test_renderer_requires_an_mp4_output_path(self):
        with tempfile.TemporaryDirectory() as directory:
            facecam = Path(directory) / "facecam.mp4"
            gameplay = Path(directory) / "gameplay.mp4"
            facecam.touch()
            gameplay.touch()
            with self.assertRaisesRegex(ValueError, "must be a new MP4 path"):
                render_video(facecam, gameplay, Path(directory) / "result.mov")


if __name__ == "__main__":
    unittest.main()
