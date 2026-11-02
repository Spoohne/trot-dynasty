import v5_cast as K, v5_choreo as C, random, numpy as np
R = C.R; RN = ["lead", "pocket", "fo", "fol", "line"]; shown = 0
for k, r in enumerate(K.model_races(60, 607)):
    if K.story_of(r) != "first_over":
        continue
    rng = random.Random(k * 1000); final = 115.9 + rng.uniform(-.3, .3); lead_s, q = C.leader_clock(final, rng)
    st = rng.getstate(); beh, lane = K.formations(r, rng); S, Y, ts, ty = C.paths(beh, lane, lead_s)
    kk = int(np.argmax(S.max(0) >= 3960)); rng.setstate(st)
    beh, lane = K.formations(r, rng, ((S[:, kk].max() - S[:, kk]) / 8, (Y[:, kk] - 3) / 7)); S, Y, ts, ty = C.paths(beh, lane, lead_s)
    ok, why = C.check(S, Y); lead = S.max(0)
    wt = [float(np.interp(R.FT_MILE, s, lead_s[:, 0])) for s in S]; got = sorted(range(8), key=lambda i: wt[i])
    print(f"race {k}: {why} | want {r['order']} got {got}")
    for i in r["order"][:4]:
        c = [int(np.argmax(lead >= ft)) for ft in (2640, 3300, 3960, 4700, 5100)]
        print(f"   {i} {RN[r['role'][i]]:6} start#{r['start'][i]} post{r['post'][i]} margin {r['margin'][i]:4.1f} | L behind @2640/3300/3960/4700/5100 "
              + " ".join(f"{(lead[x]-S[i,x])/8:4.1f}" for x in c) + " | lane " + " ".join(f"{(Y[i,x]-3)/7:4.1f}" for x in c) + f" | plan lane {lane[i,8:12]}")
    shown += 1
    if shown == 4: break
