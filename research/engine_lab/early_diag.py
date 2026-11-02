"""Item 94 trace: where does +0.5 early speed cost a horse? Same fields as ability_probe, plans frozen. Each subject races
in traffic and alone (ghost + clear path: nobody sees it and it sees nobody), split by whether its plan is to leave."""
import json, os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race2 as R
DT = 1 / 16
R.P.update(break_k=0.0, tank_full=45, mile_turns=[(0.125, 0.375), (0.625, 0.875)], stretch_at=0.875, stretch_lanes=5, route=1)
R.P.update(**{k: float(v) for k, v in (a.split("=") for a in os.environ.get("PSET", "").split(",") if a)})
TR = ("early_speed", "late_speed", "stamina", "gait")
rng = random.Random(9)
fields = [[R.avg(**{t: rng.gauss(0, .4) for t in TR}) for _ in range(8)] for _ in range(20)]


def race(stats, plans, k, alone):
    f = [R.Runner(f"H{i}", dict(s), "mid", i + 1) for i, s in enumerate(stats)]
    for h, (ins, g) in zip(f, plans):
        h.instr, h.want_gap = dict(ins), g
    if alone:
        f[k].instr.update(ghost=True, clear_path=True)
    R.P["profile"] = 0
    R.run(f, rng=random.Random(0), dt=DT)
    return f[k]


rows = []
for stats in fields:
    f = [R.Runner(f"H{i}", dict(s), "mid", i + 1) for i, s in enumerate(stats)]
    R.plan_race(f)
    plans = [(dict(h.instr), h.want_gap) for h in f]
    for k in range(8):
        better = [dict(s) for s in stats]; better[k]["early_speed"] += 0.5
        for alone in (0, 1):
            a, b = race(stats, plans, k, alone), race(better, plans, k, alone)
            rows.append(dict(alone=alone, leaver=bool(plans[k][0]["leave"]), dt=b.time - a.time, de=b.energy - a.energy,
                             dcap=b.capped_t - a.capped_t, dbox=b.boxed_t - a.boxed_t, dground=b.ground - a.ground))
out = {}
for alone in (0, 1):
    for lv in (True, False):
        g = [r for r in rows if r["alone"] == alone and r["leaver"] == lv]
        if g:
            out[f"{'alone' if alone else 'traffic'} · {'leaver' if lv else 'sitter'}"] = dict(
                n=len(g), slower=round(sum(r["dt"] > 1e-9 for r in g) / len(g), 2), secs=round(st.mean(r["dt"] for r in g), 3),
                energy_at_wire=round(st.mean(r["de"] for r in g), 2), capped_s=round(st.mean(r["dcap"] for r in g), 2),
                boxed_s=round(st.mean(r["dbox"] for r in g), 2), extra_ground_ft=round(st.mean(r["dground"] for r in g), 1))
for k, v in out.items():
    print(k, json.dumps(v))
