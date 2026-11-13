"""script.json -> narration (Kokoro, open source) + music bed (ffmpeg) + index.html (a HyperFrames composition).

  python build.py      # needs models/kokoro-v1.0.onnx, models/voices-v1.0.bin and ffmpeg on PATH
  npx hyperframes render --output out/video.mp4

Every scene lasts as long as its narration (plus breathing room), so the animation always follows the voice.
"""
import html, json, os, subprocess
import numpy as np

LEAD, TAIL, MIN_SCENE, END_HOLD = 0.7, 1.4, 5.0, 2.5  # seconds
VOICE, SPEED = "af_heart", 0.88  # Kokoro's best-rated English voice, a little slower than default for calm narration
W, H = 1920, 1080

# Line icons drawn on a 100x100 grid; every path animates its stroke from 0 to full length.
ICONS = {
    "star": ["M50 8 L58 42 L92 50 L58 58 L50 92 L42 58 L8 50 L42 42 Z"],
    "house": ["M18 50 L50 22 L82 50", "M28 44 V84 H72 V44", "M44 84 V64 H56 V84"],
    "temple": ["M12 34 L50 12 L88 34 Z", "M20 40 V80", "M35 40 V80", "M50 40 V80", "M65 40 V80", "M80 40 V80", "M10 86 H90"],
    "waves": ["M8 38 Q20 28 32 38 T56 38 T80 38 T92 38", "M8 56 Q20 46 32 56 T56 56 T80 56 T92 56",
              "M8 74 Q20 64 32 74 T56 74 T80 74 T92 74"],
    "mountains": ["M6 82 L34 34 L50 58 L64 40 L94 82 Z"],
    "fish": ["M14 50 Q50 12 86 68", "M14 50 Q50 88 86 32"],
    "sun": ["M50 30 A20 20 0 1 1 49.9 30", "M50 6 V18", "M50 82 V94", "M6 50 H18", "M82 50 H94",
            "M19 19 L27 27", "M73 73 L81 81", "M81 19 L73 27", "M27 73 L19 81"],
    "gate": ["M24 88 V48 A26 26 0 0 1 76 48 V88", "M36 88 V54 A14 14 0 0 1 64 54 V88", "M12 88 H88"],
    "cup": ["M30 18 H70 C70 48 62 58 50 58 C38 58 30 48 30 18 Z", "M50 58 V80", "M34 84 H66"],
    "cross": ["M50 10 V74", "M32 30 H68", "M10 90 Q50 66 90 90"],
    "sunrise": ["M8 76 H92", "M24 76 A26 26 0 0 1 76 76", "M50 38 V24", "M26 48 L17 39", "M74 48 L83 39"],
    "cloud": ["M26 74 H74 A14 14 0 0 0 72 46 A20 20 0 0 0 34 44 A15 15 0 0 0 26 74 Z", "M50 36 V8", "M41 17 L50 8 L59 17"],
}


def narrate(scenes, out="assets/voice.wav"):
    """TTS every scene, lay the clips on one track, return [(start, duration)] per scene and the total length."""
    from kokoro_onnx import Kokoro
    import soundfile as sf
    k = Kokoro("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
    clips, sr = [], 24000
    for s in scenes:
        audio, sr = k.create(s["narration"], voice=VOICE, speed=SPEED, lang="en-us")
        clips.append(np.asarray(audio, np.float32))
    slots = timings([len(c) / sr for c in clips])
    total = slots[-1][0] + slots[-1][1] + END_HOLD
    track = np.zeros(int(total * sr) + 1, np.float32)
    for (start, _), c in zip(slots, clips):
        i = int((start + LEAD) * sr)
        track[i:i + len(c)] = c
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sf.write(out, track, sr)
    return slots, total


def timings(voice_secs):
    """[(start, duration)] for each scene: the narration starts LEAD in, the scene ends TAIL after it."""
    slots, t = [], 0.0
    for v in voice_secs:
        d = round(max(LEAD + v + TAIL, MIN_SCENE), 3)
        slots.append((t, d))
        t = round(t + d, 3)  # rounded each step so a scene starts exactly where the last one ends
    return slots


def music(total, out="assets/music.wav"):
    """A soft piano-and-pad bed (C G Am F, 16 s per chord), generated, so no licensed audio is needed."""
    chords = [(130.81, 164.81, 196.00), (98.00, 123.47, 146.83), (110.00, 130.81, 164.81), (87.31, 110.00, 130.81)]
    pad, arp = [], []
    for i, (f1, f2, f3) in enumerate(chords):
        win = f"if(between(mod(t,64),{i * 16},{i * 16 + 16}),sin(PI*(mod(t,64)-{i * 16})/16),0)"
        pad.append(f"{win}*(sin(2*PI*{f1}*t)+0.7*sin(2*PI*{f2}*t)+0.5*sin(2*PI*{f3}*t)+0.25*sin(2*PI*{2 * f1}*t))")
        note = f"if(eq(mod(floor(mod(t,16)/2),4),0),{2 * f1},if(eq(mod(floor(mod(t,16)/2),4),2),{2 * f3},{2 * f2}))"
        arp.append(f"between(mod(t,64),{i * 16},{i * 16 + 16})*sin(2*PI*{note}*t)")
    expr = f"0.045*({'+'.join(pad)})+0.035*exp(-1.4*mod(t,2))*({'+'.join(arp)})"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"aevalsrc='{expr}':s=48000:d={total}", "-af",
                    f"lowpass=f=1800,aecho=0.8:0.6:400|800:0.35|0.2,afade=t=in:d=2,afade=t=out:st={total - 3}:d=3,"
                    "pan=stereo|c0=c0|c1=c0", out], check=True)


