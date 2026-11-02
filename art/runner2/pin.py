"""Pin the new runner's stride (mockups/pixel/runner2_raw.png) for the replay: the body dead level at the saddle pad, the
head held at one height so it only reaches forward and back (the original's steady nod, not a bob), and both shifts
blended across the columns, so the reins and shafts that cross from the driver to the horse bend instead of breaking.
Rows above the belly take the full shift, fading to none at the hooves (as fix_pace.py does), and the driver and wheel
never move.

  python art/runner2/pin.py [src] [dst]      default runner2_raw.png -> runner2_cycle.png in mockups/pixel
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "mockups", "pixel"))
from fix_pace import pad                                               # noqa: E402  the top of the white saddle pad

FW, FH, N = 208, 101, 12
X0, RAMP = 64, 24            # the driver's side ends at X0; the body shift fades in over RAMP columns either side of it
NECK, HEAD = 150, 176        # the head shift fades in from NECK to HEAD and holds to the nose
BODY, LEGS = .5, .88         # as fractions of the cell: rows above BODY move fully, fading out by LEGS
REACH = .35                  # how much of the head's own forward-and-back reach to keep: a slight nod
SEAT, AXLE = 45, 62          # the sulky: rows down to SEAT ride with the driver, from AXLE down sit on the wheel
GIVE = .5                    # how much of the driver's own bounce to keep, on the seat's spring; the wheel keeps none


def head_top(f):
    return int(np.nonzero((f[:, HEAD:, 3] > 0).any(1))[0].min())


def nose_x(f):
    return int(np.nonzero((f[:int(FH * BODY), :, 3] > 0).any(0))[0].max())


def ramp(x, a, b):
    return np.clip((x - a) / (b - a), 0, 1)


def pin(s):
    frames = [s[:, k * FW:(k + 1) * FW] for k in range(N)]
    base = int(np.median([pad(f) for f in frames]))
    body_d = [base - pad(f) for f in frames]                              # rows to move the body by (negative is up)
    heads = [head_top(f) + d for f, d in zip(frames, body_d)]           # where the head sits once the body is level
    hbase = int(np.median(heads))
    head_d = [hbase - h for h in heads]                                   # and the extra to hold it at one height
    xs = np.arange(FW)
    out = np.zeros_like(s)
    body, legs = int(FH * BODY), int(FH * LEGS)
    for k, f in enumerate(frames):
        dx = body_d[k] * ramp(xs, X0 - RAMP, X0 + RAMP) + head_d[k] * ramp(xs, NECK, HEAD)   # each column's shift
        g = np.zeros_like(f)
        for y in range(FH):
            share = 1.0 if y < body else max(0.0, (legs - y) / (legs - body))
            src = np.rint(y - dx * share).astype(int)                     # nearest row: stays crisp pixel art
            ok = (src >= 0) & (src < FH)
            g[y, xs[ok]] = f[src[ok], xs[ok]]
        out[:, k * FW:(k + 1) * FW] = g
    wheel = [int(np.nonzero((out[:, k * FW:k * FW + 50, 3] > 0).any(1))[0].max()) for k in range(N)]
    ground = max(wheel)
    ys = np.arange(FH)
    for k in range(N):                                                    # the wheel planted on the ground, the driver on a spring
        wd = ground - wheel[k]                                            # rows the wheel must drop to touch the ground
        rows = wd * (GIVE + (1 - GIVE) * ramp(ys, SEAT, AXLE))           # per row: half of it at the seat, all of it at the axle
        f = out[:, k * FW:(k + 1) * FW].copy()
        g = f.copy()
        for x in range(X0 + RAMP):
            share = 1 - ramp(x, X0 - RAMP, X0 + RAMP)                     # fading out toward the horse, as the body pin fades in
            src = np.rint(ys - rows * share).astype(int)
            ok = (src >= 0) & (src < FH)
            col = np.zeros((FH, 4), f.dtype)
            col[ok] = f[src[ok], x]
            g[:, x] = col
        out[:, k * FW:(k + 1) * FW] = g
    noses = [nose_x(out[:, k * FW:(k + 1) * FW]) for k in range(N)]
    nbase = float(np.median(noses))
    for k in range(N):                                                    # then ease the head's reach toward the middle
        f = out[:, k * FW:(k + 1) * FW].copy()
        hx = (nbase + (noses[k] - nbase) * REACH) - noses[k]             # columns to move the head by (negative is back)
        g = f.copy()
        for x in range(NECK, FW):
            src = int(round(x - hx * ramp(x, NECK, HEAD)))
            g[:int(FH * BODY), x] = f[:int(FH * BODY), src] if 0 <= src < FW else 0
        out[:, k * FW:(k + 1) * FW] = g
    tops = [head_top(out[:, k * FW:(k + 1) * FW]) for k in range(N)]     # the reach moves columns under the head: hold its height again
    tbase = int(np.median(tops))
    for k in range(N):
        f = out[:, k * FW:(k + 1) * FW].copy()
        g = f.copy()
        for x in range(NECK, FW):
            d = int(round((tbase - tops[k]) * ramp(x, NECK, HEAD)))
            if d:
                col = np.zeros_like(f[:, x])
                if d > 0:
                    col[d:int(FH * BODY)] = f[:int(FH * BODY) - d, x]
                else:
                    col[:int(FH * BODY) + d] = f[-d:int(FH * BODY), x]
                col[int(FH * BODY):] = f[int(FH * BODY):, x]
                g[:, x] = col
        out[:, k * FW:(k + 1) * FW] = g
    return out, [pad(out[:, k * FW:(k + 1) * FW]) for k in range(N)], [head_top(out[:, k * FW:(k + 1) * FW]) for k in range(N)]


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "mockups", "pixel", "runner2_raw.png")
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "mockups", "pixel", "runner2_cycle.png")
    o, pads, heads = pin(np.asarray(Image.open(src).convert("RGBA")))
    Image.fromarray(o).save(dst)
    print("pad line:", pads, "\nhead top:", heads)
    assert max(pads) - min(pads) <= 1 and max(heads) - min(heads) <= 1, "body level and head steady"
