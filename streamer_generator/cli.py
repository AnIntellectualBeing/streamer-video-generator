from __future__ import annotations

import argparse
from pathlib import Path

from .render import render_video


def _report(progress: float, message: str) -> None:
    print(f"{progress * 100:5.1f}%  {message}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gta-streamer-face-clipper",
        description="Make a vertical streamer + GTA clip from two videos and optional SRT captions.",
    )
    parser.add_argument("--facecam", type=Path, required=True, help="streamer's video or facecam file")
    parser.add_argument("--gameplay", type=Path, required=True, help="GTA gameplay video file")
    parser.add_argument("--captions", type=Path, help="optional SRT subtitle file")
    parser.add_argument("--output", type=Path, required=True, help="destination .mp4 file")
    parser.add_argument("--style", choices=("bold", "clean", "neon"), default="bold")
    parser.add_argument("--fps", type=int, choices=(30, 60), default=30)
    parser.add_argument("--streamer-volume", type=float, default=1.0, help="0 to 2")
    parser.add_argument("--gameplay-volume", type=float, default=1.0, help="0 to 2")
    args = parser.parse_args(argv)

    try:
        subtitles = args.captions.read_text(encoding="utf-8-sig") if args.captions else ""
        result = render_video(
            args.facecam,
            args.gameplay,
            args.output,
            subtitle_text=subtitles,
            style=args.style,
            fps=args.fps,
            streamer_volume=args.streamer_volume,
            gameplay_volume=args.gameplay_volume,
            on_progress=_report,
        )
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f"gta-streamer-face-clipper: error: {error}\n")
    print(f"Saved {result} ({result.stat().st_size:,} bytes)")
    return 0
