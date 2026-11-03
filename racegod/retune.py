"""RaceGod V1 point 2: retune the outcome model's post cost and front-end value on real fields, through the audit.
Differential evolution over outcome.P knobs (per track: c_post, A_lead, A_pocket, A_fol), one run of the real fields
per evaluation, loss = TARGETS.md bands plus the fitted trip shares' sanity. Proposes values; ships nothing.
    python racegod/retune.py <save.pkl> [generations, default 10]       writes racegod/retune.json"""
import json, os, pickle, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit, engine_lab, outcome                               # noqa: E402
from speed_lab import fields                                   # noqa: E402

KNOBS = {("half", "c_post"): (0.02, 0.30), ("half", "A_lead"): (0.1, 1.2), ("half", "A_pocket"): (0.1, 1.2), ("half", "A_fol"): (0.0, 0.6),
         ("mile", "c_post"): (0.02, 0.30), ("mile", "A_lead"): (0.3, 1.6), ("mile", "A_pocket"): (0.3, 1.6), ("mile", "A_fol"): (0.0, 0.8)}
LEAD_SHARE = {"half": (30, 45), "mile": (22, 35)}            # leaders' share of wins (DECISIONS 207/238: half 33-43%, mile 25-30%)


def loss(races):
    stories, results, extra = engine_lab.run(races, "today", 1)
    m, L = audit.measure(stories, results), 0.0
    for key, t in audit.targets().items():
        v, lo, hi = m[key][0], *t["band"]
        if v is not None and ("post" in key or key in ("favorite_win", "margin_median_l")):
            L += (max(0.0, lo - v, v - hi) / max(1.0, (hi - lo) / 2)) ** 2
    for track, (lo, hi) in LEAD_SHARE.items():
        wins = [s for s in stories if s["track"] == track]
        lead = 100 * sum("on the lead" in s["horses"][0]["trip"] for s in wins) / len(wins)
        L += (max(0.0, lo - lead, lead - hi) / 5) ** 2
    L += max(0.0, m["mile_post8_win"][0] - m["mile_post1_win"][0]) ** 2 / 4   # post 1 beats post 8 on the mile
    return L, m, extra


def main():
    path = sys.argv[1]
    gens = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    with open(path, "rb") as f:
        races = fields(pickle.load(f), 2626)
    rng, names, pop = random.Random(2), list(KNOBS), 8

    def score(x):
        for (track, k), v in zip(names, x):
            outcome.P[track][k] = v
        return loss(races)[0]
    X = [[outcome.P[t][k] for t, k in names]] + [[rng.uniform(*KNOBS[n]) for n in names] for _ in range(pop - 1)]
    L = [score(x) for x in X]
    print(f"gen 0: best {min(L):.2f} (today's values {L[0]:.2f})", flush=True)
    for g in range(1, gens + 1):
        for i in range(pop):
            a, b, c = rng.sample([j for j in range(pop) if j != i], 3)
            kk = rng.randrange(len(names))
            y = [min(KNOBS[n][1], max(KNOBS[n][0], X[a][j] + 0.6 * (X[b][j] - X[c][j]))) if (rng.random() < 0.7 or j == kk) else X[i][j] for j, n in enumerate(names)]
            Ly = score(y)
            if Ly <= L[i]:
                X[i], L[i] = y, Ly
        best = min(range(pop), key=lambda i: L[i])
        print(f"gen {g}: best {L[best]:.2f}  " + " ".join(f"{t}.{k}={X[best][j]:.3f}" for j, (t, k) in enumerate(names)), flush=True)
        json.dump({f"{t}.{k}": X[best][j] for j, (t, k) in enumerate(names)}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "retune.json"), "w"), indent=1)
    best = min(range(pop), key=lambda i: L[i])
    _, m, extra = loss(races) if score(X[best]) is not None else (None, None, None)
    print(f"\nbest loss {L[best]:.2f}")
    for key, t in audit.targets().items():
        print(f"  {key:28s} {m[key][0] if m[key][0] is None else round(m[key][0], 1)}   band {t['band']}")
    n = len(extra["trip"])
    print("  winning trips " + ", ".join(f"{k} {100 * extra['trip'].count(k) / n:.0f}%" for k in set(extra["trip"])))


if __name__ == "__main__":
    main()
