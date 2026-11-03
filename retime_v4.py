"""One-off (2026-11-03, the trips cut to variety): the clock shift went from 2.4 s back to 0, which moves every NEW figure
2.4 s faster; the figures already stored on results (the letter rests on them) move with it. Times stay: a time is what
the horse ran that night. Run with the server stopped; backs the save up first. Idempotent (clock_v 5).
    python retime_v4.py [save.pkl]"""
import shutil
import sys

import app

DELTA = -2.4


def convert(G):
    assert G.get("clock_v") == 4, "needs a save on the shifted clock (clock_v 4)"
    n = 0
    for h in app.c.lineage(G["horses"] + app.e.nursery + app.sk.HALL):
        for r in getattr(h, "results", []) or []:
            if r.get("fig") is not None:
                r["fig"] = round(r["fig"] + DELTA, 2); n += 1
    G["clock_v"] = 5
    return n


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else app.SAVE
    shutil.copy(path, path.replace(".pkl", ".before-trips.pkl"))
    app.load(path)
    n = convert(app.G)
    app.SAVE = path
    app.save(); app.flush()
    print(f"moved {n} figures {DELTA} s; saved {path}")
