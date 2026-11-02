"""The harness on the approved brown stride, traced: the leather is the same dark brown as the horse's shading, so no
color rule finds it alone. Each strap is a traced path instead, snapped per frame to the darkest line in its reach,
and only the dark pixels along it are leather:
  girth          a vertical band behind the saddle pad (its center searched across x 121-129)
  breast collar  a straight strap from the girth forward and down to the chest (both ends searched)
  bridle         the dark straps in the head box (cheek piece, browband, noseband), outline and eye left out
The reins come from keyit.py's color rule (they're the only pale tan). Writes the keyed sheet and a mask preview.

  python art/runner2/trace_harness.py   -> mockups/pixel/runner2_keyed.png, art/runner2/trace_mask.png
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyit import SRC, OUT, FW, masks, key                              # noqa: E402  the reins' color rule and the key repaint

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FH = 101


def line_pixels(x0, y0, x1, y1, w):
    """Cells within w of the segment, as (y, x) arrays."""
    ys, xs = np.mgrid[:FH, :FW]
    dx, dy = x1 - x0, y1 - y0
    t = np.clip(((xs - x0) * dx + (ys - y0) * dy) / (dx * dx + dy * dy), 0, 1)
    return np.hypot(xs - x0 - t * dx, ys - y0 - t * dy) <= w


def frame_mask(f):
    rgb = f[..., :3].astype(int)
    l = rgb.mean(-1)
    solid = f[..., 3] > 0
    edge = np.zeros_like(solid)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            edge |= ~np.roll(np.roll(solid, dy, 0), dx, 1)
    dark = solid & ~edge & (l < 72) & (rgb.max(-1) - rgb.min(-1) < 90)
    out = np.zeros_like(solid)
    # girth: the darkest 5-px column band in x 119-131, rows 18-60
    best = max(range(119, 127), key=lambda c: -l[18:60, c:c + 5][solid[18:60, c:c + 5]].mean())
    band = np.zeros_like(solid); band[16:62, best:best + 6] = True
    out |= band & dark
    # breast collar: the darkest straight strap from the girth to the chest
    gx = best + 5
    cand = [(y0, y1) for y0 in range(29, 38) for y1 in range(36, 48)]
    score = lambda yy: l[line_pixels(gx, yy[0], 165, yy[1], .7) & solid].mean()
    y0, y1 = min(cand, key=score)
    out |= line_pixels(gx, y0, 165, y1, 1.6) & dark
    # bridle: found from its silver ring (light grey, by the mouth), then the cheek strap up to the crown behind the ears
    # and the noseband forward round the nose, each the darkest straight line in its reach
    rg = np.zeros_like(solid); rg[18:36, 183:200] = True
    ry, rx = np.nonzero(rg & solid & (l > 115) & (rgb.max(-1) - rgb.min(-1) < 40))
    if len(rx):
        cx, cy = rx.mean(), ry.mean()
        dk = lambda m: l[m & solid].mean() if (m & solid).any() else 999
        crown = min(((x, y) for x in range(174, 188) for y in range(7, 15)), key=lambda q: dk(line_pixels(cx, cy, q[0], q[1], .7)))
        nose = min(((x, y) for x in range(196, 207) for y in range(24, 35)), key=lambda q: dk(line_pixels(cx, cy, q[0], q[1], .7)))
        strap = line_pixels(cx, cy, *crown, 1.4) | line_pixels(cx, cy, *nose, 1.4)
        out |= strap & solid & ~edge & (l < 80)
    return out


if __name__ == "__main__":
    a = np.asarray(Image.open(SRC).convert("RGBA"))
    _, reins = masks(a)
    leather = np.zeros(a.shape[:2], bool)
    for k in range(12):
        leather[:, k * FW:(k + 1) * FW] = frame_mask(a[:, k * FW:(k + 1) * FW])
    leather &= ~reins
    Image.fromarray(key(a, leather, reins)).save(OUT)
    v = np.zeros_like(a); v[..., 3] = np.where(a[..., 3] > 0, 255, 0)
    v[..., :3] = (a[..., :3].astype(int).mean(-1, keepdims=True) * .35).astype(np.uint8)
    v[leather] = (230, 60, 255, 255); v[reins] = (60, 255, 90, 255)
    Image.fromarray(v).save(os.path.join(ROOT, "art", "runner2", "trace_mask.png"))
    print("leather px/frame", [int(leather[:, k * FW:(k + 1) * FW].sum()) for k in range(12)])
