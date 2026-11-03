"""Replay badge windows offline on the logged starts (sim100.py's `starts` table) and judge them the same way for v2 and live.

  python research/encyclopedia/badge_windows.py [db]

For each horse, start by start: v2's badge for a window W = median of its last W figures (needs 3); live's = the est after
the start, as mile seconds (circuit.mile_secs) cut at the tiers. At each horse's last start of a season the badge is scored on
  next      rank correlation with next season's purses per start, by age (what a player gets from the badge)
  now       same tier as the bars' predicted mile that night (what the engine races on)
  flips     the badge changed between two season ends whose predicted tier didn't
"""
import collections
import os
import sqlite3
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
import app                                                     # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "research", "encyclopedia", "world100.db")
ORDER = ["S+", "S", "A", "B", "C", "D"]
WINDOWS = (4, 6, 8, 10, 15)


def cut(secs):
    return next((t for c, t in app.MILE_TIERS if secs <= c), "D")


def rank(xs):
    s = sorted(range(len(xs)), key=lambda i: xs[i]); r = [0] * len(xs)
    for k, i in enumerate(s):
        r[i] = k
    return r


def main():
    d = sqlite3.connect(DB)
    age = {(i, s): a for i, s, a in d.execute("SELECT id, season, age FROM seasons")}
    earn = collections.defaultdict(lambda: [0.0, 0])                       # (id, season) -> purses, starts
    by = collections.defaultdict(list)
    for i, day, track, place, won, fig, est, pred in d.execute("SELECT * FROM starts ORDER BY id, day"):
        s = day // 52
        earn[i, s][0] += won; earn[i, s][1] += 1
        by[i].append((s, fig, est, pred))
    names = [f"v2 last {w}" for w in WINDOWS] + ["live est"]
    ends = []                                                              # per season end: (id, season, badges..., pred tier)
    for i, rows in by.items():
        figs = []
        for k, (s, fig, est, pred) in enumerate(rows):
            if fig is not None:
                figs.append(fig)
            if k + 1 < len(rows) and rows[k + 1][0] == s:
                continue                                                   # not the season's last start
            b = [cut(st.median(figs[-w:])) if len(figs) >= 3 else None for w in WINDOWS]
            b.append(cut(app.c.mile_secs(est)))
            ends.append((i, s, b, cut(pred)))
    print(f"{len(ends)} season ends, {len(by)} horses\n")
    print(f"{'badge':12} {'now: same tier':>14} {'flips':>7}   next-season purses rank corr at age 3 / 4 / 5 / 6")
    for j, name in enumerate(names):
        same = [e[2][j] == e[3] for e in ends if e[2][j]]
        prev = {}
        flips = stable = 0
        for i, s, b, t in ends:
            if (i, s - 1) in prev and prev[i, s - 1][1] == t and b[j] and prev[i, s - 1][0][j]:
                stable += 1; flips += b[j] != prev[i, s - 1][0][j]
            prev[i, s] = (b, t)
        corr = []
        for a in (3, 4, 5, 6):
            xs, ys = [], []
            for i, s, b, t in ends:
                nxt = earn.get((i, s + 1))
                if b[j] and age.get((i, s)) == a and nxt and nxt[1] >= 5:
                    xs.append(-ORDER.index(b[j])); ys.append(nxt[0] / nxt[1])
            corr.append(st.correlation(rank(xs), rank(ys)) if len(xs) > 10 else float("nan"))
        print(f"{name:12} {100 * st.mean(same):13.1f}% {100 * flips / max(1, stable):6.1f}%   " + " / ".join(f"{c:.3f}" for c in corr))


if __name__ == "__main__":
    main()
