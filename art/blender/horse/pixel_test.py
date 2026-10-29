# python pixel_test.py step2_raw.png : the small model render next to the sprites at the same horse size, every tile
# nearest-upscaled x5 on the night sky. Writes step2_outlined.png (model + 1 px sprite-style outline) and step2_compare.png.
import sys
from PIL import Image, ImageFilter
SRC, UP = sys.argv[1], 5
raw = Image.open(SRC).convert("RGBA"); N = raw.width; s = N / 242            # same framing as race_b, just smaller

# 1 px dark outline round the silhouette, like the SpriteCook sprites
a = raw.getchannel("A").point(lambda v: 255 if v > 127 else 0)
ring = a.filter(ImageFilter.MaxFilter(3))
body = raw.copy(); body.putalpha(a)
out = Image.new("RGBA", raw.size, (0, 0, 0, 0)); out.paste((12, 10, 12, 255), mask=ring); out.alpha_composite(body)
out.save(SRC.replace("_raw", "_outlined"))

race = Image.open("../../../mockups/pixel/race_b.png").convert("RGBA").resize((N, N), Image.BOX)
cyc = Image.open("../../../mockups/pixel/fe12_cycle.png").convert("RGBA").crop((0, 0, 208, 101))
k = s * 242 / 207; cyc = cyc.resize((round(208 * k), round(101 * k)), Image.BOX)   # fe12 frame 0, same horse size
crisp = raw.copy(); crisp.putalpha(a)

tiles = [race, cyc, crisp, out]
TW, TH = N, N
sheet = Image.new("RGBA", (len(tiles) * (TW + 8) - 8, TH), (5, 7, 13, 255))
for i, t in enumerate(tiles):
    tile = Image.new("RGBA", (TW, TH), (11, 20, 48, 255))
    tile.alpha_composite(t, ((TW - t.width) // 2, round(178 * s) - t.height if t is cyc else 0))   # stride frame stood on race_b's ground
    sheet.paste(tile, (i * (TW + 8), 0))
sheet = sheet.crop((0, round(TH * .2), sheet.width, round(TH * .8)))
sheet.resize((sheet.width * UP, sheet.height * UP), Image.NEAREST).convert("RGB").save(SRC.replace("_raw", "_compare"))
print(N, "px frame; tiles: race_b | fe12 frame 0 | model raw | model outlined")
