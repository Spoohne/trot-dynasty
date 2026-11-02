import v5_cast as K, v5_choreo as C, random, numpy as np, sys
from collections import Counter
R = C.R; why_c = Counter(); pos_wrong = Counter()
for k, r in enumerate(K.model_races(20, 601)):
    for t in range(4):
        rng = random.Random(t); lead_s, q = C.leader_clock(115.9, rng); st = rng.getstate(); beh, lane = K.formations(r, rng); S, Y, ts, ty = C.paths(beh, lane, lead_s); kk = int(np.argmax(S.max(0) >= 3960)); rng.setstate(st)
        beh, lane = K.formations(r, rng, ((S[:, kk].max() - S[:, kk]) / 8, (Y[:, kk] - 3) / 7)); S, Y, ts, ty = C.paths(beh, lane, lead_s); ok, why = C.check(S, Y)
        wt = [float(np.interp(R.FT_MILE, s, lead_s[:, 0])) for s in S]; got = sorted(range(8), key=lambda i: wt[i])
        why_c[why.split(" ")[0] if not ok else ("order" if got != r["order"] else "ok")] += 1
        if got != r["order"]:
            first = next(x for x in range(8) if got[x] != r["order"][x]); pos_wrong[first + 1] += 1
print(why_c); print("first wrong place:", sorted(pos_wrong.items()))
