"""stories.json -> one vertical (1080x1920) HyperFrames Short per story: Kokoro narration, music bed, captions and
paper pop-up scenes (paper.py, paper.js) that act out each beat.

  python shorts/build_short.py <story-id>        -> shorts/build/<story-id>/ (index.html, assets/, fonts/)
  cd shorts/build/<story-id> && npx hyperframes render --output <file>.mp4
"""
import html, json, os, re, shutil, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from build import music, word_times  # the same generated piano-and-pad bed as the long video; Whisper word timing
import paper  # the paper pop-up pages, shared by every video (paper.py, paper.js)

LEAD, TAIL, END = 0.35, 0.6, 1.2  # silence before/after each beat's narration; music-only ending
XF = 0.3                            # the dissolve between two beats in the same setting (a new setting turns the page)
WORLD = "levant"                    # paper.py village architecture: flat roofs, domes and palms
VOICE, SPEED = "af_heart", 0.94
MAX_TOTAL = 59.0                    # YouTube Shorts must stay under 60 s
WPS = 2.55                          # measured-style estimate of Kokoro's pace at SPEED, for checks before TTS


def all_stories():
    """Every story: the silhouette set (stories.json), the parchment set (stories_parchment.json) and the library
    that ./generate.py works through (stories_library.json, both styles)."""
    first = json.load(open(os.path.join(HERE, "stories.json"), encoding="utf-8"))["stories"]
    return (first + json.load(open(os.path.join(HERE, "stories_parchment.json"), encoding="utf-8"))
            + json.load(open(os.path.join(HERE, "stories_library.json"), encoding="utf-8")))


def load(story_id):
    return next(s for s in all_stories() if s["id"] == story_id)


def estimate(story):
    """Seconds before any TTS runs: words at the voice's pace plus every beat's padding."""
    return sum(len(b["say"].split()) / WPS + LEAD + TAIL for b in story["beats"]) + END


def timings(voice_secs):
    slots, t = [], 0.0
    for v in voice_secs:
        d = round(LEAD + v + TAIL, 3)
        slots.append((t, d))
        t = round(t + d, 3)
    return slots


def narrate(story, out_dir):
    from kokoro_onnx import Kokoro
    import soundfile as sf
    k = Kokoro(os.path.join(ROOT, "models", "kokoro-v1.0.onnx"), os.path.join(ROOT, "models", "voices-v1.0.bin"))
    clips, sr = [], 24000
    for b in story["beats"]:
        audio, sr = k.create(b["say"], voice=VOICE, speed=SPEED, lang="en-us")
        clips.append(np.asarray(audio, np.float32))
    voice = [len(c) / sr for c in clips]
    slots = timings(voice)
    total = round(slots[-1][0] + slots[-1][1] + END, 3)
    track = np.zeros(int(total * sr) + 1, np.float32)
    for (start, _), c in zip(slots, clips):
        i = int((start + LEAD) * sr)
        track[i:i + len(c)] = c
    sf.write(os.path.join(out_dir, "assets", "voice.wav"), track, sr)
    return voice, slots, total, word_times(clips, sr, [b["say"] for b in story["beats"]])


def chunks(text, n=5):
    """Short caption blocks (most Shorts are watched muted), preferring breaks after punctuation."""
    words, out, cur = text.split(), [], []
    for w in words:
        cur.append(w)
        if len(cur) >= n or (len(cur) >= 3 and w[-1] in ",;:.!?"):
            out.append(" ".join(cur)); cur = []
    if cur:
        if out and len(cur) <= 1:
            out[-1] += " " + cur[0]
        else:
            out.append(" ".join(cur))
    return out


def captions(story, voice, slots, words=None):
    """[(start, duration, text, word_times)]: short blocks over each beat's narration. word_times: when each word is
    spoken (Whisper's timing from narrate(), else spread over the narration by characters), plus when the block's
    speech ends, for the word-by-word highlight. A block shows until the next one starts; the last holds to the beat's end."""
    caps = []
    for bi, (b, v, (start, dur)) in enumerate(zip(story["beats"], voice, slots)):
        ws = b["say"].split()
        at = words[bi] if words else [v * sum(len(w) + 1 for w in ws[:k]) / (len(b["say"]) + 1) for k in range(len(ws))]
        at = [round(start + LEAD + t, 3) for t in at + [max(v, at[-1] + 0.05)]]  # speech ends after the last word
        cs, k = chunks(b["say"]), 0
        for i, c in enumerate(cs):
            n = len(c.split())
            end = start + dur if i == len(cs) - 1 else at[k + n]
            caps.append((at[k], round(end - at[k], 3), c, at[k:k + n + 1]))
            k += n
    return caps


def compose_beat(i, beat, start, dur, kept=()):
    """One beat's paper pop-up page (paper.scene) plus its absolute-timed anims."""
    return paper.scene(i, beat, beat.get("sky", "day"), beat.get("ground", "hills"), start, dur, kept)


# Paper pages are bright: cream captions with a dark cut-paper shadow read on every sky; the spoken word in gold.
CSS = dict(root_bg="#2a1a10", cap_color="#fffaf0", gold="#ffd54a",
           cap_shadow="0 4px 0 rgba(40,20,5,0.85), 0 0 18px rgba(20,10,0,0.8)", label_shadow="0 3px 0 rgba(40,20,5,0.85), 0 0 14px rgba(20,10,0,0.9)")


