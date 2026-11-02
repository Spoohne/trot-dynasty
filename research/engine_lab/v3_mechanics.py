"""race3 build step 1-2 checks (DESIGN_V3 §11.9): single-horse mechanics and the eight-abreast gate.
    python research/engine_lab/v3_mechanics.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race3 as R

# 1. One pace, three trips: on the rail alone, parked out in the open, tucked behind a horse. Reserve used to the 3/4.
print("1. matched pace 47.5 ft/s to the three-quarters (mile):")
for label, y, cover in (("rail, alone", R.RAIL_Y, False), ("outside, no cover", R.RAIL_Y + R.LANE, False), ("rail, behind a horse", R.RAIL_Y, True)):
    f = [R.Horse("S", {}, 1, R.MILE)]
    if cover:
        f.append(R.Horse("C", {}, 1, R.MILE)); f[1].s = R.BODY_L + 3.0
    f[0].y = y

    def drv(field, track, t, rec=None):
        for h in field:
            h.cmd = {"v": 47.5, "y": h.y}
    used, prog = None, None
    t = 0.0
    rec = {"events": []}
    rngs = lambda h: __import__("random").Random(0)
    R.P["break_b0"] = 0.0
    while f[0].s < 0.75 * R.FT_MILE:
        drv(f, R.MILE, t, rec); R.step(f, R.MILE, t, R.DT, rngs, rec); t += R.DT
    print(f"   {label:22s} reserve used {R.P['e_max'] - f[0].E:5.2f}  time to 3/4 {t:6.2f}s")

# 2. Eight abreast at the gate on the half-mile (300 ft to the first turn): one horse leaves, the rest find the rail.
print("2. eight abreast, half-mile, average horses; post 4 leaves:")


def gate_driver(leaver):
    def drv(field, track, t, rec=None):
        for h in field:
            if h.name == leaver:
                h.cmd = {"v": 60.0, "y": R.RAIL_Y}
                continue
            inside = [o for o in field if o is not h and o.y < h.y - 1 and abs(o.s - h.s) < R.BODY_L + R.HEAD + 2]
            ease = 3.0 if inside else 0.0                     # can't drop in yet: ease back to tuck in behind
            h.cmd = {"v": h.v_sus - ease, "y": R.RAIL_Y}
    return drv


R.P["break_b0"] = 0.0
f = [R.Horse(f"P{k + 1}", {}, k + 1, R.HALF) for k in range(8)]
o, rec = R.run(f, "half", gate_driver("P4"), seed=1)
turn_in = next(k for k, fr in enumerate(rec["frames"]) if max(x[0] for x in fr) >= 300)
wide = [round((x[1] - R.RAIL_Y) / R.LANE + 1, 1) for x in rec["frames"][turn_in]]
print("   lanes at the first turn (post order):", wide)
print("   order at the half:", [rec["names"][i] for i in sorted(range(8), key=lambda i: -rec["frames"][next(k for k, fr in enumerate(rec['frames']) if max(x[0] for x in fr) >= 2640)][i][0])])
print("   finish:", [n for n, _ in rec["finish"]])
print("   audit:", R.audit(rec), " lateral moves paused:", rec.get("paused", 0))
