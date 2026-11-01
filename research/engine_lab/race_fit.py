"""Gated fit of the race prototype (review 4, item 34). Hard gates first; a config that fails any gate is rejected whatever
its score. Soft targets (style balance, winning times) only rank configs that pass.
    python research/engine_lab/race_fit.py screen <worker> <n>     random configs near today's, screened at DT 1/8
    python research/engine_lab/race_fit.py gate <config.json>      every gate at DT 1/16 (+ 1/32 robustness)
The scenario bank is fixed by seed before any search; held-out validation uses other seeds and conditions."""
import copy, json, os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race2 as R
HERE = os.path.dirname(os.path.abspath(__file__))
SM = 6.0
STY = ["front", "stalk", "stalk", "mid", "mid", "late"]
NOFRONT = ["stalk", "mid", "mid", "late", "stalk", "mid", "late"]
SEARCH = dict(kick_late=(1.0, 2.4), kick_early=(0.2, 1.0), tank_floor=(0.75, 0.93), tank_full=(30, 65), cost_base=(0.2, 0.45),
              cost_over=(0.04, 0.12), cost_wide=(0.05, 0.25), shelter=(0.35, 0.8), lead_dig=(0.0, 2.0), lead_soft=(0.0, 1.5),
              gap_stalk=(0.8, 3.0), gap_mid=(2.5, 6.0), gap_late=(4.0, 10.0), gap_k=(0.15, 0.6), gap_chase=(0.8, 3.0),
              move_stalk=(0.62, 0.82), move_mid=(0.5, 0.75), move_late=(0.65, 0.88), break_k=(0.0001, 0.0012))


def H(name, style, post, instr=None, **k):
    return R.Runner(name, R.avg(**{"gait": SM, **k}), style, post, dict(instr or {}))


def rnd_stats(r, sd=.4, gait=None):
    s = {t: r.gauss(0, sd) for t in ("early_speed", "late_speed", "stamina")}
    s["gait"] = r.gauss(0, sd) if gait is None else gait
    return s


def place(f):
    for k, h in enumerate(f):
        h.post, h.pos, h.lane = k + 1, -0.05 * R.LEN * k, k
    return f


def overlaps(field, dt, seed):
    """Run with a per-step geometry audit: two horses in one lane closer than a length is an overlap."""
    bad = [0]
    real = R.run
    o, rec = real(field, rng=random.Random(seed), dt=dt)
    return rec.get("crossings", 0) + rec.get("overlaps", 0)


# ---------------------------------------------------------------- hard gates
def g_geometry(dt):
    rng = random.Random(1)
    bad = 0
    for i in range(80):
        f = place([R.Runner(f"H{k}", R.avg(**rnd_stats(rng)), rng.choice(STY), k + 1) for k in range(rng.choice((6, 8, 10)))])
        bad += overlaps(f, dt, i)
    return dict(ok=bad == 0, violations=bad)


def g_energy(dt):
    t = []
    for e_ in (0, 15, 30, 45, 75):
        h = H("S", "mid", 1); h.pos, h.lane, h.v, h.energy, h.moving = 0.75 * R.FT_MILE, 1, R.CRUISE, e_, True
        R.run([h], rng=random.Random(1), dt=dt); t.append(h.time)
    return dict(ok=all(a > b for a, b in zip(t, t[1:])) and t[0] - t[3] >= 0.3, times=[round(x, 2) for x in t])


def g_shelter(dt, n=200):
    rng = random.Random(11); res = {"on": [], "off": []}
    for i in range(n):
        base = place([H("S", "late", 1, {"move_at": 0.62}, **rnd_stats(rng, gait=SM))] +
                     [R.Runner(f"H{k}", R.avg(**rnd_stats(rng)), s, k + 2) for k, s in enumerate(["front"] + NOFRONT[1:])])
        for arm in ("on", "off"):
            f = copy.deepcopy(base)
            if arm == "off":
                f[0].instr["no_shelter"] = True
            o, rec = R.run(f, rng=random.Random(700 + i), dt=dt)
            c75 = next(c for c in rec["calls"] if c["at"] == 0.75)
            res[arm].append(([h.name for h in o].index("S"), next(x["energy"] for x in c75["horses"] if x["name"] == "S")))
    place_gain = st.mean(x[0] for x in res["off"]) - st.mean(x[0] for x in res["on"])
    e_gain = st.mean(x[1] for x in res["on"]) - st.mean(x[1] for x in res["off"])
    return dict(ok=place_gain > 0 and e_gain > 2, place_gain=round(place_gain, 2), energy_gain=round(e_gain, 1))


