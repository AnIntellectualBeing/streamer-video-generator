# GTA Streamer Face Clipper

`gta-streamer-face-clipper` is a command-line tool that turns a streamer's video, GTA gameplay, and optional SRT captions into one vertical MP4. It has no browser interface: an operator or AI agent gives it the input paths and it renders the finished clip.

## What it produces

- H.264 MP4 at 1080 × 1920 (9:16), 30 FPS by default; 60 FPS is optional.
- The full streamer video at the top and the full gameplay frame at the bottom.
- Each source is scaled down to fit its panel. It is not stretched, zoomed, or cropped; unused space is filled with a dark background.
- Captions stay inside a separate center divider, so they do not cover the streamer or gameplay.
- Word highlighting follows the SRT cue timing. Timing inside each cue is estimated from word length, so short, accurately timed cues give the best result.
- Streamer and gameplay audio are mixed at separately configurable levels and limited to avoid clipping.
- Output duration is the shorter input's duration. Both videos start at their beginning.

The tool does not detect faces, find highlights, transcribe speech, align independently recorded footage, or publish clips. Trim the two videos to the same moment and provide captions when needed.

## Requirements

- Python 3.10 or newer
- FFmpeg and FFprobe on `PATH`; FFmpeg must include `libx264`
- Windows, macOS, or Linux

Install FFmpeg:

- Windows: install an FFmpeg build containing `ffmpeg.exe` and `ffprobe.exe`, and add its `bin` directory to `PATH`.
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt update && sudo apt install ffmpeg`

Check the installation:

```sh
ffmpeg -version
ffprobe -version
```

## Install the command

From the repository directory:

```sh
python -m venv .venv
```

Activate it, then install the local command:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

```sh
# macOS / Linux
source .venv/bin/activate
python -m pip install -e .
```

There are no Python runtime dependencies or cloud credentials.

## Run a clip

```sh
gta-streamer-face-clipper \
  --facecam input/streamer.mp4 \
  --gameplay input/gta-gameplay.mp4 \
  --captions input/captions.srt \
  --output output/clip.mp4
```

On Windows PowerShell, use backticks for line continuation or run the command on one line:

```powershell
gta-streamer-face-clipper --facecam input\streamer.mp4 --gameplay input\gta-gameplay.mp4 --captions input\captions.srt --output output\clip.mp4
```

Captions and optional adjustments can be omitted:

```sh
gta-streamer-face-clipper --facecam streamer.mp4 --gameplay gameplay.mp4 --output clip.mp4 --fps 60 --streamer-volume 1.0 --gameplay-volume 0.35
```

Use `gta-streamer-face-clipper --help` to see all options. Caption styles are `bold`, `clean`, and `neon`; audio volumes accept values from 0 to 2.

## Caption file

Pass an ordinary UTF-8 SRT file. Keep captions short and give each phrase its own accurately timed cue for better word highlighting.

```srt
1
00:00:00,400 --> 00:00:01,500
That was way too close!

2
00:00:01,550 --> 00:00:02,400
Look at that car!
```

The render is silent when neither input has audio. If both have audio, both tracks are mixed; adjust `--streamer-volume` and `--gameplay-volume` to favor speech.

## Troubleshooting

- `ffmpeg` or `ffprobe` not found: install FFmpeg, add its `bin` directory to `PATH`, and open a new terminal.
- `Unknown encoder 'libx264'`: install an FFmpeg build that includes `libx264`.
- Invalid SRT: use `HH:MM:SS,mmm --> HH:MM:SS,mmm` timestamps with caption text on the next line.
- Captions are not closely synchronized: split long dialogue into shorter cues and align their timestamps with the audio.
- The streamer and gameplay appear to start at different moments: trim both source files to the same start before running the command.
- The video looks smaller inside its panel: the tool preserves the entire frame instead of zooming or cutting off the edges. This is expected for source footage with a different shape from the panel.
- FFmpeg fails or runs out of space: check the reported FFmpeg error and ensure the destination drive has room for the MP4.

## Development

Run the automated checks:

```sh
python -m unittest discover -s tests -v
```

The tests use synthetic local media only. Do not add private streamer footage, credentials, or payment data to this repository.

## Privacy

Rendering happens locally. The tool does not upload footage, make network requests, or need an API key.

## License

MIT. See [LICENSE](LICENSE).
