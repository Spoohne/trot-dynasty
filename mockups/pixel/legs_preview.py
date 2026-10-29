"""Preview the code-drawn legs without a browser: the same gait maths as replay_pixel.html,
drawn onto the leg-free body at 8 points in the stride, enlarged.  python mockups/pixel/legs_preview.py"""
import math, os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
GROUND_Y, DUTY = 108, .45
LEG = {"fore": dict(hip=(181, 52), up=28, low=28, reach=23, lift=9, bend=1, lead=.03, w=(10, 6, 4)),
       "hind": dict(hip=(101, 52), up=29, low=28, reach=21, lift=6, bend=-1, lead=0, w=(12, 6, 4))}


def foot(L, p):
    hx = L["hip"][0]; cx = hx + 3 * L["bend"]
    if p < DUTY:
        return cx + L["reach"] - 2 * L["reach"] * (p / DUTY), GROUND_Y
    q = (p - DUTY) / (1 - DUTY); e = (1 - math.cos(math.pi * q)) / 2
    return cx - L["reach"] + 2 * L["reach"] * e, GROUND_Y - L["lift"] * math.sin(math.pi * q)


def knee(L, f):
    hx, hy = L["hip"]; dx, dy = f[0] - hx, f[1] - hy
    d = min(math.hypot(dx, dy), L["up"] + L["low"] - .5)
    a = math.acos(max(-1, min(1, (L["up"] ** 2 + d * d - L["low"] ** 2) / (2 * L["up"] * d))))
    t = math.atan2(dy, dx) - a * L["bend"]
    return hx + L["up"] * math.cos(t), hy + L["up"] * math.sin(t)


def seg(d, a, b, w0, col, w1=None):
    w1 = w0 if w1 is None else w1
    n = max(1, math.ceil(math.hypot(b[0] - a[0], b[1] - a[1])))
    for i in range(n + 1):
        t = i / n; wd = round(w0 + (w1 - w0) * t)
        x = a[0] + (b[0] - a[0]) * t; y = a[1] + (b[1] - a[1]) * t
        x0, y0 = round(x - wd / 2), round(y - wd / 2)
        d.rectangle([x0, y0, x0 + wd - 1, y0 + wd - 1], fill=col)


def leg(d, kind, p, far):
    L = LEG[kind]; f = foot(L, ((p - L["lead"]) % 1 + 1) % 1); k = knee(L, f); m = .58 if far else 1
    t = lambda r, g, b: (int(r * m), int(g * m), int(b * m))
    w0, w1, w2 = L["w"]; fet = (f[0] - 2 * L["bend"] * (-1 if f[1] < GROUND_Y - 1 else 1), f[1] - 5)
    seg(d, L["hip"], k, w0 + 2, t(40, 18, 8), w1 + 2); seg(d, k, fet, w1 + 1, t(12, 9, 7), w2 + 1)
    seg(d, L["hip"], k, w0, t(122, 60, 30), w1); seg(d, (L["hip"][0] - 1, L["hip"][1]), (k[0] - 1, k[1]), max(2, w0 // 3), t(156, 82, 42), 2)
    seg(d, k, fet, w1, t(34, 25, 20), w2); seg(d, fet, (f[0], f[1] - 2), 3, t(232, 232, 232))
    d.rectangle([round(f[0] - 3), round(f[1] - 2), round(f[0] + 2), round(f[1])], fill=t(14, 10, 8))


body = Image.open(os.path.join(HERE, "race_body.png")).convert("RGBA")
S, cells = 3, []
for k in range(8):
    p = k / 8
    im = Image.new("RGBA", (250, 118), (42, 47, 56, 255)); d = ImageDraw.Draw(im)
    d.rectangle([0, 108, 250, 118], fill=(90, 61, 41, 255))
    leg(d, "hind", (p + .5) % 1, True); leg(d, "fore", (p + .5) % 1, True)
    leg(d, "hind", p, False); leg(d, "fore", p, False)
    im.alpha_composite(body); d = ImageDraw.Draw(im)
    d.text((4, 2), f"{k}/8", fill=(255, 220, 120))
    cells.append(im.resize((250 * S, 118 * S), Image.NEAREST))
out = Image.new("RGB", (250 * S * 2, 118 * S * 4))
for k, c in enumerate(cells): out.paste(c, ((k % 2) * 250 * S, (k // 2) * 118 * S))
out.save(os.path.join(HERE, "legs_preview.png")); print("wrote legs_preview.png")
