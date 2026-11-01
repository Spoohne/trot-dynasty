"""Review 3 race tests: pace response, a scripted forced box, and DT 1/16 vs 1/32.
    python research/engine_lab/mechanisms2.py"""
import copy, json, os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race2 as R
HERE = os.path.dirname(os.path.abspath(__file__))
DT = 0.125
out = {}
SM = 6.0
NOFRONT = ["stalk", "mid", "mid", "late", "stalk", "mid", "late"]


def H(name, style, post, instr=None, **k):
    return R.Runner(name, R.avg(**{"gait": SM, **k}), style, post, dict(instr or {}))


def stats(r):
    return {t: r.gauss(0, .4) for t in ("early_speed", "late_speed", "stamina")}


def place(f):
    for k, h in enumerate(f):
        h.post, h.pos, h.lane = k + 1, -0.6 * R.LEN * k * 0.15, 0 if k == 0 else min(2, k // 3)
    return f


# ---- 1. pace response: the leader's opening speed set by its early speed; does the field follow, and pay to?
def opening(es, n=300):
    rng = random.Random(31)
    gaps, fe, le, w = [], [], [], []
    for i in range(n):
        f = place([H("L", "front", 1, {"leave": True}, **dict(stats(rng), early_speed=es))] +
                  [R.Runner(f"H{k}", R.avg(**stats(rng), gait=SM), s, k + 2) for k, s in enumerate(NOFRONT)])
        o, rec = R.run(f, rng=random.Random(1000 + i), dt=DT)
        c5 = next(c for c in rec["calls"] if c["at"] == 0.5); c75 = next(c for c in rec["calls"] if c["at"] == 0.75)
        gaps.append(st.mean(x["behind"] for x in c5["horses"] if x["name"] != "L"))
        fe.append(st.mean(x["energy"] for x in c75["horses"] if x["name"] != "L"))
        le.append(next(x["energy"] for x in c75["horses"] if x["name"] == "L"))
        w.append(o[0].name == "L")
    return dict(field_gap_at_half=round(st.mean(gaps), 2), field_energy_75=round(st.mean(fe), 1), leader_energy_75=round(st.mean(le), 1), leader_win=round(st.mean(w), 3))


out["1_pace_response_by_leader_early_speed"] = {es: opening(es) for es in (-1.0, 0.0, 1.0, 2.0)}


def duel(arm, n=400):
    rng = random.Random(21)
    w, e75 = [], []
    for i in range(n):
        subj = H("S", "front", 1, {"leave": True}, **stats(rng))
        ri = {"unchallenged": {"leave": False, "move_at": 0.7}, "pressed alongside": {"press_until": 0.5, "move_at": 0.7},
              "rival clears": {"leave": True}}[arm]
        rival = H("R", "front" if arm != "unchallenged" else "stalk", 2, ri, **dict(stats(rng), **({"early_speed": 1.5} if arm == "rival clears" else {})))
        f = place([subj, rival] + [R.Runner(f"H{k}", R.avg(**stats(rng), gait=SM), s, k + 3) for k, s in enumerate(NOFRONT[:6])])
        o, rec = R.run(f, rng=random.Random(900 + i), dt=DT)
        c75 = next(c for c in rec["calls"] if c["at"] == 0.75)
        w.append(o[0].name == "S"); e75.append(next(x["energy"] for x in c75["horses"] if x["name"] == "S"))
    return dict(subject_win=round(st.mean(w), 3), subject_energy_75=round(st.mean(e75), 1))


out["1b_duel_openings"] = {a: duel(a) for a in ("unchallenged", "pressed alongside", "rival clears")}


# ---- 2. scripted forced box: leader and blocker hold set speeds in locked lanes; the subject wants out
def box(ghost):
    at, v = 0.75 * R.FT_MILE, R.CRUISE
    lead = H("lead", "front", 1, {"fixed_v": v, "lane_lock": 0})
    subj = H("S", "stalk", 2, {"move_at": 0.0, "no_shelter": True}, late_speed=0.8)
    blk = H("blocker", "mid", 3, {"fixed_v": v, "lane_lock": 1, "ghost": ghost})
    lead.pos, subj.pos, blk.pos = at, at - R.LEN, at - R.LEN
    lead.lane, subj.lane, blk.lane = 0, 0, 1
    for h in (lead, subj, blk):
        h.v, h.energy, h.moving = v, 60.0, True
    subj.moving = True
    track = []
    f = [lead, subj, blk]
    # run 8 seconds by stepping the engine on a copy truncated by distance: measure ground made in the first 8 s
    o, rec = R.run(f, rng=random.Random(1), dt=DT)
    return dict(subject_time_from_three_quarters=round(subj.time, 3), leader_time=round(lead.time, 3), boxed_s=round(subj.boxed_t, 2),
                finished_ahead_of_leader=subj.time < lead.time, lane_at_finish=subj.lane)


out["2_scripted_forced_box"] = {"blocked": box(False), "open (blocker is a ghost)": box(True)}

# ---- 3. step size: 1/16 vs 1/32, fixed move points, no breaks, 200 fields
rng = random.Random(3)
STY = ["front", "stalk", "stalk", "mid", "mid", "late"]
fields = []
for _ in range(200):
    f = []
    for k in range(8):
        s_ = rng.choice(STY)
        f.append(H(f"H{k}", s_, k + 1, {"move_at": {"front": 9, "stalk": .72, "mid": .6, "late": .74}[s_] + rng.gauss(0, .07)}, **stats(rng)))
    fields.append(place(f))
res = {}
for dt in (0.03125, 0.0625, 0.125):
    res[dt] = [R.run(copy.deepcopy(f), rng=random.Random(i), dt=dt)[0] for i, f in enumerate(fields)]
conv = {}
for dt in (0.0625, 0.125):
    same = [a[0].name == b[0].name for a, b in zip(res[dt], res[0.03125])]
    margin = [b[1].time - b[0].time for b in res[0.03125]]
    flips_close = sum(1 for s_, m in zip(same, margin) if not s_ and m < 0.1)
    conv[f"DT {dt} vs 1/32"] = dict(same_winner=round(st.mean(same), 3), flips=len(same) - sum(same), flips_with_margin_under_0p1s=flips_close,
                                    mean_abs_time_diff=round(st.mean(abs(a[0].time - b[0].time) for a, b in zip(res[dt], res[0.03125])), 3))
out["3_step_size_vs_1_32"] = conv
json.dump(out, open(os.path.join(HERE, "mechanisms2.json"), "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
