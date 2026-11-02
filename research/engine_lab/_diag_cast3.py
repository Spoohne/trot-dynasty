import v5_cast as K, v5_choreo as C, random, numpy as np
R = C.R; RN = ["lead", "pocket", "fo", "fol", "line"]
shown = 0
for k, r in enumerate(K.model_races(20, 601)):
    rng = random.Random(0); lead_s, q = C.leader_clock(115.9, rng); st = rng.getstate(); beh, lane = K.formations(r, rng); S, Y, ts, ty = C.paths(beh, lane, lead_s); kk = int(np.argmax(S.max(0) >= 3960)); rng.setstate(st)
    beh, lane = K.formations(r, rng, ((S[:, kk].max() - S[:, kk]) / 8, (Y[:, kk] - 3) / 7)); S, Y, ts, ty = C.paths(beh, lane, lead_s); ok, why = C.check(S, Y); lead = S.max(0)
    wt = [float(np.interp(R.FT_MILE, s, lead_s[:, 0])) for s in S]; got = sorted(range(8), key=lambda i: wt[i])
    if not ok or got == r["order"]:
        continue
    print("race", k, "want", r["order"], "got", got)
    for i in r["order"]:
        k8 = int(np.argmax(lead >= 3960)); kw = int(np.argmax(lead >= 5100))
        print(f"  {i} {RN[r['role'][i]]:6} 3/4: {(lead[k8]-S[i,k8])/8:4.1f}L lane {(Y[i,k8]-3)/7:4.1f} | plan stretch lane {lane[i,11]:4.1f} | at 5100: {(lead[kw]-S[i,kw])/8:4.1f}L (plan {beh[i,11]:4.1f}) lane {(Y[i,kw]-3)/7:4.1f}")
    shown += 1
    if shown == 2: break
