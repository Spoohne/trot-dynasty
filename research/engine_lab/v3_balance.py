"""Stage 3 single-horse balance (DECISIONS 141): one setting at a time, report the clocks against the live medians
(mile 1:53.4, half 1:55.9), the reserve horses bring to the drive, and what +0.5 in each trait is worth (places,
gate aims frozen; breaks off). Settings come as k=v pairs for race3.P.
    python research/engine_lab/v3_balance.py c_turn=0.0002 pace_k=1.0 ..."""
import json, os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race3 as R, drive3 as DR
R.P.update({k: float(v) for k, v in (a.split("=") for a in sys.argv[1:])})
R.P["break_b0"] = 0.0
TR = ("gate", "cruise", "kick", "manners", "grit")
out = dict(setting=" ".join(sys.argv[1:]))
for tr in ("mile", "half"):
    rng = random.Random(11)
    fields = [[{t: rng.gauss(0, .4) for t in TR} for _ in range(8)] for _ in range(10)]
    wins, e_drive, gains = [], [], {t: [] for t in ("gate", "cruise", "kick", "grit")}

    def race(stats, plan=None, watch=False):
        drv = DR.Driver(gate_aims=plan)
        f = [R.Horse(f"H{k+1}", dict(stats[k]), k + 1, R.TRACKS[tr]) for k in range(8)]
        if not watch:
            o, _ = R.run(f, tr, drv, seed=1, dt=1 / 16, record=False)
            return o, drv
        track = R.TRACKS[tr]
        rec = {"track": tr, "dt": 1 / 16, "names": [h.name for h in f], "frames": [], "events": []}
        rngs = {h.name: random.Random(f"1:{h.name}") for h in f}
        t, seen = 0.0, set()
        R._HELD.clear()
        while not all(h.done for h in f) and t < 200:
            drv(f, track, t, rec); R.step(f, track, t, 1 / 16, lambda h: rngs[h.name], rec); t += 1 / 16
            for h in f:
                if h.name not in seen and drv.state[h.name]["phase"] == "drive":
                    seen.add(h.name); e_drive.append(h.E / R.P["e_max"])
        return sorted(f, key=lambda h: h.time or 1e9), drv
    for stats in fields:
        o, drv = race(stats, watch=True)
        wins.append(o[0].time)
        place = {h.name: k for k, h in enumerate(o)}
        plan = {n: s_["trip"][0].split(": ")[1].replace("-", "_") for n, s_ in drv.state.items()}
        for trait in gains:
            for k in range(8):
                up = [dict(x) for x in stats]; up[k][trait] += 0.5
                o2, _ = race(up, plan)
                gains[trait].append(place[f"H{k+1}"] - [h.name for h in o2].index(f"H{k+1}"))
    out[tr] = dict(win_median=round(st.median(wins), 2), reserve_at_drive=round(st.median(e_drive), 2),
                   **{f"+0.5 {t}": round(st.mean(v), 2) for t, v in gains.items()})
print(json.dumps(out))
