"""Review 17 experiment 2 (short form): at the drive, each horse runs the rest alone from its exact state (no
traffic, flat out on its own line, then the rail in the stretch). Who would win unobstructed vs who did.
    python research/engine_lab/v3_drive_solo.py <track> <races> ['<json overrides>']"""
import os, sys, copy, random, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
if len(sys.argv) > 3:
    os.environ["P1_SET"] = sys.argv[3]
import race3 as R, drive3 as DR, v3_part1 as P1
track, N = sys.argv[1], int(sys.argv[2])
T = R.TRACKS[track]
solo_win, real_win, same, lead_solo = collections.Counter(), collections.Counter(), 0, 0
for i in range(N):
    rng = random.Random(77 * 100003 + i)
    n = P1.size(rng, track)
    f = P1.field([{t: rng.gauss(0, .4) for t in P1.TR} for _ in range(n)], track)
    snap = {}
    orig = R.step
    def step(field, track_, t, dt, rng_of, rec):
        orig(field, track_, t, dt, rng_of, rec)
        lead = max(field, key=lambda h: h.s)
        if not snap and lead.s >= R.FT_MILE - 1400:
            snap["t"] = t
            snap["f"] = copy.deepcopy(field)
    R.step = step
    o, rec = R.run(f, track, DR.Driver(), seed=77000 + i, dt=P1.DT, record=False)
    R.step = orig
    rank = {h.name: r for r, h in enumerate(sorted(snap["f"], key=lambda h: -h.s))}
    solo = {}
    for h in snap["f"]:
        g = copy.deepcopy(h); t = snap["t"]; g.req = g.man = None
        while not g.done and t < 250:
            g.cmd = dict(v=1e9, y=g.y)
            R.step([g], T, t, P1.DT, lambda _: random.Random(0), {"events": []})
            t += P1.DT
        solo[h.name] = g.time if g.time else 1e9
    best = min(solo, key=solo.get)
    solo_win[rank[best]] += 1; real_win[rank[o[0].name]] += 1; same += best == o[0].name
print(f"{track} {N}: winner's rank at the drive, unobstructed vs actual")
for r in range(10):
    if solo_win[r] or real_win[r]:
        print(f"  {r+1:2d}  solo {solo_win[r]:3d}   actual {real_win[r]:3d}")
print("  same winner", same, "of", N)
