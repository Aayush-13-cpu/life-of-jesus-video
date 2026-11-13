"""Paper-cut silhouette kit for 1080x1920 story Shorts.

Everything is drawn as SVG markup; motion is described as plain dicts that the page's small GSAP interpreter
turns into tweens, so every frame is deterministic and seekable. Coordinates: x across 0-1080, y down 0-1920,
the horizon at HZ, and every character or prop is placed by the point where it touches the ground.
"""
import math

W, H, HZ = 1080, 1920, 1300
INK = "#140f17"          # the silhouette colour
FEET = 1390              # where characters on the near ground stand

SKIES = {  # top, middle, horizon colours, and an optional sun/moon (kind, x, y, radius)
    "dawn": ("#1b2440", "#c86b4a", "#f2c17a", ("sun", 760, 1170, 70)),
    "day": ("#3d6fa8", "#93bddb", "#f3e2b8", ("sun", 820, 470, 58)),
    "dusk": ("#2a1a3a", "#8a3b4a", "#f09a5a", ("sun", 300, 1160, 110)),
    "night": ("#05070f", "#141a33", "#2b3160", ("moon", 800, 400, 52)),
    "storm": ("#0b0e15", "#262e3b", "#465163", None),
}


def rng(seed):
    """Seeded pseudo-random numbers, so 'random' stars and raindrops are identical on every render."""
    s = seed & 0x7FFFFFFF

    def r():
        nonlocal s
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        return s / 0x7FFFFFFF
    return r


def sky(p, name):
    top, mid, low, orb = SKIES[name]
    out = [f'<defs><linearGradient id="{p}-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/>'
           f'<stop offset="0.5" stop-color="{mid}"/><stop offset="0.68" stop-color="{low}"/><stop offset="1" stop-color="{low}"/>'
           f'</linearGradient><radialGradient id="{p}-halo"><stop offset="0" stop-color="#ffe9b0" stop-opacity="0.9"/>'
           f'<stop offset="1" stop-color="#ffe9b0" stop-opacity="0"/></radialGradient></defs>',
           f'<rect width="{W}" height="{H}" fill="url(#{p}-sky)"/>']
    anims = []
    if name in ("night", "storm"):
        r = rng(7 if name == "night" else 11)
        stars = "".join(f'<circle cx="{r() * W:.0f}" cy="{r() * 950:.0f}" r="{1 + r() * 2.2:.1f}" fill="#fff" '
                        f'opacity="{0.35 + r() * 0.65:.2f}"/>' for _ in range(110 if name == "night" else 0))
        out.append(f'<g id="{p}-stars">{stars}</g>')
        if name == "night":
            anims.append({"t": f"#{p}-stars", "do": "twinkle"})
    if orb:
        kind, x, y, rad = orb
        col = "#fff4d6" if kind == "sun" else "#e9ecf5"
        out.append(f'<circle cx="{x}" cy="{y}" r="{rad * 3.2}" fill="url(#{p}-halo)" opacity="0.55"/>'
                   f'<circle cx="{x}" cy="{y}" r="{rad}" fill="{col}"/>')
    return "".join(out), anims


def ridge(base, amp, waves, phase, op=1.0, fill=INK):
    pts = " L".join(f"{x} {base + amp * math.sin(x / W * waves * math.pi + phase):.0f}" for x in range(-40, W + 81, 60))
    return f'<path d="M-40 {H} L{pts} L{W + 40} {H} Z" fill="{fill}" opacity="{op}"/>'


