"""The drive (leader inside the last 1400 ft): by rank at the drive, the share of steps held up, the mean speed given
away under the horse's own ceiling, and why its lane change waited.
    python research/engine_lab/v3_drive_diag.py <track> <races> ['<json overrides>']"""
import os, sys, json, random, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
if len(sys.argv) > 3:
    os.environ["P1_SET"] = sys.argv[3]
import race3 as R, drive3 as DR, v3_part1 as P1
track, N = sys.argv[1], int(sys.argv[2])
held = collections.defaultdict(list); lost = collections.defaultdict(list); why = collections.Counter(); won = collections.Counter()
for i in range(N):
    rng = random.Random(77 * 100003 + i)
    n = P1.size(rng, track)
    f = P1.field([{t: rng.gauss(0, .4) for t in P1.TR} for _ in range(n)], track)
    d = DR.Driver(); rank = {}; acc = collections.defaultdict(lambda: [0, 0, 0.0])
    orig = R.step
    def step(field, track_, t, dt, rng_of, rec):
        orig(field, track_, t, dt, rng_of, rec)
        lead = max(field, key=lambda h: h.s)
        if lead.s < R.FT_MILE - 1400 or lead.done:
            return
        if not rank:
            rank.update({h.name: r for r, h in enumerate(sorted(field, key=lambda h: -h.s))})
        for h in field:
            if h.done:
                continue
            a = acc[h.name]; a[0] += 1; a[1] += h.blocked; a[2] += max(0.0, h.ceiling() - h.v)
            if h.blocked or h.req:
                why[(rank[h.name] > 0, (h.why_not or "held behind").split(" ")[0] + " " + " ".join((h.why_not or "held behind").split(" ")[1:3]))] += 1
    R.step = step
    o, rec = R.run(f, track, d, seed=77000 + i, dt=P1.DT, record=False)
    R.step = orig
    won[rank[o[0].name]] += 1
    for nm, (k, b, g) in acc.items():
        held[rank[nm]].append(b / k); lost[rank[nm]].append(g / k)
print(track, N, "races: rank at the drive | share of the drive held up | ft/s under its ceiling | wins")
for r in range(10):
    if held[r]:
        print(f"  {r+1:2d}   {st.mean(held[r]):5.0%}   {st.mean(lost[r]):5.2f}   {won[r]}")
print(" waits:", [(k[1], v) for k, v in why.most_common(8)])
