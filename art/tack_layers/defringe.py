"""Clean the pale fringe that background removal leaves round a sprite's outline: an edge pixel (touching transparency)
that is light and colorless takes the darkest opaque neighbour's colour. Real whites are left alone: the wraps (mask),
the saddle pad, and the stock wheel and driver (left of SAFE_X, laid from today's frames).
    python art/tack_layers/defringe.py <sheet.png> <mask.png> <out.png>"""
import sys
import numpy as np
from PIL import Image

W, H = 208, 101
SAFE_X = 70                     # wheel and driver: today's own clean pixels
PAD = (95, 135, 18, 50)         # x0, x1, y0, y1 of the saddle pad region in a frame


def defringe(a, mask, passes=2):
    a = a.copy(); hh, ww = a.shape[:2]; total = 0
    for _ in range(passes):
        op = a[:, :, 3] > 0
        edge = op & ~(np.roll(op, 1, 0) & np.roll(op, -1, 0) & np.roll(op, 1, 1) & np.roll(op, -1, 1))
        rgb = a[:, :, :3].astype(int)
        pale = (rgb.sum(2) > 420) & (rgb.max(2) - rgb.min(2) < 40)
        xs = np.arange(ww) % W; ys = np.arange(hh)
        safe = (xs[None, :] < SAFE_X) | mask | ((xs[None, :] >= PAD[0]) & (xs[None, :] < PAD[1]) & (ys[:, None] >= PAD[2]) & (ys[:, None] < PAD[3]))
        hit = edge & pale & ~safe
        for y, x in zip(*np.nonzero(hit)):
            best = None
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if (dy or dx) and 0 <= yy < hh and 0 <= xx < ww and a[yy, xx, 3] and not hit[yy, xx]:
                        s = int(a[yy, xx, :3].astype(int).sum())
                        if best is None or s < best[0]:
                            best = (s, a[yy, xx].copy())
            if best is not None:
                a[y, x, :3] = best[1][:3]
            else:
                a[y, x, 3] = 0                                         # a lone speck with no horse beside it
            total += 1
    return a, total


if __name__ == "__main__":
    src, msk, out = sys.argv[1:4]
    a = np.array(Image.open(src).convert("RGBA")); m = np.array(Image.open(msk)) > 128
    b, n = defringe(a, m)
    Image.fromarray(b).save(out); print("fringe pixels cleaned:", n)
