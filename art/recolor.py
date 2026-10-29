"""Recolor the grey hero portrait into other coats in code, keeping its painted shading.

The base is a light grey horse on a transparent background, so its alpha is the silhouette and
its brightness is the lighting. A coat is a color multiplied by that lighting, with the base's
own tint (blue rim light, warm glow) added back so the light still reads as the painter's.

    python art/recolor.py          writes art/hero/chestnut_code.png, dapple_code.png, compare.png,
                                   and coats.png: every game coat and marking at card size

The game calls portrait(coat, marking, seed) and gets a cached PNG path. Coordinates below are
in the 1024px base's space and scale to whatever size is rendered.
"""
import os
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hero")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
COAT_L = 175.0   # brightness of a lit patch of the grey coat: maps to the target color itself
BASE = "hero_b.png"
_base = {}

def load(name):
    return np.asarray(Image.open(os.path.join(HERE, name)).convert("RGBA")).astype(np.float32)


def grid(shape):
    """Pixel coordinates in the 1024px base's space, whatever size we render at."""
    k = 1024 / shape[0]
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)
    return yy * k, xx * k


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def tint(rgb, lum, color):
    """A flat color lit by the base's brightness: darker below the coat's lit level,
    rising toward white in the highlights."""
    s = (lum / COAT_L)[..., None]
    c = np.array(color, np.float32)
    lit = c * np.minimum(s, 1) ** 1.25 + (255 - c) * np.clip(s - 1, 0, 1) * 0.9
    chroma = rgb - lum[..., None]                     # the painter's colored light, kept
    return lit + chroma


def masks(img):
    rgb, alpha = img[..., :3], img[..., 3] / 255
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    inside = smooth(alpha, 0.5, 0.95)
    coat = inside * smooth(lum, 22, 60)               # near-black leather, pupil and nostrils stay as painted
    return rgb, alpha, lum, coat


def dapples(shape, seed=412, n=170, r=(16, 30)):
    """Light rounds with a darker net between them, laid out from the pattern number."""
    g = np.random.default_rng(seed)
    pts = g.uniform([330, 300], [900, 1000], (n, 2))
    rad = g.uniform(*r, n)
    yy, xx = grid(shape)
    best = np.full(shape, 9.0, np.float32)
    for (x, y), rr in zip(pts, rad):
        best = np.minimum(best, np.hypot(xx - x, yy - y) / rr)
    return 1 - smooth(best, 0.25, 1.15)                # 1 at a dapple's centre, 0 in the net


def compose(img, coat_rgb, coat):
    rgb, alpha = img[..., :3], img[..., 3]
    out = rgb * (1 - coat[..., None]) + coat_rgb * coat[..., None]
    return np.dstack([np.clip(out, 0, 255), alpha]).astype(np.uint8)


def chestnut(img):
    rgb, alpha, lum, coat = masks(img)
    return compose(img, tint(rgb, lum, (136, 68, 40)), coat)   # the darker mane comes out a deep red by itself


def dapple_grey(img, seed=412):
    rgb, alpha, lum, coat = masks(img)
    spots = dapples(lum.shape, seed)
    yy, xx = grid(lum.shape)
    on_body = smooth(xx, 380, 560) * smooth(yy, 260, 420)    # dapples on neck and cheek, none on the face
    dark, light = np.array((92, 96, 104), np.float32), np.array((196, 200, 206), np.float32)
    color = dark + (light - dark) * (0.45 + 0.4 * spots * on_body)[..., None]
    face = 1 - on_body                                       # the face goes paler, as greys do
    color = color * (1 - 0.45 * face[..., None]) + np.array((210, 212, 216), np.float32) * 0.45 * face[..., None]
    s = (lum / COAT_L)[..., None]
    body = color * np.minimum(s, 1.08) + (rgb - lum[..., None])
    return compose(img, body, coat)


def solid_points(img, body, points=(28, 24, 24)):
    """Bay and brown: a body color with black points. The mane is the dark hair of the base;
    the muzzle and ear tips go dark by position on this pose."""
    rgb, alpha, lum, coat = masks(img)
    yy, xx = grid(lum.shape)
    mane = (1 - smooth(lum, 70, 115)) * smooth(xx - 0.25 * yy, 400, 470)   # dark hair on the crest, not throat shadow
    muzzle = 1 - smooth(np.hypot(xx - 215, yy - 700), 90, 190)
    ears = 1 - smooth(yy, 95, 175)
    p = np.maximum.reduce([mane, muzzle * 0.85, ears * 0.9])[..., None]
    c = tint(rgb, lum, body) * (1 - p) + tint(rgb, lum, points) * p
    return compose(img, c, coat)


