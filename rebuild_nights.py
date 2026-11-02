"""Rebuild race nights run before the speed limit and the story fixes of 2026-11-02 (Patrick approved, for days 2626-2627).

For every race on the given days: the winner, the order and the purses stay exactly as run. Each beaten horse's time is
re-read under the speed limit (outcome.LUCK: no faster than its own rating's time less a second; a visitor, gone from the
save, keeps its time), at least a nose behind the one ahead; margins
follow from the times. The race's story is rebuilt by today's story.py (no first-over move at the quarter, stretch passes
judged where the passed horse was). Horses' results, best times, season bests and last-start lines follow. Track records
don't move: they are the winners' splits, and no winner's time changes.

  python rebuild_nights.py <save.pkl> 2626 2627        writes the save in place (back it up first)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); os.chdir(HERE)
import app                                                     # noqa: E402

c, e, sk, sim = app.c, app.e, app.sk, app.sim
O, story = c.outcome, c._story
SEC = O.SEC_PER_LENGTH


class Stub:
    """A runner as the story builder needs it, from the saved story row (and the live horse, when it's still in the save)."""
    def __init__(self, row, live, time, margin):
        self.id = live.id if live else -abs(hash(row["name"])) % 10 ** 9
        self.name, self.post, self.trip = row["name"], row["post"], row["trip"]
        self.last_time, self.margin_l = time, margin
        self.coat, self.marking = row.get("coat", "bay"), row.get("marking", "none")
        self.style = sim.style_of(live) if live else "stalk"
        self._cur = {"early_speed": row["early"], "stamina": row["stamina"]}

    def current(self, track="mile"):
        return self._cur


def limit(row, live, track):
    """The fastest this runner could have gone, in display seconds, under the live speed limit."""
    if not live:                                               # a visitor is gone from the save: its time stands, save for the order
        return float("-inf")
    keep, live.freshness = live.freshness, 100.0               # its form on a race night, not how tired it is today
    try:
        b = O.bars(live, live.current(track))
    finally:
        live.freshness = keep
    rating = sum(O.RATE_W[k] * b[k] for k in O.RATE_W)
    return O.TIME_FIT[0] + O.TIME_FIT[1] * rating + (sim.HALF_SLOWER if track == "half" else 0) - O.LUCK


def rebuild(rid, st, by_name, retime=True):
    rows = sorted(st["horses"], key=lambda r: r["place"])
    win = rows[0]["time"]
    times, prev, prev0 = [], None, None
    for r in rows:                                             # pushed back by the limit, it carries the delay to those behind: they keep their gaps
        t = r["time"] if prev is None or not retime else max(r["time"], limit(r, by_name.get(r["name"]), st["track"]), prev + max(O.NOSE * SEC, r["time"] - prev0))
        times.append(t); prev, prev0 = t, r["time"]
    order = [Stub(r, by_name.get(r["name"]), t, (t - win) / SEC) for r, t in zip(rows, times)]
    new = story.build(order, st["track"], passing=st.get("passing", False))
    old_rows = {r["name"]: r for r in st["horses"]}
    for r in new["horses"]:
        for k, v in old_rows[r["name"]].items():
            r.setdefault(k, v)                                 # odds, driver, silks: as they were on the night
    c.STORIES[rid] = dict(new, **{k: st[k] for k in ("id", "name", "purse", "day", "venue", "passing", "records", "sponsor") if k in st})
    changed = []
    for r, t in zip(rows, times):
        h = by_name.get(r["name"])
        if abs(t - r["time"]) < 1e-9 or not h:
            continue
        changed.append((r["name"], r["time"], t))
        old = r["time"]
        for res in getattr(h, "results", []):
            if res.get("race_id") == rid:
                res["time"] = t
        if getattr(h, "best", 999) == old:                     # this race was its best: its best is now its next fastest
            h.best = min(x["time"] for x in h.results if "time" in x)
        yr = c.year_of(st["day"])
        led = getattr(h, "seasons", {}).get(yr)
        if led and led[5] == old:
            led[5] = min(x["time"] for x in h.results if "time" in x and c.year_of(x["day"]) == yr)
        if isinstance(getattr(h, "last", None), tuple) and h.results and h.results[-1].get("race_id") == rid:
            h.last = h.last[:3] + (t,) + h.last[4:]
    return changed


def main(path, days):
    app.save = lambda *a, **k: None; app.snapshot = lambda *a, **k: None
    app.load(path)
    everyone = c.lineage(app.G["horses"] + list(e.nursery) + sk.HALL)
    by_name = {h.name: h for h in everyone}
    races = [(rid, st) for rid, st in list(c.STORIES.items()) if st.get("day") in days]
    moved = 0
    for rid, st in races:
        ch = rebuild(rid, st, by_name)
        moved += len(ch)
        if rid == "2627-ls-mile-Open-0":
            print(rid, [(n, c.mile_time(a), c.mile_time(b)) for n, a, b in ch])
    app.SAVE = path; app.DIRTY[0] = True; app.flush()
    print(f"rebuilt {len(races)} races on days {sorted(days)}; {moved} beaten runners re-timed; saved {path}")


if __name__ == "__main__":
    main(sys.argv[1], {int(d) for d in sys.argv[2:]})
