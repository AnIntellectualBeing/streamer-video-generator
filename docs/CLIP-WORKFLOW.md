# Make a facecam-over-GTA vertical clip

This guide uses the local `gta-streamer-face-clipper` command. The command renders two already-prepared, synchronized videos; it does not find streams, detect a face, separate a webcam from a finished stream layout, generate transcripts, or publish the finished MP4.

## 1. Prepare the source footage

Use footage you own or are authorized to record, edit, and publish. Keep the original source file private. Select the moment you want, including enough lead-in for the reaction or dialogue to make sense.

Prepare two video files for the same time range:

1. `facecam.mp4`: streamer camera footage, with the face positioned near the center.
2. `gameplay.mp4`: GTA gameplay footage, with the important character, vehicle, HUD, and action near the center.

Both files must start at the same moment and cover the same duration. If they come from separate recordings, synchronize them before rendering. The renderer starts each file at timestamp zero and cannot correct drift.

If your capture has separate camera and gameplay tracks, export those tracks separately. If you only have one composited stream recording, crop each region with FFmpeg using the layout's measured pixel coordinates. Replace `CAM_W`, `CAM_H`, `CAM_X`, `CAM_Y` and the gameplay values with coordinates measured from your own recording:

```powershell
ffmpeg -ss 00:01:23.400 -i source.mp4 -t 8.2 -vf "crop=CAM_W:CAM_H:CAM_X:CAM_Y" -an -c:v libx264 -crf 18 facecam.mp4
ffmpeg -ss 00:01:23.400 -i source.mp4 -t 8.2 -vf "crop=GAME_W:GAME_H:GAME_X:GAME_Y" -an -c:v libx264 -crf 18 gameplay.mp4
```

Those commands are templates, not automatic scene detection. Measure coordinates from the actual source resolution. A camera box already burned over gameplay cannot be removed from the gameplay pixels; use a clean gameplay track or crop around the box when the important action remains visible.

## 2. Write or prepare captions

Save captions as UTF-8 SRT. Use short phrases with accurate start and end times relative to the beginning of the trimmed clips. The renderer uppercases each phrase, uses bold green text with a thick black outline, and places it across the join between panels.

```srt
1
00:00:00,000 --> 00:00:00,800
WAIT, WHAT?

2
00:00:00,800 --> 00:00:01,700
THAT WAS CLOSE!
```

Each cue pops in as a phrase; there is no automatic transcription or word-by-word karaoke timing. Review the SRT against the audio before rendering. If you do not have captions, omit `--captions`.

## 3. Install and render

Install Python 3.10+, FFmpeg (including FFprobe and `libx264`), then install this repository:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Render with the CLI:

```powershell
gta-streamer-face-clipper `
  --facecam facecam.mp4 `
  --gameplay gameplay.mp4 `
  --captions captions.srt `
  --output output\gta-streamer-short.mp4 `
  --fps 30 `
  --style bold `
  --streamer-volume 1.0 `
  --gameplay-volume 0
```

Use `--fps 60` when both source videos support it and you want a 60 FPS export. Audio volume values range from `0` to `2`. To retain gameplay sound, set `--gameplay-volume` above zero. The tool mixes available audio tracks and applies a limiter. It does not invent missing audio.

## 4. Review the exported video

The MP4 should be 1080 × 1920 (9:16), H.264, and the shorter of the two input durations. The facecam fills the upper 760 px; gameplay fills the lower 1,160 px. Both use centered aspect-ratio crops, so outer edges are intentionally trimmed. No blur or letterbox fill is added.

Inspect the beginning, middle, and end of the MP4. Confirm:

- The streamer's face stays inside the top panel and is not cut off.
- The important gameplay action and any HUD you need stay inside the lower panel.
- The two shots show the same moment and do not drift out of sync.
- Captions are present at the right moments, readable, and do not cover the face.
- Streamer speech is clear and the combined audio is not distorted.

Check file details with FFprobe:

```powershell
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,codec_type -show_entries format=duration -of json output\gta-streamer-short.mp4
```

## Common fixes

- **Face or game action is clipped:** Reframe the corresponding input so the important area is in the center. The current layout uses a centered crop; it does not track a moving face or gameplay character.
- **Captions are mistimed:** Correct SRT cue times against the trimmed clip. Times are relative to the start of each input.
- **Audio is doubled or too loud:** Lower one track with `--streamer-volume` or `--gameplay-volume`; set an unused track to `0`.
- **Input durations differ:** The output ends with the shorter input. Trim or export both inputs to the intended common duration.
- **FFmpeg reports an encoder or filter error:** Check `ffmpeg -version` and confirm the installed build includes `libx264` and the subtitles filter (libass).

The renderer saves output only to the path you provide. It makes no network requests and does not post to social accounts.
