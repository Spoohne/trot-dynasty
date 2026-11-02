"""race3 + drive3 on random fields: Part 0 audit totals and the first Part 1 readings (not yet tuned).
    python research/engine_lab/v3_field.py <track> <seed> <races>"""
import collections, json, os, random, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race3 as R, drive3 as DR
track, seed, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
TR = ("gate", "cruise", "kick", "manners", "grit")
rng = random.Random(seed)
c = collections.defaultdict(collections.Counter)
aud = collections.Counter()
t0 = time.time()
for i in range(n):
    f = [R.Horse(f"H{k+1}", {t: rng.gauss(0, .4) for t in TR}, k + 1, R.TRACKS[track]) for k in range(8)]
    o, rec = R.run(f, track, DR.Driver(), seed=seed * 10000 + i)
    a = R.audit(rec)
    for k, v in a.items():
        if k != "min_gap_ft":
            aud[k] += v
    aud["races_with_overlap"] += a["overlaps"] > 0
    aud["unfinished"] += o[-1].time is None
    w = o[0]
    def at(frac):                                       # the field as it stood when the leader passed frac of the mile
        k = next(j for j, F in enumerate(rec["frames"]) if max(x[0] for x in F) >= frac * R.FT_MILE)
        return rec["frames"][k]
    names = rec["names"]
    F = at(0.75); order = sorted(range(8), key=lambda j: -F[j][0]); wi = names.index(w.name)
    rail = [j for j in order if F[j][1] < R.RAIL_Y + 2]
    lane = (F[wi][1] - R.RAIL_Y) / R.LANE
    trip = ("on the lead" if order[0] == wi else "pocket" if rail[:2] == [order[0], wi] or (len(rail) > 1 and rail[1] == wi and order.index(wi) <= 2)
            else "first-over" if lane > 0.6 and not any(F[j][1] > R.RAIL_Y + 2 and 0 < F[j][0] - F[wi][0] < 3 * R.LENGTH for j in range(8))
            else "followed cover" if lane > 0.6 else "came from further back")
    c["win_trip_3_4"][trip] += 1
    H = at(0.5); c["half_leader_post"][f[max(range(8), key=lambda j: H[j][0])].post] += 1
    c["leader_at_3_4"]["won" if order[0] == wi else "lost"] += 1
    c["post_wins"][w.post] += 1
    c["gate_aim"].update(rec["plans"].values()); c["win_gate_aim"][rec["plans"][w.name]] += 1
    c["changes"][min(3, sum(1 for x in rec.get("aim_changes", []) if x["h"] == w.name))] += 1
    best = max(f, key=lambda h: sum(h.t.values()))
    c["best_on_paper"]["won" if w is best else "lost"] += 1
    c["breaks"]["races with a break"] += any(e[2] == "broke stride" for e in rec["events"])
    c["time"]["sum"] += w.time or 0
c["secs"]["per_race_ms"] = int(1000 * (time.time() - t0) / n)
print(json.dumps({"audit": dict(aud), **{k: dict(v) for k, v in c.items()}}))
