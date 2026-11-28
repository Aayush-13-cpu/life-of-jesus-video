"""Paper pop-up art for every video: the Shorts (1080x1920) and the long videos (1920x1080) of both channels.

The style, strictly: a pop-up book. Every hill, house, figure and prop is a flat piece of bright card stock with
a soft shadow under it. A scene is a page: its pieces stand up off the page, back to front, each hinged at its
base with a small springy overshoot. Before a new setting they fold flat again and the next page turns over.
Figures move like paper puppets: they slide on a slot, waddle as they walk, and swing their arms on paper
fasteners. Nothing glows and nothing traces itself in. No gradients, no floating dust, no faces (heads are plain
paper ovals). The motion itself lives in paper.js; this module draws the pieces and says which ones pop.

The same file is used in both repos (osho-video, life-of-jesus-video); `world` picks the village
architecture ("asia": tiled roofs and a pagoda; "levant": flat roofs, domes and palms).
Coordinates: x across 0-W, y down 0-H, the horizon at HZ, and every figure or prop is placed by the point where
it touches the ground (GF for the near ground).
"""
import json
import math

# frame: W, H, horizon, near ground, default figure scale, crowd y offset, crowd scale, cloud spots (x, y, size)
FRAMES = {"short": dict(W=1080, H=1920, HZ=1300, GF=1390, s=1.6, cy=-40, cs=0.9,
                        clouds=[(0.2, 0.47, 1.0), (0.8, 0.55, 0.8)]),
          "long": dict(W=1920, H=1080, HZ=760, GF=850, s=1.5, cy=-20, cs=0.8,
                       clouds=[(0.14, 0.2, 1.0), (0.5, 0.32, 0.8), (0.74, 0.16, 0.7)])}
W, H, HZ, GF = 1080, 1920, 1300, 1390
FR = FRAMES["short"]
WORLD = "asia"


def frame(name, world="asia"):
    """Switch every drawing function to a frame and a world (module-level: one page is built per process)."""
    global W, H, HZ, GF, FR, WORLD
    FR, WORLD = FRAMES[name], world
    W, H, HZ, GF = FR["W"], FR["H"], FR["HZ"], FR["GF"]


def rng(seed):
    """Seeded pseudo-random numbers, so 'random' stars and tufts are identical on every render."""
    s = seed & 0x7FFFFFFF

    def r():
        nonlocal s
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        return s / 0x7FFFFFFF
    return r


def _seed(text):
    return sum((i + 1) * ord(ch) for i, ch in enumerate(text))


def mix(a, b, t):
    """Blend two #rrggbb colours: t=0 gives a, t=1 gives b."""
    x, y = (tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in (a, b))
    return "#" + "".join(f"{round(u + (v - u) * t):02x}" for u, v in zip(x, y))


# The light of each sky: the page's backdrop, a paler horizon strip, the clouds, the sun or moon (kind, x and y as
# fractions of the frame, y None = just above the far hills; radius), and the tint that every colour is mixed toward.
SKIES = {
    "day": dict(top="#7cc8ec", band="#b6e3f4", cloud="#ffffff", orb=("sun", 0.84, 0.3, 58), tint=("#ffffff", 0.0)),
    "dawn": dict(top="#f3a49f", band="#fbd2b0", cloud="#fff0e2", orb=("sun", 0.72, None, 70), tint=("#7a4a7a", 0.2)),
    "dusk": dict(top="#ec7a48", band="#f8b65e", cloud="#fbd08c", orb=("sun", 0.26, None, 100), tint=("#6a2a4a", 0.3)),
    "night": dict(top="#1d2858", band="#2c3d78", cloud="#3c4f8e", orb=("moon", 0.76, 0.2, 52), tint=("#0e1640", 0.55)),
    "storm": dict(top="#546378", band="#6e7e96", cloud="#8794a8", orb=None, tint=("#26303c", 0.4)),
}
GROUNDS = ("hills", "field", "desert", "city", "sea", "garden", "forest", "river", "zen", "mountain")

# Card-stock colours for props and figures, before the sky's tint.
PAPER = dict(wood="#a0673a", woodd="#70441f", trunk="#8d5a2b", stone="#a9a395", stoned="#7d786d", gold="#f4c542",
             flame="#ff8a2a", flame2="#ffe066", cloth="#d9534f", cream="#f6ecd6", white="#fbf7ee", water="#4aa3c8",
             leaf="#4caf50", leafd="#2e7d32", leafl="#8bc34a", roof="#c8553d", wall="#f2d6a8", pink="#f48fb1",
             blue="#5c8fd6", clay="#c8703a", ink="#2b2433", grey="#8f8a96", straw="#e2bb62", bronze="#c9963a",
             wool="#f4efe6")
ROBES = {  # kind: robe, sleeve (the robe's shade), accent (sash, scarf, hat, turban)
    "master": ("#e8772e", "#c95f1f", "#f4c542"), "seeker": ("#2f9e9a", "#237a77", "#f2d6a8"),
    "monk": ("#a33b3b", "#7f2a2a", "#e8772e"), "nun": ("#4f5678", "#3c4260", "#fbf7ee"),
    "man": ("#4f7fc0", "#3a62a0", "#f2d6a8"), "woman": ("#d6587e", "#b0405f", "#f4b942"),
    "child": ("#f2c14e", "#d9a52e", "#4caf50"), "elder": ("#8a77b8", "#6c5a98", "#fbf7ee"),
    "dancer": ("#c8408c", "#a02e6e", "#f4c542"), "samurai": ("#2c3e78", "#1f2d5c", "#c0c4cc"),
    "farmer": ("#6aa84f", "#4f8a3a", "#e8c068"), "nasruddin": ("#7b3fa0", "#5e2e80", "#fbf7ee"),
    "jesus": ("#f6f1e6", "#ddd5c4", "#b83a3a"), "mary": ("#2f6fc0", "#2456a0", "#9cc3ef"),
    "angel": ("#fbf7ee", "#e8e0cc", "#f4c542"), "shepherd": ("#a0703a", "#7d5528", "#e8d8b0"),
    "widow": ("#4a3a5a", "#382a46", "#6a5a7a"),
}
CROWD = [("#4f7fc0", "#3a62a0"), ("#d6587e", "#b0405f"), ("#6aa84f", "#4f8a3a"), ("#e8a33a", "#c9862a"),
         ("#8a77b8", "#6c5a98"), ("#2f9e9a", "#237a77"), ("#c8553d", "#a3402c")]
SKINS = ["#c68a5a", "#b47a4c", "#d39a6a", "#a86e44"]
PEOPLE = set(ROBES)
GLOW = {"master", "jesus", "angel"}   # figures with a paper sunburst behind them (never a face or a portrait)
SIZES = {"child": 0.62, "master": 1.06, "jesus": 1.06}
SKY = SKIES["day"]
T = dict(PAPER)


def use(sky):
    """Tint every colour for a sky: night pieces are deep blue card, dawn ones rose, day ones bright."""
    global SKY, T
    SKY = SKIES[sky]
    tint, k = SKY["tint"]
    T = {name: mix(c, tint, k * 0.5) for name, c in PAPER.items()}


def tone(c, k=1.0):
    """A land colour under the current sky (the land takes the full tint, props and people half)."""
    tint, kk = SKY["tint"]
    return mix(c, tint, kk * k)


def piece(p, markup, cls="", extra=""):
    """One cut-out: a group with the paper shadow that paper.js stands up (class pp) when its page opens."""
    return f'<g class="pp{(" " + cls) if cls else ""}" filter="url(#{p}-sh)"{extra}>{markup}</g>'


def ridge(base, amp, waves, phase, fill):
    """A strip of card cut along a gentle wave and running down off the bottom of the page."""
    pts = " L".join(f"{x} {base + amp * math.sin(x / W * waves * math.pi + phase):.0f}" for x in range(-200, W + 201, 40))
    return f'<path d="M-200 {H + 120} L{pts} L{W + 200} {H + 120} Z" fill="{fill}"/>'


def _cloud(x, y, s, col):
    bumps = [(-80, -40, 50), (-10, -72, 70), (70, -46, 55), (130, -24, 36)]
    return (f'<g transform="translate({x:.0f},{y:.0f}) scale({s:.2f})" fill="{col}">'
            + "".join(f'<circle cx="{a}" cy="{b}" r="{r}"/>' for a, b, r in bumps)
            + '<rect x="-130" y="-42" width="290" height="42" rx="21"/></g>')


def _star(x, y, r):
    return (f'<path d="M{x:.0f} {y - r:.0f} L{x + r * 0.28:.1f} {y - r * 0.28:.1f} L{x + r:.0f} {y:.0f} '
            f'L{x + r * 0.28:.1f} {y + r * 0.28:.1f} L{x:.0f} {y + r:.0f} L{x - r * 0.28:.1f} {y + r * 0.28:.1f} '
            f'L{x - r:.0f} {y:.0f} L{x - r * 0.28:.1f} {y - r * 0.28:.1f} Z"/>')


