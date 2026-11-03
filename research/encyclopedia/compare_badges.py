"""Ratings v2 against the live badge, on the 100-season world (sim100.py with the fig_* and tier_live columns).

  python research/encyclopedia/compare_badges.py [db]

The truth is the engine's own: pred (outcome.pred_mile of the horse's bars that season) is what it races on, cut at
MILE_TIERS it is the tier the horse "is". Each badge is judged against it on the same horse-seasons (racing, 2+):
  shares      S+ and S shares by season (drift)
  agreement   badge == truth tier; mean |badge secs - pred|
  flips       badge changed between two seasons whose truth tier didn't
  decline lag seasons from the first season the truth tier drops below its peak until the badge drops
  jump        the badge change from the last unproven season to the first proven one
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


def cut(secs):
    return next((t for c, t in app.MILE_TIERS if secs <= c), "D")


def main():
    d = sqlite3.connect(DB)
    rows = d.execute("SELECT id, season, age, tier, tier_live, fig_recent, fig_peak, pred, starts FROM seasons "
                     "WHERE retired=0 AND age>=2 ORDER BY id, season").fetchall()
    by = collections.defaultdict(list)
    for r in rows:
        by[r[0]].append(r)
    print(f"{len(rows)} horse-seasons, {len(by)} horses\n")
    print("shares of S+ / S among racing horses 2+ (truth = the bars' predicted mile cut at the tiers)")
    print(f"{'season':>6} {'n':>5} {'truth':>11} {'v2':>11} {'live':>11}")
    for s in (5, 20, 40, 60, 80, 99):
        rs = [r for r in rows if r[1] == s]
        if not rs:
            continue
        def sh(f):
            ts = [f(r) for r in rs]
            return f"{100 * ts.count('S+') / len(ts):4.1f}% {100 * ts.count('S') / len(ts):4.1f}%"
        print(f"{s:>6} {len(rs):>5} {sh(lambda r: cut(r[7])):>11} {sh(lambda r: r[3]):>11} {sh(lambda r: r[4]):>11}")
    proven = [r for r in rows if r[3] and r[4] and r[5] is not None]
    print(f"\nagreement with the truth tier (n {len(proven)} proven horse-seasons):")
    for name, f, secs in (("v2 recent", lambda r: r[3], lambda r: r[5]), ("v2 peak", lambda r: cut(r[6]) if r[6] else None, lambda r: r[6]),
                          ("live est", lambda r: r[4], None)):
        ok = [f(r) == cut(r[7]) for r in proven if f(r)]
        off = [abs(ORDER.index(f(r)) - ORDER.index(cut(r[7]))) for r in proven if f(r)]
        err = f"  mean |secs - pred| {st.mean(abs(secs(r) - r[7]) for r in proven if secs(r) is not None):.2f} s" if secs else ""
        print(f"  {name:10} same tier {100 * st.mean(ok):4.1f}%   within one {100 * st.mean(x <= 1 for x in off):4.1f}%{err}")
    flips, lags, jumps = collections.Counter(), collections.defaultdict(list), collections.defaultdict(list)
    stable = collections.Counter()
    for hid, hs in by.items():
        peak_i, truth = None, [cut(r[7]) for r in hs]
        for i in range(1, len(hs)):
            if truth[i] == truth[i - 1]:
                stable["n"] += 1
                for name, k in (("v2", 3), ("live", 4)):
                    if hs[i][k] and hs[i - 1][k] and hs[i][k] != hs[i - 1][k]:
                        flips[name] += 1
        best = min(range(len(truth)), key=lambda i: ORDER.index(truth[i]))
        drop = next((i for i in range(best + 1, len(truth)) if ORDER.index(truth[i]) > ORDER.index(truth[best])), None)
        if drop is not None and hs[drop][3] and hs[drop][4]:
            for name, k in (("v2", 3), ("live", 4)):
                top = min(ORDER.index(hs[i][k]) for i in range(best, drop) if hs[i][k])
                after = next((i for i in range(drop, len(hs)) if hs[i][k] and ORDER.index(hs[i][k]) > top), None)
                lags[name].append(after - drop if after is not None else len(hs) - drop)
        first = next((i for i in range(1, len(hs)) if hs[i - 1][8] < app.PED_STARTS <= hs[i][8]), None)
        if first is not None and hs[first][3] and hs[first - 1][3]:
            jumps["v2"].append(ORDER.index(hs[first][3]) - ORDER.index(hs[first - 1][3]))
    print(f"\nflips while the truth tier held (n {stable['n']} season pairs): v2 {100 * flips['v2'] / stable['n']:.1f}%  live {100 * flips['live'] / stable['n']:.1f}%")
    for name in ("v2", "live"):
        v = lags[name]
        print(f"decline lag, {name}: n {len(v)}, median {st.median(v):.0f} seasons, caught the same season {100 * v.count(0) / len(v):.0f}%, never {100 * sum(x >= 3 for x in v) / len(v):.0f}% (3+)")
    j = jumps["v2"] or [0]
    print(f"\nunproven -> proven jump (v2, n {len(j)}): no change {100 * j.count(0) / len(j):.0f}%, one tier {100 * sum(abs(x) == 1 for x in j) / len(j):.0f}%, two or more {100 * sum(abs(x) >= 2 for x in j) / len(j):.0f}%, mean {st.mean(j):+.2f} (positive = a lower badge once proven)")


if __name__ == "__main__":
    main()
