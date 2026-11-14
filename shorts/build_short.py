"""stories.json -> one vertical (1080x1920) HyperFrames Short per story: Kokoro narration, music bed, captions and
paper-cut silhouette scenes that act out each beat.

  python shorts/build_short.py <story-id>        -> shorts/build/<story-id>/ (index.html, assets/, fonts/)
  cd shorts/build/<story-id> && npx hyperframes render --output <file>.mp4
"""
import html, json, os, re, shutil, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from build import music  # the same generated piano-and-pad bed as the long video
import kit

LEAD, TAIL, END = 0.35, 0.6, 1.2  # silence before/after each beat's narration; music-only ending
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
    return voice, slots, total


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


def captions(story, voice, slots):
    """[(start, duration, text)], spread over each beat's narration in proportion to characters."""
    caps = []
    for b, v, (start, dur) in zip(story["beats"], voice, slots):
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
    """One beat's SVG scene plus its absolute-timed anims."""
    p = f"b{i}"
    parts, anims = [], []
    m, a = kit.sky(p, beat.get("sky", "day")); parts.append(m); anims += a
    m, a = kit.ground(p, beat.get("ground", "hills")); parts.append(m); anims += a
    cast = beat.get("cast", [])
    inner = {j: [] for j in range(len(cast))}
    drawn = {}
    for j, c in enumerate(cast):
        pid = f"{p}-c{j}"
        if c["k"] == "crowd":
            drawn[j] = kit.crowd(pid, c.get("x", 540), c.get("y", kit.FEET - 40), c.get("s", 0.9), c.get("n", 12), p)
        else:
            drawn[j] = None  # placed after its children are known
        for act in c.get("acts", []):
            anims.append(dict(act, t=f"#{pid}", x0=c.get("x", 540), y0=c.get("y", kit.FEET)))
        if c["k"] == "jesus":
            anims.append({"t": f"#{pid}-glow", "do": "glow"})
    for j in reversed(range(len(cast))):  # children drawn inside their parent so they move with it (people in a boat)
        c = cast[j]
        if drawn[j] is None:
            drawn[j] = kit.place(f"{p}-c{j}", c["k"], c.get("x", 540), c.get("y", kit.FEET), c.get("s", 1.6),
                                 c.get("flip", False), "".join(inner[j]), p)
        if "in" in c:
            inner[c["in"]].insert(0, drawn[j])
    parts += [drawn[j] for j in range(len(cast)) if "in" not in cast[j]]
    for name in beat.get("fx", []):
        m, a = kit.fx(p, name); parts.append(m); anims += [dict(x, at=0) for x in a]
    for x in anims:  # relative beat times -> absolute timeline times
        x["s"] = round(start + x.pop("at", 0), 3)
        x["d"] = round(x.pop("dur", start + dur - x["s"] - 0.05), 3)
        x["b0"] = start
    svg = (f'<svg id="{p}-svg" class="stage" viewBox="0 0 {kit.W} {kit.H}" xmlns="http://www.w3.org/2000/svg">'
           f'{"".join(parts)}</svg>')
    return svg, anims


CSS = {  # page-level colours per style (the scene colours live in kit.STYLES)
    "silhouette": dict(root_bg="#05060c", cap_color="#fff8ec", gold="#f0d79c",
                       cap_shadow="0 0 18px rgba(0,0,0,0.85), 0 4px 6px rgba(0,0,0,0.7)", label_shadow="0 0 14px rgba(0,0,0,0.9)",
                       vignette="radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)"),
    "parchment": dict(root_bg="#e9d9b4", cap_color="#2a170b", gold="#7a4f1a",
                      cap_shadow="0 0 16px rgba(250,240,215,0.95), 0 0 5px rgba(250,240,215,0.9)",
                      label_shadow="0 0 10px rgba(250,240,215,0.95)",
                      vignette="radial-gradient(ellipse at 50% 45%, rgba(90,55,20,0) 48%, rgba(70,40,15,0.6) 100%)"),
}


