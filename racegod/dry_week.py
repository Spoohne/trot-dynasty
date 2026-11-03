"""Run a COPY of the live save forward N race nights (app.tick with the night checks), then save it beside the copy for
racegod/audit.py. Never points at the live save; the game folder's own save.pkl is left alone (app.save is redirected).
    python racegod/dry_week.py <save copy.pkl> [nights, default 7]        writes <save copy>.week.pkl"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rebuild_nights as rn                                    # noqa: E402  (chdirs to the game folder, loads app)

app = rn.app


def main(path, nights):
    out = path[:-4] + ".week.pkl"
    app.SAVE = out                                             # app.save() writes here, never the game folder's save.pkl
    app.snapshot = lambda *a, **k: None
    app.load(path)
    day0 = app.G["day"]
    for n in range(nights):
        d = app.G["day"]
        ok = app.checked_tick()
        print(f"night {n + 1}: day {d} -> {app.G['day']}  {'ok' if ok else 'HELD: ' + str(app.G.get('held'))}", flush=True)
        if not ok:
            break
    app.save(); app.flush()                                   # app.save only marks the world dirty; flush writes it
    print(f"saved {out}; audit with: python racegod/audit.py {out} --since {day0}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 7)
