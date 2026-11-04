"""The page over a Gallop-model world (gallop100.py's SQLite file): winners against the field, each stat's pull on win
rate, win rate by rank letter, the winning times, and every horse's record. One self-contained HTML file.

  python research/encyclopedia/gallop_report.py [db=gallop100.db] [out=gallop.html]

Open the file, or http://127.0.0.1:8114/gallop from serve.py.
"""
import json
import os
import sqlite3
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import gallop                                                    # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "gallop100.db")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "gallop.html")
MIN_STARTS = 20
RANKS = [L for _, L in gallop.CFG["rank_bands"]]


def spearman(a, b):
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def main():
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    meta = {r["k"]: r["v"] for r in db.execute("SELECT k, v FROM meta")}
    horses = [dict(r) for r in db.execute("SELECT * FROM horses ORDER BY wins DESC, earnings DESC")]
    done = [h for h in horses if h["starts"] >= MIN_STARTS]
    S = np.array([[h[k] for k in gallop.STATS] for h in done], float)
    wr = np.array([h["wins"] / h["starts"] for h in done])
    order = np.argsort(-wr)
    n = len(done)
    groups = {"top": order[: n // 10], "middle": order[int(n * .45): int(n * .55)], "bottom": order[-(n // 10):]}
    means = {g: {k: float(S[idx, i].mean()) for i, k in enumerate(gallop.STATS)} for g, idx in groups.items()}
    means["all"] = {k: float(S[:, i].mean()) for i, k in enumerate(gallop.STATS)}
    group_wr = {g: float(wr[idx].mean()) for g, idx in groups.items()}
    corr = {k: {"pearson": float(np.corrcoef(S[:, i], wr)[0, 1]), "spearman": spearman(S[:, i], wr)} for i, k in enumerate(gallop.STATS)}
    # a least-squares fit of win rate on the ten stats: what each point buys, holding the rest fixed
    X = np.c_[S, np.ones(n)]
    beta = np.linalg.lstsq(X, wr, rcond=None)[0]
    fit = {k: float(beta[i] * 1000) for i, k in enumerate(gallop.STATS)}          # win-rate points (per mille) a stat point buys
    by_rank = []
    for L in RANKS:
        r = db.execute("SELECT COUNT(*) n, SUM(starts) st, SUM(wins) w, SUM(places) p, AVG(earnings) e, MIN(best) b FROM horses WHERE rank=? AND starts>0", (L,)).fetchone()
        if r["n"]:
            by_rank.append({"rank": L, "horses": r["n"], "starts": r["st"], "winpct": 100 * r["w"] / r["st"], "placepct": 100 * r["p"] / r["st"],
                            "earn": r["e"], "best": r["b"]})
    wt = np.array([r[0] for r in db.execute("SELECT win_time FROM races")])
    margins = np.array([r[0] for r in db.execute("SELECT margin FROM races")])
    edges = np.arange(np.floor(wt.min() * 2) / 2, wt.max() + 0.5, 0.5)
    hist, _ = np.histogram(wt, edges)
    times = {"n": int(wt.size), "mean": float(wt.mean()), "median": float(np.median(wt)), "fastest": float(wt.min()), "slowest": float(wt.max()),
             "sd": float(wt.std()), "p10": float(np.percentile(wt, 10)), "p90": float(np.percentile(wt, 90)),
             "margin_mean": float(margins.mean()), "margin_under_02": float((margins < 0.2).mean()),
             "hist": [[float(e), int(c)] for e, c in zip(edges, hist)]}
    # what a rank letter predicts of a single race: the favorite by rank in each field, how often it won
    fav = db.execute("""SELECT AVG(won) FROM (SELECT s.place = 1 AS won FROM starts s JOIN horses h ON h.id = s.id
                        WHERE NOT EXISTS (SELECT 1 FROM starts s2 JOIN horses h2 ON h2.id = s2.id WHERE s2.season = s.season AND s2.week = s.week
                        AND s2.race = s.race AND (h2.speed + h2.staying + h2.stamina + h2.fierce + h2.tenacity + h2.power + h2.response) >
                        (h.speed + h.staying + h.stamina + h.fierce + h.tenacity + h.power + h.response)))""").fetchone()[0]
    seasons = {}
    for r in db.execute("SELECT id, season, COUNT(*) st, SUM(place = 1) w, SUM(place <= 3) p, SUM(won) e, MIN(time) b, AVG(blocked) bl, MIN(age) age FROM starts GROUP BY id, season"):
        seasons.setdefault(r["id"], []).append([r["season"], r["age"], r["st"], r["w"], r["p"], r["e"], r["b"], r["bl"]])
    data = {"meta": meta, "stats": gallop.STATS, "min_starts": MIN_STARTS, "n_done": n, "means": means, "group_wr": group_wr, "corr": corr, "fit": fit,
            "by_rank": by_rank, "fav_by_rank": fav, "times": times, "bands": gallop.CFG["rank_bands"], "clock_scale": gallop.CFG["clock_scale"],
            "horses": [[h["id"], h["name"], h["sex"], h["foaled"], h["retired"], h["rank"]] + [h[k] for k in gallop.STATS]
                       + [h["starts"], h["wins"], h["places"], round(h["earnings"]), h["best"]] for h in horses],
            "seasons": seasons}
    html = open(os.path.join(HERE, "gallop_page.html"), encoding="utf-8").read().replace("/*DATA*/null", json.dumps(data))
    open(OUT, "w", encoding="utf-8").write(html)
    print(f"{OUT}: {len(horses)} horses, {n} with {MIN_STARTS}+ starts, {times['n']} races")
    print("top 10% by win rate vs middle vs bottom, mean stat:")
    for k in gallop.STATS:
        print(f"  {k:<10}{means['top'][k]:6.1f}{means['middle'][k]:6.1f}{means['bottom'][k]:6.1f}   r={corr[k]['pearson']:+.2f}  fit {fit[k]:+.2f}")
    for r in by_rank:
        print(f"  {r['rank']:<3}{r['horses']:6d} horses  win {r['winpct']:5.1f}%  place {r['placepct']:5.1f}%")
    print(f"  rank favorite wins {100 * fav:.1f}% of races; winning time {times['mean']:.1f} s mean, {times['fastest']:.1f} fastest")


if __name__ == "__main__":
    main()
