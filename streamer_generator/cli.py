from __future__ import annotations

import argparse
import os
from pathlib import Path

from .render import render_video


def _focus(value: str) -> tuple[float, float]:
    try:
        x, y = (float(part) / 100 for part in value.split(",", maxsplit=1))
    except (ValueError, TypeError) as error:
        raise argparse.ArgumentTypeError("focus must be written as X,Y percentages, for example 50,45") from error
    if not 0 <= x <= 1 or not 0 <= y <= 1:
        raise argparse.ArgumentTypeError("focus percentages must be between 0 and 100")
    return x, y


def _report(progress: float, message: str) -> None:
    print(f"{progress * 100:5.1f}%  {message}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="streamer-shorts", description="Create vertical streamer and gameplay videos locally with FFmpeg.")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="launch the local browser studio")
    serve.add_argument("--host", default=os.getenv("STREAMER_GENERATOR_HOST", "127.0.0.1"))
    serve.add_argument("--port", type=int, default=int(os.getenv("STREAMER_GENERATOR_PORT", "8765")))

    render = commands.add_parser("render", help="render a video from the command line")
    render.add_argument("--facecam", type=Path, required=True)
    render.add_argument("--gameplay", type=Path, required=True)
    render.add_argument("--captions", type=Path, help="optional SRT subtitle file")
    render.add_argument("--output", type=Path, required=True)
    render.add_argument("--style", choices=("bold", "clean", "neon"), default="bold")
    render.add_argument("--facecam-height", type=int, choices=(576, 672, 768, 864, 960), default=768)
    render.add_argument("--fps", type=int, choices=(30, 60), default=30)
    render.add_argument("--streamer-volume", type=float, default=1.0, help="0 to 2")
    render.add_argument("--gameplay-volume", type=float, default=1.0, help="0 to 2")
    render.add_argument("--facecam-focus", type=_focus, default=(0.5, 0.5), metavar="X,Y")
    render.add_argument("--gameplay-focus", type=_focus, default=(0.5, 0.5), metavar="X,Y")

    args = parser.parse_args(argv)
    if args.command == "serve":
        if args.host not in {"127.0.0.1", "localhost", "::1"}:
            parser.error("the local studio binds to loopback only; do not expose unprotected uploads on a network")
        try:
            import uvicorn
        except ImportError:
            parser.error("web mode needs the optional dependencies: pip install -r requirements.txt")
        from .server import app

        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
        return 0

    subtitles = args.captions.read_text(encoding="utf-8-sig") if args.captions else ""
    result = render_video(
        args.facecam,
        args.gameplay,
        args.output,
        subtitle_text=subtitles,
        style=args.style,
        facecam_height=args.facecam_height,
        fps=args.fps,
        streamer_volume=args.streamer_volume,
        gameplay_volume=args.gameplay_volume,
        facecam_focus=args.facecam_focus,
        gameplay_focus=args.gameplay_focus,
        on_progress=_report,
    )
    print(f"Saved {result} ({result.stat().st_size:,} bytes)")
    return 0
