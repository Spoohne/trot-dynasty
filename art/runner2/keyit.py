"""Give the approved brown stride (mockups/pixel/runner2_cycle_c.png) its key colors: the harness leather to purple and
the reins to green, so the replay can recolor each without touching the coat. The leather is a cool dark brown (blue
about level with green), where the bay coat's shadows are red-brown with blue well below green; the reins are a pale
tan, lighter and greyer than any coat highlight. Only on the horse's side of the cell (the driver's skin is warm too).

  python art/runner2/keyit.py      -> mockups/pixel/runner2_keyed.png and a mask preview in art/runner2/keyit_mask.png
"""
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "mockups", "pixel", "runner2_cycle_c.png")
OUT = os.path.join(ROOT, "mockups", "pixel", "runner2_keyed.png")
FW = 208


def masks(a):
    rgb = a[..., :3].astype(int)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    solid = a[..., 3] > 0
    l = rgb.mean(-1)
    x = np.arange(a.shape[1])[None, :] % FW
    horse = solid & (x >= 64)
    leather = horse & (l < 70) & (r > g + 6) & (b >= g - 4) & (r < 110)
    edge = np.zeros_like(solid)                                           # the outline ring: as dark as the leather, never leather
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            edge |= ~np.roll(np.roll(solid, dy, 0), dx, 1)
    leather &= ~edge
    thick = leather.copy()                                                # straps are 2+ px wide; muscle lines are 1 px
    for dy, dx in ((0, 1), (1, 0)):
        thick &= np.roll(np.roll(leather, dy, 0), dx, 1) | np.roll(np.roll(leather, -dy, 0), -dx, 1)
    grown = np.zeros_like(thick)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            grown |= np.roll(np.roll(thick, dy, 0), dx, 1)
    leather &= grown
    reins = solid & (x >= 30) & (l > 105) & (r > b + 25) & (r - b < 95) & (g > b + 8) & (g < 200)
    return leather, reins


def key(a, leather, reins):
    o = a.astype(float).copy()
    lum = o[..., :3].max(-1, keepdims=True) / 255
    o[..., :3] = np.where(leather[..., None], np.array([122, 44, 200]) * np.clip(lum * 2.2, .35, 1.2), o[..., :3])
    o[..., :3] = np.where(reins[..., None], np.array([32, 192, 64]) * np.clip(lum * 1.1, .4, 1.2), o[..., :3])
    return o.clip(0, 255).astype(np.uint8)


if __name__ == "__main__":
    a = np.asarray(Image.open(SRC).convert("RGBA"))
    le, re = masks(a)
    Image.fromarray(key(a, le, re)).save(OUT)
    v = np.zeros_like(a); v[..., 3] = np.where(a[..., 3] > 0, 255, 0)
    v[..., :3] = (a[..., :3].astype(int).mean(-1, keepdims=True) * .35).astype(np.uint8)
    v[le] = (230, 60, 255, 255); v[re] = (60, 255, 90, 255)
    Image.fromarray(v).save(os.path.join(ROOT, "art", "runner2", "keyit_mask.png"))
    print("leather px/frame", [int(le[:, k * FW:(k + 1) * FW].sum()) for k in range(12)])
    print("reins px/frame", [int(re[:, k * FW:(k + 1) * FW].sum()) for k in range(12)])
