"""longform/videos.json -> 16:9 (1920x1080) long videos, 10-12 minutes each, of Jesus' life and his prayers, in
divine glowing line art. Self-contained: shorts/ is not used (only the generated music bed comes from build.py).

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
from build import music  # noqa: E402  the generated piano-and-pad bed, no licensed audio
import lineart as art  # noqa: E402

LEAD, TAIL, END = 0.6, 1.6, 1.6   # silence before/after each beat's narration (room to breathe); a chapter's end hold
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
    return voice, slots, total


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


def captions(ch, voice, slots):
    """[(start, duration, text)], spread over each beat's narration in proportion to characters."""
    caps = []
    for b, v, (start, dur) in zip(ch["beats"], voice, slots):
        cs = chunks(b["say"])
        total = sum(len(c) for c in cs)
        t = start + LEAD
        for i, c in enumerate(cs):
            d = v * len(c) / total
            end = (start + dur) if i == len(cs) - 1 else t + d  # the last block holds to the beat's end
            caps.append((round(t, 3), round(end - t, 3), c))
            t += d
    return caps


def compose_beat(i, beat, start, dur):
    """One beat's line-art scene plus its absolute-timed anims."""
    p = f"b{i}"
    m, anims = art.background(p, beat.get("sky", "night"))
    parts = [m]
    lines = []
    g, a = art.land(p, beat.get("land", "hills")); lines.append(g); anims += a
    cast = beat.get("cast", [])
    inner = {j: [] for j in range(len(cast))}
    drawn = {}
    for j, c in enumerate(cast):
        pid = f"{p}-c{j}"
        drawn[j] = (art.crowd(pid, c.get("x", 960), c.get("y", art.GF - 20), c.get("s", 0.8), c.get("n", 12))
                    if c["k"] == "crowd" else None)
        for act in c.get("acts", []):
            anims.append(dict(act, t=f"#{pid}", x0=c.get("x", 960), y0=c.get("y", art.GF)))
        if c["k"] in ("jesus", "angel"):
            anims.append({"t": f"#{pid}-glow", "do": "glow"})
    for j in reversed(range(len(cast))):  # children are drawn inside their parent and move with it (people in a boat)
        c = cast[j]
        if drawn[j] is None:
            drawn[j] = art.place(f"{p}-c{j}", c["k"], c.get("x", 960), c.get("y", art.GF), c.get("s", 1.5),
                                 c.get("flip", False), "".join(inner[j]), p)
        if "in" in c:
            inner[c["in"]].insert(0, drawn[j])
    lines += [drawn[j] for j in range(len(cast)) if "in" not in cast[j]]
    for fx in beat.get("fx", []):
        m, a = art.fx(p, fx); lines.append(m); anims += a
    parts.append(f'<g filter="url(#{p}-glow)">{"".join(lines)}</g>')  # the divine glow on every line of the scene
    for x in anims:  # beat-relative times -> absolute timeline times
        x["s"] = round(start + x.pop("at", 0), 3)
        x["d"] = round(x.pop("dur", start + dur - x["s"] - 0.05), 3)
        x["b0"] = start
    return (f'<svg id="{p}-svg" class="stage" viewBox="0 0 {art.W} {art.H}" xmlns="http://www.w3.org/2000/svg">'
            f'{"".join(parts)}</svg>'), anims


