"""The sulky shaft as what it is: a rigid straight pole, drawn identically in every frame from the sulky's front corner
to the ring on the harness saddle. The model's own (bendy) shaft is cleared out of the corridor first.
    python shaft.py sheet_a.png out.png"""
import sys
import numpy as np
from PIL import Image

W, H = 208, 101
A, B = np.array([23.0, 55.0]), np.array([125.0, 31.0])           # sulky front corner -> harness saddle ring
CORE, MID, EDGE = (90, 150, 255), (40, 90, 220), (12, 24, 70)


def seg_dist(xx, yy):
    d = B - A; t = np.clip(((xx - A[0]) * d[0] + (yy - A[1]) * d[1]) / (d @ d), 0, 1)
    px, py = A[0] + t * d[0], A[1] + t * d[1]
    return np.hypot(xx - px, yy - py), t


def pole(f):
    a = np.array(f).astype(int); yy, xx = np.mgrid[:H, :W]; dist, t = seg_dist(xx, yy)
    blue = (((a[..., 2] > a[..., 0] + 40) | ((a[..., 2] > a[..., 0] + 12) & (a[..., :3].sum(2) < 200))) & (a[..., 3] > 0))   # shaft and its navy outline
    reins = A + np.array([15.0, -18.0])                                 # the driver's hands: reins run from here, above the shaft
    rein_y = reins[1] + (xx - reins[0]) * (B[1] - 2 - reins[1]) / (B[0] - reins[0])
    wheel = np.hypot(xx - 30, yy - 75) <= 29
    old = blue & (xx >= 40) & (xx <= B[0] - 3) & (yy > rein_y + 2) & (yy < 64) & ~wheel   # the model's own shaft, wherever it bent to
    src = a.copy(); keep = ~old & (a[..., 3] > 0)
    for y, x in zip(*np.nonzero(old)):                                  # filled with the median of the untouched pixels around it
        for r in (2, 3, 4, 6):
            y0, y1, x0, x1 = max(0, y - r), min(H, y + r + 1), max(0, x - r), min(W, x + r + 1)
            k = keep[y0:y1, x0:x1]
            if k.sum() >= 4:
                a[y, x] = np.median(src[y0:y1, x0:x1][k], axis=0).astype(int); break
        else:
            a[y, x] = (0, 0, 0, 0)
    on = (t > 0) & (t < 1)
    a[on & (dist <= 1.6)] = (*EDGE, 255)
    a[on & (dist <= 1.0)] = (*MID, 255)
    a[on & (dist <= .5)] = (*CORE, 255)
    return Image.fromarray(a.astype(np.uint8))


if __name__ == "__main__":
    s = Image.open(sys.argv[1]).convert("RGBA"); out = Image.new("RGBA", s.size)
    for i in range(s.width // W):
        out.paste(pole(s.crop((i * W, 0, (i + 1) * W, H))), (i * W, 0))
    out.save(sys.argv[2])
