"""longform/videos.json -> 16:9 (1920x1080) long videos, 10-12 minutes each, of Jesus' life and his prayers, in
a paper pop-up book (paper.py, paper.js). Self-contained: shorts/ is not used (only the generated music bed comes from build.py).

The voice and captions match the Shorts (Kokoro af_heart at the same speed; Cormorant captions in short blocks).
Each chapter renders as its own HyperFrames page, all chapters in parallel on GitHub Actions; `finish` joins them,
lays one continuous music bed under the whole video, and writes the YouTube text (with chapter timestamps) and a
thumbnail.

  python longform/build_long.py plan [video-id ...]           -> GitHub step outputs (ids from longform/render.txt)
  python longform/build_long.py chapter <video-id> <n>        -> longform/build/<video-id>--<nn>/ (index.html, assets/)
  python longform/build_long.py finish <video-id> <dir> <out> -> <out>/<video-id>.mp4, .txt, .jpg
"""
import html, json, os, shutil, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from build import music, word_times  # noqa: E402  the generated piano-and-pad bed; Whisper word timing
import paper  # noqa: E402  the paper pop-up pages, shared by every video (paper.py, paper.js)

LEAD, TAIL, END = 0.6, 1.6, 1.6   # silence before/after each beat's narration (room to breathe); a chapter's end hold
XF = 0.5                           # the dissolve between two beats in the same setting (a new setting turns the page)
WORLD = "levant"                   # paper.py village architecture: flat roofs, domes and palms
VOICE, SPEED = "af_heart", 0.94    # the Shorts' voice and pace
WPS = 3.24                         # words per second at SPEED, measured on rendered chapters (the Shorts' 2.55 is
                                   # a conservative guess); used to check 10-12 minutes before any TTS runs
MIN_LEN, MAX_LEN = 600, 720        # every long video is 10-12 minutes


def videos():
    """Every long video, in upload order: longform/videos/NN-<id>.json, one file per video."""
    d = os.path.join(HERE, "videos")
    return [json.load(open(os.path.join(d, f), encoding="utf-8")) for f in sorted(os.listdir(d)) if f.endswith(".json")]


def video(vid):
    return next(v for v in videos() if v["id"] == vid)


def name(vid, n):
    return f"{vid}--{n:02d}"


def estimate(ch):
    """Seconds for one chapter before any TTS runs."""
    return sum(len(b["say"].split()) / WPS + LEAD + TAIL for b in ch["beats"]) + END


def timings(voice_secs):
    slots, t = [], 0.0
    for v in voice_secs:
        d = round(LEAD + v + TAIL, 3)
        slots.append((t, d))
        t = round(t + d, 3)  # rounded each step so a beat starts exactly where the last one ends
    return slots


def narrate(ch, out_dir):
    from kokoro_onnx import Kokoro
    import soundfile as sf
    k = Kokoro(os.path.join(ROOT, "models", "kokoro-v1.0.onnx"), os.path.join(ROOT, "models", "voices-v1.0.bin"))
    clips, sr = [], 24000
    for b in ch["beats"]:
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
    return voice, slots, total, word_times(clips, sr, [b["say"] for b in ch["beats"]])


def chunks(text, n=5):
    """Short caption blocks, as in the Shorts, preferring breaks after punctuation."""
    out, cur = [], []
    for w in text.split():
        cur.append(w)
        if len(cur) >= n or (len(cur) >= 3 and w[-1] in ",;:.!?"):
            out.append(" ".join(cur)); cur = []
    if cur:
        if out and len(cur) <= 1:
            out[-1] += " " + cur[0]
        else:
            out.append(" ".join(cur))
    return out


def captions(ch, voice, slots, words=None):
    """[(start, duration, text, word_times)]: short blocks over each beat's narration. word_times: when each word is
    spoken (Whisper's timing from narrate(), else spread over the narration by characters), plus when the block's
    speech ends, for the word-by-word highlight. A block shows until the next one starts; the last holds to the beat's end."""
    caps = []
    for bi, (b, v, (start, dur)) in enumerate(zip(ch["beats"], voice, slots)):
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
    """One beat's paper pop-up page (paper.scene) plus its absolute-timed anims. `kept`: placements already standing
    from the previous beat in the same setting; they stay up, and only what is new pops up."""
    return paper.scene(i, beat, beat.get("sky", "night"), beat.get("land", "hills"), start, dur, kept)


GOLD, CREAM = "#ffd54a", "#fffaf0"  # title and spoken-word gold; caption cream (a dark cut-paper shadow under both)


