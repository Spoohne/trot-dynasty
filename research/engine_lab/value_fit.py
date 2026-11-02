"""The driver's value model, learned from paired counterfactuals (review 11). Each sample: race a random field under the
current policy to a decision point (the gate, or a share of the mile), save the state, then continue it once per
feasible aim for one subject horse, everyone else on the same policy and the same random draws. The subject's finish
place in each arm is the target. Fitted per aim: ridge regression on quadratic terms of aim_state + crowd.
    python research/engine_lab/value_fit.py collect <round> <seed> <samples>
    python research/engine_lab/value_fit.py fit <round>          held-out regret by race, then saves value_<round>.json
    python research/engine_lab/value_fit.py aims <round>         review 11's test: which aim is best, and how often
Round 0 runs under the linear driver (drive2 model 4); round k under value_<k-1>. Mile and half-mile 50/50, tuck_back 4,
breaks at a plausible rate, DT 1/8."""
import copy, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drive_fit as D
R = D.R
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.environ.get("VDIR", "value2"))   # value/: before review 12
os.makedirs(OUT, exist_ok=True)
POINTS = (0.0, 0.0, 0.2, 0.35, 0.5, 0.62)        # the gate counts double: it's where most of a trip is decided
HALF = R.half_layout(float(os.environ.get("RUNIN", "300")))   # review 12's synthetic half-mile: 300 ft to the first turn


def setup(rnd):
    D.setup()
    R.P.update(tuck_back=4.0, **HALF)
    D.load(4)                                     # the linear scores: round 0's policy, and the fallback
    if rnd > 0:
        load(rnd - 1)


def load(rnd):
    R.VALUE_MODEL.clear()
    R.VALUE_MODEL.update(json.load(open(os.path.join(OUT, f"value_{rnd}.json"))))


def place(o, name):
    return [h.name for h in o].index(name) + 1


def sample(rng, i, seed):
    track = rng.choice(("mile", "half"))
    stats = [R.avg(**{t: rng.gauss(0, .4) for t in D.TR}) for _ in range(8)]
    at = rng.choice(POINTS)
    rs = seed * 1000003 + i
    f = [R.Runner(f"H{k}", dict(s), "mid", k + 1) for k, s in enumerate(stats)]
    if at == 0.0:                                 # the gate: plan once, then everyone starts on their planned aim but one
        R.drive_plan(f, track, {"events": []})
        plan = {h.name: h.aim for h in f}
        subj = rng.choice(f)
        rows = []
        for a in R.AIMS:
            g = [R.Runner(f"H{k}", dict(s), "mid", k + 1, {"start_aim": a if f"H{k}" == subj.name else plan[f"H{k}"]}) for k, s in enumerate(stats)]
            o, _ = R.run(g, track, rng=random.Random(rs), dt=0.125)
            rows.append((a, R.aim_x(subj, f, track, a, 0.0, plan), place(o, subj.name)))
        return rows, track, at
    o, rec = R.run(f, track, rng=random.Random(rs), dt=0.125, snap_at=at)
    snap = rec.get("snap")
    cands = [h for h in (snap or []) if not h.done and not h.moving]
    if not cands:
        return [], track, at
    subj = rng.choice(cands)
    xs = {a: R.aim_x(subj, snap, track, a, rec["snap_t"]) for a in R.AIMS}
    rows = []
    for a in R.AIMS:
        if not R.feasible(subj, a, snap):
            continue
        g = copy.deepcopy(snap)
        for h in g:
            h.aim_t -= rec["snap_t"]                  # the continuation's clock starts at 0
        s_ = next(h for h in g if h.name == subj.name)
        R.set_aim(s_, a, 0.0, {"events": []}, "")
        o, _ = R.run(g, track, rng=random.Random(rs + 7), dt=0.125)
        rows.append((a, xs[a], place(o, subj.name)))
    return rows, track, at


if __name__ == "__main__":
    cmd, rnd = sys.argv[1], int(sys.argv[2])
    setup(rnd if cmd == "collect" else 0)
    if cmd == "collect":
        seed, n = int(sys.argv[3]), int(sys.argv[4])
        rng = random.Random(seed + 7919 * rnd)
        data = []
        for i in range(n):
            rows, track, at = sample(rng, i, seed + 7919 * rnd)
            if len(rows) > 1:
                data.append(dict(track=track, at=at, rows=rows))
        json.dump(data, open(os.path.join(OUT, f"cf_{rnd}_{seed}.json"), "w"))
        print(len(data), "states")
    else:
        import glob
        import numpy as np
        data = [d for k in range(rnd + 1) for fn in glob.glob(os.path.join(OUT, f"cf_{k}_*.json")) for d in json.load(open(fn))]
        if cmd == "aims":
            import collections
            best, wins, n = collections.Counter(), collections.Counter(), collections.Counter()
            for d in data:
                pl = {a: p for a, _, p in d["rows"]}
                lo = min(pl.values())
                for a in pl:
                    n[a] += 1; best[a] += pl[a] == lo; wins[a] += pl[a] == 1
            print("aim: share of states where it's (tied) best · share where it wins · states tried")
            for a in R.AIMS:
                print(f"  {a:10s} best {best[a] / n[a]:.2f}  wins {wins[a] / n[a]:.2f}  n {n[a]}")
            sys.exit()
        rng = random.Random(5)
        test = set(rng.sample(range(len(data)), len(data) // 5))       # held out by whole state
        model, lam = {}, float(os.environ.get("LAM", "30"))
        for a in R.AIMS:
            X = np.array([R.quad(r[1]) for k, d in enumerate(data) if k not in test for r in d["rows"] if r[0] == a])
            y = np.array([r[2] for k, d in enumerate(data) if k not in test for r in d["rows"] if r[0] == a], float)
            mu, sd = X.mean(0), X.std(0)
            flat = sd < 1e-4                          # constant in this aim's rows: no information, keep it out
            sd[flat] = 1.0
            Z = (X - mu) / sd
            Z[:, flat] = 0.0
            coef = np.linalg.solve(Z.T @ Z + lam * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
            coef[flat] = 0.0
            model[a] = dict(mean=mu.round(6).tolist(), std=sd.round(6).tolist(), coef=coef.round(6).tolist(), b=round(float(y.mean()), 4))
        pred = lambda a, x: model[a]["b"] + float(((np.array(R.quad(x)) - model[a]["mean"]) / model[a]["std"]) @ model[a]["coef"])
        reg, rnd_reg, top1, n = 0.0, 0.0, 0, 0
        for k in test:
            rows = data[k]["rows"]
            pl = {a: p for a, _, p in rows}
            choice = min(rows, key=lambda r: pred(r[0], r[1]))[0]
            reg += pl[choice] - min(pl.values()); rnd_reg += sum(pl.values()) / len(pl) - min(pl.values())
            top1 += pl[choice] == min(pl.values()); n += 1
        print(f"held-out states {n}: regret {reg / n:.2f} places (random aim {rnd_reg / n:.2f}); picked a best aim {top1 / n:.0%}")
        json.dump(model, open(os.path.join(OUT, f"value_{rnd}.json"), "w"))
