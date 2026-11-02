"""Review 12's two tests, on the value model value2/value_<MODEL> (default 2).
    python research/engine_lab/review12_tests.py early <track>    +0.5 early speed: fixed aims vs adaptive driving
    python research/engine_lab/review12_tests.py regret <track>   expected-action regret on untouched states
early: 20 fields x 8 subjects, breaks off, DT 1/16. "fixed" = everyone held to its baseline gate aim with learned
switching off (events still fire), baseline and upgrade alike; "adaptive" = the driver. For the subject: place at the
quarter, energy used by the quarter, extra ground, time, finish place; split by whether its baseline aim was the top or
the pocket. Then the upgraded subject's learned gate aim against all five gate aims tried (others on their plans).
regret: 20 fresh states (gate and mid-race, seeds never used in fitting), every feasible aim continued with 20 seeds
(each horse's random stream reseeded the same way in every arm), breaks at a plausible rate, DT 1/8. Reports the model's
expected regret, a split-half sample oracle's, and the hindsight advantage min_a E[L_a] - E[min_a L_a]."""
import copy, json, os, random, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import value_fit as V
R = V.R
V.setup(0)
V.load(int(os.environ.get("MODEL", "2")))
cmd, track = sys.argv[1], sys.argv[2]
TR = V.D.TR


def runners(stats, ins=None):
    return [R.Runner(f"H{k}", dict(s), "mid", k + 1, dict(ins[k]) if ins else {}) for k, s in enumerate(stats)]


if cmd == "early":
    R.P["break_k"] = 0.0
    rng = random.Random(9)
    fields = [[R.avg(**{t: rng.gauss(0, .4) for t in TR}) for _ in range(8)] for _ in range(20)]

    def race(stats, ins=None):
        f = runners(stats, ins)
        o, rec = R.run(f, track, rng=random.Random(0), dt=1 / 16)
        q = next(c for c in rec["calls"] if c["at"] == 0.25)["horses"]
        info = {x["name"]: (i + 1, x["energy"]) for i, x in enumerate(q)}
        return {h.name: dict(place=[x.name for x in o].index(h.name) + 1, time=h.time, q_place=info[h.name][0],
                             q_used=h.spent0 - info[h.name][1], ground=h.ground, aim0=h.aim0) for h in f}
    rows, match, cf_regret = [], 0, []
    for stats in fields:
        base = race(stats)
        aims = [base[f"H{k}"]["aim0"] for k in range(8)]
        fixed_ins = [{"aim": a} for a in aims]
        base_fixed = race(stats, fixed_ins)
        for k in range(8):
            up = [dict(s) for s in stats]; up[k]["early_speed"] += 0.5
            n = f"H{k}"
            ad, fx = race(up), race(up, fixed_ins)
            rows.append(dict(group="top/pocket" if aims[k] in ("top", "pocket") else "sitter",
                             **{f"{arm}_{m}": (b[n][m] - a[n][m]) for arm, a, b in (("fixed", base_fixed, fx), ("adaptive", base, ad))
                                for m in ("place", "time", "q_place", "q_used", "ground")}))
            tries = {}
            for a in R.AIMS:                            # the upgraded horse's gate aim, every choice tried
                ins = [{"start_aim": aims[j]} if j != k else {"start_aim": a} for j in range(8)]
                tries[a] = race(up, ins)[n]["place"]
            match += tries.get(ad[n]["aim0"], 9) == min(tries.values())
            cf_regret.append(tries[ad[n]["aim0"]] - min(tries.values()))
    out = {}
    for g in ("top/pocket", "sitter", "all"):
        sub = [r for r in rows if g == "all" or r["group"] == g]
        out[g] = {"n": len(sub), **{k: round(-st.mean(r[k] for r in sub), 3) for k in sub[0] if k != "group"}}
    out["learned gate aim was a best choice"] = round(match / len(cf_regret), 2)
    out["learned gate aim regret (places)"] = round(st.mean(cf_regret), 2)
    print(json.dumps(out, indent=1))
    print("(positive = the upgrade helped: places gained, seconds gained, quarter places gained, less energy used, less ground)")
else:
    rng = random.Random(4242)
    res = []
    while len(res) < 20:
        stats = [R.avg(**{t: rng.gauss(0, .4) for t in TR}) for _ in range(8)]
        at = (0.0, 0.25, 0.45)[len(res) % 3]
        f = runners(stats)
        if at == 0.0:
            R.drive_plan(f, track, {"events": []})
            plan = {h.name: h.aim for h in f}
            subj = rng.choice(f)
            arms = {a: R.aim_x(subj, f, track, a, 0.0, plan) for a in R.AIMS}

            def go(a, seed):
                g = runners(stats, [{"start_aim": a if f"H{k}" == subj.name else plan[f"H{k}"]} for k in range(8)])
                o, _ = R.run(g, track, rng=random.Random(seed), dt=0.125)
                return [h.name for h in o].index(subj.name) + 1
        else:
            o, rec = R.run(f, track, rng=random.Random(rng.random()), dt=0.125, snap_at=at)
            snap = rec.get("snap")
            cands = [h for h in snap if not h.done and not h.moving]
            if not cands:
                continue
            subj = rng.choice(cands)
            arms = {a: R.aim_x(subj, snap, track, a, rec["snap_t"]) for a in R.AIMS if R.feasible(subj, a, snap)}

            def go(a, seed, snap=snap, rec=rec, subj=subj):
                g = copy.deepcopy(snap)
                for h in g:
                    h.aim_t -= rec["snap_t"]
                    h.rng = random.Random(f"{seed}:{h.name}")
                s_ = next(h for h in g if h.name == subj.name)
                R.set_aim(s_, a, 0.0, {"events": []}, "")
                o, _ = R.run(g, track, rng=random.Random(seed), dt=0.125)
                return [h.name for h in o].index(subj.name) + 1
        if len(arms) < 2:
            continue
        L = {a: [go(a, 1000 + s) for s in range(20)] for a in arms}
        pred = {a: R.VALUE_MODEL[a]["b"] + sum(c * (v - mu) / sd for c, v, mu, sd in zip(R.VALUE_MODEL[a]["coef"], R.quad(x),
                    R.VALUE_MODEL[a]["mean"], R.VALUE_MODEL[a]["std"])) for a, x in arms.items()}
        mean = {a: st.mean(v) for a, v in L.items()}
        best = min(mean.values())
        model_reg = mean[min(pred, key=pred.get)] - best
        half = lambda a, lo: st.mean(L[a][lo:lo + 10])
        oracle_reg = st.mean(half(min(L, key=lambda a: half(a, lo)), 10 - lo) - min(half(a, 10 - lo) for a in L) for lo in (0, 10))
        hind = best - st.mean(min(L[a][s] for a in L) for s in range(20))
        spread = max(mean.values()) - best
        res.append(dict(at=at, model=model_reg, oracle=oracle_reg, hindsight=hind, spread=spread))
    print(json.dumps({k: round(st.mean(r[k] for r in res), 2) for k in ("model", "oracle", "hindsight", "spread")}),
          "(places; model and oracle = expected regret vs the best mean aim; spread = worst minus best mean aim)")
    for at in (0.0, 0.25, 0.45):
        sub = [r for r in res if r["at"] == at]
        print(f"  at {at}: model {st.mean(r['model'] for r in sub):.2f}  oracle {st.mean(r['oracle'] for r in sub):.2f}  n {len(sub)}")
