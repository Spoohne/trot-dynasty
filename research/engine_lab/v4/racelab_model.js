// The outcome model v4 (research/engine_lab/v4_outcome.py), one field at a time. Kept line-for-line with the Python.
const SD = 0.4, DUEL = 0.15, P_NONE = 0.10, N_FOLLOW = 2, A_FO = 6.0, BREAK = 3.0;
const FO_MAX = { half: 4, mile: 5 };
const ROLES = ["lead", "pocket", "first-over", "followed cover", "in the line"];

function rng32(seed) {                       // mulberry32: a small seeded generator
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
function normal(r) { let u = 0; while (u === 0) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); }
function gumbel(r) { let u = 0; while (u === 0) u = r(); return -Math.log(-Math.log(u)); }

// field: [{traits: {gate, cruise, kick, manners, grit}}] in post order. Returns {P, role, rank, broke}.
// Trips are chosen, not assigned (DECISIONS 215): in the order they come out of the gate, each driver takes the best
// trip still open to its horse, with a little noise. Same rules as v4_outcome.race.
function raceOnce(field, track, p, r) {
  const n = field.length;
  const f = field.map(() => normal(r) * p.s_form);
  const z = field.map(() => normal(r)), u = field.map(() => normal(r));
  const none = r(), brk = field.map(() => r()), cg = field.map(() => [0, 1, 2, 3, 4].map(() => gumbel(r)));
  const gate = field.map((h, i) => h.traits.gate + f[i]), cruise = field.map((h, i) => h.traits.cruise + f[i]);
  const kick = field.map((h, i) => h.traits.kick + f[i]), grit = field.map(h => h.traits.grit), manners = field.map(h => h.traits.manners);
  const e = gate.map((g, i) => g - p.c_post * i + p.s_start * z[i]);
  const order = [...Array(n).keys()].sort((a, b) => e[b] - e[a]);
  const rank = Array(n); order.forEach((h, k) => rank[h] = k);
  const wk = 1 - p.omega, A = [p.A_lead, p.A_pocket, p.A_fo, p.A_fol, 0];
  const role = Array(n).fill(4), depth = Array(n).fill(0);
  let lead = -1, pocketTaken = false, mover = -1, followers = 0, lineCount = 0;
  const canMove = none >= P_NONE;
  for (let k = 0; k < n; k++) {
    const h = order[k], kh = kick[h], lg = lead >= 0 ? grit[lead] : 0;
    const v = [-Infinity, -Infinity, -Infinity, -Infinity, -Infinity];
    if (lead < 0) v[0] = A[0] + wk * kh;
    if (!pocketTaken) v[1] = A[1] + wk * kh;                 // the first out may tuck and let the next one lead
    const press = k === 1 && n > 1 && (e[order[0]] - e[order[1]]) < DUEL;
    const mid = k >= 2 && k <= FO_MAX[track] && canMove;
    if (mover < 0 && (press || mid)) v[2] = A[2] + wk * kh + p.g * (grit[h] - lg);
    if (mover >= 0 && followers < N_FOLLOW) v[3] = A[3] + (wk + p.k_close) * kh;
    v[4] = (wk + p.k_close) * kh - p.b_depth * lineCount;
    let pick = 0, best = -Infinity;
    for (let j = 0; j < 5; j++) { const x = v[j] + p.s_choice * cg[k][j]; if (x > best) { best = x; pick = j; } }
    role[h] = pick; depth[h] = pick === 4 ? lineCount : 0;
    if (pick === 0) lead = h; else if (pick === 1) pocketTaken = true; else if (pick === 2) mover = h; else if (pick === 3) followers++; else lineCount++;
  }
  if (lead < 0) { lead = order[0]; role[lead] = 0; depth[lead] = 0; }
  const gd = Array(n).fill(0);
  if (mover >= 0) { gd[mover] = grit[mover] - grit[lead]; gd[lead] = grit[lead] - grit[mover]; }
  const P = [], broke = [];
  for (let i = 0; i < n; i++) {
    broke[i] = brk[i] < 0.005 * Math.exp(-2.88 * manners[i]);
    const closing = role[i] === 3 || role[i] === 4;
    P[i] = p.omega * cruise[i] + (wk + p.k_close * (closing ? 1 : 0)) * kick[i] + A[role[i]] - p.b_depth * depth[i]
         + p.g * gd[i] + p.s_eps * u[i] - BREAK * (broke[i] ? 1 : 0);
  }
  return { P, role, rank, broke };
}

// Many runs of one field: per horse wins, places, average finish, trips, margins.
function runMany(field, track, p, runs, seed) {
  const r = rng32(seed), n = field.length;
  const st = field.map(() => ({ fin: Array(n).fill(0), sumPlace: 0, trips: [0, 0, 0, 0, 0], broke: 0, beaten: [] }));
  for (let k = 0; k < runs; k++) {
    const { P, role, broke } = raceOnce(field, track, p, r);
    const order = [...Array(n).keys()].sort((a, b) => P[b] - P[a]);
    order.forEach((h, place) => {
      const s = st[h]; s.fin[place]++; s.sumPlace += place + 1; s.trips[role[h]]++; if (broke[h]) s.broke++;
      if (place > 0) s.beaten.push((P[order[0]] - P[h]) * p.s_margin);
    });
  }
  return st;
}
if (typeof module !== "undefined") module.exports = { raceOnce, runMany, rng32, ROLES };
