from __future__ import annotations

import re
from dataclasses import dataclass


TIMESTAMP = re.compile(r"^(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})$")
TIMING_LINE = re.compile(
    r"^(\d{2}:\d{2}:\d{2}[,.]\d{3})\s+-->\s+"
    r"(\d{2}:\d{2}:\d{2}[,.]\d{3})(?:\s+.*)?$"
)
STYLES = {
    "bold": {"font": "Arial", "size": 64, "primary": "&H00FFFFFF", "highlight": "&H0000D7FF", "outline": 5},
    "clean": {"font": "Arial", "size": 58, "primary": "&H00FFFFFF", "highlight": "&H0000D7FF", "outline": 4},
    "neon": {"font": "Arial", "size": 62, "primary": "&H00FFFFFF", "highlight": "&H0000FFFF", "outline": 6},
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


def to_ass(cues: list[Cue], style: str = "bold") -> str:
    """Build centered, outlined ASS captions with per-word karaoke timing."""
    if style not in STYLES:
        raise ValueError(f"unknown caption style: {style}")
    selected = STYLES[style]
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 180",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{selected['font']},{selected['size']},{selected['primary']},{selected['highlight']},&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,{selected['outline']},2,5,48,48,0,1",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for cue in cues:
        words = cue.text.split()
        if not words:
            continue
        duration = max(1, round((cue.end - cue.start) * 100))
        weights = [max(1, len(re.sub(r"\W", "", word))) for word in words]
        total_weight = sum(weights)
        word_durations = [max(1, int(duration * weight / total_weight)) for weight in weights]
        # Keep the karaoke total within the cue duration after minimum rounding.
        word_durations[-1] = max(1, duration - sum(word_durations[:-1]))
        karaoke = " ".join(f"{{\\k{span}}}{_ass_text(word)}" for span, word in zip(word_durations, words))
        lines.append(f"Dialogue: 0,{_ass_time(cue.start)},{_ass_time(cue.end)},Default,,0,0,0,,{karaoke}")
    return "\n".join(lines) + "\n"
