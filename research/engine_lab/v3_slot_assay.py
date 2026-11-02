"""Review 16 assay B: is a better spot worth anything at equal resources? Race 64 fields per track to the quarter,
save the state, pick two horses on the rail line (a forward spot and a rear spot), make them identical (the mean of
their traits, the mean of their reserve), and race on with the same drivers. The rear body's place minus the forward
body's place is what the spot is worth (positive = the forward spot is better). Breaks off, DT 1/16.
    python research/engine_lab/v3_slot_assay.py <track>"""
import collections, copy, os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race3 as R, drive3 as DR
track = sys.argv[1]
R.P["break_b0"] = 0.0
TR = ("gate", "cruise", "kick", "manners", "grit")
T = R.TRACKS[track]
DT = 1 / 16
rng = random.Random(41)
res = collections.defaultdict(list)


def go(f, drv, t, rec, rngs):
    while not all(h.done for h in f) and t < 200:
        drv(f, T, t, rec); R.step(f, T, t, DT, lambda x: rngs[x.name], rec); t += DT
    return [h.name for h in sorted(f, key=lambda h: h.time or 1e9)]


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
    order = sorted(f, key=lambda h: -h.s)
    rail = [h for h in order if h.y < R.RAIL_Y + 1 and not h.man]
    if len(rail) < 5:
        continue
    pairs = {"lead vs 4th on the rail": (rail[0], rail[3]), "pocket vs 4th on the rail": (rail[1], rail[3]),
             "2nd vs last on the rail": (rail[1], rail[-1]), "3rd vs 5th on the rail": (rail[2], rail[4])}
    for label, (a, b) in pairs.items():
        g, d2 = copy.deepcopy(f), copy.deepcopy(drv)
        A, B = next(h for h in g if h.name == a.name), next(h for h in g if h.name == b.name)
        mean_t = {k: (A.t[k] + B.t[k]) / 2 for k in A.t}
        for h in (A, B):                                  # two identical horses: same traits, same tank
            h.t = dict(mean_t)
            h.p_sus = 1.0 + R.P["p_cruise"] * h.t["cruise"]
            h.v_sus = R.sus_speed(h.p_sus)
        A.E = B.E = (A.E + B.E) / 2
        R._HELD.clear()
        fin = go(g, d2, t, copy.deepcopy(rec), {k: copy.deepcopy(v) for k, v in rngs.items()})
        res[label].append(fin.index(b.name) - fin.index(a.name))
print(track)
for label, v in res.items():
    print(f"   {label:28s} forward spot worth {st.mean(v):+.2f} places (±{st.stdev(v) / len(v) ** 0.5:.2f}), forward finished ahead {sum(x > 0 for x in v) / len(v):.0%}  n {len(v)}")
