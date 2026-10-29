# python stride_check.py : each model frame (trace/m242_fNN.png, race_b framing) over its fe12 frame in race_b space,
# legs region, x3, in a 4x3 grid -> trace/stride_check.png. Left half of each tile fe12, right half the model.
from PIL import Image, ImageDraw
import trace_sheets as T
tiles = []
for i in range(12):
    f = T.to_race(i).crop((0, 0, 242, 242)); m = Image.open(f"trace/m242_f{i:02d}.png").convert("RGBA")
    ov = f.copy(); mm = m.copy(); mm.putalpha(m.getchannel("A").point(lambda v: v * 65 // 100)); ov.alpha_composite(mm)
    mb = Image.new('RGBA', (242, 242), (20, 26, 40, 255)); mb.alpha_composite(m)
    box = (80, 95, 242, 180)
    t = Image.new("RGB", (2 * 162 * 3 + 6, 85 * 3), (0, 0, 0))
    t.paste(f.crop(box).resize((486, 255), Image.NEAREST), (0, 0)); t.paste(mb.crop(box).resize((486, 255), Image.NEAREST), (492, 0))
    ImageDraw.Draw(t).text((6, 6), f"frame {i}", fill=(255, 220, 90)); tiles.append(t)
W, H = tiles[0].size
s = Image.new("RGB", (W * 2 + 10, H * 6 + 25), (0, 0, 0))
for i, t in enumerate(tiles): s.paste(t, ((i % 2) * (W + 10), (i // 2) * (H + 5)))
s.save("trace/stride_check.png")
