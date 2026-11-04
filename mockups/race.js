// One scripted race shared by the replay mockups: who is where, lane by lane, at each call.
// In the game this story would be generated from the result; here it's written by hand.
// Distances are in feet; one length is 8 ft. Lanes: 0 the rail, 1 parked out, 2 three-wide.
const RACE = {
  title: "Race 4 · NW$20k · 1 mile · $11,000",
  S: 1100, R: 490, LEN: 8,
  TT: [0, 27.4, 56.2, 84.1, 112], DD: [0, 1320, 2640, 3960, 5280],     // the leader's quarters
  CT: [0, 14, 27.4, 56.2, 84.1, 100, 112],                              // when each call below is taken
  PAD: ["#d8322f", "#1f4fbf", "#f3f3f3", "#1f8f3f", "#1a1a1a", "#f2d233", "#e88fb0", "#9a9a9a", "#6b3fa0", "#7fc4e8"],
  DARK: [3, 6, 8, 10],
  // name, coat, lengths behind the leader at each call, lane at each call
  H: [
    ["H2466", "#5a3420", [0, .5, 1.5, 1.5, 1.5, 1.25, 3], [0, 0, 0, 0, 0, 0, 0]],
    ["H2541", "#3d2a1e", [0, 1, 3, 3.5, 3.5, 4, 5.5], [1, .6, 0, 0, 0, .5, 1]],
    ["H2395", "#8a4a26", [0, 0, 0, 0, 0, 0, 0], [2, 1, 0, 0, 0, 0, 0]],
    ["H2251", "#241a16", [0, 1.5, 4.5, 5, 6, 7, 9.5], [3, 1.5, 0, 0, 0, 0, 0]],
    ["H2408", "#5a3420", [0, 1, 2.5, 1.5, .75, .5, 1.75], [4, 2, 1, 1, 1, 1, 1]],
    ["H2771", "#8c8f95", [0, 2, 5.5, 5.5, 4.5, 3.5, 4.25], [5, 2.5, 0, 0, 1, 1.6, 2]],
    ["H2299", "#3d2a1e", [0, 2.5, 4, 2.5, 2, 2, 3.5], [6, 3, .5, 1, 1, 1.4, 1.7]],
    ["H2667", "#8a4a26", [0, 3, 6.5, 7, 8, 9, 11], [7, 3.5, 0, 0, 0, 0, 0]],
    ["H2750", "#241a16", [1.3, 3.5, 7.5, 8.5, 8.5, 8, 7.5], [0, 0, 0, 0, 0, .5, 1.5]],
    ["H2749", "#8c8f95", [1.3, 4, 8.5, 9.5, 10, 12, 14], [1, .5, 0, 0, 0, 0, 0]]],
  CAPS: [[0, "They're away. The gate folds clear"], [6, "H2395 leaves sharply from post 3"],
    [16, "H2395 clears to the lead, H2466 tucks into the pocket"], [33, "H2408 pulls first-over, H2299 follows cover"],
    [56.2, "Half in :56.2, H2408 still parked out"], [84.1, "Three-quarters in 1:24.1, H2395 in command"],
    [98, "Into the stretch, H2408 ranges up on the outside"], [106, "H2395 digs in"], [112, "H2395 wins it in 1:52.0"]],
  END: 118, FIN: 112, ME: 2,
};
RACE.L = 2 * RACE.S + 2 * Math.PI * RACE.R;
RACE.SF = RACE.S - 150;                                                  // finish line, on the homestretch