def render_html(v, n, ch, voice, slots, total):
    art.use(v["template"])
    t = art.TEMPLATES[v["template"]]
    e = html.escape
    sections, anims = [], []
    for i, (b, (start, dur)) in enumerate(zip(ch["beats"], slots)):
        svg, a = compose_beat(i, b, start, dur)
        anims += a
        sections.append(f'<section id="beat-{i}" class="clip" data-start="{start}" data-duration="{dur}" data-track-index="1">'
                        f'<div class="scene" id="beat-{i}-in">{svg}</div></section>')
    cl = captions(ch, voice, slots)
    caps = "".join(f'<div id="cap-{i}" class="clip cap" data-start="{s}" data-duration="{d}" data-track-index="2">'
                   f'<span id="cap-{i}-t">{e(c)}</span></div>' for i, (s, d, c) in enumerate(cl))
    last = slots[-1][0]
    plan = {"beats": [{"id": f"beat-{i}", "s": s, "d": d} for i, (s, d) in enumerate(slots)],
            "anims": anims, "caps": len(cl), "last": last}
    return TEMPLATE.format(
        title=e(ch["title"]), kicker=e(f"Chapter {n}" if n else ("" if ch["title"] == v["title"] else v["title"])), total=total,
        sections="\n".join(sections), caps=caps, plan=json.dumps(plan), ref=e(ch["ref"]), last=last,
        lastdur=round(total - last, 3), W=art.W, H=art.H, line=t["line"], glow=t["glow"],
        bg=t["skies"]["night"][0])


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  @font-face {{ font-family: "Cormorant"; src: url("fonts/CormorantGaramond.ttf"); }}
  @font-face {{ font-family: "Cinzel"; src: url("fonts/Cinzel.ttf"); }}
  body {{ margin: 0; background: #000; }}
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; isolation: isolate; background: {bg}; }}
  .clip, .scene, .stage {{ position: absolute; inset: 0; }}
  .stage {{ width: 100%; height: 100%; }}
  /* line art: every stroke traces itself in (pathLength=1, dash offset 1 -> 0) */
  .d {{ fill: {line}; fill-opacity: 0.05; stroke: {line}; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round;
        stroke-dasharray: 1; stroke-dashoffset: 1; }}
  .d.n {{ fill: none; }}
  .d.f {{ fill: {glow}; fill-opacity: 0.9; }}
  #vignette {{ position: absolute; inset: 0; z-index: 3; pointer-events: none;
              background: radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.6) 100%); }}
  /* captions: the Shorts' captions, set for a wide frame (bottom centre) */
  .cap {{ z-index: 5; display: flex; justify-content: center; align-items: flex-end; }}
  .cap span {{ margin-bottom: 64px; max-width: 1500px; text-align: center; color: #fff8ec; font: 600 64px/1.1 "Cormorant", serif;
              text-shadow: 0 0 18px rgba(0,0,0,0.85), 0 4px 6px rgba(0,0,0,0.7); }}
  #title {{ z-index: 6; }}
  #title-k {{ position: absolute; top: 74px; left: 0; right: 0; text-align: center; font: 24px "Cinzel", serif;
             letter-spacing: 9px; color: {line}; text-transform: uppercase; text-shadow: 0 0 14px rgba(0,0,0,0.9); }}
  #title-t {{ position: absolute; top: 112px; left: 0; right: 0; text-align: center; font: 54px "Cinzel", serif;
             letter-spacing: 4px; color: #fff3dc; text-shadow: 0 0 22px {glow}, 0 0 8px rgba(0,0,0,0.8); }}
  #verse {{ z-index: 6; }}
  #verse-t {{ position: absolute; top: 74px; left: 0; right: 0; text-align: center; font: 28px "Cinzel", serif;
             letter-spacing: 7px; color: {line}; text-shadow: 0 0 14px rgba(0,0,0,0.9); }}
</style>
</head>
<body>
<div id="root" data-composition-id="long-chapter" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
{sections}
  <div id="vignette"></div>
{caps}
  <div id="title" class="clip" data-start="0" data-duration="4.2" data-track-index="3"><div id="title-k">{kicker}</div><div id="title-t">{title}</div></div>
  <div id="verse" class="clip" data-start="{last}" data-duration="{lastdur}" data-track-index="3"><div id="verse-t">{ref} · KJV</div></div>
  <audio id="voice" src="assets/voice.wav" data-start="0" data-duration="{total}" data-volume="1"></audio>
