# python compare.py render.png out.png : race_b.png (4x nearest) | render on the same dark plate | overlay
import sys
from PIL import Image
r = Image.open(sys.argv[1]).convert("RGBA").resize((968, 968), Image.LANCZOS)
s = Image.open("../../../mockups/pixel/race_b.png").convert("RGBA").resize((968, 968), Image.NEAREST)
plate = lambda: Image.new("RGBA", (968, 968), (20, 24, 36, 255))
a = plate(); a.alpha_composite(s)
b = plate(); b.alpha_composite(r)
c = plate(); c.alpha_composite(s); ov = r.copy(); ov.putalpha(r.getchannel("A").point(lambda v: v * 6 // 10)); c.alpha_composite(ov)
out = Image.new("RGBA", (968 * 3 + 40, 968), (7, 10, 20, 255))
for i, im in enumerate((a, b, c)): out.paste(im, (i * 988, 0))
out.convert("RGB").save(sys.argv[2])
