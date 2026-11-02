"""The part map for the replay runner (mockups/pixel/fe12_cycle.png): a sheet the same size where every pixel is a flat
code color saying which part of the rig it belongs to, so the replay recolors by part instead of guessing from color
(the guess "anything blue is the driver's silks" is what dyed the bridle under a mask and flickered it in trim color).

The runner faces right with the driver and sulky on the left of each 208x101 cell, so position settles most of it:
blue left of the horse is silks (its top is the helmet trim) or, low down, the wheel; blue over the horse is tack.
The white pad is found as the side stride's pad always was (light, grey, a solid block over the back).

  python art/part_map.py        -> mockups/pixel/fe12_parts.png  (classified from the art before the outline pass)
"""
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "mockups", "pixel", "fe12_cycle.bak-halo.png")    # the original colors; same pixels as the shipped sheet
SHIP = os.path.join(ROOT, "mockups", "pixel", "fe12_cycle.png")
OUT = os.path.join(ROOT, "mockups", "pixel", "fe12_parts.png")
FW, FH = 208, 101
DRIVER_X = 64                          # left of it: driver and sulky

PARTS = {                              # part -> code color in the map (the replay reads these exact values)
    "coat": (200, 60, 60), "tack": (60, 200, 60), "silks": (60, 60, 220), "trim": (120, 200, 255),
    "wheel": (90, 90, 90), "pad": (255, 255, 255), "driver": (255, 200, 120), "sulky": (40, 40, 40),
}


