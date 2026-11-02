"""The aim-scoring driver on its own (model from drive_fit round 4).
    python research/engine_lab/driver_assay.py field <seed> <races>      race shape: aims, posts, calls
    python research/engine_lab/driver_assay.py ability                   +0.5 in each trait, aims frozen vs re-picked
    python research/engine_lab/driver_assay.py sum                       pool the field runs
field: long stretch five wide, tank 45, breaks at a plausible rate, DT 1/8. ability: breaks off, DT 1/16, 20 fields x 8
subjects; "frozen" starts every horse on its baseline aim (checks and events still run), "replan" lets every driver re-pick."""
import collections, glob, json, os, random, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drive_fit as D
R = D.R
HERE = D.HERE
TR = D.TR
D.setup()
D.load(int(os.environ.get("MODEL", "4")))
prof = lambda s: "speed" if s["early_speed"] - s["late_speed"] > 0.25 else "finisher" if s["late_speed"] - s["early_speed"] > 0.25 else "balanced"
mode = sys.argv[1]
if mode == "field":
    seed, n = int(sys.argv[2]), int(sys.argv[3])
    rng = random.Random(seed)
    c = collections.defaultdict(collections.Counter)
    for i in range(n):
        f = [R.Runner(f"H{k}", R.avg(**{t: rng.gauss(0, .4) for t in TR}), "mid", k + 1) for k in range(8)]
        o, rec = R.run(f, rng=random.Random(seed * 100000 + i), dt=0.125)
        w = o[0]
        first = {h.name: "yielded" if h.trip[0].startswith("Let") else h.aim0 for h in f}
        for h in f:
            c["start_aim"][first[h.name]] += 1; c["profile_starts"][prof(h.s)] += 1
            c["changes"][min(3, len(h.trip) - 1)] += 1
        c["win_start_aim"][first[w.name]] += 1; c["win_end_aim"][w.aim] += 1; c["profile_wins"][prof(w.s)] += 1
        c["post_wins"][w.post] += 1
        half = next(x for x in rec["calls"] if x["at"] == 0.5)["horses"]
        c["half_leader_post"][next(h.post for h in f if h.name == half[0]["name"])] += 1
        c["winner_behind_at_half"]["2 lengths or less" if next(x["behind"] for x in half if x["name"] == w.name) <= 2 else ">2 lengths"] += 1
        q3 = next(x for x in rec["calls"] if x["at"] == 0.75)["horses"]
        c["leader_at_3_4"]["won" if q3[0]["name"] == w.name else "lost"] += 1
        c["races"]["n"] += 1
    json.dump({k: dict(v) for k, v in c.items()}, open(os.path.join(HERE, f"assay_{seed}.json"), "w"))
elif mode == "sum":
    tot = collections.defaultdict(collections.Counter)
    for fn in glob.glob(os.path.join(HERE, "assay_*.json")):
        for k, v in json.load(open(fn)).items():
            tot[k].update({str(a): b for a, b in v.items()})
    n = tot["races"]["n"]
    for k in ("start_aim", "win_start_aim", "win_end_aim", "profile_starts", "profile_wins", "post_wins", "half_leader_post",
              "winner_behind_at_half", "leader_at_3_4", "changes"):
        d = tot[k]; s = sum(d.values())
        print(f"{k:22s}", {a: f"{100 * b / s:.1f}%" for a, b in sorted(d.items())})
    print("races", n)
else:
    R.P["break_k"] = 0.0
    rng = random.Random(9)
    fields = [[R.avg(**{t: rng.gauss(0, .4) for t in TR}) for _ in range(8)] for _ in range(20)]

    def race(stats, aims=None):
        f = [R.Runner(f"H{k}", dict(s), "mid", k + 1, {"start_aim": aims[k]} if aims else {}) for k, s in enumerate(stats)]
        o, rec = R.run(f, rng=random.Random(0), dt=1 / 16)
        return f, [h.name for h in o]
    out = {}
    for trait in ("early_speed", "late_speed", "stamina"):
        rows = []
        for fi, stats in enumerate(fields):
            base, border = race(stats)
            starts = [h.aim0 for h in base]
            for k in range(8):
                better = [dict(s) for s in stats]; better[k][trait] += 0.5
                r = dict(field=fi)
                for tag, aims_ in (("frozen", starts), ("replan", None)):
                    f, order = race(better, aims_)
                    r[f"dp_{tag}"] = order.index(f"H{k}") - border.index(f"H{k}")
                    r[f"dt_{tag}"] = f[k].time - base[k].time
                    r[f"aim_{tag}"] = f[k].aim != base[k].aim
                rows.append(r)
        res = {}
        for tag in ("frozen", "replan"):
            by_field = [st.mean(-r[f"dp_{tag}"] for r in rows if r["field"] == fi) for fi in range(20)]
            res[tag] = dict(places_gained=round(st.mean(by_field), 2), places_gained_se=round(st.stdev(by_field) / 20 ** 0.5, 2),
                            secs_gained=round(-st.mean(r[f"dt_{tag}"] for r in rows), 3),
                            worse_place=round(sum(r[f"dp_{tag}"] > 0 for r in rows) / len(rows), 3),
                            slower=round(sum(r[f"dt_{tag}"] > 1e-9 for r in rows) / len(rows), 3),
                            aim_changed=round(sum(r[f"aim_{tag}"] for r in rows) / len(rows), 3))
        out[trait] = res
        print(trait, json.dumps(res))
    json.dump(out, open(os.path.join(HERE, "ability.json"), "w"), indent=1)
