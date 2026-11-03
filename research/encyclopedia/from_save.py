"""The encyclopedia of a world's own past, read off a save: every horse in the stud book with its season ledger (card
bars at each age from its ability curve, graded within its crop), the replays the save still keeps, and the last thirty
starts of each horse. Seasons are numbered from the oldest ledger year (Year -50 is season 0; Year 0 is season 50).

  python research/encyclopedia/from_save.py <save copy.pkl> [db=research/encyclopedia/history.db]
"""
import bisect
import json
import os
import sqlite3
import sys
import time
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "research", "encyclopedia"))
import app                                                     # noqa: E402
_argv, sys.argv = sys.argv, sys.argv[:1]                          # sim100 reads its own arguments at import
from sim100 import open_db, grade_of                           # noqa: E402
sys.argv = _argv
c, e, sk, sim = app.c, app.e, app.sk, app.sim
O = c.outcome


def main(path, db_path):
    app.load(path)
    app.ME = 0
    db = open_db(db_path)
    now = c.year_of(app.G["day"])
    everyone = c.lineage(app.G["horses"] + list(e.nursery) + list(sk.HALL))
    years = sorted({y for h in everyone for y in (getattr(h, "seasons", None) or {})})
    first = min(years) if years else now - 1
    S = lambda y: y - first                                     # season number on the page
    print(f"{len(everyone)} horses, ledger years {first}..{max(years)} (season 0 = Year {first})", flush=True)
    # cards by season: a horse's ability at that age (its ceiling, no training detail kept), graded in its crop that year
    rows = []
    for h in everyone:
        led = getattr(h, "seasons", None) or {}
        keep = dict(getattr(h, "developed", {}) or {}), h.age
        age0 = h.age
        for y, r in led.items():
            if len(r) < 6:
                continue
            age = age0 - (now - y)
            if age < 2:
                continue
            h.age = age
            h.developed = {t: h.ceiling(t, age) for t in c.RACE_TRAITS}
            b = O.bars(h, h.developed)
            bars = dict(speed=b["kick"], stamina=b["cruise"], grit=b["grit"], manners=b["manners"])
            pred = O.pred_mile(b)
            rows.append([h, y, age, bars, O.rating(h), r, b["gate"], O.best_mile(b), pred,
                         next((t for cut, t in app.MILE_TIERS if pred <= cut), "D")])
        h.developed, h.age = keep
    crop = {}
    for h, y, age, bars, *_ in rows:
        for k, v in bars.items():
            crop.setdefault((y, c.age_group(h), k), []).append(v)
    for v in crop.values():
        v.sort()
    out = []
    for h, y, age, bars, rating, r, gate, bm, pred, tier in rows:
        g = {}
        for k, v in bars.items():
            vals = crop[(y, c.age_group(h), k)]
            g[k] = grade_of((len(vals) - bisect.bisect_left(vals, v - 1e-9)) / len(vals))
        retired = int(h.retired and y == max(h.seasons))
        out.append((h.id, S(y), age, retired, bars["speed"], bars["stamina"], bars["grit"], bars["manners"], g["speed"], g["stamina"],
                    g["grit"], g["manners"], rating, tier, r[0], r[1], r[4], r[4], gate, bm, None, None, None, pred))
    db.executemany("INSERT OR REPLACE INTO seasons VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", out)
    print(f"{len(out)} horse-seasons", flush=True)
    for h in everyone:
        coat, marking = app.looks(h)
        titles = [f"Year {y} {div}" for y, d in sk.CHAMPIONS.items() for div, n in d.items() if n == h.name]
        led = getattr(h, "seasons", None) or {}
        last = S(max(led)) if led else S(now - h.age)
        db.execute("INSERT OR REPLACE INTO horses VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (h.id, h.name, h.sex, coat, marking, getattr(getattr(h, "sire", None), "id", None), getattr(getattr(h, "dam", None), "id", None),
                    S(now - h.age), int(bool(getattr(h, "foundation", False))), sim.style_of(h), getattr(h, "peak_age", None), h.starts, h.wins,
                    h.earnings, getattr(h, "best", None), json.dumps(getattr(h, "trophies", [])), json.dumps(titles), last, int(h.retired), h.age))
        for r in getattr(h, "results", []) or []:
            db.execute("INSERT INTO starts VALUES(?,?,?,?,?,?,?,?)", (h.id, r.get("day"), r.get("track"), r.get("place"), r.get("won"), r.get("fig"), None, None))
    ids = {h.name: h.id for h in everyone}
    for rid, st in c.STORIES.items():
        st = dict(st)
        if (lk := app.vlook(st.get("venue", "Harness Park"))):
            st["tlook"] = dict(zip(("p", "a", "font", "motto", "badge"), lk))
        st["matinee"] = bool(next((v.get("day") for v in c.VENUES if v["name"] == st.get("venue")), False))
        season = S(c.year_of(st.get("day", app.G["day"])))
        db.execute("INSERT OR REPLACE INTO stories VALUES(?,?,?,?,?,?,?)", (rid, st.get("day"), season, st.get("name"), st.get("purse"),
                                                                          int("-stake-" in rid), zlib.compress(json.dumps(st, default=list).encode(), 6)))
        for row in st.get("horses", []):
            if row.get("name") in ids:
                db.execute("INSERT INTO kept VALUES(?,?,?,?)", (ids[row["name"]], rid, float(st.get("purse") or 0) / max(1, row.get("place", 1)), row.get("place")))
    db.executemany("INSERT OR REPLACE INTO meta VALUES(?,?)", [("seasons_planned", str(S(now))), ("season_done", str(S(now))),
                                                             ("first_year", str(first)), ("source", os.path.basename(path)),
                                                             ("finished", time.strftime("%Y-%m-%d %H:%M"))])
    db.commit()
    print("done", db_path, "stories", len(c.STORIES), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "research", "encyclopedia", "history.db"))
