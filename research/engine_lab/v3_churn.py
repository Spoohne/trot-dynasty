"""Position churn (DECISIONS 194): how far the running order departs from post order, and how much it moves.
Checked against the free chart summaries (chart_targets.md): rail horse on the lead at the half (about 25%, half-mile),
rail horse in the top three at the half (79% half-mile, 37% bigger track), outer two posts on the lead at the half
(under 5% half-mile).
    python v3_churn.py <track> <races> [seed]        (PyPy recommended; Part 1 field mix, P1_SET overrides apply)"""
import os, sys, random, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import race3 as R, drive3 as DR, v3_part1 as P1
track, N = sys.argv[1], int(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 71


def spearman(a, b):
    n = len(a)
    return 1 - 6 * sum((x - y) ** 2 for x, y in zip(a, b)) / (n * (n * n - 1)) if n > 2 else 1.0


CALLS = (1320, 2640, 3960)
rho = {c: [] for c in CALLS + ("fin",)}; step_rho = {c: [] for c in CALLS[1:] + ("fin",)}
rail_lead = rail_top3 = out_lead = win_close = 0
for i in range(N):
    rng = random.Random(seed * 100003 + i)
    n = P1.size(rng, track)
    f = P1.field([{t: rng.gauss(0, .4) for t in P1.TR} for _ in range(n)], track)
    o, rec = R.run(f, track, DR.Driver(), seed=seed * 1000 + i, dt=P1.DT)
    fr = rec["frames"]
    place = {}
    for c in CALLS:
        k = next(j for j, F in enumerate(fr) if max(x[0] for x in F) >= c)
        order = sorted(range(n), key=lambda j: -fr[k][j][0])
        place[c] = {j: p for p, j in enumerate(order)}
        if c == 2640:
            rail_lead += order[0] == 0; rail_top3 += 0 in order[:3]; out_lead += f[order[0]].post >= n - 1
            win_close += (fr[k][order[0]][0] - fr[k][[h.name for h in f].index(o[0].name)][0]) / R.LENGTH <= 3
    place["fin"] = {[h.name for h in f].index(h.name): p for p, h in enumerate(o)}
    posts = [h.post - 1 for h in f]
    for c in rho:
        rho[c].append(spearman(posts, [place[c][j] for j in range(n)]))
    prev = CALLS[0]
    for c in CALLS[1:] + ("fin",):
        step_rho[c].append(spearman([place[prev][j] for j in range(n)], [place[c][j] for j in range(n)])); prev = c
print(f"{track} {N} races | order vs post (1 = post order): 1/4 {st.mean(rho[1320]):.2f}  1/2 {st.mean(rho[2640]):.2f}"
      f"  3/4 {st.mean(rho[3960]):.2f}  finish {st.mean(rho['fin']):.2f}")
print(f"   call to call (1 = no change): 1/4->1/2 {st.mean(step_rho[2640]):.2f}  1/2->3/4 {st.mean(step_rho[3960]):.2f}  3/4->finish {st.mean(step_rho['fin']):.2f}")
print(f"   at the half: rail horse leads {100*rail_lead/N:.0f}% (ref ~25% half-mile), rail top 3 {100*rail_top3/N:.0f}% (ref 79% half / 37% bigger),"
      f" outer two posts lead {100*out_lead/N:.0f}% (ref <5% half), winner within 3 lengths of the lead {100*win_close/N:.0f}% (ref most)")