def render_html(story, voice, slots, total, words=None):
    paper.frame("short", WORLD)
    e = html.escape
    sections, anims = [], []
    beats = story["beats"]
    # A new setting turns the page; the same setting dissolves scene over scene (XF s), so figures that moved do
    # not jump, and only what is new pops up (paper.js).
    setting = [(b.get("sky", "day"), b.get("ground", "hills")) for b in beats]
    cont = [i > 0 and setting[i] == setting[i - 1] for i in range(len(beats))]
    for i, (b, (start, dur), clip) in enumerate(zip(beats, slots, paper.clips(slots, cont, total, XF))):
        kept = {paper.placement(c) for c in beats[i - 1].get("cast", [])} if cont[i] else set()
        svg, a = compose_beat(i, b, start, dur, kept)
        anims += a
        sections.append(paper.section(i, start, clip, svg))
    cl = captions(story, voice, slots, words)
    caps = "".join(f'<div id="cap-{i}" class="clip cap" data-start="{s}" data-duration="{d}" data-track-index="2">'
                   f'<span id="cap-{i}-t">{" ".join(f"<span class=w>{e(w)}</span>" for w in t.split())}</span></div>'
                   for i, (s, d, t, _) in enumerate(cl))
    last = slots[-1][0]
    plan = {"cfg": paper.cfg("short"), "beats": paper.plan_beats(beats, slots, cont), "xf": XF,
            "anims": anims, "caps": [w for *_, w in cl], "total": total, "last": last}
    return TEMPLATE.format(
        title=e(story["title"]), total=total, sections="\n".join(sections), caps=caps, plan=json.dumps(plan),
        ref=e(story["ref"]), last=last, lastdur=round(total - last, 3), W=paper.W, H=paper.H, paper_css=paper.CSS, **CSS)


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<script src="paper.js"></script>
<style>
  @font-face {{ font-family: "Cormorant"; src: url("fonts/CormorantGaramond.ttf"); }}
  @font-face {{ font-family: "Cinzel"; src: url("fonts/Cinzel.ttf"); }}
  body {{ margin: 0; background: #000; }}
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; isolation: isolate; background: {root_bg}; }}
  .clip {{ position: absolute; inset: 0; }}
  .scene {{ position: absolute; inset: 0; }}
  .stage {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
  {paper_css}
  .cap {{ z-index: 5; display: flex; justify-content: center; align-items: flex-start; }}
  .cap > span {{ margin-top: 470px; max-width: 900px; text-align: center; color: {cap_color}; font: 600 84px/1.1 "Cormorant", serif;
              text-shadow: {cap_shadow}; }}
  #title {{ z-index: 6; }}
  #title-t {{ position: absolute; top: 250px; left: 0; right: 0; text-align: center; font: 38px "Cinzel", serif;
             letter-spacing: 8px; color: {gold}; text-transform: uppercase; text-shadow: {label_shadow}; }}
  #verse {{ z-index: 6; }}
  #verse-t {{ position: absolute; top: 330px; left: 0; right: 0; text-align: center; font: 32px "Cinzel", serif;
             letter-spacing: 7px; color: {gold}; text-shadow: {label_shadow}; }}
</style>
</head>
<body>
<div id="root" data-composition-id="story-short" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
{sections}
  <div id="vignette"></div>
  <div id="grain"></div>
{caps}
  <div id="title" class="clip" data-start="0" data-duration="3.2" data-track-index="3"><div id="title-t">{title}</div></div>
  <div id="verse" class="clip" data-start="{last}" data-duration="{lastdur}" data-track-index="3"><div id="verse-t">{ref} · KJV</div></div>
  <audio id="voice" src="assets/voice.wav" data-start="0" data-duration="{total}" data-volume="1"></audio>
  <audio id="music" src="assets/music.wav" data-start="0" data-duration="{total}" data-volume="1"></audio>
</div>
<script>
  const PLAN = {plan};
  Promise.all([document.fonts.load('600 84px "Cormorant"'), document.fonts.load('38px "Cinzel"')]).then(() => {{
    const tl = gsap.timeline({{ paused: true }});
    paperScenes(tl, PLAN);  // the pages, their pop-ups and every figure's motion (paper.js)
    // captions pop in per block, and the word being spoken lights up
    PLAN.caps.forEach((w, i) => {{
      tl.fromTo("#cap-" + i + "-t", {{ opacity: 0, y: 18 }}, {{ opacity: 1, y: 0, duration: 0.2, ease: "power2.out", immediateRender: false }}, w[0]);
      document.querySelectorAll("#cap-" + i + "-t .w").forEach((el, k) => {{
        tl.set(el, {{ color: "{gold}" }}, w[k]);
        tl.set(el, {{ color: "{cap_color}" }}, w[k + 1]);
      }});
    }});
    // the title is on screen from the very first frame (the hook), then lifts away
    tl.to("#title-t", {{ opacity: 0, y: -12, duration: 0.4, ease: "power2.in" }}, 2.7);
    tl.fromTo("#verse-t", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.8, immediateRender: false }}, {last} + 0.4);
    window.__timelines = window.__timelines || {{}};
    window.__timelines["story-short"] = tl;
  }});
</script>
</body>
</html>
"""


def main(story_id):
    story = load(story_id)
    out = os.path.join(HERE, "build", story_id)
    os.makedirs(os.path.join(out, "assets"), exist_ok=True)
    shutil.copytree(os.path.join(ROOT, "fonts"), os.path.join(out, "fonts"), dirs_exist_ok=True)
    shutil.copy(os.path.join(ROOT, "paper.js"), out)
    voice, slots, total, words = narrate(story, out)
    if total > MAX_TOTAL:
        sys.exit(f"{story_id}: {total:.1f} s is over the {MAX_TOTAL} s Shorts limit; trim its narration")
    music(total, os.path.join(out, "assets", "music.wav"))
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(render_html(story, voice, slots, total, words))
    print(f"{story_id}: {len(slots)} beats, {total:.1f} s -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
