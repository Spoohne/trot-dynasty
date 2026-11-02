"""Reserve spent before the drive, split into parts, by rank at the drive: acceleration, air when uncovered (above
what a covered horse pays), and everything else. Rebuilt from the frames with race3's own formulas."""
import os, sys, random, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import race3 as R, drive3 as DR, v3_part1 as P1
track, N = sys.argv[1], int(sys.argv[2])
acc = collections.defaultdict(list); air = collections.defaultdict(list); unc = collections.defaultdict(list)
for i in range(N):
    rng = random.Random(77 * 100003 + i)
    n = P1.size(rng, track)
    f = P1.field([{t: rng.gauss(0, .4) for t in P1.TR} for _ in range(n)], track)
    o, rec = R.run(f, track, DR.Driver(), seed=77000 + i, dt=P1.DT)
    fr = rec["frames"]
    k = next(j for j, F in enumerate(fr) if max(x[0] for x in F) >= R.FT_MILE - 1400)
    rank = {j: r for r, j in enumerate(sorted(range(n), key=lambda j: -fr[k][j][0]))}
    for j in range(n):
        a_e = air_e = t_unc = 0.0
        for q in range(1, k):
            s, y, v = fr[q][j][:3]
            a = (v - fr[q - 1][j][2]) / P1.DT
            a_e += R.P["pace_k"] * R.C_ACC * max(0, a) * v * P1.DT
            cov = any(m != j and 0 < fr[q][m][0] - R.BODY_L - s < 1.5 * R.LENGTH and abs(fr[q][m][1] - y) < R.BODY_W - 1 for m in range(n))
            if not cov:
                air_e += R.P["pace_k"] * R.C_ACC * 0 + R.P["pace_k"] * R.C_AIR * v ** 3 * (1 - R.DRAFT) * P1.DT
                t_unc += P1.DT
        acc[rank[j]].append(a_e); air[rank[j]].append(air_e); unc[rank[j]].append(t_unc)
print(f"{track}: reserve-units spent before the drive on acceleration, and extra air when uncovered (s uncovered)")
for r in range(10):
    if acc[r]:
        print(f" {r+1:2d}  accel {st.mean(acc[r]):5.1f}   uncovered air {st.mean(air[r]):5.1f}  ({st.mean(unc[r]):4.1f}s)")
