"""Bringing the new engine to the live world (DECISIONS 235): convert every horse to the big-four card and the
bars-make-the-tier rating, and list every tier that moves. Read-only: works on a copy of the live save.

Bars stay on the live game's own pip scale (an average aged horse about 6; 9 about one in a hundred), made continuous,
so every horse keeps its standing in each stat (1A). The card (DECISIONS 222): Speed = gate speed and finish blended by
what each wins; Stamina; Grit (new, seeded from durability and gait genes, 2A); Manners (shown, not rated).
Rating (DECISIONS 217/224): .242 gate + .304 stamina + .391 finish + .064 grit, on bars; tiers from the approved lines.
    python v6_convert.py <save.pkl> [out.json]"""
import json, os, sys
from collections import Counter, defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, ROOT)

W = {"gate": .242, "stam": .304, "finish": .391, "grit": .064}
LINES = None   # set from the approved tier sizes on today's racing horses (DECISIONS 219): see lines()


def lines(ratings, old_tiers):
    """Tier lines from the approved sizes: Galaxy top 0.1%, S+ top 2%, S the rest of today's S+ and S band,
    A, B, C and D keep today's shares. ratings and old_tiers: today's racing horses 3+."""
    r = np.sort(ratings)[::-1]; n = len(r); c = Counter(old_tiers)
    at = lambda share: float(r[min(n - 1, max(0, int(round(share * n)) - 1))])
    top = (c["S+"] + c["S"]) / n
    a, b, cc = top + c["A"] / n, top + (c["A"] + c["B"]) / n, top + (c["A"] + c["B"] + c["C"]) / n
    return (("Galaxy", at(.001)), ("S+", at(.02)), ("S", at(top)), ("A", at(a)), ("B", at(b)), ("C", at(cc)))
LIVE = {"gate": "early_speed", "stam": "stamina", "finish": "late_speed", "manners": "gait"}


def tier(r, L=None):
    return next((t for t, cut in (L or LINES) if r >= cut), "D")


def bar(app, trait, v):
    """The live pip scale made continuous: 1 below the bottom step, 10 at the top step (6.0), linear between."""
    v = app.on_bar(trait, v)
    xs = (-4.17,) + tuple(app.PIP_STEPS)
    return float(np.clip(np.interp(v, xs, range(1, 11)), 1, 10))


def grit_z(H):
    """Grit seeded from toughness genes (2A): each horse's durability and gait potential, standardized and averaged,
    then standardized again across the population: a normal score per horse."""
    d = np.array([h.potential["durability"] for h in H]); g = np.array([h.potential["gait"] for h in H])
    raw = (d - d.mean()) / d.std() + (g - g.mean()) / g.std()
    return dict(zip([h.id for h in H], (raw - raw.mean()) / raw.std()))


def convert(app, H, ref):
    """Bars, rating and tier for each horse. ref: the racing horses whose stamina bars set the Grit bar's spread."""
    gz = grit_z(H)
    stam = np.sort([bar(app, "stamina", h.developed["stamina"]) for h in ref])
    qs = np.linspace(0, 1, len(stam))
    out = {}
    for h in H:
        if h.retired:                                               # a retired horse keeps the rating of its prime, as today
            dev = {t: h.ceiling(t, h.peak_age) for t in h.potential}
        else:
            dev = h.developed if not app.is_pedigree(h) else {t: h.potential[t] for t in h.potential}
        b = {k: bar(app, t, dev[t]) for k, t in LIVE.items()}
        from statistics import NormalDist
        b["grit"] = float(np.interp(NormalDist().cdf(gz[h.id]), qs, stam))   # same spread as the stamina bars
        b["speed"] = (W["gate"] * b["gate"] + W["finish"] * b["finish"]) / (W["gate"] + W["finish"])
        r = sum(W[k] * b[k] for k in W)
        out[h.id] = dict(bars={k: round(v, 2) for k, v in b.items()}, rating=round(r, 3))
    return out


if __name__ == "__main__":
    save = sys.argv[1]; out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "v6", "convert.json")
    os.chdir(ROOT)
    import app
    app.load(save)
    racing = [h for h in app.G["horses"] if not h.retired and h.age >= 3 and not app.is_pedigree(h)]
    everyone = [h for h in app.G["horses"] if not app.is_pedigree(h)]
    conv = convert(app, everyone, racing)
    LINES = lines([conv[h.id]["rating"] for h in racing], [app.tier_label(h) for h in racing])
    # two-year-olds are tiered within their age group (Patrick, DECISIONS 237): the same tier sizes as the racing
    # horses 3+, measured on the two-year-olds' own ratings
    twos = [h for h in everyone if not h.retired and h.age == 2]
    share = Counter(tier(conv[h.id]["rating"]) for h in racing)
    r2 = np.sort([conv[h.id]["rating"] for h in twos])[::-1]; cum, L2 = 0, []
    for t in ("Galaxy", "S+", "S", "A", "B", "C"):
        cum += share[t] / len(racing)
        L2.append((t, float(r2[min(len(r2) - 1, max(0, int(round(cum * len(r2))) - 1))]) if share[t] else 99.0))
    for h in everyone:
        conv[h.id]["tier"] = tier(conv[h.id]["rating"], L2 if h in twos else None)
    print("two-year-old lines:", ", ".join(f"{t} {c:.2f}" for t, c in L2))
    print("tier lines:", ", ".join(f"{t} {c:.2f}" for t, c in LINES))
    order = ["Galaxy", "S+", "S", "A", "B", "C", "D"]
    old_rank = {"S+": 1, "S": 2, "A": 3, "B": 4, "C": 5, "D": 6}
    rows, moves, by_barn = [], Counter(), defaultdict(list)
    for h in everyone:
        new, old = conv[h.id]["tier"], app.tier_label(h)
        d = old_rank.get(old, 9) - order.index(new)                 # positive: moved up (Galaxy counts above S+)
        moves["up" if d > 0 else "down" if d < 0 else "same"] += 1
        row = dict(name=h.name, barn=app.barn_name(h.owner) if h.owner is not None else "(house)", owner=h.owner,
                   age=h.age, retired=h.retired, old=old, new=new, **conv[h.id])
        rows.append(row)
        if d:
            by_barn[row["barn"]].append(row)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(dict(lines=LINES, rows=rows), open(out_path, "w"), indent=0)
    print(f"{len(everyone)} horses ({len(racing)} racing 3+): {moves['same']} keep their tier, {moves['up']} up, {moves['down']} down")
    print("new tier counts, racing 3+:", Counter(conv[h.id]["tier"] for h in racing))
    print("old tier counts, racing 3+:", Counter(app.tier_label(h) for h in racing))
    for b, rs in sorted(by_barn.items(), key=lambda x: -len(x[1]))[:12]:
        up = sum(order.index(r["new"]) < old_rank.get(r["old"], 9) for r in rs)
        print(f"  {b}: {len(rs)} change ({up} up, {len(rs) - up} down)")
