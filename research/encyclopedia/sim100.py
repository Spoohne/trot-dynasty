"""The encyclopedia run: a fresh world, no players, run season after season by the live rules (the new outcome engine, the
stakes book and the Crown, breeding, claiming), the same loop app.new_game runs for a world's past. Everything worth
reading is written to a SQLite file as it goes, so the encyclopedia page can open it while the run is still going.

  python research/encyclopedia/sim100.py [seasons=100] [db=research/encyclopedia/world100.db]

Recorded:
  horses     one row per horse (name, sex, coat, parents, foaled, style, trophies, titles, career totals), refreshed each season
  seasons    every horse at the end of every season: age, its card (Speed, Stamina, Grit, Manners bars, as the live card
             shows them), each bar's grade in its crop, rating and the live badge tier, and the season's starts, wins and purses
  stories    the races kept for replay: every stake, and each horse's three best races (wins first, by purse)
  meta       progress (season reached, horses, seconds per season)
"""
import heapq
import json
import os
import sqlite3
import sys
import time
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
import app                                                     # noqa: E402  the live card's bars (app.bar_of) and the circuit
c, e, sk, sim = app.c, app.e, app.sk, app.sim
O = c.outcome

SEASONS = int(sys.argv[1]) if len(sys.argv) > 1 else 100
DB = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "research", "encyclopedia", "world100.db")
BAR_KEYS = (("speed", "late_speed"), ("stamina", "stamina"), ("grit", "grit"), ("manners", "gait"))   # the live card (app.BARS)
KEEP = 3                                                       # races kept per horse
CHOREO_LAST = 5                                                # seasons whose every race goes through the choreographer


def tier(h):
    """The badge the live game shows (app.tier_label): cut from the horse's rated mile, the same at any age."""
    return app.tier_label(h)


def tier_live(h):
    """The badge the live game cuts from the handicapper's est (app.tier_label before ratings v2), for the comparison."""
    if h.age < 2 or c.age_group(h) not in c.GROUP_STATS:
        return None
    secs = c.mile_secs(c.peak_est(h) if h.retired else h.est)
    return next((t for cut, t in app.MILE_TIERS if secs <= cut), "D")


def grade_of(share):
    return next(g for cut, g in app.GRADE_CUT if share <= cut)


def open_db(path):
    for f in (path, path + "-wal", path + "-shm"):                # a fresh file: a stale write-ahead log would corrupt it
        if os.path.exists(f):
            os.remove(f)
    db = sqlite3.connect(path)
    db.executescript("""
      PRAGMA journal_mode=WAL;
      CREATE TABLE horses(id INTEGER PRIMARY KEY, name TEXT, sex TEXT, coat TEXT, marking TEXT, sire INTEGER, dam INTEGER,
        foaled INTEGER, foundation INTEGER, style TEXT, peak_gene INTEGER, starts INTEGER, wins INTEGER, earnings REAL,
        best REAL, trophies TEXT, titles TEXT, last_season INTEGER, retired INTEGER, last_age INTEGER);
      CREATE TABLE seasons(id INTEGER, season INTEGER, age INTEGER, retired INTEGER, speed REAL, stamina REAL, grit REAL,
        manners REAL, g_speed TEXT, g_stamina TEXT, g_grit TEXT, g_manners TEXT, rating REAL, tier TEXT, starts INTEGER,
        wins INTEGER, earnings REAL, season_earn REAL, gate REAL, best_mile REAL, fig_recent REAL, fig_peak REAL, tier_live TEXT, pred REAL,
        PRIMARY KEY(id, season));   -- gate: early speed, not on the card; best_mile: outcome.best_mile; fig_*: ratings v2 badge figures; tier_live: the est badge; pred: outcome.pred_mile
      CREATE TABLE stories(rid TEXT PRIMARY KEY, day INTEGER, season INTEGER, name TEXT, purse REAL, stake INTEGER, json BLOB);   -- zlib'd JSON
      CREATE TABLE kept(id INTEGER, rid TEXT, score REAL, place INTEGER);
      CREATE TABLE starts(id INTEGER, day INTEGER, track TEXT, place INTEGER, won REAL, fig REAL, est REAL, pred REAL);   -- every start: ratings v2 figure, live est after it, the bars' predicted mile that night
      CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
      CREATE INDEX seasons_season ON seasons(season); CREATE INDEX kept_id ON kept(id); CREATE INDEX kept_rid ON kept(rid);
    """)
    return db


