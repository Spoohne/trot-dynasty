"""Halo cleanup for the replay runner's stride sheet (mockups/pixel/fe12_cycle.png).

The sprite was cut out of a lighter background, which left a rim of light, greyish pixels along the outline: round the
muzzle, the mane, the body, the legs and the harness. Up close (the wire shot) the rim reads as a jagged white cut-out.
This pass looks at every pixel within two of the outline. Where it is clearly lighter and greyer than the art just
inside it (or a bright white rim against a dark inside), it takes that inner tone, a shade darker. Thin parts with no
inside of their own (spokes, reins in the air) and genuinely light areas (socks, a grey coat, the blaze) are left alone.

  python art/dehalo_runner.py            -> writes mockups/pixel/fe12_cycle_clean.png (the original is untouched)
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "mockups", "pixel", "fe12_cycle.png")
OUT = os.path.join(ROOT, "mockups", "pixel", "fe12_cycle_clean.png")


def dehalo(img, band=2, inner=3, lift=20, white=150, dark_inside=150):
    a = np.asarray(img.convert("RGBA")).astype(np.float32)
    H, W = a.shape[:2]
    solid = a[..., 3] >= 128
    # distance (in pixels, chessboard) from the nearest see-through pixel, up to inner+1
    dist = np.where(solid, inner + 1, 0).astype(np.int32)
    for d in range(1, inner + 1):
        near = np.zeros_like(solid)
        pad = np.pad(~solid, d, constant_values=True)
        for dy in range(-d, d + 1):
            for dx in range(-d, d + 1):
                near |= pad[d + dy:d + dy + H, d + dx:d + dx + W]
        dist = np.where(solid & near & (dist > d), d, dist)
    lum = a[..., :3].mean(-1)
    sat = a[..., :3].max(-1) - a[..., :3].min(-1)
    out = a.copy()
    ys, xs = np.nonzero(solid & (dist <= band))
    changed = 0
    for y, x in zip(ys, xs):
        l, s = lum[y, x], sat[y, x]
        edge = dist[y, x] == 1                                              # the outermost ring: always a dark outline
        if not edge and (l < 70 or s >= 90):
            continue
        y0, y1, x0, x1 = max(0, y - inner), min(H, y + inner + 1), max(0, x - inner), min(W, x + inner + 1)
        win = dist[y0:y1, x0:x1] > band                                    # the art properly inside the outline
        if not win.any():
            continue                                                        # a thin part with no inside: leave it
        ref = a[y0:y1, x0:x1, :3][win]
        il = ref.mean()
        rm = ref.mean(0)
        if rm[2] > rm[0] + 30:
            continue                                                        # beside blue (the sulky wheel, silks): keep its white rim
        rs = (ref.max(1) - ref.min(1)).mean()
        grey = s < 40 and rs > s + 25                                       # a grey fleck on a colored coat: the cut-out fringe
        if il < 70 and l <= white:
            continue                                                        # dark parts (hooves, legs, mane): their grey rim is their shape; darkening it thins them
        if edge:                                               # dark parts (hooves, legs, mane) already read as edge: outlining them thins them
            out[y, x, :3] = np.minimum(rm * .5, a[y, x, :3])
            changed += 1
            continue
        if l > il + lift or grey or (l > white and s < 60 and il < dark_inside):
            out[y, x, :3] = ref.mean(0) * .85
            changed += 1
    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA"), changed


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else SRC
    out = sys.argv[2] if len(sys.argv) > 2 else OUT
    img, n = dehalo(Image.open(src))
    img.save(out)
    print(f"cleaned {n} halo pixels -> {out}")
