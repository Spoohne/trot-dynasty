# python trace_sheets.py : fe12_cycle frames moved into race_b pixel space (wheel-matched: x1.176, wheel corner on
# wheel corner), legs region zoomed x6 with a race_b-pixel grid, two frames per sheet -> trace/legs_AB.png
from PIL import Image, ImageDraw
SC, X0, Y0 = 46 / 39, 95, 98          # race_b wheel 46 px across, fe12's 39; crop origin in race_b px
cyc = Image.open("../../../mockups/pixel/fe12_cycle.png").convert("RGBA")
def to_race(i):
    f = cyc.crop((i * 208, 0, i * 208 + 208, 101))
    f = f.resize((round(208 * SC), round(101 * SC)), Image.NEAREST)
    c = Image.new("RGBA", (260, 242), (20, 26, 40, 255)); c.alpha_composite(f, (round(16 - 14 * SC), round(125 - 55 * SC)))
    return c
def sheet(i, Z=6, W=150, H=80):
    im = to_race(i).crop((X0, Y0, X0 + W, Y0 + H)).resize((W * Z, H * Z), Image.NEAREST); g = ImageDraw.Draw(im)
    for x in range(X0 - X0 % 5 + 5, X0 + W, 5):
        g.line([((x - X0) * Z, 0), ((x - X0) * Z, H * Z)], fill=(90, 200, 255, 90) if x % 10 else (90, 200, 255, 200))
        if x % 10 == 0: g.text(((x - X0) * Z + 2, 2), str(x), fill=(255, 255, 120))
    for y in range(Y0 - Y0 % 5 + 5, Y0 + H, 5):
        g.line([(0, (y - Y0) * Z), (W * Z, (y - Y0) * Z)], fill=(90, 200, 255, 90) if y % 10 else (90, 200, 255, 200))
        if y % 10 == 0: g.text((2, (y - Y0) * Z + 2), str(y), fill=(255, 255, 120))
    g.text((W * Z - 70, H * Z - 14), f"frame {i}", fill=(255, 120, 120)); return im
if __name__ == "__main__":
    for a in range(0, 12, 2):
        s = Image.new("RGB", (900, 960), (0, 0, 0)); s.paste(sheet(a), (0, 0)); s.paste(sheet(a + 1), (0, 480))
        s.save(f"trace/legs_{a:02d}_{a + 1:02d}.png")
    to_race(0).save("trace/frame0_race.png")
