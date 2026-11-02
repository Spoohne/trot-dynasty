"""Pixel-art edge smoothing for the replay runner: Scale2x (EPX), applied twice for 4x. Each pixel becomes a 2x2 block,
and where two neighbors that meet at a corner match each other (and not the others), that corner of the block takes
their color, so stair-steps along diagonals become clean lines and nothing is blurred: no new colors are made.
Optionally the outline's alpha is softened a touch after (aa=True), for a page that blends edges instead of cutting.

  python art/edge_smooth.py src.png dst.png [times=2] [aa]
"""
import sys

import numpy as np
from PIL import Image


def scale2x(a):
    """EPX on an RGBA array: returns an array twice the size."""
    p = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode="edge")
    E = p[1:-1, 1:-1]
    B, D, F, H = p[:-2, 1:-1], p[1:-1, :-2], p[1:-1, 2:], p[2:, 1:-1]   # up, left, right, down
    eq = lambda x, y: (x == y).all(-1)
    ok = ~eq(B, H) & ~eq(D, F)
    E0 = np.where((ok & eq(D, B))[..., None], D, E)
    E1 = np.where((ok & eq(B, F))[..., None], F, E)
    E2 = np.where((ok & eq(D, H))[..., None], D, E)
    E3 = np.where((ok & eq(H, F))[..., None], F, E)
    h, w = a.shape[:2]
    out = np.empty((h * 2, w * 2, a.shape[2]), a.dtype)
    out[0::2, 0::2], out[0::2, 1::2], out[1::2, 0::2], out[1::2, 1::2] = E0, E1, E2, E3
    return out


def smooth_outline(a, times=2):
    """EPX on the silhouette alone (the art's shading has too many colors for EPX to find equal neighbors): the outline's
    stair-steps become clean diagonals, and each pixel the new outline adds takes the color of the art beside it."""
    solid = (a[..., 3] >= 128).astype(np.uint8)[..., None]
    for _ in range(times):
        solid = scale2x(solid)
    k = 2 ** times
    big = a.repeat(k, 0).repeat(k, 1)
    out = big.copy()
    add = (solid[..., 0] == 1) & (big[..., 3] < 128)
    if add.any():                                                       # fill each added pixel from the nearest solid one
        ys, xs = np.nonzero(add)
        for y, x in zip(ys, xs):
            for r in range(1, k + 2):
                win = big[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1]
                m = win[..., 3] >= 128
                if m.any():
                    out[y, x] = win[m][0]; break
    out[..., 3] = np.where(solid[..., 0] == 1, 255, 0)
    return out


def soften_alpha(a):
    al = a[..., 3].astype(float)
    p = np.pad(al, 1, mode="edge")
    blur = sum(p[1 + dy:p.shape[0] - 1 + dy, 1 + dx:p.shape[1] - 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9
    o = a.copy()
    o[..., 3] = np.where(al > 0, np.maximum(blur, al * .55), blur * .6).clip(0, 255).astype(np.uint8)
    return o


if __name__ == "__main__":
    a = np.asarray(Image.open(sys.argv[1]).convert("RGBA"))
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    a = smooth_outline(a, n) if "outline" in sys.argv[4:] else a
    for _ in range(0 if "outline" in sys.argv[4:] else n):
        a = scale2x(a)
    if "aa" in sys.argv[4:]:
        a = soften_alpha(a)
    Image.fromarray(a).save(sys.argv[2])
    print(sys.argv[2], a.shape)