def ground(p, name):
    """The landscape layers in front of the sky; returns (markup, anims)."""
    anims = []
    if name == "hills":
        g = ridge(HZ - 70, 55, 3, 0.5, 0.42) + ridge(HZ - 10, 40, 2.2, 2.0, 0.7) + ridge(FEET - 20, 22, 1.6, 4.0)
    elif name == "field":
        r = rng(5)
        tufts = "".join(f'<path d="M{x:.0f} {FEET + 8} l-6 -{18 + r() * 14:.0f} l6 10 l6 -{14 + r() * 12:.0f} l4 14 Z"/>'
                        for x in [r() * W for _ in range(40)])
        g = ridge(HZ - 50, 35, 2.5, 1.2, 0.42) + ridge(FEET - 10, 14, 1.4, 0.3) + f'<g fill="{INK}">{tufts}</g>'
    elif name == "desert":
        g = ridge(HZ - 30, 26, 2, 1.0, 0.38) + ridge(HZ + 20, 30, 1.3, 2.6, 0.62) + ridge(FEET, 12, 1.0, 3.3)
    elif name == "city":
        towers = "".join(f'<rect x="{x}" y="{HZ - h}" width="{w}" height="{h + 40}"/>'
                         for x, w, h in [(40, 70, 150), (160, 120, 90), (300, 60, 210), (380, 200, 120), (610, 90, 170),
                                         (730, 150, 100), (900, 70, 190), (980, 110, 130)])
        domes = "".join(f'<path d="M{x - r} {y} A{r} {r} 0 0 1 {x + r} {y} Z"/>' for x, y, r in
                        [(480, HZ - 120, 70), (330, HZ - 210, 30), (655, HZ - 170, 45), (935, HZ - 190, 35)])
        g = (f'<g fill="{INK}" opacity="0.55">{towers}{domes}<rect x="0" y="{HZ - 40}" width="{W}" height="80"/></g>'
             + ridge(FEET - 10, 10, 1.2, 0.8))
    elif name == "sea":
        r = rng(3)
        waves = "".join(f'<path d="M-120 {y:.0f} q30 -12 60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 '
                        f't60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0" fill="none" stroke="#dfe8ff" '
                        f'stroke-opacity="{0.08 + r() * 0.12:.2f}" stroke-width="3"/>' for y in range(HZ + 40, H, 70))
        g = (ridge(HZ - 25, 18, 2, 1.5, 0.45)
             + f'<defs><linearGradient id="{p}-sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a4a6a"/>'
               f'<stop offset="1" stop-color="{INK}"/></linearGradient></defs>'
             + f'<rect x="0" y="{HZ}" width="{W}" height="{H - HZ}" fill="url(#{p}-sea)"/><g id="{p}-waves">{waves}</g>')
        anims.append({"t": f"#{p}-waves", "do": "drift", "amp": 40, "period": 3.2})
    elif name == "garden":
        g = (ridge(HZ - 60, 40, 2.5, 0.2, 0.42) + ridge(FEET - 10, 14, 1.5, 1.0)
             + f'<path d="M560 {FEET} C560 1010 1120 980 1120 1040 L1120 {FEET} Z" fill="{INK}"/>'
             + f'<ellipse cx="800" cy="{FEET - 95}" rx="80" ry="105" fill="#030206"/>')
    else:
        raise ValueError(f"unknown ground {name!r}")
    return g, anims