// Smooth curves through the calls: a cubic with continuous speed, so nobody surges or stalls
// at a quarter pole. Tangents are the slope across each call; the leader's are kept monotone.
RACE.curve = (ts, vs, monotone) => {
  const n = ts.length, m = vs.map((_, i) => i === 0 ? (vs[1] - vs[0]) / (ts[1] - ts[0])
    : i === n - 1 ? (vs[n - 1] - vs[n - 2]) / (ts[n - 1] - ts[n - 2])
    : (vs[i + 1] - vs[i - 1]) / (ts[i + 1] - ts[i - 1]));
  if (monotone) m.forEach((_, i) => { m[i] = Math.max(0, m[i]); });
  return t => {
    if (t <= ts[0]) return vs[0];
    if (t >= ts[n - 1]) return vs[n - 1] + m[n - 1] * (t - ts[n - 1]);
    let i = 1; while (t > ts[i]) i++;
    const h = ts[i] - ts[i - 1], u = (t - ts[i - 1]) / h, u2 = u * u, u3 = u2 * u;
    return (2 * u3 - 3 * u2 + 1) * vs[i - 1] + (u3 - 2 * u2 + u) * h * m[i - 1] + (-2 * u3 + 3 * u2) * vs[i] + (u3 - u2) * h * m[i];
  };
};
// For real races: position eases between calls with no overshoot, so nobody runs through the horse
// ahead; a lane change happens in the last few seconds before its call and then holds, the way a
// driver tips out or tucks in, instead of drifting sideways for a whole quarter.
RACE.ease = (ts, vs, win) => t => {
  if (t <= ts[0]) return vs[0];
  for (let i = 1; i < ts.length; i++) if (t <= ts[i]) {
    const wi = Array.isArray(win) ? win[i - 1] : win, w = wi ? Math.min(wi, ts[i] - ts[i - 1]) : ts[i] - ts[i - 1];
    let u = (t - (ts[i] - w)) / w; u = Math.max(0, Math.min(1, u)); u = u * u * (3 - 2 * u);
    return vs[i - 1] + (vs[i] - vs[i - 1]) * u;
  }
  return vs[vs.length - 1];
};
// Each driver's silks: one color per horse, unique in the race and clearly unlike its own saddle pad (the pad
// colors are fixed by post; silks belong to the stable). Picked from the horse's name, so a horse's silks
// never change from race to race.
RACE.SILKS = ["#c0392b", "#e67e22", "#f1c40f", "#27ae60", "#16a085", "#2e86de", "#1b2a6b", "#8e44ad", "#e84393", "#6d4c41", "#ecf0f1", "#111418", "#a3cb38", "#00cec9", "#5b0f1e", "#f8c291", "#7f8fa6", "#0a5c36", "#b8a9f0", "#ff6b00", "#004d61", "#d4af37"];
RACE.silks = () => {
  if (RACE.H.length && RACE.H.every(h => h.silks)) { RACE.SILK = RACE.H.map(h => h.silks.join("|")); return; }   // drivers wear their own colors: jacket|trim
  const rgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)), far = (a, b) => { const x = rgb(a), y = rgb(b); return Math.hypot(x[0] - y[0], x[1] - y[1], x[2] - y[2]) > 80; };   // 80: up to 15 mutually distinct colors in this palette
  // each horse tries colors starting from its own (name) choice; backtrack until every horse has one unlike
  // its pad and unlike every other horse's silks
  const N = RACE.SILKS.length, start = RACE.H.map(h => [...h[0]].reduce((a, ch) => (a * 33 + ch.charCodeAt(0)) >>> 0, 11) % N);
  const out = [];
  let steps = 0;
  const place = i => {
    if (i === RACE.H.length) return true;
    if (++steps > 20000) return false;                                    // bounded: falls back below rather than hang
    for (let n = 0; n < N; n++) { const c = RACE.SILKS[(start[i] + n) % N];
      if (far(c, RACE.PAD[i]) && out.every(u => far(c, u))) { out.push(c); if (place(i + 1)) return true; out.pop(); } }
    return false;
  };
  if (!place(0)) { out.length = 0; RACE.H.forEach((h, i) => out.push(RACE.SILKS[(start[i] + i) % N])); }   // search ran out: still give everyone a color
  RACE.SILK = out.map((c, i) => RACE.H[i].silks ? RACE.H[i].silks.join("|") : c);   // a horse in its barn's harness colors keeps them, in older races too
};
RACE.rebuild = () => {
  RACE.silks();
  RACE.paths = null;
  RACE.D = RACE.curve(RACE.TT, RACE.DD, true);                           // leader's distance run
  RACE.H.forEach(h => {
    h.b = RACE.real ? RACE.ease(RACE.CT, h[2]) : RACE.curve(RACE.CT, h[2]);
    h.lane = RACE.real ? RACE.ease(RACE.CT, h[3], [0, 0, 6, 6, 4, 0]) : RACE.curve(RACE.CT, h[3]);   // the field cuts over to the rail through the whole first turn
    h.b.hold = h[2][6]; h.lane.hold = h[3][6];
  });
};
RACE.rebuild();
// Load a real race's story (from /race/<id>.json) in place of the scripted one. The story holds
// lengths behind and lane at seven calls per horse, in finishing order; here they're put back
// in post order so colors and pads follow the saddle cloth.
RACE.load = async (id, myName) => {
  const r = await fetch(`/race/${encodeURIComponent(id)}.json`); if (!r.ok) return false;
  const s = await r.json();
  const horses = [...s.horses].sort((a, b) => a.post - b.post);
  RACE.title = `${s.name} · ${s.track === "half" ? "half-mile" : "mile"} · $${s.purse.toLocaleString()}`;
  RACE.venue = s.venue || "Harness Park";
  RACE.tlook = s.tlook || null;                                             // the track's identity: colors, type, badge, motto                                // the track it was run at (older races: the flagship)
  RACE.TT = s.quarters; RACE.DD = [0, 1320, 2640, 3960, 5280];
  RACE.REC = s.records || null;                                           // course records going in (null: none yet, or an older story)
  RACE.CT = s.calls; RACE.FIN = s.final; RACE.END = s.final + 12;   // room to run on past the wire, the result, and the winner's circle
  horses.forEach(h => { h.lane[0] = h.post - 1; h.behind[0] = 0; });       // everyone on the gate, one wide line (older saved stories had a second tier)
  // older saved stories carry no coat: give each horse one from its name, in the breed's proportions
  const COATS = ["bay", "bay", "bay", "bay", "bay", "brown", "brown", "black", "black", "chestnut", "chestnut", "grey"];
  const pick = n => COATS[[...n].reduce((a, ch) => (a * 31 + ch.charCodeAt(0)) >>> 0, 7) % COATS.length];
  RACE.H = horses.map(h => Object.assign([h.name, "#5a3420", h.behind, h.lane], { broke: h.broke_at ?? null, fractious: !!h.fractious, stamina: h.stamina || 0, early: h.early || 0, coat: h.coat || pick(h.name), odds: h.odds || "", owner: h.owner || "", stable: h.stable || "", player: !!h.player, silks: h.silks || null, wraps: h.wraps || "", mask: h.mask || "", driver: h.driver || "", emblem: h.emblem || "", marquee: h.marquee || "" }));
  RACE.PICK = s.pick || ""; RACE.HERO = s.hero ? horses.findIndex(h => h.name === s.hero) : -1;   // a scripted showcase: its hero runs exactly as written
  RACE.MATINEE = !!s.matinee;                                              // a daytime track: the replay draws it in daylight
  RACE.PASSING = !!s.passing; RACE.DIVER = horses.findIndex(h => (h.trip || "").includes("passing lane"));   // a passing-lane track, and who goes up it
  RACE.real = true; RACE.CAPS = s.captions; RACE.ME = Math.max(0, horses.findIndex(h => h.name === myName));
  RACE.PAD = RACE.PAD.concat(["#2e8b8b", "#c05020"]).slice(0, Math.max(10, horses.length));
  RACE.rebuild(); return true;
};
RACE.BODY = 15.5;                                                        // nose to sulky wheel, ft: no two runners closer than this in one lane
RACE.WIDE = 5.4;                                                         // a sulky's width, ft: closer than this sideways and they'd touch
// Where the story wants a runner at time t (no physics): distance run and feet off the rail.
RACE.story = (h, t) => {
  const b = t >= RACE.FIN ? h.b.hold : h.b(t), ln = t >= RACE.FIN ? h.lane.hold : h.lane(t);
  const go = RACE.CT[4] - 6, wide = h.wide && t > go ? h.wide * Math.min(1, (t - go) / 6) : 0;   // a closer that got boxed is sent wide, but only for its run off the far turn (see RACE.state)
  return [RACE.D(t) - b * RACE.LEN, 4 + (ln + wide) * 6];                       // a lane is a sulky's width, ~6 ft; the rail horse 4 ft off the fence
};
// The race as it's drawn: every runner chases its story position under real limits (how hard it can
// speed up, brake and move sideways), can't run up the back of a horse ahead or move across into one
// alongside, and so gets held up or boxed in instead of passing through. Stepped 20 times a second
// once per race and stored, so scrubbing just reads the track.
RACE.HZ = 20;
RACE.simulate = () => {
  // ------------------------------------------------------------------
  // Harness-feel rewrite
  // Goals:
  //   - low acceleration (no Thoroughbred surges)
  //   - committed, slow lane changes
  //   - early-race single-file discipline
  //   - parked / three-wide horses stay out longer and "pay"
  //   - closers wait, then swing decisively
  //   - finish order still matches the story (lengths + lanes at calls)
  // ------------------------------------------------------------------
  const dt = 1 / RACE.HZ;
  const n = Math.ceil(RACE.END * RACE.HZ) + 2;
  const H = RACE.H;
  const rank = H.map((h, i) => i)
    .sort((a, b) => H[a][2][6] - H[b][2][6])
    .reduce((m, i, place) => (m[i] = place, m), {});

  // Tunables for the feel
  const MAX_ACCEL = 3.8;          // ft/s²  (was ~6-9) — trotters don't explode
  const MAX_DECEL = 6.5;          // ft/s²
  const LANE_SPEED = 3.2;         // ft/s sideways when changing lanes (slow tip)
  const COMMIT_TIME = 1.5;        // seconds a lane change is locked once started
  const EARLY = RACE.CT[3];       // roughly the half — stay disciplined until then
  const STRETCH = RACE.CT[5] - 7; // start of real stretch action
  const BODY = RACE.BODY;
  const WIDE = RACE.WIDE;

  const run = H.map((h, i) => {
    const [d0, o0] = RACE.story(h, 0);
    const [d1] = RACE.story(h, dt);
    return {
      i, h, rank: rank[i],
      d: d0, o: o0,
      v: (d1 - d0) / dt,
      // lateral state
      ov: 0,              // current lateral velocity
      wantO: o0,          // target offset we are currently committed to
      commitT: 0,         // time left on the current lateral commitment
      side: 0,            // last chosen side for a go-round
      path: new Float32Array(n * 2)
    };
  });

  const minO = r => r.i === RACE.DIVER
    ? 4 - Math.min(6, RACE.inset(RACE.SF + r.d))
    : 4;

  const yields = (r, p, late) => !late || p.rank < r.rank;

  const ahead = (r, o, late) => run.filter(p =>
    p !== r && p.d > r.d && Math.abs(p.o - o) < WIDE && yields(r, p, late));

  const crowds = (r, o) => run.some(p =>
    p !== r &&
    Math.abs(p.d - r.d) < BODY &&
    Math.abs(p.o - o) < Math.min(WIDE, Math.abs(p.o - r.o) + 0.3));

  // Start them a legal body apart if the story put two on top of each other
  for (const r of [...run].sort((a, b) => b.d - a.d))
    for (const p of ahead(r, r.o, false))
      r.d = Math.min(r.d, p.d - BODY);

  for (let k = 0; k < n; k++) {
    const t = k * dt;
    const late = t > STRETCH;
    const early = t < EARLY;

    // write current state
    for (const r of run) {
      r.path[k * 2] = r.d;
      r.path[k * 2 + 1] = r.o;
    }

    // process front-to-back so leaders move first
    for (const r of [...run].sort((a, b) => b.d - a.d)) {

      // ---------- HERO / showcase: exact story ----------
      if (r.i === RACE.HERO) {
        const [d, o] = RACE.story(r.h, t + dt);
        r.v = (d - r.d) / dt;
        r.d = d;
        r.o = o;
        continue;
      }

      // ---------- target from the story ----------
      const [sd, so] = RACE.story(r.h, t + dt);
      const [sd0] = RACE.story(r.h, t);
      const storyV = (sd - sd0) / dt;                 // speed the story wants right now
      const storyLane = (so - 4) / 6;                 // story lane index

      // ---------- longitudinal (speed) ----------
      // Pull toward the story speed, but with tight accel limits.
      // Extra cost when parked / three-wide so those horses look like they are working.
      const parkedPenalty = Math.max(0, (r.o - 4) / 6 - 0.4) * 0.7;  // ~0.7 ft/s slower per extra lane
      let targetV = storyV - parkedPenalty;

      // Never run through a horse ahead in the same lane
      let held = false;
      for (const p of ahead(r, r.o, late)) {
        const room = p.d - r.d - BODY;
        const cap = room < 0
          ? p.v + room * 1.2
          : p.v + Math.sqrt(2 * MAX_DECEL * Math.max(0, room));
        if (targetV > cap) {
          targetV = Math.max(cap, r.v - MAX_DECEL * dt);
          held = true;
        }
      }

      // Soft clamp so we don't overshoot the story position late
      if (late && r.d + targetV * dt > sd + 2) {
        targetV = Math.max((sd - r.d) / dt, r.v - MAX_DECEL * dt);
      }

      // Apply limited acceleration
      const dv = targetV - r.v;
      const maxDv = (dv > 0 ? MAX_ACCEL : MAX_DECEL) * dt;
      r.v += Math.max(-maxDv, Math.min(maxDv, dv));

      // ---------- lateral (lane) ----------
      // 1. Desired offset from story
      let desiredO = so;

      // 2. Early race: strongly prefer staying put unless the story change is large
      if (early) {
        const storyDelta = Math.abs(so - r.o);
        if (storyDelta < 3.5) {           // less than ~0.6 lanes
          desiredO = r.o;                 // hold current line
        }
      }

      // 3. If held up and the story still wants us further forward, commit to a go-round
      if ((held || (late && storyV > r.v + 1.5)) && sd - r.d > 3 && !early) {
        if (r.commitT <= 0) {
          // pick a side once
          const outOK = !crowds(r, r.o + WIDE * 1.1);
          const inOK  = r.o > minO(r) + 2 && !crowds(r, r.o - WIDE * 1.1);
          if (outOK) r.side = 1;
          else if (inOK) r.side = -1;
          else r.side = 0;
          if (r.side) {
            r.commitT = COMMIT_TIME + 0.6;
            desiredO = r.o + r.side * WIDE * 1.15;
            r.wantO = desiredO;
          }
        }
      }

      // 4. Commitment: once we start a lateral move we finish it
      if (r.commitT > 0) {
        r.commitT -= dt;
        desiredO = r.wantO;
      } else {
        // new commitment only if the desired is meaningfully different
        if (Math.abs(desiredO - r.o) > 1.8) {
          r.wantO = desiredO;
          r.commitT = COMMIT_TIME;
        } else {
          r.wantO = desiredO;
        }
      }

      // 5. Parked / three-wide horses resist dropping in too early
      //    (they look like they are still working on the outside)
      const storyWantsIn = (so - r.o) < -2.5;
      if (!late && r.o > 4 + 6 * 0.9 && storyWantsIn && r.commitT <= 0) {
        // delay the drop-in a bit unless the story is screaming for it
        if (Math.abs(so - r.o) < 5) {
          desiredO = r.o;                 // stay out
          r.wantO = r.o;
        }
      }

      // 6. In the stretch, higher-ranked horses get clearer right of way;
      //    lower-ranked ones give ground laterally rather than collide
      if (late) {
        for (const p of run) {
          if (p === r) continue;
          if (Math.abs(p.d - r.d) < BODY + 4 && Math.abs(p.o - r.o) < WIDE + 1) {
            if (p.rank < r.rank) {
              // they finish ahead of us — we should not sit on their line
              if (Math.abs(desiredO - p.o) < WIDE * 0.85) {
                desiredO = p.o + Math.sign(r.o - p.o || 1) * WIDE * 1.05;
              }
            }
          }
        }
      }

      // 7. Move laterally with limited speed and no crowding
      const maxDo = LANE_SPEED * dt;
      let do_ = Math.max(-maxDo, Math.min(maxDo, desiredO - r.o));
      let nextO = r.o + do_;

      // clamp to inside rail
      nextO = Math.max(minO(r), nextO);

      // refuse the move if it would crowd someone
      if (crowds(r, nextO) && Math.abs(do_) > 0.05) {
        // try half step, otherwise stay
        const half = r.o + do_ * 0.4;
        if (!crowds(r, half) && half >= minO(r)) nextO = half;
        else nextO = r.o;
      }

      r.o = nextO;
      r.d += r.v * dt;
      // the run to the wire: each horse eases onto its story distance over the last six seconds, so at the official time every
      // nose is where the result says (the winner's on the wire, the margins as charted); the feel above shapes the race before that
      if (t > RACE.FIN - 6) { const u = Math.min(1, (t - (RACE.FIN - 6)) / 6); r.d += (sd - r.d) * u * u * .25; }
    }
  }

  RACE.paths = run.map(r => r.path);
  RACE.pathN = n;
}
;
RACE.state = t => {                                                      // everyone at time t: distance, lane, track offset
  if (!RACE.paths || RACE.paths.src !== RACE.H) {
    // Run the race; any horse that finishes worse than the official result was boxed in, so send it
    // wider through the stretch and run it again, the way a closer swings out to find clear track.
    RACE.H.forEach(h => h.wide = 0);
    const want = RACE.H.map((h, i) => i).sort((a, b) => RACE.H[a][2][6] - RACE.H[b][2][6]);
    for (let pass = 0; pass < 6; pass++) {
      RACE.simulate();
      const k = Math.floor(RACE.FIN * RACE.HZ), got = RACE.paths.map((p, i) => i).sort((a, b) => RACE.paths[b][k * 2] - RACE.paths[a][k * 2]);
      const late = want.filter((i, place) => got.indexOf(i) > place && RACE.H[i].wide < 4 && i !== RACE.HERO);
      if (!late.length) break;
      late.forEach(i => RACE.H[i].wide += 1);
    }
    // Still the wrong horse first across the wire after every try (Northern Star, 2627-ls-mile-Open-0, was shut in on the
    // rail): the winner runs its own story line exactly, and the field parts for it. Only a race that came out wrong is run
    // again, so every other replay stays as it was.
    const wire = RACE.D(RACE.FIN), crossing = p => { for (let k = 0; k < RACE.pathN; k++) if (p[k * 2] >= wire) return k; return 1e9; };
    const first = RACE.paths.map((p, i) => i).sort((a, b) => crossing(RACE.paths[a]) - crossing(RACE.paths[b]))[0];
    if (first !== want[0] && RACE.HERO < 0) {
      RACE.HERO = want[0];
      RACE.H[want[0]].wide = 0;                                         // its own story's line, not extra lanes the retries tried (it went 7 wide)
      RACE.simulate();
      RACE.HERO = -1;
    }
    RACE.paths.src = RACE.H;
  }
  const f = Math.max(0, Math.min(RACE.pathN - 1.001, t * RACE.HZ)), k = Math.floor(f), u = f - k;
  return RACE.paths.map((p, i) => {
    let d = p[k * 2] + (p[k * 2 + 2] - p[k * 2]) * u; const o = p[k * 2 + 1] + (p[k * 2 + 3] - p[k * 2 + 1]) * u;
    if (t > RACE.FIN) {                                                   // past the finish: everyone keeps running at the pace they hit the wire
      const kf = Math.floor(RACE.FIN * RACE.HZ), v = (p[kf * 2] - p[(kf - 2) * 2]) * RACE.HZ / 2;
      d = p[kf * 2] + v * (t - kf / RACE.HZ);
    }
    return { i, d, ln: (o - 4) / 6, o, s: RACE.SF + d };
  });
};
RACE.camLead = st => {                                                   // the front of the field, as a smooth max: no kink when the lead changes hands
  const top = Math.max(...st.map(h => h.d)); let e = 0;
  for (const h of st) e += Math.exp((h.d - top) / 12);
  return top + 12 * Math.log(e);
};
RACE.camS = st => {                                                      // where cameras aim: near the front, never jumping when places swap
  const sum = st.reduce((a, h) => a + h.d, 0);
  return RACE.SF + RACE.camLead(st) * .85 + (sum / st.length) * .15;    // mostly the leaders; a strung-out field still pulls it back a touch
};
// The passing lane: down the homestretch the inside rail swings 8 ft into the infield, opening a lane inside the
// leader from the top of the stretch to just past the wire. inset(s) is how far in the rail sits at s (0 elsewhere).
RACE.inset = s => { if (!RACE.PASSING) return 0; s = ((s % RACE.L) + RACE.L) % RACE.L; const a = 90, w = RACE.SF + 40, b = RACE.SF + 130;
  return s < a ? 8 * s / a : s < w ? 8 : s < b ? 8 * (1 - (s - w) / (b - w)) : 0; };
