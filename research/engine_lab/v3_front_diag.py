"""Why front-runners dominate (Part 1 read 166): at the drive point, where is everyone, how much reserve do they
carry, and what does the last 1400 ft do with it.
    python research/engine_lab/v3_front_diag.py <track> <races>"""
import os, sys, random, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import race3 as R, drive3 as DR, v3_part1 as P1
track, N = sys.argv[1], int(sys.argv[2])
rows = []
for i in range(N):
    rng = random.Random(77 * 100003 + i)
    n = P1.size(rng, track)
    f = P1.field([{t: rng.gauss(0, .4) for t in P1.TR} for _ in range(n)], track)
    o, rec = R.run(f, track, DR.Driver(), seed=77000 + i, dt=P1.DT)
    fr = rec["frames"]
    k = next(j for j, F in enumerate(fr) if max(x[0] for x in F) >= R.FT_MILE - 1400)
    F = fr[k]
    rank = sorted(range(n), key=lambda j: -F[j][0])
    lead_s = F[rank[0]][0]
    place = {h.name: p for p, h in enumerate(o)}
    for r, j in enumerate(rank):
        rows.append(dict(r=r, back=(lead_s - F[j][0]) / R.LENGTH, E=F[j][3], lane=(F[j][1] - R.RAIL_Y) / R.LANE,
                         fin=place[f[j].name], v=F[j][2], n=n))
    rows[-n]["spread"] = (lead_s - F[rank[-1]][0]) / R.LENGTH
print(f"{track}: {N} races")
print(" rank  lengths back   E      lane   speed  finish  wins")
for r in range(10):
    g = [x for x in rows if x["r"] == r]
    if g:
        print(f"  {r+1:2d}   {st.mean(x['back'] for x in g):6.1f}     {st.mean(x['E'] for x in g):5.1f}  {st.mean(x['lane'] for x in g):5.2f}  {st.mean(x['v'] for x in g):5.1f}"
              f"   {st.mean(x['fin'] for x in g)+1:4.1f}   {100*sum(x['fin']==0 for x in g)/len(g):4.0f}%")
print(" field spread at the drive, lengths:", round(st.median(x["spread"] for x in rows if "spread" in x), 1))
