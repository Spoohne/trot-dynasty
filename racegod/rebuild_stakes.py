"""Rebuild stakes replays that finished on borrowed margins (RaceGod V2, Patrick approved 2026-11-02).
Stakes ran on sim.race, which sets no margins, so the story used each horse's margins from its previous race.
Times, order, purses and trophies stay exactly as recorded; only the story is rebuilt, its margins read from the times.

  python racegod/rebuild_stakes.py <save.pkl> [first day, default 2626]      writes the save in place (back it up first)"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rebuild_nights as rn                                    # noqa: E402  (chdirs to the game folder, loads app)

app, c = rn.app, rn.c


def main(path, first):
    app.save = lambda *a, **k: None; app.snapshot = lambda *a, **k: None
    app.load(path)
    by_name = {h.name: h for h in c.lineage(app.G["horses"] + list(rn.e.nursery) + rn.sk.HALL)}
    rids = [rid for rid, st in c.STORIES.items() if "-stake-" in rid and st["day"] >= first]
    for rid in rids:
        assert not rn.rebuild(rid, c.STORIES[rid], by_name, retime=False), "times never move"
        h = c.STORIES[rid]["horses"]
        print(rid, c.STORIES[rid]["name"], "- second", h[1]["behind"][6], "L, clock", round((h[1]["time"] - h[0]["time"]) / rn.SEC, 1), "L")
    app.SAVE = path; app.DIRTY[0] = True; app.flush()
    print(f"rebuilt {len(rids)} stakes replays; saved {path}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2626)
