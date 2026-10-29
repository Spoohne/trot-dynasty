"""Draw the overhead (blimp) sprite's horse in code, with the side sprite's proportions: slim body, long tapering
neck (~45% of the horse), a proper head, mane on the neck only. The driver and sulky seat come from the old art.
12 frames: the hooves peek out from under the body and swing with a pacer's lateral stride.
    python draw_top.py  -> mockups/pixel/top/cycle12_v2.png (+ preview)"""
import math, os
import numpy as np
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mockups", "pixel", "top")
OLD = Image.open(os.path.join(ROOT, "cycle12.png")).convert("RGBA")
FW, FH, FR, CY = 213, 83, 12, 41
COAT, COAT_HI, COAT_LO = (150, 84, 40), (190, 116, 62), (104, 56, 26)
BLACK, BLACK_HI, LINE = (28, 24, 24), (64, 58, 56), (20, 14, 12)
METAL, PAD, PAD_LO = (60, 64, 72), (240, 240, 236), (200, 200, 196)


def body_width(x):
    """Half-width of the horse at column x, in pixels: hips, barrel, shoulder, neck, head (0 = no horse)."""
    keys = [(58, 0), (62, 7), (70, 10), (80, 10.5), (92, 9.5), (106, 10), (118, 9), (128, 7.5),
            (138, 5.5), (152, 4.6), (166, 4.0), (174, 4.4), (182, 4.8), (192, 4.2), (199, 3.0), (203, 0)]
    for (x0, w0), (x1, w1) in zip(keys, keys[1:]):
        if x0 <= x <= x1:
            return w0 + (w1 - w0) * (x - x0) / (x1 - x0)
    return 0


def frame(k):
    img = np.zeros((FH, FW, 4), np.uint8)
    old = np.array(OLD.crop((k * (OLD.width // FR), 0, k * (OLD.width // FR) + FW, FH)))
    img[:, :52] = old[:, :52]                                   # the driver and seat from the old art
    def put(x, y, c, a=255):
        if 0 <= x < FW and 0 <= y < FH:
            img[y, x] = (*c, a)
    ph = 2 * math.pi * k / FR
    # hooves first, so the body covers them: a pacer moves the legs on one side together
    for side, sgn in ((-1, 1), (1, -1)):
        swing = 6 * math.sin(ph) * sgn
        for hx, spread in ((134 + swing, 6.5), (74 - swing, 8.5)):
            for dx in range(-2, 2):
                for dy in range(0, 3):
                    put(int(hx + dx), CY + side * int(spread + 3 + dy), BLACK if dy else BLACK_HI)
    # tail: streams back between the shafts
    for x in range(44, 60):
        for dy in range(-1, 2):
            put(x, CY + dy + (1 if x % 7 == 0 else 0), BLACK if dy else BLACK_HI)
    # the horse: shaded across its width (light along the spine, darker at the flanks), outlined
    for x in range(56, 205):
        w = body_width(x)
        if w <= 0:
            continue
        for y in range(int(CY - w), int(CY + w) + 1):
            d = abs(y - CY) / max(w, .1)
            col = COAT_HI if d < .35 else COAT if d < .8 else COAT_LO
            put(x, y, col)
        put(x, int(CY - w) - 1, LINE); put(x, int(CY + w) + 1, LINE)
    # ears
    for ex in (178, 179):
        put(ex, CY - 6, COAT_LO); put(ex, CY + 6, COAT_LO); put(ex + 1, CY - 7, LINE); put(ex + 1, CY + 7, LINE)
    # mane along the top of the neck only, from the withers to the poll
    for x in range(128, 177):
        put(x, CY - 1, BLACK); put(x, CY, BLACK_HI if x % 3 else BLACK)
    # saddle pad and harness: pad over the back, girth behind the shoulder, breeching over the hips
    for x in range(108, 118):
        for y in range(int(CY - body_width(x)) + 1, int(CY + body_width(x))):
            put(x, y, PAD if x < 116 else PAD_LO)
    for x in (120, 121):
        for y in range(int(CY - body_width(x)), int(CY + body_width(x)) + 1):
            put(x, y, BLACK)
    for y in range(int(CY - body_width(72)), int(CY + body_width(72)) + 1):
        put(72, y, BLACK)
    # shafts: from the sulky seat along the horse's sides to the tugs at the girth
    for x in range(44, 124):
        off = 15 - 4 * (x - 44) / 80
        for sgn in (-1, 1):
            put(x, int(CY + sgn * off), METAL)
    # reins: driver's hands to the bit
    for x in range(52, 196):
        for sgn in (-1, 1):
            if body_width(x) == 0 or abs(sgn * 2) > body_width(x) - 1:
                put(x, CY + sgn * 2, LINE)
    return Image.fromarray(img)


if __name__ == "__main__":
    frames = [frame(k) for k in range(FR)]
    sheet = Image.new("RGBA", (FW * FR, FH))
    for k, f in enumerate(frames):
        sheet.alpha_composite(f, (k * FW, 0))
    sheet.save(os.path.join(ROOT, "cycle12_v2.png"))
    S = 4
    side = Image.open(os.path.join(ROOT, "..", "fe12_cycle.png")).convert("RGBA").crop((0, 0, 208, 101))
    pv = Image.new("RGBA", (FW * S + 20, (101 + FH * 2) * S + 40), (90, 64, 48, 255))
    pv.alpha_composite(side.resize((208 * S, 101 * S), Image.NEAREST), (10, 10))
    pv.alpha_composite(frames[0].resize((FW * S, FH * S), Image.NEAREST), (10, 101 * S + 20))
    pv.alpha_composite(frames[3].resize((FW * S, FH * S), Image.NEAREST), (10, (101 + FH) * S + 30))
    pv.save(os.path.join(ROOT, "v2_preview.png"))
    print("ok")
