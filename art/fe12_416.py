"""The replay runner at twice the old sheet's size (416x202 frames, 2/3 of SpriteCook's frame-engine output), rebuilt from
the raw frames (mockups/pixel/fe12_raw.webp). The old 208-wide sheet kept one pixel of every 3x3 (nearest), which broke the
reins and shafts into steps and speckled the coat; this one resamples in linear light (Lanczos, premultiplied alpha).
Same crop box as fe_prep.py, exactly twice its size, so the 208-wide gear overlays line up when scaled 2x; then pinned level
at the saddle pad (as fe12_pin_blend.py), the cut-out fringe outlined (dehalo_runner.py), and laid out 6 across, 2 down
(a 12-across row at this size is wider than some phones' textures allow).

  python art/fe12_416.py   -> mockups/pixel/fe12_cycle416.png
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIX = os.path.join(ROOT, "mockups", "pixel")
sys.path.insert(0, PIX); sys.path.insert(0, os.path.join(ROOT, "art"))
from fix_pace import pad, X0, BODY, LEGS                                   # noqa: E402  the same anchor and bands as the old sheet
from dehalo_runner import dehalo                                            # noqa: E402

N, COLS, S = 12, 6, 2                                                       # frames, frames per row, scale over the 208 sheet


def lin_resize(im, w, h):
    """Resize in linear light with premultiplied alpha, so edges don't pick up dark or light fringes."""
    a = np.asarray(im).astype(np.float32) / 255
    lin = np.where(a[..., :3] <= .04045, a[..., :3] / 12.92, ((a[..., :3] + .055) / 1.055) ** 2.4) * a[..., 3:4]
    ch = [np.asarray(Image.fromarray(c).resize((w, h), Image.LANCZOS)) for c in (lin[..., 0], lin[..., 1], lin[..., 2], a[..., 3])]
    al = np.clip(ch[3], 0, 1)
    rgb = np.clip(np.stack(ch[:3], -1) / np.maximum(al[..., None], 1e-4), 0, 1)
    rgb = np.where(rgb <= .0031308, rgb * 12.92, 1.055 * rgb ** (1 / 2.4) - .055)
    out = np.dstack([rgb, al]) * 255 + .5
    out[..., 3] = np.where(out[..., 3] >= 128, 255, 0)                      # hard alpha: the replay's cards cut at .5 anyway
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def pin(frames, fw, fh, ramp):
    """fe12_pin_blend.pin at any size: each frame's body moved to the median pad line, blended across the driver seam."""
    base = int(np.median([pad(f) for f in frames]))
    xs = np.arange(fw)
    share_x = np.clip((xs - (int(fw * X0) - ramp)) / (2 * ramp), 0, 1)
    body, legs = int(fh * BODY), int(fh * LEGS)
    out = []
    for f in frames:
        d = base - pad(f)
        g = np.zeros_like(f)
        for y in range(fh):
            share = 1.0 if y < body else max(0.0, (legs - y) / (legs - body))
            src = np.rint(y - d * share * share_x).astype(int)
            ok = (src >= 0) & (src < fh)
            g[y, xs[ok]] = f[src[ok], xs[ok]]
        out.append(g)
    return out, base


if __name__ == "__main__":
    raw = Image.open(os.path.join(PIX, "fe12_raw.webp")).convert("RGBA")
    fw0 = raw.width // N
    fr = [raw.crop((i * fw0, 0, (i + 1) * fw0, raw.height)) for i in range(N)]
    bb = [f.getchannel("A").point(lambda a: 255 if a > 40 else 0).getbbox() for f in fr]
    x0, y0 = min(b[0] for b in bb), min(b[1] for b in bb); x1, y1 = max(b[2] for b in bb), max(b[3] for b in bb)
    W1 = round((x1 - x0) * 242 / 726); H1 = round((y1 - y0) * W1 / (x1 - x0))
    assert (W1, H1) == (208, 101), (W1, H1)                                  # the old sheet's box, so overlays line up at 2x
    FW, FH = W1 * S, H1 * S
    frames = [np.asarray(lin_resize(f.crop((x0, y0, x1, y1)), FW, FH)) for f in fr]
    frames, base = pin(frames, FW, FH, 24 * S)
    pads = [pad(f) for f in frames]
    assert all(abs(p - base) <= 1 for p in pads), pads                      # level at the pad
    sheet = Image.new("RGBA", (FW * COLS, FH * (N // COLS)))
    for k, f in enumerate(frames):
        sheet.paste(Image.fromarray(f), ((k % COLS) * FW, (k // COLS) * FH))
    sheet, n = dehalo(sheet, band=S + 1, inner=3 * S)
    sheet.save(os.path.join(PIX, "fe12_cycle416.png"), optimize=True)
    print(f"{FW}x{FH} frames, {COLS}x{N // COLS} sheet {sheet.size}, pad line {base}, {n} fringe pixels outlined")
