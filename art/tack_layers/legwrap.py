"""Leg wraps cut from today's own legs: the cannon of each leg (a band measured up the leg from the hoof) is recolored
as white cloth, shaded by the leg's own light. The shape is the leg's shape, so it can't sit off the leg.
    python art/tack_layers/legwrap.py   -> overlays/legwrap/fNN.png"""
import os
from collections import deque
import numpy as np
from PIL import Image
from overlay import base, zone, OUT, W, H, N

LO = 4                  # the hoof: this many px up the leg from its tip stay bare


def walk(leg, seeds):
    """Steps from the seed pixels to every leg pixel, moving only through the leg."""
    dist = np.full((H, W), 999); q = deque()
    for y, x in zip(*np.nonzero(seeds)):
        dist[y, x] = 0; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                yy, xx = y + dy, x + dx
                if 0 <= yy < H and 0 <= xx < W and leg[yy, xx] and dist[yy, xx] > dist[y, x] + 1:
                    dist[yy, xx] = dist[y, x] + 1; q.append((yy, xx))
    return dist


def legwrap(i):
    f = base(i); a = np.array(f); rgb = a[..., :3].astype(int)
    leg = (a[..., 3] > 0); leg[:64] = False; leg[:, :40] = False            # lower legs, wheel area included (legs pass in front of it)
    blue = (rgb[..., 2] > rgb[..., 0] + 30)                               # the wheel and shafts are never leg
    leg &= ~blue
    top = np.zeros_like(leg); top[64:67] = leg[64:67]                      # where each leg leaves the body
    dt = walk(leg, top); dt[dt == 999] = -1
    pad = np.pad(dt, 3, constant_values=-1)
    near_max = np.max([pad[3 + dy:3 + dy + H, 3 + dx:3 + dx + W] for dy in range(-3, 4) for dx in range(-3, 4)], axis=0)
    tips = leg & (dt >= 12) & (dt == near_max)                             # the far end of each leg: the hoof
    dh = walk(leg, tips)
    dark = rgb.sum(2) < 250                                               # the black stocking of the lower leg
    band = leg & dark & (dh >= LO)                            # all of it, except the hoof at the tip
    lum = a[..., :3].astype(float).mean(2)
    inner = band & np.roll(band, 1, 0) & np.roll(band, -1, 0) & np.roll(band, 1, 1) & np.roll(band, -1, 1)
    edge = band & ~inner
    o = np.zeros((H, W, 4), np.uint8)
    lo, hi = (lum[band].min(), lum[band].max()) if band.any() else (0, 1)
    v = 200 + 50 * (lum - lo) / max(1, hi - lo)                           # the leg's own light and shade, in white
    v = np.where(dh % 4 == 0, v - 16, v)                                   # the wrap's turns
    o[band, 0] = o[band, 1] = o[band, 2] = np.clip(v[band], 0, 255); o[band, 3] = 255
    o[edge, :3] = (150, 150, 158)                                          # cloth edge
    return Image.fromarray(o)


if __name__ == "__main__":
    d = os.path.join(OUT, "legwrap"); os.makedirs(d, exist_ok=True)
    for i in range(N):
        legwrap(i).save(os.path.join(d, f"f{i + 1:02d}.png"))
    print("ok")