def pad_pixels(f):
    """The saddle pad in one cell: light grey pixels in the box over the back, in pieces of 12 or more (no buckle glints)."""
    rgb = f[..., :3].astype(int)
    l, sat = rgb.mean(-1), rgb.max(-1) - rgb.min(-1)
    m = np.zeros(f.shape[:2], bool)
    m[20:55, 95:135] = (f[20:55, 95:135, 3] > 0) & (l[20:55, 95:135] > 150) & (sat[20:55, 95:135] < 40)
    keep, seen = np.zeros_like(m), np.zeros_like(m)
    for y, x in zip(*np.nonzero(m)):
        if seen[y, x]:
            continue
        part, st = [(y, x)], [(y, x)]
        seen[y, x] = True
        while st:
            cy, cx = st.pop()
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < FH and 0 <= nx < FW and m[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True; part.append((ny, nx)); st.append((ny, nx))
        if len(part) >= 12:
            for p in part:
                keep[p] = True
    return keep


def classify(f):
    rgb = f[..., :3].astype(int)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    solid = f[..., 3] > 0
    l = rgb.mean(-1)
    blue = solid & (b > r + 40) & (b > g + 20)
    ys, xs = np.mgrid[:FH, :FW]
    left = xs < DRIVER_X
    # the wheel: a disc, fitted to the blue below the seat (spokes and hub), so a tail or hind leg beside it stays horse
    wb = blue & left & (ys >= 58)
    cy, cx = ys[wb].mean(), xs[wb].mean()
    rad = max(ys[wb].max() - cy, cx - xs[wb].min()) + 1.5
    wheel = solid & ((ys - cy) ** 2 + (xs - cx) ** 2 <= rad * rad)
    # the silks are a body, the shafts and reins are lines: what survives a 3x3 opening of the driver's blue is silks
    sbl = blue & left & ~wheel
    er = np.ones_like(sbl)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            er &= np.roll(np.roll(sbl, dy, 0), dx, 1)
    body = np.zeros_like(sbl)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            body |= np.roll(np.roll(er, dy, 0), dx, 1)
    body &= sbl
    out = np.full(f.shape[:2], "", object)
    out[solid] = "coat"
    out[solid & left] = "driver"
    out[solid & left & (l < 60)] = "sulky"                                   # seat, boots, tire: dark, never recolored
    out[solid & left & (l < 75) & (xs >= 40) & (ys < 50) & (np.abs(r - b) < 25)] = "coat"   # the tail streaming back past the driver
    dist = np.sqrt((ys - cy) ** 2 + (xs - cx) ** 2)
    wheelpix = wheel & (blue | (np.abs(dist - rad) < 3) | (dist < 3.5))    # spokes, rim and tire, hub: what's really wheel in the disc
    out[wheelpix] = "wheel"
    # the far hind leg reaches back past the wheel: grow the coat into the low part of the driver's side from the horse,
    # through anything that isn't blue or wheel (a leg in front of the wheel stays leg, a sock stays leg)
    grow = solid & left & (ys >= 55) & ~blue & ~wheelpix & (dist > rad + 3)   # never into the tire's outer edge
    seed = (out == "coat") & ~left
    st = list(zip(*np.nonzero(seed & np.roll(grow, 1, 1))))
    while st:
        y, x = st.pop()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < FH and 0 <= nx < FW and grow[ny, nx] and out[ny, nx] != "coat":
                out[ny, nx] = "coat"; st.append((ny, nx))
    out[wheel & ~wheelpix & (out != "coat")] = "sulky"                     # the rest of the disc: shadow between the spokes
    out[blue & ~left & (ys < 70)] = "tack"                                    # blue down at the hooves is shine on the hoof, not a strap
    out[sbl & ~body] = "tack"                                                # shafts and reins at the driver's end
    out[solid & ~left & (l < 75) & (b > r + 8) & (ys < 65)] = "tack"          # the navy-black girth and straps (never down at the hooves)
    sb = keep_big(body, 30)                                                   # the driver's body and legs: sizable pieces; a small blob is a shaft or rein thickening by the hands
    out[body & ~sb] = "tack"
    out[sb] = "silks"
    if sb.any():
        wide = np.nonzero((blue & left & ~wheel).sum(1) >= 8)[0]               # the shoulders: the first row the silks run wide
        out[blue & left & ~wheel & (ys < wide.min())] = "trim"               # above them, the helmet's stripe and visor                      # the helmet's stripe and visor: blue at helmet height, thin or not
    out[pad_pixels(f)] = "pad"
    for comp in pieces(out == "tack"):                                       # specks of "tack" on a dark leg: too small to be a strap
        if len(comp) < 12:
            for q in comp:
                out[q] = "coat"
    return out


def pieces(m):
    """The 4-connected pieces of a mask, as lists of (y, x)."""
    seen, out = np.zeros_like(m), []
    for y, x in zip(*np.nonzero(m)):
        if seen[y, x]:
            continue
        part, st = [(y, x)], [(y, x)]
        seen[y, x] = True
        while st:
            cy, cx = st.pop()
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < m.shape[0] and 0 <= nx < m.shape[1] and m[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True; part.append((ny, nx)); st.append((ny, nx))
        out.append(part)
    return out


def keep_big(m, n):
    k = np.zeros_like(m)
    for p in pieces(m):
        if len(p) >= n:
            for q in p:
                k[q] = True
    return k


def build(src=SRC):
    a = np.asarray(Image.open(src).convert("RGBA"))
    n = a.shape[1] // FW
    m = np.zeros((FH, FW * n, 4), np.uint8)
    for k in range(n):
        lab = classify(a[:, k * FW:(k + 1) * FW])
        for name, col in PARTS.items():
            sel = lab == name
            m[:, k * FW:(k + 1) * FW][sel] = (*col, 255)
    return m


if __name__ == "__main__":
    m = build()
    ship = np.asarray(Image.open(SHIP).convert("RGBA"))
    assert ((m[..., 3] > 0) == (ship[..., 3] > 0)).all(), "every visible pixel of the runner has a part, and nothing else"
    Image.fromarray(m).save(OUT)
    print("parts:", {k: int((m[..., :3] == v).all(-1).sum()) for k, v in PARTS.items()}, "->", OUT)
