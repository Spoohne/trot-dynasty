"""Fit the race prototype's tuning table (race2.P) to targets by random search. Each worker tries configs and writes
one JSON line per config: python fit_race2.py <worker> <configs> [center.json] [scale]"""
import sys, json, random, statistics as st, os
sys.path.insert(0, r"C:\Users\spooh\HarnessSim")
import race2 as R
W, K = int(sys.argv[1]), int(sys.argv[2])
CENTER = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else dict(R.P)
SCALE = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
RANGE = dict(lead_soft=(0, 2.5), lead_dig=(0, 4), duel_until=(0.15, 0.45), close_up=(0.2, 2), kick_late=(0.8, 2.6),
             kick_early=(0.2, 1.2), tank_floor=(0.7, 0.95), tank_full=(20, 70), cost_base=(0.15, 0.5), cost_over=(0.03, 0.14),
             cost_wide=(0.03, 0.3), shelter=(0.3, 0.9), move_stalk=(0.6, 0.85), move_mid=(0.45, 0.8), move_late=(0.65, 0.9),
             move_sd=(0.03, 0.12), accel=(2.5, 5), accel_early=(0.3, 1.2), energy=(70, 130), energy_stam=(6, 20))
NOFRONT = ["stalk", "mid", "mid", "late", "stalk", "mid", "late"]
STY = ["front", "stalk", "stalk", "mid", "mid", "late"]
rate = lambda s: 1.15 * s["early_speed"] + 0.85 * s["late_speed"] + 0.66 * s["stamina"] + 0.7 * s["gait"]


def noise(r):
    return R.avg(**{t: r.gauss(0, .4) for t in ("early_speed", "late_speed", "stamina", "gait")})


def field(r, subj, styles):
    hs = [subj] + [R.Runner(f"H{k}", noise(r), s, 0) for k, s in enumerate(styles)]
    posts = list(range(len(hs))); r.shuffle(posts)
    for p, h in zip(posts, hs):
        h.post, h.pos, h.lane = p + 1, -0.6 * R.LEN * p * 0.15, 0 if p == 0 else min(2, p // 3)
    return hs


def win(r, mk, n):
    w = 0
    for _ in range(n):
        o, _ = R.run(mk(r), rng=r, record=False)
        w += o[0].name == "S"
    return w / n


def evaluate(seed, n=150, m=300):
    r = random.Random(seed)
    m_ = {}
    m_["lead"] = win(r, lambda r: field(r, R.Runner("S", noise(r), "front", 1, {"leave": True}), NOFRONT), n)
    m_["sit"] = win(r, lambda r: field(r, R.Runner("S", noise(r), "front", 1, {"leave": False, "move_at": 0.7}), NOFRONT), n)
    m_["duel"] = win(r, lambda r: field(r, R.Runner("S", noise(r), "front", 1, {"leave": True}), ["front"] + NOFRONT[1:]), n)
    m_["closer_calm"] = win(r, lambda r: field(r, R.Runner("S", noise(r), "late", 1), ["front", "stalk", "mid", "mid", "stalk", "mid", "late"]), n)
    m_["closer_duel"] = win(r, lambda r: field(r, R.Runner("S", noise(r), "late", 1), ["front", "front", "mid", "mid", "stalk", "mid", "late"]), n)
    m_["cover"] = win(r, lambda r: field(r, R.Runner("S", noise(r), "late", 1, {"move_at": 0.62, "follow": True}), ["stalk", "front"] + NOFRONT[2:]), n)
    m_["first_over"] = win(r, lambda r: field(r, R.Runner("S", noise(r), "late", 1, {"move_at": 0.5, "follow": False}), ["stalk", "front"] + NOFRONT[2:]), n)
    m_["early_avg"] = win(r, lambda r: field(r, R.Runner("S", noise(r), "mid", 1, {"move_at": 0.3, "follow": False}), NOFRONT), n)
    m_["wait_avg"] = win(r, lambda r: field(r, R.Runner("S", noise(r), "mid", 1, {"move_at": 0.72}), NOFRONT), n)
    m_["early_strong"] = win(r, lambda r: field(r, R.Runner("S", R.avg(early_speed=1.2, late_speed=1.2, stamina=1.2), "mid", 1, {"move_at": 0.3, "follow": False}), NOFRONT), n)
    sw, best, wire, times = {k: 0 for k in set(STY)}, 0, 0, []
    for _ in range(m):
        f = [R.Runner(f"H{k}", noise(r), r.choice(STY), k + 1) for k in range(8)]
        o, rec = R.run(f, rng=r)
        sw[o[0].style] += 1
        best += o[0] is max(f, key=lambda h: rate(h.s))
        wire += all(c["horses"][0]["name"] == o[0].name for c in rec["calls"])
        times.append(o[0].time)
    share = {k: STY.count(k) / len(STY) for k in sw}
    m_.update(style={k: round(v / m, 3) for k, v in sw.items()}, best=best / m, wire=wire / m, time=st.median(times))
    return m_


def loss(x):
    L = sum(abs(x["style"][k] / s - 1) for k, s in {"front": 1 / 6, "stalk": 1 / 3, "mid": 1 / 3, "late": 1 / 6}.items())
    hinge = lambda v, lo, hi: max(0, lo - v) + max(0, v - hi)
    L += 6 * hinge(x["best"], 0.20, 0.32) + 4 * hinge(x["wire"], 0.15, 0.35)
    L += 4 * hinge(x["lead"] / max(x["sit"], 0.01), 1.3, 4.0) + 4 * hinge(x["lead"], 0.1, 0.45)
    L += 4 * hinge(x["duel"] / max(x["lead"], 0.01), 0.4, 0.85)               # a duel costs the leader
    L += 4 * hinge(x["closer_duel"] - x["closer_calm"], 0.02, 1)                # a hot pace helps the closer
    L += 4 * hinge(x["cover"] - x["first_over"], 0.01, 1)                       # cover pays
    L += 4 * hinge(x["wait_avg"] - x["early_avg"], 0.0, 1)                      # an average horse pays for an early move
    L += 4 * hinge(x["early_strong"], 0.35, 0.8)                                # class can survive a poor trip, not always
    L += 2 * hinge(x["time"], 109, 114)                                         # a plausible winning time (raw seconds)
    return L


if __name__ == "__main__":
    rng = random.Random(1000 + W)
    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fit", f"w{W}.jsonl"), "a")
    for k in range(K):
        cfg = {key: (min(hi, max(lo, CENTER[key] + rng.gauss(0, SCALE * 0.25 * (hi - lo)))) if SCALE < 1 else rng.uniform(lo, hi))
               for key, (lo, hi) in RANGE.items()}
        if W == 0 and k == 0:
            cfg = dict(CENTER)
        R.P.update(cfg)
        x = evaluate(seed=W * 1000 + k)
        out.write(json.dumps(dict(loss=round(loss(x), 3), cfg=cfg, m=x)) + "\n"); out.flush()
