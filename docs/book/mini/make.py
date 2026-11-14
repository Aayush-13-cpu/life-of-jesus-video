"""story.json -> assets/voice.wav + index.html: a narrated, animated 1920x1080 HyperFrames page."""
import html, json, os
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

LEAD, TAIL = 0.5, 1.0                       # seconds of silence before and after each spoken line
story = json.load(open("story.json", encoding="utf-8"))
k = Kokoro("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")

# 1. Speak every beat and measure it. The voice decides how long each scene lasts.
clips, starts, t = [], [], 0.0
for beat in story["beats"]:
    audio, sr = k.create(beat["say"], voice="af_heart", speed=0.94, lang="en-us")
    clips.append(audio)
    starts.append(round(t, 3))
    t = round(t + LEAD + len(audio) / sr + TAIL, 3)
total = t

# 2. Put all the clips on one sound track, each one LEAD seconds into its scene.
track = np.zeros(int(total * sr) + 1, np.float32)
for s, a in zip(starts, clips):
    i = int((s + LEAD) * sr)
    track[i:i + len(a)] = a
os.makedirs("assets", exist_ok=True)
sf.write("assets/voice.wav", track, sr)

# 3. One <section> per beat (a hill, maybe a sun, a robed figure, a caption), and the tweens that move them.
L = 'class="line" pathLength="1"'
sections, tweens = [], []
for n, (beat, s) in enumerate(zip(story["beats"], starts)):
    d = round((starts[n + 1] if n + 1 < len(starts) else total) - s, 3)
    sun = f'<circle {L} cx="1400" cy="300" r="70"/>' if beat.get("sun") else ""
    sections.append(f"""
  <section id="b{n}" class="clip" data-start="{s}" data-duration="{d}" data-track-index="1">
    <svg viewBox="0 0 1920 1080"><path {L} d="M0 820 Q960 700 1920 820"/>{sun}
      <g id="b{n}-fig" transform="translate(600,850) scale(1.6)">
        <path {L} d="M-30 0 C-28 -60 -24 -118 -17 -150 Q0 -160 17 -150 C24 -118 28 -60 30 0 Z"/>
        <circle {L} cx="0" cy="-172" r="15"/></g></svg>
    <div class="cap">{html.escape(beat["say"])}</div>
  </section>""")
    tweens.append(f'tl.fromTo("#b{n} .line", {{strokeDashoffset: 1}}, {{strokeDashoffset: 0, duration: 2, stagger: 0.3}}, {s});')
    tweens.append(f'tl.fromTo("#b{n}-fig", {{x: 600}}, {{x: 1100, duration: {d}, ease: "none"}}, {s});')
    tweens.append(f'tl.fromTo("#b{n} .cap", {{opacity: 0}}, {{opacity: 1, duration: 0.5}}, {round(s + LEAD, 3)});')

# 4. The page: the HyperFrames contract (a root with an id, timed clips, the audio, one paused timeline).
page = f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(story["title"])}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  body {{ margin: 0; }}
  #root {{ position: relative; width: 1920px; height: 1080px; overflow: hidden; background: #0a0c22; }}
  .clip, svg {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
  .line {{ fill: none; stroke: #f0d79c; stroke-width: 3; stroke-dasharray: 1; stroke-dashoffset: 1; }}
  .cap {{ position: absolute; left: 160px; right: 160px; bottom: 70px; text-align: center; color: #fff8ec;
          font: 600 60px Georgia, serif; text-shadow: 0 0 16px #000; }}
</style></head><body>
<div id="root" data-composition-id="mini" data-start="0" data-duration="{total}" data-width="1920" data-height="1080">
{"".join(sections)}
  <audio id="voice" src="assets/voice.wav" data-start="0" data-duration="{total}" data-volume="1"></audio>
</div>
<script>
  const tl = gsap.timeline({{ paused: true }});
  {chr(10).join("  " + x for x in tweens)}
  window.__timelines = {{ mini: tl }};
</script></body></html>"""
open("index.html", "w", encoding="utf-8").write(page)
print(f"index.html: {len(starts)} scenes, {total} seconds")
