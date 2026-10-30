"""Leg wraps inpainted onto today's runner on the local GPU: only the lower legs are repainted, everything else stays
the stock frame's own pixels, so the body can't jitter and the wrap layer is exactly the pixels that changed.
    python art/tack_layers/inpaint_wraps.py <frame 1-12> [seed] [denoise]   -> inpaint/f<NN>_s<seed>.png (+ preview)"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
import comfy

W, H, K = 208, 101, 5                                   # frame size; worked at 5x
BG = (128, 128, 128)
OUT = os.path.join(HERE, "inpaint"); os.makedirs(OUT, exist_ok=True)
PROMPT = ("Add plain white padded polo leg wraps (bandages) on the horse's four lower legs, wrapped around the cannon bone "
          "from just below the knee and hock down to the fetlock. The pasterns and black hooves below stay bare and keep "
          "their exact shape. Keep the 16-bit pixel art style, the same pose, the same leg positions and the same colors.")


def frame(i):
    im = Image.open(os.path.join(HERE, "..", "..", "mockups", "pixel", "fe12_cycle.png")).convert("RGBA")
    return im.crop(((i - 1) * W, 0, i * W, H))


def leg_mask(f, grow=3):
    """The lower legs: the horse's opaque pixels below the knees, right of the sulky, grown a little for the padding."""
    a = np.array(f)[:, :, 3] > 0
    m = np.zeros_like(a); m[64:, 40:] = a[64:, 40:]
    yy, xx = np.mgrid[:H, :W]
    wheel = np.hypot(xx - 30, yy - 75) <= 28                            # the sulky wheel is never a leg
    m &= ~wheel
    grown = np.array(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(grow * 2 + 1))) > 0
    return Image.fromarray(((grown & ~wheel) * 255).astype(np.uint8))


def run(i, seed=7, denoise=.8):
    f = frame(i); m = leg_mask(f)
    flat = Image.new("RGB", f.size, BG); flat.paste(f, mask=f.getchannel("A"))
    src = os.path.join(OUT, f"src_{i:02d}.png"); msk = os.path.join(OUT, f"mask_{i:02d}.png")
    flat.resize((W * K, H * K), Image.NEAREST).save(src); m.resize((W * K, H * K), Image.NEAREST).save(msk)
    raw = os.path.join(OUT, f"raw_{i:02d}_s{seed}.png")
    _, secs = comfy.inpaint(PROMPT, src, msk, raw, seed=seed, denoise=denoise)
    r = Image.open(raw).convert("RGB").resize((W, H), Image.BOX)                         # back to sprite scale
    rn, fn, mn = np.array(r).astype(int), np.array(f), np.array(m) > 0
    out = fn.copy()
    keyed = np.abs(rn - np.array(BG)).sum(2) > 40                                        # not the grey backdrop
    take = mn & keyed
    out[take, :3] = rn[take]; out[take, 3] = 255
    out[mn & ~keyed] = 0                                                                 # backdrop inside the leg area: clear
    res = Image.fromarray(out.astype(np.uint8))
    path = os.path.join(OUT, f"f{i:02d}_s{seed}.png"); res.save(path)
    view = Image.new("RGBA", (W * 2 + 6, H), (58, 38, 26, 255)); view.alpha_composite(f); view.alpha_composite(res, (W + 6, 0))
    view.resize((view.width * 4, view.height * 4), Image.NEAREST).save(path.replace(".png", "_view.png"))
    return path, secs


if __name__ == "__main__":
    i = int(sys.argv[1]); seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7; dn = float(sys.argv[3]) if len(sys.argv) > 3 else .8
    p, s = run(i, seed, dn); print(p, f"{s}s")
