"""Animate the overhead (blimp) sprite from one clean still (SpriteCook still 'H'): from straight above a pacer's
body hardly changes, so the painted body stays exactly as drawn and only the hooves swing (legs on one side move
together), the head nods a pixel and the tail sways. 12 frames, one stride, like the side cycle.
    python animate_top.py -> mockups/pixel/top/cycle12_h.png"""
import math, os
import numpy as np
from PIL import Image
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mockups", "pixel", "top")
still = Image.open(os.path.join(D, "new", "h_fixed.png")).convert("RGBA")   # H with the croup reshaped (no "cheeks")
still = np.array(still.crop(still.getbbox()))
H, W = still.shape[:2]
CY, FR = 40, 12
HEAD_X, TAIL = 160, (28, 62)                      # head from here forward; tail columns
HOOF, HOOF_HI = (24, 20, 20, 255), (70, 64, 62, 255)


def frame(k):
    ph = 2 * math.pi * k / FR
    a = still.copy()
    nod = round(math.sin(ph * 2))                       # the head nods twice a stride (each footfall)
    if nod:
        head = still[:, HEAD_X:].copy()
        a[:, HEAD_X:] = 0
        a[:, HEAD_X:] = np.roll(head, nod, axis=1) if nod > 0 else np.roll(head, nod, axis=1)
        a[:, HEAD_X:HEAD_X + 1] = still[:, HEAD_X:HEAD_X + 1]   # keep the neck joined
    sway = round(math.sin(ph))
    if sway:                                            # the tail swings with the hips
        t0, t1 = TAIL
        a[:, t0:t1] = np.roll(still[:, t0:t1], sway, axis=0)
    # hooves: under the body, peeking out at the sides; near side and off side alternate (lateral gait)
    for side in (-1, 1):
        reach = 7 * math.sin(ph) * side
        for hx, spread in ((112 + reach, 12), (66 - reach, 13)):
            for dx in range(3):
                for dy in range(2):
                    x, y = int(hx) + dx, CY + side * (spread + dy)
                    if 0 <= x < W and 0 <= y < H and a[y, x, 3] < 128:
                        a[y, x] = HOOF if dy else HOOF_HI
    return Image.fromarray(a)


if __name__ == "__main__":
    sheet = Image.new("RGBA", (W * FR, H))
    for k in range(FR):
        sheet.alpha_composite(frame(k), (k * W, 0))
    sheet.save(os.path.join(D, "cycle12_h.png"))
    S = 3
    pv = Image.new("RGBA", (W * S * 2 + 20, H * S * 6 + 40), (90, 64, 48, 255))
    for k in range(FR):
        pv.alpha_composite(frame(k).resize((W * S, H * S), Image.NEAREST), ((k % 2) * (W * S + 10) + 5, (k // 2) * (H * S + 6) + 5))
    pv.save(os.path.join(D, "h_cycle_preview.png"))
    print("frame", W, "x", H)
