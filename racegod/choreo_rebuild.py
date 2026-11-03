"""Rebuild kept stories through the choreographer (racegod/engine.py choreograph): the decided result in, positions from a run.
Reads a save copy, never writes it; the rebuilt stories go to a JSON for racegod/replay_server.py (as <id>-choreo, with
the original as <id>-story). Also prints the picture checks: two horses in one lane within a body at the stretch or the
wire, and lane changes between the stretch and the wire (what the viewer draws as going through each other).
    python racegod/choreo_rebuild.py <save.pkl> <out.json> [race id ...]      (no ids: every kept story since day 2626)"""
import json, os, pickle, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sim                                                     # noqa: E402
from racegod import engine                                     # noqa: E402

KEEP = ("id", "name", "purse", "day", "venue", "passing", "records", "sponsor")


def horses_of(save):
    H = {}
    for h in save["G"]["horses"]:
        H[h.name] = h
    for h in save.get("nursery", []) or []:
        H.setdefault(getattr(h, "name", None), h)
    for h in save.get("hall", []) or []:
        H.setdefault(getattr(h, "name", None), h)
    return H


def rebuild(st, H):
    rows = sorted(st["horses"], key=lambda r: r["place"])
    order = []
    win_raw = sim.CLOCK_REF + (rows[0]["time"] - sim.CLOCK_AT) / sim.CLOCK_K
    backs = 0
    for r in rows:
        h = H[r["name"]]
        h.post, h.trip, h.last_time = r["post"], r["trip"], r["time"]
        if not r.get("why"):                                   # a story from before the ledger: read the ledger off the trip text
            role = ("lead" if "on the lead" in r["trip"] else "pocket" if "pocket" in r["trip"] else "first_over" if "first-over" in r["trip"]
                    else "followed" if "mid-pack" in r["trip"] else "back")
            r["why"] = dict(out=r["post"], role=role, depth=backs if role == "back" else 0, margin=round((r["time"] - rows[0]["time"]) / engine.SEC_PER_LENGTH, 2))
            backs += role == "back"
        h.why = r["why"]
        h.margin_l = r["why"]["margin"]
        h.raw_time = win_raw + h.margin_l * engine.SEC_PER_LENGTH
        order.append(h)
    s = engine.choreograph(order, st["track"], st.get("passing", False))
    for k in KEEP:
        if k in st:
            s[k] = st[k]
    for new, old in zip(s["horses"], rows):
        for k in ("odds", "why", "driver", "silks", "owner", "stable", "player", "wraps", "mask", "emblem", "marquee"):
            if k in old:
                new[k] = old[k]
    return s


def checks(s):
    bad = []
    for c, name in ((5, "stretch"), (6, "wire")):
        seen = []
        for r in s["horses"]:
            ln, b = r["lane"][c], r["behind"][c]
            if any(pl == ln and abs(pb - b) < engine.BODY_L for pl, pb in seen):
                bad.append(f"two in a lane within a body at the {name}: {r['name']}")
            seen.append((ln, b))
    bad += [f"lane change in the stretch: {r['name']} {r['lane'][5]} -> {r['lane'][6]}" for r in s["horses"] if r["lane"][5] != r["lane"][6]]
    bad += [f"4-wide before the stretch: {r['name']}" for r in s["horses"] if max(r["lane"][2:5]) > 2]
    return bad


def main():
    path, out = sys.argv[1], sys.argv[2]
    ids = sys.argv[3:]
    with open(path, "rb") as f:
        save = pickle.load(f)
    H = horses_of(save)
    stories = {rid: st for rid, st in save["stories"].items() if (rid in ids if ids else st["day"] >= 2626 and all(r.get("why") for r in st["horses"]))}
    kept, n_bad_new, n_bad_old = {}, 0, 0
    for rid, st in stories.items():
        if any(r["name"] not in H for r in st["horses"]):
            print(f"{rid}: a horse is gone from the save, skipped"); continue
        s = rebuild(st, H)
        kept[f"{rid}-choreo"], kept[f"{rid}-story"] = s, dict(st, id=f"{rid}-story")
        b_new, b_old = checks(s), checks(st)
        n_bad_new += bool(b_new); n_bad_old += bool(b_old)
        if ids:
            print(f"{rid}: choreographed {len(b_new)} picture faults ({'; '.join(b_new[:4])}) vs the story's {len(b_old)}")
    json.dump(kept, open(out, "w"))
    print(f"{len(stories)} races: picture faults in {n_bad_new} choreographed vs {n_bad_old} story-built; written to {out}")


if __name__ == "__main__":
    main()
