"""One race from the Gallop world, run again with every frame recorded and written as a story the game's replay viewer
plays (mockups/race.js: lengths behind the leader and lane at each call). The field is a race's own horses at the age
they ran; the race itself is a fresh run, since the sim's dice aren't kept.

  python research/encyclopedia/gallop_replay.py [season week race]     default: the fastest mile in the world file

Writes research/encyclopedia/gallop_races/<rid>.json; serve.py plays it at /replay/<rid>.
"""
import json
import os
import sqlite3
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import gallop                                                    # noqa: E402
from gallop100 import AGE_K                                      # noqa: E402

DB = os.path.join(HERE, "gallop100.db")

LENGTH = 2.44            # metres: a length is 8 ft in the viewer
LANE = 0.65              # metres: the sim's lane step; the viewer draws a lane as a sulky's width
CALL_S = 2.0             # seconds between calls in the story
QUARTER = gallop.MILE / 4


def fmt(t):
    return f"{int(t // 60)}:{t % 60:04.1f}" if t >= 60 else f":{t:04.1f}"


def main():
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    if len(sys.argv) > 3:
        key = tuple(int(x) for x in sys.argv[1:4])
    else:
        key = db.execute("SELECT season, week, race FROM races ORDER BY win_time LIMIT 1").fetchone()
    rows = db.execute("SELECT h.*, s.post, s.age FROM starts s JOIN horses h ON h.id = s.id WHERE s.season=? AND s.week=? AND s.race=? ORDER BY s.post", key).fetchall()
    cols = [d[0] for d in db.execute("SELECT * FROM horses LIMIT 0").description] + ["post", "age"]
    horses = [dict(zip(cols, r)) for r in rows]
    purse = db.execute("SELECT purse FROM races WHERE season=? AND week=? AND race=?", key).fetchone()[0]
    stats = np.array([[h[k] for k in gallop.STATS] for h in horses], float) * np.array([[AGE_K[h["age"]]] for h in horses])
    place, times, blocked, frames = gallop.run(stats, rng=np.random.default_rng(key[0] * 10000 + key[1] * 100 + key[2]), record=True)
    scale = gallop.CFG["clock_scale"] / gallop.FPS                 # a frame, in the trotter's clock
    prog, lat = frames[..., 0], frames[..., 1]
    lead = prog.max(1)
    final = float(times.min())
    calls = [round(t, 3) for t in np.arange(0, final, CALL_S)] + [round(final, 3)]
    at = lambda t: min(len(frames) - 1, int(round(t / scale)))
    quarters = [0.0] + [round(float(np.argmax(lead >= q * QUARTER) * scale), 1) for q in (1, 2, 3)] + [round(final, 1)]
    win = int(np.argmin(times))
    out = []
    for i, h in enumerate(horses):
        out.append({"name": h["name"], "post": h["post"], "place": int(place[i]), "time": round(float(times[i]), 2),
                    "behind": [round(float((lead[at(t)] - prog[at(t), i]) / LENGTH), 2) for t in calls],
                    "lane": [round(float(max(0.0, (lat[at(t), i] - LANE) / LANE)), 2) for t in calls],
                    "trip": f"post {h['post']}, rank {h['rank']}, blocked {blocked[i] / gallop.FPS * gallop.CFG['clock_scale']:.1f} s",
                    "coat": "bay", "rank": h["rank"]})
    out.sort(key=lambda h: h["place"])
    caps = [[0.0, "They're away"], [quarters[1], f"Quarter in {fmt(quarters[1])}"], [quarters[2], f"Half in {fmt(quarters[2])}"],
            [quarters[3], f"Three-quarters in {fmt(quarters[3])}"], [final, f"{horses[win]['name']} wins it in {fmt(final)}"]]
    rid = f"gallop-{key[0]}-{key[1]}-{key[2]}"
    story = {"id": rid, "track": "mile", "name": f"Gallop model · season {key[0]} week {key[1]} race {key[2] + 1}", "purse": round(purse),
             "venue": "Harness Park", "day": key[0] * 52 + key[1], "passing": False, "matinee": False,
             "calls": calls, "quarters": quarters, "final": round(final, 2), "horses": out, "captions": caps}
    os.makedirs(os.path.join(HERE, "gallop_races"), exist_ok=True)
    path = os.path.join(HERE, "gallop_races", rid + ".json")
    json.dump(story, open(path, "w"), separators=(",", ":"))
    print(f"{path}: {len(calls)} calls, winner {horses[win]['name']} ({horses[win]['rank']}) in {fmt(final)}, quarters {quarters}")
    print("replay: http://127.0.0.1:8119/replay/" + rid)


if __name__ == "__main__":
    main()