# Props: drawn in INK unless they carry their own colour; (0,0) is the point that touches the ground.
PROPS = {
    "boat": '<path d="M-210 -40 L210 -40 L160 40 L-160 40 Z"/><rect x="-6" y="-330" width="10" height="300"/>'
            '<path d="M6 -320 L6 -70 L170 -70 Z" opacity="0.92"/>',
    "tree": '<path d="M-18 0 C-12 -90 -14 -180 -4 -260 L8 -260 C16 -180 14 -90 22 0 Z"/>'
            '<circle cx="-70" cy="-300" r="95"/><circle cx="60" cy="-320" r="105"/><circle cx="0" cy="-400" r="110"/>'
            '<circle cx="-120" cy="-230" r="60"/><circle cx="125" cy="-240" r="70"/>',
    "house": '<path d="M-150 0 V-210 H150 V0 Z"/><rect x="-170" y="-230" width="340" height="26"/>'
             '<rect x="-40" y="-120" width="60" height="120" fill="#f0b45a" opacity="0.85"/>'
             '<rect x="70" y="-170" width="40" height="40" fill="#f0b45a" opacity="0.85"/>',
    "rock": '<path d="M-230 0 C-240 -90 -150 -170 -20 -160 C110 -170 240 -100 230 0 Z"/>',
    "jar": '<path d="M-38 0 C-60 -40 -60 -120 -30 -150 L-24 -175 L24 -175 L30 -150 C60 -120 60 -40 38 0 Z"/>'
           '<rect id="{pid}-liq" x="-30" y="-150" width="60" height="130" rx="20" fill="#5d86b8" opacity="0.9"/>',
    "basket": '<path d="M-70 -50 L70 -50 L55 0 L-55 0 Z"/><circle cx="-35" cy="-56" r="18" fill="#c99a5b"/>'
              '<circle cx="0" cy="-62" r="20" fill="#d8a866"/><circle cx="35" cy="-56" r="18" fill="#c99a5b"/>',
    "sheep": '<circle cx="-30" cy="-60" r="30" fill="#efe6d4"/><circle cx="5" cy="-70" r="34" fill="#efe6d4"/>'
             '<circle cx="35" cy="-58" r="28" fill="#efe6d4"/><ellipse cx="68" cy="-72" rx="18" ry="14"/>'
             '<rect x="-30" y="-35" width="7" height="35"/><rect x="25" y="-35" width="7" height="35"/>',
    "pig": '<ellipse cx="0" cy="-50" rx="70" ry="38"/><ellipse cx="72" cy="-58" rx="22" ry="18"/>'
           '<rect x="-45" y="-20" width="10" height="20"/><rect x="35" y="-20" width="10" height="20"/>',
    "table": '<rect x="-170" y="-90" width="340" height="18"/><rect x="-150" y="-80" width="14" height="80"/>'
             '<rect x="136" y="-80" width="14" height="80"/><ellipse cx="-30" cy="-102" rx="45" ry="14" fill="#d8a866"/>'
             '<path d="M60 -90 L72 -130 L98 -130 L110 -90 Z" fill="#7a1f35"/>',
    "stone": '<circle cx="0" cy="-95" r="95"/><circle cx="0" cy="-95" r="60" fill="none" stroke="#2a2230" stroke-width="6"/>',
    "coin": '<circle cx="0" cy="-12" r="12" fill="#f2c96b"/><circle cx="0" cy="-12" r="26" fill="#f2c96b" opacity="0.25"/>',
    "seed": '<circle cx="0" cy="-8" r="8" fill="#f6d78b"/><circle cx="0" cy="-8" r="30" fill="#f6d78b" opacity="0.22"/>',
    "plant": '<path d="M-3 0 Q-6 -60 0 -120 Q6 -60 3 0 Z"/><path d="M0 -50 Q-40 -70 -48 -100 Q-14 -90 0 -60 Z"/>'
             '<path d="M0 -80 Q40 -100 46 -130 Q12 -122 0 -90 Z"/><circle cx="0" cy="-128" r="12" fill="#d9b25f"/>',
    "lily": '<path d="M-3 0 Q-4 -70 0 -130 Q4 -70 3 0 Z"/><path d="M0 -130 C-40 -150 -46 -190 -10 -200 C-4 -170 0 -150 0 -130 Z" '
            'fill="#f3e7c9"/><path d="M0 -130 C40 -150 46 -190 10 -200 C4 -170 0 -150 0 -130 Z" fill="#f3e7c9"/>'
            '<path d="M0 -130 C-12 -170 0 -215 0 -215 C0 -215 12 -170 0 -130 Z" fill="#fff6e0"/>',
    "thorns": '<path d="M-90 0 L-70 -60 L-55 -20 L-40 -90 L-20 -30 L0 -110 L20 -30 L40 -95 L55 -25 L75 -70 L90 0 Z"/>',
    "net": '<path d="M-160 0 Q0 -60 160 0 M-160 0 L-120 -80 M-80 -30 L-60 -100 M0 -40 L0 -110 M80 -30 L60 -100 M160 0 L120 -80 '
           'M-130 -50 Q0 -100 130 -50 M-110 -85 Q0 -125 110 -85" fill="none" stroke="#d9d2c4" stroke-width="3" opacity="0.7"/>',
    "fish": '<path d="M-30 -20 Q0 -44 30 -20 Q0 4 -30 -20 Z M30 -20 L48 -34 L48 -6 Z" fill="#cfd8e6"/>',
    "fire": '<path d="M-60 0 L60 0 L40 -14 L-40 -14 Z"/><path id="{pid}-flame" d="M-28 -14 C-34 -60 -6 -70 0 -110 '
            'C10 -70 36 -60 28 -14 Z" fill="#f0a23c"/><path d="M-12 -14 C-14 -40 0 -50 0 -70 C6 -46 14 -40 12 -14 Z" fill="#ffe28a"/>',
    "star": '<circle cx="0" cy="0" r="160" fill="#fff3c4" opacity="0.18"/><path d="M0 -70 L14 -14 L70 0 L14 14 L0 70 L-14 14 '
            'L-70 0 L-14 -14 Z" fill="#fff6d8"/><path d="M0 -150 L4 -4 L0 150 L-4 -4 Z M-150 0 L-4 -4 L150 0 L-4 4 Z" '
            'fill="#fff6d8" opacity="0.5"/>',
    "chest": '<rect x="-80" y="-90" width="160" height="90"/><path d="M-90 -90 Q0 -140 90 -90 Z"/>'
             '<rect x="-14" y="-100" width="28" height="22" fill="#f2c96b"/>',
    "birds": '<g fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"><path d="M0 0 q14 -12 28 0 q14 -12 28 0"/>'
             '<path d="M70 -40 q10 -9 20 0 q10 -9 20 0"/><path d="M-60 -30 q11 -10 22 0 q11 -10 22 0"/></g>',
}