</div>
<script>
  const PLAN = {plan};
  Promise.all([document.fonts.load('600 64px "Cormorant"'), document.fonts.load('54px "Cinzel"')]).then(() => {{
    const tl = gsap.timeline({{ paused: true }});
    const n = (d, p) => Math.max(0, Math.round(d / p) - 1);   // finite repeats only (deterministic render)
    tl.set(".arm-l", {{ rotation: 10, transformOrigin: "50% 0%" }}, 0);
    tl.set(".arm-r", {{ rotation: -10, transformOrigin: "50% 0%" }}, 0);
    tl.set(".body", {{ transformOrigin: "50% 100%" }}, 0);
    const arms = (t, l, r, s, d) => {{
      if (l !== null) tl.to(t + "-al", {{ rotation: l, duration: d, ease: "power2.inOut" }}, s);
      if (r !== null) tl.to(t + "-ar", {{ rotation: r, duration: d, ease: "power2.inOut" }}, s);
    }};
    const bob = (t, s, d, p, h) => tl.to(t + "-b", {{ y: -h, duration: p / 2, repeat: n(d, p / 2), yoyo: true, ease: "sine.inOut" }}, s);
    const F = {{
      walk: a => {{ tl.to(a.t, {{ x: a.to, duration: a.d, ease: "sine.inOut" }}, a.s); bob(a.t, a.s, a.d, 0.62, 7); }},
      climb: a => tl.to(a.t, {{ y: a.to, duration: a.d, ease: "power1.inOut" }}, a.s),
      raise: a => arms(a.t, 140, -140, a.s, 0.8),
      bless: a => arms(a.t, null, -125, a.s, 0.8),
      reach: a => arms(a.t, null, -78, a.s, 0.7),
      lower: a => arms(a.t, 10, -10, a.s, 0.8),
      kneel: a => tl.to(a.t + "-b", {{ scaleY: 0.68, duration: 0.7, ease: "power2.out" }}, a.s),
      stand: a => tl.to(a.t + "-b", {{ scaleY: 1, rotation: 0, duration: 0.9, ease: "power2.out" }}, a.s),
      lie: a => tl.set(a.t + "-b", {{ rotation: -90 }}, a.b0),
      appear: a => {{ tl.set(a.t, {{ opacity: 0 }}, a.b0); tl.to(a.t, {{ opacity: 1, duration: 0.8, ease: "power1.out" }}, a.s); }},
      vanish: a => tl.to(a.t, {{ opacity: 0, duration: 1.0, ease: "power1.in" }}, a.s),
      rock: a => tl.fromTo(a.t + "-b", {{ rotation: -(a.amp || 4) }}, {{ rotation: a.amp || 4, duration: (a.period || 2.4) / 2,
                  repeat: n(a.d, (a.period || 2.4) / 2), yoyo: true, ease: "sine.inOut", immediateRender: false }}, a.s),
      drift: a => tl.fromTo(a.t, {{ x: -(a.amp || 40) }}, {{ x: a.amp || 40, duration: (a.period || 3) / 2,
                   repeat: n(a.d, (a.period || 3) / 2), yoyo: true, ease: "sine.inOut", immediateRender: false }}, a.s),
      fly: a => tl.to(a.t, {{ x: a.to, y: a.toy === undefined ? a.y0 : a.toy, duration: a.d, ease: "none" }}, a.s),
      grow: a => {{ tl.set(a.t + "-b", {{ scale: 0 }}, a.b0); tl.to(a.t + "-b", {{ scale: 1, duration: a.grow || 2.4, ease: "power2.out" }}, a.s); }},
      roll: a => {{ tl.to(a.t, {{ x: a.to, duration: a.d, ease: "power2.inOut" }}, a.s);
                   tl.to(a.t + "-b", {{ rotation: a.deg || 200, duration: a.d, ease: "power2.inOut" }}, a.s); }},
      flicker: a => tl.to(a.t + "-flame", {{ scaleY: 0.82, transformOrigin: "50% 100%", duration: 0.16, repeat: n(a.d, 0.16), yoyo: true }}, a.s),
      glow: a => tl.fromTo(a.t, {{ opacity: 0.5 }}, {{ opacity: 0.95, duration: 1.4, repeat: n(a.d, 1.4), yoyo: true, ease: "sine.inOut", immediateRender: false }}, a.s),
      twinkle: a => tl.fromTo(a.t, {{ opacity: 0.6 }}, {{ opacity: 1, duration: 1.1, repeat: n(a.d, 1.1), yoyo: true, ease: "sine.inOut", immediateRender: false }}, a.s),
      spin: a => tl.fromTo(a.t, {{ rotation: 0 }}, {{ rotation: a.deg, duration: a.d, ease: "none", svgOrigin: a.ox + " " + a.oy, immediateRender: false }}, a.s),
      pulse: a => tl.fromTo(a.t, {{ scale: 1 }}, {{ scale: 1.06, duration: 3, repeat: n(a.d, 3), yoyo: true, ease: "sine.inOut",
                  svgOrigin: a.ox + " " + a.oy, immediateRender: false }}, a.s),
      rise: a => tl.fromTo(a.t, {{ y: 0 }}, {{ y: -a.by, duration: a.d, ease: "none", immediateRender: false }}, a.s),
      descend: a => tl.fromTo(a.t, {{ opacity: 0, y: 40 }}, {{ opacity: 1, y: 40 + a.by, duration: 3.4, ease: "power1.out", immediateRender: false }}, a.s + 0.6),
      rain: a => tl.fromTo(a.t, {{ y: -{H} }}, {{ y: 0, duration: 0.7, repeat: n(a.d, 0.7), ease: "none", immediateRender: false }}, a.s),
      flash: a => [0.6, 2.3, 3.4].filter(o => o < a.d - 0.4).forEach(o => {{
        tl.to([a.t, a.bolt], {{ opacity: 0.85, duration: 0.05 }}, a.s + o);
        tl.to([a.t, a.bolt], {{ opacity: 0, duration: 0.4 }}, a.s + o + 0.05); }}),
      rays: a => {{ tl.to(a.t, {{ opacity: 0.5, duration: 1.4, ease: "power1.out" }}, a.s + 0.3);
                   tl.to(a.t, {{ opacity: 0.25, duration: 1.6, repeat: n(a.d - 1.7, 1.6), yoyo: true, ease: "sine.inOut" }}, a.s + 1.7); }},
      sparkle: a => {{ tl.to(a.t, {{ opacity: 1, duration: 0.8 }}, a.s + 0.4);
                      tl.to(a.t, {{ opacity: 0.4, duration: 0.6, repeat: n(a.d - 1.2, 0.6), yoyo: true }}, a.s + 1.2); }},
    }};
    PLAN.beats.forEach(b => {{
      tl.fromTo("#" + b.id + "-in", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.5, immediateRender: false }}, b.s);
      tl.to("#" + b.id + "-in", {{ opacity: 0, duration: 0.4 }}, b.s + b.d - 0.4);
      tl.fromTo("#" + b.id + "-in", {{ scale: 1.0 }}, {{ scale: 1.05, duration: b.d, ease: "none", transformOrigin: "50% 62%", immediateRender: false }}, b.s);
      // the scene draws itself: land first, then figures and props, in document order
      tl.fromTo("#" + b.id + "-in .d", {{ strokeDashoffset: 1 }}, {{ strokeDashoffset: 0, duration: 2.2, ease: "power2.inOut",
                stagger: {{ amount: 1.6 }}, immediateRender: false }}, b.s + 0.1);
    }});
    PLAN.anims.forEach(a => F[a.do](a));
    for (let i = 0; i < PLAN.caps; i++)
      tl.fromTo("#cap-" + i + "-t", {{ opacity: 0, y: 18 }}, {{ opacity: 1, y: 0, duration: 0.25, ease: "power2.out", immediateRender: false }},
                Number(document.getElementById("cap-" + i).dataset.start));
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
    voice, slots, total = narrate(ch, out)
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(render_html(v, n, ch, voice, slots, total))
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
