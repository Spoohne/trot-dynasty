"""Generate the emblem parts on ComfyUI: blank badges (gold rim, flat light-gray field) and white devices, all on magenta.
python art/emblem/gen_all.py  (from the project root; skips parts already made)"""
import os, subprocess, sys

STYLE = "16-bit pixel art game icon, centered, solid pure magenta background, crisp pixels, SNES style, no text"
BADGE = ("a blank heraldic {} badge seen straight on, thick beveled gold metal rim with highlights, the inner field is flat plain "
         "light gray with subtle top-left shading, nothing inside the field, " + STYLE)
DEV = "{}, solid white with light gray shading and a dark outline, " + STYLE
SHAPES = {"shield": "shield", "round": "perfectly round circular", "diamond": "diamond shaped (a square rotated 45 degrees)",
          "banner": "hanging pennant banner with a swallowtail notch at the bottom", "hex": "hexagon shaped"}
DEVICES = {"horse": "a horse head bust in profile facing left, no base", "star": "a five pointed star", "shoe": "a horseshoe, open end down",
           "diamond": "a cut gemstone diamond", "bolt": "a lightning bolt", "heart": "a heart", "moon": "a crescent moon",
           "clover": "a four leaf clover"}
jobs = [(f"art/emblem/raw/shape_{k}.png", BADGE.format(v)) for k, v in SHAPES.items()]
jobs += [(f"art/emblem/raw/dev_{k}.png", DEV.format(v)) for k, v in DEVICES.items()]
os.makedirs("art/emblem/raw", exist_ok=True)
for out, prompt in jobs:
    if not os.path.exists(out):
        subprocess.run([sys.executable, "art/comfy.py", "gen", prompt, out, "--w", "512", "--h", "512", "--seed", "3"], check=True)
        print("made", out, flush=True)
