"""Regression checks for the three defects in the Nov 1 review (Trot-Dynasty-Review-and-Roadmap.md), each forced:
signup taking players' horses, a race settled twice after a failure, a failed save never retried.
Works on a COPY of a save, never writes the real one.
    python check_defects.py <save copy.pkl>"""
import builtins, copy, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); os.chdir(HERE)
import app

c, e = app.c, app.e
TMP = tempfile.mkdtemp()


def fresh(save):
    app.SAVE = os.path.join(TMP, "save.pkl")
    app.snapshot = lambda *a, **k: None
    app.load(save)


def check_signup(save):
    fresh(save)
    app.save = lambda *a, **k: None
    humans = sorted(c.HUMAN)
    for k, h in enumerate(app.G["horses"]):                   # worst case: every horse a starter could be is a player's
        if (not h.retired and 2 <= h.age <= 4) or (h.retired and h.sex == "f" and h.age <= 12):
            h.owner = humans[k % len(humans)]
    owned = {h.id: h.owner for h in app.G["horses"] + list(e.nursery) if h.owner in c.HUMAN}
    for k in range(3):
        o, err = app.signup(f"defectcheck{k}", "password1")
        assert err is None, err
    moved = [hid for hid, o in owned.items() if next(h for h in app.G["horses"] + list(e.nursery) if h.id == hid).owner != o]
    assert not moved, f"signup took {len(moved)} players' horses"
    app.G["ai"] = set()
    o, err = app.signup("defectcheckfull", "password1")
    assert o is None and "full" in err, (o, err)
    print("signup: 3 new barns, no player's horse moved; a full circuit says so")


def check_settlement(save):
    fresh(save)
    app.save = lambda *a, **k: None
    r = next(r for r in c.CARD["races"] if not r.get("done"))
    alive = {id(h) for h in app.G["horses"]}
    starts = {h.id: h.starts for h in r["field"]}
    keep = c.set_records
    c.set_records = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("injected"))   # fail after results are written
    try:
        c.run_race(r, alive, [])
    except RuntimeError:
        pass
    c.set_records = keep
    assert not r.get("done")
    c.run_race(r, alive, [])                                  # the evening loop's retry
    assert r.get("done")
    assert all(h.starts == starts[h.id] + 1 for h in r["field"]), "a start was counted twice"
    # and a failure before any result is written: the retry runs the race normally, once
    fresh(save)
    r = next(r for r in c.CARD["races"] if not r.get("done"))
    alive = {id(h) for h in app.G["horses"]}
    starts = {h.id: h.starts for h in r["field"]}
    keep = c._story.build
    c._story.build = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("injected"))
    try:
        c.run_race(r, alive, [])
    except RuntimeError:
        pass
    c._story.build = keep
    assert not r.get("settling") and all(h.starts == starts[h.id] for h in r["field"])
    c.run_race(r, alive, [])
    assert r.get("done") and all(h.starts == starts[h.id] + 1 for h in r["field"])
    print("settlement: a failure after results are written is never applied twice; one before them retries cleanly")


def check_save(save):
    fresh(save)
    app.DIRTY[0] = True
    real_open = builtins.open
    builtins.open = lambda p, *a, **k: (_ for _ in ()).throw(OSError("injected")) if str(p).endswith(".tmp") else real_open(p, *a, **k)
    try:
        app.flush()
    except OSError:
        pass
    finally:
        builtins.open = real_open
    assert app.DIRTY[0], "a failed save marked the world saved"
    app.flush()                                               # the background saver's next pass
    assert not app.DIRTY[0] and os.path.exists(app.SAVE), "the retry didn't save"
    print("save: a failed write stays unsaved and the next pass saves it")


if __name__ == "__main__":
    for check in (check_signup, check_settlement, check_save):
        check(sys.argv[1])
    print("all three defects stay fixed")
