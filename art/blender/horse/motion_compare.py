# python motion_compare.py : fe12_cycle (left) and the 3D model's 12 frames (right, frames/fNN.png) at the replay's
# close size (horse ~92 px), both pinned and standing on race_b's ground, nearest-upscaled x4 on the night sky.
# Writes stride_24fps.gif (the replay's 24 poses/s), stride_8fps.gif (slowed for inspection) and stride_strip.png.
from PIL import Image
UP = 4
cyc = Image.open("../../../mockups/pixel/fe12_cycle.png").convert("RGBA")
N = Image.open("frames/f00.png").width; s = N / 242; k = s * 242 / 207            # same scales as pixel_test.py
top, bot = round(N * .22), round(N * .78)
def tile(im, ground=False):
    t = Image.new("RGBA", (N, N), (11, 20, 48, 255))
    t.alpha_composite(im, ((N - im.width) // 2, round(178 * s) - im.height) if ground else (0, 0))
    return t.crop((0, top, N, bot))
pairs = []
for i in range(12):
    f = cyc.crop((i * 208, 0, i * 208 + 208, 101)).resize((round(208 * k), round(101 * k)), Image.BOX)
    a, b = tile(f, True), tile(Image.open(f"frames/f{i:02d}.png").convert("RGBA"))
    p = Image.new("RGBA", (2 * N + 6, bot - top), (5, 7, 13, 255)); p.paste(a, (0, 0)); p.paste(b, (N + 6, 0))
    pairs.append(p.resize((p.width * UP, p.height * UP), Image.NEAREST).convert("P", palette=Image.ADAPTIVE, colors=255))
for name, ms in (("stride_24fps.gif", 40), ("stride_8fps.gif", 125)):
    pairs[0].save(name, save_all=True, append_images=pairs[1:], duration=ms, loop=0, disposal=1)
strip = Image.new("RGB", (12 * (2 * N + 6) * 2 // 2, (bot - top) * 2), (5, 7, 13))
for i in range(12):
    model = tile(Image.open(f"frames/f{i:02d}.png").convert("RGBA"))
    f = cyc.crop((i * 208, 0, i * 208 + 208, 101)).resize((round(208 * k), round(101 * k)), Image.BOX)
    strip.paste(tile(f, True).convert("RGB"), (i * N, 0)); strip.paste(model.convert("RGB"), (i * N, bot - top))
strip = strip.crop((0, 0, 12 * N, strip.height)); strip.resize((strip.width * 2, strip.height * 2), Image.NEAREST).save("stride_strip.png")
print("ok", N)
