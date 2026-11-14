"""Self-check for every story, without TTS or rendering: python shorts/test_shorts.py  (must print ok)"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
from build_short import all_stories, estimate, render_html, timings, chunks, TEMPLATE, MAX_TOTAL, WPS

ACTIONS = set(re.findall(r"^\s{6}(\w+): a =>", TEMPLATE, re.M))
assert {"walk", "raise", "rock", "flash", "rain"} <= ACTIONS, ACTIONS
KINDS = set(kit.PROPS) | kit.PEOPLE | {"crowd"}
FX = {"rain", "lightning", "rays", "sparkle"}

stories = all_stories()
assert len(stories) >= 40 and len({s["id"] for s in stories}) == len(stories), "story ids must be unique"
assert all(s.get("style", "silhouette") in kit.STYLES for s in stories)
for st in stories:
    sid = st["id"]
    assert estimate(st) <= MAX_TOTAL - 2, f"{sid}: ~{estimate(st):.0f} s is too close to the 60 s Shorts limit"
    for b in st["beats"]:
        assert b.get("sky", "day") in kit.SKIES and b.get("ground", "hills") in ("hills", "field", "desert", "city", "sea", "garden"), sid
        assert set(b.get("fx", [])) <= FX, (sid, b.get("fx"))
        for j, c in enumerate(b.get("cast", [])):
            assert c["k"] in KINDS, (sid, c["k"])
            assert "in" not in c or (0 <= c["in"] < j and b["cast"][c["in"]]["k"] in set(kit.PROPS) | kit.PEOPLE), (sid, j)
            for a in c.get("acts", []):
                assert a["do"] in ACTIONS, (sid, a["do"])
                assert a["do"] not in ("walk", "run", "roll", "fly", "climb") or "to" in a, (sid, a)
    voice = [len(b["say"].split()) / WPS for b in st["beats"]]
    slots = timings(voice)
    total = round(slots[-1][0] + slots[-1][1] + 1.2, 3)
    page = render_html(st, voice, slots, total)
    ids = re.findall(r'\sid="([^"]+)"', page)
    assert len(ids) == len(set(ids)), (sid, sorted({i for i in ids if ids.count(i) > 1})[:5])
    assert f'data-duration="{total}"' in page and 'window.__timelines["story-short"]' in page
    assert "letterSpacing" not in page
    assert ("#3b2414" in page) == (st.get("style") == "parchment"), sid  # the right palette is in use
assert chunks("Peace, be still. And the wind ceased") == ["Peace, be still.", "And the wind ceased"]
print(f"ok: {len(stories)} stories, {min(estimate(s) for s in stories):.0f}-{max(estimate(s) for s in stories):.0f} s each")
