"""One race from the Gallop world, run again with every frame recorded and written as a story the game's replay viewer
plays (mockups/race.js: lengths behind the leader and lane at each call). The field is a race's own horses at the age
they ran; the race itself is a fresh run, since the sim's dice aren't kept.

  python research/encyclopedia/gallop_replay.py [season week race]     default: the fastest mile in the world file
  python research/encyclopedia/gallop_replay.py sample [each=3]        that many random races from each of the five class levels

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
import replay_check                                              # noqa: E402
from gallop100 import AGE_K                                      # noqa: E402

DB = os.path.join(HERE, "gallop100.db")

LENGTH = gallop.CFG["body_m"] / replay_check.BODY   # metres a drawn length: the sim's following distance is drawn as the viewer's horse and sulky, nose to tail
LANE = 0.65              # metres: the sim's lane step; the viewer draws a lane as a sulky's width
LEVELS = {0: "Bottom class", 1: "Low class", 2: "Middle class", 3: "High class", 4: "Top class"}
CALL_S = 0.5             # seconds between calls in the story: fine enough that interpolation never draws one horse through another
QUARTER = gallop.MILE / 4


def fmt(t):
    return f"{int(t // 60)}:{t % 60:04.1f}" if t >= 60 else f":{t:04.1f}"


def level_of(db, key):
    """Where a race sits on its night's card, which runs in class order: 0 the bottom fifth .. 4 the top."""
    n = db.execute("SELECT COUNT(*) FROM races WHERE season=? AND week=?", key[:2]).fetchone()[0]
    return min(4, key[2] * 5 // n)


def main():
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    if sys.argv[1:2] == ["sample"]:
        rng = np.random.default_rng(int(sys.argv[3]) if len(sys.argv) > 3 else 7)
        each = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        got = {i: 0 for i in LEVELS}
        while min(got.values()) < each:
            key = (int(rng.integers(1, 100)), int(rng.integers(52)), 0)
            n = db.execute("SELECT COUNT(*) FROM races WHERE season=? AND week=?", key[:2]).fetchone()[0]
            key = (key[0], key[1], int(rng.integers(n)))
            if got[level_of(db, key)] < each:
                got[level_of(db, key)] += 1
                record(db, key)
    elif len(sys.argv) > 3:
        record(db, tuple(int(x) for x in sys.argv[1:4]))
    else:
        record(db, db.execute("SELECT season, week, race FROM races ORDER BY win_time LIMIT 1").fetchone())


def record(db, key):
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
    # the last call is the wire: where each horse was as the winner crossed, kept in finishing order (a horse that passes
    # another after the winner is home is drawn a nose ahead of it, not behind it)
    wire = (lead[at(final)] - prog[at(final)]) / LENGTH
    for i in np.argsort(place):
        ahead = place == place[i] - 1
        if ahead.any():
            wire[i] = max(wire[i], wire[ahead][0] + 0.05)
    out = []
    for i, h in enumerate(horses):
        out.append({"name": h["name"], "post": h["post"], "place": int(place[i]), "time": round(float(times[i]), 2),
                    "behind": [round(float((lead[at(t)] - prog[at(t), i]) / LENGTH), 2) for t in calls[:-1]] + [round(float(wire[i]), 2)],
                    "lane": [round(float(lat[at(t), i] / LANE), 2) for t in calls],
                    "trip": f"post {h['post']}, rank {h['rank']}, blocked {blocked[i] / gallop.FPS * gallop.CFG['clock_scale']:.1f} s",
                    "coat": "bay", "rank": h["rank"]})
    out.sort(key=lambda h: h["place"])
    caps = [[0.0, "They're away"], [quarters[1], f"Quarter in {fmt(quarters[1])}"], [quarters[2], f"Half in {fmt(quarters[2])}"],
            [quarters[3], f"Three-quarters in {fmt(quarters[3])}"], [final, f"{horses[win]['name']} wins it in {fmt(final)}"]]
    rid = f"gallop-{key[0]}-{key[1]}-{key[2]}"
    story = {"id": rid, "track": "mile", "name": LEVELS[level_of(db, key)], "level": level_of(db, key), "season": key[0], "week": key[1], "purse": round(purse),
             "venue": "Harness Park", "day": key[0] * 52 + key[1], "passing": False, "matinee": False, "sim": True,
             "calls": calls, "marks": [0.0, round(quarters[1] * 0.45, 2), *quarters[1:4], round(final - 12.5, 2), round(final, 2)], "quarters": quarters, "final": round(final, 2), "horses": out, "captions": caps}
    story = replay_check.guard(story)                                   # never saved broken: clean, repaired, or single file
    os.makedirs(os.path.join(HERE, "gallop_races"), exist_ok=True)
    path = os.path.join(HERE, "gallop_races", rid + ".json")
    json.dump(story, open(path, "w"), separators=(",", ":"))
    print(f"{path}: {story['guard']}, {len(calls)} calls, winner {horses[win]['name']} ({horses[win]['rank']}) in {fmt(final)}, quarters {quarters}")
    print("replay: http://127.0.0.1:8119/replay/" + rid)


if __name__ == "__main__":
    main()