def render_html(v, n, ch, voice, slots, total, words=None):
    paper.frame("long", WORLD)
    e = html.escape
    sections, anims = [], []
    beats = ch["beats"]
    # A new setting turns the page. The same setting carries on: the outgoing beat dissolves (XF s) under the
    # incoming one, what was standing stays, and only new figures pop up (paper.js).
    setting = [(b.get("sky", "night"), b.get("land", "hills")) for b in beats]
    cont = [i > 0 and setting[i] == setting[i - 1] for i in range(len(beats))]
    for i, (b, (start, dur), clip) in enumerate(zip(beats, slots, paper.clips(slots, cont, total, XF))):
        kept = {paper.placement(c) for c in beats[i - 1].get("cast", [])} if cont[i] else set()
        svg, a = compose_beat(i, b, start, dur, kept)
        anims += a
        sections.append(paper.section(i, start, clip, svg))
    cl = captions(ch, voice, slots, words)
    caps = "".join(f'<div id="cap-{i}" class="clip cap" data-start="{s}" data-duration="{d}" data-track-index="2">'
                   f'<span id="cap-{i}-t">{" ".join(f"<span class=w>{e(w)}</span>" for w in c.split())}</span></div>'
                   for i, (s, d, c, _) in enumerate(cl))
    last = slots[-1][0]
    plan = {"cfg": paper.cfg("long"), "beats": paper.plan_beats(beats, slots, cont), "xf": XF,
            "anims": anims, "caps": [w for *_, w in cl], "last": last}
    return TEMPLATE.format(
        title=e(ch["title"]), kicker=e(f"Chapter {n}" if n else ("" if ch["title"] == v["title"] else v["title"])), total=total,
        sections="\n".join(sections), caps=caps, plan=json.dumps(plan), ref=e(ch["ref"]), last=last,
        lastdur=round(total - last, 3), W=paper.W, H=paper.H, line=GOLD, glow=GOLD, cream=CREAM, bg="#2a1a10",
        paper_css=paper.CSS)


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
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; isolation: isolate; background: {bg}; }}
  .clip, .scene, .stage {{ position: absolute; inset: 0; }}
  .stage {{ width: 100%; height: 100%; }}
  {paper_css}
  /* captions: the Shorts' captions, set for a wide frame (bottom centre) */
  .cap {{ z-index: 5; display: flex; justify-content: center; align-items: flex-end; }}
  .cap > span {{ margin-bottom: 64px; max-width: 1500px; text-align: center; color: {cream}; font: 600 64px/1.1 "Cormorant", serif;
              text-shadow: 0 4px 0 rgba(40,20,5,0.85), 0 0 18px rgba(20,10,0,0.8); }}
  #title {{ z-index: 6; }}
  #title-k {{ position: absolute; top: 74px; left: 0; right: 0; text-align: center; font: 24px "Cinzel", serif;
             letter-spacing: 9px; color: {line}; text-transform: uppercase; text-shadow: 0 3px 0 rgba(40,20,5,0.85), 0 0 14px rgba(20,10,0,0.9); }}
  #title-t {{ position: absolute; top: 112px; left: 0; right: 0; text-align: center; font: 54px "Cinzel", serif;
             letter-spacing: 4px; color: {cream}; text-shadow: 0 4px 0 rgba(40,20,5,0.85), 0 0 16px rgba(20,10,0,0.8); }}
  #verse {{ z-index: 6; }}
  #verse-t {{ position: absolute; top: 74px; left: 0; right: 0; text-align: center; font: 28px "Cinzel", serif;
             letter-spacing: 7px; color: {line}; text-shadow: 0 3px 0 rgba(40,20,5,0.85), 0 0 14px rgba(20,10,0,0.9); }}
</style>
</head>
<body>
<div id="root" data-composition-id="long-chapter" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
{sections}
  <div id="vignette"></div>
  <div id="grain"></div>
{caps}
  <div id="title" class="clip" data-start="0" data-duration="4.2" data-track-index="3"><div id="title-k">{kicker}</div><div id="title-t">{title}</div></div>
  <div id="verse" class="clip" data-start="{last}" data-duration="{lastdur}" data-track-index="3"><div id="verse-t">{ref} · KJV</div></div>
  <audio id="voice" src="assets/voice.wav" data-start="0" data-duration="{total}" data-volume="1"></audio>
</div>
<script>
  const PLAN = {plan};
  Promise.all([document.fonts.load('600 64px "Cormorant"'), document.fonts.load('54px "Cinzel"')]).then(() => {{
    const tl = gsap.timeline({{ paused: true }});
    paperScenes(tl, PLAN);  // the pages, their pop-ups and every figure's motion (paper.js)
    // captions rise in per block, and the word being spoken lights up
    PLAN.caps.forEach((w, i) => {{
      tl.fromTo("#cap-" + i + "-t", {{ opacity: 0, y: 18 }}, {{ opacity: 1, y: 0, duration: 0.25, ease: "power2.out", immediateRender: false }}, w[0]);
      document.querySelectorAll("#cap-" + i + "-t .w").forEach((el, k) => {{
        tl.set(el, {{ color: "{glow}" }}, w[k]);
        tl.set(el, {{ color: "{cream}" }}, w[k + 1]);
      }});
    }});
    tl.fromTo("#title-k", {{ opacity: 0, y: 12 }}, {{ opacity: 1, y: 0, duration: 0.8, immediateRender: false }}, 0.2);
    tl.fromTo("#title-t", {{ opacity: 0, y: 16 }}, {{ opacity: 1, y: 0, duration: 1.0, immediateRender: false }}, 0.4);
    tl.to(["#title-k", "#title-t"], {{ opacity: 0, duration: 0.6 }}, 3.5);
    tl.fromTo("#verse-t", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.8, immediateRender: false }}, PLAN.last + 0.4);
    window.__timelines = window.__timelines || {{}};
    window.__timelines["long-chapter"] = tl;
  }});
