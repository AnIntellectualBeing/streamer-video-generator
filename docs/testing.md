# Test and sample render

Run the unit tests:

```sh
python -m unittest discover -s tests -v
```

To check an actual render without using private footage, create two short synthetic source clips with FFmpeg:

```sh
ffmpeg -y -f lavfi -i "testsrc2=size=1280x720:rate=30:duration=3" -f lavfi -i "sine=frequency=440:duration=3" -c:v libx264 -pix_fmt yuv420p -c:a aac sample-facecam.mp4
ffmpeg -y -f lavfi -i "testsrc2=size=1920x1080:rate=30:duration=3" -f lavfi -i "sine=frequency=220:duration=3" -c:v libx264 -pix_fmt yuv420p -c:a aac sample-gameplay.mp4
```

Create `sample.srt`:

```srt
1
00:00:00,400 --> 00:00:02,600
The test render is ready!
```

Render and inspect dimensions, frame rate, duration, audio, and the phrase caption at the join between the two panels:

```sh
gta-streamer-face-clipper --facecam sample-facecam.mp4 --gameplay sample-gameplay.mp4 --captions sample.srt --output sample-short.mp4
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,codec_type -show_entries format=duration -of json sample-short.mp4
```

The sample videos are synthetic and should not be committed. Inspect a still frame to confirm the center crop fills each panel without blur or bars, the important subject remains visible, and the caption sits across the panel join.
