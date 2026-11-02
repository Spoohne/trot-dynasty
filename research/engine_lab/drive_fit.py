"""What each aim is worth, learned from the engine itself (the driver's racing knowledge). Round 0: every horse is given a
random aim. Round 1 and on: the driver picks with the previous round's model (fitted on every driver round so far), but a random 30% of horses are given a
random aim, and only those are fitted (so the fit isn't biased by the driver's own choices). Per aim, least squares of
lengths behind the winner on aim_features.
    python research/engine_lab/drive_fit.py collect <round> <seed> <races>
    python research/engine_lab/drive_fit.py fit <round>
Settings: long stretch five wide, tank 45, breaks at a plausible rate, route on, DT 1/8, mile track."""
import json, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race2 as R
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drive2")   # v2: crowding features (v1 rows in drive/)
os.makedirs(HERE, exist_ok=True)
TR = ("early_speed", "late_speed", "stamina", "gait")


def setup():
    R.P.update(driver=1, break_k=0.0002, tank_full=45, mile_turns=[(0.125, 0.375), (0.625, 0.875)], stretch_at=0.875,
               stretch_lanes=5, route=1, open_early=0.0)
    R.P.update(**{k: float(v) for k, v in (a.split("=") for a in os.environ.get("PSET", "").split(",") if a)})


def load(rnd):
    m = json.load(open(os.path.join(HERE, f"model_{rnd}.json")))
    R.AIM_MODEL.clear()
    R.AIM_MODEL.update({("mile", a): c for a, c in m.items()})


def lengths_back(o):
    w = o[0].time
    return [(h.time - w) * R.FT_MILE / w / R.LEN for h in o]


if __name__ == "__main__":
    setup()
    if sys.argv[1] == "collect":
        rnd, seed, n = map(int, sys.argv[2:5])
        if rnd > 0:
            load(rnd - 1)
        rng = random.Random(seed)
        rows = []
        for i in range(n):
            f = []
            for k in range(8):
                ins = {"aim": rng.choice(R.AIMS)} if rnd == 0 or rng.random() < 0.3 else {}
                f.append(R.Runner(f"H{k}", R.avg(**{t: rng.gauss(0, .4) for t in TR}), "mid", k + 1, ins))
            feats = {h.name: R.aim_features(h, f) for h in f}
            o, rec = R.run(f, rng=random.Random(seed * 100000 + i), dt=0.125)
            for h, lb in zip(o, lengths_back(o)):
                if "aim" in h.instr:
                    others = [(x, x.aim0) for x in f if x is not h]
                    rows.append((h.instr["aim"], feats[h.name] + R.crowd(h, h.instr["aim"], others), lb))
        json.dump(rows, open(os.path.join(HERE, f"rows_{rnd}_{seed}.json"), "w"))
        print(len(rows), "rows")
    else:
        import glob
        import numpy as np
        rnd = int(sys.argv[2])
        rnds = [0] if rnd == 0 else range(1, rnd + 1)    # pooled over the driver rounds: damps the back-and-forth between rounds
        rows = [r for k in rnds for f in glob.glob(os.path.join(HERE, f"rows_{k}_*.json")) for r in json.load(open(f))]
        model, report = {}, {}
        for a in R.AIMS:
            X = np.array([r[1] for r in rows if r[0] == a]); y = np.array([r[2] for r in rows if r[0] == a])
            c, *_ = np.linalg.lstsq(X, y, rcond=None)
            model[a] = [round(float(v), 4) for v in c]
            report[a] = dict(n=len(y), mean_lengths_back=round(float(y.mean()), 2),
                             r2=round(1 - float(((X @ c - y) ** 2).sum()) / float(((y - y.mean()) ** 2).sum()), 3))
        json.dump(model, open(os.path.join(HERE, f"model_{rnd}.json"), "w"), indent=1)
        names = ["const", "early", "late", "stamina", "gait", "post-1", "top_rival_gap", "quicker_inside", "field_mean_gap", "n",
                 "same_aim", "same_aim_quicker", "same_aim_inside"]
        for a in R.AIMS:
            print(a, report[a], {k: v for k, v in zip(names, model[a]) if k != "n"})
