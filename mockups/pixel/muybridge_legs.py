"""Real pacing legs from Muybridge's 1887 plate 594 ("Pronto" pacing, harnessed to sulky; public
domain). Each photo frame's legs are cut out below the belly, scaled to our sprite, pixelated,
colored as a bay (brown upper legs shaded by the photo, black lower legs) and drawn under the
leg-free body SpriteCook made. The body never moves; only the photographed legs do.

    python mockups/pixel/muybridge_legs.py          -> mockups/pixel/mb_cycle.png (+ mb_preview.png)
"""
import os
import numpy as np
from PIL import Image, ImageOps, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "..", "..", "art", "reference")
FRAMES = [2, 3, 4, 5, 6, 7]            # one stride; frame 1 is clipped and 7 repeats 1's pose a stride later
# photo geometry (317x236 crops): the belly line, the track, the front of the chest
P_BELLY, P_GROUND, P_X0 = 128, 224, 105          # X0 keeps the driver's boots out of the leg crop
# our body sprite: ground line, where the chest front sits, and the belly it hides the leg tops under
S_GROUND, S_CHEST_X, SCALE = 108, 205, 0.55
DARK = 140                             # photo value below which it's horse (blurred lower legs are pale)


def chest_x(a):
    """Muybridge's cameras fired as the horse tripped wires at equal spacings, so the horse sits in
    nearly the same place in every frame: a fixed alignment is steadier than finding the chest,
    which the forward-reaching foreleg confuses."""
    return 270


def drop_thin(m, n=2):
    """Clear horizontal runs of n pixels or fewer: background grid lines and rim arcs, not legs."""
    out = m.copy()
    for y in range(m.shape[0]):
        row = m[y]; x = 0
        while x < len(row):
            if row[x]:
                e = x
                while e < len(row) and row[e]: e += 1
                if e - x <= n: out[y, x:e] = False
                x = e
            else:
                x += 1
    return out


def attached(m):
    """Keep only the blobs that hang from the belly line (the top row of the crop): legs do,
    track-line smudges and dust don't."""
    h, w = m.shape
    keep = np.zeros_like(m); stack = [(P_BELLY, x) for x in range(w) if m[P_BELLY, x]]
    while stack:
        y, x = stack.pop()
        if y < 0 or y >= h or x < 0 or x >= w or keep[y, x] or not m[y, x]:
            continue
        keep[y, x] = True
        stack += [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]
    return keep


def legs_from(frame):
    im = ImageOps.autocontrast(Image.open(os.path.join(REF, f"pronto_{frame:02d}.png")).convert("L"), cutoff=2)
    a = np.asarray(im).astype(np.float32)
    m = drop_thin(a < DARK)
    m[:P_BELLY] = False; m[:, :P_X0] = False; m[P_GROUND + 1:] = False
    m = attached(m)
    # the cannons are only 3-4 photo pixels wide: fatten everything by one so they survive the scale-down
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))) > 0
    cx = chest_x(a)
    return a, m, cx


def render(frame, body):
    a, m, cx = legs_from(frame)
    h, w = m.shape
    # scale to the sprite: box-filter the mask and colors, then threshold so the pixels stay crisp
    sw, sh = round(w * SCALE), round(h * SCALE)
    mk = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((sw, sh), Image.BOX)) > 100
    gy = round(P_GROUND * SCALE)
    for y in range(gy - 2, sh):                                                   # along the track line, a hoof is short: clear longer smears
        row = mk[y]; x = 0
        while x < sw:
            if row[x]:
                e = x
                while e < sw and row[e]: e += 1
                if e - x > 7: mk[y, x:e] = False
                x = e
            else:
                x += 1
    lum = np.asarray(Image.fromarray(a.astype(np.uint8)).resize((sw, sh), Image.BOX)).astype(np.float32)
    out = np.zeros((sh, sw, 4), np.uint8)
    ys, xs = np.nonzero(mk)
    for y, x in zip(ys, xs):
        depth = (y - P_BELLY * SCALE) / ((P_GROUND - P_BELLY) * SCALE)          # 0 at the belly, 1 at the ground
        t = np.clip((lum[y, x] - 20) / 90, 0, 1)                                  # the photo's own shading
        if depth < .55:
            col = (int(96 + 60 * t), int(44 + 34 * t), int(20 + 18 * t))            # bay upper leg
        elif depth < .94:
            col = (int(34 + 26 * t), int(28 + 18 * t), int(26 + 16 * t))            # black points
        else:
            col = (14, 10, 8)                                                     # hoof
        out[y, x] = (*col, 255)
    # a one-pixel dark outline, like the rest of the sprite
    dil = np.asarray(Image.fromarray((mk * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))) > 0
    edge = dil & ~mk
    out[edge] = (34, 16, 8, 255)
    # place: photo ground -> sprite ground, photo chest -> sprite chest
    ox = S_CHEST_X - round(cx * SCALE); oy = S_GROUND - round(P_GROUND * SCALE)
    canvas = Image.new("RGBA", body.size, (0, 0, 0, 0))
    canvas.alpha_composite(Image.fromarray(out), (ox, oy))
    canvas.alpha_composite(body)
    return canvas


def main():
    body = Image.open(os.path.join(HERE, "race_body.png")).convert("RGBA")
    frames = [render(f, body) for f in FRAMES]
    w, h = body.size
    sheet = Image.new("RGBA", (w * len(frames), h))
    for i, f in enumerate(frames):
        sheet.paste(f, (i * w, 0))
    sheet.save(os.path.join(HERE, "mb_cycle.png"))
    prev = Image.new("RGBA", (w * 3 * 3, h * 3 * 2), (122, 86, 58, 255))   # on the dirt, where it will live
    for i, f in enumerate(frames):
        prev.alpha_composite(f.resize((w * 3, h * 3), Image.NEAREST), ((i % 3) * w * 3, (i // 3) * h * 3))
    prev.convert("RGB").save(os.path.join(HERE, "mb_preview.png"))
    print("frames", len(frames), "size", w, h)


if __name__ == "__main__":
    main()
