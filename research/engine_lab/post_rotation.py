"""Review 11's post test: is the inside-post edge the engine or the driver? 20 fixed fields, each run in all 8 cyclic post
rotations (every horse from every post), breaks off, DT 1/16. Arm "fixed": each horse keeps one preassigned aim through
every rotation (event rules only). Arm "driver": the learned driver picks. Wins, first-call position and ground by post."""
import collections, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drive_fit as D
R = D.R
D.setup(); D.load(4)
R.P["break_k"] = 0.0
R.P.update(**{k: float(v) for k, v in (a.split("=") for a in os.environ.get("PSET", "").split(",") if a)})
rng = random.Random(21)
fields = [[R.avg(**{t: rng.gauss(0, .4) for t in D.TR}) for _ in range(8)] for _ in range(20)]
FIXED = ["top", "pocket", "first_over", "follow", "close", "pocket", "follow", "close"]
out = {}
for arm in ("fixed", "driver"):
    wins, q1, ground, aims = collections.Counter(), collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(collections.Counter)
    for stats in fields:
        for rot in range(8):
            f = []
            for k in range(8):
                post = (k + rot) % 8 + 1
                f.append(R.Runner(f"H{k}", dict(stats[k]), "mid", post, {"aim": FIXED[k]} if arm == "fixed" else {}))
            f.sort(key=lambda h: h.post)
            o, rec = R.run(f, rng=random.Random(0), dt=1 / 16)
            wins[o[0].post] += 1
            c1 = next(c for c in rec["calls"] if c["at"] == 0.25)["horses"]
            for i, x in enumerate(c1):
                q1[next(h.post for h in f if h.name == x["name"])].append(i + 1)
            for h in f:
                ground[h.post].append(h.ground); aims[h.post][h.aim0] += 1
    n = sum(wins.values())
    out[arm] = {p: dict(win=round(wins[p] / n * 100, 1), pos_at_quarter=round(sum(q1[p]) / len(q1[p]), 2),
                        extra_ground_ft=round(sum(ground[p]) / len(ground[p]), 1),
                        gate_aims={a: c for a, c in aims[p].most_common(3)}) for p in range(1, 9)}
    print("==", arm)
    for p, v in out[arm].items():
        print(p, v)
json.dump(out, open(os.path.join(D.HERE, "post_rotation.json"), "w"), indent=1)
