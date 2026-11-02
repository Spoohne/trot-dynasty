"""Shrink SpriteCook's 640px stride frames to the replay runner's cell (208x101, same scale as fe12_cycle.png):
one crop box for all 12 frames (so the rig doesn't jitter), a premultiplied box shrink (no background color bleeds into
the edge), then a hard alpha cut. Writes mockups/pixel/runner2_raw.png; pin it level with fix_pace.py afterwards.

  python art/runner2/shrink.py art/runner2/anim_raw.webp
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FW, FH, N, SRC_W = 208, 101, 12, 640


def shrink(path):
    a = np.asarray(Image.open(path).convert("RGBA")).astype(float)
    frames = [a[:, k * SRC_W:(k + 1) * SRC_W] for k in range(N)]
    solid = np.any([f[..., 3] > 0 for f in frames], axis=0)
    ys, xs = np.nonzero(solid)
    box = frames[0][ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    k = max((xs.max() - xs.min() + 1) / (FW - 1), (ys.max() - ys.min() + 1) / FH)   # fill the cell as fe12 does, never taller than it
    w, h = round(box.shape[1] / k), round(box.shape[0] / k)
    assert h <= FH, f"too tall for the cell: {h}"
    out = np.zeros((FH, FW * N, 4), np.uint8)
    for i, f in enumerate(frames):
        c = f[ys.min():ys.max() + 1, xs.min():xs.max() + 1].copy()
        c[..., :3] *= c[..., 3:] / 255
        s = np.asarray(Image.fromarray(c.clip(0, 255).astype(np.uint8), "RGBA").resize((w, h), Image.BOX)).astype(float)
        al = s[..., 3:]
        rgb = np.where(al > 0, s[..., :3] * 255 / np.maximum(al, 1), 0)
        cell = np.dstack([rgb, np.where(al >= 128, 255, 0)]).clip(0, 255).astype(np.uint8)
        out[FH - h:, i * FW:i * FW + w] = cell                  # hooves on the cell's floor
    return out


if __name__ == "__main__":
    o = shrink(sys.argv[1])
    dst = os.path.join(ROOT, "mockups", "pixel", "runner2_raw.png")
    Image.fromarray(o).save(dst)
    print("wrote", dst, o.shape)
