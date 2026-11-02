"""Stage 3: fit the clock (pace_k) and the cost of turning (c_turn) to the live game's median winning times
(mile 1:53.4, half-mile 1:55.9; chart_targets / live save). Random 8-horse fields, traits SD 0.4, the driver on.
    python research/engine_lab/v3_clock_fit.py <pace_k> <c_turn> <races>"""
import json, os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race3 as R, drive3 as DR
pk, ct, n = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
R.P.update(pace_k=pk, c_turn=ct)
TR = ("gate", "cruise", "kick", "manners", "grit")
out = {}
for tr in ("mile", "half"):
    rng = random.Random(5)
    w = []
    for i in range(n):
        f = [R.Horse(f"H{k+1}", {t: rng.gauss(0, .4) for t in TR}, k + 1, R.TRACKS[tr]) for k in range(8)]
        o, rec = R.run(f, tr, DR.Driver(), seed=i, record=False)
        w.append(o[0].time)
    out[tr] = round(st.median(w), 2)
lone = R.Horse("A", {}, 1, R.MILE).v_sus
print(json.dumps(dict(pace_k=pk, c_turn=ct, **out, miss=round(abs(out["mile"] - 113.4) + abs(out["half"] - 115.9), 2),
                      lone_mile=round(R.FT_MILE / lone, 1))))
