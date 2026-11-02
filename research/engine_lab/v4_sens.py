"""Identifiability check (review 19 step 6): how each fitted setting moves the measured targets, scaled by each
target's tolerance; the singular values show which directions the targets don't pin down.
    python v4_sens.py <track>"""
import json, os, sys
import numpy as np
import v4_outcome as V
track = sys.argv[1]
p0 = json.load(open(os.path.join(V.OUT, f"fit_{track}.json")))["params"]
n = V.N_STARTERS[track]
D, R = V.draws(6000, n, 31), V.rerun_draws(250, 24, n, 33)
def vec(p):
    m = V.measures(p, track, D, R)
    tot, ttot = sum(m[k] for k in V.WORTH_T[track]), 1.0
    v = [x / 3 for x in m["post"]] + [x / 6 for x in m["trips"]] + [m[k] / tot / .05 for k in V.WORTH_T[track]]
    v += [m["rail_lead"] / 8, m["rail_top3"] / 10, m["repeat"] / 6, m["margin_med"] / .5, m["photo"] / 4]
    return np.array(v)
base = vec(p0); J = []
for k, (lo, hi) in zip(V.NAMES, V.BOUNDS):
    h = 0.05 * (hi - lo)
    J.append((vec(dict(p0, **{k: min(hi, p0[k] + h)})) - vec(dict(p0, **{k: max(lo, p0[k] - h)}))) / 2)
J = np.array(J).T                                   # targets x settings: change in tolerance units per 5% of range
U, S, Vt = np.linalg.svd(J, full_matrices=False)
print(f"{track}: effect of each setting (tolerance units per 5% of its range, largest target moved):")
for j, k in enumerate(V.NAMES):
    print(f"   {k:9s} {np.abs(J[:, j]).max():5.2f}")
print("   singular values:", np.round(S, 3))
weak = Vt[-1]; print("   weakest direction:", {k: round(float(w), 2) for k, w in zip(V.NAMES, weak) if abs(w) > .2})
