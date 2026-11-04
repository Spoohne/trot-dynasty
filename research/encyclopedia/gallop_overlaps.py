"""Do horses occupy the same ground? Runs fields through gallop.run and counts pairs closer than a body and a sulky's width
(the viewer's RACE.BODY 15.5 ft and RACE.WIDE 5.4 ft against a 6 ft lane). python research/encyclopedia/gallop_overlaps.py [races]"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import gallop                                                    # noqa: E402

BODY, WIDE = 15.5 * 0.3048, 0.9 * gallop.CFG["lane_m"]


def overlaps(prog, lat):
    """Pairs on the same ground per field, for one frame: prog, lat (R, n)."""
    dp = np.abs(prog[:, None, :] - prog[:, :, None])
    dl = np.abs(lat[:, None, :] - lat[:, :, None])
    racing = prog < gallop.MILE                                  # past the wire they stop in the record, which is no collision
    return (dp < BODY) & (dl < WIDE) & np.triu(np.ones(prog.shape[1], bool), 1)[None] & racing[:, None, :] & racing[:, :, None]


if __name__ == "__main__":
    R = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    gallop.CFG.update(eval(sys.argv[2]) if len(sys.argv) > 2 else {})
    rng = np.random.default_rng(5)
    q = rng.normal(size=(R, 10, 1))
    st = np.clip(np.rint(60 + 9 * q + 11 * rng.normal(size=(R, 10, 10))), 1, 99)
    p, t, b, f = gallop.run(st, rng=rng, record=True)
    hits = 0
    for lo, hi in ((0, 300), (300, 900), (900, 1800), (1800, len(f))):
        m = np.mean([overlaps(f[k, :, :, 0], f[k, :, :, 1]).sum() / R for k in range(lo, min(hi, len(f)), 15)])
        hits += m
        print(f"frames {lo:4d}-{hi:4d}: {m:.2f} overlapping pairs a field")
    srt = np.sort(f[:900, :, :, 0], 2)
    print(f"leader clear of second, peak in the first 36 s: {(srt[:, :, -1] - srt[:, :, -2]).max(0).mean():.1f} m")
    print(f"post win %: {[round(100 * float((p[:, i] == 1).mean()), 1) for i in range(10)]}")
    print(f"winner {t.min(1).mean():.1f} s, last {np.sort(t, 1)[:, -1].mean() - t.min(1).mean():.1f} s back")