def icon_svg(name, sid):
    paths = "".join(f'<path pathLength="1" d="{d}"/>' for d in ICONS[name])
    return f'<svg id="{sid}-icon" class="icon" viewBox="0 0 100 100">{paths}</svg>'


def render_html(meta, scenes, slots, total):
    """The HyperFrames composition: one root, one timed <section class="clip"> per scene, one paused GSAP timeline."""
    e = html.escape
    events = [s for s in scenes if s["icon"]]  # every scene but the intro gets a dot on the timeline
    dots = "".join(f'<div class="dot" id="dot-{s["id"]}" style="left:{i * 1560 / (len(events) - 1):.1f}px"></div>'
                   for i, s in enumerate(events))
    sections = []
    for s, (start, dur) in zip(scenes, slots):
        sid = s["id"]
        words = "".join(f'<span class="w">{e(w)}</span> ' for w in s["title"].split())
        if s["icon"]:
            body = (f'{icon_svg(s["icon"], sid)}<div class="year" id="{sid}-year">{e(s["year"])}</div>'
                    f'<h1 class="title" id="{sid}-title">{words}</h1>'
                    f'<div class="quote" id="{sid}-quote">“{e(s["quote"])}”<span class="ref">{e(s["ref"])} · KJV</span></div>')
        else:
            body = (f'<h1 class="title big" id="{sid}-title">{words}</h1>'
                    f'<div class="sub" id="{sid}-sub">{e(meta["subtitle"])}</div>')
        sections.append(f'<section id="{sid}" class="clip scene" data-start="{start}" data-duration="{dur}" '
                        f'data-track-index="1"><div class="inner" id="{sid}-inner">{body}</div></section>')
    plan = json.dumps([{"id": s["id"], "start": st, "dur": d, "icon": bool(s["icon"])}
                       for s, (st, d) in zip(scenes, slots)])
    return TEMPLATE.format(total=round(total, 3), sections="\n".join(sections), dots=dots, plan=plan,
                           title=e(meta["title"]), W=W, H=H)


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  @font-face {{ font-family: "Cormorant"; src: url("fonts/CormorantGaramond.ttf"); }}
  @font-face {{ font-family: "Cormorant"; font-style: italic; src: url("fonts/CormorantGaramond-Italic.ttf"); }}
  @font-face {{ font-family: "Cinzel"; src: url("fonts/Cinzel.ttf"); }}
  body {{ margin: 0; background: #070b18; }}
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; isolation: isolate;
          background: radial-gradient(ellipse at 50% 120%, #3a2a1a 0%, #141a33 45%, #070b18 100%);
          color: #f4ead8; font-family: "Cormorant", serif; }}
  #glow {{ position: absolute; width: 1400px; height: 1400px; left: 260px; top: -700px; border-radius: 50%;
          background: radial-gradient(circle, rgba(227,199,138,0.16) 0%, rgba(227,199,138,0) 60%); z-index: 0; }}
  .clip {{ position: absolute; inset: 0; z-index: 2; }}
  .inner {{ position: absolute; left: 0; right: 0; top: 120px; display: flex; flex-direction: column; align-items: center; }}
  .icon {{ width: 200px; height: 200px; fill: none; stroke: #e3c78a; stroke-width: 2.2; stroke-linecap: round;
          stroke-linejoin: round; filter: drop-shadow(0 0 12px rgba(227,199,138,0.45)); }}
  .icon path {{ stroke-dasharray: 1; stroke-dashoffset: 1; }}
  .year {{ margin-top: 26px; font: 30px "Cinzel", serif; letter-spacing: 10px; color: #e3c78a; text-transform: uppercase; }}
  .title {{ margin: 14px 0 0; font-weight: 600; font-size: 104px; line-height: 1.05; text-align: center; }}
  .title.big {{ margin-top: 210px; font-size: 140px; }}
  .w {{ display: inline-block; }}
  .quote {{ margin-top: 34px; max-width: 1240px; text-align: center; font-style: italic; font-size: 50px; line-height: 1.25;
           color: #efe3cc; }}
  .ref {{ display: block; margin-top: 16px; font: 24px "Cinzel", serif; font-style: normal; letter-spacing: 6px; color: #b9a27a; }}
  .sub {{ margin-top: 28px; font: 32px "Cinzel", serif; letter-spacing: 8px; color: #e3c78a; text-transform: uppercase; }}
  #timeline {{ position: absolute; left: 180px; width: 1560px; top: 960px; height: 3px; z-index: 3; }}
  #track {{ position: absolute; inset: 0; background: rgba(244,234,216,0.18); transform-origin: left center; }}
  #progress {{ position: absolute; inset: 0; background: #e3c78a; transform-origin: left center; transform: scaleX(0);
              box-shadow: 0 0 14px rgba(227,199,138,0.7); }}
  .dot {{ position: absolute; top: -9px; width: 20px; height: 20px; margin-left: -10px; border-radius: 50%;
         background: #070b18; border: 2px solid rgba(244,234,216,0.45); }}
</style>
</head>
<body>
<div id="root" data-composition-id="life-of-jesus" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
  <div id="glow"></div>
{sections}
  <div id="timeline"><div id="track"></div><div id="progress"></div>{dots}</div>
  <audio id="voice" src="assets/voice.wav" data-start="0" data-duration="{total}" data-volume="1"></audio>
  <audio id="music" src="assets/music.wav" data-start="0" data-duration="{total}" data-volume="1"></audio>
</div>
<script>
  const PLAN = {plan};
  const TOTAL = {total};
  Promise.all([
    document.fonts.load('600 100px "Cormorant"'), document.fonts.load('italic 50px "Cormorant"'),
    document.fonts.load('30px "Cinzel"'),
  ]).then(() => {{
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#glow", {{ x: -160, scale: 0.9 }}, {{ x: 160, scale: 1.1, duration: TOTAL, ease: "none" }}, 0);
    tl.fromTo("#track", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 1.6, ease: "power2.inOut" }}, 0.4);
    tl.fromTo(".dot", {{ scale: 0, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.4, stagger: 0.06, ease: "back.out(2)" }}, 1.2);
    const events = PLAN.filter(p => p.icon);
    PLAN.forEach(p => {{
      const s = p.start, id = p.id;
      tl.fromTo("#" + id + "-inner", {{ opacity: 1 }}, {{ opacity: 0, duration: 0.5, ease: "power1.in" }}, s + p.dur - 0.5);
      tl.fromTo("#" + id + " .w", {{ opacity: 0, y: 46, rotateX: -60 }},
                {{ opacity: 1, y: 0, rotateX: 0, duration: 0.8, stagger: 0.12, ease: "power3.out" }}, s + 0.45);
      if (!p.icon) {{
        tl.fromTo("#" + id + "-sub", {{ opacity: 0, y: 18 }}, {{ opacity: 1, y: 0, duration: 1.4, ease: "power2.out" }}, s + 1.1);
        return;
      }}
      const k = events.indexOf(p);
      tl.fromTo("#" + id + "-icon path", {{ strokeDashoffset: 1 }}, {{ strokeDashoffset: 0, duration: 1.4, stagger: 0.12, ease: "power2.inOut" }}, s + 0.1);
      tl.fromTo("#" + id + "-icon", {{ scale: 0.85, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.9, ease: "power2.out" }}, s + 0.1);
      // transforms only: letter-spacing snaps to whole pixels and stutters in frame-by-frame capture (lint error)
      tl.fromTo("#" + id + "-year", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 1.0, ease: "power2.out" }}, s + 0.3);
      tl.fromTo("#" + id + "-quote", {{ opacity: 0, y: 24 }}, {{ opacity: 1, y: 0, duration: 1.0, ease: "power2.out" }}, s + 1.3);
      tl.to("#progress", {{ scaleX: k / (events.length - 1), duration: 0.9, ease: "power2.inOut" }}, s + 0.2);
      tl.to("#dot-" + id, {{ backgroundColor: "#e3c78a", borderColor: "#e3c78a", scale: 1.35, duration: 0.5, ease: "back.out(3)" }}, s + 0.6);
      tl.to("#dot-" + id, {{ scale: 1, duration: 0.6, ease: "power2.out" }}, s + 1.1);
    }});
    tl.to("#timeline", {{ opacity: 0, duration: 1.2 }}, TOTAL - 1.4);
    window.__timelines = window.__timelines || {{}};
    window.__timelines["life-of-jesus"] = tl;
  }});
</script>
</body>
</html>
"""


def main():
    data = json.load(open("script.json", encoding="utf-8"))
    slots, total = narrate(data["scenes"])
    music(total)
    open("index.html", "w", encoding="utf-8").write(render_html(data, data["scenes"], slots, total))
    print(f"index.html: {len(slots)} scenes, {total:.1f} s")


if __name__ == "__main__":
    main()
