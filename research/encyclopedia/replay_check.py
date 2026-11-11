"""The guard between a recorded sim race and the viewer: every story is checked on exactly what the viewer will draw (calls,
lengths behind, lanes, straight lines between calls), repaired where it can be, and drawn single file when it can't.
A replay is never shown broken; it may be shown simpler.

    problems(story) -> list of strings, empty when it plays clean
    guard(story)    -> the story to save: as recorded, repaired, or single file (story["guard"] says which)
    python research/encyclopedia/replay_check.py          check every saved race in gallop_races/ (and the self-test)
"""
import glob
import json
import os
import sys

BODY = 15.5 / 8          # lengths: the viewer's RACE.BODY (15.5 ft) in its 8 ft lengths
WIDE = 0.9               # lanes: closer than this side by side is the same ground
MAX_STEP = 3.0           # lengths a horse may gain or lose on the leader between two calls (0.5 s): more is a jump
MAX_SIDE = 0.5           # lanes a horse may move between two calls
SNAP = 0.08              # a lane this close to whole is drawn whole


def _frames(story):
    """The positions the viewer draws: every call, and the midpoint between calls (it draws straight lines)."""
    hs = story["horses"]
    for k in range(len(story["calls"])):
        yield [(h["behind"][k], h["lane"][k]) for h in hs]
        if k + 1 < len(story["calls"]):
            yield [((h["behind"][k] + h["behind"][k + 1]) / 2, (h["lane"][k] + h["lane"][k + 1]) / 2) for h in hs]


def problems(story):
    hs, out = story["horses"], []
    for f, pos in enumerate(_frames(story)):
        if f == 0:
            continue                                                       # the gate: the viewer lines everyone up itself
        for i in range(len(hs)):
            for j in range(i + 1, len(hs)):
                (bi, li), (bj, lj) = pos[i], pos[j]
                if abs(li - lj) < WIDE and abs(bi - bj) < BODY - 0.02:   # stories round to 0.01 length
                    out.append(f"overlap {hs[i]['name']} / {hs[j]['name']} at frame {f / 2:.1f}")
    for h in hs:
        for k in range(1, len(story["calls"])):
            if abs(h["behind"][k] - h["behind"][k - 1]) > MAX_STEP:
                out.append(f"jump {h['name']} at call {k}")
            if abs(h["lane"][k] - h["lane"][k - 1]) > MAX_SIDE:
                out.append(f"side jump {h['name']} at call {k}")
            if h["behind"][k] < -1e-6:
                out.append(f"ahead of the leader {h['name']} at call {k}")
    by_wire = sorted(range(len(hs)), key=lambda i: (hs[i]["behind"][-1], hs[i]["time"]))
    if [hs[i]["place"] for i in by_wire] != sorted(h["place"] for h in hs):
        out.append("order at the wire doesn't match the result")
    return out


def repair(story):
    """Snap near-whole lanes, then at every call push a horse back to a body behind anyone it sits on in its lane
    (front to back, so the order never changes and only the trailing horse gives ground)."""
    hs = story["horses"]
    for h in hs:
        h["lane"] = [round(l) if abs(l - round(l)) < SNAP else l for l in h["lane"]]
    for k in range(1, len(story["calls"])):
        order = sorted(range(len(hs)), key=lambda i: hs[i]["behind"][k])
        for a, i in enumerate(order):
            for j in order[:a]:
                if abs(hs[i]["lane"][k] - hs[j]["lane"][k]) < WIDE:
                    hs[i]["behind"][k] = max(hs[i]["behind"][k], hs[j]["behind"][k] + BODY)
    return story


def single_file(story):
    """The fallback: the field in one line on the rail in finishing order, each horse easing from a body apart off the gate
    to its own margin at the wire. Plain, never wrong."""
    hs = sorted(story["horses"], key=lambda h: h["place"])
    n = len(story["calls"])
    end = -BODY
    for rank, h in enumerate(hs):
        end = max(h["behind"][-1], end + BODY)          # a photo is drawn a body apart: in one line nobody can be closer
        h["behind"] = [round(rank * BODY + (end - rank * BODY) * k / (n - 1), 2) for k in range(n)]
        h["lane"] = [0.0] * n
    story["horses"] = hs
    return story


def guard(story):
    if not problems(story):
        story["guard"] = "clean"
        return story
    repair(story)
    if not problems(story):
        story["guard"] = "repaired"
        return story
    story["guard"] = "single file"
    return single_file(story)


def _selftest():
    mk = lambda name, place, b, l: {"name": name, "place": place, "time": 100 + place, "behind": b, "lane": l}
    s = {"calls": [0, 0.5, 1.0], "horses": [mk("A", 1, [0, 0, 0], [0, 0, 0]), mk("B", 2, [0, 1, 2], [1, 1, 1])]}
    assert guard(s)["guard"] == "clean"
    s = {"calls": [0, 0.5, 1.0, 1.5], "horses": [mk("A", 1, [0, 0, 0, 0], [0, 0, 0, 0]), mk("B", 2, [3, 3, 0.5, 3], [0, 0, 0, 0])]}
    assert guard(s)["guard"] == "repaired" and not problems(s)
    s = {"calls": [0, 0.5, 1.0, 1.5], "horses": [mk("A", 1, [0, 0, 0, 0], [0, 0, 0, 0]), mk("B", 2, [3, 3, 9, 1], [0, 0, 3, 0])]}
    assert guard(s)["guard"] == "single file" and not problems(s)


if __name__ == "__main__":
    _selftest()
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gallop_races")
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(here, "*.json")))
    for p in files:
        s = json.load(open(p))
        bad = problems(s)
        print(f"{os.path.basename(p)}: {s.get('guard', 'unchecked')}, {len(bad)} problems" + (f" (first: {bad[0]})" if bad else ""))
    print("ok")