def backdrop(p, sky, orb_shown=True):
    """The page itself (flat sky card and a paler horizon strip, stars printed on it at night), plus its pop-up
    pieces: the sun or moon on its tab and a few clouds. Returns (markup, anims)."""
    s = SKIES[sky]
    out = [f'<defs><filter id="{p}-sh" x="-25%" y="-25%" width="150%" height="150%">'
           f'<feDropShadow dx="0" dy="6" stdDeviation="5" flood-color="#1c0f05" flood-opacity="0.38"/></filter></defs>',
           f'<rect x="-200" y="-200" width="{W + 400}" height="{H + 400}" fill="{s["top"]}"/>',
           ridge(HZ - 230, 26, 1.6, 0.7, s["band"])]
    anims = []
    if sky == "night":
        r = rng(7)
        stars = "".join(_star(r() * W, r() * (HZ - 260), 4 + r() * 7) for _ in range(46))
        out.append(f'<g id="{p}-stars" fill="#ffe9a8">{stars}</g>')
        anims.append({"t": f"#{p}-stars", "do": "twinkle"})
    orb = s["orb"]
    left = orb is not None and orb[1] < 0.5
    if orb and orb_shown:  # off when the cast brings its own moon
        kind, ox, oy, rad = orb
        x, y = ox * W, (oy * H if oy is not None else HZ - 130)
        if kind == "sun":
            col = "#ffd447" if sky == "day" else "#ffe066"
            m = (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rad * 1.45:.0f}" fill="{mix(col, s["top"], 0.55)}"/>'
                 f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rad}" fill="{col}"/>')
        else:  # a crescent cut from cream card
            m = (f'<path d="M{x:.0f} {y - rad:.0f} A{rad} {rad} 0 1 0 {x:.0f} {y + rad:.0f} A{rad * 0.72:.0f} {rad} 0 1 1 '
                 f'{x:.0f} {y - rad:.0f} Z" fill="#f6efc6"/>')
        out.append(piece(p, m))
    if sky != "night":
        for k, (cx, cy, cs) in enumerate(FR["clouds"]):
            if sky in ("storm", "day") or k < 2:
                out.append(piece(p, f'<g id="{p}-cl{k}">{_cloud((1 - cx if left else cx) * W, cy * H, cs, s["cloud"])}</g>'))
                anims.append({"t": f"#{p}-cl{k}", "do": "drift", "amp": 22 + 8 * k, "period": 16 + 4 * k})
    return "".join(out), anims


def _roof(x, y, w, col, lift=26):
    """A tiled roof with upturned eaves over a wall of width w whose top is at y."""
    a = w / 2 + 22
    return (f'<path d="M{x - a:.0f} {y} Q{x - a * 0.6:.0f} {y - lift * 0.7:.0f} {x - a * 0.4:.0f} {y - lift} '
            f'L{x + a * 0.4:.0f} {y - lift} Q{x + a * 0.6:.0f} {y - lift * 0.7:.0f} {x + a:.0f} {y} Z" fill="{col}"/>')


def _pagoda(wall, roof, tiers=4, w=150, th=64):
    """A pagoda around (0,0): walls shrinking upwards, each under its own roof, and a spire."""
    out, y = [], 0
    for k in range(tiers):
        ww = w * (1 - 0.15 * k)
        out.append(f'<rect x="{-ww * 0.4:.0f}" y="{y - th}" width="{ww * 0.8:.0f}" height="{th}" fill="{wall}"/>'
                   f'<rect x="{-ww * 0.12:.0f}" y="{y - th + 18}" width="{ww * 0.24:.0f}" height="{th - 18}" fill="{roof}" opacity="0.55"/>'
                   + _roof(0, y - th, ww, roof))
        y -= th + 22
    return "".join(out) + f'<rect x="-4" y="{y - 70}" width="8" height="80" fill="{roof}"/><circle cx="0" cy="{y - 74}" r="9" fill="#f4c542"/>'


def _pine(x, y, h, w, col):
    """A pine of three stacked paper triangles on a short trunk."""
    tiers = "".join(f'<path d="M{x:.0f} {y - h * (0.42 + 0.29 * k):.0f} L{x + w * (0.5 - 0.1 * k):.0f} {y - h * (0.1 + 0.29 * k):.0f} '
                    f'L{x - w * (0.5 - 0.1 * k):.0f} {y - h * (0.1 + 0.29 * k):.0f} Z"/>' for k in range(3))
    return (f'<rect x="{x - w * 0.06:.0f}" y="{y - h * 0.14:.0f}" width="{w * 0.12:.0f}" height="{h * 0.16:.0f}" fill="{tone("#6e4a2a")}"/>'
            f'<g fill="{col}">{tiers}</g>')


def _flowers(r, y0, y1, n, cols):
    return "".join(f'<circle cx="{r() * W:.0f}" cy="{y0 + r() * (y1 - y0):.0f}" r="{5 + r() * 5:.0f}" fill="{cols[int(r() * len(cols))]}"/>'
                   for _ in range(n))


def _palm(x, y, h, trunk, leaf):
    fronds = "".join(f'<path d="M{x:.0f} {y - h} q{d * 60} {-40 + k * 18} {d * 130} {10 + k * 40} '
                     f'q{-d * 60} {-30 + k * 10} {-d * 130} {-10 - k * 40} Z"/>' for d in (-1, 1) for k in range(2))
    return (f'<path d="M{x - 8:.0f} {y} Q{x - 20:.0f} {y - h / 2:.0f} {x - 4:.0f} {y - h} L{x + 6:.0f} {y - h} '
            f'Q{x - 6:.0f} {y - h / 2:.0f} {x + 8:.0f} {y} Z" fill="{trunk}"/><g fill="{leaf}">{fronds}</g>')


