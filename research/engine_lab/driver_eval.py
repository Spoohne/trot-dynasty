"""The value-model driver end to end (value2/value_<MODEL>, default 2), mile and half-mile.
    python research/engine_lab/driver_eval.py field <track> <seed> <races>    race shape (DT 1/8, breaks on)
    python research/engine_lab/driver_eval.py sum <track>
    python research/engine_lab/driver_eval.py ability <track>                 +0.5 per trait, aims frozen vs re-picked
    python research/engine_lab/driver_eval.py posts <track>                   20 fields x 8 post rotations, fixed aims vs driver
ability and posts: breaks off, DT 1/16. "frozen" starts every horse on its baseline gate aim (checks still run)."""
import collections, glob, json, os, random, statistics as st, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import value_fit as V
R = V.R
V.setup(0)
V.load(int(os.environ.get("MODEL", "2")))
OUT = os.path.join(V.OUT, "eval")
os.makedirs(OUT, exist_ok=True)
TR = V.D.TR
prof = lambda s: "speed" if s["early_speed"] - s["late_speed"] > 0.25 else "finisher" if s["late_speed"] - s["early_speed"] > 0.25 else "balanced"
cmd, track = sys.argv[1], sys.argv[2]
if cmd == "field":
    seed, n = int(sys.argv[3]), int(sys.argv[4])
    rng = random.Random(seed)
    c = collections.defaultdict(collections.Counter)
    t0 = time.time()
    for i in range(n):
        f = [R.Runner(f"H{k}", R.avg(**{t: rng.gauss(0, .4) for t in TR}), "mid", k + 1) for k in range(8)]
        o, rec = R.run(f, track, rng=random.Random(seed * 100000 + i), dt=0.125)
        w = o[0]
        for h in f:
            ch = [x for x in rec.get("aim_changes", []) if x["h"] == h.name and x["why"] != "cover"]
            c["gate_aim"][h.aim0] += 1; c["profile_starts"][prof(h.s)] += 1; c["aim_changes"][min(3, len(ch))] += 1
            c["reversals"]["back to an earlier aim" if any(x["new"] in [y["old"] for y in ch[:i]] for i, x in enumerate(ch)) else "none"] += 1
            for x in ch:
                c["change_reason"][x["why"].split(",")[0]] += 1
        c["win_gate_aim"][w.aim0] += 1; c["win_last_aim"][w.aim] += 1; c["profile_wins"][prof(w.s)] += 1; c["post_wins"][w.post] += 1
        half = next(x for x in rec["calls"] if x["at"] == 0.5)["horses"]
        c["half_leader_post"][next(h.post for h in f if h.name == half[0]["name"])] += 1
        c["winner_at_half"]["within 2 lengths" if next(x["behind"] for x in half if x["name"] == w.name) <= 2 else "further back"] += 1
        q3 = next(x for x in rec["calls"] if x["at"] == 0.75)["horses"]
        c["leader_at_3_4"]["won" if q3[0]["name"] == w.name else "lost"] += 1
        c["races"]["n"] += 1; c["secs"]["total"] += time.time() - t0; t0 = time.time()
    json.dump({k: dict(v) for k, v in c.items()}, open(os.path.join(OUT, f"field_{track}_{seed}.json"), "w"))
elif cmd == "sum":
    tot = collections.defaultdict(collections.Counter)
    for fn in glob.glob(os.path.join(OUT, f"field_{track}_*.json")):
        for k, v in json.load(open(fn)).items():
            tot[k].update({str(a): b for a, b in v.items()})
    for k in ("gate_aim", "win_gate_aim", "win_last_aim", "profile_starts", "profile_wins", "post_wins", "half_leader_post",
              "winner_at_half", "leader_at_3_4", "aim_changes", "reversals", "change_reason"):
        d = tot[k]; s = sum(d.values())
        print(f"{k:17s}", " ".join(f"{a}:{100 * b / s:.1f}" for a, b in sorted(d.items(), key=lambda x: (len(x[0]), x[0]))))
    print(f"races {tot['races']['n']}, {1000 * tot['secs']['total'] / tot['races']['n']:.0f} ms per race")
else:
    R.P["break_k"] = 0.0
    rng = random.Random(9 if cmd == "ability" else 21)
    fields = [[R.avg(**{t: rng.gauss(0, .4) for t in TR}) for _ in range(8)] for _ in range(20)]
    if cmd == "ability":
        def race(stats, aims=None):
            f = [R.Runner(f"H{k}", dict(s), "mid", k + 1, {"start_aim": aims[k]} if aims else {}) for k, s in enumerate(stats)]
            o, rec = R.run(f, track, rng=random.Random(0), dt=1 / 16)
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
                        r[tag] = order.index(f"H{k}") - border.index(f"H{k}")
                    rows.append(r)
            res = {}
            for tag in ("frozen", "replan"):
                by_field = [st.mean(-r[tag] for r in rows if r["field"] == fi) for fi in range(20)]
                res[tag] = dict(places_gained=round(st.mean(by_field), 2), se=round(st.stdev(by_field) / 20 ** 0.5, 2),
                                worse=round(sum(r[tag] > 0 for r in rows) / len(rows), 3), better=round(sum(r[tag] < 0 for r in rows) / len(rows), 3))
            out[trait] = res
            print(track, trait, json.dumps(res))
        json.dump(out, open(os.path.join(OUT, f"ability_{track}.json"), "w"), indent=1)
    else:
        FIXED = ["top", "pocket", "first_over", "follow", "close", "pocket", "follow", "close"]
        out = {}
        for arm in ("fixed", "driver"):
            wins = collections.Counter()
            for stats in fields:
                for rot in range(8):
                    f = sorted((R.Runner(f"H{k}", dict(stats[k]), "mid", (k + rot) % 8 + 1, {"aim": FIXED[k]} if arm == "fixed" else {})
                                for k in range(8)), key=lambda h: h.post)
                    o, rec = R.run(f, track, rng=random.Random(0), dt=1 / 16)
                    wins[o[0].post] += 1
            out[arm] = [round(100 * wins[p] / 160, 1) for p in range(1, 9)]
            print(track, arm, out[arm])
        json.dump(out, open(os.path.join(OUT, f"posts_{track}.json"), "w"), indent=1)
