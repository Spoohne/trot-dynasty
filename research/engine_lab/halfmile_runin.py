"""Review 12: half-mile run-in sensitivity (200 / 300 / 400 ft from the start to the first turn, straights 800 ft, arcs
520 ft). Engine only: every horse keeps one preassigned aim (events still fire), 20 fields x 8 post rotations, breaks
off, DT 1/16. Wins by post against Patrick's target 18.6 / 14.9 / 12.8 / 12.0 / 10.0 / 7.6 / 7.1 / 5.9."""
import collections, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import value_fit as V
R = V.R
V.setup(0)
R.P["break_k"] = 0.0
TARGET = [18.6, 14.9, 12.8, 12.0, 10.0, 7.6, 7.1, 5.9]
FIXED = ["top", "pocket", "first_over", "follow", "close", "pocket", "follow", "close"]
rng = random.Random(21)
fields = [[R.avg(**{t: rng.gauss(0, .4) for t in V.D.TR}) for _ in range(8)] for _ in range(20)]
for run_in in map(float, sys.argv[1:]):
    R.P.update(R.half_layout(run_in))
    wins, lead_half = collections.Counter(), collections.Counter()
    for stats in fields:
        for rot in range(8):
            f = sorted((R.Runner(f"H{k}", dict(stats[k]), "mid", (k + rot) % 8 + 1, {"aim": FIXED[k]}) for k in range(8)), key=lambda h: h.post)
            o, rec = R.run(f, "half", rng=random.Random(0), dt=1 / 16)
            wins[o[0].post] += 1
            lead_half[next(h.post for h in f if h.name == next(c for c in rec["calls"] if c["at"] == 0.5)["horses"][0]["name"])] += 1
    w = [round(100 * wins[p] / 160, 1) for p in range(1, 9)]
    print(f"run-in {run_in:.0f} ft: wins {w}  miss vs target {sum(abs(a - b) for a, b in zip(w, TARGET)) / 8:.1f} pts/post;"
          f" leads at the half from posts 1-2 {100 * (lead_half[1] + lead_half[2]) / 160:.0f}%, 7-8 {100 * (lead_half[7] + lead_half[8]) / 160:.0f}%")
