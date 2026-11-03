"""One hood for every frame of the 208 runner cycle (then art/gear416.py doubles it for the 416 runner).

SpriteCook drew the hood afresh on each frame: the ears are covered on some frames and bare on others, and the back edge
sits anywhere from 30 to 40 pixels behind the nose, so in motion the hood grew down the neck and shrank back. Here one
well-drawn frame (TEMPLATE) is the hood: for each frame it is moved by however far the runner's head moved (found by
matching the head), and trimmed to the runner's outline, so the shape is the same on every frame and rides with the head.

  python art/hood_rigid.py   -> mockups/pixel/tack/hood12.png and hood12_mask.png (the originals kept as *.bak-rigid.png)
"""
import os
import shutil

import numpy as np
from PIL import Image

TACK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mockups", "pixel", "tack")
RUN = os.path.join(os.path.dirname(TACK), "fe12_cycle.png")
FW, N, TEMPLATE, SEARCH = 208, 12, 5, 8               # TEMPLATE: frame 6, a typical hood (ears covered, back edge 30 px)
HEAD = np.s_[0:45, 150:208]                            # where the head is, in every frame


def frame(a, k):
    return a[:, k * FW:(k + 1) * FW]


def roll(a, dy, dx):
    return np.roll(np.roll(a, dy, 0), dx, 1)


def head_shift(run, k):
    """How far the head in frame k sits from the template frame's head."""
    a, b = frame(run, TEMPLATE).astype(float), frame(run, k).astype(float)
    def miss(dy, dx):
        s = roll(a, dy, dx)
        both = (s[HEAD][..., 3] > 127) | (b[HEAD][..., 3] > 127)
        return (((s[HEAD][..., :3] - b[HEAD][..., :3]) ** 2).sum(-1) * both).sum()
    return min(((dy, dx) for dy in range(-SEARCH, SEARCH + 1) for dx in range(-SEARCH, SEARCH + 1)), key=lambda m: miss(*m))


if __name__ == "__main__":
    for name in ("hood12", "hood12_mask"):
        if not os.path.exists(os.path.join(TACK, name + ".bak-rigid.png")):
            shutil.copy(os.path.join(TACK, name + ".png"), os.path.join(TACK, name + ".bak-rigid.png"))
    run = np.asarray(Image.open(RUN).convert("RGBA"))
    hood = np.asarray(Image.open(os.path.join(TACK, "hood12.bak-rigid.png")).convert("RGBA"))
    mask = np.asarray(Image.open(os.path.join(TACK, "hood12_mask.bak-rigid.png")).convert("L"))
    out_h, out_m = np.zeros_like(hood), np.zeros_like(mask)
    moves = []
    for k in range(N):
        dy, dx = head_shift(run, k)
        moves.append((dy, dx))
        on = frame(run, k)[..., 3] > 127                                   # never past the runner's outline
        h, m = roll(frame(hood, TEMPLATE), dy, dx).copy(), roll(frame(mask, TEMPLATE), dy, dx).copy()
        h[~on] = 0; m[~on] = 0
        out_h[:, k * FW:(k + 1) * FW], out_m[:, k * FW:(k + 1) * FW] = h, m
    Image.fromarray(out_h, "RGBA").save(os.path.join(TACK, "hood12.png"), optimize=True)
    Image.fromarray(out_m, "L").save(os.path.join(TACK, "hood12_mask.png"), optimize=True)
    px = [(frame(out_m, k) > 127).sum() for k in range(N)]
    assert max(px) - min(px) < 0.15 * max(px), f"the hood's size still swings: {px}"
    print("head moves:", moves, "\nhood pixels per frame:", px)
