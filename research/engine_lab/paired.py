"""Round-2 analysis by history (review 1, item 11): each variant minus the base history with the same seed.
    python research/engine_lab/paired.py <league dir> base pkg pkg_dim pkg_reset pkg_both
Reports the mean and spread of the 8 paired differences for: late-period slope of the public estimate (seasons 30-50,
per decade), S/S+ share and top-5 sire share at season 50, the best-nick minus ordinary foal edge, and foals clearing
FIXED thresholds taken from the base population's births in seasons 0-10 (median and top 5%). Under `dim` the potential
scale itself is compressed, so its fixed-threshold figures are marked."""
import glob, json, os, statistics as st, sys
D, VARS = sys.argv[1], sys.argv[2:]
base, rest = VARS[0], VARS[1:]
load = lambda v: {int(os.path.basename(f).split("_")[-1][:-5]): json.load(open(f)) for f in glob.glob(os.path.join(D, f"{v}_*.json"))
                  if os.path.basename(f)[:-5].rsplit("_", 1)[0] == v}
B = load(base)
early = sorted(b[4] for r in B.values() for b in r["births"] if b[0] <= 10)
T_USEFUL, T_GREAT = early[len(early) // 2], early[int(.95 * len(early))]


def slope(rows, key, a=30, b=50):
    xs = [r["season"] for r in rows if a <= r["season"] <= b and r[key] is not None]
    ys = [r[key] for r in rows if a <= r["season"] <= b and r[key] is not None]
    mx, my = st.mean(xs), st.mean(ys)
    return 10 * sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)


def metrics(r):
    rows, births = r["rows"], r["births"]
    late = [b for b in births if b[0] >= 40]
    nick = [b[4] for b in births if b[1] == "nick"]; ordi = [b[4] for b in births if b[1] == "ordinary"]
    return dict(est_slope=slope(rows, "racer_est"), est_end=rows[-1]["racer_est"], s_end=rows[-1]["s_share"], top5_end=rows[-1]["top5"],
                nick_minus_ordinary=(st.mean(nick) - st.mean(ordi)) if nick and ordi else None,
                late_useful_fixed=st.mean(b[4] >= T_USEFUL for b in late), late_great_fixed=st.mean(b[4] >= T_GREAT for b in late))


def fmt(xs):
    xs = [x for x in xs if x is not None]
    return f"{st.mean(xs):+.3f} ± {st.stdev(xs):.3f} (n={len(xs)})" if len(xs) > 1 else "—"


MB = {s: metrics(r) for s, r in B.items()}
out = {"base": {k: fmt([m[k] for m in MB.values()]).replace("+", "") for k in next(iter(MB.values()))},
       "fixed_thresholds": {"useful": round(T_USEFUL, 3), "exceptional": round(T_GREAT, 3)}}
for v in rest:
    V = load(v)
    seeds = sorted(set(V) & set(B))
    MV = {s: metrics(V[s]) for s in seeds}
    out[v + " minus base"] = {k: fmt([MV[s][k] - MB[s][k] if MV[s][k] is not None and MB[s][k] is not None else None for s in seeds])
                              for k in MB[seeds[0]]}
    out[v + " level"] = {k: fmt([MV[s][k] for s in seeds]).replace("+", "") for k in MB[seeds[0]]}
    if "dim" in v:
        out[v + " minus base"]["note"] = "potential scale compressed under dim: fixed-threshold and nick figures aren't comparable"
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "paired_round2.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