def g_box(dt):
    out = {}
    for at in (0.6, 0.75):
        t = {}
        for ghost in (False, True):
            v = R.CRUISE
            lead = H("lead", "front", 1, {"fixed_v": v, "lane_lock": 0}); subj = H("S", "stalk", 2, {"move_at": 0.0, "no_shelter": True}, late_speed=0.8)
            blk = H("blocker", "mid", 3, {"fixed_v": v, "lane_lock": 1, "ghost": ghost})
            p = at * R.FT_MILE
            lead.pos, subj.pos, blk.pos, lead.lane, subj.lane, blk.lane = p, p - R.LEN, p - R.LEN, 0, 0, 1
            for h in (lead, subj, blk):
                h.v, h.energy, h.moving = v, 60.0, True
            R.run([lead, subj, blk], rng=random.Random(1), dt=dt)
            t[ghost] = (subj.time, subj.boxed_t)
        out[at] = dict(cost=round(t[False][0] - t[True][0], 3), boxed_s=round(t[False][1], 2))
    return dict(ok=all(v["cost"] > 0.1 and v["boxed_s"] > 1 for v in out.values()), by_start=out)


def g_pace(dt, n=120):
    """Scripted openings: the leader holds a set speed to the half, then is released. The field must sit closer and pay."""
    rows = []
    for v in (R.CRUISE - 1.0, R.CRUISE + 0.5, R.CRUISE + 2.0):
        rng = random.Random(31); gap, en = [], []
        for i in range(n):
            lead = H("L", "front", 1, {"leave": True, "fixed_v": v, "lane_lock": 0, "fixed_until": 0.5})
            f = place([lead] + [R.Runner(f"H{k}", R.avg(**rnd_stats(rng, gait=SM)), s, k + 2) for k, s in enumerate(NOFRONT)])
            o, rec = R.run(f, rng=random.Random(100 + i), dt=dt)
            c5 = next(c for c in rec["calls"] if c["at"] == 0.5)
            gap.append(st.mean(x["behind"] for x in c5["horses"] if x["name"] != "L")); en.append(st.mean(x["energy"] for x in c5["horses"] if x["name"] != "L"))
        rows.append((round(st.mean(gap), 2), round(st.mean(en), 1)))
    gaps, ens = [r[0] for r in rows], [r[1] for r in rows]
    return dict(ok=gaps[2] >= gaps[0] and ens[2] < ens[0] - 3 and ens[1] <= ens[0] + 2, slow_mid_fast=rows)   # a fast opening costs the field


def g_class(dt, n=200):
    out = {}
    rng = random.Random(41)
    for boost in (1.0, 2.0):
        w = 0
        for i in range(n):
            subj = R.Runner("S", R.avg(**{t: boost for t in ("early_speed", "late_speed", "stamina")}, gait=0.0), rng.choice(STY), 1)
            f = place([subj] + [R.Runner(f"H{k}", R.avg(**rnd_stats(rng)), rng.choice(STY), k + 2) for k in range(7)])
            rng.shuffle(f); place(f)
            o, _ = R.run(f, rng=random.Random(200 + i), dt=dt); w += o[0].name == "S"
        out[boost] = round(w / n, 3)
    brk = {}
    for g in (-2.0, 2.0):
        b = 0
        for i in range(n):
            f = place([R.Runner(f"H{k}", R.avg(gait=g), rng.choice(STY), k + 1) for k in range(8)])
            o, rec = R.run(f, rng=random.Random(300 + i), dt=dt); b += sum(1 for e_ in rec["events"] if "broke" in e_[2])
        brk[g] = round(b / (n * 8), 4)
    return dict(ok=out[1.0] >= 0.30 and out[2.0] >= 0.55 and brk[-2.0] > brk[2.0] and 0.08 <= brk[-2.0] <= 0.35, win=out, breaks_per_start=brk)


