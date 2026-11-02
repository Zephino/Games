# Recording the gameplay clips

The clips on the homepage (`clips/<game>-1/2/3.mp4`, plus a `.webm` and a `.jpg` poster for each) are real gameplay, recorded from each game's own code. Re-record them when a game changes a lot.

## Godot games (Mythriven, The Last Wagon, Lastborn Colony)

These use Godot's **Movie Maker** mode, which renders every frame at a fixed 30 fps, so clips are smooth even on a slow machine. `trailer_driver.gd` replays timed input from a JSON file: clicks, key presses, pressing buttons by their label, auto-answering dialogs, setting a number box, and, for Lastborn Colony only, letting the game's own test bot choose each turn. The commands it understands are listed at the top of the script.

1. Work on a **copy** of the game (`git archive` it into a scratch folder). Never commit the driver to a game repo.
2. Copy `trailer_driver.gd` into the copy, and add it to `project.godot` under `[autoload]`:
   `TrailerDriver="*res://trailer_driver.gd"`
3. Import once, then record (Godot 4.7.2; `xvfb-run` provides a virtual screen):
   ```bash
   godot --headless --import --path .
   TRAILER_SCRIPT=/path/to/tools/clips/lastborn.json \
     xvfb-run -a -s "-screen 0 1280x720x24" godot --path . --write-movie out.avi --fixed-fps 30
   ```
   Mythriven must be the **debug** build that its own workflow publishes. Running from the editor binary like this is a debug run, so its heroes show up. A release build hides heroes whose mythology isn't checked yet.

The scripts: `mythriven-heracles.json`, `mythriven-cu-chulainn.json`, `lastwagon.json` and `lastborn.json`. Lastborn Colony uses map seed 4242, so its runs repeat exactly. The Last Wagon is random every run, so its script presses buttons by label and auto-answers events.

## Wave Defence

Wave Defence's web build is committed in its repo (`docs/`), so it's recorded in the browser with Playwright instead:

```bash
cd WaveDefence/docs && python3 -m http.server 8771 &
mkdir -p out/vid out/shots
node tools/clips/wavedefence-maze.js out    # builds a maze, then a wave
node tools/clips/wavedefence-clash.js out   # Clash mode with AI bots
```

Both print `MARK` times (seconds into the recording) for cutting.

## Cutting and encoding

Pick about 7–9 seconds per clip, then encode it at 960×540 with no audio, as MP4 (H.264, plays everywhere) and WebM (VP9, used when supported), plus a poster image:

```bash
ffmpeg -ss START -t LENGTH -i out.avi -an -vf "scale=960:540:flags=lanczos,fps=30" \
  -c:v libx264 -preset slow -crf 27 -pix_fmt yuv420p -movflags +faststart clips/NAME.mp4
ffmpeg -i clips/NAME.mp4 -an -c:v libvpx-vp9 -b:v 0 -crf 36 -row-mt 1 clips/NAME.webm
ffmpeg -ss 0.4 -i clips/NAME.mp4 -frames:v 1 -q:v 4 clips/NAME.jpg
```

Add a `crop=` before `scale=` to zoom in. The current Mythriven clips use `crop=922:519:115:65`, and the Lastborn Colony clips use `crop=892:502:224:150`, which hides the side panels.

After replacing clips, bump the cache version in `index.html` (see `CLAUDE.md`).
