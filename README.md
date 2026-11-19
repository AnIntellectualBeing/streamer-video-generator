# GTA Streamer Face Clipper

`gta-streamer-face-clipper` is a command-line tool that turns a streamer's video, GTA gameplay, and optional SRT captions into one vertical MP4. It has no browser interface: an operator or AI agent gives it the input paths and it renders the finished clip.

## What it produces

- H.264 MP4 at 1080 × 1920 (9:16), 30 FPS by default; 60 FPS is optional.
- Streamer video at the top (760 px) and GTA gameplay at the bottom (1,160 px).
- Each panel is filled with its source video using a centered crop. There is no blurred fill or blank bars; the panels touch directly at the seam. Since landscape sources are cropped to fit portrait panels, inspect the result for cut-off faces, HUD, or action.
- Large uppercase green captions with a thick black outline pop over that seam, matching the supplied reference style.
- Each SRT cue appears as one uppercase phrase and briefly scales up when it starts. The tool does not estimate speech timing; accurate SRT timestamps are required for synchronization.
- Streamer and gameplay audio are mixed at separately configurable levels and limited to avoid clipping.
- Output duration is the shorter input's duration. Both videos start at their beginning.

The tool does not find streams or highlights, extract a facecam from a composite stream, detect faces, transcribe speech, synchronize independently recorded footage, or publish clips. Prepare aligned facecam and gameplay files and an accurately timed SRT file before rendering. For a repeatable end-to-end checklist, see [the clip workflow](docs/CLIP-WORKFLOW.md). A printable copy is available as [the PDF workflow guide](docs/GTA-Streamer-Face-Clipper-Guide.pdf).

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

Pass an ordinary UTF-8 SRT file. Keep cues short and accurately timed; each phrase pops in over the panel seam.

```srt
1
00:00:00,400 --> 00:00:01,500
That was way too close!

2
00:00:01,550 --> 00:00:02,400
Look at that car!
```

Caption text is uppercased. Each cue is shown as a single phrase at the panel seam; it is not karaoke word highlighting. The render is silent when neither input has audio. If both have audio, both tracks are mixed; adjust `--streamer-volume` and `--gameplay-volume` to favor speech.

## Troubleshooting

- `ffmpeg` or `ffprobe` not found: install FFmpeg, add its `bin` directory to `PATH`, and open a new terminal.
- `Unknown encoder 'libx264'`: install an FFmpeg build that includes `libx264`.
- Invalid SRT: use `HH:MM:SS,mmm --> HH:MM:SS,mmm` timestamps with caption text on the next line.
- Captions are not closely synchronized: split long dialogue into shorter cues and align their timestamps with the audio.
- The streamer and gameplay appear to start at different moments: trim both source files to the same start before running the command.
- Important content is cut off: the panels use a centered crop to avoid blur and bars. Reframe the input before rendering so the face, HUD, and gameplay action sit inside the center-safe area.
- The clip starts at different moments: the tool starts both files at timestamp zero and does not sync them. Trim both files to the same event before rendering.
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