def g_robust(n=150):
    rng = random.Random(3); fields = []
    for _ in range(n):
        f = []
        for k in range(8):
            s_ = rng.choice(STY)
            f.append(H(f"H{k}", s_, k + 1, {"move_at": {"front": 9, "stalk": R.P["move_stalk"], "mid": R.P["move_mid"], "late": R.P["move_late"]}[s_] + rng.gauss(0, .07)},
                       **{t: rng.gauss(0, .4) for t in ("early_speed", "late_speed", "stamina")}))
        fields.append(place(f))
    a = [R.run(copy.deepcopy(f), rng=random.Random(i), dt=1 / 16)[0] for i, f in enumerate(fields)]
    b = [R.run(copy.deepcopy(f), rng=random.Random(i), dt=1 / 32)[0] for i, f in enumerate(fields)]
    big = sum(1 for x, y in zip(a, b) if x[0].name != y[0].name and y[1].time - y[0].time >= 0.1)
    return dict(ok=big / n <= 0.03, same_winner=round(sum(x[0].name == y[0].name for x, y in zip(a, b)) / n, 3), large_margin_flips=big)


GATES = [("geometry", g_geometry), ("energy", g_energy), ("shelter", g_shelter), ("box", g_box), ("pace", g_pace), ("class", g_class)]


# ---------------------------------------------------------------- soft targets (rank only)
def soft(dt, n=300):
    rng = random.Random(77)
    sw, times, leaders = {s: 0 for s in set(STY)}, [], []
    for i in range(n):
        f = place([R.Runner(f"H{k}", R.avg(**rnd_stats(rng)), rng.choice(STY), k + 1) for k in range(8)])
        o, rec = R.run(f, rng=random.Random(500 + i), dt=dt)
        sw[o[0].style] += 1; times.append(o[0].time)
        leaders.append(len({c["horses"][0]["name"] for c in rec["calls"]} | {o[0].name}))
    share = {s: STY.count(s) / len(STY) for s in sw}
    style_dev = sum(abs(sw[s] / n / share[s] - 1) for s in sw)
    time_pen = max(0, 109 - st.median(times)) + max(0, st.median(times) - 114)
    return dict(loss=round(style_dev + time_pen, 3), style={k: round(v / n, 3) for k, v in sw.items()}, median_time=round(st.median(times), 2),
                lead_changes=round(sum(x > 1 for x in leaders) / n, 3))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "screen":
        w, n = int(sys.argv[2]), int(sys.argv[3])
        rng = random.Random(2000 + w); base = dict(R.P)
        os.makedirs(os.path.join(HERE, "fit"), exist_ok=True)
        f = open(os.path.join(HERE, "fit", f"screen_w{w}.jsonl"), "a")
        for k in range(n):
            cfg = dict(base) if (w == 0 and k == 0) else {**base, **{p: min(hi, max(lo, base.get(p, (lo + hi) / 2) + rng.gauss(0, 0.2 * (hi - lo)))) for p, (lo, hi) in SEARCH.items()}}
            R.P.clear(); R.P.update(cfg)
            res = dict(cfg=cfg, soft=soft(1 / 8))
            for name, g in GATES:                             # cheap gates at screening resolution; a failure stops the config
                r_ = g(1 / 8); res[name] = r_
                if not r_["ok"]:
                    break
            res["passed_screen"] = all(res.get(name, {}).get("ok") for name, _ in GATES)
            f.write(json.dumps(res) + "\n"); f.flush()
    elif mode == "gate":
        cfg = json.load(open(sys.argv[2])); R.P.clear(); R.P.update(cfg)
        res = {name: g(1 / 16) for name, g in GATES}
        res["robust_1_32"] = g_robust(); res["soft"] = soft(1 / 16)
        res["all_gates_pass"] = all(v["ok"] for k, v in res.items() if k != "soft")
        print(json.dumps(res, indent=1))
