"""One-off (2026-11-03, Patrick: "Send patfrio's barn 3 killer S+ horses"): copies of the world's three best racers for
a player's barn, the admin page's clone gift with fresh names. Run with the server stopped; backs the save up first.
    python gift3.py <barn id> [save.pkl]"""
import copy
import shutil
import sys

import app
import names as _names

BEST = ("Northern Star", "Crimson Ivy", "Fable Mustang")


def clone(ref, o):
    h = copy.copy(ref)
    for k, v in list(vars(ref).items()):                   # own copies of every dict/list so the two never share state
        if isinstance(v, (dict, list, set)) and k not in ("sire", "dam"):
            setattr(h, k, copy.deepcopy(v))
    h.id = max(x.id for x in app.G["horses"] + list(app.e.nursery)) + 1
    h.name = _names.make(ref.sire, ref.dam, ref.sex)
    h.results, h.trophies, h.seasons, h.history = [], [], {}, []
    h.starts = h.wins = h.earnings = h.costs = 0; h.places = h.shows = 0; h.last5 = []; h.recent = []
    app.e.settled[h.id] = (0, 0)
    h.last, h.best, h.order, h.ship, h.job, h.wk = None, 999, None, None, None, None
    h.owner, h.breeder, h.gone = o, None, "a gift from the circuit"
    h.freshness, h.ageless = 100, False
    app.G["horses"].append(h); app.e.barn_size[o] = app.e.barn_size.get(o, 0) + 1; app.c.trainer_of(h)
    return h


if __name__ == "__main__":
    o = int(sys.argv[1]); path = sys.argv[2] if len(sys.argv) > 2 else app.SAVE
    shutil.copy(path, path.replace(".pkl", ".before-gift3.pkl"))
    app.load(path); app.ME = 0
    assert o in app.G["players"], f"no barn {o}"
    for n in BEST:
        h = clone(app.find_horse(n), o)
        print(f"{h.name}: {h.age}yo {h.sex}, {app.tier_label(h)}, a copy of {n}, now races for {app.G['players'][o].get('user')}")
    app.SAVE = path; app.save(); app.flush()
