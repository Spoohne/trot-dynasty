"""Patrick's horse (DECISIONS 215): win % by Speed bar from posts 1, 4 and 8 in Half race 1's field."""
import json, sys
import numpy as np
import v4_outcome as V
d = json.load(open("v4/racelab_data.json"))["half"]
p = dict(V.FIXED, **json.load(open("v4/fit_half.json"))["params"])
base = [[h["traits"][k] for k in ("gate", "cruise", "kick", "manners", "grit")] for h in d["horses"]]
def win(post, bars, N=40000):
    t = np.array(base, float); t[post - 1] = [(x - 5) * 0.2 for x in bars]
    D = V.draws(N, 8, 77); D["present"] = np.ones((N, 8), bool); D["traits"] = np.repeat(t[None], N, 0)
    return 100 * np.mean(np.argmax(V.race(p, D, "half")[0], 1) == post - 1)
for post in (1, 4, 8):
    print(f"  post {post}:", "  ".join(f"Speed {sp}: {win(post, [sp, 8, 6, 7, 6]):4.1f}%" for sp in (4, 6, 8, 10, 12)))
