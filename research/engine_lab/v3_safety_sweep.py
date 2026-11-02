"""Part 0 sweep: random fields, the driver, DT 1/16, breaks at the default rate. Totals of every audit count.
    python research/engine_lab/v3_safety_sweep.py <track> <seed> <races>"""
import collections, json, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race3 as R, drive3 as DR
track, seed, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
rng = random.Random(seed)
tot = collections.Counter()
for i in range(n):
    f = [R.Horse(f"H{k+1}", {t: rng.gauss(0, .4) for t in ("gate", "cruise", "kick", "manners", "grit")}, k + 1, R.TRACKS[track]) for k in range(8)]
    o, rec = R.run(f, track, DR.Driver(), seed=seed * 1000 + i, dt=1 / 16)
    a = R.audit(rec)
    for k, v in a.items():
        if k not in ("min_gap_ft", "reversals_max", "commits", "overdraw"):
            tot[k] += v
    tot["worst_reversals"] = max(tot["worst_reversals"], a["reversals_max"])
    tot["breaks"] += sum(1 for e in rec["events"] if e[2] == "broke stride")
    tot["unfinished"] += o[-1].time is None
print(json.dumps(dict(tot)))
