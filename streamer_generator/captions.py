from __future__ import annotations

import re
from dataclasses import dataclass


TIMESTAMP = re.compile(r"^(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})$")
TIMING_LINE = re.compile(
    r"^(\d{2}:\d{2}:\d{2}[,.]\d{3})\s+-->\s+"
    r"(\d{2}:\d{2}:\d{2}[,.]\d{3})(?:\s+.*)?$"
)
STYLES = {
    "bold": {"font": "Georgia", "size": 104, "primary": "&H0000FF00", "outline": 9},
    "clean": {"font": "Georgia", "size": 96, "primary": "&H0000FF00", "outline": 8},
    "neon": {"font": "Georgia", "size": 102, "primary": "&H0000FF00", "outline": 10},
}


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


def _seconds(value: str) -> float:
    match = TIMESTAMP.fullmatch(value)
    if not match:
        raise ValueError("invalid subtitle cue timestamp")
    hours, minutes, seconds, milliseconds = map(int, match.groups())
    if minutes > 59 or seconds > 59:
        raise ValueError("invalid subtitle cue timestamp")
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000


def parse_srt(source: str) -> list[Cue]:
    """Parse standard SRT blocks, preserving multiline cue text."""
    normalized = source.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    cues: list[Cue] = []
    for block in re.split(r"\n\s*\n", normalized):
        lines = [line.strip("\ufeff") for line in block.split("\n")]
        timing_index = next((i for i, line in enumerate(lines) if TIMING_LINE.match(line)), None)
        if timing_index is None or timing_index + 1 >= len(lines):
            raise ValueError("invalid subtitle cue: expected timing line and text")
        timing = TIMING_LINE.match(lines[timing_index])
        assert timing is not None
        start, end = map(_seconds, timing.groups())
        text = " ".join(line.strip() for line in lines[timing_index + 1 :] if line.strip())
        if end <= start or not text:
            raise ValueError("invalid subtitle cue: end must follow start and text is required")
        cues.append(Cue(start, end, text))
    cues.sort(key=lambda cue: (cue.start, cue.end))
    return cues


def _ass_time(seconds: float) -> str:
    centiseconds = max(0, round(seconds * 100))
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    whole_seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02}:{whole_seconds:02}.{centiseconds:02}"


def _ass_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def to_ass(cues: list[Cue], style: str = "bold", caption_y: int = 760) -> str:
    """Build bold green, black-outlined captions that pop at the facecam/gameplay seam."""
    if style not in STYLES:
        raise ValueError(f"unknown caption style: {style}")
    if not isinstance(caption_y, int) or not 0 <= caption_y <= 1920:
        raise ValueError("caption_y must be between 0 and 1920")
    selected = STYLES[style]
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{selected['font']},{selected['size']},{selected['primary']},&H0000FF00,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,{selected['outline']},4,5,40,40,0,1",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for cue in cues:
        words = cue.text.split()
        if not words:
            continue
        text = _ass_text(" ".join(words).upper())
        font_size = min(selected["size"], max(58, round(1080 / (0.62 * len(text)))))
        pop = f"{{\\an5\\pos(540,{caption_y})\\fs{font_size}\\fscx88\\fscy88\\t(0,120,\\fscx100\\fscy100)}}{text}"
        lines.append(f"Dialogue: 0,{_ass_time(cue.start)},{_ass_time(cue.end)},Default,,0,0,0,,{pop}")
    return "\n".join(lines) + "\n"
