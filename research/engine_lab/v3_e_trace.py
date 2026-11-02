"""Where the back of the field loses its reserve: E by rank-at-the-drive at each eighth, and accel/brake work."""
import os, sys, random, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import race3 as R, drive3 as DR, v3_part1 as P1
track, N = sys.argv[1], int(sys.argv[2])
E = collections.defaultdict(list); brake = collections.defaultdict(list); park = collections.defaultdict(list)
for i in range(N):
    rng = random.Random(77 * 100003 + i)
    n = P1.size(rng, track)
    f = P1.field([{t: rng.gauss(0, .4) for t in P1.TR} for _ in range(n)], track)
    o, rec = R.run(f, track, DR.Driver(), seed=77000 + i, dt=P1.DT)
    fr = rec["frames"]
    k = next(j for j, F in enumerate(fr) if max(x[0] for x in F) >= R.FT_MILE - 1400)
    rank = {j: r for r, j in enumerate(sorted(range(n), key=lambda j: -fr[k][j][0]))}
    for j in range(n):
        r = rank[j]
        for e8 in range(1, 7):
            kk = next(q for q, F in enumerate(fr) if F[j][0] >= e8 * 660)
            E[(r, e8)].append(fr[kk][j][3])
        dv = [fr[q + 1][j][2] - fr[q][j][2] for q in range(k)]
        brake[r].append(sum(-x for x in dv if x < 0))          # ft/s shed before the drive (speed thrown away)
        park[r].append(sum(P1.DT for q in range(k) if fr[q][j][1] > R.RAIL_Y + 2) )
print(f"{track}: E at each eighth by rank at the drive; ft/s braked away; s spent off the rail")
for r in range(10):
    if E[(r, 1)]:
        print(f" {r+1:2d} " + " ".join(f"{st.mean(E[(r, e)]):5.1f}" for e in range(1, 7)) + f"   brake {st.mean(brake[r]):5.1f}   wide {st.mean(park[r]):5.1f}s")
