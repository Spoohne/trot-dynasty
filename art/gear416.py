"""The Tack Room gear overlays (hood, leg wraps and their masks) at the 416 runner's size and layout (6 across, 2 down).

The overlays are drawn on the old 208 sheet. The 416 runner was rebuilt from the raw frames and pinned level on its own
(art/fe12_416.py), so a few of its frames sit a pixel higher or lower than the 208 frames doubled; the replay scaled the
overlays 2x, which left the gear a pixel off on those frames (it shivered at 12 frames a second). Here each
overlay frame is doubled smoothly (as before) and moved by that frame's own offset, measured by
matching the doubled 208 runner to the 416 runner around that piece of gear.

  python art/gear416.py   -> mockups/pixel/tack/<name>416.png
"""
import os

import numpy as np
from PIL import Image

PIX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mockups", "pixel")
FW, FH, N, COLS = 208, 101, 12, 6
GEAR = {"hood12": "hood12_mask", "wraps12": "wraps12_mask"}      # overlay -> the mask that says where its pixels are
GAIN = 20                                                        # pixels of better fit before a frame is moved (below: noise)
SHIFT = 6                                                        # largest move tried, in 416 pixels


def x2(a):
    return np.kron(a, np.ones((2, 2) + (1,) * (a.ndim - 2), a.dtype))


def frame416(a, k):
    r, c = divmod(k, COLS)
    return a[r * 2 * FH:(r + 1) * 2 * FH, c * 2 * FW:(c + 1) * 2 * FW]


def grow(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def offset(old, new, near):
    """(dy, dx) that best lays the doubled 208 silhouette on the 416 one, around the gear; (0, 0) unless clearly better."""
    s, near = x2(old), x2(grow(near, 6))
    ys, xs = np.nonzero(near)
    if not len(ys):
        return 0, 0
    box = np.s_[max(ys.min() - 12, 0):ys.max() + 12, max(xs.min() - 12, 0):xs.max() + 12]
    miss = {(dy, dx): (np.roll(np.roll(s, dy, 0), dx, 1)[box] ^ new[box]).sum()
            for dy in range(-SHIFT, SHIFT + 1) for dx in range(-SHIFT, SHIFT + 1)}
    best = min(miss, key=miss.get)
    return best if miss[(0, 0)] - miss[best] >= GAIN else (0, 0)


def shift(a, dy, dx):
    out = np.zeros_like(a)
    h, w = a.shape[:2]
    out[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = a[max(-dy, 0):h - max(dy, 0), max(-dx, 0):w - max(dx, 0)]
    return out


if __name__ == "__main__":
    old = np.asarray(Image.open(os.path.join(PIX, "fe12_cycle.png")).convert("RGBA"))[..., 3] > 127
    new = np.asarray(Image.open(os.path.join(PIX, "fe12_cycle416.png")).convert("RGBA"))[..., 3] > 127
    for over, mask in GEAR.items():
        m = np.asarray(Image.open(os.path.join(PIX, "tack", mask + ".png")).convert("L"))
        moves = [offset(old[:, k * FW:(k + 1) * FW], frame416(new, k), m[:, k * FW:(k + 1) * FW] > 127) for k in range(N)]
        for name in (over, mask):
            im = Image.open(os.path.join(PIX, "tack", name + ".png"))
            a = np.asarray(im)
            out = np.zeros((2 * FH * (N // COLS), 2 * FW * COLS) + a.shape[2:], a.dtype)
            for k, (dy, dx) in enumerate(moves):
                r, c = divmod(k, COLS)
                big = np.asarray(im.crop((k * FW, 0, (k + 1) * FW, FH)).resize((2 * FW, 2 * FH), Image.BICUBIC))   # smooth, as the runner is
                out[r * 2 * FH:(r + 1) * 2 * FH, c * 2 * FW:(c + 1) * 2 * FW] = shift(big, dy, dx)
            Image.fromarray(out, im.mode).save(os.path.join(PIX, "tack", name + "416.png"), optimize=True)
        print(over, "moved frames:", {k + 1: mv for k, mv in enumerate(moves) if mv != (0, 0)})