class Recorder:
    def __init__(self, db):
        self.db = db
        self.best = {}                                         # horse id -> min-heap of (score, rid, place): its kept races
        self.refs = {}                                         # rid -> how many horses keep it (stakes are kept regardless)

    def store(self, rid, season):
        if self.db.execute("SELECT 1 FROM stories WHERE rid=?", (rid,)).fetchone() or rid not in c.STORIES:
            return
        st = dict(c.STORIES[rid])
        if (lk := app.vlook(st.get("venue", "Harness Park"))):
            st["tlook"] = dict(zip(("p", "a", "font", "motto", "badge"), lk))
        st["matinee"] = bool(next((v.get("day") for v in c.VENUES if v["name"] == st.get("venue")), False))
        self.db.execute("INSERT INTO stories VALUES(?,?,?,?,?,?,?)", (rid, st.get("day"), season, st.get("name"), st.get("purse"),
                                                                    int("-stake-" in rid), zlib.compress(json.dumps(st, default=list).encode(), 6)))

    def drop(self, rid):
        self.refs[rid] -= 1
        if self.refs[rid] <= 0 and "-stake-" not in rid:
            self.db.execute("DELETE FROM stories WHERE rid=?", (rid,))
            del self.refs[rid]

    def night(self, d, horses):
        """After a race night: keep tonight's stakes, and any race that's now one of a starter's three best."""
        season = d // c.YEAR
        for rid, st in list(c.STORIES.items()):
            if st.get("day") == d and "-stake-" in rid:
                self.store(rid, season)
        for h in horses:
            r = h.results[-1] if getattr(h, "results", None) else None
            if not r or r.get("day") != d or not r.get("race_id"):
                continue
            score = r.get("won", 0) or 0.0                       # what it earned in the race: a win beats a place in the same race
            if score <= 0:
                continue
            heap = self.best.setdefault(h.id, [])
            if len(heap) < KEEP or score > heap[0][0]:
                self.store(r["race_id"], season)
                self.refs[r["race_id"]] = self.refs.get(r["race_id"], 0) + 1
                if len(heap) == KEEP:
                    _, old, _ = heapq.heappop(heap)
                    self.drop(old)
                heapq.heappush(heap, (score, r["race_id"], r["place"]))

    def season_end(self, season, horses):
        """Every horse's card and season at the end of a season, graded within its crop."""
        everyone = horses + list(e.nursery)
        app.G["horses"] = horses                                      # the card reads a foal against the world's horses (app.young_bar)
        rows, crop = [], {}
        for h in everyone:
            bars = {k: app.bar_of(h, t) for k, t in BAR_KEYS}
            rating = O.rating(h)
            rows.append((h, bars, rating))
            if not h.retired and h.age >= 2:
                for k in bars:
                    crop.setdefault((c.age_group(h), k), []).append(bars[k])
        for v in crop.values():
            v.sort()
        out = []
        import bisect
        for h, bars, rating in rows:
            g = {}
            for k, b in bars.items():
                vals = crop.get((c.age_group(h), k)) if not h.retired and h.age >= 2 else None
                g[k] = grade_of((len(vals) - bisect.bisect_left(vals, b - 1e-9)) / len(vals)) if vals else None
            out.append((h.id, season, h.age, int(h.retired), bars["speed"], bars["stamina"], bars["grit"], bars["manners"],
                        g["speed"], g["stamina"], g["grit"], g["manners"], rating, tier(h) if h.age >= 2 else None,
                        h.starts, h.wins, h.earnings, getattr(h, "earnings", 0) - getattr(h, "season0", 0), app.bar_of(h, "early_speed"),
                        O.best_mile(O.bars(h, h.developed)), app.badge_secs(h), app.badge_secs(h, "peak"), tier_live(h),
                        O.pred_mile(O.bars(h, h.developed))))
            self.horse_row(h, season)
        self.db.executemany("INSERT OR REPLACE INTO seasons VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", out)
        for hid, heap in self.best.items():
            self.db.execute("DELETE FROM kept WHERE id=?", (hid,))
            self.db.executemany("INSERT INTO kept VALUES(?,?,?,?)", [(hid, rid, s, pl) for s, rid, pl in heap])

    def horse_row(self, h, season):
        coat, marking = app.looks(h)
        titles = [f"Year {y} {div}" for y, d in sk.CHAMPIONS.items() for div, n in d.items() if n == h.name]
        foaled = getattr(h, "foaled_season", None)
        if foaled is None:
            foaled = h.foaled_season = season - h.age
        self.db.execute("INSERT OR REPLACE INTO horses VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (h.id, h.name, h.sex, coat, marking, getattr(getattr(h, "sire", None), "id", None), getattr(getattr(h, "dam", None), "id", None),
                         foaled, int(bool(getattr(h, "foundation", False))), sim.style_of(h), getattr(h, "peak_age", None), h.starts, h.wins,
                         h.earnings, getattr(h, "best", None), json.dumps(getattr(h, "trophies", [])), json.dumps(titles), season, int(h.retired), h.age))


