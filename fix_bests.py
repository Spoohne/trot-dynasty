"""One-off, 2026-10-28: repair best times after the clock change. retime_save.py rebuilt each horse's best (and season
bests) from the results it still keeps, which for an aged horse is only its last 30 starts, so champions showed their
slow late-career times. Here every best is taken from the pre-change save (save.before-clock.pkl), put through the same
clock conversion, and kept if it's faster than what the horse has run since. Run with the server stopped."""
import pickle
import shutil

import app
import sim

c, sk = app.c, app.sk
shutil.copy(app.SAVE, app.SAVE.replace("save.pkl", "save.before-bestfix.pkl"))
old = pickle.load(open(app.SAVE.replace("save.pkl", "save.before-clock.pkl"), "rb"))
app.load()
assert not app.G.get("bests_fixed"), "already fixed"
was = {h.id: h for h in c.lineage(old["G"]["horses"] + old.get("nursery", []) + old["hall"])}
fixed = 0
for h in c.lineage(app.G["horses"] + app.e.nursery + sk.HALL):
    o = was.get(h.id)
    if not o:
        continue                                                          # born since the change: its times are all new-clock
    if getattr(o, "best", 999) < 999:
        true = round(sim.retime(o.best), 2)
        if true < getattr(h, "best", 999):
            h.best = true; fixed += 1
    for y, row in (getattr(o, "seasons", None) or {}).items():
        mine = (getattr(h, "seasons", None) or {}).get(y)
        if mine and row[5] < 999:
            mine[5] = min(mine[5], round(sim.retime(row[5]), 2))
app.G["bests_fixed"] = True
app.save(); app.flush()
print("best times repaired:", fixed)
