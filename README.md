# Streamer Shorts Studio

A standalone, local-first tool for turning a streamer camera and gameplay recording into a vertical 1080 × 1920 short. The browser studio and the command-line renderer use the same FFmpeg pipeline. Video files remain on your computer; the web server binds to loopback and does not send footage to a cloud service.

## What it can do

- Stack facecam above full-width gameplay without stretching either source.
- Adjust the vertical split and the horizontal/vertical crop focus for both sources.
- Import or edit SRT subtitles; render outlined captions with word-by-word highlight timing.
- Adjust streamer and gameplay volume independently, including muting either track.
- Render H.264 MP4 at 30 or 60 FPS, using the shorter source duration.
- Preview the layout in the browser, see upload/render progress, and download the finished video.
- Run headless from the command line for repeatable batches.

The crop controls use a manually selected focal point. The application does not use face recognition, automatic action detection, speech recognition, or automatic clip selection. Word highlight timing is estimated across each supplied SRT cue; provide well-timed cues for the best synchronization.

## Requirements

- Python 3.10 or newer
- FFmpeg and FFprobe on `PATH`, with the `libx264` encoder enabled
- `pip` for the browser interface dependencies

### Install FFmpeg

- **Windows:** install a current FFmpeg build that includes `ffmpeg.exe` and `ffprobe.exe`, then add its `bin` directory to `PATH`.
- **macOS:** `brew install ffmpeg`
- **Ubuntu/Debian:** `sudo apt update && sudo apt install ffmpeg`

Confirm both commands work before rendering:

```sh
ffmpeg -version
ffprobe -version
```

## Install

From this directory:

```sh
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```sh
# macOS / Linux
source .venv/bin/activate
```

Install the browser mode dependencies (the CLI renderer itself uses the Python standard library):

```sh
python -m pip install -r requirements.txt
```

## Browser workflow

```sh
python -m streamer_generator serve
```

Open <http://127.0.0.1:8765>. Upload a facecam recording and GTA gameplay, set the split and crop focal points, choose a caption look and frame rate, adjust the two audio tracks, then generate. Import an SRT or edit the SRT text area directly. The render appears as an MP4 download when it finishes.

The local interface accepts MP4, MOV, MKV, WebM, and M4V files. The default maximum is 1.5 GB per source video. Change it with `STREAMER_GENERATOR_MAX_UPLOAD_BYTES`; set a private scratch location with `STREAMER_GENERATOR_JOBS_DIR`. Jobs and source uploads are removed after 24 hours on the next launch.

## Command-line workflow

```sh
python -m streamer_generator render \
  --facecam examples/facecam.mp4 \
  --gameplay examples/gameplay.mp4 \
  --captions examples/captions.srt \
  --output output/streamer-short.mp4 \
  --style bold \
  --facecam-height 768 \
  --fps 60 \
  --streamer-volume 1.0 \
  --gameplay-volume 0.35 \
  --facecam-focus 50,42 \
  --gameplay-focus 50,55
```

Omit `--captions` for a clean video. Focus values are horizontal and vertical percentages from 0 to 100. The supported facecam heights are 576, 672, 768, 864, and 960 pixels; gameplay fills the remainder of the 1920-pixel canvas.

View all options with:

```sh
python -m streamer_generator --help
python -m streamer_generator render --help
```

## Caption format

Captions use ordinary SRT timing. The renderer keeps each cue's start and end times and apportions its word highlight spans across that interval based on word length. For accurate word sync, split dialogue into short SRT cues and align those cue times to the speech.

```srt
1
00:00:00,400 --> 00:00:01,900
That was way too close!
```

Styles are `bold`, `clean`, and `neon`. Text is centered in the lower portion of the video with an outline and safe side margins.

## Configuration

Copy `.env.example` to `.env` if you want to keep local settings nearby. The app does not require an API key or any cloud account. Shell environment variables take effect when starting the command:

| Variable | Default | Purpose |
| --- | --- | --- |
| `STREAMER_GENERATOR_HOST` | `127.0.0.1` | Local interface host; loopback values only |
| `STREAMER_GENERATOR_PORT` | `8765` | Local interface port |
| `STREAMER_GENERATOR_JOBS_DIR` | `~/.streamer-video-generator/jobs` | Upload, scratch, and output directory |
| `STREAMER_GENERATOR_MAX_UPLOAD_BYTES` | `1500000000` | Per-video upload limit |

The `.env` file is a template only; environment-file loading is not automatic. Set variables in your shell or configure them in your process manager.

## Example workflow

1. Trim or select the same moment in the facecam and gameplay recordings before importing. The output duration is the shorter source duration; the renderer starts both inputs at their beginning.
2. Upload both files and use the live canvas to set the facecam size and focal points.
3. Import an SRT file or edit the text area. Keep the timing lines and update the dialogue.
4. Choose 30 FPS for standard footage or 60 FPS when both sources contain smooth high-frame-rate motion.
5. Balance the two audio sources. The mixed output is limited to prevent peaks from clipping.
6. Render and check the downloaded MP4 in a player before posting.

## Troubleshooting

- **`ffmpeg was not found` / `ffprobe was not found`:** install FFmpeg and restart the terminal after editing `PATH`.
- **`Unknown encoder 'libx264'`:** use an FFmpeg distribution built with `libx264`.
- **Invalid subtitle cue:** use SRT timestamp lines in `HH:MM:SS,mmm --> HH:MM:SS,mmm` form, with text below each line.
- **Audio is silent:** verify the source tracks contain audio; set their volume above zero. Silent sources are allowed and mixed as silence.
- **Face or gameplay subject is cut off:** move that source's horizontal/vertical focus controls and inspect the preview before rendering.
- **Output starts at the wrong point:** trim the source files to the same moment first. This app does not align separate recordings or detect a shared start time.
- **Upload is rejected:** each source has a configurable size limit. Increase `STREAMER_GENERATOR_MAX_UPLOAD_BYTES` if the local disk has enough free space.
- **Render fails or is slow:** check the error shown in the local studio, available disk space, and the source codecs. The browser renderer processes one job at a time.

## Development checks

```sh
python -m unittest discover -s tests -v
```

An actual FFmpeg integration check can be run with generated test sources; see `docs/testing.md`. Do not add private footage or credentials to the repository.

## Privacy and safety

The browser mode is for local use and rejects remote bind addresses. Do not put this app behind a public URL without adding authentication, upload quotas, and isolated job storage. The ignored job directory contains source footage and rendered videos; review before backing it up or sharing it.

## License

MIT. See [LICENSE](LICENSE).
