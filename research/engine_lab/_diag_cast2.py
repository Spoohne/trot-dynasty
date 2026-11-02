import v5_cast as K, v5_choreo as C, random, numpy as np
R = C.R; RN = ["lead", "pocket", "fo", "fol", "line"]
for k, r in enumerate(K.model_races(8, 601)):
    rng = random.Random(0); lead_s, q = C.leader_clock(115.9, rng); beh, lane = K.formations(r, rng)
    S, Y, ts, ty = C.paths(beh, lane, lead_s); ok, why = C.check(S, Y); lead = S.max(0)
    msg = why
    if why.startswith("burst"):
        V = np.diff(S, axis=1) * 20; pre = lead[:-1] < 4400; rel = V[:, pre] - np.median(V[:, pre], axis=0)
        b = [(np.convolve(x, np.ones(40) / 40, "valid").max(), i) for i, x in enumerate(rel)]; m, i = max(b)
        kk = int(np.argmax(np.convolve(rel[i], np.ones(40) / 40, "valid"))) + 20
        msg += f" horse {i} {RN[r['role'][i]]} at {int(lead[kk])} ft, plan lanes {lane[i, 4:10]} beh {beh[i, 4:10].round(1)}"
    if why.startswith("overlap"):
        a, b = map(int, why.split()[1].split("-"))
        c = (np.abs(S[a] - S[b]) < C.BODY) & (np.abs(Y[a] - Y[b]) < C.WIDE) & (np.minimum(S[a], S[b]) > 30)
        kk = int(np.argmax(c)); msg += f" {RN[r['role'][a]]}/{RN[r['role'][b]]} at {int(lead[kk])} ft y {Y[a,kk]:.1f}/{Y[b,kk]:.1f} ds {S[a,kk]-S[b,kk]:.1f}"
    print(k, msg, "| order", r["order"], "margins", [round(r["margin"][i], 1) for i in r["order"]])
