from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from .captions import parse_srt, to_ass


Progress = Callable[[float, str], None]


def _number(value: float, name: str, low: float, high: float) -> float:
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be between {low:g} and {high:g}")
    return value


def build_filter_graph(
    *,
    duration: float,
    fps: int,
    streamer_volume: float,
    gameplay_volume: float,
    has_streamer_audio: bool,
    has_gameplay_audio: bool,
    captions: bool = True,
    caption_filename: str = "captions.ass",
) -> str:
    """Fill both panels with source footage and put captions directly over their seam."""
    duration = _number(duration, "duration", 0.05, 24 * 60 * 60)
    if fps not in (30, 60):
        raise ValueError("fps must be 30 or 60")
    streamer_volume = _number(streamer_volume, "streamer volume", 0, 2)
    gameplay_volume = _number(gameplay_volume, "gameplay volume", 0, 2)
    top_height, bottom_height = 760, 1160
    duration_arg = f"{duration:.3f}"
    graph = [
        f"[0:v:0]trim=duration={duration_arg},setpts=PTS-STARTPTS,"
        f"scale=1080:{top_height}:force_original_aspect_ratio=increase,"
        f"crop=1080:{top_height},setsar=1,"
        f"fps={fps},format=yuv420p[top]",
        f"[1:v:0]trim=duration={duration_arg},setpts=PTS-STARTPTS,"
        f"scale=1080:{bottom_height}:force_original_aspect_ratio=increase,"
        f"crop=1080:{bottom_height},setsar=1,"
        f"fps={fps},format=yuv420p[bottom]",
    ]
    graph.append("[top][bottom]vstack=inputs=2:shortest=1[stack]")
    if captions:
        graph.append(
            f"[stack]subtitles=filename='{caption_filename}':original_size=1080x1920,"
            "format=yuv420p[vout]"
        )
    else:
        graph.append("[stack]format=yuv420p[vout]")

    for index, (exists, volume) in enumerate(
        ((has_streamer_audio, streamer_volume), (has_gameplay_audio, gameplay_volume))
    ):
        label = f"a{index}"
        if exists:
            graph.append(
                f"[{index}:a:0]aresample=48000,atrim=duration={duration_arg},"
                f"asetpts=PTS-STARTPTS,volume={volume:.3f}[{label}]"
            )
        else:
            graph.append(
                f"anullsrc=r=48000:cl=stereo,atrim=duration={duration_arg},"
                f"asetpts=PTS-STARTPTS,volume={volume:.3f}[{label}]"
            )
    graph.append("[a0][a1]amix=inputs=2:duration=shortest:dropout_transition=0,alimiter=limit=0.95[aout]")
    return ";".join(graph)


def probe_media(path: Path, ffprobe: str | None = None) -> dict:
    executable = ffprobe or shutil.which("ffprobe")
    if not executable:
        raise RuntimeError("ffprobe was not found. Install FFmpeg and add it to PATH.")
    result = subprocess.run(
        [executable, "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode:
        raise ValueError(f"Could not read {path.name}: {result.stderr.strip()[-1000:]}")
    try:
        data = json.loads(result.stdout)
        duration = float(data["format"]["duration"])
        streams = data.get("streams", [])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read video information from {path.name}") from error
    if not math.isfinite(duration) or duration <= 0 or not any(s.get("codec_type") == "video" for s in streams):
        raise ValueError(f"{path.name} must contain a video track with a valid duration")
    return {"duration": duration, "has_audio": any(s.get("codec_type") == "audio" for s in streams)}


def render_video(
    facecam: Path,
    gameplay: Path,
    output: Path,
    *,
    subtitle_text: str = "",
    style: str = "bold",
    fps: int = 30,
    streamer_volume: float = 1,
    gameplay_volume: float = 1,
    on_progress: Progress | None = None,
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
) -> Path:
    """Render facecam-over-gameplay into an H.264 1080x1920 MP4."""
    ffmpeg = ffmpeg or shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg was not found. Install FFmpeg and add it to PATH.")
    facecam = Path(facecam).resolve(strict=True)
    gameplay = Path(gameplay).resolve(strict=True)
    output = Path(output).resolve()
    if output.suffix.lower() != ".mp4" or output in {facecam, gameplay}:
        raise ValueError("output must be a new MP4 path, separate from source files")
    output.parent.mkdir(parents=True, exist_ok=True)
    face_info = probe_media(facecam, ffprobe)
    game_info = probe_media(gameplay, ffprobe)
    duration = min(face_info["duration"], game_info["duration"])
    cue_list = parse_srt(subtitle_text)
    ass_path: Path | None = None
    if cue_list:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".ass", prefix="gta-face-clipper-",
            dir=output.parent, delete=False,
        ) as captions_file:
            ass_path = Path(captions_file.name)
            captions_file.write(to_ass(cue_list, style))

    graph = build_filter_graph(
        duration=duration,
        fps=fps,
        streamer_volume=streamer_volume,
        gameplay_volume=gameplay_volume,
        has_streamer_audio=face_info["has_audio"],
        has_gameplay_audio=game_info["has_audio"],
        captions=bool(cue_list),
        caption_filename=ass_path.name if ass_path else "captions.ass",
    )
    command = [
        ffmpeg, "-hide_banner", "-nostdin", "-y", "-i", str(facecam), "-i", str(gameplay),
        "-filter_complex", graph, "-map", "[vout]", "-map", "[aout]", "-t", f"{duration:.3f}",
        "-r", str(fps), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", str(output),
    ]
    if on_progress:
        on_progress(0.18, "Composing facecam and gameplay")
    try:
        process = subprocess.Popen(
            command,
            cwd=output.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as error:
        if ass_path and ass_path.exists():
            ass_path.unlink()
        raise RuntimeError(f"FFmpeg could not start: {error}") from error
    stderr_chunks: list[str] = []
    assert process.stdout is not None and process.stderr is not None
    # FFmpeg writes progress to stdout. stderr is drained on a helper thread to avoid pipe backpressure.
    import threading

    def drain_stderr() -> None:
        for line in process.stderr:
            stderr_chunks.append(line)
            if len(stderr_chunks) > 300:
                del stderr_chunks[:100]

    stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
    stderr_thread.start()
    for line in process.stdout:
        if line.startswith("out_time_ms=") and on_progress:
            try:
                seconds = int(line.partition("=")[2]) / 1_000_000
                on_progress(min(0.92, 0.28 + 0.62 * seconds / duration), "Rendering video and audio")
            except ValueError:
                pass
    try:
        return_code = process.wait(timeout=max(180, duration * 30))
    except subprocess.TimeoutExpired as error:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        if output.exists():
            output.unlink()
        if ass_path and ass_path.exists():
            ass_path.unlink()
        raise RuntimeError("FFmpeg render exceeded the time limit and was stopped.") from error
    stderr_thread.join(timeout=5)
    if ass_path and ass_path.exists():
        ass_path.unlink()
    if return_code:
        if output.exists():
            output.unlink()
        detail = "".join(stderr_chunks).strip()[-3500:]
        raise RuntimeError(f"FFmpeg could not render the video. {detail}")
    if not output.exists() or output.stat().st_size < 1024:
        raise RuntimeError("FFmpeg finished without producing a usable MP4.")
    if on_progress:
        on_progress(1.0, "Video ready")
    return output