def person(pid, kind, p):
    """A robed figure 190 units tall: body group -b (for bob/kneel/lie), arm groups -al / -ar (for gestures)."""
    fill = "#fff3d0" if kind == "angel" else INK
    parts = []
    if kind == "angel":
        parts.append(f'<circle cx="0" cy="-120" r="190" fill="url(#{p}-halo)" opacity="0.9"/>'
                     '<path d="M-10 -150 C-120 -230 -170 -120 -150 -40 C-110 -110 -60 -120 -10 -110 Z" opacity="0.8"/>'
                     '<path d="M10 -150 C120 -230 170 -120 150 -40 C110 -110 60 -120 10 -110 Z" opacity="0.8"/>')
    parts.append('<path d="M-30 0 C-28 -60 -24 -118 -17 -150 Q0 -160 17 -150 C24 -118 28 -60 30 0 Z"/>'
                 '<circle cx="0" cy="-172" r="15"/>')
    if kind in ("woman", "widow"):
        parts.append('<path d="M-18 -180 Q0 -202 18 -180 L24 -138 L-24 -138 Z"/>')
    if kind in ("shepherd", "elder"):
        parts.append('<path d="M38 2 L38 -205 Q38 -228 56 -222" fill="none" stroke="currentColor" stroke-width="6"/>')
    arm = '<path d="M-5 0 L5 0 L4 74 L-4 74 Z"/>'
    parts.append(f'<g id="{pid}-al" class="arm-l" transform="translate(-15,-146)">{arm}</g>'
                 f'<g id="{pid}-ar" class="arm-r" transform="translate(15,-146)">{arm}</g>')
    return f'<g fill="{fill}" color="{fill}">{"".join(parts)}</g>'


SIZES = {"child": 0.62, "jesus": 1.06}
PEOPLE = {"jesus", "man", "woman", "widow", "child", "shepherd", "elder", "angel"}


