"""The joint scorecard (DECISIONS 201): everything measured together on the same races, so nothing is traded away
unseen. Part 1 field mix, P1_SET overrides apply (PyPy recommended).
    python v3_card.py <track> <races> [seed]"""
import os, sys, random, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import race3 as R, drive3 as DR, v3_part1 as P1
track, N = sys.argv[1], int(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 97
c = collections.Counter(); trips = collections.Counter(); margins, times, wireE, empty_unforced = [], [], [], 0
posts_start, posts_win = collections.Counter(), collections.Counter()
for i in range(N):
    rng = random.Random(seed * 100003 + i)
    n = P1.size(rng, track)
    f = P1.field([{t: rng.gauss(0, .4) for t in P1.TR} for _ in range(n)], track)
    best = max(f, key=lambda h: h.t["gate"] + h.t["cruise"] + h.t["kick"])
    done_E, done_dv = {}, {}
    orig = R.step
    def step(field, tr, t, dt, rng_of, rec):
        before = {h.name: h.v for h in field}
        orig(field, tr, t, dt, rng_of, rec)
        for h in field:
            if h.done and h.name not in done_E:
                done_E[h.name] = h.E; done_dv[h.name] = h.v - before[h.name]
    R.step = step
    d = DR.Driver()
    o, rec = R.run(f, track, d, seed=seed * 1000 + i, dt=P1.DT)
    R.step = orig
    fr = rec["frames"]; names = [h.name for h in f]
    k2 = next(j for j, F in enumerate(fr) if max(x[0] for x in F) >= 2640)
    k3 = next(j for j, F in enumerate(fr) if max(x[0] for x in F) >= 3960)
    lead3 = max(range(n), key=lambda j: fr[k3][j][0]); lead2 = max(range(n), key=lambda j: fr[k2][j][0])
    c["best"] += o[0] is best; c["lead3"] += o[0].name == names[lead3]; c["rail_half"] += f[lead2].post == 1
    trips[P1.trip(rec, f, o[0])] += 1
    m = (o[1].time - o[0].time) * R.FT_MILE / o[0].time / R.LENGTH if n > 1 else 9
    margins.append(m); times.append(o[0].time)
    for h in f:
        posts_start[h.post] += 1
        forced = any(w in " ".join(d.state[h.name]["trip"]) for w in ("pressed", "parked", "couldn't"))
        wireE.append(done_E.get(h.name, 0))
        if done_E.get(h.name, 0) < 0.3 and done_dv.get(h.name, 0) < -0.05 and not forced:
            empty_unforced += 1
    posts_win[o[0].post] += 1
pc = lambda k: f"{100 * c[k] / N:.0f}%"
tp = {k: round(100 * trips[k] / N) for k in ("lead", "pocket", "first_over", "followed", "back")}
print(f"{track} {N} races | best horse wins {pc('best')} (~50) | leader at 3/4 wins {pc('lead3')} (35 half/25 mile) | rail leads at 1/2 {pc('rail_half')} (~25)")
print(f"   trips {tp} | median margin {st.median(margins):.2f} L (<2) | photos {100 * sum(m < .25 for m in margins) / N:.0f}% (8-17) | winning time {st.median(times):.1f}")
print(f"   reserve at the wire: median {st.median(wireE):.1f} | horses empty and slowing at the wire, not forced: {100 * empty_unforced / sum(posts_start.values()):.0f}% of starters (~0)")
print("   wins by post", [round(100 * posts_win[p] / posts_start[p], 1) for p in sorted(posts_start) if posts_start[p] >= N * .5])
