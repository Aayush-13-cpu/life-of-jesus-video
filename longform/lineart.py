"""Divine glowing line art for the long-form videos (1920x1080): every sky, land, figure and prop is a thin line of
light that traces itself in when its beat begins, inside a soft glow.

Markup is plain SVG; motion is described as dicts that the page's GSAP interpreter turns into tweens, so every frame
is deterministic. Coordinates are the frame's own: x across 0-1920, y down 0-1080, horizon at HZ, and every figure or
prop is placed by the point where it touches the ground (GF for the near ground).
"""
import math

W, H, HZ, GF = 1920, 1080, 760, 850
D = 'class="d" pathLength="1"'      # traced in when the beat begins, with a faint fill
N = 'class="d n" pathLength="1"'    # traced in, never filled (open lines)
F = 'class="d f" pathLength="1"'    # traced in, then glowing solid (flames, the star)

# One template per video: its palette, its glow, and the moving light behind every scene.
TEMPLATES = {
    "sanctuary": dict(line="#f0d79c", glow="#e8bd6a", dot="#fff3d6", motif="sunburst",
                      skies={"night": ("#03050d", "#121a38"), "dawn": ("#0a0c22", "#4a3226"), "dusk": ("#0c0818", "#46222e"),
                             "day": ("#0d1836", "#34416c"), "storm": ("#040509", "#1c2029")}),
    "dawnlight": dict(line="#f8cdb6", glow="#ff9f7f", dot="#ffe8de", motif="motes",
                      skies={"night": ("#0b0416", "#2a1236"), "dawn": ("#170a24", "#6a3242"), "dusk": ("#14061c", "#56203a"),
                             "day": ("#1e0f30", "#56305e"), "storm": ("#09050d", "#261c2a")}),
}


def _mix(a, b, t):
    """Blend two #rrggbb colours: t=0 gives a, t=1 gives b."""
    x, y = (tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in (a, b))
    return "#" + "".join(f"{round(u + (v - u) * t):02x}" for u, v in zip(x, y))


def _template(line, glow, deep, horizon, motif):
    """A template from four colours: the five skies are the night sky warmed, cooled or darkened."""
    return dict(line=line, glow=glow, dot=_mix(line, "#ffffff", 0.6), motif=motif, skies={
        "night": (deep, horizon), "dawn": (deep, _mix(horizon, "#6a4a2a", 0.5)), "dusk": (deep, _mix(horizon, "#5a2030", 0.5)),
        "day": (_mix(deep, horizon, 0.6), _mix(horizon, "#5a6a9a", 0.35)), "storm": (_mix(deep, "#000000", 0.3), _mix(horizon, "#202428", 0.6))})


TEMPLATES.update({  # name: line, glow, deep sky, horizon, motif
    "olivet": _template("#dfeab4", "#b8d47a", "#050a06", "#1c2a18", "constellation"),
    "galilee": _template("#bfe6ff", "#6fc3ff", "#020814", "#0d2a44", "halo"),
    "bethany": _template("#ffd9a8", "#ffb35c", "#0d0603", "#3a1e0e", "sunburst"),
    "jordan": _template("#a8f0e6", "#4fd8c4", "#021010", "#0b3534", "motes"),
    "zion": _template("#f4f1ff", "#b9a8ff", "#07051a", "#241c4e", "constellation"),
    "emmaus": _template("#f6d2a0", "#ff8a5c", "#120806", "#4a2016", "halo"),
    "nazareth": _template("#e8d6b8", "#c9a26a", "#0a0806", "#2c241a", "motes"),
    "capernaum": _template("#c8f0ff", "#8ad8ff", "#040b12", "#16323f", "sunburst"),
    "gethsemane": _template("#d8c8ff", "#9a7bff", "#06030f", "#1f1238", "constellation"),
    "golgotha": _template("#ffc4b0", "#ff6a4a", "#0b0304", "#34100e", "halo"),
    "magdala": _template("#ffd0e4", "#ff7fb5", "#10040b", "#3e1028", "motes"),
    "tabor": _template("#fff4c2", "#ffe066", "#0a0a04", "#34300c", "sunburst"),
    "kidron": _template("#b8d0ff", "#7a9cff", "#03050f", "#121c3e", "motes"),
    "siloam": _template("#b0fff0", "#3fe0c0", "#020c0a", "#0a302a", "halo"),
    "hermon": _template("#e6f4ff", "#a8d0ff", "#04070c", "#1a2638", "constellation"),
    "cana": _template("#ffc8d0", "#e05a7a", "#0e0306", "#3a0e1c", "sunburst"),
    "bethlehem": _template("#fff0c8", "#ffd27a", "#050611", "#1a1c40", "halo"),
    "pentecost": _template("#ffd8b0", "#ff8c3a", "#0c0502", "#3c180a", "constellation"),
})
SKIES = ("night", "dawn", "dusk", "day", "storm")
LANDS = ("hills", "field", "desert", "city", "sea", "garden", "mountain", "river")
T = TEMPLATES["sanctuary"]


