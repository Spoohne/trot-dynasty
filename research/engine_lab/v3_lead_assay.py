"""Why is leading a bad spot? From saved quarter states (as in the slot assay), two identical horses: the leader and
the 4th horse on the rail. The continuation runs once per variant, one change at a time:
base; no draft for anyone; leader paces at what it can hold on the turn; first-over doesn't sit on the leader's flank;
no breather; a big breather. Reports what the lead is worth against 4th, and both horses' reserve at the drive.
    python research/engine_lab/v3_lead_assay.py <track>"""
import collections, copy, os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race3 as R, drive3 as DR
track = sys.argv[1]
R.P["break_b0"] = 0.0
TR = ("gate", "cruise", "kick", "manners", "grit")
T = R.TRACKS[track]
DT = 1 / 16
VARIANTS = {"base": {}, "no draft": {"DRAFT": 1.0}, "leader paces the turns": {"lead_held": 1},
            "first-over doesn't sit on the flank": {"press": 0}, "no breather": {"breather": 0.0}, "breather 3": {"breather": 3.0}}
if os.environ.get("VARIANTS"):
    import json
    VARIANTS = json.loads(os.environ["VARIANTS"])
rng = random.Random(41)
res = collections.defaultdict(list)
e_at = collections.defaultdict(list)
for fi in range(64):
    stats = [{t: rng.gauss(0, .4) for t in TR} for _ in range(8)]
    f = [R.Horse(f"H{j+1}", dict(stats[j]), j + 1, T) for j in range(8)]
    drv = DR.Driver()
    rec = {"track": track, "dt": DT, "names": [h.name for h in f], "frames": [], "events": []}
    rngs = {h.name: random.Random(f"1:{h.name}") for h in f}
    t = 0.0
    R._HELD.clear()
    while max(h.s for h in f) < 0.25 * R.FT_MILE:
        drv(f, T, t, rec); R.step(f, T, t, DT, lambda x: rngs[x.name], rec); t += DT
    rail = [h for h in sorted(f, key=lambda h: -h.s) if h.y < R.RAIL_Y + 1 and not h.man]
    if len(rail) < 4 or rail[0] is not max(f, key=lambda h: h.s):
        continue
    a, b = rail[0], rail[3]
    for name, var in VARIANTS.items():
        g, d2 = copy.deepcopy(f), copy.deepcopy(drv)
        A, B = next(h for h in g if h.name == a.name), next(h for h in g if h.name == b.name)
        mean_t = {k: (A.t[k] + B.t[k]) / 2 for k in A.t}
        for h in (A, B):
            h.t = dict(mean_t); h.p_sus = 1.0 + R.P["p_cruise"] * h.t["cruise"]; h.v_sus = R.sus_speed(h.p_sus)
        A.E = B.E = (A.E + B.E) / 2
        draft0 = R.DRAFT
        R.DRAFT = var.get("DRAFT", draft0)
        p0 = dict(R.P)
        R.P.update({k[2:]: v for k, v in var.items() if k.startswith("P_")})     # P_ = engine settings
        d2.d.update({k: v for k, v in var.items() if k != "DRAFT" and not k.startswith("P_")})
        R._HELD.clear()
        tt, rr, rg, seen = t, copy.deepcopy(rec), {k: copy.deepcopy(v) for k, v in rngs.items()}, {}
        while not all(h.done for h in g) and tt < 200:
            d2(g, T, tt, rr); R.step(g, T, tt, DT, lambda x: rg[x.name], rr); tt += DT
            for h in (A, B):
                if h.name not in seen and d2.state[h.name]["phase"] == "drive":
                    seen[h.name] = h.E
        R.DRAFT = draft0
        R.P.clear(); R.P.update(p0)
        fin = [h.name for h in sorted(g, key=lambda h: h.time or 1e9)]
        res[name].append(fin.index(b.name) - fin.index(a.name))
        e_at[name].append((seen.get(a.name, 0), seen.get(b.name, 0)))
print(track, f"({len(res['base'])} states)")
for name in VARIANTS:
    v = res[name]; e = e_at[name]
    print(f"   {name:36s} lead worth {st.mean(v):+.2f} (±{st.stdev(v) / len(v) ** 0.5:.2f}) | reserve at the drive: leader {st.mean(x for x, _ in e):.1f}, 4th {st.mean(y for _, y in e):.1f}")
