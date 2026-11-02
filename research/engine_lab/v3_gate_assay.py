"""Review 16 assay A: does +0.5 gate change anything a horse does at the start? 64 fields x 8 subjects, breaks off,
DT 1/16, normal driving. For the subject, baseline vs upgrade: seconds its request, its ceiling or the safety rule
bound its speed in the first 700 ft; whether it cleared (aimed for the top and led by the first turn); its place at
the first turn and at the quarter; extra ground to the quarter; reserve left at the quarter."""
import collections, os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race3 as R, drive3 as DR
track = sys.argv[1]
R.P["break_b0"] = 0.0
TR = ("gate", "cruise", "kick", "manners", "grit")
rng = random.Random(31)
fields = [[{t: rng.gauss(0, .4) for t in TR} for _ in range(8)] for _ in range(64)]
T = R.TRACKS[track]


def race(stats, k):
    f = [R.Horse(f"H{j+1}", dict(stats[j]), j + 1, T) for j in range(8)]
    drv = DR.Driver()
    rec = {"track": track, "dt": 1 / 16, "names": [h.name for h in f], "frames": [], "events": []}
    rngs = {h.name: random.Random(f"1:{h.name}") for h in f}
    h = f[k]
    bind = collections.Counter()
    out = {}
    t = 0.0
    R._HELD.clear()
    while not all(x.done for x in f) and t < 200:
        drv(f, T, t, rec)
        v0, req, cap = h.v, h.cmd.get("v", h.v_sus), h.ceiling()
        R.step(f, T, t, 1 / 16, lambda x: rngs[x.name], rec); t += 1 / 16
        if h.s < 700:
            want = min(req, cap)
            bind["accel"] += 1 / 16 if h.v < want - 0.05 and not h.blocked else 0
            bind["request"] += 1 / 16 if req <= cap and h.v >= req - 0.05 else 0
            bind["ceiling"] += 1 / 16 if cap < req and h.v >= cap - 0.05 else 0
            bind["safety"] += 1 / 16 if h.blocked else 0
        lead = max(f, key=lambda x: x.s)
        for name, mark in (("turn", T.arcs[0][0]), ("quarter", 0.25 * R.FT_MILE)):
            if name not in out and lead.s >= mark:
                order = sorted(f, key=lambda x: -x.s)
                out[name] = order.index(h) + 1
                if name == "quarter":
                    out["ground"] = sum(T.path(0, h.s, h.y) for _ in [0]) - h.s
                    out["reserve"] = h.E
    out["cleared"] = drv.state[h.name]["trip"][0] == "gate: top" and out.get("turn") == 1
    out["aim"] = drv.state[h.name]["trip"][0].split(": ")[1]
    out["place"] = sorted(f, key=lambda x: x.time or 1e9).index(h) + 1
    out.update({f"bind_{k_}": v for k_, v in bind.items()})
    return out


rows = []
for stats in fields:
    for k in range(8):
        b = race(stats, k)
        up = [dict(x) for x in stats]; up[k]["gate"] += 0.5
        u = race(up, k)
        rows.append((k + 1, b, u))
d = lambda key: st.mean(u[key] - b[key] for _, b, u in rows)
print(f"{track}: places gained at the first turn {-d('turn'):+.2f}, at the quarter {-d('quarter'):+.2f}, at the wire {-d('place'):+.2f}")
print(f"   reserve at the quarter {d('reserve'):+.2f} (of {R.P['e_max']}), extra ground to the quarter {d('ground'):+.1f} ft,"
      f" cleared for the lead {st.mean(b['cleared'] for _, b, _ in rows):.0%} -> {st.mean(u['cleared'] for _, _, u in rows):.0%}")
for key in ("accel", "request", "ceiling", "safety"):
    print(f"   first 700 ft, seconds bound by {key}: baseline {st.mean(b.get('bind_' + key, 0) for _, b, _ in rows):.2f}, with +gate {st.mean(u.get('bind_' + key, 0) for _, _, u in rows):.2f}")
aims = collections.Counter((b["aim"], u["aim"]) for _, b, u in rows)
print("   gate aim baseline -> upgraded (most common):", aims.most_common(6))
by_post = collections.defaultdict(list)
for p, b, u in rows:
    by_post[p].append(b["quarter"] - u["quarter"])
print("   places gained at the quarter by post:", {p: round(st.mean(v), 2) for p, v in sorted(by_post.items())})
