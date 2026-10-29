"""Pixel emblems: a badge (metal rim + field) and a device, recolored for each barn and cached as small PNGs.
Parts are SpriteCook pixel art (mockups/brand/emblem/parts: 64px badges, 40px devices, gray where the barn's color goes).
The rim's metal follows the barn's Prestige: iron, then silver from IV, gold from VII."""
import colorsys, hashlib, os
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(ROOT, "mockups", "brand", "emblem", "parts")
CACHE = os.path.join(ROOT, "mockups", "brand", "emblem", "cache")
TROPHIES = os.path.join(ROOT, "mockups", "brand", "trophies")
TROPHY_FILE = {"cup": "cup", "laurel": "horseshoe", "crown": "crown", "clock": "clock", "money": "money", "medal": "medal",
               "plaque": "plaque", "star": "star", "ribbon": "ribbon"}
DEV = 32                                                     # the device's size on the 64px badge
OUT = 128                                                    # stored at 2x; the browser scales it down smoothly, so it stays sharp on phone screens


def _hex(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def _gray(r, g, b):
    return max(r, g, b) - min(r, g, b) < 34                 # the field and device are drawn in grays; the rim is gold


def _lum(r, g, b):
    return (r * 299 + g * 587 + b * 114) / 255000


def _tint(lum, col):
    """A gray pixel recolored: the color at mid-gray, lighter in the highlights, darker in the shade."""
    k = lum / 0.72
    return tuple(max(0, min(255, round(v * k if k <= 1 else v + (255 - v) * (k - 1) * 1.6))) for v in col)


def _metal(r, g, b, rim):
    if rim == "gold":
        return r, g, b
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if rim == "silver":
        r2, g2, b2 = colorsys.hls_to_rgb(0.6, min(1, l * 1.12), 0.1)
    else:                                                    # iron: dark, a little warm
        r2, g2, b2 = colorsys.hls_to_rgb(0.07, l * 0.55, 0.14)
    return round(r2 * 255), round(g2 * 255), round(b2 * 255)


def _badge(em, rim):
    """The 64px emblem: field tinted color 1, rim in its metal, the device (color 2) centered on the field."""
    c1, c2 = _hex(em["c1"]), _hex(em["c2"])
    badge = Image.open(os.path.join(PARTS, f"shape_{em['shape']}.png")).convert("RGBA")
    out, field = [], []
    for i, (r, g, b, a) in enumerate(badge.getdata()):
        if not a:
            out.append((0, 0, 0, 0))
        elif _gray(r, g, b) and _lum(r, g, b) > 0.35:
            out.append((*_tint(_lum(r, g, b), c1), 255))
            field.append(divmod(i, badge.width))
        else:
            out.append((*_metal(r, g, b, rim), 255))
    badge.putdata(out)
    dev_name = f"letter_{em.get('letter') or 'A'}" if em["dev"] == "letter" else em["dev"]
    dp = os.path.join(PARTS, f"dev_{dev_name}.png")
    if os.path.exists(dp):
        dev = Image.open(dp).convert("RGBA")
        dev.putdata([(*_tint(_lum(r, g, b), c2), a) if a and _gray(r, g, b) and _lum(r, g, b) > 0.3 else (r, g, b, a)
                     for r, g, b, a in dev.getdata()])
    else:                                                    # a trophy device: its own art, not recolored
        dev = Image.open(os.path.join(TROPHIES, f"{TROPHY_FILE.get(em['dev'], 'cup')}.png")).convert("RGBA")
    dev = dev.crop(dev.getbbox())
    # everything at 2x: the pixel-art badge doubles exactly; the device scales smoothly (trophy art isn't on a 2x grid)
    badge = badge.resize((OUT, OUT), Image.NEAREST)
    k = 2 * DEV / max(dev.size)
    dev = dev.resize((max(1, round(dev.width * k)), max(1, round(dev.height * k))), Image.LANCZOS)
    cy = 2 * sum(y for y, _ in field) / len(field) if field else OUT / 2
    cx = 2 * sum(x for _, x in field) / len(field) if field else OUT / 2
    badge.alpha_composite(dev, (round(cx - dev.width / 2), round(cy - dev.height / 2)))
    return badge


def render(em, rim="gold"):
    """The emblem's PNG (one 128px image for every size shown), built once and cached; returns its path under /mock."""
    key = f"{em['shape']}|{em['c1']}|{em['c2']}|{em['dev']}{em.get('letter', '') if em['dev'] == 'letter' else ''}|{rim}|sc2"
    name = hashlib.md5(key.encode()).hexdigest()[:12] + ".png"
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        _badge(em, rim).save(path)
    return "/mock/brand/emblem/cache/" + name


# ---- silks: every barn's stock colors, a pixel racing jacket in its two colors (the emblem builder is a paid license)
PATTERNS = ["plain", "hoops", "sash", "quartered", "chevron", "stars"]
_JACKET = [(8, 6), (13, 3), (19, 3), (24, 6), (31, 11), (28, 17), (24, 14), (24, 29), (8, 29), (8, 14), (4, 17), (1, 11)]   # a 32px grid


def _silks(sk):
    from PIL import ImageDraw, ImageChops
    c1, c2 = _hex(sk["c1"]), _hex(sk["c2"])
    pat = Image.new("RGBA", (32, 32), (*c1, 255))
    d = ImageDraw.Draw(pat)
    p = sk.get("pat", "plain")
    if p == "plain":
        d.rectangle((0, 27, 31, 31), fill=c2); d.rectangle((0, 0, 7, 31), fill=c2); d.rectangle((25, 0, 31, 31), fill=c2)   # trim on the sleeves and hem
    elif p == "hoops":
        for y in (10, 16, 22):
            d.rectangle((0, y, 31, y + 2), fill=c2)
    elif p == "sash":
        d.polygon([(7, 3), (13, 3), (27, 29), (21, 29)], fill=c2)
    elif p == "quartered":
        d.rectangle((16, 0, 31, 15), fill=c2); d.rectangle((0, 16, 15, 31), fill=c2)
    elif p == "chevron":
        d.polygon([(0, 13), (16, 22), (31, 13), (31, 18), (16, 27), (0, 18)], fill=c2)
    elif p == "stars":
        for x, y in ((12, 11), (19, 11), (16, 17), (12, 23), (19, 23)):
            d.polygon([(x, y - 2), (x + 1, y), (x + 2, y), (x, y + 2), (x - 2, y), (x - 1, y)], fill=c2)
    mask = Image.new("L", (32, 32), 0)
    ImageDraw.Draw(mask).polygon(_JACKET, fill=255)
    out = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    out.paste(pat, (0, 0), mask)
    shade = Image.new("L", (32, 32), 0)                               # the sleeves a shade darker, for shape
    ImageDraw.Draw(shade).polygon([(8, 14), (4, 17), (1, 11), (8, 6)], fill=90)
    ImageDraw.Draw(shade).polygon([(24, 14), (28, 17), (31, 11), (24, 6)], fill=90)
    out.paste(Image.new("RGBA", (32, 32), (0, 0, 0, 255)), (0, 0), ImageChops.multiply(shade, mask))
    ImageDraw.Draw(out).line(_JACKET + _JACKET[:1], fill=(5, 7, 13, 255), width=1)
    ImageDraw.Draw(out).line([(13, 3), (16, 7), (19, 3)], fill=(5, 7, 13, 255), width=1)   # the V of the collar
    return out.resize((OUT, OUT), Image.NEAREST)


def render_silks(sk):
    """The silks' PNG, cached like the emblems; returns its path under /mock."""
    key = f"silks|{sk.get('pat', 'plain')}|{sk['c1']}|{sk['c2']}|s1"
    name = hashlib.md5(key.encode()).hexdigest()[:12] + ".png"
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        _silks(sk).save(path)
    return "/mock/brand/emblem/cache/" + name
