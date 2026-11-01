"""Race prototype mechanics gate (review 1, item 15). Does the engine's step logic, not its tuning, produce its results?
  A. small fixed cases: catching, blocking, passing; illegal crossings and finish order
  B. step size: sequential vs simultaneous updates at DT 0.5, 0.25, 0.125; do results converge?
  C. paired scenario effects: the same horses and posts, one decision changed, same random stream per pair
    python research/engine_lab/mechanics_gate.py"""
import copy, json, os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race2 as R

out = {}
SMOOTH = dict(gait=6.0)                       # near-perfect manners: no breaks, so fixed cases are fixed


def runner(name, style, post, instr=None, **st_):
    h = R.Runner(name, R.avg(**{**SMOOTH, **st_}), style, post, instr)
    return h


def go(field, mode, dt, seed):
    f = copy.deepcopy(field)
    rng = random.Random(seed)
    if mode == "seq":
        old = R.DT; R.DT = dt
        try:
            o, rec = R.run_seq(f, rng=rng)
        finally:
            R.DT = old
    else:
        o, rec = R.run(f, rng=rng, dt=dt)
    return o, rec


# ---- A. fixed cases
cases = {
    "catch: fast closer behind a slow leader, same lane": [runner("slow", "front", 1, {"leave": True}, late_speed=-1.5, early_speed=0.5),
                                                           runner("fast", "late", 2, {"move_at": 0.99, "pull": False}, late_speed=1.5)],
    "box: rail horse behind a leader, horse outside": [runner("lead", "front", 1, {"leave": True}),
                                                       runner("boxed", "stalk", 2, {"move_at": 0.99, "pull": False}, late_speed=1.0),
                                                       runner("outside", "mid", 3, {"move_at": 0.4, "follow": False})],
    "pass: a faster horse with room outside": [runner("lead", "front", 1, {"leave": True}, late_speed=-1.0),
                                               runner("passer", "mid", 2, {"move_at": 0.6, "follow": False}, late_speed=1.0)],
}
A = {}
for name, field in cases.items():
    row = {}
    for mode in ("seq", "sim"):
        for dt in (0.5, 0.25, 0.125):
            o, rec = go(field, mode, dt, 1)
            row[f"{mode} {dt}"] = dict(order=[h.name for h in o], crossings=rec.get("crossings", 0),
                                      times=[round(h.time, 2) for h in o], boxed=[round(h.boxed_t, 1) for h in o])
    A[name] = row
out["A_fixed_cases"] = A

# ---- B. step size: the same 400 random fields under each update and step
rng0 = random.Random(7)
STY = ["front", "stalk", "stalk", "mid", "mid", "late"]
fields = [[R.Runner(f"H{k}", R.avg(**{t: rng0.gauss(0, .4) for t in ("early_speed", "late_speed", "stamina", "gait")}), rng0.choice(STY), k + 1)
           for k in range(8)] for _ in range(400)]
B, winners = {}, {}
for mode in ("seq", "sim"):
    for dt in (0.5, 0.25, 0.125):
        sw, times, cross, w = {s: 0 for s in set(STY)}, [], 0, []
        for i, f in enumerate(fields):
            o, rec = go(f, mode, dt, 100 + i)
            sw[o[0].style] += 1; times.append(o[0].time); cross += rec.get("crossings", 0); w.append(o[0].name)
        winners[(mode, dt)] = w
        B[f"{mode} {dt}"] = dict(style_wins={k: round(v / len(fields), 3) for k, v in sw.items()},
                                 median_win_time=round(st.median(times), 2), crossings_per_race=round(cross / len(fields), 3))
for mode in ("seq", "sim"):
    a, b = winners[(mode, 0.25)], winners[(mode, 0.125)]
    B[f"{mode}: same winner at DT 0.25 and 0.125"] = round(sum(x == y for x, y in zip(a, b)) / len(a), 3)
out["B_step_size"] = B

# ---- C. paired scenarios: identical horses and posts, one decision changed, same random stream per pair
NOFRONT = ["stalk", "mid", "mid", "late", "stalk", "mid", "late"]


def paired(make, change_a, change_b, n=600, modes=(("seq", 0.5), ("sim", 0.5), ("sim", 0.25))):
    res = {}
    for mode, dt in modes:
        wa = wb = 0
        r = random.Random(42)
        for i in range(n):
            base = make(r)
            fa, fb = copy.deepcopy(base), copy.deepcopy(base)
            change_a(fa); change_b(fb)
            oa, _ = go(fa, mode, dt, 5000 + i)
            ob, _ = go(fb, mode, dt, 5000 + i)
            wa += oa[0].name == "S"; wb += ob[0].name == "S"
        res[f"{mode} {dt}"] = [round(wa / n, 3), round(wb / n, 3)]
    return res


def mk(styles, subject_style):
    def make(r):
        f = [R.Runner("S", R.avg(**{t: r.gauss(0, .4) for t in ("early_speed", "late_speed", "stamina", "gait")}), subject_style, 1)]
        f += [R.Runner(f"H{k}", R.avg(**{t: r.gauss(0, .4) for t in ("early_speed", "late_speed", "stamina", "gait")}), s, k + 2) for k, s in enumerate(styles)]
        return f
    return make


def set_s(**instr):
    return lambda f: f[0].instr.update(instr)


def add_duel(f):
    f[1].style = "front"; f[1].instr["leave"] = True


C = {}
C["duel: leader alone vs a second leaver (subject = leader)"] = paired(mk(NOFRONT, "front"), set_s(leave=True), lambda f: (set_s(leave=True)(f), add_duel(f)))
C["duel: closer, calm pace vs a duel ahead (subject = closer)"] = paired(mk(["front"] + NOFRONT[1:], "late"), lambda f: None, lambda f: add_duel(f) if f[1].style != "front" else f[2].instr.update(leave=True) or setattr(f[2], "style", "front"))
C["cover: same move point, follows cover vs refuses it"] = paired(mk(["front"] + NOFRONT[1:], "late"), set_s(move_at=0.62, follow=True), set_s(move_at=0.62, follow=False))
C["move: same horse, moves at 0.3 vs 0.72 (follow off both)"] = paired(mk(NOFRONT, "mid"), set_s(move_at=0.3, follow=False), set_s(move_at=0.72, follow=False))
out["C_paired_scenarios_[A,B]_win_share"] = C
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mechanics_gate.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
