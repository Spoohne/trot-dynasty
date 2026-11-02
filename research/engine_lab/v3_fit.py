"""Stage 3 fit to the DECISIONS 143 contract: random search over the single-horse settings, scored on the clocks
and on what +0.5 in each trait is worth (gate aims frozen, breaks off, DT 1/16). The same 12 fields and the same 4
subjects per field for every candidate (common random numbers), both tracks.
    python research/engine_lab/v3_fit.py eval '<json settings>'       one candidate, prints its metrics and loss
    python research/engine_lab/v3_fit.py search <rounds> <width>       rounds of 8 candidates around the best so far"""
import json, os, random, statistics as st, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
TARGET = {"half": dict(cruise=0.35, gate=0.05, kick=0.20, grit=0.12, time=115.9),   # gate amended (DECISIONS 189)
          "mile": dict(cruise=0.20, gate=0.05, kick=0.45, grit=0.12, time=113.4)}
KNOBS = dict(pace_k=(0.9, 1.1), c_turn=(0.0, 0.0006), k_kick=(1.0, 4.0), a_gate=(0.5, 3.0), burst_gate=(0.5, 4.0),
             launch_ft=(400.0, 1200.0), p_cruise=(0.03, 0.10), duel=(0.1, 0.8), k_grit=(0.3, 1.0), e_max=(8.0, 20.0),
             fade=(0.2, 0.8), v_top=(52.0, 57.0), d_s_top=(0.0, 6.0), d_s_pocket=(0.0, 4.0), d_gate_pace=(0.0, 1.5),
             d_s_close_kick=(0.0, 2.5), d_s_follow_kick=(0.0, 2.0))
LOG = os.path.join(HERE, "v3", os.environ.get("FIT_LOG", "fit_log.jsonl"))   # FIT_LOG: a fresh search per regime
BAND = float(os.environ.get("FIT_CLOCK_BAND", "0"))   # s either side of the clock target that costs nothing (DECISIONS 177: display map)
FIXED = json.loads(os.environ.get("FIT_FIXED", "{}"))                        # FIT_FIXED: held in every candidate


def evaluate(cfg):
    import race3 as R, drive3 as DR
    R.P.update({k: v for k, v in cfg.items() if not k.startswith("d_")})
    DR.D.update({k[2:]: v for k, v in cfg.items() if k.startswith("d_")})   # d_ settings are driver habits
    R.P["break_b0"] = 0.0
    TR = ("gate", "cruise", "kick", "manners", "grit")
    out, loss = {}, 0.0
    for tr in ("half", "mile"):
        rng = random.Random(21)
        fields = [[{t: rng.gauss(0, .4) for t in TR} for _ in range(8)] for _ in range(12)]
        subj = [rng.sample(range(8), 4) for _ in fields]

        def race(stats, plan=None):
            drv = DR.Driver(gate_aims=plan)
            f = [R.Horse(f"H{k+1}", dict(stats[k]), k + 1, R.TRACKS[tr]) for k in range(8)]
            o, _ = R.run(f, tr, drv, seed=1, dt=1 / 16, record=False)
            return [h.name for h in o], drv, o[0].time
        wins, gains = [], {t: [] for t in ("gate", "cruise", "kick", "grit")}
        for stats, ks in zip(fields, subj):
            order, drv, wt = race(stats)
            wins.append(wt)
            plan = {n: s_["trip"][0].split(": ")[1].replace("-", "_") for n, s_ in drv.state.items()}
            for trait in gains:
                for k in ks:
                    up = [dict(x) for x in stats]; up[k][trait] += 0.5
                    o2, _, _ = race(up, plan)
                    gains[trait].append(order.index(f"H{k+1}") - o2.index(f"H{k+1}"))
        m = {t: round(st.mean(v), 3) for t, v in gains.items()}
        m["time"] = round(st.median(wins), 2)
        out[tr] = m
        tg = TARGET[tr]
        loss += sum(((m[t] - tg[t]) / 0.08) ** 2 for t in ("cruise", "gate", "kick", "grit")) + (max(0.0, abs(m["time"] - tg["time"]) - BAND) / 0.5) ** 2
    return out, round(loss, 2)


if __name__ == "__main__":
    if sys.argv[1] == "eval":
        cfg = json.loads(sys.argv[2])
        out, loss = evaluate(cfg)
        print(json.dumps(dict(cfg=cfg, out=out, loss=loss)))
    else:
        rounds, width = int(sys.argv[2]), float(sys.argv[3])
        import race3 as R, drive3 as DR
        best = {k: (DR.D[k[2:]] if k.startswith("d_") else R.P[k]) for k in KNOBS}
        if os.path.exists(LOG):
            rows = [json.loads(l) for l in open(LOG)]
            if rows:
                best = min(rows, key=lambda r: r["loss"])["cfg"]
        rng = random.Random(len(open(LOG).readlines()) if os.path.exists(LOG) else 0)
        for r in range(rounds):
            cands = [dict(best, **FIXED)] + [dict(FIXED, **{k: round(min(hi, max(lo, best[k] + rng.gauss(0, width * (hi - lo)))), 6) for k, (lo, hi) in KNOBS.items()})
                              for _ in range(7)]
            procs = [subprocess.Popen([sys.executable, __file__, "eval", json.dumps(c)], stdout=subprocess.PIPE, text=True) for c in cands]
            res = [json.loads(p.communicate()[0].strip().splitlines()[-1]) for p in procs]
            with open(LOG, "a") as fh:
                for x in res:
                    fh.write(json.dumps(x) + "\n")
            b = min(res, key=lambda x: x["loss"])
            best = b["cfg"]
            print(f"round {r}: best loss {b['loss']}  {json.dumps(b['out'])}", flush=True)
        print("best settings:", json.dumps(best))
