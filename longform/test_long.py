"""Self-check for every long-form video, without TTS or rendering: python longform/test_long.py  (must print ok)"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lineart as art
from build_long import (videos, estimate, timings, render_html, chunks, description, stamp, TEMPLATE, END, WPS,
                        MIN_LEN, MAX_LEN)

ACTIONS = set(re.findall(r"^\s{6}(\w+): a =>", TEMPLATE, re.M))
assert {"walk", "raise", "kneel", "rays", "spin", "rise", "descend"} <= ACTIONS, ACTIONS
KINDS = set(art.PROPS) | art.PEOPLE | {"crowd"}

vs = videos()
assert len({v["id"] for v in vs}) == len(vs) and all("--" not in v["id"] for v in vs)
assert len({v["template"] for v in vs}) == len(vs), "every long video has its own template"
for v in vs:
    vid = v["id"]
    assert v["template"] in art.TEMPLATES, vid
    assert len(v["chapters"]) >= 3, f"{vid}: YouTube chapters need at least 3"
    length = sum(estimate(c) for c in v["chapters"])
    # the estimate runs a little long or short of the real voice; keep a margin inside 10-12 minutes
    assert MIN_LEN + 20 <= length <= MAX_LEN - 20, f"{vid}: ~{stamp(length)}, aim for 10:20-11:40"
    for n, ch in enumerate(v["chapters"]):
        where = f"{vid} ch{n}"
        assert estimate(ch) >= 12, f"{where}: YouTube chapters must be at least 10 s"
        assert len(ch["beats"]) >= 2 and ch["title"] and ch["ref"], where  # the title card and verse need room
        for b in ch["beats"]:
            assert b.get("sky", "night") in art.SKIES and b.get("land", "hills") in art.LANDS, (where, b["say"][:30])
            assert set(b.get("fx", [])) <= art.FX, (where, b.get("fx"))
            for j, c in enumerate(b.get("cast", [])):
                assert c["k"] in KINDS, (where, c["k"])
                assert "in" not in c or 0 <= c["in"] < j, (where, j)
                for a in c.get("acts", []):
                    assert a["do"] in ACTIONS, (where, a["do"])
                    assert a["do"] not in ("walk", "roll", "fly", "climb") or "to" in a, (where, a)
        voice = [len(b["say"].split()) / WPS for b in ch["beats"]]
        slots = timings(voice)
        total = round(slots[-1][0] + slots[-1][1] + END, 3)
        page = render_html(v, n, ch, voice, slots, total)
        ids = re.findall(r'\sid="([^"]+)"', page)
        assert len(ids) == len(set(ids)), (where, sorted({i for i in ids if ids.count(i) > 1})[:5])
        assert f'data-duration="{total}"' in page and 'window.__timelines["long-chapter"]' in page
        assert "letterSpacing" not in page and 'id="music"' not in page  # music is laid once, under the whole video
        assert page.count('pathLength="1"') > 20, where  # the scene is line art that draws itself in
        assert art.TEMPLATES[v["template"]]["line"] in page, where
    print(f"  {vid}: {len(v['chapters'])} chapters, ~{stamp(length)} ({v['template']})")

assert chunks("Peace, be still. And the wind ceased") == ["Peace, be still.", "And the wind ceased"]
assert stamp(0) == "0:00" and stamp(61.9) == "1:01" and stamp(3725) == "1:02:05"
txt = description(vs[0], [0.0] + [70.0 * i for i in range(1, len(vs[0]["chapters"]))])
assert "\n0:00 " in txt and "Chapters" in txt  # YouTube turns these into chapters only if the first is 0:00
print(f"ok: {len(vs)} long videos")
