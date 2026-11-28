/* Paper pop-up motion for every video (the Shorts and the long videos of both channels), drawn by paper.py.

   The rules, strictly a pop-up book:
   - A new setting is a new page. It turns over onto the last one (hinged at the left edge), then its pieces
     (class .pp: the sun, clouds, each strip of land, every figure and prop) stand up off the page back to front,
     each hinged at its base (the branch at its top) with a springy overshoot. The opening page is already
     standing on the first frame (the hook); its figures pop up.
   - Before a new setting the page's pieces fold flat again, front first, and the next page turns over them.
   - The same setting carries on: the next beat dissolves in, what was standing stays, and only new pieces pop up.
   - Figures are paper puppets: they slide along a slot, waddle and hop as they walk, swing their arms on paper
     fasteners, and a holy figure's paper sunburst turns slowly. Only transforms and opacity are animated.
   - Every repeat is finite (n), so each frame is deterministic and seekable.

   paperScenes(tl, PLAN) builds everything onto the paused timeline tl.
   PLAN: { cfg: {W, H, turn, cam, oy, depth}, xf, beats: [{id, p, s, d, x, o, f}], anims: [{t, do, s, d, b0, ...}] } */
function paperScenes(tl, PLAN) {
  const C = PLAN.cfg;
  const n = (d, p) => Math.max(0, Math.round(d / p) - 1);   // finite repeats only (deterministic render)
  tl.set(".arm-l", { rotation: 10, transformOrigin: "50% 0%" }, 0);
  tl.set(".arm-r", { rotation: -10, transformOrigin: "50% 0%" }, 0);
  tl.set(".body", { transformOrigin: "50% 100%" }, 0);
  const arms = (t, l, r, s, d) => {
    if (l !== null) tl.to(t + "-al", { rotation: l, duration: d, ease: "back.out(1.6)" }, s);
    if (r !== null) tl.to(t + "-ar", { rotation: r, duration: d, ease: "back.out(1.6)" }, s);
  };
  const bob = (t, s, d, p, h) => tl.to(t + "-b", { y: -h, duration: p / 2, repeat: n(d, p / 2), yoyo: true, ease: "sine.inOut" }, s);
  // a puppet's waddle: the cut-out rocks from foot to foot on its slot, then settles with a little overshoot
  const waddle = (t, s, d, p, deg) => {
    tl.fromTo(t + "-b", { rotation: -deg }, { rotation: deg, duration: p, repeat: n(d, p), yoyo: true, ease: "sine.inOut", immediateRender: false }, s);
    tl.to(t + "-b", { rotation: 0, duration: 0.5, ease: "back.out(2.4)" }, s + d);
  };
  // arms swing on their fasteners against the steps, then settle (follow-through)
  const swing = (t, s, d, p, deg) => {
    tl.fromTo(t + "-al", { rotation: 10 - deg }, { rotation: 10 + deg, duration: p, repeat: n(d, p), yoyo: true, ease: "sine.inOut", immediateRender: false }, s);
    tl.fromTo(t + "-ar", { rotation: -10 + deg }, { rotation: -10 - deg, duration: p, repeat: n(d, p), yoyo: true, ease: "sine.inOut", immediateRender: false }, s);
    tl.to(t + "-al", { rotation: 10, duration: 0.6, ease: "back.out(2.2)" }, s + d);
    tl.to(t + "-ar", { rotation: -10, duration: 0.6, ease: "back.out(2.2)" }, s + d);
  };
  const F = {
    walk: a => { tl.to(a.t, { x: a.to, duration: a.d, ease: "sine.inOut" }, a.s); bob(a.t, a.s, a.d, 0.62, 9);
                 waddle(a.t, a.s, a.d, 0.62, 3); swing(a.t, a.s, a.d, 0.62, 16); },
    run: a => { tl.to(a.t, { x: a.to, duration: a.d, ease: "power1.inOut" }, a.s); bob(a.t, a.s, a.d, 0.36, 14);
                waddle(a.t, a.s, a.d, 0.36, 5); swing(a.t, a.s, a.d, 0.36, 32); },
    climb: a => tl.to(a.t, { y: a.to, duration: a.d, ease: "power1.inOut" }, a.s),
    raise: a => arms(a.t, 140, -140, a.s, 0.8),
    bless: a => arms(a.t, null, -125, a.s, 0.8),
    reach: a => arms(a.t, null, -78, a.s, 0.7),
    lower: a => arms(a.t, 10, -10, a.s, 0.8),
    kneel: a => tl.to(a.t + "-b", { scaleY: 0.68, duration: 0.6, ease: "back.out(1.6)" }, a.s),
    sit: a => tl.to(a.t + "-b", { scaleY: 0.58, duration: 0.7, ease: "back.out(1.6)" }, a.s),
    stand: a => tl.to(a.t + "-b", { scaleY: 1, rotation: 0, duration: 0.7, ease: "back.out(1.8)" }, a.s),
    lie: a => tl.set(a.t + "-b", { rotation: -90 }, a.b0),
    bow: a => tl.to(a.t + "-b", { rotation: 28, duration: 0.8, repeat: 1, repeatDelay: 0.6, yoyo: true, ease: "power2.inOut" }, a.s),
    // a piece that arrives later in the beat stands up off the page; one that leaves folds down flat
    appear: a => { tl.set(a.t, { opacity: 0 }, a.b0); tl.set(a.t, { opacity: 1 }, a.s);
                   tl.fromTo(a.t + "-b", { scaleY: 0 }, { scaleY: 1, duration: 0.7, ease: "back.out(1.8)", immediateRender: false }, a.s); },
    vanish: a => { tl.to(a.t + "-b", { scaleY: 0, duration: 0.55, ease: "back.in(1.6)" }, a.s); tl.set(a.t, { opacity: 0 }, a.s + 0.55); },
    rock: a => tl.fromTo(a.t + "-b", { rotation: -(a.amp || 4) }, { rotation: a.amp || 4, duration: (a.period || 2.4) / 2,
                repeat: n(a.d, (a.period || 2.4) / 2), yoyo: true, ease: "sine.inOut", immediateRender: false }, a.s),
    // a paper strip sliding to and fro in its slot (clouds, waves)
    drift: a => tl.fromTo(a.t, { x: -(a.amp || 40) }, { x: a.amp || 40, duration: (a.period || 3) / 2,
                 repeat: n(a.d, (a.period || 3) / 2), yoyo: true, ease: "sine.inOut", immediateRender: false }, a.s),
    fly: a => { tl.to(a.t, { x: a.to, y: a.toy === undefined ? a.y0 : a.toy, duration: a.d, ease: "none" }, a.s);
                tl.to(a.t + "-b", { scaleY: 0.55, duration: 0.18, repeat: n(a.d, 0.18), yoyo: true }, a.s); },
    grow: a => { tl.set(a.t + "-b", { scale: 0 }, a.b0); tl.to(a.t + "-b", { scale: 1, duration: a.grow || 2.4, ease: "back.out(1.4)" }, a.s); },
    collapse: a => tl.to(a.t + "-b", { rotation: 22, y: 140, opacity: 0, duration: 1.6, ease: "power2.in" }, a.s),
    roll: a => { tl.to(a.t, { x: a.to, duration: a.d, ease: "power2.inOut" }, a.s);
                 tl.to(a.t + "-b", { rotation: a.deg || 200, duration: a.d, ease: "power2.inOut" }, a.s); },
    sink: a => tl.to(a.t + "-b", { y: a.by || 90, rotation: 8, duration: a.d, ease: "power1.in" }, a.s),
    tint: a => tl.to(a.t + "-liq", { fill: a.color, duration: a.d, ease: "power1.inOut" }, a.s),
    flicker: a => tl.to(a.t + "-flame", { scaleY: 0.8, transformOrigin: "50% 100%", duration: 0.16, repeat: n(a.d, 0.16), yoyo: true }, a.s),
    // the paper sunburst behind a holy figure breathes and turns slowly
    glow: a => { tl.fromTo(a.t, { scale: 1 }, { scale: 1.05, duration: 2, repeat: n(a.d, 2), yoyo: true, ease: "sine.inOut",
                           transformOrigin: "50% 50%", immediateRender: false }, a.s);
                 tl.fromTo(a.t + " .rays", { rotation: 0 }, { rotation: Math.min(40, a.d * 2.5), duration: a.d, ease: "none",
                           transformOrigin: "50% 50%", immediateRender: false }, a.s); },
    twinkle: a => tl.fromTo(a.t, { opacity: 0.6 }, { opacity: 1, duration: 1.1, repeat: n(a.d, 1.1), yoyo: true, ease: "sine.inOut", immediateRender: false }, a.s),
    rain: a => tl.fromTo(a.t, { y: -C.H }, { y: 0, duration: 0.8, repeat: n(a.d, 0.8), ease: "none", immediateRender: false }, a.s),
    flash: a => [0.6, 2.3, 3.4].filter(o => o < a.d - 0.4).forEach(o => {
      tl.to([a.t, a.bolt], { opacity: 0.85, duration: 0.05 }, a.s + o);
      tl.to([a.t, a.bolt], { opacity: 0, duration: 0.4 }, a.s + o + 0.05); }),
    rays: a => { tl.to(a.t, { opacity: 0.4, duration: 1.4, ease: "power1.out" }, a.s + 0.3);
                 tl.to(a.t, { opacity: 0.22, duration: 1.6, repeat: n(a.d - 1.7, 1.6), yoyo: true, ease: "sine.inOut" }, a.s + 1.7); },
    sparkle: a => { tl.to(a.t, { opacity: 1, duration: 0.8 }, a.s + 0.4);
                    tl.to(a.t, { opacity: 0.4, duration: 0.6, repeat: n(a.d - 1.2, 0.6), yoyo: true }, a.s + 1.2); },
    // breathing scales the drawing (-s), not the body (-b), so it never undoes a sit
    breathe: a => tl.fromTo(a.t + "-s", { scale: 1 }, { scale: 1.025, duration: 2, repeat: n(a.d, 2), yoyo: true, ease: "sine.inOut",
                transformOrigin: "50% 100%", immediateRender: false }, a.s),
    whirl: a => tl.fromTo(a.t + "-b", { scaleX: 1 }, { scaleX: -1, duration: 0.5, repeat: n(a.d, 0.5), yoyo: true, ease: "sine.inOut",
              immediateRender: false }, a.s),
    dance: a => { bob(a.t, a.s, a.d, 0.8, 10); waddle(a.t, a.s, a.d, 0.8, 4);
                  tl.fromTo(a.t + "-al", { rotation: 10 }, { rotation: 150, duration: 0.8, repeat: n(a.d, 0.8), yoyo: true, ease: "sine.inOut", immediateRender: false }, a.s);
                  tl.fromTo(a.t + "-ar", { rotation: -150 }, { rotation: -10, duration: 0.8, repeat: n(a.d, 0.8), yoyo: true, ease: "sine.inOut", immediateRender: false }, a.s); },
    open: a => { tl.to(a.t + "-door", { scaleX: 0.15, transformOrigin: "100% 50%", duration: 1.2, ease: "power2.out" }, a.s);
                 tl.to(a.t + "-bird", { x: 170, y: -180, duration: 1.8, ease: "power1.out" }, a.s + 0.9); },
    petals: a => { tl.fromTo(a.t, { y: 0 }, { y: a.by || 700, duration: a.d, ease: "none", immediateRender: false }, a.s);
                   tl.fromTo(a.t, { x: -30 }, { x: 30, duration: 2.5, repeat: n(a.d, 2.5), yoyo: true, ease: "sine.inOut", immediateRender: false }, a.s); },
    mist: a => { tl.fromTo(a.t + "-a", { x: -140 }, { x: 140, duration: a.d, ease: "sine.inOut", immediateRender: false }, a.s);
                 tl.fromTo(a.t + "-c", { x: 120 }, { x: -120, duration: a.d, ease: "sine.inOut", immediateRender: false }, a.s); },
    ripples: a => tl.fromTo(a.t + " ellipse", { scale: 0.2, opacity: 0.9 }, { scale: 1.8, opacity: 0, duration: 3, ease: "sine.out",
                transformOrigin: "50% 50%", stagger: { each: 1, repeat: n(a.d - 2, 3) }, immediateRender: false }, a.s),
    fireflies: a => { tl.fromTo(a.t + " circle", { opacity: 0.1 }, { opacity: 1, duration: 0.9, ease: "sine.inOut",
                        stagger: { each: 0.11, repeat: n(a.d - 4.4, 0.9), yoyo: true }, immediateRender: false }, a.s);
                      tl.fromTo(a.t, { y: 0 }, { y: -60, duration: a.d, ease: "none", immediateRender: false }, a.s); },
    descend: a => tl.fromTo(a.t, { opacity: 0, y: 40 }, { opacity: 1, y: 40 + a.by, duration: 3.4, ease: "power1.out", immediateRender: false }, a.s + 0.6),
    // a paper figure on its tab is never quite still: it rocks a hair on its base
    idle: a => { const p = a.period || 4.2, s = a.s + (a.phase || 0), d = Math.max(0, a.d - (a.phase || 0));
                 tl.fromTo(a.t + "-s", { rotation: -0.8 }, { rotation: 0.8, duration: p / 2, repeat: n(d, p / 2), yoyo: true, ease: "sine.inOut",
                           transformOrigin: "50% 100%", immediateRender: false }, s); },
    // the branch nearest the camera swings a little on its pin at the top of the page
    sway: a => tl.fromTo(a.t, { rotation: -1.2 }, { rotation: 1.2, duration: 2.6, repeat: n(a.d, 2.6), yoyo: true, ease: "sine.inOut",
               transformOrigin: "0% 0%", immediateRender: false }, a.s),
  };
  const hinge = el => (el.classList.contains("top") ? "50% 0%" : "50% 100%");
  let cam = null;
  PLAN.beats.forEach((b, i) => {
    const sc = "#" + b.id + "-in";
    // camera [scale, x, medium]: a medium shot frames the beat's main figure (b.f), or stays wide with no one to frame
    const pick = j => { const [s, x, m] = C.cam[j % C.cam.length];
                        return !m ? [s, x, 0.5, 0] : b.f === null ? [C.cam[0][0], 0, 0.5, 0] : [s, 0, Math.min(0.68, Math.max(0.32, b.f)), 1]; };
    const from = b.x && cam ? cam : pick(i + 2), p = pick(i);
    // one setting is one continuous camera: keep its origin, so the dissolve lines up with the beat underneath
    const to = b.x && cam ? [p[0], p[1], cam[2], cam[3]] : p;
    cam = to;
    tl.fromTo(sc, { scale: from[0], x: from[1] }, { scale: to[0], x: to[1], duration: b.d, ease: "sine.inOut",
              transformOrigin: (to[2] * 100) + "% " + C.oy[to[3]] + "%", immediateRender: false }, b.s);
    // multiplane: the sky page lags the camera, the land lags less, the branch leads
    const k = Math.max(-0.06, Math.min(0.06, (to[0] - from[0]) / to[0]));
    C.depth.forEach(([L, f]) => { if (document.querySelector("#" + b.p + L))
      tl.fromTo("#" + b.p + L, { x: f * from[1], scale: 1 }, { x: f * to[1], scale: 1 + f * k, duration: b.d, ease: "sine.inOut",
                svgOrigin: (to[2] * C.W) + " " + (0.72 * C.H), immediateRender: false }, b.s); });
    const pieces = Array.from(document.querySelectorAll(sc + " .pp"));
    // the same setting, or the opening page (already standing on the first frame, the hook): only new figures pop
    const fresh = b.x || i === 0 ? pieces.filter(el => el.classList.contains("new")) : pieces;
    let t0;
    if (b.x) {           // the same setting: dissolve over the last beat; what stood there stays standing
      tl.fromTo(sc, { opacity: 0 }, { opacity: 1, duration: PLAN.xf, ease: "none", immediateRender: false }, b.s);
      t0 = b.s + 0.1;
    } else if (i > 0) {  // a new setting: the page turns over onto the last one, flat, then its pieces stand up
      tl.fromTo("#" + b.id + "-pg", { scaleX: 0.03, skewY: -6 }, { scaleX: 1, skewY: 0, duration: C.turn, ease: "power2.inOut",
                transformOrigin: "0% 50%", immediateRender: false }, b.s);
      t0 = b.s + C.turn * 0.7;
    } else t0 = b.s + 0.15;
    // flat on the page from the first frame; the hinge is set in the same step (GSAP's smoothOrigin would otherwise
    // shift a piece whose origin changes after it was scaled)
    fresh.forEach(el => tl.set(el, { scaleY: 0, transformOrigin: hinge(el) }, b.s));
    const gap = Math.min(0.12, 1.3 / Math.max(1, fresh.length));
    fresh.forEach((el, j) => tl.fromTo(el, { scaleY: 0 }, { scaleY: 1, duration: 0.7, ease: "back.out(1.8)", transformOrigin: hinge(el),
                                       immediateRender: false }, t0 + j * gap));
    // the next beat is a new setting: fold everything flat, front first, before its page turns over
    if (b.o) { const g = Math.min(0.03, 0.12 / Math.max(1, pieces.length));
      pieces.slice().reverse().forEach((el, j) => tl.to(el, { scaleY: 0, duration: 0.3, ease: "power2.in", transformOrigin: hinge(el) },
                                                       b.s + b.d - 0.42 + j * g)); }
  });
  PLAN.anims.forEach(a => F[a.do](a));
}