def land(p, name):
    """The ground: a few strips of card, far to near, each its own pop-up piece. Returns (markup, anims)."""
    r = rng(_seed(name))
    front = GF + (H - GF) * 0.45
    hills = [ridge(HZ - 70, 55, 3, 0.5, tone("#9fd18b")), ridge(HZ - 10, 40, 2.2, 2.0, tone("#6dbb5e"))]
    near = ridge(GF - 20, 22, 1.6, 4.0, tone("#4a9a48"))
    lip = ridge(front, 16, 2.4, 1.3, tone("#3d8a3e")) + _flowers(r, front + 40, H - 30, 14,
                                                                 [tone("#f48fb1"), tone("#ffe066"), tone("#ffffff")])
    anims = []
    if name == "hills":
        ps = hills + [near, lip]
    elif name == "field":
        rows = "".join(f'<path d="M{x:.0f} {GF + 12 + k * 46} l-7 -{26 + r() * 14:.0f} l7 8 l7 -{22 + r() * 12:.0f} l3 22 Z"/>'
                       for k in range(3) for x in [r() * W for _ in range(int(W / 36))])
        ps = [hills[0], ridge(HZ - 10, 30, 2.0, 1.2, tone("#e8c75a")),
              ridge(GF - 20, 16, 1.4, 0.3, tone("#d4a843")) + f'<g fill="{tone("#b8892e")}">{rows}</g>',
              ridge(front, 14, 2.0, 2.2, tone("#c39436"))]
    elif name == "desert":
        ps = [ridge(HZ - 30, 26, 2, 1.0, tone("#f4cf8c")), ridge(HZ + 20, 30, 1.3, 2.6, tone("#ebb46a")),
              ridge(GF, 12, 1.0, 3.3, tone("#dc9a50")), ridge(front, 18, 1.7, 0.4, tone("#c98642"))]
    elif name == "city":
        if WORLD == "levant":  # flat roofs, small dark windows, white domes and a palm
            houses = "".join(f'<rect x="{f * W - w / 2:.0f}" y="{HZ - h}" width="{w}" height="{h + 60}" fill="{tone(c)}"/>'
                             f'<rect x="{f * W - 10:.0f}" y="{HZ - h + 26}" width="20" height="26" fill="{tone("#5a3a2a")}"/>'
                             for f, w, h, c in [(0.05, 90, 150, "#f2d6a8"), (0.16, 120, 95, "#e9c48e"), (0.29, 70, 210, "#f6e2bc"),
                                                (0.4, 170, 120, "#ecc89a"), (0.58, 100, 170, "#f2d6a8"), (0.7, 150, 105, "#e3b984"),
                                                (0.84, 80, 190, "#f6e2bc"), (0.95, 110, 130, "#ecc89a")])
            domes = "".join(f'<path d="M{f * W - rr:.0f} {HZ - h} A{rr} {rr} 0 0 1 {f * W + rr:.0f} {HZ - h} Z" fill="{tone("#fbf7ee")}"/>'
                            for f, h, rr in [(0.4, 120, 62), (0.29, 210, 28), (0.58, 170, 40), (0.84, 190, 32)])
            ps = [hills[0], houses + domes + _palm(0.5 * W, HZ + 30, 230, tone("#8d5a2b"), tone("#4f9a48")),
                  ridge(GF - 10, 10, 1.2, 0.8, tone("#d8b47a")), ridge(front, 12, 1.6, 2.0, tone("#c49a62"))]
        else:  # a village of tiled roofs with a pagoda above them
            cols = ["#f2d6a8", "#f6e2bc", "#e9c48e", "#f0c9c0"]
            houses = "".join(f'<rect x="{f * W - w / 2:.0f}" y="{HZ - h}" width="{w}" height="{h + 60}" fill="{tone(cols[k % 4])}"/>'
                             f'<rect x="{f * W - 14:.0f}" y="{HZ - h + 22}" width="28" height="24" fill="{tone("#ffd36a")}"/>'
                             + _roof(f * W, HZ - h, w, tone("#c8553d" if k % 2 else "#a8452f"))
                             for k, (f, w, h) in enumerate([(0.06, 110, 70), (0.19, 130, 95), (0.33, 100, 60), (0.48, 150, 85),
                                                            (0.64, 110, 65), (0.91, 120, 80)]))
            pag = f'<g transform="translate({0.78 * W:.0f},{HZ}) scale(0.9)">{_pagoda(tone("#f6e2bc"), tone("#c8553d"))}</g>'
            ps = [hills[0], pag, houses, ridge(GF - 10, 10, 1.2, 0.8, tone("#c9a26b")), ridge(front, 12, 1.6, 2.0, tone("#b38a55"))]
    elif name == "sea":  # distant hills, then three strips of paper waves sliding against each other
        def waves(y, col, amp):
            crest = " ".join(f"q30 -{amp} 60 0" for _ in range((W + 480) // 60))
            return f'<path d="M-240 {y:.0f} {crest} L{W + 240} {H + 120} L-240 {H + 120} Z" fill="{col}"/>'
        ps = [ridge(HZ - 25, 18, 2, 1.5, tone("#8fbf9f")),
              f'<g id="{p}-w0">{waves(HZ, tone("#7cc4dc"), 14)}</g>',
              f'<g id="{p}-w1">{waves(HZ + (GF - HZ) * 1.4, tone("#4aa3c8"), 18)}</g>',
              f'<g id="{p}-w2">{waves(front, tone("#2f86ad"), 22)}</g>']
        anims += [{"t": f"#{p}-w{k}", "do": "drift", "amp": 18 + 8 * k, "period": 7 - k * 1.5} for k in range(3)]
    elif name == "garden":
        bushes = "".join(f'<circle cx="{f * W:.0f}" cy="{GF - 20}" r="{rr}"/>' for f, rr in [(0.05, 70), (0.14, 50), (0.86, 60), (0.96, 80)])
        blooms = _flowers(r, GF - 110, GF - 10, 18, [tone("#f48fb1"), tone("#ffe066"), tone("#ffffff")])
        ps = hills + [near, f'<g fill="{tone("#3f9a5a")}">{bushes}</g>{blooms}', lip]
    elif name == "forest":
        far = "".join(_pine(x, HZ, 230 + (x * 7) % 90, 120, tone("#4f9a6a")) for x in range(-20, W + 60, 75))
        mid = "".join(_pine(x, HZ + 60, 330 + (x * 13) % 120, 160, tone("#2f7a4f")) for x in range(20, W + 60, 160))
        ps = [hills[0], far, mid, ridge(GF - 10, 12, 1.4, 2.0, tone("#3f8a48")), lip]
    elif name == "river":  # a blue paper river winding across the near ground, its waves sliding
        y = GF + (H - GF) * 0.25
        band = (f'<path d="M-240 {y:.0f} C{W * 0.3:.0f} {y - 50:.0f} {W * 0.65:.0f} {y + 80:.0f} {W + 240} {y + 10:.0f} '
                f'L{W + 240} {y + 120:.0f} C{W * 0.65:.0f} {y + 190:.0f} {W * 0.3:.0f} {y + 60:.0f} -240 {y + 110:.0f} Z" fill="{tone("#4aa3c8")}"/>')
        lines = "".join(f'<path d="M{r() * W:.0f} {y + 30 + r() * 60:.0f} q15 -8 30 0 q15 -8 30 0" fill="none" stroke="{tone("#bfe6f5")}" '
                        f'stroke-width="5" stroke-linecap="round"/>' for _ in range(int(W / 70)))
        ps = hills + [near + band + f'<g id="{p}-waves">{lines}</g>', lip]
        anims.append({"t": f"#{p}-waves", "do": "drift", "amp": 30, "period": 4})
    elif name == "zen":  # a raked-sand garden behind a low wall, three stones with rings raked around them
        wall = (f'<rect x="-200" y="{HZ - 70}" width="{W + 400}" height="90" fill="{tone("#efe2c4")}"/>'
                f'<rect x="-200" y="{HZ - 88}" width="{W + 400}" height="22" fill="{tone("#7a5a48")}"/>')
        rakes = "".join(f'<path d="M-200 {y} H{W + 200}"/>' for y in range(int(GF + 30), H, 30))
        stones = ([(0.23, GF + 160, 60), (0.59, GF + 260, 85), (0.83, GF + 120, 40)] if H > W else
                  [(0.22, GF + 110, 60), (0.61, GF + 150, 90), (0.81, GF + 80, 44)])
        rings = "".join(f'<ellipse cx="{f * W:.0f}" cy="{y}" rx="{rr + k * 26}" ry="{(rr + k * 26) * 0.35:.0f}"/>'
                        for f, y, rr in stones for k in (3, 2, 1))
        sand = (f'<rect x="-200" y="{GF - 10}" width="{W + 400}" height="{H - GF + 140}" fill="{tone("#efe4cc")}"/>'
                f'<g fill="none" stroke="{tone("#d6c4a0")}" stroke-width="3">{rakes}{rings}</g>')
        rocks = "".join(f'<ellipse cx="{f * W:.0f}" cy="{y - rr * 0.3:.0f}" rx="{rr}" ry="{rr * 0.6:.0f}" fill="{tone("#8a8478")}"/>'
                        f'<ellipse cx="{f * W - rr * 0.25:.0f}" cy="{y - rr * 0.5:.0f}" rx="{rr * 0.45:.0f}" ry="{rr * 0.2:.0f}" fill="{tone("#a8a294")}"/>'
                        for f, y, rr in stones)
        ps = [hills[0], wall, sand, rocks]
    elif name == "mountain":
        peaks = [(-0.04, 20), (0.22, -420), (0.35, -250), (0.52, -620), (0.7, -300), (0.83, -440), (1.04, 0)]
        if H < W:  # the long frame has less sky: lower peaks
            peaks = [(f, round(dy * 0.55)) for f, dy in peaks]
        rock = " L".join(f"{f * W:.0f} {HZ + dy}" for f, dy in peaks)
        snow = "".join(f'<path d="M{f * W - 70:.0f} {HZ + dy + 110} L{f * W:.0f} {HZ + dy} L{f * W + 70:.0f} {HZ + dy + 110} '
                       f'L{f * W + 30:.0f} {HZ + dy + 90} L{f * W:.0f} {HZ + dy + 115} L{f * W - 30:.0f} {HZ + dy + 90} Z"/>'
                       for f, dy in peaks if dy < -200)
        ps = [f'<path d="M-200 {H + 120} L{rock} L{W + 200} {H + 120} Z" fill="{tone("#8aa0c8")}"/><g fill="{tone("#ffffff")}">{snow}</g>',
              hills[1], near, lip]
    else:
        raise ValueError(f"unknown ground {name!r}")
    return "".join(piece(p, m) for m in ps), anims


LANDS = GROUNDS

# Props: (0,0) is the point that touches the ground. {colour} names come from PAPER (tinted for the sky);
# parts named {pid}-... are found by actions (a flame flickers, a cup's tea changes, a cage door opens).
_BAMBOO = "".join(f'<rect x="{x - 8}" y="-{h}" width="16" height="{h}" fill="{{leafl}}"/>'
                  + "".join(f'<rect x="{x - 10}" y="-{y}" width="20" height="6" fill="{{leafd}}"/>' for y in range(90, h, 90))
                  + f'<path d="M{x} -{h - 40} q40 -10 70 -40 q-40 6 -70 30 Z M{x} -{h - 120} q-40 -10 -66 -36 q36 4 66 26 Z" fill="{{leaf}}"/>'
                  for x, h in [(-50, 560), (0, 620), (46, 520)])
PROPS = {
    "boat": '<path d="M-210 -40 L210 -40 L160 40 L-160 40 Z" fill="{wood}"/><path d="M-200 -28 L200 -28 L193 -14 L-193 -14 Z" fill="{cloth}"/>'
            '<rect x="-5" y="-330" width="10" height="295" fill="{woodd}"/><path d="M8 -320 L8 -70 L170 -70 Z" fill="{cream}"/>'
            '<path d="M-8 -290 L-8 -80 L-110 -80 Z" fill="{white}"/>',
    "tree": '<path d="M-18 0 C-12 -90 -14 -180 -4 -260 L8 -260 C16 -180 14 -90 22 0 Z" fill="{trunk}"/>'
            '<g fill="{leafd}"><circle cx="-120" cy="-230" r="60"/><circle cx="125" cy="-240" r="70"/><circle cx="-70" cy="-300" r="95"/></g>'
            '<g fill="{leaf}"><circle cx="60" cy="-320" r="105"/><circle cx="0" cy="-400" r="110"/></g>'
            '<g fill="{leafl}"><circle cx="-20" cy="-440" r="45"/><circle cx="90" cy="-360" r="38"/></g>',
    "house": '<rect x="-150" y="-210" width="300" height="210" fill="{wall}"/><rect x="-170" y="-236" width="340" height="30" fill="{roof}"/>'
             '<rect x="-40" y="-120" width="60" height="120" fill="{woodd}"/><rect x="70" y="-170" width="40" height="40" fill="{gold}"/>',
    "rock": '<path d="M-230 0 C-240 -90 -150 -170 -20 -160 C110 -170 240 -100 230 0 Z" fill="{stoned}"/>'
            '<path d="M-150 -60 C-140 -120 -60 -150 20 -145 C-40 -120 -100 -90 -150 -60 Z" fill="{stone}"/>',
    "jar": '<path d="M-38 0 C-60 -40 -60 -120 -30 -150 L-24 -175 L24 -175 L30 -150 C60 -120 60 -40 38 0 Z" fill="{clay}"/>'
           '<rect x="-50" y="-110" width="100" height="10" fill="{cream}"/>'
           '<ellipse id="{pid}-liq" cx="0" cy="-172" rx="22" ry="6" fill="{water}"/>',
    "basket": '<path d="M-70 -50 L70 -50 L55 0 L-55 0 Z" fill="{straw}"/><path d="M-64 -34 H64 M-60 -18 H60" stroke="{wood}" stroke-width="5"/>'
              '<circle cx="-35" cy="-56" r="18" fill="#f08a2e"/><circle cx="0" cy="-62" r="20" fill="#d9483b"/><circle cx="35" cy="-56" r="18" fill="#f4c542"/>',
    "sheep": '<g fill="{wool}"><circle cx="-30" cy="-60" r="30"/><circle cx="5" cy="-70" r="34"/><circle cx="35" cy="-58" r="28"/></g>'
             '<ellipse cx="68" cy="-72" rx="18" ry="14" fill="{ink}"/><rect x="-30" y="-35" width="7" height="35" fill="{ink}"/>'
             '<rect x="25" y="-35" width="7" height="35" fill="{ink}"/>',
    "pig": '<ellipse cx="0" cy="-50" rx="70" ry="38" fill="#f4a6b8"/><ellipse cx="72" cy="-58" rx="22" ry="18" fill="#f4a6b8"/>'
           '<ellipse cx="90" cy="-56" rx="8" ry="7" fill="#e07a92"/><path d="M60 -76 L70 -94 L78 -74 Z" fill="#e07a92"/>'
           '<rect x="-45" y="-20" width="12" height="20" fill="#e07a92"/><rect x="35" y="-20" width="12" height="20" fill="#e07a92"/>',
    "table": '<rect x="-170" y="-90" width="340" height="18" fill="{wood}"/><rect x="-150" y="-80" width="14" height="80" fill="{woodd}"/>'
             '<rect x="136" y="-80" width="14" height="80" fill="{woodd}"/><ellipse cx="-30" cy="-102" rx="45" ry="14" fill="{straw}"/>'
             '<path d="M60 -90 L72 -130 L98 -130 L110 -90 Z" fill="#8a2a45"/>',
    "stone": '<circle cx="0" cy="-95" r="95" fill="{stone}"/><circle cx="0" cy="-95" r="60" fill="{stoned}"/><circle cx="0" cy="-95" r="16" fill="{ink}"/>',
    "coin": '<circle cx="0" cy="-12" r="22" fill="#fff0b0" opacity="0.6"/><circle cx="0" cy="-12" r="12" fill="{gold}"/>',
    "seed": '<circle cx="0" cy="-8" r="24" fill="#fff0b0" opacity="0.55"/><circle cx="0" cy="-8" r="8" fill="{gold}"/>',
    "plant": '<path d="M-3 0 Q-6 -60 0 -120 Q6 -60 3 0 Z" fill="{leafd}"/><path d="M0 -50 Q-40 -70 -48 -100 Q-14 -90 0 -60 Z" fill="{leaf}"/>'
             '<path d="M0 -80 Q40 -100 46 -130 Q12 -122 0 -90 Z" fill="{leafl}"/><circle cx="0" cy="-128" r="12" fill="{gold}"/>',
    "lily": '<path d="M-3 0 Q-4 -70 0 -130 Q4 -70 3 0 Z" fill="{leafd}"/><path d="M0 -130 C-40 -150 -46 -190 -10 -200 C-4 -170 0 -150 0 -130 Z" fill="{white}"/>'
            '<path d="M0 -130 C40 -150 46 -190 10 -200 C4 -170 0 -150 0 -130 Z" fill="{white}"/>'
            '<path d="M0 -130 C-12 -170 0 -215 0 -215 C0 -215 12 -170 0 -130 Z" fill="{cream}"/>',
    "net": '<path d="M-160 0 Q0 -60 160 0 M-160 0 L-120 -80 M-80 -30 L-60 -100 M0 -40 L0 -110 M80 -30 L60 -100 M160 0 L120 -80 '
           'M-130 -50 Q0 -100 130 -50 M-110 -85 Q0 -125 110 -85" fill="none" stroke="{straw}" stroke-width="5" stroke-linecap="round"/>',
    "fish": '<path d="M-30 -20 Q0 -44 30 -20 Q0 4 -30 -20 Z M30 -20 L48 -34 L48 -6 Z" fill="{blue}"/><circle cx="-16" cy="-22" r="3" fill="{white}"/>',
    "fire": '<path d="M-60 0 L60 -16 L60 -4 L-60 12 Z M-60 -16 L60 0 L60 12 L-60 -4 Z" fill="{woodd}"/><path id="{pid}-flame" d="M-28 -14 C-34 -60 -6 -70 0 -110 '
            'C10 -70 36 -60 28 -14 Z" fill="{flame}"/><path d="M-12 -14 C-14 -40 0 -50 0 -70 C6 -46 14 -40 12 -14 Z" fill="{flame2}"/>',
    "star": '<circle cx="0" cy="0" r="120" fill="#fff3c4" opacity="0.35"/><path d="M0 -150 L5 -5 L0 150 L-5 -5 Z M-150 0 L-5 -5 L150 0 L-5 5 Z" fill="#fff6d8"/>'
            '<path d="M0 -70 L14 -14 L70 0 L14 14 L0 70 L-14 14 L-70 0 L-14 -14 Z" fill="{gold}"/>',
    "chest": '<rect x="-80" y="-90" width="160" height="90" fill="{wood}"/><path d="M-90 -90 Q0 -140 90 -90 Z" fill="{woodd}"/>'
             '<rect x="-80" y="-60" width="160" height="10" fill="{bronze}"/><rect x="-14" y="-100" width="28" height="22" fill="{gold}"/>',
    "well": '<rect x="-110" y="-120" width="220" height="120" fill="{stone}"/><path d="M-110 -80 H110 M-110 -40 H110" stroke="{stoned}" stroke-width="5"/>'
            '<rect x="-125" y="-135" width="250" height="22" fill="{stoned}"/><rect x="-95" y="-300" width="12" height="170" fill="{woodd}"/>'
            '<rect x="83" y="-300" width="12" height="170" fill="{woodd}"/><path d="M-130 -300 L0 -350 L130 -300 Z" fill="{roof}"/>',
    "lamp": '<path d="M-40 -10 Q0 10 40 -10 L30 -30 L-30 -30 Z" fill="{clay}"/><path d="M40 -22 L70 -34 L60 -18 Z" fill="{clay}"/>'
            '<path id="{pid}-flame" d="M66 -36 C60 -60 72 -66 74 -84 C80 -66 88 -60 80 -36 Z" fill="{flame}"/>',
    "mat": '<rect x="-110" y="-16" width="220" height="16" rx="6" fill="{cloth}"/><path d="M-90 -8 H90" stroke="{gold}" stroke-width="4"/>',
    "stones": '<g fill="{stone}"><ellipse cx="-40" cy="-14" rx="26" ry="16"/><ellipse cx="50" cy="-16" rx="28" ry="17"/></g>'
              '<ellipse cx="10" cy="-12" rx="20" ry="13" fill="{stoned}"/>',
    "birds": '<g fill="{ink}"><path d="M0 0 q14 -16 28 -2 q14 -14 28 2 q-14 -6 -28 4 q-14 -10 -28 -4 Z"/>'
             '<path d="M70 -40 q10 -12 20 -2 q10 -10 20 2 q-10 -4 -20 3 q-10 -7 -20 -3 Z"/><path d="M-60 -30 q11 -13 22 -2 q11 -11 22 2 q-11 -5 -22 3 q-11 -8 -22 -3 Z"/></g>',
    "lotus": '<ellipse cx="0" cy="-4" rx="95" ry="14" fill="{leaf}"/><g fill="{pink}"><path d="M0 -10 C-34 -18 -64 -46 -66 -74 C-38 -66 -14 -44 0 -10 Z"/>'
             '<path d="M0 -10 C34 -18 64 -46 66 -74 C38 -66 14 -44 0 -10 Z"/></g>'
             '<path d="M0 -10 C-20 -40 -12 -82 0 -104 C12 -82 20 -40 0 -10 Z" fill="#fbd3e0"/><circle cx="0" cy="-30" r="9" fill="{gold}"/>',
    "bodhi": '<path d="M-34 0 C-22 -120 -44 -220 -12 -300 L16 -300 C46 -220 26 -120 38 0 Z" fill="{trunk}"/>'
             '<path d="M-6 -250 C-60 -270 -120 -300 -170 -330 M8 -260 C60 -280 130 -300 180 -340" fill="none" stroke="{trunk}" stroke-width="14"/>'
             '<g fill="{leafd}"><ellipse cx="-170" cy="-350" rx="140" ry="90"/><ellipse cx="180" cy="-355" rx="150" ry="95"/></g>'
             '<ellipse cx="0" cy="-400" rx="300" ry="120" fill="{leaf}"/><ellipse cx="0" cy="-500" rx="200" ry="90" fill="{leafl}"/>',
    "bamboo": _BAMBOO,
    "bell": '<rect x="-120" y="-330" width="16" height="330" fill="{woodd}"/><rect x="104" y="-330" width="16" height="330" fill="{woodd}"/>'
            '<path d="M-150 -330 Q0 -360 150 -330 L150 -312 L-150 -312 Z" fill="{roof}"/><rect x="-4" y="-312" width="8" height="30" fill="{ink}"/>'
            '<path d="M-58 -120 C-58 -220 -46 -282 0 -282 C46 -282 58 -220 58 -120 Z" fill="{bronze}"/><rect x="-70" y="-122" width="140" height="12" fill="{woodd}"/>',
    "cup": '<path d="M-44 -44 H44 C44 -14 26 0 0 0 C-26 0 -44 -14 -44 -44 Z" fill="{white}"/><path d="M-40 -30 H40" stroke="{blue}" stroke-width="5"/>'
           '<ellipse id="{pid}-liq" cx="0" cy="-44" rx="40" ry="8" fill="#9a7a44"/>',
    "teapot": '<ellipse cx="0" cy="-50" rx="62" ry="50" fill="{blue}"/><path d="M50 -60 Q90 -70 100 -110 L110 -104 Q100 -56 56 -34 Z" fill="{blue}"/>'
              '<path d="M-56 -80 C-100 -84 -100 -20 -56 -26" fill="none" stroke="{blue}" stroke-width="10"/>'
              '<ellipse cx="0" cy="-60" rx="40" ry="14" fill="{white}"/><ellipse cx="0" cy="-100" rx="26" ry="8" fill="{white}"/><circle cx="0" cy="-110" r="8" fill="{white}"/>',
    "candle": '<rect x="-16" y="-110" width="32" height="110" fill="{cream}"/><rect x="-2" y="-122" width="4" height="14" fill="{ink}"/>'
              '<path id="{pid}-flame" d="M-9 -122 C-12 -140 -2 -146 0 -166 C4 -146 12 -140 9 -122 Z" fill="{flame}"/>',
    "cushion": '<path d="M-80 0 C-92 -44 -50 -58 0 -58 C50 -58 92 -44 80 0 Z" fill="{cloth}"/><path d="M-60 -24 H60" stroke="{gold}" stroke-width="5"/>',
    "pagoda": "",  # drawn by _prop() (it is built from the tinted colours)
    "hut": '<rect x="-110" y="-130" width="220" height="130" fill="{straw}"/><path d="M-150 -120 L0 -250 L150 -120 Z" fill="{wood}"/>'
           '<rect x="-26" y="-80" width="52" height="80" fill="{gold}"/>',
    "bridge": '<path d="M-280 0 Q0 -170 280 0 L250 0 Q0 -130 -250 0 Z" fill="{roof}"/>'
              '<path d="M-260 -40 Q0 -210 260 -40" fill="none" stroke="{roof}" stroke-width="8"/>'
              + "".join(f'<rect x="{x - 4}" y="{-40 - 170 * (1 - (x / 260) ** 2) * 0.82:.0f}" width="8" height="46" fill="{{roof}}"/>'
                        for x in (-200, -100, 0, 100, 200)),
    "gate": '<rect x="-150" y="-380" width="26" height="380" fill="{roof}"/><rect x="124" y="-380" width="26" height="380" fill="{roof}"/>'
            '<path d="M-220 -400 Q0 -380 220 -400 L230 -440 Q0 -410 -230 -440 Z" fill="{ink}"/><rect x="-180" y="-330" width="360" height="20" fill="{roof}"/>',
    "flute": '<rect x="-70" y="-10" width="140" height="10" rx="5" fill="{straw}"/>'
             '<g fill="{woodd}"><circle cx="-30" cy="-5" r="2.5"/><circle cx="0" cy="-5" r="2.5"/><circle cx="30" cy="-5" r="2.5"/></g>',
    "drum": '<rect x="-60" y="-90" width="120" height="90" fill="{roof}"/><path d="M-60 -70 L60 -20 M-60 -20 L60 -70" stroke="{gold}" stroke-width="4"/>'
            '<ellipse cx="0" cy="-90" rx="60" ry="16" fill="{cream}"/>',
    "donkey": '<g fill="{grey}"><ellipse cx="0" cy="-110" rx="90" ry="44"/><path d="M70 -130 L112 -190 L140 -176 L104 -110 Z"/>'
              '<path d="M112 -192 L104 -236 L120 -196 Z M126 -188 L132 -232 L136 -190 Z"/>'
              '<rect x="-66" y="-80" width="12" height="80"/><rect x="-34" y="-80" width="12" height="80"/>'
              '<rect x="30" y="-80" width="12" height="80"/><rect x="58" y="-80" width="12" height="80"/></g>'
              '<path d="M-88 -118 Q-118 -100 -110 -60" fill="none" stroke="{grey}" stroke-width="6"/><ellipse cx="-10" cy="-140" rx="50" ry="14" fill="{cloth}"/>',
    "cage": '<path d="M-60 -200 Q0 -260 60 -200" fill="none" stroke="{gold}" stroke-width="8"/><rect x="-70" y="-12" width="140" height="12" fill="{woodd}"/>'
            + "".join(f'<rect x="{x - 2}" y="-200" width="4" height="190" fill="{{gold}}"/>' for x in (-60, -36, -12))
            + '<path id="{pid}-bird" d="M-6 -70 Q8 -96 26 -82 Q34 -92 44 -88 L36 -78 Q30 -56 4 -56 Z" fill="#f2c14e"/>'
              '<g id="{pid}-door">' + "".join(f'<rect x="{x - 2}" y="-200" width="4" height="190" fill="{{gold}}"/>' for x in (12, 36, 60)) + '</g>',
    "rope": '<path d="M-130 -8 C-90 -34 -50 18 -10 -8 C30 -34 70 18 110 -8 Q130 -20 140 -10" fill="none" stroke="{straw}" '
            'stroke-width="11" stroke-linecap="round"/>',
    "mirror": '<rect x="-6" y="-170" width="12" height="170" fill="{woodd}"/><path d="M-50 0 H50 L40 -12 H-40 Z" fill="{woodd}"/>'
              '<ellipse cx="0" cy="-250" rx="72" ry="96" fill="{gold}"/><ellipse id="{pid}-liq" cx="0" cy="-250" rx="60" ry="84" fill="#dfe9f2"/>',
    "ladder": '<rect x="-60" y="-520" width="12" height="520" fill="{wood}"/><rect x="48" y="-520" width="12" height="520" fill="{wood}"/>'
              + "".join(f'<rect x="-50" y="-{y}" width="100" height="10" fill="{{woodd}}"/>' for y in range(60, 520, 70)),
    "cloud": '<g fill="{white}"><circle cx="-80" cy="-40" r="50"/><circle cx="-10" cy="-70" r="70"/>'
             '<circle cx="70" cy="-45" r="55"/><rect x="-130" y="-40" width="250" height="40" rx="20"/></g>',
    "butterfly": '<g fill="#f08a2e"><path d="M0 -20 C-30 -60 -70 -50 -60 -20 C-70 6 -30 10 0 -14 Z"/>'
                 '<path d="M0 -20 C30 -60 70 -50 60 -20 C70 6 30 10 0 -14 Z"/></g><g fill="{gold}"><circle cx="-36" cy="-30" r="8"/><circle cx="36" cy="-30" r="8"/></g>'
                 '<rect x="-3" y="-40" width="6" height="34" rx="3" fill="{ink}"/>',
    "moon": '<circle cx="0" cy="-150" r="210" fill="#f6efc6" opacity="0.18"/><circle cx="0" cy="-150" r="150" fill="#f6efc6"/>'
            '<g fill="#e6dcae"><circle cx="-40" cy="-190" r="24"/><circle cx="50" cy="-120" r="16"/></g>',
    "scroll": '<rect x="-90" y="-150" width="180" height="130" fill="{cream}"/><rect x="-100" y="-160" width="14" height="150" rx="6" fill="{woodd}"/>'
              '<rect x="86" y="-160" width="14" height="150" rx="6" fill="{woodd}"/><path d="M-60 -115 H60 M-60 -85 H60 M-60 -55 H30" stroke="{ink}" stroke-width="5"/>',
    "cross": '<rect x="-14" y="-430" width="28" height="430" fill="{wood}"/><rect x="-110" y="-350" width="220" height="24" fill="{wood}"/>'
             '<path d="M-4 -420 V-20" stroke="{woodd}" stroke-width="4"/>',
    "thorns": '<path d="M-90 0 L-70 -60 L-55 -20 L-40 -90 L-20 -30 L0 -110 L20 -30 L40 -95 L55 -25 L75 -70 L90 0 Z" fill="#5a6a3a"/>',
    "bread": '<g fill="{straw}"><ellipse cx="-46" cy="-22" rx="44" ry="22"/><ellipse cx="40" cy="-22" rx="44" ry="22"/></g>'
             '<ellipse cx="-4" cy="-52" rx="44" ry="22" fill="#d9a24a"/>',
    "dove": '<path d="M-40 0 Q-10 -20 20 -6 Q40 -30 70 -40 Q52 -12 30 2 Q50 4 64 14 Q30 14 10 8 Q-20 14 -40 0 Z" fill="{white}"/>',
    "manger": '<circle cx="0" cy="-70" r="120" fill="#fff3c4" opacity="0.35"/><path d="M-90 -60 L90 -60 L60 0 L-60 0 Z" fill="{wood}"/>'
              '<path d="M-96 -60 L-70 -90 L-40 -64 L-10 -96 L20 -64 L50 -92 L96 -60 Z" fill="{straw}"/>',
    "tomb": '<path d="M-260 0 C-250 -250 250 -270 280 0 Z" fill="{stoned}"/><path d="M-70 0 V-120 A70 70 0 0 1 70 -120 V0 Z" fill="{ink}"/>'
            '<circle cx="150" cy="-80" r="80" fill="{stone}"/>',
}


def _prop(k, pid):
    if k == "pagoda":
        return _pagoda(T["cream"], T["roof"])
    return PROPS[k].replace("{pid}", pid).format(**T)


_ROBE = {"master": ("M-42 0 C-38 -50 -31 -100 -25 -128 C-22 -141 -14 -148 -6 -150 L6 -150 C14 -148 22 -141 25 -128 "
                    "C31 -100 38 -50 42 0 Q0 9 -42 0 Z", 42),
         "dancer": ("M-74 0 Q-44 -46 -22 -104 C-20 -126 -14 -146 -6 -149 L6 -149 C14 -146 20 -126 22 -104 Q44 -46 74 0 "
                    "Q0 10 -74 0 Z", 74),
         "samurai": ("M-44 0 C-38 -55 -34 -105 -33 -140 Q-30 -150 -8 -151 L8 -151 Q30 -150 33 -140 C34 -105 38 -55 44 0 "
                     "Q0 7 -44 0 Z", 44)}
_PLAIN = ("M-31 0 C-29 -45 -27 -95 -23 -126 C-21 -140 -14 -147 -6 -149 L6 -149 C14 -147 21 -140 23 -126 C27 -95 29 -45 31 0 "
          "Q0 7 -31 0 Z", 31)
_CAP = "M-14 -172 Q-14 -190 0 -190 Q14 -190 14 -172 Q8 -181 0 -181 Q-8 -181 -14 -172 Z"  # a cap of hair over the head


def person(pid, kind, cols=None):
    """A paper doll 190 units tall, never with a face: robe group -r, the whole drawing -s (breathe, waddle), arm
    groups -al / -ar pinned at the shoulder with a gold paper fastener. cols overrides (robe, sleeve) for crowds."""
    robe, sleeve, acc = (tone(c, 0.5) for c in ROBES[kind])
    if cols:
        robe, sleeve = (tone(c, 0.5) for c in cols)
    skin = tone("#c68a5a" if kind in ("jesus", "mary") else SKINS[_seed(pid) % len(SKINS)], 0.5)
    hair = tone("#3a2a22", 0.5)
    d, hw = _ROBE.get(kind, _PLAIN)
    back, top = [], []  # pieces behind the head, and on top of it
    if kind == "angel":  # wings behind everything
        back.append(f'<g fill="{tone("#ffffff", 0.5)}"><path d="M-10 -150 C-120 -230 -170 -120 -150 -40 C-110 -110 -60 -120 -10 -110 Z"/>'
                    f'<path d="M10 -150 C120 -230 170 -120 150 -40 C110 -110 60 -120 10 -110 Z"/></g>')
    if kind in ("woman", "mary", "widow", "shepherd"):  # a headscarf: behind the head, and a fold over its crown
        scarf = sleeve if kind == "widow" else acc
        back.append(f'<path d="M-18 -181 Q0 -203 18 -181 L25 -136 Q0 -128 -25 -136 Z" fill="{scarf}"/>')
        top.append(f'<path d="M-16 -176 Q0 -198 16 -176 Q0 -186 -16 -176 Z" fill="{scarf}"/>')
    if kind == "nun":
        back.append(f'<path d="M-20 -183 Q0 -207 20 -183 L33 -114 Q0 -106 -33 -114 Z" fill="{robe}"/>')
        top.append(f'<path d="M-15 -178 Q0 -196 15 -178 Q0 -186 -15 -178 Z" fill="{acc}"/>')
    if kind == "jesus":
        back.append(f'<path d="M-15 -170 Q-17 -193 0 -193 Q17 -193 15 -170 L17 -146 L-17 -146 Z" fill="{tone("#5a3a24", 0.5)}"/>')
    if kind in ("man", "seeker", "child", "dancer", "samurai"):
        top.append(f'<path d="{_CAP}" fill="{hair}"/>')
    if kind == "elder":
        top.append(f'<path d="{_CAP}" fill="{acc}"/>')
    if kind == "farmer":
        top.append(f'<path d="M-52 -176 Q0 -214 52 -176 Q0 -184 -52 -176 Z" fill="{acc}"/>')
    if kind == "nasruddin":  # turban and beard
        top.append(f'<ellipse cx="0" cy="-189" rx="23" ry="15" fill="{acc}"/><path d="M-12 -163 Q0 -132 12 -163 Z" fill="{tone("#8a8a8a", 0.5)}"/>')
    if kind == "samurai":
        top.append(f'<circle cx="0" cy="-193" r="6" fill="{hair}"/>')
    staff = (f'<path d="M38 2 L38 -205 Q38 -228 56 -222" fill="none" stroke="{tone(PAPER["wood"], 0.5)}" stroke-width="7" '
             f'stroke-linecap="round"/>' if kind in ("elder", "shepherd") else "")
    sword = f'<path d="M-36 -70 L44 -120" stroke="{acc}" stroke-width="6" stroke-linecap="round"/>' if kind == "samurai" else ""
    sash = (f'<path d="M-20 -140 L-8 -148 L26 -10 L12 -4 Z" fill="{acc}"/>' if kind in ("jesus", "master", "monk", "dancer") else
            f'<path d="M-{hw - 2} -18 L{hw - 2} -18 L{hw} 0 Q0 7 -{hw} 0 Z" fill="{sleeve}"/>')  # else a hem band
    body = (f'<g id="{pid}-r" class="robe"><path d="{d}" fill="{robe}"/>{sash}</g>{sword}'
            f'<path d="M-6 -146 L-5 -158 L5 -158 L6 -146 Z" fill="{skin}"/>')
    head = f'<ellipse cx="0" cy="-171" rx="13.5" ry="16" fill="{skin}"/>'
    arm = (f'<path d="M-7 -2 C-9 22 -12 46 -15 64 Q-1 70 13 64 C10 46 8 22 7 -2 Z" fill="{sleeve}"/>'
           f'<ellipse cx="-1" cy="72" rx="5.5" ry="7" fill="{skin}"/><circle cx="0" cy="2" r="3.2" fill="{tone(PAPER["gold"], 0.5)}"/>')
    arms = (f'<g id="{pid}-al" class="arm-l" transform="translate(-15,-144)">{arm}</g>'
            f'<g id="{pid}-ar" class="arm-r" transform="translate(15,-144)">{arm}</g>')
    return f'<g id="{pid}-s">{"".join(back)}{staff}{body}{head}{"".join(top)}{arms}</g>'


def _aureole(pid, k):
    """The paper sunburst behind a holy figure: a solid pale disc and a ring of gold paper rays, just wider than
    the shoulders (paper.js breathes it by scale and turns its rays slowly; paper never fades)."""
    r = 72 if k != "angel" else 60
    rays = "".join(f'<path d="M{r * math.cos(a - 0.12):.0f} {-128 + r * math.sin(a - 0.12):.0f} L{r * 1.55 * math.cos(a):.0f} '
                   f'{-128 + r * 1.55 * math.sin(a):.0f} L{r * math.cos(a + 0.12):.0f} {-128 + r * math.sin(a + 0.12):.0f} Z"/>'
                   for a in (i * math.pi / 8 for i in range(16)))
    return (f'<g id="{pid}-glow"><g class="rays" fill="{tone("#ffc93a", 0.5)}">{rays}</g>'
            f'<circle cx="0" cy="-128" r="{r + 4}" fill="{tone("#fff1b8", 0.5)}"/>'
            f'<circle cx="0" cy="-128" r="{r * 0.7:.0f}" fill="{tone("#fff8dc", 0.5)}"/></g>')


def place(pid, k, x, y, s, flip, inner):
    """Outer group moves (walk, climb); inner -b bends about the feet (sit, bow, lie, rock, grow)."""
    if k in PEOPLE:
        body = person(pid, k)
        s *= SIZES.get(k, 1.0)
    elif k in PROPS:
        body = _prop(k, pid)
    else:
        raise ValueError(f"unknown cast kind {k!r}")
    glow = _aureole(pid, k) if k in GLOW else ""  # outside the body group, so sit/bow/lie pivot at the feet
    return (f'<g id="{pid}" transform="translate({x},{y}) scale({-s if flip else s},{s})">{glow}'
            f'<g id="{pid}-b" class="body">{inner}{body}</g></g>')


def crowd(pid, x, y, s, n, seed=9):
    """A row of small paper figures in many colours; deterministic spacing, height and colours."""
    r = rng(seed)
    figs = []
    for i in range(n):
        fx_ = x + (i - (n - 1) / 2) * 62 * s + (r() - 0.5) * 20
        fs = s * (0.85 + r() * 0.25)
        kind = "woman" if r() < 0.35 else ("child" if r() < 0.15 else "man")
        cols = CROWD[int(r() * len(CROWD))]
        figs.append(f'<g transform="translate({fx_:.0f},{y + r() * 14:.0f}) scale({fs * (0.62 if kind == "child" else 1):.2f})">'
                    f'{person(f"{pid}-{i}", kind, cols)}</g>')
    return f'<g id="{pid}"><g id="{pid}-b" class="body">{"".join(figs)}</g></g>'


def fx(p, name):
    """Full-frame effects, all of paper: strips of rain, a cut-out bolt, paper rays and petals. (markup, anims)"""
    if name == "rain":
        r = rng(13)
        drops = "".join(f'<path d="M{x:.0f} {y:.0f} l-12 40"/>' for x, y in ((r() * (W + 200), r() * 2 * H) for _ in range(W * H // 12000)))
        return (f'<g id="{p}-rain" stroke="#d6e8f8" stroke-width="5" stroke-opacity="0.75" stroke-linecap="round">{drops}</g>',
                [{"t": f"#{p}-rain", "do": "rain"}])
    if name == "lightning":
        x = W * 0.6
        return (f'<path id="{p}-bolt" d="M{x:.0f} 0 L{x - 80:.0f} {H * 0.19:.0f} L{x:.0f} {H * 0.19:.0f} L{x - 120:.0f} {H * 0.4:.0f} '
                f'L{x + 60:.0f} {H * 0.16:.0f} L{x - 25:.0f} {H * 0.16:.0f} L{x + 60:.0f} 0 Z" fill="#ffe14d" filter="url(#{p}-sh)" opacity="0"/>'
                f'<rect id="{p}-flash" x="-200" y="-200" width="{W + 400}" height="{H + 400}" fill="#fffbe8" opacity="0"/>',
                [{"t": f"#{p}-flash", "do": "flash", "bolt": f"#{p}-bolt"}])
    if name == "rays":
        cx = W / 2
        rays = "".join(f'<path d="M{cx:.0f} -60 L{cx + H * 0.6 * math.sin(a):.0f} {H * 0.68 * math.cos(a):.0f} '
                       f'L{cx + H * 0.6 * math.sin(a + 0.08):.0f} {H * 0.68 * math.cos(a + 0.08):.0f} Z"/>'
                       for a in [i * 0.2 - 0.9 for i in range(10)])
        return f'<g id="{p}-rays" fill="#fff4c2" opacity="0">{rays}</g>', [{"t": f"#{p}-rays", "do": "rays"}]
    if name == "sparkle":
        r = rng(17)
        sp = "".join(_star(W * 0.13 + r() * W * 0.74, HZ * 0.5 + r() * HZ * 0.48, 12 + r() * 8) for _ in range(26))
        return f'<g id="{p}-sparkle" fill="#ffe066" opacity="0">{sp}</g>', [{"t": f"#{p}-sparkle", "do": "sparkle"}]
    if name == "petals":  # paper blossom drifting down; placed above the frame too, so the whole beat has petals
        r = rng(31)
        ps = "".join(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="12" ry="6" transform="rotate({r() * 180:.0f} {x:.0f} {y:.0f})" '
                     f'fill="{"#f8b4c8" if r() < 0.6 else "#fde0ea"}"/>' for x, y in ((r() * W, -H * 0.4 + r() * H * 1.3) for _ in range(46)))
        return f'<g id="{p}-petals">{ps}</g>', [{"t": f"#{p}-petals", "do": "petals", "by": round(H * 0.36)}]
    if name == "mist":  # two scalloped strips of pale paper sliding slowly in opposite directions
        def strip(y, h):
            return f'M-320 {y:.0f} ' + " ".join("q40 -26 80 0" for _ in range((W + 640) // 80)) + f' L{W + 320} {y + h:.0f} L-320 {y + h:.0f} Z'
        return (f'<g id="{p}-mist" fill="#f4f1f8"><path id="{p}-mist-a" d="{strip(HZ - 170, 70)}" opacity="0.7"/>'
                f'<path id="{p}-mist-c" d="{strip(HZ + 30, 80)}" opacity="0.6"/></g>', [{"t": f"#{p}-mist", "do": "mist"}])
    if name == "ripples":  # paper rings spreading on still water
        rings = "".join(f'<ellipse cx="{W / 2:.0f}" cy="{GF + (H - GF) * 0.4:.0f}" rx="{W * 0.12:.0f}" ry="{W * 0.03:.0f}"/>' for _ in range(3))
        return f'<g id="{p}-ripples" fill="none" stroke="#e8f6fc" stroke-width="5">{rings}</g>', [{"t": f"#{p}-ripples", "do": "ripples"}]
    if name == "fireflies":
        r = rng(37)
        dots = "".join(f'<circle cx="{r() * W:.0f}" cy="{HZ * 0.7 + r() * (H - HZ * 0.7) * 0.8:.0f}" r="{4 + r() * 3:.1f}"/>' for _ in range(40))
        return f'<g id="{p}-fireflies" fill="#fff27a">{dots}</g>', [{"t": f"#{p}-fireflies", "do": "fireflies"}]
    if name == "dove":  # a white paper bird coming down out of an opened sky
        return (f'<g id="{p}-dove" transform="translate({W / 2:.0f},40) scale(1.2)" opacity="0" filter="url(#{p}-sh)">{_prop("dove", p)}</g>',
                [{"t": f"#{p}-dove", "do": "descend", "by": round(H * 0.35)}])
    raise ValueError(f"unknown fx {name!r}")


FX = {"rain", "lightning", "rays", "sparkle", "petals", "mist", "ripples", "fireflies", "dove"}


def foreground(p, ground_name, sky_name):
    """A leafy branch (or a pine bough) hanging down the side nearest the camera, away from the sun; seeded by the
    setting, so beats in one setting keep the same branch. None in the desert or the village. (markup, anims)"""
    kind = {"hills": "leaf", "field": "leaf", "garden": "leaf", "forest": "leaf", "mountain": "pine", "zen": "pine",
            "river": "leaf", "sea": "leaf"}.get(ground_name)
    r = rng(_seed(ground_name + sky_name))
    if not kind or r() > 0.75:
        return "", []
    orb = SKIES[sky_name]["orb"]
    left = orb[1] > 0.5 if orb else r() < 0.5
    limb = f'<path d="M-60 170 C40 250 125 390 205 610 L193 616 C105 400 25 275 -60 232 Z" fill="{tone("#6e4a2a")}"/>'
    pts = [(min(235, -30 + 240 * t + (r() - 0.5) * 70), 210 + 390 * t + (r() - 0.5) * 50) for t in [r() for _ in range(34)]]
    greens = [tone("#4caf50"), tone("#2e7d32"), tone("#8bc34a")]
    if kind == "leaf":
        tips = "".join(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{15 + r() * 9:.0f}" ry="{7 + r() * 3:.0f}" fill="{greens[k % 3]}" '
                       f'transform="rotate({r() * 180:.0f} {x:.0f} {y:.0f})"/>' for k, (x, y) in enumerate(pts))
    else:  # pine: fans of paper needles
        tips = "".join(f'<path d="{" ".join(f"M{x:.0f} {y:.0f} l{26 * math.cos(a):.0f} {26 * math.sin(a):.0f}" for a in [math.pi * (0.95 + 0.11 * j) for j in range(10)])}" '
                       f'stroke="{greens[k % 2]}" stroke-width="5" stroke-linecap="round"/>' for k, (x, y) in enumerate(pts[:16]))
    s = 1.0 if H > W else 0.62  # the long frame is short: a smaller branch
    flip = f' transform="scale({s})"' if left else f' transform="translate({W},0) scale({-s},{s})"'
    return f'<g{flip}>' + piece(p, f'<g id="{p}-fg">{limb}{tips}</g>', "top") + '</g>', [{"t": f"#{p}-fg", "do": "sway"}]


def placement(c):
    """A cast entry without its actions: two beats with the same placement show the same figure in the same spot."""
    return json.dumps({k: v for k, v in c.items() if k != "acts"}, sort_keys=True)


def depth_order(cast):
    """Indices of the top-level cast, back to front: whatever stands farther up the ground is drawn first, so a nearer
    figure is never covered by a farther one (ties keep the script's order)."""
    top = [j for j, c in enumerate(cast) if "in" not in c]
    return sorted(top, key=lambda j: cast[j].get("y", GF + FR["cy"] if cast[j]["k"] == "crowd" else GF))


def focus(beat):
    """Where the beat's main figure stands, as a fraction of the width (a person first, else the first prop; the
    middle of a walk), for medium shots; None when there is no one to frame."""
    cs = [c for c in beat.get("cast", []) if "in" not in c and c["k"] != "crowd"]
    c = next((c for c in cs if c["k"] in PEOPLE), cs[0] if cs else None)
    if c is None:
        return None
    to = next((a["to"] for a in c.get("acts", []) if a["do"] in ("walk", "run", "roll") and "to" in a), None)
    x = c.get("x", W / 2) if to is None else (c.get("x", W / 2) + to) / 2
    return round(x / W, 3)


def scene(i, beat, sky, ground, start, dur, kept=(), branch=True):
    """One beat's page: an SVG of four multiplane layers (L0 the sky page, L1 the land, L2 cast and effects, L3 the
    branch nearest the camera) and its absolute-timed anims. kept: placements already standing from the previous
    beat in the same setting; every other cast piece is class `new` and pops up when the beat begins."""
    use(sky)
    p = f"b{i}"
    cast = beat.get("cast", [])
    back, anims = backdrop(p, sky, not any(c["k"] == "moon" for c in cast))
    ground_m, a = land(p, ground); anims += a
    near, a = foreground(p, ground, sky) if branch else ("", []); anims += a
    r = rng(i * 101 + 7)
    inner = {j: [] for j in range(len(cast))}
    drawn = {}
    for j, c in enumerate(cast):
        pid = f"{p}-c{j}"
        drawn[j] = (crowd(pid, c.get("x", W / 2), c.get("y", GF + FR["cy"]), c.get("s", FR["cs"]), c.get("n", 12))
                    if c["k"] == "crowd" else None)
        for act in c.get("acts", []):
            anims.append(dict(act, t=f"#{pid}", x0=c.get("x", W / 2), y0=c.get("y", GF)))
        if c["k"] in GLOW:
            anims.append({"t": f"#{pid}-glow", "do": "glow"})
        if c["k"] in PEOPLE:  # a paper figure on its tab is never quite still
            anims.append({"t": f"#{pid}", "do": "idle", "period": round(3.6 + r() * 1.4, 2), "phase": round(r() * 1.5, 2)})
    for j in reversed(range(len(cast))):  # children drawn inside their parent so they move with it (people in a boat)
        c = cast[j]
        if drawn[j] is None:
            drawn[j] = place(f"{p}-c{j}", c["k"], c.get("x", W / 2), c.get("y", GF), c.get("s", FR["s"]),
                             c.get("flip", False), "".join(inner[j]))
        if "in" in c:
            inner[c["in"]].insert(0, drawn[j])
    figures = "".join(piece(p, drawn[j], "" if placement(cast[j]) in kept else "new") for j in depth_order(cast))
    effects = ""
    for name in beat.get("fx", []):
        m, a = fx(p, name); effects += m; anims += a
    for x in anims:  # beat-relative times -> absolute timeline times
        x["s"] = round(start + x.pop("at", 0), 3)
        x["d"] = round(x.pop("dur", start + dur - x["s"] - 0.05), 3)
        x["b0"] = start
    layers = [back, ground_m, figures + effects, near]
    return (f'<svg id="{p}-svg" class="stage" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">'
            + "".join(f'<g id="{p}-L{k}">{m}</g>' for k, m in enumerate(layers)) + '</svg>'), anims


def section(i, start, clip, svg):
    """A beat's clip: the page (turned over by paper.js when a new setting begins) holding the camera's scene."""
    return (f'<section id="beat-{i}" class="clip" data-start="{start}" data-duration="{clip}" data-track-index="{1 if i % 2 == 0 else 4}">'
            f'<div class="page" id="beat-{i}-pg"><div class="scene" id="beat-{i}-in">{svg}</div></div></section>')


TURN = 0.6  # seconds for a page to turn over at a new setting; the outgoing page stays under it that long

# Camera framings per frame [scale, x, medium]: wide holds, pans and medium shots on the beat's main figure. |x| stays
# inside the zoom's overflow. Origin y (percent) for wide and medium shots. Depth: how far each layer lags (-) or
# leads (+) the camera, so a move has the depth of a diorama.
CAMERA = {"short": dict(cam=[[1.24, 0, 0], [1.46, 0, 1], [1.26, -40, 0], [1.3, 0, 0], [1.46, 0, 1], [1.26, 40, 0]], oy=[72, 72]),
          "long": dict(cam=[[1.05, 0, 0], [1.0, 0, 0], [1.03, -24, 0], [1.2, 0, 1], [1.03, 24, 0], [1.18, 0, 1]], oy=[62, 76])}


def cfg(name):
    """What paper.js needs to know about the frame."""
    return dict(W=FRAMES[name]["W"], H=FRAMES[name]["H"], turn=TURN, depth=[["-L0", -0.6], ["-L1", -0.3], ["-L3", 0.6]],
                **CAMERA[name])


def clips(slots, cont, total, xf):
    """Each beat's clip length: its own time, plus the dissolve (xf, same setting) or the page turn (a new setting)
    under the next beat; the last scene holds under the closing card."""
    return [round(total - s if i + 1 == len(slots) else d + (xf if cont[i + 1] else TURN), 3) for i, (s, d) in enumerate(slots)]


def plan_beats(beats, slots, cont):
    """PLAN entries for paper.js: x = continues the setting (dissolve), o = the next beat is a new setting (fold flat)."""
    return [{"id": f"beat-{i}", "p": f"b{i}", "s": s, "d": d, "x": cont[i], "o": i + 1 < len(beats) and not cont[i + 1],
             "f": focus(b)} for i, (b, (s, d)) in enumerate(zip(beats, slots))]


# Shared page CSS: the page and its turn, and the paper's tooth over everything (under the captions).
CSS = """
  .page { position: absolute; inset: 0; box-shadow: 0 0 70px rgba(30, 15, 0, 0.55); }
  #grain { position: absolute; inset: 0; z-index: 4; pointer-events: none; opacity: 0.32; mix-blend-mode: soft-light;
           background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Cfilter id='g'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.55' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23g)'/%3E%3C/svg%3E"); }
  #vignette { position: absolute; inset: 0; z-index: 3; pointer-events: none;
              background: radial-gradient(ellipse at 50% 45%, rgba(40,20,0,0) 60%, rgba(40,20,0,0.35) 100%); }
"""
