"""Fields made for a replay (DECISIONS 226): find eight horses the outcome model would most often send down a library
replay's story: the scripted winner, on the scripted trip, with the scripted runner-up. Cross-entropy search over the
field's traits, kept to a believable class (every trait within two spreads of average).
    python v5_fit_field.py <story> <A|B>      prints the field and how often the model plays out the replay"""
import json, os, re, sys
import numpy as np
import v4_outcome as V

HERE = os.path.dirname(os.path.abspath(__file__))
ROLE = {"lead": 0, "pocket": 1, "first-over": 2, "follow": 3, "back": 4, "line": 4}
K, POP, ELITE, ITERS = 400, 48, 8, 25
CAP = 2 * V.SD
W = np.array([0.242, 0.304, 0.391, 0.0, 0.064])                     # the rating's weights on gate, cruise, kick, (manners), grit
BAND = float(os.environ.get('BAND', 0.6))                                                         # one class: every rating within this of the field's average
rating = lambda F: 5 + 2 * (F @ W) / 0.4                            # bars weighted by worth (DECISIONS 217)


def replay(story, ab):
    p = open(os.path.join(HERE, "v5", "library", "index.html"), encoding="utf-8").read()
    races = json.loads(re.search(r"window\.V3 = (\{.*?\});\n", p, re.S).group(1))["half" if ab == "A" else "mile"]
    s = next(r for r in races if r["title"].startswith("Replay library · " + __import__("v5_choreo").TITLE[story]))
    hs = sorted(s["horses"], key=lambda h: h["place"])
    return hs[0]["post"] - 1, ROLE[hs[0]["trip"]], hs[1]["post"] - 1, s


def score(p, D, fields, w, role_w, second):
    """Per candidate field: share of K races that play out the replay (winner, its trip, runner-up), and winner-only share."""
    C = fields.shape[0]
    traits = np.repeat(fields, K, axis=0)
    DD = {k: (np.tile(v, (C,) + (1,) * (v.ndim - 1)) if k != "traits" else traits) for k, v in D.items()}
    P, role, _ = V.race(p, DD, "half")
    order = np.argsort(-P, axis=1)
    win = (order[:, 0] == w).reshape(C, K)
    trip = (role[:, w] == role_w).reshape(C, K)
    two = (order[:, 1] == second).reshape(C, K)
    return (win & trip & two).mean(1), (win & trip).mean(1), win.mean(1)


if __name__ == "__main__":
    story, ab = sys.argv[1], sys.argv[2]
    w, role_w, second, s = replay(story, ab)
    p = dict(V.FIXED, **json.load(open(os.path.join(V.OUT, "fit_half.json")))["params"])
    D = V.draws(K, 8, 777)
    D.pop("present")
    rng = np.random.default_rng(5)
    mu, sd = np.zeros((8, 5)), np.full((8, 5), V.SD)
    mu[w, [0, 1, 2, 4]] = 0.3; mu[second, [0, 1, 2, 4]] = 0.15          # warm start: the search needs some wins to learn from
    best = (-1, None)
    for it in range(ITERS):
        F = np.clip(mu + sd * rng.normal(size=(POP, 8, 5)), -CAP, CAP)
        F[..., 3] = np.clip(F[..., 3], -V.SD, CAP)                   # manners: no wild breakers in a showcase field
        F[..., 4] = np.clip(F[..., 4], -V.SD, V.SD)                  # grit within a spread: it's nearly free in the rating, so the search maxed it
        F -= F.mean(1, keepdims=True)                                # an average class: the story comes from trips, not a mismatch
        full, wt, wo = score(p, D, F, w, role_w, second)
        r = rating(F)
        obj = full + 0.5 * wt - 2 * np.maximum(0, np.abs(r - r.mean(1, keepdims=True)) - BAND).sum(1)
        el = np.argsort(-obj)[:ELITE]
        mu, sd = F[el].mean(0), np.maximum(F[el].std(0), 0.03)
        if obj[el[0]] > best[0]:
            best = (obj[el[0]], F[el[0]], full[el[0]], wt[el[0]], wo[el[0]])
    _, f, full, wt, wo = best
    D2 = V.draws(4000, 8, 4242); D2.pop("present")                     # judged on fresh races, not the ones it was tuned on
    K_ = K; K = 4000
    full2, wt2, wo2 = score(p, D2, f[None], w, role_w, second)
    print(f"{story} {ab}: winner post {w + 1} ({V.ROLES[role_w]}), runner-up post {second + 1}")
    print(f"  plays out the replay {100 * full2[0]:.0f}% (winner on that trip {100 * wt2[0]:.0f}%, winner at all {100 * wo2[0]:.0f}%)")
    bar = lambda v: int(round(min(10, max(1, 5 + 2 * v / 0.4))))
    r = rating(f[None])[0]
    for i in range(8):
        print(f"  post {i + 1}: Speed {bar((0.242 * f[i, 0] + 0.391 * f[i, 2]) / 0.633)}  Stam {bar(f[i, 1])}  Grit {bar(f[i, 4])}  Manners {bar(f[i, 3])}  rating {r[i]:.2f}   "
              f"(gate {f[i, 0]:+.2f} cruise {f[i, 1]:+.2f} kick {f[i, 2]:+.2f} grit {f[i, 4]:+.2f})")
    os.makedirs(os.path.join(HERE, "v5", "fields"), exist_ok=True)
    json.dump(dict(story=story, ab=ab, traits=f.round(3).tolist(), plays_out=float(full2[0]), win_trip=float(wt2[0]), win=float(wo2[0])),
              open(os.path.join(HERE, "v5", "fields", f"{story}_{ab}.json"), "w"), indent=1)
