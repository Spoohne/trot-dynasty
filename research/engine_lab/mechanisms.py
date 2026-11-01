"""Race prototype mechanism tests (review 2, section 3). Fixed horses, breaks off (manners +6), move points fixed, so
each comparison changes one thing.  python research/engine_lab/mechanisms.py"""
import copy, json, os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race2 as R
HERE = os.path.dirname(os.path.abspath(__file__))
out = {}
SMOOTH = 6.0


def H(name, style, post, instr=None, **k):
    return R.Runner(name, R.avg(**{"gait": SMOOTH, **k}), style, post, dict(instr or {}))


def stats(r):
    return {t: r.gauss(0, .4) for t in ("early_speed", "late_speed", "stamina")}


def place(f, at=None):
    for k, h in enumerate(f):
        h.post = k + 1
        if at is None:
            h.pos, h.lane = -0.6 * R.LEN * k * 0.15, 0 if k == 0 else min(2, k // 3)
    return f


# ---- 0. convergence: fixed 8-horse fields, move points set, no breaks; pathwise against DT 0.0625
rng = random.Random(3)
STY = ["front", "stalk", "stalk", "mid", "mid", "late"]
fields = []
for _ in range(200):
    f = []
    for k in range(8):
        s = rng.choice(STY)
        f.append(H(f"H{k}", s, k + 1, {"move_at": {"front": 9, "stalk": .72, "mid": .6, "late": .74}[s] + rng.gauss(0, .07)}, **stats(rng)))
    fields.append(place(f))
ref = {}
conv = {}
for dt in (0.0625, 0.125, 0.25, 0.5):
    same, dtime, styles = 0, [], {s: 0 for s in set(STY)}
    for i, f in enumerate(fields):
        o, _ = R.run(copy.deepcopy(f), rng=random.Random(i), dt=dt)
        if dt == 0.0625:
            ref[i] = (o[0].name, o[0].time)
        same += o[0].name == ref[i][0]; dtime.append(abs(o[0].time - ref[i][1])); styles[o[0].style] += 1
    conv[f"DT {dt}"] = dict(same_winner_as_finest=round(same / len(fields), 3), mean_abs_time_diff=round(st.mean(dtime), 3),
                            style_wins={k: round(v / len(fields), 3) for k, v in styles.items()})
out["0_convergence"] = conv


# ---- 1. forced box: start at the three-quarters, subject on the rail a length behind the leader, rival outside it
def box_case(with_rival, seed=1):
    lead = H("lead", "front", 1, {"leave": True}); subj = H("S", "stalk", 2, {"move_at": 0.99, "pull": False}, late_speed=0.8)
    f = [lead, subj]
    if with_rival:
        f.append(H("rival", "mid", 3, {"press_until": 0.97}))     # stays alongside the leader's quarters: the subject's way out
    at = 0.75 * R.FT_MILE
    lead.pos, lead.lane = at, 0
    subj.pos, subj.lane = at - R.LEN, 0
    for h in f:
        h.v, h.energy, h.moving = R.CRUISE, 40.0, h is not lead
    if with_rival:
        f[2].pos, f[2].lane = at - R.LEN, 1
    o, rec = R.run(f, rng=random.Random(seed), dt=0.25)
    return dict(order=[h.name for h in o], subject_boxed_s=round(subj.boxed_t, 2), subject_time=round(subj.time, 2))


out["1_forced_box"] = {"with rival outside": box_case(True), "rival removed": box_case(False)}


# ---- 2. energy dose: the subject alone in an open stretch from the three-quarters with set energy
def stretch(energy):
    h = H("S", "mid", 1)
    h.pos, h.lane, h.v, h.energy, h.moving = 0.75 * R.FT_MILE, 1, R.CRUISE, energy, True
    o, _ = R.run([h], rng=random.Random(1), dt=0.25)
    return round(h.time, 3)


base_t = None
dose = {}
for e_ in (0, 15, 30, 45, 75):
    dose[e_] = stretch(e_)
out["2a_energy_dose_last_quarter_time"] = dose
# actual energies at the three-quarters, by trip
by = {"sheltered >= 20s": [], "sheltered < 20s": [], "moved before 0.55": [], "moved after 0.7": []}
rng = random.Random(9)
for i in range(400):
    f = place([R.Runner(f"H{k}", R.avg(**stats(rng), gait=rng.gauss(0, .4)), rng.choice(STY), k + 1) for k in range(8)])
    o, rec = R.run(f, rng=random.Random(100 + i), dt=0.25)
    c75 = next(c for c in rec["calls"] if c["at"] == 0.75)
    e75 = {x["name"]: x["energy"] for x in c75["horses"]}
    for h in f:
        by["sheltered >= 20s" if h.shelter_t >= 20 else "sheltered < 20s"].append(e75[h.name])
        ma = h.instr.get("move_at", 1)
        if ma < 0.55:
            by["moved before 0.55"].append(e75[h.name])
        elif 0.7 < ma < 1:
            by["moved after 0.7"].append(e75[h.name])
out["2b_energy_at_three_quarters"] = {k: dict(n=len(v), mean=round(st.mean(v), 1), p10=round(sorted(v)[len(v) // 10], 1),
                                             share_above_45=round(sum(x > 45 for x in v) / len(v), 3)) for k, v in by.items() if v}

# ---- 3. shelter: same following trip, the discount on vs off (paired fields, same random stream)
NOFRONT = ["stalk", "mid", "mid", "late", "stalk", "mid", "late"]
rng = random.Random(11)
res = {"on": [], "off": []}
for i in range(500):
    base = place([H("S", "late", 1, {"move_at": 0.62, "follow": True}, **stats(rng))] +
                 [R.Runner(f"H{k}", R.avg(**stats(rng), gait=rng.gauss(0, .4)), s, k + 2) for k, s in enumerate(["front"] + NOFRONT[1:])])
    for arm in ("on", "off"):
        f = copy.deepcopy(base)
        if arm == "off":
            f[0].instr["no_shelter"] = True
        o, rec = R.run(f, rng=random.Random(700 + i), dt=0.25)
        c75 = next(c for c in rec["calls"] if c["at"] == 0.75)
        res[arm].append((o[0].name == "S", next(x["energy"] for x in c75["horses"] if x["name"] == "S"), f[0].shelter_t, [h.name for h in o].index("S") + 1))
out["3_shelter_on_vs_off"] = {arm: dict(win=round(st.mean(x[0] for x in v), 3), energy_75=round(st.mean(x[1] for x in v), 1),
                                         sheltered_s=round(st.mean(x[2] for x in v), 1), mean_place=round(st.mean(x[3] for x in v), 2)) for arm, v in res.items()}


# ---- 4. the duel: three scripted openings, drivers released at the half
def duel(arm, n=500):
    rng = random.Random(21)
    w, e75, q1, led_q = [], [], [], []
    for i in range(n):
        subj = H("S", "front", 1, {"leave": True}, **stats(rng))
        rival_instr = {"unchallenged": {"leave": False, "move_at": 0.7},
                       "pressed alongside": {"press_until": 0.5, "move_at": 0.7},
                       "rival clears": {"leave": True}}[arm]
        rival_stats = dict(stats(rng), **({"early_speed": 1.5} if arm == "rival clears" else {}))
        rival = H("R", "front" if arm != "unchallenged" else "stalk", 2, rival_instr, **rival_stats)
        rest = [R.Runner(f"H{k}", R.avg(**stats(rng), gait=rng.gauss(0, .4)), s, k + 3) for k, s in enumerate(NOFRONT[:6])]
        f = place([subj, rival] + rest)
        o, rec = R.run(f, rng=random.Random(900 + i), dt=0.25)
        c25 = next(c for c in rec["calls"] if c["at"] == 0.25); c75 = next(c for c in rec["calls"] if c["at"] == 0.75)
        w.append(o[0].name == "S"); e75.append(next(x["energy"] for x in c75["horses"] if x["name"] == "S"))
        q1.append(c25["t"]); led_q.append(c25["horses"][0]["name"] == "S")
    return dict(subject_win=round(st.mean(w), 3), subject_energy_75=round(st.mean(e75), 1), first_quarter_s=round(st.mean(q1), 2),
                subject_leads_at_quarter=round(st.mean(led_q), 3))


out["4_duel_openings"] = {arm: duel(arm) for arm in ("unchallenged", "pressed alongside", "rival clears")}
json.dump(out, open(os.path.join(HERE, "mechanisms.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