def place(pid, k, x, y, s, flip, inner, p):
    """Wrap a drawing so it can be moved (outer, x/y) and bent (inner -b, rotation/scale about its feet)."""
    if k in PEOPLE:
        body = person(pid, k, p)
        s *= SIZES.get(k, 1.0)
    elif k in PROPS:
        body = f'<g fill="{INK}">{PROPS[k].replace("{pid}", pid).replace("{INK}", INK)}</g>'
    else:
        raise ValueError(f"unknown cast kind {k!r}")
    sx = -s if flip else s
    # Jesus is shown as a figure in soft light, never with an invented face; the glow stays outside the body group
    # so that kneel/lie pivot around the feet, not around the glow's bounding box
    glow = (f'<circle id="{pid}-glow" cx="0" cy="-120" r="160" fill="url(#{p}-halo)" opacity="0.75"/>'
            if k == "jesus" else "")
    return f'<g id="{pid}" transform="translate({x},{y}) scale({sx},{s})">{glow}<g id="{pid}-b" class="body">{inner}{body}</g></g>'


def crowd(pid, x, y, s, n, p, seed=9):
    """A row of small figures for crowds; deterministic spacing and height."""
    r = rng(seed)
    figs = []
    for i in range(n):
        fx = x + (i - (n - 1) / 2) * 62 * s + (r() - 0.5) * 20
        fs = s * (0.85 + r() * 0.25)
        kind = "woman" if r() < 0.35 else ("child" if r() < 0.15 else "man")
        figs.append(f'<g transform="translate({fx:.0f},{y + r() * 14:.0f}) scale({fs * (0.62 if kind == "child" else 1):.2f})">'
                    f'{person(f"{pid}-{i}", kind, p)}</g>')
    return f'<g id="{pid}"><g id="{pid}-b" class="body" opacity="0.9">{"".join(figs)}</g></g>'


def fx(p, name):
    """Full-frame effects; returns (markup, anims)."""
    if name == "rain":
        r = rng(13)
        drops = "".join(f'<path d="M{x:.0f} {y:.0f} l-14 46" />' for x, y in ((r() * (W + 200), r() * 2 * H) for _ in range(170)))
        return (f'<g id="{p}-rain" stroke="#c9d6ec" stroke-width="2.5" stroke-opacity="0.45" stroke-linecap="round">{drops}</g>',
                [{"t": f"#{p}-rain", "do": "rain"}])
    if name == "lightning":
        return (f'<path id="{p}-bolt" d="M640 0 L560 360 L640 360 L520 760 L700 300 L615 300 L700 0 Z" fill="#f4f7ff" opacity="0"/>'
                f'<rect id="{p}-flash" width="{W}" height="{H}" fill="#e8eeff" opacity="0"/>',
                [{"t": f"#{p}-flash", "do": "flash", "bolt": f"#{p}-bolt"}])
    if name == "rays":
        rays = "".join(f'<path d="M540 -60 L{540 + 700 * math.sin(a):.0f} {1300 * math.cos(a):.0f} '
                       f'L{540 + 700 * math.sin(a + 0.09):.0f} {1300 * math.cos(a + 0.09):.0f} Z"/>'
                       for a in [i * 0.2 - 0.9 for i in range(10)])
        return (f'<g id="{p}-rays" fill="#fff1c8" opacity="0">{rays}</g>', [{"t": f"#{p}-rays", "do": "rays"}])
    if name == "sparkle":
        r = rng(17)
        sp = "".join(f'<path d="M{x:.0f} {y - 14:.0f} l4 10 l10 4 l-10 4 l-4 10 l-4 -10 l-10 -4 l10 -4 Z"/>'
                     for x, y in ((140 + r() * 800, 700 + r() * 600) for _ in range(26)))
        return f'<g id="{p}-sparkle" fill="#fff3c4" opacity="0">{sp}</g>', [{"t": f"#{p}-sparkle", "do": "sparkle"}]
    raise ValueError(f"unknown fx {name!r}")
