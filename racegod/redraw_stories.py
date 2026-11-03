"""Redraw every kept replay of a world through the choreographer as it is now (the results never change, only the picture),
so a fix to the picture reaches the replays already kept. Run with the game stopped; backs the save up first.
    python racegod/redraw_stories.py <save.pkl> [first day, default 0] [--write]        (no --write: a dry run, counts only)"""
import copy, os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app                                                     # noqa: E402
from racegod import choreo_rebuild as cr                        # noqa: E402

c = app.c


def crossed(rows):
    return any(a["lane"][6] == b["lane"][6] and (a["behind"][5] > b["behind"][5]) != (a["behind"][6] > b["behind"][6])
               for a in rows for b in rows if a is not b)


def main(path, first, write):
    app.load(path)
    H = cr.horses_of({"G": app.G, "nursery": list(app.e.nursery), "hall": list(app.sk.HALL)})
    n = bad_before = bad_after = 0
    for rid, st in list(c.STORIES.items()):
        if st.get("day", 0) < first or not st["horses"] or not st["horses"][0].get("why"):
            continue
        for k, r in enumerate(st["horses"]):
            if r["name"] not in H:                             # AI fillers aren't kept in the save: a stand-in, for the picture only
                h = copy.copy(next(iter(H.values()))); h.name, h.id = r["name"], f"standin-{rid}-{k}"; H[h.name] = h
        bad_before += crossed(st["horses"])
        s = cr.rebuild(st, H)
        order = [H[r["name"]] for r in sorted(st["horses"], key=lambda r: r["place"])]
        c.tells(s, order)                                      # the captions the night had: fractious, breaks, fights, sharp
        s["id"] = rid
        for k in ("tlook", "matinee", "track"):
            if k in st and k not in s:
                s[k] = st[k]
        bad_after += crossed(s["horses"])
        if write:
            c.STORIES[rid] = s
        n += 1
    print(f"{n} replays redrawn: passes inside one lane {bad_before} -> {bad_after}")
    if write:
        app.SAVE = path
        app.save(); app.flush()
        print("saved", path)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--write"]
    path = args[0] if args else app.SAVE
    if "--write" in sys.argv:
        shutil.copy(path, path.replace(".pkl", ".before-redraw.pkl"))
    main(path, int(args[1]) if len(args) > 1 else 0, "--write" in sys.argv)
