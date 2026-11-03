"""One-off (2026-11-03): the clock moved sim.CLOCK_SHIFT slower so the fastest possible mile is 1:45.5. Every saved time
(results, bests, season bests, course records, replays, form lines) moves with it. Run with the server stopped; it backs
the save up first. Idempotent: refuses to run twice (G["clock_v"] == 4).
    python retime_v3.py [save.pkl]"""
import shutil
import sys

import app
import retime_v2
import sim


def convert(G):
    assert G.get("clock_v") == 3, "needs a save on the honest clock (clock_v 3)"
    keep, sim.squeeze = sim.squeeze, (lambda x, half=False: x + sim.CLOCK_SHIFT)   # retime_v2 walks every time through sim.squeeze
    G["clock_v"] = 2
    try:
        n = retime_v2.convert(G)
    finally:
        sim.squeeze = keep
    G["clock_v"] = 4
    return n


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else app.SAVE
    shutil.copy(path, path.replace(".pkl", ".before-clock-shift.pkl"))
    app.load(path)
    n = convert(app.G)
    app.SAVE = path
    app.save(); app.flush()
    print(f"moved {n} results {sim.CLOCK_SHIFT} s slower; saved {path}")
