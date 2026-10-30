"""Turn a frame-engine spritesheet (made from the 3x upscaled racing sprite) back into a crisp
pixel-scale cycle: trim to a shared box, shrink to the 242-px sprite grid, then pin the body dead
level at the saddle pad with fix_pace.   python mockups/pixel/fe_prep.py fe8_raw.webp 8 fe8_cycle.png"""
import os, subprocess, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
src, n, dst = sys.argv[1], int(sys.argv[2]), sys.argv[3]
im = Image.open(os.path.join(HERE, src)).convert("RGBA"); fw = im.width // n; fh = im.height
fr = [im.crop((i * fw, 0, (i + 1) * fw, fh)) for i in range(n)]
bb = [f.getchannel("A").point(lambda a: 255 if a > 40 else 0).getbbox() for f in fr]
x0 = min(b[0] for b in bb); y0 = min(b[1] for b in bb); x1 = max(b[2] for b in bb); y1 = max(b[3] for b in bb)
W = round((x1 - x0) * 242 / 726); H = round((y1 - y0) * W / (x1 - x0))     # the source was a 3x upscale of a 242-wide sprite
sheet = Image.new("RGBA", (W * n, H))
for i, f in enumerate(fr):
    sheet.paste(f.crop((x0, y0, x1, y1)).resize((W, H), Image.NEAREST), (i * W, 0))
raw = dst.replace(".png", "_raw.png"); sheet.save(os.path.join(HERE, raw))
subprocess.run([sys.executable, os.path.join(HERE, "fix_pace.py"), raw, str(n), dst, "--bob", "0", "--anchor", "pad"], check=True)
print("frame", W, H, "->", dst)
