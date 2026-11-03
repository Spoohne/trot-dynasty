"""One-off (ratings v2, the honest clock): move every saved race time from the 2026-10-27 clock onto the honest one
(sim.squeeze), so results, bests, course records, replays and form lines read on the same scale as new races.
Run with the server stopped; it backs the save up first. Idempotent: refuses to run twice (G["clock_v"] == 3).
    python retime_v2.py [save.pkl]          (defaults to the game's save; writes it back)"""
import re
import shutil
import sys

import app
import sim

c, sk = app.c, app.sk


def convert(G):
    """Every time in a loaded world onto the honest clock. Returns how many results were moved."""
    assert G.get("clock_v", 2) < 3, "already on the honest clock"
    half_of = {v["id"]: v["track"] == "half" for v in c.VENUES} | {"half": True, "mile": False}
    rt = lambda x, half=False: round(sim.squeeze(x, half), 2)
    TIME = re.compile(r"(\d):(\d\d\.\d)")

    def scaled(qs, half):
        if not qs:
            return qs
        k = sim.squeeze(qs[-1], half) / qs[-1]
        return [round(q * k, 2) for q in qs]

    n = 0
    for h in c.lineage(G["horses"] + app.e.nursery + sk.HALL):
        res = getattr(h, "results", [])
        for r in res:
            r["time"] = rt(r["time"], r.get("track") == "half"); n += 1
            if r.get("fig") is not None:
                r["fig"] = rt(r["fig"])
        mile = [r["time"] for r in res if r.get("track") != "half"]
        if getattr(h, "best", 999) < 999:
            h.best = min(mile) if mile else rt(h.best)
        if getattr(h, "last_time", None):
            h.last_time = res[-1]["time"] if res else rt(h.last_time)
        if getattr(h, "raw_time", None):
            h.raw_time = h.last_time
        for y, row in (getattr(h, "seasons", None) or {}).items():
            if row[5] < 999:
                ys = [r["time"] for r in res if c.year_of(r["day"]) == y and r.get("track") != "half"]
                row[5] = min(ys) if ys else rt(row[5])
        if getattr(h, "form", None):
            h.form = [TIME.sub(lambda m: c.mile_time(rt(int(m[1]) * 60 + float(m[2]), " half" in f.split(":")[0])), f) for f in h.form]
    for k_, qs in c.RECORDS.items():
        c.RECORDS[k_] = scaled(qs, half_of.get(k_, False))
    for st in c.STORIES.values():
        half = st.get("track") == "half"
        k = sim.squeeze(st["final"], half) / st["final"]
        st["final"] = round(st["final"] * k, 2)
        st["quarters"] = [round(q * k, 2) for q in st["quarters"]]
        st["calls"] = [q * k for q in st["calls"]]
        QT = re.compile(r"(\d)?:(\d\d\.\d)")
        sc = lambda m: (lambda v: c.mile_time(v) if v >= 60 else f":{v:04.1f}")(round((int(m[1] or 0) * 60 + float(m[2])) * k * 5) / 5)
        st["captions"] = [[t * k, QT.sub(sc, txt)] for t, txt in st.get("captions", [])]
        for r in st["horses"]:
            r["time"] = rt(r["time"], half)
            if r.get("broke_at") is not None:
                r["broke_at"] = round(r["broke_at"] * k, 1)
        if st.get("records"):
            st["records"] = scaled(st["records"], half)
    G["clock_v"] = 3
    return n


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else app.SAVE
    shutil.copy(path, path.replace(".pkl", ".before-honest-clock.pkl"))
    app.load(path)
    n = convert(app.G)
    app.SAVE = path
    app.save(); app.flush()
    print(f"moved {n} results onto the honest clock; saved {path}")