def use(name):
    """Switch every drawing function to a template (module-level: one chapter is built per process)."""
    global T
    T = TEMPLATES[name]


def rng(seed):
    """Seeded pseudo-random numbers, so 'random' stars and motes are identical on every render."""
    s = seed & 0x7FFFFFFF

    def r():
        nonlocal s
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        return s / 0x7FFFFFFF
    return r


def ridge(base, amp, waves, phase, op=1.0):
    pts = " L".join(f"{x} {base + amp * math.sin(x / W * waves * math.pi + phase):.0f}" for x in range(-40, W + 81, 60))
    return f'<path {N} d="M{pts}" opacity="{op}"/>'


def background(p, sky):
    """Sky gradient, the divine halo, the template's moving light, stars and the sun or moon."""
    top, low = T["skies"][sky]
    out = [f'<defs><linearGradient id="{p}-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/>'
           f'<stop offset="1" stop-color="{low}"/></linearGradient>'
           f'<radialGradient id="{p}-halo"><stop offset="0" stop-color="{T["glow"]}" stop-opacity="0.75"/>'
           f'<stop offset="1" stop-color="{T["glow"]}" stop-opacity="0"/></radialGradient>'
           f'<filter id="{p}-glow" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="5" result="b"/>'
           f'<feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>',
           f'<rect width="{W}" height="{H}" fill="url(#{p}-sky)"/>',
           f'<circle cx="{W // 2}" cy="{HZ - 220}" r="720" fill="url(#{p}-halo)" opacity="{0.22 if sky == "storm" else 0.4}"/>']
    anims = []
    c = T["line"]
    if T["motif"] == "sunburst":  # slow-turning rays of light around the centre of the frame
        r = rng(21)
        rays = "".join(f'<path d="M{W / 2 + 380 * math.cos(a):.0f} {HZ - 220 + 380 * math.sin(a):.0f} '
                       f'L{W / 2 + 1300 * math.cos(a):.0f} {HZ - 220 + 1300 * math.sin(a):.0f}" opacity="{0.05 + r() * 0.1:.2f}"/>'
                       for a in (i * math.pi / 24 for i in range(48)))
        out.append(f'<g id="{p}-burst" stroke="{c}" stroke-width="2" fill="none">{rays}</g>'
                   f'<circle {N} cx="{W // 2}" cy="{HZ - 220}" r="330" opacity="0.18"/>'
                   f'<circle {N} cx="{W // 2}" cy="{HZ - 220}" r="450" opacity="0.1"/>')
        anims.append({"t": f"#{p}-burst", "do": "spin", "deg": 6, "ox": W // 2, "oy": HZ - 220})
    elif T["motif"] == "constellation":  # bright stars joined by lines of light, traced in like the scene
        r = rng(29)
        pts = [(160 + r() * 1600, 70 + r() * 420) for _ in range(14)]
        links = "".join(f'<path {N} d="M{a[0]:.0f} {a[1]:.0f} L{b[0]:.0f} {b[1]:.0f}" opacity="0.22"/>'
                        for a, b in zip(pts, pts[1:]) if abs(a[0] - b[0]) < 520)
        out.append(f'<g id="{p}-const" fill="{T["dot"]}">' + "".join(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{2.5 + r() * 2.5:.1f}"/>' for x, y in pts) + f'</g>{links}')
        anims.append({"t": f"#{p}-const", "do": "twinkle"})
    elif T["motif"] == "halo":  # rings of light around the centre, breathing slowly
        rings = "".join(f'<circle cx="{W // 2}" cy="{HZ - 220}" r="{rr}" opacity="{0.3 - k * 0.04:.2f}"/>'
                        for k, rr in enumerate(range(220, 900, 110)))
        out.append(f'<g id="{p}-rings" fill="none" stroke="{c}" stroke-width="2">{rings}</g>')
        anims.append({"t": f"#{p}-rings", "do": "pulse", "ox": W // 2, "oy": HZ - 220})
    else:  # "motes": embers of light rising through the frame, and rings of sunrise on the horizon
        r = rng(23)
        motes = "".join(f'<circle cx="{r() * W:.0f}" cy="{r() * (H + 200):.0f}" r="{1.5 + r() * 3:.1f}" opacity="{0.15 + r() * 0.5:.2f}"/>'
                        for _ in range(80))
        out.append(f'<g id="{p}-motes" fill="{T["dot"]}">{motes}</g>'
                   + "".join(f'<path {N} d="M{W // 2 - rr} {HZ} A{rr} {rr} 0 0 1 {W // 2 + rr} {HZ}" opacity="{0.28 - k * 0.05:.2f}"/>'
                             for k, rr in enumerate((260, 380, 500, 620))))
        anims.append({"t": f"#{p}-motes", "do": "rise", "by": 160})
    if sky in ("night", "dusk"):
        r = rng(7)
        stars = "".join(f'<circle cx="{r() * W:.0f}" cy="{r() * (HZ - 120):.0f}" r="{0.8 + r() * 1.8:.1f}" opacity="{0.3 + r() * 0.7:.2f}"/>'
                        for _ in range(170 if sky == "night" else 60))
        out.append(f'<g id="{p}-stars" fill="{T["dot"]}">{stars}</g>')
        anims.append({"t": f"#{p}-stars", "do": "twinkle"})
    if sky in ("night", "dusk"):
        out.append(f'<path {D} d="M1500 120 A64 64 0 1 0 1500 248 A48 64 0 1 1 1500 120 Z" opacity="0.9"/>')  # crescent moon
    elif sky in ("day", "dawn"):
        x, y, rad = (1460, 230, 54) if sky == "day" else (1300, HZ - 40, 80)
        rays = "".join(f'<path d="M{x + (rad + 14) * math.cos(a):.0f} {y + (rad + 14) * math.sin(a):.0f} '
                       f'L{x + (rad + 40) * math.cos(a):.0f} {y + (rad + 40) * math.sin(a):.0f}"/>' for a in (i * math.pi / 6 for i in range(12)))
        out.append(f'<circle {D} cx="{x}" cy="{y}" r="{rad}"/><g stroke="{c}" stroke-width="3" opacity="0.7">{rays}</g>')
    return "".join(out), anims


def land(p, name):
    """The ground, drawn as lines of light; returns (markup, anims)."""
    anims = []
    if name == "hills":
        g = ridge(HZ - 70, 55, 3, 0.5, 0.35) + ridge(HZ - 10, 40, 2.2, 2.0, 0.6) + ridge(GF - 20, 22, 1.6, 4.0)
    elif name == "field":
        r = rng(5)
        tufts = "".join(f'<path {N} d="M{x:.0f} {GF + 30 + r() * 120:.0f} l-6 -{18 + r() * 14:.0f} m6 18 l8 -{14 + r() * 12:.0f}" opacity="0.6"/>'
                        for x in [r() * W for _ in range(60)])
        g = ridge(HZ - 50, 35, 2.5, 1.2, 0.35) + ridge(GF - 10, 14, 1.4, 0.3) + tufts
    elif name == "desert":
        g = ridge(HZ - 30, 26, 2, 1.0, 0.3) + ridge(HZ + 20, 30, 1.3, 2.6, 0.55) + ridge(GF, 12, 1.0, 3.3)
    elif name == "city":
        blocks = [(80, 120, 150), (230, 160, 90), (420, 80, 220), (530, 240, 120), (820, 110, 170), (960, 190, 100),
                  (1180, 90, 200), (1300, 150, 130), (1480, 120, 160), (1640, 200, 110)]
        towers = "".join(f'<path {N} d="M{x} {HZ + 40} V{HZ - h} H{x + w} V{HZ + 40}"/>' for x, w, h in blocks)
        domes = "".join(f'<path {N} d="M{x - r} {HZ - h} A{r} {r} 0 0 1 {x + r} {HZ - h}"/>' for x, h, r in
                        [(650, 120, 70), (460, 220, 34), (875, 170, 45), (1225, 200, 38), (1540, 160, 50)])
        g = f'<g opacity="0.5">{towers}{domes}</g>' + ridge(GF - 10, 10, 1.2, 0.8)
    elif name in ("sea", "river"):
        r = rng(3)
        rows = range(HZ + 30, H, 55) if name == "sea" else range(GF - 40, GF + 140, 45)
        waves = "".join(f'<path {N} d="M-120 {y} q30 -12 60 0 {"t60 0 " * ((W + 200) // 60)}" opacity="{0.25 + r() * 0.35:.2f}"/>' for y in rows)
        g = (ridge(HZ - 25, 18, 2, 1.5, 0.4) if name == "sea" else ridge(HZ - 60, 40, 2.4, 0.6, 0.35) + ridge(GF - 60, 14, 1.4, 2.2, 0.7))
        g += f'<g id="{p}-waves">{waves}</g>'
        anims.append({"t": f"#{p}-waves", "do": "drift", "amp": 40, "period": 3.4})
    elif name == "garden":  # an olive grove on the slope
        trees = "".join(f'<g transform="translate({x},{HZ + 10}) scale({s})" opacity="0.45">{PROPS["tree"]}</g>'
                        for x, s in [(180, 0.55), (420, 0.45), (1500, 0.5), (1760, 0.6)])
        g = ridge(HZ - 60, 40, 2.5, 0.2, 0.35) + trees + ridge(GF - 10, 14, 1.5, 1.0)
    elif name == "mountain":
        g = (f'<path {N} d="M-40 {HZ + 20} L380 {HZ - 260} L560 {HZ - 120} L860 {HZ - 420} L1180 {HZ - 140} L1420 {HZ - 300} '
             f'L1960 {HZ + 10}" opacity="0.55"/>' + ridge(GF - 20, 24, 1.6, 4.0))
    else:
        raise ValueError(f"unknown land {name!r}")
    return g, anims


# Props: (0,0) is the point that touches the ground. Ids with {pid} let actions find a part (flames).
PROPS = {
    "cross": f'<path {N} d="M0 0 V-430 M-110 -338 H110"/>',
    "boat": f'<path {D} d="M-210 -40 L210 -40 L160 40 L-160 40 Z"/><path {N} d="M0 -40 V-330"/><path {D} d="M8 -320 L8 -70 L170 -70 Z"/>',
    "lamp": f'<path {D} d="M-40 -10 Q0 10 40 -10 L30 -30 L-30 -30 Z"/><path {N} d="M40 -22 L70 -34 L60 -18"/>'
            f'<path id="{{pid}}-flame" {F} d="M66 -36 C60 -60 72 -66 74 -84 C80 -66 88 -60 80 -36 Z"/>',
    "tree": f'<path {N} d="M-14 0 C-8 -90 -12 -170 0 -240 C10 -170 8 -90 14 0"/>'
            f'<circle {D} cx="-70" cy="-280" r="85"/><circle {D} cx="60" cy="-300" r="95"/><circle {D} cx="0" cy="-380" r="100"/>',
    "stone": f'<circle {D} cx="0" cy="-95" r="95"/><circle {N} cx="0" cy="-95" r="60"/>',
    "tomb": f'<path {N} d="M-260 0 C-250 -250 250 -270 280 0"/><path {D} d="M-70 0 V-120 A70 70 0 0 1 70 -120 V0"/>',
    "star": f'<path {F} d="M0 -70 L14 -14 L70 0 L14 14 L0 70 L-14 14 L-70 0 L-14 -14 Z"/><path {N} d="M0 -170 V170 M-170 0 H170" opacity="0.5"/>',
    "dove": f'<path {D} d="M-40 0 Q-10 -20 20 -6 Q40 -30 70 -40 Q52 -12 30 2 Q50 4 64 14 Q30 14 10 8 Q-20 14 -40 0 Z"/>',
    "bread": f'<ellipse {D} cx="-46" cy="-22" rx="44" ry="22"/><ellipse {D} cx="40" cy="-22" rx="44" ry="22"/><ellipse {D} cx="-4" cy="-52" rx="44" ry="22"/>',
    "fish": f'<path {D} d="M-30 -20 Q0 -44 30 -20 Q0 4 -30 -20 Z M30 -20 L48 -34 L48 -6 Z"/>',
    "cup": f'<path {D} d="M-30 -110 H30 C30 -60 18 -46 0 -46 C-18 -46 -30 -60 -30 -110 Z"/><path {N} d="M0 -46 V-8 M-26 0 H26"/>',
    "scroll": f'<path {D} d="M-90 -150 H90 V-20 H-90 Z"/><path {N} d="M-100 -160 V-10 M100 -160 V-10 M-60 -115 H60 M-60 -85 H60 M-60 -55 H30"/>',
    "sheep": f'<circle {D} cx="-30" cy="-60" r="30"/><circle {D} cx="5" cy="-70" r="34"/><circle {D} cx="35" cy="-58" r="28"/>'
             f'<ellipse {D} cx="68" cy="-72" rx="18" ry="14"/><path {N} d="M-26 -32 V0 M28 -32 V0"/>',
    "well": f'<path {D} d="M-110 0 V-120 H110 V0 Z"/><path {N} d="M-125 -124 H125 M-90 -124 V-300 M90 -124 V-300 M-110 -300 H110"/>',
    "house": f'<path {N} d="M-150 0 V-210 H150 V0 M-170 -216 H170"/><path {D} d="M-40 0 V-120 H20 V0"/><path {D} d="M70 -170 H110 V-130 H70 Z"/>',
    "manger": f'<circle cx="0" cy="-70" r="120" fill="url(#{{p}}-halo)"/><path {D} d="M-90 -60 L90 -60 L60 0 L-60 0 Z"/>'
              f'<path {N} d="M-80 -60 L-100 0 M80 -60 L100 0"/><ellipse {D} cx="0" cy="-70" rx="40" ry="14"/>',
    "table": f'<path {N} d="M-200 -90 H200 M-180 -90 V0 M180 -90 V0"/><ellipse {D} cx="-60" cy="-104" rx="44" ry="14"/>'
             f'<path {D} d="M40 -150 H80 C80 -120 72 -112 60 -112 C48 -112 40 -120 40 -150 Z"/><path {N} d="M60 -112 V-92"/>',
    "net": f'<path {N} d="M-160 0 Q0 -60 160 0 M-160 0 L-120 -80 M-80 -30 L-60 -100 M0 -40 L0 -110 M80 -30 L60 -100 M160 0 L120 -80 '
           f'M-130 -50 Q0 -100 130 -50 M-110 -85 Q0 -125 110 -85"/>',
    "thorns": f'<path {N} d="M-80 -40 Q0 -90 80 -40 Q0 10 -80 -40 M-70 -60 L-84 -78 M-30 -74 L-30 -96 M10 -76 L18 -98 M50 -66 L68 -84 M74 -40 L96 -46"/>',
    "basket": f'<path {D} d="M-70 -50 L70 -50 L55 0 L-55 0 Z"/><path {N} d="M-60 -50 Q0 -120 60 -50"/>',
    "fire": f'<path {N} d="M-60 0 L60 -14 M-60 -14 L60 0"/><path id="{{pid}}-flame" {F} d="M-28 -14 C-34 -60 -6 -70 0 -110 C10 -70 36 -60 28 -14 Z"/>',
    "stones": f'<ellipse {D} cx="-40" cy="-14" rx="26" ry="16"/><ellipse {D} cx="10" cy="-12" rx="20" ry="13"/><ellipse {D} cx="50" cy="-16" rx="28" ry="17"/>',
    "mat": f'<path {D} d="M-110 0 V-14 H110 V0 Z"/>',
    "birds": f'<path {N} d="M0 0 q14 -12 28 0 q14 -12 28 0 M70 -40 q10 -9 20 0 q10 -9 20 0 M-60 -30 q11 -10 22 0 q11 -10 22 0"/>',
}
PEOPLE = {"jesus", "man", "woman", "child", "elder", "shepherd", "angel", "mary"}
SIZES = {"child": 0.62, "jesus": 1.06}


def person(pid, kind):
    """A robed figure 190 units tall, in lines. Arms are groups -al / -ar that rotate at the shoulder."""
    parts = []
    if kind == "angel":
        parts.append(f'<path {N} d="M-10 -150 C-120 -230 -170 -120 -150 -40 C-110 -110 -60 -120 -10 -110"/>'
                     f'<path {N} d="M10 -150 C120 -230 170 -120 150 -40 C110 -110 60 -120 10 -110"/>')
    parts.append(f'<path {D} d="M-30 0 C-28 -60 -24 -118 -17 -150 Q0 -160 17 -150 C24 -118 28 -60 30 0 Z"/>'
                 f'<circle {D} cx="0" cy="-172" r="15"/>')
    if kind in ("woman", "mary"):
        parts.append(f'<path {N} d="M-26 -136 L-18 -180 Q0 -204 18 -180 L26 -136"/>')
    if kind in ("shepherd", "elder"):
        parts.append(f'<path {N} d="M38 2 L38 -205 Q38 -228 56 -222"/>')
    if kind in ("jesus", "angel", "mary"):
        parts.append(f'<circle {N} cx="0" cy="-172" r="{27 if kind == "jesus" else 23}" opacity="0.85"/>')  # halo ring
    arm = f'<path {N} d="M0 0 L2 72"/>'
    parts.append(f'<g id="{pid}-al" class="arm-l" transform="translate(-15,-146)">{arm}</g>'
                 f'<g id="{pid}-ar" class="arm-r" transform="translate(15,-146)">{arm}</g>')
    return "".join(parts)


def place(pid, k, x, y, s, flip, inner, p):
    """Outer group moves (walk, climb); inner -b bends about the feet (kneel, lie, rock, grow)."""
    if k in PEOPLE:
        body = person(pid, k)
        s *= SIZES.get(k, 1.0)
    elif k in PROPS:
        body = PROPS[k].replace("{pid}", pid).replace("{p}", p)
    else:
        raise ValueError(f"unknown cast kind {k!r}")
    # Jesus (and angels) carry a soft light; it stays outside the body group so kneel/lie pivot at the feet.
    # Faces are never drawn.
    glow = (f'<circle id="{pid}-glow" cx="0" cy="-120" r="{170 if k == "jesus" else 140}" fill="url(#{p}-halo)" opacity="0.8"/>'
            if k in ("jesus", "angel") else "")
    return (f'<g id="{pid}" transform="translate({x},{y}) scale({-s if flip else s},{s})">{glow}'
            f'<g id="{pid}-b" class="body">{inner}{body}</g></g>')


def crowd(pid, x, y, s, n, seed=9):
    r = rng(seed)
    figs = []
    for i in range(n):
        fx_ = x + (i - (n - 1) / 2) * 62 * s + (r() - 0.5) * 20
        fs = s * (0.85 + r() * 0.25)
        kind = "woman" if r() < 0.35 else ("child" if r() < 0.15 else "man")
        figs.append(f'<g transform="translate({fx_:.0f},{y + r() * 14:.0f}) scale({fs * (0.62 if kind == "child" else 1):.2f})">'
                    f'{person(f"{pid}-{i}", kind)}</g>')
    return f'<g id="{pid}"><g id="{pid}-b" class="body" opacity="0.75">{"".join(figs)}</g></g>'


def fx(p, name):
    """Full-frame effects; returns (markup, anims)."""
    c = T["line"]
    if name == "rain":
        r = rng(13)
        drops = "".join(f'<path d="M{r() * (W + 200):.0f} {r() * 2 * H:.0f} l-14 46"/>' for _ in range(200))
        return (f'<g id="{p}-rain" stroke="{c}" stroke-width="2" stroke-opacity="0.35" stroke-linecap="round">{drops}</g>',
                [{"t": f"#{p}-rain", "do": "rain"}])
    if name == "lightning":
        return (f'<path id="{p}-bolt" d="M1140 0 L1060 210 L1140 210 L1020 450 L1200 180 L1115 180 L1200 0 Z" fill="none" '
                f'stroke="#f4f7ff" stroke-width="4" opacity="0"/><rect id="{p}-flash" width="{W}" height="{H}" fill="#e8eeff" opacity="0"/>',
                [{"t": f"#{p}-flash", "do": "flash", "bolt": f"#{p}-bolt"}])
    if name == "rays":
        rays = "".join(f'<path {N} d="M{W // 2} -60 L{W // 2 + 1100 * math.sin(a):.0f} {HZ * math.cos(a):.0f}"/>'
                       for a in [i * 0.16 - 0.88 for i in range(12)])
        return f'<g id="{p}-rays" opacity="0">{rays}</g>', [{"t": f"#{p}-rays", "do": "rays"}]
    if name == "sparkle":
        r = rng(17)
        sp = "".join(f'<path d="M{x:.0f} {y - 14:.0f} l4 10 l10 4 l-10 4 l-4 10 l-4 -10 l-10 -4 l10 -4 Z"/>'
                     for x, y in ((200 + r() * 1520, 140 + r() * 620) for _ in range(34)))
        return f'<g id="{p}-sparkle" fill="{T["dot"]}" opacity="0">{sp}</g>', [{"t": f"#{p}-sparkle", "do": "sparkle"}]
    if name == "dove":  # the Spirit descending like a dove, out of an opened sky
        return (f'<g id="{p}-dove" transform="translate({W // 2},40) scale(1.2)" opacity="0">{PROPS["dove"]}</g>'
                f'<path {N} d="M{W // 2 - 220} 0 Q{W // 2} 120 {W // 2 + 220} 0" opacity="0.8"/>',
                [{"t": f"#{p}-dove", "do": "descend", "by": 380}])
    raise ValueError(f"unknown fx {name!r}")


FX = {"rain", "lightning", "rays", "sparkle", "dove"}
