"""Re-outline the replay runner: the cut-out's edge is ragged (the outermost pixels alternate dark, grey and coat, with
single-pixel spikes), so trim it and draw a clean one. Per frame: drop lone spike pixels (solid with fewer than 3 solid
neighbors), peel off the outermost ring, then put back a continuous 1-px outline round the silhouette in one dark
shade of the color just inside it. Thin parts (reins, spokes, whip-thin mane tips) keep their pixels: the peel skips
any pixel whose removal would leave a hole in a line.

  python art/reoutline.py src.png dst.png
"""
import sys

import numpy as np
from PIL import Image

N8 = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
N4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def shift(m, dy, dx):
    return np.roll(np.roll(m, dy, 0), dx, 1)


def reoutline(a, dark=.38):
    a = a.copy()
    solid = a[..., 3] >= 128
    n8 = sum(shift(solid, dy, dx) for dy, dx in N8)
    solid &= n8 >= 3                                                       # lone spikes off
    edge = solid & ~np.all([shift(solid, dy, dx) for dy, dx in N4], axis=0)
    thick = sum(shift(solid, dy, dx) for dy, dx in N8) >= 5               # inside a body, not a 1-2 px line
    core = solid & ~(edge & thick)                                         # peel the ring where there's body behind it
    ring = ~core & np.any([shift(core, dy, dx) for dy, dx in N8], axis=0)  # the new outline: one px round what's left
    rgb = a[..., :3].astype(float)
    inner = np.zeros_like(rgb); cnt = np.zeros(core.shape)
    for dy, dx in N8:                                                      # the color just inside, for the outline's shade
        m = shift(core & ~ring, dy, dx)
        inner += np.where(m[..., None], shift(rgb, dy, dx), 0); cnt += m
    col = np.where(cnt[..., None] > 0, inner / np.maximum(cnt, 1)[..., None] * dark, 12)
    out = np.zeros_like(a)
    out[core] = a[core]
    out[ring, :3] = col[ring].clip(0, 255).astype(np.uint8)
    out[ring, 3] = 255
    return out


if __name__ == "__main__":
    s = np.asarray(Image.open(sys.argv[1]).convert("RGBA"))
    FW = 208
    o = np.concatenate([reoutline(s[:, k * FW:(k + 1) * FW]) for k in range(s.shape[1] // FW)], axis=1)
    Image.fromarray(o).save(sys.argv[2])
    print(sys.argv[2], o.shape)
