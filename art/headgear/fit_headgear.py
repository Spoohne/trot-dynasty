"""Head number and blinkers on the replay runner: the gear cut out of SpriteCook's still (hg1.png, the runner with the
gear added, from the user's reference photo) and set on every frame of the stride at the same place on the head,
found from that frame's nose tip and the top of its head. The gear art is used as drawn: the plate small and faint.

  python art/headgear/fit_headgear.py  -> mockups/pixel/tack/headgear12.png (overlay) and a preview sheet
"""
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FW, FH, N = 208, 101, 12
TOP = 12                     # the runner's cell has no room above the ears: the gear sheet is this much taller
PLATE = (163, 0, 176, 14)            # the number plate and its post above the ears, in hg1
CUP = (185, 17, 197, 28)             # the blinker cup over the eye, in hg1


def head(a):
    """(nose x, head top y): the rightmost solid pixel above the belly, and the topmost solid one from x 176 on."""
    s = a[..., 3] > 0
    return int(np.nonzero(s[:50].any(0))[0].max()), int(np.nonzero(s[:, 176:].any(1))[0].min())


def gear():
    g = np.asarray(Image.open(os.path.join(HERE, "hg1.png")).convert("RGBA")).astype(int)
    rgb = g[..., :3]
    sat = rgb.max(-1) - rgb.min(-1)
    m = np.zeros(g.shape[:2], bool)
    x0, y0, x1, y1 = PLATE
    m[y0:y1, x0:x1] = g[y0:y1, x0:x1, 3] > 0
    x0, y0, x1, y1 = CUP
    m[y0:y1, x0:x1] = (g[y0:y1, x0:x1, 3] > 0) & (sat[y0:y1, x0:x1] < 35)       # the grey cup, not the coat or the blue bridle
    out = np.zeros_like(g); out[m] = g[m]
    nx, hy = head(g)                                                     # the plate stands left of x 176, so this is the ears
    return out.astype(np.uint8), nx, hy


if __name__ == "__main__":
    run = np.asarray(Image.open(os.path.join(ROOT, "mockups", "pixel", "fe12_cycle.png")).convert("RGBA"))
    g, gnx, ghy = gear()
    over = np.zeros((FH + TOP, FW * N, 4), np.uint8)
    for k in range(N):
        nx, hy = head(run[:, k * FW:(k + 1) * FW])
        dx, dy = nx - gnx, hy - ghy
        layer = Image.new("RGBA", (FW, FH + TOP)); layer.alpha_composite(Image.fromarray(g), (dx, dy + TOP))
        over[:, k * FW:(k + 1) * FW] = np.asarray(layer)
    os.makedirs(os.path.join(ROOT, "mockups", "pixel", "tack"), exist_ok=True)
    Image.fromarray(over).save(os.path.join(ROOT, "mockups", "pixel", "tack", "headgear12.png"))
    print("gear head anchor", gnx, ghy)
