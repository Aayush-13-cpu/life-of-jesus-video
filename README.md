# Making Animated Videos with Code

### A field guide to this project, written so you can build your own

This repository makes narrated, animated Bible videos with **free, open-source tools**, and renders them on
**GitHub's computers instead of yours**. It contains:

- **The Life of Jesus**: a 2-minute horizontal timeline video (`script.json`, `build.py`).
- **40 story Shorts**: vertical 30–40 second animations in two visual styles (`shorts/`).

Read it like a short book. Part One explains the ideas, Part Two walks through how this project uses them, Part
Three shows how to change it, and Part Four shows how to start something new of your own. Every code snippet
comes from this repository, so you can open the file and see it in context.

---

## Contents

**Part One: The ideas**
1. [A video is a web page that plays itself](#1-a-video-is-a-web-page-that-plays-itself)
2. [Drawing with SVG](#2-drawing-with-svg)
3. [Moving things with GSAP](#3-moving-things-with-gsap)
4. [HyperFrames: turning the page into an MP4](#4-hyperframes-turning-the-page-into-an-mp4)
5. [A voice from text: Kokoro](#5-a-voice-from-text-kokoro)
6. [Sound with FFmpeg](#6-sound-with-ffmpeg)
7. [Someone else's computer: GitHub Actions](#7-someone-elses-computer-github-actions)

**Part Two: How this project works**

8. [The map of files](#8-the-map-of-files)
9. [The timeline video, step by step](#9-the-timeline-video-step-by-step)
10. [The story Shorts, step by step](#10-the-story-shorts-step-by-step)
11. [The silhouette kit](#11-the-silhouette-kit)
12. [The animation interpreter](#12-the-animation-interpreter)
13. [The cloud pipeline](#13-the-cloud-pipeline)

**Part Three: Changing it**

14. [Write a new story](#14-write-a-new-story)
15. [Add a prop, an action or a style](#15-add-a-prop-an-action-or-a-style)
16. [Checking your work](#16-checking-your-work)
17. [Mistakes we made, and what they teach](#17-mistakes-we-made-and-what-they-teach)

**Part Four: On your own**

18. [Start a new project from nothing](#18-start-a-new-project-from-nothing)
19. [Continue on another computer](#19-continue-on-another-computer)
20. [Glossary and licences](#20-glossary-and-licences)

---

# Part One: The ideas

## 1. A video is a web page that plays itself

A web browser is a very good drawing machine. It draws text, shapes, colours and images, and it can move them. If
you could photograph a web page 30 times a second while its animations play, you would have a video.

That's the whole trick of this project:

```
 words you write ─► a web page with animations ─► a browser photographs every frame ─► MP4
```

Why do it this way instead of in a video editor?

- **Text is precise and repeatable.** Change one word in `stories.json` and every video that uses it updates.
- **Code can make 40 videos as easily as 1.** You describe a pattern once and reuse it.
- **Everything is free.** Browsers, the animation library, the voice, the encoder: all open source.

The rest of Part One introduces the pieces one at a time.

## 2. Drawing with SVG

SVG ("Scalable Vector Graphics") describes pictures as shapes, written as text. This draws a sun:

```html
<svg viewBox="0 0 1080 1920">
  <circle cx="820" cy="470" r="58" fill="#fff4d6"/>
</svg>
```

Three ideas carry you most of the way:

- **The coordinate system.** `viewBox="0 0 1080 1920"` says: this drawing is 1080 wide and 1920 tall (a vertical
  Short). `x` grows to the right, and **`y` grows downward**, so `y=0` is the top of the screen.
- **Paths.** `<path d="M-30 0 C-28 -60 ... Z"/>` draws any outline. `M` moves the pen, `L` draws a line, `C` and
  `Q` draw curves, `Z` closes the shape. The robe of every figure in this project is one path.
- **Groups and transforms.** `<g transform="translate(540,1390) scale(1.6)">…</g>` draws everything inside the
  group shifted to (540, 1390) and 1.6 times bigger. Draw a figure once around (0, 0), then place it anywhere.

## 3. Moving things with GSAP

[GSAP](https://gsap.com) is a JavaScript animation library. You give it an element, the values to change, and
how long to take:

```js
const tl = gsap.timeline({ paused: true });
tl.to("#boat-b", { rotation: 4, duration: 1.2, ease: "sine.inOut" }, 3.0);
```

Read it as: *on the timeline, at 3.0 seconds, rotate the boat to 4 degrees over 1.2 seconds, easing in and out.*

- **A timeline** is a list of animations placed at exact times. The last number (`3.0`) is the start time.
- **`to`** animates from the current value; **`fromTo`** sets both ends (safer when the playhead can jump);
  **`set`** changes a value instantly.
- **Ease** is the feel of the motion: `"none"` is mechanical, `"power2.out"` starts fast and settles,
  `"sine.inOut"` is gentle at both ends.
- **`repeat` and `yoyo`** make a back-and-forth (a rocking boat, a flickering flame). Here every repeat is
  *finite*, for a reason Chapter 4 explains.
- **`paused: true`** matters: the timeline must not play by itself, because HyperFrames will move it to each frame.

## 4. HyperFrames: turning the page into an MP4

[HyperFrames](https://github.com/heygen-com/hyperframes) (open source, Apache 2.0, from HeyGen) opens your page in
a hidden Chrome browser, moves the timeline to frame 0, takes a picture, moves to frame 1, takes a picture, and so
on. FFmpeg then joins the pictures and the sound into an MP4.

For that to work, a page has to follow a small contract:

```html
<div id="root" data-composition-id="story-short" data-start="0" data-duration="35.9"
     data-width="1080" data-height="1920">
  <section id="beat-0" class="clip" data-start="0" data-duration="8.4"> … scene 1 … </section>
  <section id="beat-1" class="clip" data-start="8.4" data-duration="7.9"> … scene 2 … </section>
  <audio id="voice" src="assets/voice.wav" data-start="0" data-duration="35.9"></audio>
</div>
<script>
  window.__timelines = window.__timelines || {};
  window.__timelines["story-short"] = tl;   // the key must equal data-composition-id
</script>
```

- **`data-start` / `data-duration`** say when each piece is visible (or audible). HyperFrames shows and hides
  clips for you.
- **The timeline is registered** under the composition's id, *after* every tween is added.
- **Determinism.** HyperFrames may photograph frames in any order, so frame 412 must look the same every time.
  That means: no clock (`Date.now()`), no unseeded `Math.random()`, no infinite repeats, nothing loading in the
  middle. This project uses a seeded random generator (`kit.rng`) for stars and raindrops for exactly this reason.
- **Two commands check a page:** `npx hyperframes lint` (rules, instant) and `npx hyperframes render` (the video).

## 5. A voice from text: Kokoro

[Kokoro](https://github.com/thewh1teagle/kokoro-onnx) is a small open-source text-to-speech model (Apache 2.0, so
monetized videos are fine). It runs on an ordinary CPU:

```python
from kokoro_onnx import Kokoro
k = Kokoro("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
audio, sample_rate = k.create("Peace, be still.", voice="af_heart", speed=0.94, lang="en-us")
```

`af_heart` is its best-rated English voice, and `speed` below 1 slows it down. The important trick: **the voice
decides the timing.** The project generates each scene's narration first, measures how long it is, and only then
decides how long the scene lasts. Nothing is timed by hand.

## 6. Sound with FFmpeg

[FFmpeg](https://ffmpeg.org) is the Swiss-army knife of audio and video. Two uses here:

- **Generating music from maths.** `aevalsrc` turns a formula into sound. The music bed is four soft chords (C, G,
  Am, F), each swelling in and out over 16 seconds, plus a gentle plucked note every 2 seconds, then smoothed with
  a low-pass filter and an echo. See `music()` in `build.py`. No licensed track needed.
- **Loudness.** YouTube plays everything at about **−14 LUFS** (a loudness measure). If a video is quieter, it
  just sounds weak next to others. After rendering, the workflow runs FFmpeg's `loudnorm` filter to land on −14.

## 7. Someone else's computer: GitHub Actions

GitHub Actions runs scripts on GitHub's computers whenever you push. A *workflow* file in
`.github/workflows/` lists the steps: install tools, run your build, upload results. For **public repositories it
is free with no minute limit**. That's why this laptop never had to render anything.

The finished videos are attached to a **GitHub Release**, a downloads page anyone can open from any device:
`https://github.com/Aayush-13-cpu/life-of-jesus-video/releases`.

---

# Part Two: How this project works

## 8. The map of files

```
script.json                 the timeline video's 13 scenes (year, title, verse, icon, narration)
build.py                    narrates script.json and writes its HyperFrames page
test_build.py               checks for the timeline video
shorts/
  stories.json              20 stories, silhouette style
  stories_parchment.json    20 stories, illuminated-parchment style
  kit.py                    the drawing kit: skies, landscapes, props, figures, effects, styles
  build_short.py            narrates one story and writes its HyperFrames page (+ the animation interpreter)
  test_shorts.py            checks every story before any rendering
  render.txt                which story ids the next cloud run renders
  fetch.py                  downloads a finished batch to shorts/output/ (optional)
fonts/                      Cinzel and Cormorant Garamond (SIL Open Font License)
.github/workflows/
  render.yml                renders the timeline video
  shorts.yml                renders the Shorts in parallel and publishes them to a Release
```

## 9. The timeline video, step by step

`build.py` does four things, in order:

1. **Narrate.** `narrate()` speaks every scene's `narration` with Kokoro and measures each clip.
2. **Time.** `timings()` gives each scene `0.7 s + narration + 1.4 s` (never less than 5 s). Starts are rounded
   at every step so one scene ends exactly where the next begins. A test checks that.
3. **Music.** `music()` generates the bed to the exact total length.
4. **Write the page.** `render_html()` fills `TEMPLATE` with one `<section class="clip">` per scene, the
   timeline bar with a dot per event, and the two audio tracks.

The page's script then builds the animation: each icon's lines *draw themselves* (every path has
`pathLength="1"`, and its `strokeDashoffset` goes from 1 to 0), the year rises in, the title's words appear one
after another (`stagger`), the verse fades up, and the gold progress line grows to the current dot.

## 10. The story Shorts, step by step

A story is a list of **beats**. Each beat is one sentence of narration plus the scene that acts it out:

```json
{"say": "And he arose, and rebuked the wind, and said unto the sea: Peace, be still.",
 "sky": "storm", "ground": "sea", "fx": ["rain"],
 "cast": [{"k": "boat", "x": 540, "y": 1350, "s": 1.35, "acts": [{"do": "rock", "amp": 3, "period": 2.6}]},
          {"k": "jesus", "in": 0, "x": 90, "y": -40, "s": 0.8, "flip": true, "acts": [{"do": "raise", "at": 0.4}]}]}
```

`build_short.py <story-id>` turns that into a page:

1. **Narrate** every beat (`narrate`) and time the beats to the voice (`timings`).
2. **Captions.** `chunks()` cuts each sentence into blocks of up to 5 words, breaking after punctuation, and
   `captions()` spreads them across the narration in proportion to their length. Most Shorts are watched muted,
   so captions carry the story.
3. **Scenes.** `compose_beat()` asks the kit for the sky, the ground, each cast member and the effects, and
   collects their *acts* as plain instructions with absolute times.
4. **The page.** `render_html()` writes it all into `TEMPLATE`: the beat sections, the captions, a title card for
   the first 3 seconds, the verse reference on the last beat, the voice and the music.
5. **Camera.** Every beat is framed about 25% tighter on the action and pushes in slowly (`scale 1.24 → 1.31`),
   which keeps a static drawing feeling alive.

## 11. The silhouette kit

`shorts/kit.py` draws everything. A few ideas make it work:

- **Everything stands on the ground line.** Each figure and prop is drawn around the point where it touches the
  ground, `(0, 0)`. Near characters stand at `y = 1390` (`FEET`), the horizon is at `1300` (`HZ`).
- **Two groups per character.** `place()` wraps each drawing twice:

  ```
  <g id="b2-c3"   transform="translate(x,y) scale(s)">   ← outer: moves across the screen (walk, run, climb)
     <g id="b2-c3-b" class="body"> … </g>                ← inner: bends in place (kneel, lie, rock, grow)
  </g>
  ```

  Splitting "where it is" from "how it bends" keeps the two kinds of motion from fighting each other.
- **Arms are their own groups** (`-al`, `-ar`) rotating at the shoulder, so a figure can raise, reach or bless.
- **Nesting.** `"in": 0` draws a figure *inside* cast member 0, so people in a boat rock with the boat.
- **Faces are never drawn.** Jesus is a figure surrounded by a soft light (`-glow`), never an invented face.
- **Styles.** `kit.use("parchment")` swaps the whole palette: skies, ink colour, rain, rays and the rest. The page
  colours (captions, vignette) live in `CSS` in `build_short.py`.

## 12. The animation interpreter

Stories don't contain JavaScript. They contain *verbs*: `walk`, `kneel`, `rock`, `grow`, `tint`… The page holds
a small dictionary `F` that turns each verb into GSAP calls:

```js
walk: a => { tl.to(a.t, { x: a.to, duration: a.d, ease: "sine.inOut" }, a.s); bob(a.t, a.s, a.d, 0.62, 7); },
kneel: a => tl.to(a.t + "-b", { scaleY: 0.68, duration: 0.7, ease: "power2.out" }, a.s),
```

`a.t` is the element, `a.s` the start time, `a.d` the duration. `walk` moves the outer group and bobs the
inner one. `kneel` squashes the inner group from the feet up. To add a verb, you add one line here and use it in a
story (Chapter 15).

## 13. The cloud pipeline

`.github/workflows/shorts.yml` runs on every push that changes `shorts/`:

1. **plan**: reads `shorts/render.txt` into a list and creates a Release named `shorts-<run number>`.
2. **render**, once per story, all in parallel (a *matrix*): install Node, Python and FFmpeg; download Kokoro
   (cached between runs); run `test_shorts.py`; build the page; `hyperframes lint`; `hyperframes render`;
   loudness-normalize; save four preview stills; upload everything to the Release.

If anything fails, the error is printed as an *annotation* that anyone can read on the run page, without logging
in.

**To render something:** edit `shorts/render.txt` (one story id per line), commit, push. **To download:** open
the Releases page and take the newest `shorts-N`.

---

# Part Three: Changing it

## 14. Write a new story

1. **Pick the moment and the line.** One story, 4 beats, about 80–120 words. Open with a hook for adults (a
   situation, a stake), quote the King James Version exactly where you quote Scripture, and end with one line that
   speaks to grown-up life.
2. **Add it** to `shorts/stories.json` (silhouette) or `stories_parchment.json` (parchment, add
   `"style": "parchment"`). Give it a unique `id`, a `title`, and a `ref` (shown at the end).
3. **Stage each beat.** Choose a `sky` (`dawn day dusk night storm`) and a `ground`
   (`hills field desert city sea garden`). Add the `cast`:

   | Field | Meaning |
   |---|---|
   | `k` | what it is: a person (`jesus man woman widow child shepherd elder angel`), `crowd`, or a prop (`boat tree house rock jar basket sheep pig table stone coin seed plant lily thorns net fish fire star chest well lamp cross mat stones birds`) |
   | `x`, `y` | where it touches the ground (`y` defaults to 1390) |
   | `s` | size (people look right around 1.5–1.6) |
   | `flip` | face left instead of right |
   | `in` | the index of another cast member to ride inside (people in a boat) |
   | `acts` | what it does: `{"do": "walk", "to": 760, "at": 0.5, "dur": 3}` (`at` = seconds into the beat) |

   Verbs: `walk run climb` (need `to`), `raise bless reach lower`, `kneel stand lie`, `appear vanish`,
   `rock drift` (`amp`, `period`), `fly` (`to`, `toy`), `grow`, `collapse`, `roll` (`to`, `deg`), `sink` (`by`),
   `tint` (`color`, for jars), `flicker` (fire and lamps).
4. **Add effects** if you like: `"fx": ["rain", "lightning", "rays", "sparkle"]`.
5. **Check it:** `python shorts/test_shorts.py`, then put its id in `render.txt` and push.

## 15. Add a prop, an action or a style

- **A prop:** add an entry to `PROPS` in `kit.py`, drawn around `(0, 0)` with `0` at the ground, in SVG path
  language. Use `{pid}` in an id if an action needs to find a part (see `jar` and its `-liq` liquid).
- **An action:** add one line to `F` in the page script in `build_short.py`. The test discovers it automatically.
- **A style:** add a palette to `STYLES` in `kit.py` and a matching entry to `CSS` in `build_short.py`, then set
  `"style": "<name>"` on a story.

## 16. Checking your work

| Check | Command | What it catches |
|---|---|---|
| Story check | `python shorts/test_shorts.py` | unknown props or verbs, bad `in` links, duplicate ids, length over the Shorts limit, the wrong palette |
| Timeline check | `python test_build.py` | timing gaps, duplicate ids, dots off the bar, forbidden animations |
| HyperFrames rules | `npx hyperframes lint` (in a built folder) | anything the renderer would refuse |
| The real thing | a cloud run, then watch the MP4 | everything else: always watch with sound before publishing |

## 17. Mistakes we made, and what they teach

Every one of these really happened while building this project:

- **Letter-spacing animation was rejected** by `hyperframes lint`: it snaps to whole pixels and stutters frame by
  frame. *Animate transforms (`x`, `y`, `scale`, `rotation`) and `opacity`; they move smoothly between pixels.*
- **The timeline dots ran off the screen.** They were positioned from the page's edge *inside* a bar that was
  already offset. *When something is inside a positioned container, measure from the container.*
- **The sleeping Jesus stuck out of the boat like a pole.** His glow was inside the group being rotated, so it
  pivoted around the glow's box instead of his feet. *Keep decorations out of the group you rotate.*
- **Scenes overlapped by a hair.** Adding decimals drifts (`0.1 + 0.2 ≠ 0.3` in computers). *Round at every step.*
- **The music was inaudible** and the video too quiet. *Measure loudness; don't trust your speakers.*
- **A downloaded zip got committed** to the public repo. *Check `git status` before every commit; ignore `*.zip`.*

---

# Part Four: On your own

## 18. Start a new project from nothing

The smallest working video, about 15 lines. Make a folder with this `index.html`:

```html
<!doctype html>
<html><head>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style> body{margin:0} #root{position:relative;width:1080px;height:1920px;background:#141a33;color:#fff}
  #t{position:absolute;top:800px;width:100%;text-align:center;font:96px serif} </style>
</head><body>
<div id="root" data-composition-id="hello" data-start="0" data-duration="4" data-width="1080" data-height="1920">
  <div id="t" class="clip" data-start="0" data-duration="4">Be still.</div>
</div>
<script>
  const tl = gsap.timeline({ paused: true });
  tl.fromTo("#t", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 1.2, ease: "power2.out" }, 0.3);
  window.__timelines = { hello: tl };
</script>
</body></html>
```

Then `npx hyperframes lint` and `npx hyperframes render --output hello.mp4` (needs Node 22+ and FFmpeg). Grow it
the way this project grew: add a voice (Chapter 5), let the voice set the timing, add SVG scenes (Chapter 2), move
them (Chapter 3), and when it works, put it in a GitHub repo with a workflow (Chapter 13) so a free cloud computer
renders it.

## 19. Continue on another computer

1. Install [Git](https://git-scm.com), then `git clone https://github.com/Aayush-13-cpu/life-of-jesus-video.git`.
2. Edit, then `git add -A`, `git commit -m "what you changed"`, `git push`. The cloud renders it.
3. Download results from the Releases page. Rendering never needs your own computer.
4. To run the checks locally you need Python 3.11 (`pip install numpy`) and, for `lint`, Node 22+.

## 20. Glossary and licences

| Word | Meaning |
|---|---|
| Composition | One HyperFrames page that becomes one video |
| Clip | An element with `data-start` / `data-duration` |
| Beat | One sentence of narration and the scene that acts it out |
| Timeline | GSAP's list of timed animations |
| Tween | A single animation on the timeline |
| Easing | The feel of a motion (sudden, gentle, bouncy) |
| Deterministic | The same frame always looks the same |
| Matrix job | One workflow step repeated in parallel for each item in a list |
| Release | A GitHub page of downloadable files |
| LUFS | A loudness unit; YouTube targets −14 |

| Part | Licence |
|---|---|
| HyperFrames | Apache 2.0 |
| GSAP | free standard licence (core library used here) |
| Kokoro voice | Apache 2.0 |
| Fonts (Cinzel, Cormorant Garamond) | SIL Open Font License |
| Scripture | King James Version, public domain |
| Music | generated in this repository |