def main():
    db = open_db(DB)
    rec = Recorder(db)
    starts, record = [], c.record_result
    def logged(h, name, track, place, purse, field_est, size=None):          # every start, for replaying badge windows offline
        record(h, name, track, place, purse, field_est, size)
        r = h.results[-1]
        starts.append((h.id, r["day"], track, r["place"], r["won"], r["fig"], h.est, O.pred_mile(O.bars(h, h.developed))))
    c.record_result = logged
    c.HUMAN.clear(); c.STORIES.clear(); c.RECORDS.clear(); sk.CHAMPIONS.clear(); sk.HALL.clear(); sk.RATINGS.clear(); app._names.USED.clear()
    e.ROLLED[0] = None; c.EPOCH[0] = 0                          # Year 0 is the first season, so trophies read "Year 37 ..." = season 37
    horses = e.world(barns=app.BARNS)
    ai = set(range(app.BARNS))
    for h in horses:
        h.foundation = True
    sk.new_calendar()
    t0 = time.time()
    db.execute("INSERT OR REPLACE INTO meta VALUES('seasons_planned', ?)", (str(SEASONS),))
    for d in range(SEASONS * c.YEAR):
        c.DAY[0] = d
        if d % c.YEAR == 0 and d:
            rec.season_end(d // c.YEAR - 1, horses)               # the season just finished, before the year turns
            db.executemany("INSERT INTO starts VALUES(?,?,?,?,?,?,?,?)", starts); starts.clear()
            sk.year_tick(horses, ai, d)
            done = d // c.YEAR
            db.execute("INSERT OR REPLACE INTO meta VALUES('season_done', ?)", (str(done),))
            db.execute("INSERT OR REPLACE INTO meta VALUES('secs_per_season', ?)", (f"{(time.time() - t0) / done:.1f}",))
            db.commit()
            print(f"season {done}/{SEASONS}: {len(horses)} horses, {(time.time() - t0) / done:.1f} s a season", flush=True)
        sk.ai_nominate(horses, ai, d)
        c._story.CHOREO = True                                   # the choreographer (positions from a run of the decided result, the
        sk.run_today(d, horses)                                  # replay hops) is slow: every stake, and every race in the last seasons
        c._story.CHOREO = d >= (SEASONS - CHOREO_LAST) * c.YEAR
        horses = e.day(d, horses, ai, [])
        rec.night(d, horses)
        for h in horses:
            if getattr(h, "order", None) == "stakes":
                h.order = None
    rec.season_end(SEASONS - 1, horses)
    db.executemany("INSERT INTO starts VALUES(?,?,?,?,?,?,?,?)", starts)
    db.execute("INSERT OR REPLACE INTO meta VALUES('season_done', ?)", (str(SEASONS),))
    db.execute("INSERT OR REPLACE INTO meta VALUES('finished', ?)", (time.strftime("%Y-%m-%d %H:%M"),))
    db.commit()
    print("done", DB, flush=True)


if __name__ == "__main__":
    main()
