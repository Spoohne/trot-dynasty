"""Review 15's merge acceptance suite (zero tolerance): scripted horses, no tactics, each case alone. Hard mechanics:
no overlaps, braking breaches or sideways snaps. Progress controls: the move that should happen does.
    python research/engine_lab/v3_merge_tests.py"""
import os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race3 as R

LANE2, LANE3 = R.RAIL_Y + R.LANE, R.RAIL_Y + 2 * R.LANE
results = []


def horse(name, s, y, v, track=R.MILE, **traits):
    h = R.Horse(name, traits, 1, track)
    h.s, h.y, h.v = s, y, v
    return h


def run(field, script, t_end=25.0, track=R.MILE, breaks=False, seed=1):
    """script(t, H) sets each horse's cmd. Returns the record and the horses."""
    R.P["break_b0"] = R.P["break_b0"] if breaks else 0.0
    rec = {"track": track.name, "dt": R.DT, "names": [h.name for h in field], "frames": [], "events": []}
    rngs = {h.name: random.Random(f"{seed}:{h.name}") for h in field}
    H = {h.name: h for h in field}
    t = 0.0
    R._HELD.clear()
    while t < t_end and not all(h.done for h in field):
        script(t, H)
        R.step(field, track, t, R.DT, lambda h: rngs[h.name], rec)
        t += R.DT
        rec["frames"].append([(h.s, h.y, h.v, h.E, int(h.broke > 0)) for h in field])
    return rec, H


def check(name, rec, progress, detail=""):
    a = R.audit(rec)
    hard = a["overlaps"] == 0 and a["safety"] == 0 and a["snaps"] == 0 and a["stop_dead"] == 0
    results.append((name, hard and progress, hard, progress, a["safety"], a["overlaps"], a["min_gap_ft"], detail))


b0 = R.P["break_b0"]
on_the_line = lambda h, y: abs(h.y - y) < 0.01

# 1. Empty corridor: a horse stuck behind a slower one on the rail pulls out and passes.
f = [horse("SLOW", 200, R.RAIL_Y, 44), horse("M", 170, R.RAIL_Y, 46)]   # starts at a safe following distance
def s1(t, H):
    H["SLOW"].cmd = dict(v=44, y=R.RAIL_Y)
    H["M"].cmd = dict(v=50, y=LANE2 if H["M"].s < H["SLOW"].s + 30 else R.RAIL_Y)
rec, H = run(f, s1)
check("1 empty-corridor pass", rec, H["M"].s > H["SLOW"].s + 20, f"M ahead by {H['M'].s - H['SLOW'].s:.0f} ft")

# 2. Adequate gap: M in lane 2, two lengths clear of B on the rail, comes in with no help.
f = [horse("B", 200, R.RAIL_Y, 46), horse("M", 236, LANE2, 46)]
def s2(t, H):
    H["B"].cmd = dict(v=46, y=R.RAIL_Y); H["M"].cmd = dict(v=46, y=R.RAIL_Y)
rec, H = run(f, s2, 6)
check("2 adequate gap, no yielding", rec, on_the_line(H["M"], R.RAIL_Y) and H["B"].v > 45.9, f"B speed {H['B'].v:.1f}")

# 3. Boundary sweep: B at a range of gaps behind M's slot, closing at 2 ft/s; commit only where it's safe.
fails = 0
for gap in range(2, 40, 2):
    f = [horse("B", 200, R.RAIL_Y, 48), horse("M", 200 + R.BODY_L + gap, LANE2, 46)]
    def s3(t, H):
        H["B"].cmd = dict(v=48, y=R.RAIL_Y); H["M"].cmd = dict(v=46, y=R.RAIL_Y)
    rec, H = run(f, s3, 6)
    a = R.audit(rec)
    fails += a["overlaps"] + a["safety"]
results.append(("3 boundary sweep (2-38 ft)", fails == 0, fails == 0, True, fails, 0, None, ""))

