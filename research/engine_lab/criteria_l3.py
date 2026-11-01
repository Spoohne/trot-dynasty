"""The 100-season stud-book test against the predeclared "matches reset" criteria (log item 24).
    python research/engine_lab/criteria_l3.py <l3 dir>
Every arm vs pkg_reset, paired by history, seasons 50-100:
  1. late slope of the public estimate (points per decade): one-sided 95% upper bound of (arm - reset) <= +0.10
  2. S/S+ share at season 100: upper bound of (arm - reset) <= +0.02
  3. oracle pairing advantage (best-nick minus ordinary foal potential, frozen scale) >= 80% of reset's
  4. frozen genetic drift: birth-cohort trend of frozen potential, seasons 50-100, per decade (reported, and compared)
Frozen evaluator: each foal's saved trait potentials scored with today's weights and today's diminishing-returns
curve (soft at 5.0 / 2.5), so a changed scoring map can't pass for genetic change."""
import glob, json, math, os, statistics as st, sys
D = sys.argv[1]
ARMS = ["pkg", "pkg_q00", "pkg_all", "pkg_all_q00"]
REF = "pkg_reset"
W_SPEED, W_FINISH, W_STAM, GAIT_W, GAIT_CAP = 1.15, 0.85, 0.66, 0.7, 3.0


def soft(x, at=5.0, room=2.5):
    return x if x <= at else at + room * (1 - math.exp(-(x - at) / room))


def frozen(p):
    s = {t: soft(p[t]) for t in ("early_speed", "late_speed", "stamina", "gait")}
    return W_SPEED * s["early_speed"] + W_FINISH * s["late_speed"] + W_STAM * s["stamina"] + GAIT_W * min(s["gait"], GAIT_CAP) + min(s["gait"], s["stamina"], 0)


def load(v):
    return {int(f.rsplit("_", 1)[1][:-5]): json.load(open(f)) for f in glob.glob(os.path.join(D, f"{v}_*.json"))
            if os.path.basename(f)[:-5].rsplit("_", 1)[0] == v}


def trend(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    return 10 * sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)


def metrics(r):
    rows = [x for x in r["rows"] if x["season"] >= 50]
    births = [b for b in r["births"] if b[0] >= 50 and len(b) > 7]
    by = {}
    for b in births:
        by.setdefault(b[0], []).append(frozen(b[7]))
    seasons = sorted(by)
    nick = [frozen(b[7]) for b in r["births"] if b[1] == "nick" and len(b) > 7]
    ordi = [frozen(b[7]) for b in r["births"] if b[1] == "ordinary" and len(b) > 7]
    st_ = r["rows"][-1].get("stages", {})
    return dict(slope=trend([x["season"] for x in rows], [x["racer_est"] for x in rows]), s_end=r["rows"][-1]["s_share"],
                frozen_drift=trend(seasons, [st.mean(by[s]) for s in seasons]) if len(seasons) > 5 else None,
                edge=(st.mean(nick) - st.mean(ordi)) if nick and ordi else None, top5=r["rows"][-1]["top5"],
                eligible=st_.get("n_eligible"), stage=st_)


ref = {s: metrics(r) for s, r in load(REF).items()}
T95 = 1.895                                                   # one-sided 95%, 7 degrees of freedom
out = {"reset": {k: round(st.mean(m[k] for m in ref.values() if m[k] is not None), 3) for k in ("slope", "s_end", "frozen_drift", "edge", "top5")}}
for a in ARMS:
    A = {s: metrics(r) for s, r in load(a).items()}
    seeds = sorted(set(A) & set(ref))
    row = {"histories": len(seeds), "level": {k: round(st.mean(A[s][k] for s in seeds if A[s][k] is not None), 3) for k in ("slope", "s_end", "frozen_drift", "edge", "top5")}}
    for k, limit in (("slope", 0.10), ("s_end", 0.02)):
        d = [A[s][k] - ref[s][k] for s in seeds]
        m, se = st.mean(d), st.stdev(d) / len(d) ** .5
        row[f"{k}_minus_reset"] = dict(mean=round(m, 3), upper95=round(m + T95 * se, 3), passes=m + T95 * se <= limit)
    e_a = st.mean(A[s]["edge"] for s in seeds if A[s]["edge"] is not None); e_r = st.mean(ref[s]["edge"] for s in seeds if ref[s]["edge"] is not None)
    row["edge_share_of_reset"] = dict(value=round(e_a / e_r, 3), passes=e_a >= 0.8 * e_r)
    d = [A[s]["frozen_drift"] - ref[s]["frozen_drift"] for s in seeds if A[s]["frozen_drift"] is not None and ref[s]["frozen_drift"] is not None]
    row["frozen_drift_minus_reset"] = dict(mean=round(st.mean(d), 4), se=round(st.stdev(d) / len(d) ** .5, 4))
    row["matches_reset"] = all(row[k]["passes"] for k in ("slope_minus_reset", "s_end_minus_reset", "edge_share_of_reset"))
    row["selection_stages_season100_mean"] = {k: round(st.mean(A[s]["stage"].get(k) for s in seeds if A[s]["stage"].get(k) is not None), 3)
                                             for k in ("males2", "retired_m", "eligible", "n_eligible", "fem2", "retired_f")}
    out[a] = row
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "criteria_l3.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