RACE.pt = (s, o) => {                                                    // a point on the oval: s along the rail, o feet out
  const { S, R, L } = RACE, PI = Math.PI;
  s = ((s % L) + L) % L;
  if (s < S) return [-S / 2 + s, R + o];
  if (s < S + PI * R) { const t = PI / 2 - (s - S) / R, r = R + o; return [S / 2 + r * Math.cos(t), r * Math.sin(t)]; }
  if (s < 2 * S + PI * R) return [S / 2 - (s - S - PI * R), -(R + o)];
  const t = -PI / 2 - (s - 2 * S - PI * R) / R, r = R + o; return [-S / 2 + r * Math.cos(t), r * Math.sin(t)];
};

// ------------------------------------------------------------ broadcast HUD, shared by both mockups
RACE.fmt = t => { const m = Math.floor(t / 60), s = (t % 60).toFixed(1); return `${m}:${s.padStart(4, "0")}`; };
RACE.lengths = x => {
  if (x < .12) return ""; if (x < .3) return "nk";
  const w = Math.floor(x), q = Math.round((x - w) * 4) / 4;
  return (q === 1 ? w + 1 : (w || "")) + ({ 0: "", .25: "¼", .5: "½", .75: "¾", 1: "" }[q]);
};
RACE.pad = (i, size = 22) => `<span class="pad" style="width:${size}px;height:${size}px;background:${RACE.PAD[i]};color:${RACE.DARK.includes(i + 1) ? "#111" : "#fff"}${i === 4 ? ";box-shadow:inset 0 0 0 1px #5b6270" : ""}">${i + 1}</span>`;
RACE.hud = (t, ord) => {
  const $ = id => document.getElementById(id);
  $("clk").textContent = RACE.fmt(Math.min(t, RACE.FIN));
  $("cap").textContent = ([...RACE.CAPS].reverse().find(c => t >= c[0]) || RACE.CAPS[0])[1];
  // each split against the course record: green under it, red over, white level
  const vs = i => !RACE.REC ? "" : RACE.TT[i + 1] < RACE.REC[i] ? " fast" : RACE.TT[i + 1] > RACE.REC[i] ? " slow" : "";
  $("fr").innerHTML = ["¼", "½", "¾", "Fin"].map((n, i) => `<span class="${t >= RACE.TT[i + 1] ? "on" + vs(i) : ""}"><small>${n}</small>${t >= RACE.TT[i + 1] ? RACE.fmt(RACE.TT[i + 1]) : "–"}</span>`).join("");
  const lead = ord[0].d;
  $("ord").innerHTML = ord.map((h, k) => `<div class="oc${h.i === RACE.ME ? " me" : ""}">${RACE.pad(h.i)}<small>${k ? RACE.lengths((lead - h.d) / RACE.LEN) : ""}</small></div>`).join("");
};
RACE.controls = (onScrub) => {                                           // speed 1x/2x/5x, pause, scrub; returns live state
  const st = { t: 0, speed: 1, play: true };
  const pp = document.getElementById("pp"), sc = document.getElementById("sc");
  sc.max = RACE.END;
  st.refit = () => { sc.max = RACE.END; };
  pp.onclick = () => { if (st.t >= RACE.END) st.t = 0; st.play = !st.play || st.t === 0; pp.textContent = st.play ? "❚❚" : "▶"; };
  sc.oninput = () => { st.t = +sc.value; onScrub && onScrub(); };
  document.querySelectorAll("[data-s]").forEach(b => b.onclick = () => {
    st.speed = +b.dataset.s; document.querySelectorAll("[data-s]").forEach(x => x.classList.toggle("sel", x === b));
  });
  st.tick = dt => { dt = Math.max(0, dt); if (st.play) { st.t += dt * st.speed; if (st.t > RACE.END) { st.t = RACE.END; st.play = false; pp.textContent = "↺"; } } sc.value = st.t; };
  return st;
};
