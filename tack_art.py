"""The Tack Room's horse model: frame 0 of the replay runner with the barn's gear painted on in its two colors.
shortcut: the pieces are pixel masks found on the stock frame (blue tack, wheel geometry, head and leg boxes), not drawn
art; swap each for a SpriteCooked layer sheet when the kit goes into the replay."""
import hashlib, math, os
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
FRAME = os.path.join(ROOT, "mockups", "pixel", "fe12_cycle.png")
CACHE = os.path.join(ROOT, "mockups", "brand", "emblem", "cache")
PIECES = ("harness", "mask", "wraps", "bike")
_frame = []


def frame0():
    if not _frame:
        im = Image.open(FRAME).convert("RGBA")
        _frame.append(im.crop((0, 0, im.width // 12, im.height)))
    return _frame[0]


def rgb(hx):
    return tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5))


def shade(p, base):
    """The stock pixel's light and dark kept, its hue swapped for the barn color."""
    l = (p[0] + p[1] + p[2]) / 3 / 255
    k = 0.55 + l * 0.9
    return tuple(min(255, int(c * k)) for c in base) + (p[3],)


def paint(pieces, cols, c1, c2):
    """pieces: the fitted set; cols: piece -> 'p' | 's' (and 'hub'); c1/c2: the barn's primary and secondary hex."""
    col = lambda k: rgb(c1 if cols.get(k, "p") == "p" else c2)
    im = frame0().copy(); px = im.load(); W, H = im.size
    blue = lambda p: p[3] > 0 and p[2] > p[0] + 40 and p[2] > p[1] + 30
    cx, cy = 27, 82
    for y in range(H):
        for x in range(W):
            p = px[x, y]
            if not blue(p):
                continue
            if x < 60 and y < 58:                                     # the driver: a neutral grey, drivers wear their own silks
                px[x, y] = shade(p, (150, 150, 158))
            elif math.hypot(x - cx, y - cy) <= 19:
                px[x, y] = shade(p, col("bike") if "bike" in pieces else (150, 150, 158))
            else:
                px[x, y] = shade(p, col("harness") if "harness" in pieces else (120, 95, 70))
    if "bike" in pieces:                                              # a solid disc in the bike color, the hub in its own
        for y in range(cy - 19, cy + 20):
            for x in range(cx - 19, cx + 20):
                if 0 <= x < W and 0 <= y < H and px[x, y][3]:
                    d = math.hypot(x - cx, y - cy)
                    if d < 5:
                        px[x, y] = col("hub") + (255,)
                    elif d < 14.5:
                        px[x, y] = shade((120, 120, 120, 255), col("bike"))
                    elif d < 17:
                        px[x, y] = col("bike") + (255,)
    if "mask" in pieces:                                              # over the head, muzzle bare, the ear tips in the other color
        other = rgb(c2 if cols.get("mask", "p") == "p" else c1)
        for y in range(9, 34):
            for x in range(176, 201):
                p = px[x, y]
                if p[3] and ((p[0] > p[1] > p[2] and p[0] > 60) or (sum(p[:3]) < 150 and y < 16)):
                    px[x, y] = other + (255,) if y < 15 else shade(p, col("mask"))
    if "wraps" in pieces:                                             # the front legs, a band in the other color
        other = rgb(c2 if cols.get("wraps", "p") == "p" else c1)
        for x0, x1 in ((128, 146), (186, 201)):
            for y in range(70, 86):
                for x in range(x0, x1):
                    p = px[x, y]
                    if p[3] and sum(p[:3]) < 200:
                        px[x, y] = other + (255,) if 75 <= y <= 76 else shade(p, col("wraps"))
    return im


def render(pieces, cols, c1, c2):
    """The model's PNG at 3x, cached like the emblems; returns its path under /mock."""
    pieces = tuple(p for p in PIECES if p in pieces)
    key = "tack|" + ",".join(pieces) + "|" + ",".join(f"{k}{v}" for k, v in sorted(cols.items())) + f"|{c1}|{c2}|v1"
    name = hashlib.md5(key.encode()).hexdigest()[:12] + ".png"
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        im = paint(pieces, cols, c1, c2)
        im.resize((im.width * 3, im.height * 3), Image.NEAREST).save(path)
    return "/mock/brand/emblem/cache/" + name


if __name__ == "__main__":
    full = render(PIECES, {"bike": "p", "hub": "s"}, "#8e44ad", "#f3f3f3")
    bare = render((), {}, "#8e44ad", "#f3f3f3")
    assert full != bare and os.path.exists(os.path.join(ROOT, full.replace("/mock/", "mockups/")))
    a, b = paint(PIECES, {}, "#8e44ad", "#f3f3f3").load(), paint((), {}, "#8e44ad", "#f3f3f3").load()
    W, H = frame0().size
    assert sum(a[x, y] != b[x, y] for x in range(W) for y in range(H)) > 400, "the kit paints something"
    print("tack art ok")
