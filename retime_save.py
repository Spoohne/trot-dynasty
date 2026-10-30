"""One-off, 2026-10-27: move every saved race time from the old clock to the new one (sim.retime), so results, bests,
course records, replays and form lines read on the same scale as new races. Run with the server stopped; it backs
the save up first. Idempotent guard: refuses to run twice (G["clock_v"])."""
import re
import shutil

import app
import sim

c, sk = app.c, app.sk
shutil.copy(app.SAVE, app.SAVE.replace("save.pkl", "save.before-clock.pkl"))
app.load()
assert app.G.get("clock_v", 1) < 2, "already converted"

half_of = {v["id"]: v["track"] == "half" for v in c.VENUES} | {"half": True, "mile": False}
rt = lambda x, half=False: round(sim.retime(x, half), 2)
TIME = re.compile(r"(\d):(\d\d\.\d)")


def scaled(qs, half):
    """Cumulative quarter times: the last one onto the new clock, the splits scaled with it."""
    if not qs:
        return qs
    k = sim.retime(qs[-1], half) / qs[-1]
    return [round(q * k, 2) for q in qs]


n_res = 0
for h in c.lineage(app.G["horses"] + app.e.nursery + sk.HALL):
    res = getattr(h, "results", [])
    for r in res:
        r["time"] = rt(r["time"], r.get("track") == "half"); n_res += 1
    mile = [r["time"] for r in res if r.get("track") != "half"]
    if getattr(h, "best", 999) < 999:
        h.best = min(mile) if mile else rt(h.best)
    if getattr(h, "last_time", None):
        h.last_time = res[-1]["time"] if res else rt(h.last_time)
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
    k = sim.retime(st["final"], half) / st["final"]
    st["final"] = round(st["final"] * k, 2)
    st["quarters"] = [round(q * k, 2) for q in st["quarters"]]
    st["calls"] = [q * k for q in st["calls"]]
    QT = re.compile(r"(\d)?:(\d\d\.\d)")                     # split and final times in the captions: scaled with the race
    sc = lambda m: (lambda v: c.mile_time(v) if v >= 60 else f":{v:04.1f}")(round((int(m[1] or 0) * 60 + float(m[2])) * k * 5) / 5)
    st["captions"] = [[t * k, QT.sub(sc, txt)] for t, txt in st.get("captions", [])]
    for r in st["horses"]:
        r["time"] = rt(r["time"], half)
    if st.get("records"):
        st["records"] = scaled(st["records"], half)

app.G["clock_v"] = 2
app.save(); app.flush()
print("converted", n_res, "results,", len(c.RECORDS), "course records,", len(c.STORIES), "replays")
