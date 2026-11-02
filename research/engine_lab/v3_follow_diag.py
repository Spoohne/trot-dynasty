"""How sitters follow (DECISIONS 202): for horses sitting in line behind another, the clear gap (ft), the time out of
the draft (gap over 1.5 lengths), the speed thrown away braking, and why (capped by the budget, held by the safety
layer, or the controller).  python v3_follow_diag.py <track> <races>   (P1_SET overrides apply)"""
import os, sys, random, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import race3 as R, drive3 as DR, v3_part1 as P1
track, N = sys.argv[1], int(sys.argv[2])
gaps, why = [], collections.Counter(); steps = out = 0; braked = 0.0
for i in range(N):
    rng = random.Random(41 * 100003 + i)
    n = 8 if track == "half" else 10
    f = P1.field([{t: rng.gauss(0, .4) for t in P1.TR} for _ in range(n)], track)
    d = DR.Driver(); orig = R.step
    def step(field, tr, t, dt, rng_of, rec):
        global steps, out, braked
        v0 = {h.name: h.v for h in field}
        orig(field, tr, t, dt, rng_of, rec)
        lead = max(field, key=lambda h: h.s)
        if lead.s < 600 or lead.s > R.FT_MILE - 1400:
            return                                          # the middle of the race only: after the start, before the drive
        for h in field:
            st_ = d.state.get(h.name)
            if not st_ or st_["phase"] != "sit" or h.done:
                continue
            ahead = [o for o in field if o is not h and o.s > h.s and abs(o.y - h.y) < R.BODY_W]
            if not ahead:
                continue
            o = min(ahead, key=lambda o: o.s)
            g = o.s - R.BODY_L - h.s
            if g > 4 * R.LENGTH:
                continue
            steps += 1; gaps.append(g); out += g > 1.5 * R.LENGTH
            dv = v0[h.name] - h.v
            if dv > 0:
                braked += dv
                why["budget" if "aff" in st_ and h.cmd.get("v", 99) >= st_["aff"] - 0.01 else "safety" if h.blocked else "controller"] += dv
    R.step = step
    R.run(f, track, d, seed=41000 + i, dt=P1.DT, record=False)
    R.step = orig
q = sorted(gaps)
print(f"{track} {N} races, sitters mid-race: clear gap median {q[len(q)//2]:.1f} ft (10th {q[len(q)//10]:.1f}, 90th {q[9*len(q)//10]:.1f}),"
      f" out of the draft {100*out/steps:.0f}% of the time, speed braked away {braked/N:.0f} ft/s per race: "
      + ", ".join(f"{k} {100*v/braked:.0f}%" for k, v in why.most_common()))
