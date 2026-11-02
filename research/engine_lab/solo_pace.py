"""Review 10's isolated test: one horse alone, no field-dependent driving. It holds a fixed pace (on the rail) to the
three-quarters, then drives to the wire. A menu of paces, before and after a +0.5 trait upgrade, under each energy rule.
Reports the finish time per pace and the best time over the menu (what the horse can do, however it's driven)."""
import json, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race2 as R
R.P.update(break_k=0.0, tank_full=45, mile_turns=[(0.125, 0.375), (0.625, 0.875)], stretch_at=0.875, stretch_lanes=5)
PACES = [46.7, 48.5, 49.5, 50.5, 51.5, 52.5, 53.5]


def solo(stats, pace):
    h = R.Runner("S", dict(stats), "mid", 1, {"fixed_v": pace, "lane_lock": 0, "fixed_until": 0.75, "leave": False, "move_at": 0.75})
    R.run([h], rng=random.Random(0), dt=1 / 32)
    return h.time


out = {}
for ease in (0.0, 0.8):
    R.P["ease_early"] = ease
    for trait in ("none", "early_speed", "late_speed", "stamina"):
        s = R.avg()
        if trait != "none":
            s[trait] += 0.5
        times = [round(solo(s, p), 2) for p in PACES]
        out[f"ease {ease} · +0.5 {trait}"] = dict(times=times, best=min(times))
base = {e: out[f"ease {e} · +0.5 none"]["best"] for e in (0.0, 0.8)}
for k, v in out.items():
    e = float(k.split()[1])
    print(f"{k:32s} best {v['best']:.2f} (gain {base[e] - v['best']:+.2f} s)  by pace {PACES}: {v['times']}")
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "solo_pace.json"), "w"), indent=1)