def render_html(story, voice, slots, total):
    style = story.get("style", "silhouette")
    kit.use(style)
    e = html.escape
    sections, anims = [], []
    for i, (b, (start, dur)) in enumerate(zip(story["beats"], slots)):
        svg, a = compose_beat(i, b, start, dur)
        anims += a
        sections.append(f'<section id="beat-{i}" class="clip" data-start="{start}" data-duration="{dur}" data-track-index="1">'
                        f'<div class="scene" id="beat-{i}-in">{svg}</div></section>')
    caps = "".join(f'<div id="cap-{i}" class="clip cap" data-start="{s}" data-duration="{d}" data-track-index="2">'
                   f'<span id="cap-{i}-t">{e(t)}</span></div>' for i, (s, d, t) in enumerate(captions(story, voice, slots)))
    last = slots[-1][0]
    plan = {"beats": [{"id": f"beat-{i}", "s": s, "d": d} for i, (s, d) in enumerate(slots)],
            "anims": anims, "caps": len(captions(story, voice, slots)), "total": total, "last": last}
    return TEMPLATE.format(
        title=e(story["title"]), total=total, sections="\n".join(sections), caps=caps, plan=json.dumps(plan),
        ref=e(story["ref"]), last=last, lastdur=round(total - last, 3), W=kit.W, H=kit.H, **CSS[style])


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
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; isolation: isolate; background: {root_bg}; }}
  .clip {{ position: absolute; inset: 0; }}
  .scene {{ position: absolute; inset: 0; }}
  .stage {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
  #vignette {{ position: absolute; inset: 0; z-index: 3; pointer-events: none;
              background: {vignette}; }}
  .cap {{ z-index: 5; display: flex; justify-content: center; align-items: flex-start; }}
  .cap span {{ margin-top: 470px; max-width: 900px; text-align: center; color: {cap_color}; font: 600 84px/1.1 "Cormorant", serif;
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
      run: a => {{ tl.to(a.t, {{ x: a.to, duration: a.d, ease: "power1.inOut" }}, a.s); bob(a.t, a.s, a.d, 0.36, 12); }},
      climb: a => {{ tl.to(a.t, {{ y: a.to, duration: a.d, ease: "power1.inOut" }}, a.s); }},
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
      fly: a => {{ tl.to(a.t, {{ x: a.to, y: a.toy === undefined ? a.y0 : a.toy, duration: a.d, ease: "none" }}, a.s);
                  tl.to(a.t + "-b", {{ scaleY: 0.55, duration: 0.18, repeat: n(a.d, 0.18), yoyo: true }}, a.s); }},
      grow: a => {{ tl.set(a.t + "-b", {{ scale: 0 }}, a.b0); tl.to(a.t + "-b", {{ scale: 1, duration: a.grow || 2.4, ease: "power2.out" }}, a.s); }},
      collapse: a => tl.to(a.t + "-b", {{ rotation: 22, y: 140, opacity: 0, duration: 1.6, ease: "power2.in" }}, a.s),
      roll: a => {{ tl.to(a.t, {{ x: a.to, duration: a.d, ease: "power2.inOut" }}, a.s);
                   tl.to(a.t + "-b", {{ rotation: a.deg || 200, duration: a.d, ease: "power2.inOut" }}, a.s); }},
      sink: a => tl.to(a.t + "-b", {{ y: a.by || 90, rotation: 8, duration: a.d, ease: "power1.in" }}, a.s),
      tint: a => tl.to(a.t + "-liq", {{ fill: a.color, duration: a.d, ease: "power1.inOut" }}, a.s),
      flicker: a => tl.to(a.t + "-flame", {{ scaleY: 0.82, transformOrigin: "50% 100%", duration: 0.16, repeat: n(a.d, 0.16), yoyo: true }}, a.s),
      glow: a => tl.fromTo(a.t, {{ opacity: 0.55 }}, {{ opacity: 0.95, duration: 1.4, repeat: n(a.d, 1.4), yoyo: true, ease: "sine.inOut", immediateRender: false }}, a.s),
      twinkle: a => tl.fromTo(a.t, {{ opacity: 0.6 }}, {{ opacity: 1, duration: 1.1, repeat: n(a.d, 1.1), yoyo: true, ease: "sine.inOut", immediateRender: false }}, a.s),
      rain: a => tl.fromTo(a.t, {{ y: -{H} }}, {{ y: 0, duration: 0.7, repeat: n(a.d, 0.7), ease: "none", immediateRender: false }}, a.s),
      flash: a => [0.6, 2.3, 3.4].filter(o => o < a.d - 0.4).forEach(o => {{
        tl.to([a.t, a.bolt], {{ opacity: 0.85, duration: 0.05 }}, a.s + o);
        tl.to([a.t, a.bolt], {{ opacity: 0, duration: 0.4 }}, a.s + o + 0.05); }}),
      rays: a => {{ tl.to(a.t, {{ opacity: 0.32, duration: 1.4, ease: "power1.out" }}, a.s + 0.3);
                   tl.to(a.t, {{ opacity: 0.18, duration: 1.6, repeat: n(a.d - 1.7, 1.6), yoyo: true, ease: "sine.inOut" }}, a.s + 1.7); }},
      sparkle: a => {{ tl.to(a.t, {{ opacity: 1, duration: 0.8 }}, a.s + 0.4);
                      tl.to(a.t, {{ opacity: 0.4, duration: 0.6, repeat: n(a.d - 1.2, 0.6), yoyo: true }}, a.s + 1.2); }},
    }};
    PLAN.beats.forEach(b => {{
      tl.fromTo("#" + b.id + "-in", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.35, immediateRender: false }}, b.s);
      tl.to("#" + b.id + "-in", {{ opacity: 0, duration: 0.3 }}, b.s + b.d - 0.3);
      tl.fromTo("#" + b.id + "-in", {{ scale: 1.24 }}, {{ scale: 1.31, duration: b.d, ease: "none", transformOrigin: "50% 72%", immediateRender: false }}, b.s);
    }});
    PLAN.anims.forEach(a => F[a.do](a));
    for (let i = 0; i < PLAN.caps; i++)
      tl.fromTo("#cap-" + i + "-t", {{ opacity: 0, y: 18 }}, {{ opacity: 1, y: 0, duration: 0.25, ease: "power2.out", immediateRender: false }},
                Number(document.getElementById("cap-" + i).dataset.start));
    tl.fromTo("#title-t", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.6, immediateRender: false }}, 0.1);
    tl.to("#title-t", {{ opacity: 0, duration: 0.5 }}, 2.6);
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
    voice, slots, total = narrate(story, out)
    if total > MAX_TOTAL:
        sys.exit(f"{story_id}: {total:.1f} s is over the {MAX_TOTAL} s Shorts limit; trim its narration")
    music(total, os.path.join(out, "assets", "music.wav"))
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(render_html(story, voice, slots, total))
    print(f"{story_id}: {len(slots)} beats, {total:.1f} s -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