# 4. Breaks at each stage: M merging in front of B, with F ahead; F, M or B breaks at 0.2 / 0.6 / 1.2 / 2.0 s.
fails, cases = 0, 0
for who in ("F", "M", "B"):
    for when in (0.2, 0.6, 1.2, 2.0):
        f = [horse("B", 200, R.RAIL_Y, 46), horse("M", 235, LANE2, 46), horse("F", 275, R.RAIL_Y, 46)]
        def s4(t, H, who=who, when=when):
            for n in ("B", "F"):
                H[n].cmd = dict(v=46, y=R.RAIL_Y)
            H["M"].cmd = dict(v=46, y=R.RAIL_Y)
            if abs(t - when) < R.DT / 2:
                H[who].broke = 3.5; H[who].cmd["v_break_from"] = H[who].v
        rec, H = run(f, s4, 8)
        a = R.audit(rec); fails += a["overlaps"] + a["safety"]; cases += 1
results.append((f"4 breaks mid-merge ({cases} cases)", fails == 0, fails == 0, True, fails, 0, None, ""))

# 5. A follow chain behind B: three horses tight behind it; M merges in front of B.
f = [horse("M", 245, LANE2, 46)] + [horse(f"C{k}", 200 - k * 21, R.RAIL_Y, 46) for k in range(4)]
def s5(t, H):
    for n, h in H.items():
        h.cmd = dict(v=46, y=R.RAIL_Y)
rec, H = run(f, s5, 8)
check("5 follow chain", rec, on_the_line(H["M"], R.RAIL_Y))

# 6. Two horses want one slot (lanes 2 and 3, both aiming for the rail gap).
f = [horse("B", 200, R.RAIL_Y, 46), horse("F", 290, R.RAIL_Y, 46), horse("M2", 240, LANE2, 46), horse("M3", 242, LANE3, 46)]
def s6(t, H):
    for h in H.values():
        h.cmd = dict(v=46, y=R.RAIL_Y)
rec, H = run(f, s6, 12)
check("6 two horses, one slot", rec, on_the_line(H["M2"], R.RAIL_Y), f"M3 at y {H['M3'].y:.1f}")

# 7. Opposite swap: level horses in lanes 1 and 2 each want the other's lane; then one drops back.
f = [horse("A", 200, R.RAIL_Y, 46), horse("Z", 200, LANE2, 46)]
def s7(t, H):
    H["A"].cmd = dict(v=46, y=LANE2); H["Z"].cmd = dict(v=46 if t < 4 else 42, y=R.RAIL_Y)
rec, H = run(f, s7, 12)
check("7 opposite swap", rec, on_the_line(H["A"], LANE2) or on_the_line(H["Z"], R.RAIL_Y))

# 8. Turn entry and exit, wide: merges across the arc boundaries on the half-mile.
fails = 0
for s0 in (240, 300, 360, 780, 820, 860):
    f = [horse("B", s0, R.RAIL_Y + R.LANE, 46, R.HALF), horse("M", s0 + 36, R.RAIL_Y + 2 * R.LANE, 47, R.HALF)]
    def s8(t, H):
        H["B"].cmd = dict(v=46, y=H["B"].y); H["M"].cmd = dict(v=47, y=R.RAIL_Y + R.LANE)
    rec, H = run(f, s8, 6, R.HALF)
    a = R.audit(rec); fails += a["overlaps"] + a["safety"]
results.append(("8 turn entry/exit merges", fails == 0, fails == 0, True, fails, 0, None, ""))

# 9. Pocket: blocked while a horse sits outside it; out when that horse moves on.
f = [horse("L", 300, R.RAIL_Y, 46), horse("P", 279, R.RAIL_Y, 46), horse("O", 281, LANE2, 46)]
def s9(t, H):
    H["L"].cmd = dict(v=46, y=R.RAIL_Y); H["P"].cmd = dict(v=46, y=LANE2); H["O"].cmd = dict(v=46 if t < 6 else 50, y=LANE2)
rec, H = run(f, s9, 20)
commits_blocked = sum(1 for k, fr in enumerate(rec["frames"][:40]) if abs(fr[1][1] - R.RAIL_Y) > 0.01)
check("9 pocket blocked, then out", rec, commits_blocked == 0 and H["P"].y > R.RAIL_Y + 1, f"left the rail at step {next((k for k, fr in enumerate(rec['frames']) if fr[1][1] > R.RAIL_Y + 0.01), None)}")

R.P["break_b0"] = b0
print(f"{'case':34s} {'PASS':5s} hard progress breaches overlaps min_gap")
for name, ok, hard, prog, br, ov, mg, det in results:
    print(f"{name:34s} {'yes' if ok else 'NO':5s} {str(hard):5s} {str(prog):8s} {br:8} {ov:8} {mg if mg is not None else '':7}  {det}")
