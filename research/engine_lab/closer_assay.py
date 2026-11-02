"""Closer assay (review 5, item 54). One combination per run: drive point, surplus kick, closers' move point.
    python research/engine_lab/closer_assay.py <drive_all> <surplus_k> <move_late>
Matched random fields (DT 1/8, breaks at a plausible rate): win share by style, and for closers the ground behind the
leader at the three-quarters, energy left at the finish, and seconds boxed."""
import json, os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race2 as R
drive, surplus, move_late = map(float, sys.argv[1:4])
R.P.update(drive_all=drive, surplus_k=surplus, move_late=move_late, break_k=0.0002, budget=int(os.environ.get("BUDGET", "0")),
           tank_full=float(os.environ.get("TANK", R.P["tank_full"])), split=int(os.environ.get("SPLIT", "0")), route=int(os.environ.get("ROUTE", "0")))
if os.environ.get("GEO") == "1":                                   # an eighth-mile homestretch that fans out five wide
    R.P.update(mile_turns=[(0.125, 0.375), (0.625, 0.875)], stretch_at=0.875, stretch_lanes=5)
if os.environ.get("GAPLATE"):
    R.P["gap_late"] = float(os.environ["GAPLATE"])
if os.environ.get("GAPMID"):
    R.P["gap_mid"] = float(os.environ["GAPMID"])
if R.P["split"]:
    R.P["cost_base"] = R.P["cost_base"] - R.P["air_k"]          # same spend alone at cruise; only its make-up changes
STY = ["front", "stalk", "stalk", "mid", "mid", "late"]
rng = random.Random(77)
N = 300
wins = {s: 0 for s in set(STY)}
behind, e_end, boxed, late_place = [], [], [], []
for i in range(N):
    f = [R.Runner(f"H{k}", R.avg(**{t: rng.gauss(0, .4) for t in ("early_speed", "late_speed", "stamina", "gait")}), rng.choice(STY), k + 1)
         for k in range(8)]
    o, rec = R.run(f, rng=random.Random(500 + i), dt=0.125)
    wins[o[0].style] += 1
    c75 = next(c for c in rec["calls"] if c["at"] == 0.75)
    pos = {x["name"]: x for x in c75["horses"]}
    for k, h in enumerate(o):
        if h.style == "late":
            behind.append(pos[h.name]["behind"]); e_end.append(h.energy); boxed.append(h.boxed_t); late_place.append(k + 1)
share = {s: STY.count(s) / len(STY) for s in wins}
out = dict(gap_late=R.P["gap_late"], geo=os.environ.get("GEO", "0"), route=R.P["route"], tank_full=R.P["tank_full"], split=R.P["split"], drive_all=drive, surplus_k=surplus, move_late=move_late,
           style_wins={s: round(wins[s] / N, 3) for s in wins}, style_win_over_share={s: round(wins[s] / N / share[s], 2) for s in wins},
           closer_behind_at_75=round(st.mean(behind), 2), closer_energy_at_finish=round(st.mean(e_end), 1),
           closer_boxed_s=round(st.mean(boxed), 2), closer_mean_place=round(st.mean(late_place), 2))
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "closer"), exist_ok=True)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "closer", f"d{drive}_s{surplus}_m{move_late}_b{os.environ.get('BUDGET', '0')}_t{R.P['tank_full']}_x{R.P['split']}_r{R.P['route']}_g{os.environ.get('GEO','0')}_gl{R.P['gap_late']:g}.json"), "w"), indent=1)
print(json.dumps(out))
