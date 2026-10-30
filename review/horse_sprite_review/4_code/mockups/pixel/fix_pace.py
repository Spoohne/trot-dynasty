"""Take the hitch out of the pacing cycle. In the generated frames the horse's back sinks about
8 px over the second half of the stride and snaps back up at the loop: that reads as hobbling.
Hooves and wheel stay on the ground, so only the horse's upper body is moved: rows above the
belly shift fully, the legs stretch to meet them, and the driver and sulky are left alone.

    python mockups/pixel/fix_pace.py                         pace.png (8 frames) -> pace_fixed.png
    python mockups/pixel/fix_pace.py pace12.png 12 pace_cycle.png --drop 11
    python mockups/pixel/fix_pace.py fe.png 8 fe_cycle.png --bob 0 --anchor pad    dead level, pinned at the saddle pad
The 12-frame cycle's last frame nearly repeats its first, a held pose at the loop, so it's dropped.
"""
import math, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
N = 8
X0, BODY, LEGS = .31, .5, .88         # as fractions of the frame: columns left of X0 are the driver and sulky,
                                      # rows above BODY move fully, between BODY and LEGS the shift fades out


def back(a):
    w = a.shape[1]
    return int(np.nonzero((a[:, int(w * .55):int(w * .76), 3] > 60).any(axis=1))[0].min())


def pad(a):
    """Top of the white saddle pad: a fixed point on the horse's back, steadier than the outline."""
    h, w = a.shape[:2]
    white = (a[..., :3] > 205).all(axis=2) & (a[..., 3] > 200)
    white[:int(h * .12)] = white[int(h * .5):] = False
    white[:, :int(w * .45)] = white[:, int(w * .75):] = False
    return int(np.nonzero(white.any(axis=1))[0].min())


def main(src="pace.png", n=N, dst="pace_fixed.png", drop=(), bob=1.5, anchor=back):
    s = np.asarray(Image.open(os.path.join(HERE, src)).convert("RGBA"))
    h, w = s.shape[0], s.shape[1] // n
    x0, body, legs = int(w * X0), int(h * BODY), int(h * LEGS)
    keep = [i for i in range(n) if i not in drop]
    base = int(np.median([anchor(s[:, i * w:(i + 1) * w]) for i in keep]))
    target = [base - round(bob * math.cos(4 * math.pi * k / len(keep))) for k in range(len(keep))]   # bob=0: dead level   # a small even bob, one per lateral pair
    out = np.zeros((h, w * len(keep), 4), np.uint8)
    before, after = [], []
    for k, i in enumerate(keep):
        f = s[:, i * w:(i + 1) * w]
        d = target[k] - anchor(f)                                      # rows to move the body by (negative is up)
        g = f.copy()
        g[:, x0:] = 0
        for y in range(h):
            share = 1.0 if y < body else max(0.0, (legs - y) / (legs - body))
            row = int(round(y - d * share))                           # nearest row: stays crisp pixel art
            if 0 <= row < h:
                g[y, x0:] = f[row, x0:]
        before.append(anchor(f)); after.append(anchor(g))
        out[:, k * w:(k + 1) * w] = g
    Image.fromarray(out).save(os.path.join(HERE, dst))
    print("back line before:", before)
    print("back line after: ", after)
    assert all(abs(a - t) <= 1 for a, t in zip(after, target)), "the body follows the even bob, no sink and snap"


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    drop = tuple(int(v) for v in opt("--drop").split(",")) if opt("--drop") else ()
    bob = float(opt("--bob")) if opt("--bob") else 1.5
    anchor = pad if opt("--anchor") == "pad" else back
    a = [v for i, v in enumerate(a) if not v.startswith("--") and not (i and a[i - 1].startswith("--"))]
    main(*([a[0], int(a[1]), a[2]] if a else []), drop=drop, bob=bob, anchor=anchor)