</script>
</body>
</html>
"""


def stamp(t):
    m, s = divmod(int(t), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def description(v, starts):
    """YouTube text: title, description, chapter timestamps (the first at 0:00), scripture and hashtags."""
    marks = "\n".join(f"{stamp(t)} {c['title']}" for t, c in zip(starts, v["chapters"]))
    refs = " · ".join(dict.fromkeys(c["ref"] for c in v["chapters"]))
    return (f"{v['title']}\n\n{v['description']}\n\nChapters\n{marks}\n\nScripture (King James Version): {refs}\n\n"
            f"{' '.join(v['tags'])}\n")


def plan(ids):
    """GitHub step outputs: the videos to finish, and one matrix entry per chapter to render."""
    vs = [video(i) for i in ids]
    chs = [{"video": v["id"], "n": n, "name": name(v["id"], n)} for v in vs for n in range(len(v["chapters"]))]
    print(f"videos={json.dumps([v['id'] for v in vs])}")
    print(f"chapters={json.dumps(chs)}")


def chapter(vid, n):
    v = video(vid)
    ch = v["chapters"][n]
    out = os.path.join(HERE, "build", name(vid, n))
    os.makedirs(os.path.join(out, "assets"), exist_ok=True)
    shutil.copytree(os.path.join(ROOT, "fonts"), os.path.join(out, "fonts"), dirs_exist_ok=True)
    shutil.copy(os.path.join(ROOT, "paper.js"), out)
    voice, slots, total, words = narrate(ch, out)
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(render_html(v, n, ch, voice, slots, total, words))
    print(f"{name(vid, n)}: {ch['title']}, {len(slots)} beats, {total:.1f} s -> {out}")


def run(*cmd):
    subprocess.run(cmd, check=True)


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                check=True, capture_output=True, text=True).stdout)


def finish(vid, src, out):
    v = video(vid)
    files = [os.path.abspath(os.path.join(src, name(vid, n) + ".mp4")) for n in range(len(v["chapters"]))]
    missing = [f for f in files if not os.path.exists(f)]
    if missing:
        sys.exit(f"{vid}: missing chapter renders {missing}")
    durs = [duration(f) for f in files]
    starts = [round(sum(durs[:i]), 3) for i in range(len(durs))]
    os.makedirs(out, exist_ok=True)
    tmp = os.path.join(out, f"{vid}.parts")
    os.makedirs(tmp, exist_ok=True)
    open(os.path.join(tmp, "list.txt"), "w").write("".join(f"file '{f}'\n" for f in files))
    run("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "list.txt"), "-c", "copy",
        os.path.join(tmp, "joined.mp4"))
    total = duration(os.path.join(tmp, "joined.mp4"))
    if not MIN_LEN <= total <= MAX_LEN:
        print(f"::warning::{vid} is {stamp(total)}, outside 10-12 minutes; add or trim beats in longform/videos.json")
    music(total, os.path.join(tmp, "music.wav"))
    # the voice plus one unbroken music bed, then -14 LUFS (YouTube's playback loudness), as for the Shorts
    run("ffmpeg", "-v", "error", "-y", "-i", os.path.join(tmp, "joined.mp4"), "-i", os.path.join(tmp, "music.wav"),
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", os.path.join(out, f"{vid}.mp4"))
    open(os.path.join(out, f"{vid}.txt"), "w", encoding="utf-8").write(description(v, starts))
    open(os.path.join(tmp, "title.txt"), "w", encoding="utf-8").write(v.get("thumbnail", v["title"]))
    # thumbnail: a drawn-in frame from the first chapter, the title set large in Cinzel on a dark band
    run("ffmpeg", "-v", "error", "-y", "-ss", str(min(8.0, durs[0] / 2)), "-i", files[0], "-frames:v", "1", "-vf",
        "scale=1280:720,drawbox=y=ih*0.64:w=iw:h=ih*0.36:color=black@0.9:t=fill,"  # hides the caption under it
        f"drawtext=fontfile={os.path.join(ROOT, 'fonts', 'Cinzel.ttf')}:textfile={os.path.join(tmp, 'title.txt')}:"
        "fontsize=70:fontcolor=0xf6e2b0:x=(w-text_w)/2:y=h*0.64+(h*0.36-text_h)/2", os.path.join(out, f"{vid}.jpg"))
    shutil.rmtree(tmp)
    print(f"{vid}: {len(files)} chapters, {stamp(total)} -> {out}")


if __name__ == "__main__":
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if cmd == "plan":
        lines = open(os.path.join(HERE, "render.txt"), encoding="utf-8").read().split("\n")
        plan(args or [l.strip() for l in lines if l.strip() and not l.lstrip().startswith("#")])
    elif cmd == "chapter":
        chapter(args[0], int(args[1]))
    elif cmd == "finish":
        finish(*args)
    else:
        sys.exit(__doc__)
