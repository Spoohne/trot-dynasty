"""SpriteCook badge parts: turn every pixel that isn't the gold rim (or the dark outline) to gray, so the game can tint the field.
python art/emblem/prep_sc.py"""
import colorsys, glob
from PIL import Image

for f in glob.glob("mockups/brand/emblem/parts/shape_*.png"):
    im = Image.open(f).convert("RGBA")
    px = []
    for r, g, b, a in im.getdata():
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        gold = 0.05 < h < 0.18 and s > 0.45 and l > 0.25
        v = round(l * 255)
        px.append((r, g, b, a) if not a or gold or l < 0.3 else (v, v, v, a))
    im.putdata(px)
    im.save(f)
    print(f)
