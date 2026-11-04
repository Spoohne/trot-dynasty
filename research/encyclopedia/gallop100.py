"""The encyclopedia run on the Gallop Racer model (gallop.py): a world of ten-stat horses raced season after season at
one mile, the circuit's shape (about 900 in training, fields of ten, nearly every horse out every week, 52 weeks a year,
new two-year-olds in as the old retire), no players, no breeding. Written to SQLite as it goes.

  python research/encyclopedia/gallop100.py [seasons=100] [db=research/encyclopedia/gallop100.db]

Tables: horses (ten stats, rank letter, career), starts (every start), races (every race), meta (progress).
Then `python research/encyclopedia/gallop_report.py` builds the page.
"""
import os
import sqlite3
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import gallop                                                    # noqa: E402
try:
    import names                                                 # noqa: E402  the game's own names
    make_name = lambda rng, sex: names.make(sex=sex)
except Exception:                                                # noqa: BLE001
    make_name = lambda rng, sex: f"Horse {rng.integers(10**6)}"

SEASONS = int(sys.argv[1]) if len(sys.argv) > 1 else 100
DB = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "research", "encyclopedia", "gallop100.db")
HERD = 900                 # in training (app.BARNS 90 x 10)
FIELD = 10                 # circuit.FIELD["mile"]
WEEKS = 52                 # circuit.YEAR
RACE_P = 0.9               # a horse's chance to be out on a given week (the live world: 47 starts in 52 weeks)
STAT_MEAN, STAT_SD, CLASS_SD = 60, 11, 9     # a stat = mean + class*N(0,1) shared by all ten + its own N(0,1)
AGE_K = {2: 0.92, 3: 0.97, 4: 1.0, 5: 1.0, 6: 1.0, 7: 0.98, 8: 0.95, 9: 0.91, 10: 0.86}   # what a horse shows of its stats at an age
RETIRE = (6, 7, 8, 9, 10)                    # the age a horse retires after, drawn with
RETIRE_P = (0.15, 0.3, 0.3, 0.15, 0.1)
PURSE_SHARE = (0.5, 0.25, 0.12, 0.08, 0.05)
CLASS_EMA = 0.2            # the class figure fields are made from: a running mean of (field - place)/(field - 1)


def open_db(path):
    for f in (path, path + "-wal", path + "-shm"):
        if os.path.exists(f):
            os.remove(f)
    db = sqlite3.connect(path)
    db.executescript("""
      PRAGMA journal_mode=WAL;
      CREATE TABLE horses(id INTEGER PRIMARY KEY, name TEXT, sex TEXT, foaled INTEGER, retired INTEGER, rank TEXT,
        speed INTEGER, staying INTEGER, stamina INTEGER, breaking INTEGER, response INTEGER, fierce INTEGER, tenacity INTEGER,
        power INTEGER, courage INTEGER, feel INTEGER, starts INTEGER, wins INTEGER, places INTEGER, earnings REAL, best REAL);
      CREATE TABLE starts(id INTEGER, season INTEGER, week INTEGER, race INTEGER, post INTEGER, place INTEGER, time REAL,
        blocked INTEGER, won REAL, age INTEGER);
      CREATE TABLE races(season INTEGER, week INTEGER, race INTEGER, class REAL, purse REAL, win_time REAL, margin REAL,
        PRIMARY KEY(season, week, race));
      CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
      CREATE INDEX starts_id ON starts(id); CREATE INDEX starts_season ON starts(season);
    """)
    return db


class Herd:
    def __init__(self, rng):
        self.rng = rng
        self.next_id = 1
        self.cols = {k: [] for k in ("id", "name", "sex", "foaled", "retire_age", "stats", "age", "cls", "starts", "wins", "places", "earn", "best")}
        self.rows = []                                           # live horses, dicts

    def foal(self, season, age=2):
        r = self.rng
        q = r.normal()
        stats = np.clip(np.rint(STAT_MEAN + CLASS_SD * q + STAT_SD * r.normal(size=10)), 1, 99)
        sex = "f" if r.random() < 0.5 else "m"
        h = dict(id=self.next_id, name=make_name(r, sex), sex=sex, foaled=season - age, age=age, stats=stats,
                 retire_age=int(r.choice(RETIRE, p=RETIRE_P)), cls=0.5, starts=0, wins=0, places=0, earn=0.0, best=None, retired=None)
        self.next_id += 1
        self.rows.append(h)
        return h


