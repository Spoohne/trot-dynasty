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
  RACE.H = horses.map(h => Object.assign([h.name, "#5a3420", h.behind, h.lane], { stamina: h.stamina || 0, early: h.early || 0, coat: h.coat || pick(h.name), odds: h.odds || "", owner: h.owner || "", stable: h.stable || "", player: !!h.player, silks: h.silks || null, wraps: h.wraps || "", mask: h.mask || "", driver: h.driver || "", emblem: h.emblem || "", marquee: h.marquee || "" }));
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
  const dt = 1 / RACE.HZ, n = Math.ceil(RACE.END * RACE.HZ) + 2, H = RACE.H;
  const rank = H.map((h, i) => i).sort((a, b) => H[a][2][6] - H[b][2][6]).reduce((m, i, place) => (m[i] = place, m), []);
  const run = H.map((h, i) => { const [d, o] = RACE.story(h, 0), [d1] = RACE.story(h, dt); return { i, h, rank: rank[i], d, o, v: (d1 - d) / dt, ov: 0, out: 0, side: 0, nudge: 0, drive: 0, path: new Float32Array(n * 2) }; });
  // From the top of the stretch the result decides right of way: a horse doesn't wait on, or steer
  // round, one that it beats; that one gets out of its road instead. Before then, whoever is there first.
  let late = false;
  const yields = (r, p) => !late || p.rank < r.rank;
  const minO = r => r.i === RACE.DIVER ? 4 - Math.min(6, RACE.inset(RACE.SF + r.d)) : 4;   // the inside limit: the rail, or the passing lane for the pocket horse
  const ahead = (r, o) => run.filter(p => p !== r && p.d > r.d && Math.abs(p.o - o) < RACE.WIDE && yields(r, p));
  // moving to o would squeeze a horse alongside: closer than a sulky's width, and closer than it already is
  const crowds = (r, o) => run.some(p => p !== r && Math.abs(p.d - r.d) < RACE.BODY && Math.abs(p.o - o) < Math.min(RACE.WIDE, Math.abs(p.o - r.o)));   // nobody squeezes sideways into anybody
  for (const r of [...run].sort((p, q) => q.d - p.d))                   // the gate's second tier starts a legal body back
    for (const p of ahead(r, r.o)) r.d = Math.min(r.d, p.d - RACE.BODY);
  // How much more the oval turns between distance d and the top of the stretch, in radians: every foot a
  // horse is out from the rail costs it that many extra feet of running before the stretch.
  const turnLeft = d => { const end = RACE.D(RACE.CT[5]); let a = 0, h0 = null;
    for (let x = d; x < end; x += 20) { const p = RACE.pt(RACE.SF + x, 0), q = RACE.pt(RACE.SF + x + 4, 0), h = Math.atan2(q[1] - p[1], q[0] - p[0]);
      if (h0 !== null) { let dh = h - h0; dh = Math.atan2(Math.sin(dh), Math.cos(dh)); a += Math.abs(dh); } h0 = h; }
    return a; };
  for (let k = 0; k < n; k++) {
    const t = k * dt; late = t > RACE.CT[5] - 6;
    for (const r of run) { r.path[k * 2] = r.d; r.path[k * 2 + 1] = r.o; }
    for (const r of [...run].sort((p, q) => q.d - p.d)) {                // leaders first: those behind react to where they've gone
      if (r.i === RACE.HERO) { const [d, o] = RACE.story(r.h, t + dt); r.v = (d - r.d) / dt; r.d = d; r.o = o;   // the story's hero: no traffic touches it,
        for (const p of run) if (p !== r && p.d > r.d - RACE.BODY && p.d - r.d < RACE.BODY * 4 && Math.abs(p.o - r.o) < RACE.WIDE + 1) p.room = p.o >= r.o ? 1 : -1;   // and the field parts for it
        continue; }
      const [sd, so] = RACE.story(r.h, t), [sd1] = RACE.story(r.h, t + dt), vs = (sd1 - sd) / dt;
      // keep pace with the story, close any gap gently; a horse boxing in a closer moves on or drops back to let it out
      const vWant = vs + (sd - r.d) * (t > RACE.FIN - 10 ? 4 : 1.5) + r.nudge * 5;   // keep station tighter in the run to the wire
      r.nudge *= Math.exp(-dt / .8);
      // Seeking the rail. A horse the plan wants further in, held out only because it isn't clear of the horse
      // inside, weighs it up: the ground lost staying out through the turns still to come, against the ground
      // it must gain to clear by a body, which costs a horse with less stamina more. If clearing is cheaper it
      // pushes on (r.drive) until it can cross, then tucks in.
      if (!late && r.o - so > 2.5 && k % 10 === 0) {
        const inside = run.filter(p => p !== r && p.o < r.o - 1 && p.o > so - 3 && Math.abs(p.d - r.d) < RACE.BODY * 1.5);
        const need = inside.length ? Math.max(0, ...inside.map(p => RACE.BODY + 1.5 - (r.d - p.d))) : 0;
        const stay = (r.o - so) * turnLeft(r.d), effort = 1.6 - .35 * Math.max(-2, Math.min(2, r.h.stamina || 0));
        r.drive = need > 0 && need < 40 && stay > need * effort && (r.driveT || 0) < 4 ? 1 : 0;   // a push that hasn't cleared in 4 s is given up
      } else if (late || r.o - so <= 2.5) r.drive = 0;
      // before the half, one the plan wants in on the rail but who can't cross because a horse is alongside
      // inside it eases back and drops in behind (unless it has decided to push on clear)
      r.driveT = r.drive ? (r.driveT || 0) + dt : r.driveT;
      if (t < RACE.CT[3] && r.o - so > 2.5) for (const p of run)            // wanting in: the rail horse just behind gives it room to drop in
        if (p !== r && p.o < r.o - 1 && r.d > p.d && r.d - p.d < RACE.BODY + 2) p.nudge = -1;
      const tuck = t < RACE.CT[3] && !r.drive && r.o - so > 2.5 && run.some(p => p !== r && p.o < r.o - 1 && Math.abs(p.d - r.d) < RACE.BODY + 1) ? 3 : 0;
      let vNew = r.v + Math.max(-9 * dt, Math.min(6 * dt, vWant + r.drive * 3.5 - tuck - r.v));    // ~6 ft/s/s to quicken, ~9 to check
      let held = false;
      for (const p of ahead(r, r.o)) {                                     // a horse ahead in the way: ease off so the gap never closes
        const room = p.d - r.d - RACE.BODY, cap = room < 0 && !late ? p.v + room * 1.5 : p.v + Math.sqrt(2 * 9 * Math.max(0, room));   // inside a body: ease back to one (before the stretch)
        if (vNew > cap) { vNew = Math.max(cap, r.v - 14 * dt); held = true; }
      }
      // a horse that beats it closing from behind in its path: quicken to stay clear while it steps aside
      // in the stretch: a horse that beats it, coming up behind or alongside in its path; it steps out of the way (below)
      const chaser = late && run.find(p => p.rank < r.rank && r.d - p.d > -RACE.BODY && r.d - p.d < RACE.BODY * 4 && Math.abs(p.o - r.o) < RACE.WIDE + 1.5 && p.v > r.v - 1);
      // and one it beats, in front in its path: it steers round early rather than running up its back
      const blocker = late && run.filter(p => p.rank > r.rank && p.d > r.d && p.d - r.d < RACE.BODY * 3 && Math.abs(p.o - r.o) < RACE.WIDE + .5).sort((a, b) => a.d - b.d)[0];
      if (blocker && Math.abs(blocker.o - r.o) < RACE.WIDE) {              // not round it yet: never through it, check behind it meanwhile
        const cap = blocker.v + Math.sqrt(2 * 9 * Math.max(0, blocker.d - r.d - RACE.BODY));
        if (vNew > cap) vNew = Math.max(cap, r.v - 14 * dt);
      }
      // catching up late, a horse never runs past its own story spot: overshooting it is how a beaten horse (Harbor Oak,
      // 2626-stake-S6637) hit the wire a length and a half before the winner
      if (late && r.d + vNew * dt > sd1) vNew = Math.max((sd1 - r.d) / dt, r.v - 9 * dt);   // ease back onto it, at the usual braking
      r.v = vNew;
      // held up but the story wants it further on: pull out a lane and go round, the way a closer swings wide
      const slowAhead = ahead(r, r.o).some(p => p.d - r.d < RACE.BODY * 3 && p.v < vs - .5);   // the one in front is coming back to it
      const early = t < RACE.CT[3];                                         // to the half they string out single file: wait in line, don't swing out
      if ((held || slowAhead) && sd - r.d > 1 && !early) {                 // go round: outside if there's room, else up the inside
        if (!r.side) r.side = !crowds(r, r.o + 1) ? 1 : r.o > 6 && !crowds(r, r.o - 1) ? -1 : 0;
        if (r.side) r.out = Math.min(late ? 1.5 : 1, r.out + dt * 1.2);   // one lane round, a little more in the stretch
      } else if (sd - r.d < 1 || early) { r.out = Math.max(0, r.out - dt * (early ? 1 : .3)); if (!r.out) r.side = 0; }
      let ovWant = Math.max(-4, Math.min(4, (so + r.out * 6 * (r.side || 1) - r.o) * 1.2));   // up to 4 ft/s sideways
      if (chaser) { const away = r.o >= chaser.o || chaser.o - RACE.WIDE - 1 < 4 ? 1 : -1; ovWant = Math.max(-6, Math.min(6, (chaser.o + away * (RACE.WIDE + 1) - r.o) * 2)); }   // step aside: outward, or in if there's rail room
      if (blocker) { r.passSide = r.passSide || (minO(r) < 4 ? -1 : r.o >= blocker.o || blocker.o - RACE.WIDE - 1 < 4 ? 1 : -1); ovWant = Math.max(-6, Math.min(6, (blocker.o + r.passSide * (RACE.WIDE + 1) - r.o) * 2)); }
      else if (!late) r.passSide = 0;
      if (blocker) for (const p of run)                                     // whoever it beats alongside on that side moves over to open the gap
        if (p !== r && p !== blocker && p.rank > r.rank && Math.abs(p.d - r.d) < RACE.BODY * 1.5 && Math.sign(p.o - r.o) === r.passSide && Math.abs(p.o - r.o) < RACE.WIDE * 2) p.room = r.passSide;
      if (r.room) { ovWant = r.room * 5; r.room = 0; }
      // last resort in the stretch: two horses nose-to-tail inside a body of each other split apart sideways,
      // the better one taking the outside (or the rail if it's already inside), and they fan out from there
      let split = 0;
      if (late) for (const p of run) {
        if (p === r || p.rank > r.rank || Math.abs(p.d - r.d) >= RACE.BODY || Math.abs(p.o - r.o) >= RACE.WIDE) continue;   // a horse that finishes ahead holds its line
        r.nudge = -1;                                                       // the one it beats checks a little while it gives way
        const dirn = Math.abs(r.o - p.o) > .3 ? Math.sign(r.o - p.o) : (r.rank < p.rank ? 1 : -1);
        const pinned = (r.o <= minO(r) + .2 && dirn < 0) || (r.o >= 4 + 6 * 4 && dirn > 0);   // on the rail, or five wide: no room that way
        if (pinned) { split = 0; r.nudge = -2; } else split = dirn;            // pinned: drop back behind it instead
      }
      if (split) ovWant = split * 6;
      if (held && sd - r.d > 3) for (const p of run)                      // boxed: the horses penning it in give way
        if (p !== r && Math.abs(p.d - r.d) < RACE.BODY + 2 && Math.abs(p.o - r.o) < RACE.WIDE + 1.5) p.nudge = p.d > r.d + 4 ? 1 : -1;   // clearly ahead: move on; level or behind: drop back
      // Lines, not wobbles: in the stretch a horse holds the line it has picked; it only changes
      // sideways direction after holding a new wish for a moment, and small corrections are ignored.
      if (late) {
        if (Math.abs(ovWant) < .6) ovWant = 0;
        // never tuck into the wake of a horse that beats it: it would only be held up behind it and swing out again
        if (ovWant < 0 && !split && run.some(p => p.rank < r.rank && p.d > r.d && p.d - r.d < RACE.BODY * 3 && Math.abs(p.o - (r.o - RACE.WIDE)) < RACE.WIDE)) ovWant = 0;
        if (r.o >= 4 + 6 * 4 && ovWant > 0) ovWant = 0;                       // five wide at the most
        const dir = Math.sign(ovWant);
        if (dir && r.ldir && dir !== r.ldir && !split) { r.flipT = (r.flipT || 0) + dt; if (r.flipT < 2) ovWant = 0; else { r.ldir = dir; r.flipT = 0; } }
        else { r.flipT = 0; if (dir) r.ldir = dir; }
      }
      r.ov += Math.max(-8 * dt, Math.min(8 * dt, ovWant - r.ov));
      const oNext = Math.max(minO(r), r.o + r.ov * dt);                   // only the pocket horse may use the passing lane
      if (crowds(r, oNext) && !split) r.ov = 0; else r.o = oNext;        // someone alongside on that side: wait (unless splitting from an overlap)
      r.d += r.v * dt;
    }
  }
  RACE.paths = run.map(r => r.path); RACE.pathN = n;
};
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
    // Still the wrong winner after every try (Northern Star, 2627-ls-mile-Open-0: shut in on the rail from the quarter by a
    // horse level outside him that wanted in): the winner runs exactly as the story has it, and the field parts for it.
    // Only a race that came out wrong is run again, so every other replay stays as it was.
    const kf = Math.floor(RACE.FIN * RACE.HZ), first = RACE.paths.map((p, i) => i).sort((a, b) => RACE.paths[b][kf * 2] - RACE.paths[a][kf * 2])[0];
    if (first !== want[0] && RACE.HERO < 0) {
      RACE.HERO = want[0];
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
