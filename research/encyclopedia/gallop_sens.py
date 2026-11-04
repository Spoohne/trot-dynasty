"""What +10 on one stat buys: a random horse in each field of a world-like population, same dice with and without.
  python research/encyclopedia/gallop_sens.py [fields=400] ["{'cfg_key': value}"] [speed,staying,...]
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import gallop                                                    # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
gallop.CFG.update(eval(sys.argv[2]) if len(sys.argv) > 2 else {})
rng = np.random.default_rng(11)
base = np.clip(np.rint(60 + 9 * rng.normal(size=(N, 10, 1)) + 11 * rng.normal(size=(N, 10, 10))), 1, 89)   # room for +10 under the game's 99
who = rng.integers(0, 10, N)
at = np.arange(N)
p0, t0, _ = gallop.run(base, rng=np.random.default_rng(3))
print(f"winner {t0.min(1).mean():.1f} s, 2nd +{(np.sort(t0, 1)[:, 1] - t0.min(1)).mean():.2f}, last +{(t0.max(1) - t0.min(1)).mean():.1f}, base win {100 * (p0[at, who] == 1).mean():.1f}%")
print("stat        dTime(s)  dPlace   win%")
rows = []
only = sys.argv[3].split(",") if len(sys.argv) > 3 else gallop.STATS
for k, name in enumerate(gallop.STATS):
    if name not in only:
        continue
    alt = base.copy(); alt[at, who, k] += 10
    p1, t1, _ = gallop.run(alt, rng=np.random.default_rng(3))
    rows.append((name, (t1[at, who] - t0[at, who]).mean() / gallop.CFG["clock_scale"], (p1[at, who] - p0[at, who]).mean(), 100 * (p1[at, who] == 1).mean(), (p1[at, who] - p0[at, who]).std() / N ** 0.5))
for name, dt, dp, w, se in sorted(rows, key=lambda r: r[2]):
    print(f"{name:<11}{dt:8.3f}{dp:8.2f} +-{se:.2f}   {w:.1f}")
