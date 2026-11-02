"""Profile-based positioning vs fixed style labels (log item 89). Same random fields both ways, long homestretch fanning five
wide (turns 0.125-0.375, 0.625-0.875), tank_full 45, breaks at a plausible rate, DT 1/8.
    python research/engine_lab/profile_assay.py <style|profile> <n> <seed>"""
import json, os, random, statistics as st, sys, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race2 as R
mode, N, SEED = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
R.P.update(break_k=0.0002, tank_full=45, mile_turns=[(0.125, 0.375), (0.625, 0.875)], stretch_at=0.875, stretch_lanes=5, route=1)
if mode == "style":
    R.P.update(gap_late=3.0, move_late=0.68)
else:
    R.P.update(profile=1, **{k: float(v) for k, v in (a.split("=") for a in os.environ.get("PSET", "").split(",") if a)})
STY = ["front", "stalk", "stalk", "mid", "mid", "late"]
rate = lambda s: 1.15 * s["early_speed"] + 0.85 * s["late_speed"] + 0.66 * s["stamina"] + 0.7 * s["gait"]
prof = lambda s: "speed" if s["early_speed"] - s["late_speed"] > 0.25 else "finisher" if s["late_speed"] - s["early_speed"] > 0.25 else "balanced"
rng = random.Random(SEED)
starters, wins, pos75, behind75, lead75_wins, best, by_plan, plan_starts = collections.Counter(), collections.Counter(), collections.Counter(), [], 0, 0, collections.Counter(), collections.Counter()
for i in range(N):
    f = []
    for k in range(8):
        stats = {t: rng.gauss(0, .4) for t in ("early_speed", "late_speed", "stamina", "gait")}
        f.append(R.Runner(f"H{k}", R.avg(**stats), rng.choice(STY), k + 1))
    o, rec = R.run(f, rng=random.Random(SEED * 10000 + i), dt=0.125)
    w = o[0]
    for h in f:
        starters[prof(h.s)] += 1; plan_starts[h.style] += 1
    wins[prof(w.s)] += 1; by_plan[w.style] += 1
    c75 = next(c for c in rec["calls"] if c["at"] == 0.75)
    order75 = [x["name"] for x in c75["horses"]]
    k = order75.index(w.name)
    pos75["1st" if k == 0 else "2nd" if k == 1 else "3rd" if k == 2 else "4th-5th" if k < 5 else "6th+"] += 1
    behind75.append(next(x["behind"] for x in c75["horses"] if x["name"] == w.name))
    lead75_wins += order75[0] == w.name
    best += w is max(f, key=lambda h: rate(h.s))
tot = sum(starters.values())
out = dict(mode=mode, races=N,
           profile_win_share={p: round(wins[p] / N, 3) for p in starters}, profile_starter_share={p: round(starters[p] / tot, 3) for p in starters},
           plan_win_share={p: round(by_plan[p] / N, 3) for p in plan_starts}, plan_starter_share={p: round(plan_starts[p] / (8 * N), 3) for p in plan_starts},
           leader_at_three_quarters_wins=round(lead75_wins / N, 3), winner_position_at_three_quarters={k: round(v / N, 3) for k, v in sorted(pos75.items())},
           winner_lengths_behind_at_three_quarters=round(st.mean(behind75), 2), best_rated_wins=round(best / N, 3))
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile"), exist_ok=True)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile", f"{mode}_{SEED}.json"), "w"), indent=1)
print(json.dumps(out))
