"""race3 + drive3 acceptance checks (review 14 items 3-4). Breaks off unless noted.
    python research/engine_lab/v3_checks.py order|dt|traits <track>"""
import os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race3 as R, drive3 as DR
cmd, track = sys.argv[1], sys.argv[2]
TR = ("gate", "cruise", "kick", "manners", "grit")
b0 = R.P["break_b0"]


def fields(n, seed):
    rng = random.Random(seed)
    return [[{t: rng.gauss(0, .4) for t in TR} for _ in range(8)] for _ in range(n)]


def race(stats, order=None, dt=R.DT, gate_aims=None, seed=0, names=None):
    names = names or [f"H{k+1}" for k in range(8)]
    f = [R.Horse(names[k], dict(stats[k]), k + 1, R.TRACKS[track]) for k in range(8)]
    if order:
        f = [f[k] for k in order]
    o, rec = R.run(f, track, DR.Driver(gate_aims=gate_aims), seed=seed, dt=dt, record=False)
    return {h.name: (pl + 1, h.time) for pl, h in enumerate(o)}, {h.name: h for h in f}


if cmd == "order":                                       # list order and horse names must not matter
    R.P["break_b0"] = 0.0
    bad_order = bad_names = 0
    for stats in fields(20, 1):
        base, _ = race(stats)
        perm, _ = race(stats, order=random.Random(9).sample(range(8), 8))
        bad_order += base != perm
        alt = ["Z" + str(9 - k) for k in range(8)]       # different names, same horses and posts
        renamed, _ = race(stats, names=alt)
        bad_names += [p for p, _ in base.values()] != [p for p, _ in renamed.values()]
    ties = 0                                              # identical horses: results by post only, and reproducible
    for k in range(5):
        a, _ = race([{t: 0.0 for t in TR}] * 8, seed=k); b, _ = race([{t: 0.0 for t in TR}] * 8, seed=k)
        ties += a != b
    print(f"{track}: list-order changes {bad_order}/20, name changes {bad_names}/20, identical-field reruns differing {ties}/5")
elif cmd == "dt":                                        # results should settle as the step shrinks
    R.P["break_b0"] = 0.0
    rows = []
    for stats in fields(15, 2):
        r = {d: race(stats, dt=d)[0] for d in (1 / 8, 1 / 16, 1 / 32)}
        win = {d: min(r[d], key=lambda n: r[d][n][0]) for d in r}
        t_err = {d: abs(r[d][win[1 / 32]][1] - r[1 / 32][win[1 / 32]][1]) for d in (1 / 8, 1 / 16)}
        same = {d: sum(r[d][n][0] == r[1 / 32][n][0] for n in r[d]) / 8 for d in (1 / 8, 1 / 16)}
        rows.append((win[1 / 8] == win[1 / 32], win[1 / 16] == win[1 / 32], t_err[1 / 8], t_err[1 / 16], same[1 / 8], same[1 / 16]))
    m = lambda i: st.mean(r[i] for r in rows)
    print(f"{track}: same winner as DT 1/32 — DT 1/8 {m(0):.0%}, 1/16 {m(1):.0%}; winner's time error 1/8 {m(2):.2f}s, 1/16 {m(3):.2f}s;"
          f" places identical 1/8 {m(4):.0%}, 1/16 {m(5):.0%}")
else:                                                    # +0.5 in one trait: frozen gate aims vs adaptive
    out = []
    for trait in ("gate", "cruise", "kick", "grit", "manners"):
        R.P["break_b0"] = b0 if trait == "manners" else 0.0
        reps = 6 if trait == "manners" else 1
        rows = []
        for fi, stats in enumerate(fields(16, 3)):
            for seed in range(reps):
                drv = DR.Driver()
                f = [R.Horse(f"H{k+1}", dict(stats[k]), k + 1, R.TRACKS[track]) for k in range(8)]
                o, _ = R.run(f, track, drv, seed=seed, record=False)
                base = {h.name: (pl + 1, h.time) for pl, h in enumerate(o)}
                plan = {n: s_["trip"][0].split(": ")[1].replace("-", "_") for n, s_ in drv.state.items()}   # each horse's gate aim
                for k in range(8):
                    up = [dict(x) for x in stats]; up[k][trait] += 0.5
                    n = f"H{k+1}"
                    fz, _ = race(up, gate_aims=plan, seed=seed)
                    ad, _ = race(up, seed=seed)
                    rows.append((fi, base[n][0] - fz[n][0], base[n][0] - ad[n][0]))
        res = []
        for col in (1, 2):
            by_f = [st.mean(r[col] for r in rows if r[0] == fi) for fi in range(16)]
            res.append((st.mean(by_f), st.stdev(by_f) / 4, sum(r[col] < 0 for r in rows) / len(rows), sum(r[col] > 0 for r in rows) / len(rows)))
        print(f"{track} +0.5 {trait:8s} frozen: {res[0][0]:+.2f} places (±{res[0][1]:.2f}) worse {res[0][2]:.0%} better {res[0][3]:.0%} |"
              f" adaptive: {res[1][0]:+.2f} (±{res[1][1]:.2f}) worse {res[1][2]:.0%} better {res[1][3]:.0%}", flush=True)
