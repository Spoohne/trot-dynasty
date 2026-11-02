"""Break rates by manners (Patrick, 2026-11-01: breaks pretty darn rare unless a horse is very low in manners).
One subject per race at a set manners level, the rest of the field random; normal driving, DT 1/16, breaks on.
    python research/engine_lab/v3_breaks.py <manners> <races> <seed> [b0]   prints breaks per start for the subject"""
import json, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race3 as R, drive3 as DR
m, n, seed = float(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
if len(sys.argv) > 4:
    R.P["break_b0"] = float(sys.argv[4])
rng = random.Random(seed)
starts = breaks = field_starts = field_breaks = 0
for i in range(n):
    tr = ("half", "mile")[i % 2]
    stats = [{t: rng.gauss(0, .4) for t in ("gate", "cruise", "kick", "manners", "grit")} for _ in range(8)]
    k = rng.randrange(8); stats[k]["manners"] = m
    f = [R.Horse(f"H{j+1}", stats[j], j + 1, R.TRACKS[tr]) for j in range(8)]
    o, rec = R.run(f, tr, DR.Driver(), seed=seed * 100000 + i, dt=1 / 16, record=False)
    broke = {e[1] for e in rec["events"] if e[2] == "broke stride"}
    starts += 1; breaks += f"H{k+1}" in broke
    field_starts += 7; field_breaks += len(broke - {f"H{k+1}"})
print(json.dumps(dict(manners=m, starts=starts, breaks=breaks, field_starts=field_starts, field_breaks=field_breaks)))