def black(img):
    rgb, alpha, lum, coat = masks(img)
    return compose(img, tint(rgb, lum, (64, 60, 64)), coat)


def mark(img, out, marking):
    """White face markings, painted under the base's lighting and kept off the bridle."""
    if marking == "none":
        return out
    rgb, alpha, lum, coat = masks(img)
    yy, xx = grid(lum.shape)
    if marking == "star":
        m = 1 - smooth(np.hypot(xx - 372, yy - 318), 18, 30)
    elif marking == "snip":
        m = 1 - smooth(np.hypot((xx - 196) * 1.3, yy - 668), 14, 26)
    else:                                                # blaze: a stripe from forehead to nose, widening
        ax, ay, bx, by = 388, 300, 222, 640
        t = np.clip(((xx - ax) * (bx - ax) + (yy - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2), 0, 1)
        d = np.hypot(xx - (ax + t * (bx - ax)), yy - (ay + t * (by - ay)))
        w = 9 + 14 * t
        m = 1 - smooth(d - w, -4, 6)
    m = (m * smooth(lum, 45, 80))[..., None]             # leather and nostrils stay as painted
    white = tint(rgb, lum * 1.05, (232, 230, 226))
    o = out.astype(np.float32)
    o[..., :3] = o[..., :3] * (1 - m) + white * m
    return np.clip(o, 0, 255).astype(np.uint8)


COATS = {"chestnut": chestnut, "black": black, "grey": dapple_grey,
         "bay": lambda img: solid_points(img, (128, 64, 32)),
         "brown": lambda img: solid_points(img, (78, 46, 30))}


def portrait(coat, marking="none", seed=0, size=512):
    """Path to the cached PNG for this look. Only greys carry their pattern number in the key;
    a solid coat with the same marking is the same picture."""
    key = f"{coat}_{marking}" + (f"_{seed % 1000}" if coat == "grey" else "") + f"_{size}.png"
    path = os.path.join(CACHE, key)
    if not os.path.exists(path):
        if size not in _base:
            im = Image.open(os.path.join(HERE, BASE)).convert("RGBA").resize((size, size), Image.LANCZOS)
            _base[size] = np.asarray(im).astype(np.float32)
        img = _base[size]
        out = dapple_grey(img, seed % 1000) if coat == "grey" else COATS.get(coat, chestnut)(img)
        os.makedirs(CACHE, exist_ok=True)
        Image.fromarray(mark(img, out, marking)).save(path + ".tmp", "PNG")
        os.replace(path + ".tmp", path)                  # a half-written file is never served
    return path


def sheet(tiles, out):
    """Each coat at card size (240) with its barn-row size (64) under it, on the dark theme."""
    W, pad = 240, 16
    im = Image.new("RGB", (pad + len(tiles) * (W + pad), pad + W + 8 + 64 + 30), (17, 20, 26))
    d = ImageDraw.Draw(im)
    for i, (label, t) in enumerate(tiles):
        x = pad + i * (W + pad)
        big = t.resize((W, W), Image.LANCZOS)
        im.paste(big, (x, pad), big)
        small = t.resize((64, 64), Image.LANCZOS)
        im.paste(small, (x, pad + W + 8), small)
        d.text((x + 72, pad + W + 30), label, fill=(225, 228, 233))
    im.save(out)


if __name__ == "__main__":
    base = load("hero_b.png")
    ch, dg = chestnut(base), dapple_grey(base)
    assert ch.shape == base.shape and (ch[..., 3] == base[..., 3]).all(), "recolor never moves the silhouette"
    Image.fromarray(ch).save(os.path.join(HERE, "chestnut_code.png"))
    Image.fromarray(dg).save(os.path.join(HERE, "dapple_code.png"))
    tiles = [(n, Image.open(os.path.join(HERE, f)).convert("RGBA")) for n, f in
             (("grey base", "hero_b.png"), ("bay (SpriteCook)", "bay.png"),
              ("chestnut (code)", "chestnut_code.png"), ("dapple grey (code)", "dapple_code.png"))]
    sheet(tiles, os.path.join(HERE, "compare.png"))
    a, b = portrait("grey", "none", 7), portrait("grey", "none", 8)
    assert open(a, "rb").read() != open(b, "rb").read(), "two pattern numbers, two different greys"
    assert portrait("bay", "star", 7) == portrait("bay", "star", 8), "a solid coat ignores the pattern number"
    tiles = [(f"{c} {m}", Image.open(portrait(c, m, 412))) for c in COATS for m in ("none", "blaze")]
    sheet(tiles[:5], os.path.join(HERE, "coats.png"))
    sheet(tiles[5:], os.path.join(HERE, "coats_marked.png"))
    print("wrote chestnut_code.png, dapple_code.png, compare.png, coats.png, coats_marked.png")
