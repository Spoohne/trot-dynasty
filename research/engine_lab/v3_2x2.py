"""Review 18's paired 2x2 (DRIVER_V4_PLAN section 7): start challenged x earlier middle, same fields, posts and seeds.
Start challenge: the quickest non-rail horse (by gate) is held to the lead aim. Middle challenge: first-over from
`move_fo` 0.375 with `advance` 4 ft/s. Each treatment's execution is checked before its outcome is read.
    python v3_2x2.py <track> <races> [seed]        (PyPy recommended)"""
import os, sys, random, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import race3 as R, drive3 as DR, v3_part1 as P1
track, N = sys.argv[1], int(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 83
MIDDLE = dict(move_fo=0.375, advance=4.0)


def spearman(a, b):
    n = len(a)
    return 1 - 6 * sum((x - y) ** 2 for x, y in zip(a, b)) / (n * (n * n - 1))


def at(fr, s_cut):
    return next(j for j, F in enumerate(fr) if max(x[0] for x in F) >= s_cut)


def one(stats, n, i, start, middle):
    f = P1.field(stats, track)
    names = [h.name for h in f]
    forced = max(f[1:], key=lambda h: h.t["gate"]).name if start else None
    d = DR.Driver(gate_aims={forced: "top"} if forced else None, **(MIDDLE if middle else {}))
    o, rec = R.run(f, track, d, seed=seed * 1000 + i, dt=P1.DT)
    fr = rec["frames"]
    out = {}
    order = lambda k: sorted(range(n), key=lambda j: -fr[k][j][0])
    k1, k2, k3 = at(fr, 1320), at(fr, 2640), at(fr, 3960)
    if forced:                                           # did the start treatment happen: on the lead at the 1/4, or took back?
        j = names.index(forced)
        out["forced_lead_q1"] = order(k1)[0] == j
        out["forced_took_back"] = any(e[1] == forced and "took back" in e[2] for e in rec["events"] if e[0] < k1 * P1.DT)
    mv = next((e for e in rec["events"] if e[2] == "pulled first-over"), None)
    out["moved"] = mv is not None
    if mv:                                               # did the middle treatment happen: out, gaining, with cover behind?
        j = names.index(mv[1]); q0 = int(mv[0] / P1.DT)
        q_exit = next((q for q in range(q0, min(len(fr), q0 + 64)) if fr[q][j][1] > R.RAIL_Y + R.LANE - 1), None)
        out["exited"] = q_exit is not None
        lead = lambda q: max(x[0] for x in fr[q])
        out["gained"] = ((lead(q0) - fr[q0][j][0]) - (lead(k3) - fr[k3][j][0])) / R.LENGTH if q0 < k3 else 0.0
        out["cover"] = sum(1 for e in rec["events"] if e[2] == f"followed {mv[1]}'s cover")
    posts = list(range(n))
    out["rail_lead_half"] = order(k2)[0] == 0
    out["rho_half"] = spearman(posts, [order(k2).index(j) for j in range(n)])
    out["rho_q3_fin"] = spearman([order(k3).index(j) for j in range(n)], [[h.name for h in o].index(names[j]) for j in range(n)])
    out["rho_fin"] = spearman(posts, [[h.name for h in o].index(names[j]) for j in range(n)])
    out["win_post"] = o[0].post
    w = names.index(o[0].name)
    out["win_back_q3"] = order(k3).index(w) >= 4                 # the winner was 5th or worse at the 3/4
    return out


cells = {(s, m): [] for s in (0, 1) for m in (0, 1)}
for i in range(N):
    rng = random.Random(seed * 100003 + i)
    n = 8 if track == "half" else 10
    stats = [{t: rng.gauss(0, .4) for t in P1.TR} for _ in range(n)]
    for c in cells:
        cells[c].append(one(stats, n, i, *c))
mean = lambda rows, k: st.mean(r[k] for r in rows if k in r) if any(k in r for r in rows) else float("nan")
print(f"{track}, {N} paired races per cell")
print("  cell             | start executed (lead at 1/4 / took back) | first-over: moved exited gained cover | rail leads 1/2 | order~post 1/2 | 3/4->fin | order~post fin | posts 1-2 win | winner 5th+ at 3/4")
for (s, m), rows in cells.items():
    name = f"{'start' if s else '-----'} {'middle' if m else '------'}"
    ex = f"{mean(rows, 'forced_lead_q1'):.0%} / {mean(rows, 'forced_took_back'):.0%}" if s else "      n/a     "
    print(f"  {name:16s} | {ex:^40s} | {mean(rows, 'moved'):5.0%} {mean(rows, 'exited'):5.0%} {mean(rows, 'gained'):5.1f}L {mean(rows, 'cover'):4.1f} |"
          f" {mean(rows, 'rail_lead_half'):^14.0%} | {mean(rows, 'rho_half'):^14.2f} | {mean(rows, 'rho_q3_fin'):^8.2f} | {mean(rows, 'rho_fin'):^14.2f} |"
          f" {sum(r['win_post'] <= 2 for r in rows) / len(rows):^13.0%} | {mean(rows, 'win_back_q3'):.0%}")