def main():
    rng = np.random.default_rng(100)
    db = open_db(DB)
    herd = Herd(rng)
    for _ in range(HERD):                                        # the founding herd, aged 2..6
        h = herd.foal(0, age=int(rng.integers(2, 7)))
    t0 = time.time()
    db.execute("INSERT INTO meta VALUES('seasons_planned', ?)", (str(SEASONS),))
    for season in range(SEASONS):
        for week in range(WEEKS):
            live = [h for h in herd.rows if rng.random() < RACE_P]
            live.sort(key=lambda h: h["cls"])
            n_races = len(live) // FIELD
            off = int(rng.integers(0, len(live) - n_races * FIELD + 1))
            live = live[off:off + n_races * FIELD]
            fields = [live[i * FIELD:(i + 1) * FIELD] for i in range(n_races)]
            for f in fields:
                rng.shuffle(f)                                   # the post draw
            stats = np.array([[h["stats"] * AGE_K[h["age"]] for h in f] for f in fields])
            place, times, blocked = gallop.run(stats, rng=rng)
            srows, rrows = [], []
            for ri, f in enumerate(fields):
                cls = float(np.mean([h["cls"] for h in f]))
                purse = 10000 * (1 + 2 * cls)
                ts = np.sort(times[ri])
                rrows.append((season, week, ri, cls, purse, float(ts[0]), float(ts[1] - ts[0])))
                for post, h in enumerate(f, 1):
                    p = int(place[ri][post - 1]); t = float(times[ri][post - 1])
                    won = purse * PURSE_SHARE[p - 1] if p <= 5 else 0.0
                    h["starts"] += 1; h["wins"] += p == 1; h["places"] += p <= 3; h["earn"] += won
                    h["best"] = t if h["best"] is None or t < h["best"] else h["best"]
                    h["cls"] += CLASS_EMA * ((FIELD - p) / (FIELD - 1) - h["cls"])
                    srows.append((h["id"], season, week, ri, post, p, t, int(blocked[ri][post - 1]), won, h["age"]))
            db.executemany("INSERT INTO starts VALUES(?,?,?,?,?,?,?,?,?,?)", srows)
            db.executemany("INSERT INTO races VALUES(?,?,?,?,?,?,?)", rrows)
        # the year turns: retirements, the new crop, every horse's row refreshed
        for h in herd.rows:
            if h["age"] >= h["retire_age"]:
                h["retired"] = season
        for h in list(herd.rows):
            db.execute("INSERT OR REPLACE INTO horses VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (h["id"], h["name"], h["sex"], h["foaled"], h["retired"], str(gallop.rank(h["stats"])), *[int(x) for x in h["stats"]],
                        h["starts"], h["wins"], h["places"], h["earn"], h["best"]))
            if h["retired"] is not None:
                herd.rows.remove(h)
            else:
                h["age"] += 1
        while len(herd.rows) < HERD:
            herd.foal(season + 1)
        db.execute("INSERT OR REPLACE INTO meta VALUES('season_done', ?)", (str(season + 1),))
        db.execute("INSERT OR REPLACE INTO meta VALUES('secs_per_season', ?)", (f"{(time.time() - t0) / (season + 1):.1f}",))
        db.commit()
        print(f"season {season + 1}/{SEASONS}: {len(herd.rows)} horses, {(time.time() - t0) / (season + 1):.1f} s a season", flush=True)
    db.execute("INSERT OR REPLACE INTO meta VALUES('finished', ?)", (time.strftime("%Y-%m-%d %H:%M"),))
    db.commit()


if __name__ == "__main__":
    main()
