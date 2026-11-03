"""Baseline: how well does the current engine (outcome.race) let a horse's bars predict its results? Measures only, tunes
nothing, writes nothing to the save (REBUILD_PLAN.md tests 1-4).
    python research/engine_lab/baseline.py [save.pkl] [--races N]

Fields are drawn from the save's racing horses (3+, unretired, raced): 'random' fields mix all classes so every rating
gap shows up; 'class' fields are 8 neighbours by rating, like a real night's condition."""
import argparse, os, pickle, random, statistics as st, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import outcome  # noqa: E402

GAPS = (0, 0.25, 0.5, 1, 1.5, 2, 3, 99)        # rating gap bins, in bars
NAMES = ("gate", "cruise", "kick", "grit", "manners")


def corr(xs, ys):
    mx, my = st.fmean(xs), st.fmean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5


def ols(X, y):
    """Least squares with no intercept (rows are already centred per race): returns coefficients."""
    k = len(X[0])
    A = [[sum(r[i] * r[j] for r in X) for j in range(k)] for i in range(k)]
    b = [sum(r[i] * v for r, v in zip(X, y)) for i in range(k)]
    for c in range(k):                                    # Gauss-Jordan
        p = max(range(c, k), key=lambda r: abs(A[r][c]))
        A[c], A[p], b[c], b[p] = A[p], A[c], b[p], b[c]
        for r in range(k):
            if r != c:
                f = A[r][c] / A[c][c]
                A[r] = [a - f * q for a, q in zip(A[r], A[c])]
                b[r] -= f * b[c]
    return [b[i] / A[i][i] for i in range(k)]


def run(pool, fields, label):
    pairs = {g: [0, 0, 0] for g in GAPS[:-1]}           # bin -> [pairs, better ahead, better beaten 5+ L]
    X, y, rho = [], [], []
    for field in fields:
        rate = {h.id: outcome.rating(h) for h in field}
        bar = {h.id: outcome.bars(h, h.developed) for h in field}
        order = outcome.race(list(field), "mile")
        L = {h.id: max(0.0, h.margin_l) for h in order}
        for i, a in enumerate(field):
            for b in field[i + 1:]:
                hi, lo = (a, b) if rate[a.id] >= rate[b.id] else (b, a)
                gap = rate[hi.id] - rate[lo.id]
                g = max(x for x in GAPS[:-1] if gap >= x)
                pairs[g][0] += 1
                pairs[g][1] += L[hi.id] < L[lo.id]
                pairs[g][2] += L[hi.id] - L[lo.id] >= 5
        mb = {k: st.fmean(bar[h.id][k] for h in field) for k in NAMES}
        ml = st.fmean(L.values())
        for h in field:
            X.append([bar[h.id][k] - mb[k] for k in NAMES])
            y.append(L[h.id] - ml)
        ranks = sorted(field, key=lambda h: -rate[h.id])
        rho.append(corr([ranks.index(h) for h in field], [order.index(h) for h in field]))
    print(f"\n== {label} fields: {len(fields)} races of 8 ==")
    print("rating gap (bars)   pairs   better horse ahead   better beaten by 5+ L")
    for i, g in enumerate(GAPS[:-1]):
        n, ahead, blow = pairs[g]
        if n:
            hi = GAPS[i + 1]
            print(f"  {g:>4}-{hi if hi < 99 else '':<4}       {n:>6}        {100 * ahead / n:5.1f}%               {100 * blow / n:5.1f}%")
    w = ols(X, y)
    print("lengths gained per bar (holding the others fixed):  " + ",  ".join(f"{k} {-c:+.2f}" for k, c in zip(NAMES, w)))
    print(f"rating rank vs finish rank (Spearman, mean per race): {st.fmean(rho):.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("save", nargs="?", default=os.path.join(ROOT, "save.pkl"))
    ap.add_argument("--races", type=int, default=1500)
    a = ap.parse_args()
    G = pickle.load(open(a.save, "rb"))["G"]
    pool = [h for h in G["horses"] if not h.retired and h.age >= 3 and h.starts]
    print(f"save day {G['day']}, racing horses 3+: {len(pool)}")
    rng = random.Random(1)
    run(pool, [rng.sample(pool, 8) for _ in range(a.races)], "random")
    by = sorted(pool, key=outcome.rating)
    run(pool, [by[s:s + 8] for s in (rng.randrange(len(by) - 8) for _ in range(a.races))], "class (8 neighbours by rating)")

    vets = [h for h in G["horses"] if h.starts >= 10]
    r = [outcome.rating(h) for h in vets]
    print(f"\n== the save's own history: {len(vets)} horses with 10+ starts (whatever engine raced them) ==")
    print(f"rating today vs earnings per start: r = {corr(r, [h.earnings / h.starts for h in vets]):.2f}")
    print(f"rating today vs win rate:           r = {corr(r, [h.wins / h.starts for h in vets]):.2f}")


if __name__ == "__main__":
    main()
