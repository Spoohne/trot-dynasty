"""RaceGod V5 lab: fit the simulated race's knobs (engine.E) to TARGETS.md and the outcome model's winning-trip shares,
by local random search on the real fields (one run each; sim only). Reads a save copy, never writes it.
    python racegod/engine_fit.py <save.pkl> [trials, default 40] [first day, default 2626]
Prints the best knobs and keeps them in racegod/engine_fit.json; paste the ones you keep into engine.E by hand."""
import json, os, pickle, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit, engine, engine_lab                                 # noqa: E402
from speed_lab import fields                                   # noqa: E402

KNOBS = dict(launch_gate=(0.005, 0.05), lead_soft=(-0.04, 0.0), lead_hot=(0.0, 0.04), push=(0.01, 0.06), drive=(0.0, 0.05),
             drive_kick=(0.0, 0.05), prof_kick=(0.0, 0.03), draft=(0.05, 0.25), wind=(0.0, 0.08), turn=(0.0, 0.15),
             duel=(0.0, 0.3), reserve=(1.0, 6.0), reserve_cruise=(0.0, 2.0), fade=(0.005, 0.04), ease=(1.0, 5.0),
             push_fo=(0.02, 0.10), drive_able=(0.0, 0.06), yield_max=(20.0, 60.0), reserve_able=(0.0, 8.0), drive_close=(0.0, 0.06))
TRIPS = {"on the lead": 29, "sat in behind": 22, "sat mid-pack": 21, "sat in the pocket": 16, "parked first-over": 13}   # today's engine, 315 fields x2


def loss(races):
    stories, results, extra = engine_lab.run(races, "sim", 1)
    m, L = audit.measure(stories, results), 0.0
    for key, t in audit.targets().items():
        v, lo, hi = m[key][0], *t["band"]
        if v is not None:
            L += (max(0.0, lo - v, v - hi) / max(1.0, (hi - lo) / 2)) ** 2 * (3 if key == "favorite_win" else 1)
    n = len(extra["trip"])
    for trip, share in TRIPS.items():
        L += (100 * extra["trip"].count(trip) / n - share) ** 2 / 100
    L += sum(audit.laws(s) != [] for s in stories) / len(stories) * 4
    L += max(0.0, (sum(x >= 20 for x in extra["last"]) / n * 100 - 25) / 10) ** 2   # a straggler 20 L back in no more than a quarter of races
    return L, m, extra


def de(races, gens, rng, pop=10, F=0.6, CR=0.7):
    """Differential evolution (rand/1/bin) over KNOBS; returns the best knobs and loss. Seeds the population on today's E."""
    names = list(KNOBS)
    X = [[engine.E[n] for n in names]] + [[rng.uniform(*KNOBS[n]) for n in names] for _ in range(pop - 1)]
    def score(x):
        engine.E.update(zip(names, x))
        return loss(races)[0]
    L = [score(x) for x in X]
    print(f"gen 0: best {min(L):.2f}", flush=True)
    for g in range(1, gens + 1):
        for i in range(pop):
            a, b, c = rng.sample([j for j in range(pop) if j != i], 3)
            k = rng.randrange(len(names))
            y = [min(KNOBS[n][1], max(KNOBS[n][0], X[a][j] + F * (X[b][j] - X[c][j]))) if (rng.random() < CR or j == k) else X[i][j] for j, n in enumerate(names)]
            Ly = score(y)
            if Ly <= L[i]:
                X[i], L[i] = y, Ly
        best = min(range(pop), key=lambda i: L[i])
        print(f"gen {g}: best {L[best]:.2f}  " + " ".join(f"{n}={X[best][j]:.3f}" for j, n in enumerate(names)), flush=True)
        json.dump(dict(zip(names, X[best])), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine_fit.json"), "w"), indent=1)
    best = min(range(pop), key=lambda i: L[i])
    engine.E.update(zip(names, X[best]))
    return L[best]


def main():
    path = sys.argv[1]
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    args = [a for a in sys.argv[3:] if not a.startswith("--")]
    first = int(args[0]) if args else 2626
    with open(path, "rb") as f:
        races = fields(pickle.load(f), first)
    rng = random.Random(1)
    if "--de" in sys.argv:                                     # python racegod/engine_fit.py <save> <generations> --de
        best = de(races, trials, rng)
        _, m, extra = loss(races)
        print(f"\nbest loss {best:.2f}")
        for key, t in audit.targets().items():
            print(f"  {key:28s} {m[key][0] if m[key][0] is None else round(m[key][0], 1)}   band {t['band']}")
        n = len(extra["trip"])
        print("  trips " + ", ".join(f"{t} {100 * extra['trip'].count(t) / n:.0f}%" for t in TRIPS))
        return
    best, m, extra = loss(races)
    print(f"start loss {best:.2f}", flush=True)
    for k in range(trials):
        saved = dict(engine.E)
        for name in rng.sample(list(KNOBS), 3):
            lo, hi = KNOBS[name]
            engine.E[name] = min(hi, max(lo, engine.E[name] * rng.uniform(0.6, 1.5) + rng.uniform(-0.1, 0.1) * (hi - lo)))
        L, m2, extra2 = loss(races)
        if L < best:
            best, m, extra = L, m2, extra2
            print(f"trial {k}: loss {L:.2f}  " + " ".join(f"{n}={engine.E[n]:.3f}" for n in KNOBS), flush=True)
            json.dump({n: engine.E[n] for n in KNOBS}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine_fit.json"), "w"), indent=1)
        else:
            engine.E.update(saved)
            print(f"trial {k}: loss {L:.2f}", flush=True)
    print(f"\nbest loss {best:.2f}")
    for key, t in audit.targets().items():
        print(f"  {key:28s} {m[key][0] if m[key][0] is None else round(m[key][0], 1)}   band {t['band']}")
    n = len(extra["trip"])
    print("  trips " + ", ".join(f"{t} {100 * extra['trip'].count(t) / n:.0f}%" for t in TRIPS))


if __name__ == "__main__":
    main()
