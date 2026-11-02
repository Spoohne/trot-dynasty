"""Stage 3 refit (review 16 plan, DECISIONS 150): paired measurements on many fields, adaptive driving, breaks off,
DT 1/16. For each setting: the median winning time per track, the median reserve at the drive, and the places gained
by +0.5 in gate, cruise, kick and grit (every horse in every field upgraded in turn), with standard errors from
field-level means.
    python research/engine_lab/v3_sens.py run <tag> '<json settings>' [fields] [seed]   runs it on 16 processes
    python research/engine_lab/v3_sens.py chunk <tag> '<json>' <fields> <seed> <i> <n>   one process's share
    python research/engine_lab/v3_sens.py show [tag ...]                               the table
Settings: plain keys go to race3.P, d_ keys to drive3.D, DRAFT to race3.DRAFT."""
import json, os, random, statistics as st, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "v3", "sens")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(HERE, "..", ".."))
TRAITS = ("gate", "cruise", "kick", "grit")
TARGET = {"half": dict(gate=0.45, cruise=0.35, kick=0.20, grit=0.12, time=115.9),
          "mile": dict(gate=0.20, cruise=0.35, kick=0.45, grit=0.12, time=113.4)}


def apply(cfg):
    import race3 as R, drive3 as DR
    R.P.update({k: v for k, v in cfg.items() if not k.startswith("d_") and k != "DRAFT"})
    DR.D.update({k[2:]: v for k, v in cfg.items() if k.startswith("d_")})
    if "DRAFT" in cfg:
        R.DRAFT = cfg["DRAFT"]
    R.P["break_b0"] = 0.0
    return R, DR


def chunk(tag, cfg, n, seed, i, k):
    R, DR = apply(cfg)
    TR = ("gate", "cruise", "kick", "manners", "grit")
    rows = []
    for tr in ("half", "mile"):
        T = R.TRACKS[tr]
        rng = random.Random(seed)
        fields = [[{t: rng.gauss(0, .4) for t in TR} for _ in range(8)] for _ in range(n)]
        for fi in range(i, n, k):
            stats = fields[fi]

            def race(st_, watch=False):
                f = [R.Horse(f"H{j+1}", dict(st_[j]), j + 1, T) for j in range(8)]
                drv = DR.Driver()
                rec = {"track": tr, "dt": 1 / 16, "names": [h.name for h in f], "frames": [], "events": []}
                rngs = {h.name: random.Random(f"1:{h.name}") for h in f}
                t, e = 0.0, []
                R._HELD.clear()
                while not all(h.done for h in f) and t < 200:
                    drv(f, T, t, rec); R.step(f, T, t, 1 / 16, lambda x: rngs[x.name], rec); t += 1 / 16
                    if watch:
                        for h in f:
                            if not getattr(h, "_seen", False) and drv.state[h.name]["phase"] == "drive":
                                h._seen = True; e.append(h.E / R.P["e_max"])
                o = sorted(f, key=lambda h: h.time or 1e9)
                return [h.name for h in o], o[0].time, e
            order, wt, e = race(stats, True)
            row = dict(track=tr, field=fi, time=wt, reserve=st.median(e) if e else 0.0)
            for trait in TRAITS:
                g = []
                for j in range(8):
                    up = [dict(x) for x in stats]; up[j][trait] += 0.5
                    o2, _, _ = race(up)
                    g.append(order.index(f"H{j+1}") - o2.index(f"H{j+1}"))
                row[trait] = st.mean(g)
            rows.append(row)
    with open(os.path.join(OUT, f"{tag}_{i}.jsonl"), "w") as fh:
        fh.write(json.dumps(dict(cfg=cfg)) + "\n")
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def summary(tag):
    rows, cfg = [], None
    for i in range(32):
        fn = os.path.join(OUT, f"{tag}_{i}.jsonl")
        if os.path.exists(fn):
            lines = [json.loads(l) for l in open(fn)]
            cfg = lines[0]["cfg"]; rows += lines[1:]
    out = {}
    for tr in ("half", "mile"):
        r = [x for x in rows if x["track"] == tr]
        m = {t: (st.mean(x[t] for x in r), st.stdev(x[t] for x in r) / len(r) ** 0.5) for t in TRAITS}
        m["time"] = (st.median(x["time"] for x in r), 0.0)
        m["reserve"] = (st.median(x["reserve"] for x in r), 0.0)
        m["n"] = len(r)
        out[tr] = m
    return cfg, out


if __name__ == "__main__":
    if sys.argv[1] == "chunk":
        chunk(sys.argv[2], json.loads(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7]))
    elif sys.argv[1] == "run":
        tag, cfg = sys.argv[2], sys.argv[3]
        n = int(sys.argv[4]) if len(sys.argv) > 4 else 64
        seed = int(sys.argv[5]) if len(sys.argv) > 5 else 71
        ps = [subprocess.Popen([sys.executable, __file__, "chunk", tag, cfg, str(n), str(seed), str(i), "16"]) for i in range(16)]
        for p in ps:
            p.wait()
        print(tag, "done")
    else:
        tags = sys.argv[2:] or sorted({f.rsplit("_", 1)[0] for f in os.listdir(OUT)})
        for tag in tags:
            cfg, out = summary(tag)
            line = f"{tag:14s}"
            for tr in ("half", "mile"):
                m = out[tr]
                line += f" | {tr} n{m['n']} t {m['time'][0]:.1f} res {m['reserve'][0]:.2f} " + " ".join(
                    f"{t[:2]} {m[t][0]:+.2f}±{m[t][1]:.2f}" for t in TRAITS)
            print(line)
