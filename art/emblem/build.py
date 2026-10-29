"""Turn the raw ComfyUI emblem parts (art/emblem/raw) into the game's pixel parts (mockups/brand/emblem/parts):
shape_<k>.png: the badge at 32x32 with its gold rim, field pixels kept gray (the game tints them with color 1);
dev_<k>.png: the device at 18x18, white and gray (tinted with color 2). python art/emblem/build.py"""
import glob, os
from PIL import Image

OUT = "mockups/brand/emblem/parts"


def key(im):
    """Magenta background out; the subject cropped square."""
    im = im.convert("RGBA")
    px = [(0, 0, 0, 0) if (r > 120 and b > 100 and g < 110 and r - g > 70 and b - g > 50) else (r, g, b, 255) for r, g, b, _ in im.getdata()]
    im.putdata(px)
    x0, y0, x1, y1 = im.getbbox()
    side = max(x1 - x0, y1 - y0)
    sq = Image.new("RGBA", (side, side))
    sq.paste(im.crop((x0, y0, x1, y1)), ((side - (x1 - x0)) // 2, (side - (y1 - y0)) // 2))
    return sq


def shrink(im, n):
    """Down to an n-pixel grid: average each cell, then hard alpha and a small palette, so it reads as real pixel art."""
    sm = im.resize((n, n), Image.BOX)
    rgb = sm.convert("RGB").quantize(24, method=Image.Quantize.MEDIANCUT).convert("RGB")
    a = sm.getchannel("A").point(lambda v: 255 if v > 110 else 0)
    rgb.putalpha(a)
    return rgb


os.makedirs(OUT, exist_ok=True)
for f in sorted(glob.glob("art/emblem/raw/*.png")):
    name = os.path.basename(f)
    n = 32 if name.startswith("shape_") else 18
    shrink(key(Image.open(f)), n).save(os.path.join(OUT, name))
    print(name)
