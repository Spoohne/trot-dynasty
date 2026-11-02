"""Re-pin the replay runner (mockups/pixel/fe12_cycle_raw.png) dead level at the saddle pad, as fix_pace.py --bob 0
--anchor pad did, but with the shift blended across the columns where the driver's side meets the horse's: fix_pace
moved every column right of one line and none left of it, so the reins and shafts that cross that line snapped.
Rows above the belly take the full shift, fading out by the hooves; the driver and wheel stay put.

  python art/fe12_pin_blend.py   -> mockups/pixel/fe12_cycle.bak-halo.png (the pinned art before the outline pass)
  python art/dehalo_runner.py mockups/pixel/fe12_cycle.bak-halo.png mockups/pixel/fe12_cycle.png
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIX = os.path.join(ROOT, "mockups", "pixel")
sys.path.insert(0, PIX)
from fix_pace import pad, X0, BODY, LEGS                                # noqa: E402  the same anchor and bands as before

FW, FH, N, RAMP = 208, 101, 12, 24


def pin(s):
    frames = [s[:, k * FW:(k + 1) * FW] for k in range(N)]
    base = int(np.median([pad(f) for f in frames]))
    xs = np.arange(FW)
    share_x = np.clip((xs - (int(FW * X0) - RAMP)) / (2 * RAMP), 0, 1)   # 0 on the driver's side, 1 on the horse's
    body, legs = int(FH * BODY), int(FH * LEGS)
    out = np.zeros_like(s)
    for k, f in enumerate(frames):
        d = base - pad(f)
        g = np.zeros_like(f)
        for y in range(FH):
            share = 1.0 if y < body else max(0.0, (legs - y) / (legs - body))
            src = np.rint(y - d * share * share_x).astype(int)          # nearest row: stays crisp pixel art
            ok = (src >= 0) & (src < FH)
            g[y, xs[ok]] = f[src[ok], xs[ok]]
        out[:, k * FW:(k + 1) * FW] = g
    return out, base


if __name__ == "__main__":
    s = np.asarray(Image.open(os.path.join(PIX, "fe12_cycle_raw.png")).convert("RGBA"))
    o, base = pin(s)
    pads = [pad(o[:, k * FW:(k + 1) * FW]) for k in range(N)]
    assert all(abs(p - base) <= 1 for p in pads), pads                     # level at the pad, as before
    Image.fromarray(o).save(os.path.join(PIX, "fe12_cycle.bak-halo.png"))
    print("pad line:", pads)
