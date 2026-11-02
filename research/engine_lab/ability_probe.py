"""Review 9's test: does the profile planner penalize ability? Planner self-checks first, then 20 fixed fields x 8
subjects (every post), breaks off, DT 1/16, long stretch five wide, tank 45. The subject gets +0.5 in one trait and races
(a) with every horse's baseline plan frozen and (b) with plans recomputed. Reading, declared before the run:
frozen helps but replanned erases or reverses it -> the planner penalizes ability; neither helps -> look at the physics.
    python research/engine_lab/ability_probe.py"""
import copy, json, os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race2 as R
DT = 1 / 16
R.P.update(break_k=0.0, tank_full=45, mile_turns=[(0.125, 0.375), (0.625, 0.875)], stretch_at=0.875, stretch_lanes=5, route=1)
R.P.update(**{k: float(v) for k, v in (a.split("=") for a in os.environ.get("PSET", "").split(",") if a)})
TR = ("early_speed", "late_speed", "stamina", "gait")


def field(stats):
    return [R.Runner(f"H{k}", dict(s), "mid", k + 1) for k, s in enumerate(stats)]


# ---- planner self-checks
R.P["profile"] = 1
f = field([R.avg()] * 8); R.plan_race(f)
assert sum(h.instr["leave"] for h in f) <= 2, "identical horses: at most the inside two go for the lead"
f = field([R.avg(early_speed=1.0)] + [R.avg()] * 7); f[0].instr["leave"] = False; R.plan_race(f)
assert f[0].want_gap > 0.5 and f[0].style != "front", "a 'don't leave' instruction must carry into the gap and the label"
rng = random.Random(3)
f = field([R.avg(**{t: rng.gauss(0, .4) for t in TR}) for _ in range(8)]); R.plan_race(f)
R.P["profile"] = 0
a = copy.deepcopy(f); b = copy.deepcopy(f)
for h in b:
    h.style = rng.choice(["front", "stalk", "mid", "late"])
ta = [h.time for h in sorted(R.run(a, rng=random.Random(0), dt=DT)[0], key=lambda h: h.name)]
tb = [h.time for h in sorted(R.run(b, rng=random.Random(0), dt=DT)[0], key=lambda h: h.name)]
assert ta == tb, "with plans fixed, the label must not change the race"
print("planner checks ok")

# ---- the intervention
rng = random.Random(9)
fields = [[R.avg(**{t: rng.gauss(0, .4) for t in TR}) for _ in range(8)] for _ in range(20)]


def race(stats, plans=None):
    f = field(stats)
    R.P["profile"] = 0 if plans else 1
    if plans:
        for h, (ins, g) in zip(f, plans):
            h.instr, h.want_gap = dict(ins), g
    o, rec = R.run(f, rng=random.Random(0), dt=DT)
    c75 = {x["name"]: x["behind"] for x in next(c for c in rec["calls"] if c["at"] == 0.75)["horses"]}
    return f, [h.name for h in o], c75


out = {}
for trait in ("late_speed", "early_speed"):
    rows = []
    for stats in fields:
        base, border, b75 = race(stats)
        plans = [(h.instr, h.want_gap) for h in base]
        for k in range(8):
            better = [dict(s) for s in stats]; better[k][trait] += 0.5
            name = f"H{k}"
            r = dict(t0=base[k].time, p0=border.index(name) + 1, g0=base[k].want_gap, b0=b75[name])
            for tag, pl in (("frozen", plans), ("replan", None)):
                f, order, c75 = race(better, pl)
                r.update({f"dt_{tag}": f[k].time - r["t0"], f"dp_{tag}": order.index(name) + 1 - r["p0"],
                          f"gap_{tag}": f[k].want_gap, f"b75_{tag}": c75[name]})
            rows.append(r)
    pct = lambda key, test: round(sum(test(r[key]) for r in rows) / len(rows), 3)
    out[f"+0.5 {trait}"] = dict(
        runs=len(rows),
        **{f"{tag}_{m}": v for tag in ("frozen", "replan") for m, v in (
            ("mean_secs_gained", round(-st.mean(r[f"dt_{tag}"] for r in rows), 3)),
            ("mean_places_gained", round(-st.mean(r[f"dp_{tag}"] for r in rows), 3)),
            ("share_faster", pct(f"dt_{tag}", lambda x: x < -1e-9)),
            ("share_slower", pct(f"dt_{tag}", lambda x: x > 1e-9)),
            ("share_finished_worse", pct(f"dp_{tag}", lambda x: x > 0)),
            ("mean_lengths_behind_at_3_4", round(st.mean(r[f"b75_{tag}"] for r in rows), 2)))},
        baseline_lengths_behind_at_3_4=round(st.mean(r["b0"] for r in rows), 2),
        replan_changed_own_plan=round(sum(abs(r["gap_replan"] - r["g0"]) > 1e-9 for r in rows) / len(rows), 3))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ability_probe.json"), "w"), indent=1)
for k, v in out.items():
    print(k, json.dumps(v))
