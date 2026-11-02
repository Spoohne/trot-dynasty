"""The start by post: plan, place in the running order (by distance) after turn 1 and at the 3/4, lane after turn 1,
reserve after turn 1, wins. Part 1 field mix.  python v3_start_diag.py <track> <races> [seed]"""
import os, sys, random, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import race3 as R, drive3 as DR, v3_part1 as P1
track, N = sys.argv[1], int(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 61
T = R.TRACKS[track]
row = collections.defaultdict(lambda: collections.defaultdict(list)); plans = collections.defaultdict(collections.Counter)
for i in range(N):
    rng = random.Random(seed * 100003 + i)
    n = 8 if track == "half" else 10
    f = P1.field([{t: rng.gauss(0, .4) for t in P1.TR} for _ in range(n)], track)
    o, rec = R.run(f, track, DR.Driver(), seed=seed * 1000 + i, dt=P1.DT)
    fr = rec["frames"]
    for m, cut in (("t1", T.arcs[0][1] + 100), ("q3", 3960)):
        k = next(j for j, F in enumerate(fr) if max(x[0] for x in F) >= cut)
        order = sorted(range(n), key=lambda j: -fr[k][j][0])
        for p, j in enumerate(order):
            row[f[j].post][m].append(p + 1)
            if m == "t1":
                row[f[j].post]["lane"].append((fr[k][j][1] - R.RAIL_Y) / R.LANE); row[f[j].post]["E"].append(fr[k][j][3])
    for h in f:
        row[h.post]["win"].append(o[0] is h); plans[h.post][rec["plans"][h.name]] += 1
print(f"{track} {N} races: post | place after turn 1 | lane | reserve | place at 3/4 | wins | plans")
for p in sorted(row):
    r = row[p]
    print(f"  {p:2d}   {st.mean(r['t1']):4.1f}   {st.mean(r['lane']):4.2f}  {st.mean(r['E']):5.1f}   {st.mean(r['q3']):4.1f}   {100*st.mean(r['win']):4.0f}%   {dict(plans[p])}")
