"""Why races don't cast (DECISIONS 232): one attempt per uncast race, classified. For an order failure: the first
place that came out wrong, the horse the model put there (its trip, where it was at the 3/4, the lane it was planned),
and who beat it instead.
    python v5_cast_why.py <races> [seed]"""
import random, sys
from collections import Counter
import numpy as np
import v5_cast as K, v5_choreo as C

R, RN = C.R, ["lead", "pocket", "first-over", "follow", "line"]


def attempt(res, t=0, seed=0):
    rng = random.Random(seed * 1000 + t)
    lead_s, q = C.leader_clock(res.get("final", 115.9) + rng.uniform(-.3, .3), rng)
    st = rng.getstate(); beh, lane = K.formations(res, rng); S, Y, ts, ty = C.paths(beh, lane, lead_s)
    k = int(np.argmax(S.max(0) >= 3960)); rng.setstate(st)
    beh, lane = K.formations(res, rng, ((S[:, k].max() - S[:, k]) / K.LEN, (Y[:, k] - R.RAIL_Y) / R.LANE))
    S, Y, ts, ty = C.paths(beh, lane, lead_s, savers={h for h in range(len(lane)) if lane[h, 12] >= 2})
    ok, why = C.check(S, Y)
    wt = [float(np.interp(R.FT_MILE, s, lead_s[:, 0])) for s in S]
    return ok, why, sorted(range(len(S)), key=lambda i: wt[i]), S, Y, beh, lane


if __name__ == "__main__":
    N = int(sys.argv[1]); seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    kinds, who = Counter(), Counter()
    for k, res in enumerate(K.model_races(N, 600 + seed)):
        ok, why, got, S, Y, beh, lane = attempt(res, seed=k)
        if ok and got == res["order"]:
            kinds["cast"] += 1; continue
        if not ok:
            kinds[why.split()[0]] += 1; continue
        place = next(x for x in range(len(got)) if got[x] != res["order"][x])
        h, beat = res["order"][place], got[place]
        k34 = int(np.argmax(S.max(0) >= 3960))
        tag = (f"{RN[res['role'][h]]} lost to {RN[res['role'][beat]]}",
               "same lane at 3/4" if abs(Y[h, k34] - Y[beat, k34]) < C.WIDE else "different lanes",
               "behind at 3/4" if S[h, k34] < S[beat, k34] else "ahead at 3/4")
        kinds["order"] += 1; who[tag] += 1
        print(f"race {k}: place {place + 1}: {tag} | planned lanes {lane[h, 9:13]} vs {lane[beat, 9:13]} | margins {res['margin'][h]:.1f} vs {res['margin'][beat]:.1f}")
    print(dict(kinds)); print(who.most_common(8))
