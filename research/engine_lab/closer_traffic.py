"""Closer traffic test (review 5, item 54): the same closer in the same races, normal traffic vs a clear path (it can't be
blocked, boxed or sheltered by anyone; it still covers its own ground). DT 1/8, plausible breaks, 400 paired races."""
import copy, json, os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race2 as R
R.P.update(break_k=0.0002)
STY = ["front", "stalk", "stalk", "mid", "mid", "late"]
rng = random.Random(5)
res = {"traffic": [], "clear": []}
for i in range(400):
    base = [R.Runner("S", R.avg(**{t: rng.gauss(0, .4) for t in ("early_speed", "late_speed", "stamina", "gait")}), "late", 1)]
    base += [R.Runner(f"H{k}", R.avg(**{t: rng.gauss(0, .4) for t in ("early_speed", "late_speed", "stamina", "gait")}), rng.choice(STY), k + 2) for k in range(7)]
    posts = list(range(8)); rng.shuffle(posts)
    for p_, h in zip(posts, base):
        h.post, h.pos, h.lane = p_ + 1, -0.05 * R.LEN * p_, p_
    for arm in ("traffic", "clear"):
        f = copy.deepcopy(base)
        if arm == "clear":
            f[0].instr["clear_path"] = True
        o, rec = R.run(f, rng=random.Random(900 + i), dt=0.125)
        s_ = f[0]
        res[arm].append(([h.name for h in o].index("S") + 1, s_.energy, s_.boxed_t, s_.ground, s_.time - o[0].time))
out = {arm: dict(win=round(st.mean(x[0] == 1 for x in v), 3), place=round(st.mean(x[0] for x in v), 2), energy_end=round(st.mean(x[1] for x in v), 1),
                 boxed_s=round(st.mean(x[2] for x in v), 2), extra_ground_ft=round(st.mean(x[3] for x in v), 1), behind_winner_s=round(st.mean(x[4] for x in v), 2))
       for arm, v in res.items()}
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "closer_traffic.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
