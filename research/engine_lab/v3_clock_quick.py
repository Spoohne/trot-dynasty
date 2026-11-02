"""Median winning time on the Part 1 field mix, no recording: python v3_clock_quick.py '<json overrides>' [races]"""
import os, sys, json, random, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
os.environ["P1_SET"] = sys.argv[1]
import race3 as R, drive3 as DR, v3_part1 as P1
N = int(sys.argv[2]) if len(sys.argv) > 2 else 48
out = []
for track in ("half", "mile"):
    T = []
    for i in range(N):
        rng = random.Random(31 * 100003 + i)
        n = P1.size(rng, track)
        f = P1.field([{t: rng.gauss(0, .4) for t in P1.TR} for _ in range(n)], track)
        o, _ = R.run(f, track, DR.Driver(), seed=31000 + i, dt=P1.DT, record=False)
        T.append(o[0].time)
    out.append(f"{track} {st.median(T):.1f}")
print(sys.argv[1], " | ".join(out))
