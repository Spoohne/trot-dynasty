"""Turn SpriteCook loop sheets into the game's <id>_loop.png: 12 frames of 256px in one row."""
import sys
from PIL import Image
R = r"C:\Users\spooh\HarnessSim"
for line in open(sys.argv[1]):
    hid, _ = line.split()
    sh = Image.open(rf"{R}\art\portrait_mock\loops\{hid}_sheet.webp").convert("RGB"); fw = sh.width // 12
    out = Image.new("RGB", (256 * 12, 256))
    for i in range(12):
        out.paste(sh.crop((i * fw, 0, (i + 1) * fw, sh.height)).resize((256, 256), Image.LANCZOS), (i * 256, 0))
    out.save(rf"{R}\mockups\portraits\top\{hid}_loop.png", optimize=True); print(hid, "ok")
