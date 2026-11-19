# Testing and sample render

The unit tests use Python's standard library:

```sh
python -m unittest discover -s tests -v
```

For an end-to-end render without personal footage, generate two short synthetic source clips with FFmpeg, then render them:

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

Render and inspect the output dimensions, frame rate, duration, audio, and caption placement:

```sh
python -m streamer_generator render --facecam sample-facecam.mp4 --gameplay sample-gameplay.mp4 --captions sample.srt --output output/sample-short.mp4 --fps 30
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,codec_type -show_entries format=duration -of json output/sample-short.mp4
```

The sample media is generated and should not be committed. The final visual check is to open the MP4 and inspect both the opening and a frame with active captions.
