"""Sprite Lab's pool: every candidate runner frame made game-ready (208x101, wheel on today's wheel, today's wheel and
driver laid on, outline cleaned) with its wrap mask, so the Lab only ever shows frames that could ship.
    python art/spritelab/build_pool.py              all sources
    python art/spritelab/build_pool.py seedance <frames_dir> <name>     add one Seedance clip
Writes art/spritelab/pool/<source>/NNNN.png and NNNN_m.png, and pool/index.json."""
import json, os, shutil, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ART = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ART, "tack_layers")); sys.path.insert(0, ART)
import assemble_wraps as A
from anchors import anchors, nose
from defringe import defringe

W, H, N = 208, 101, 12
POOL = os.path.join(HERE, "pool")
STOCK = A.orig
TL = os.path.join(ART, "tack_layers")


def cells(sheet):
    im = Image.open(sheet).convert("RGBA")
    return [im.crop((i * W, 0, (i + 1) * W, H)) for i in range(im.width // W)]


def finish(cell, slot, keep_tail=True):
    """Today's wheel and driver on, the wrap mask found, the outline cleaned."""
    c = A.steady(cell.copy(), slot % N, keep_tail)
    m = np.array(A.wraps(c)) > 128
    b, _ = defringe(np.array(c), m)
    return Image.fromarray(b), Image.fromarray((m * 255).astype(np.uint8))


def save(source, name, frames, masks, suggest, note, stride=None):
    d = os.path.join(POOL, source); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    for k, (f, m) in enumerate(zip(frames, masks)):
        f.save(os.path.join(d, f"{k:04d}.png")); m.save(os.path.join(d, f"{k:04d}_m.png"))
    idx = os.path.join(POOL, "index.json")
    data = json.load(open(idx)) if os.path.exists(idx) else {"sources": []}
    data["sources"] = [s for s in data["sources"] if s["id"] != source] + [
        {"id": source, "name": name, "frames": len(frames), "suggest": suggest, "note": note, "stride": stride}]
    json.dump(data, open(idx, "w"), indent=1)
    print(source, len(frames), "frames")


def stock():
    fr = cells(os.path.join(ART, "..", "mockups", "pixel", "fe12_cycle.png"))
    save("today", "Today's runner (no wraps)", fr, [Image.new("L", (W, H)) for _ in fr], list(range(N)),
         "The stock stride, for comparison and for borrowing frames.")


def cycle(source, name, path, note, finished=False):
    fr, ms = [], []
    for k, c in enumerate(cells(path)):
        if finished:
            m = A.wraps(c); fr.append(c); ms.append(m)
        else:
            f, m = finish(c, k); fr.append(f); ms.append(m)
    save(source, name, fr, ms, list(range(N)), note)


def inpainted():
    fr, ms = [], []
    for k in range(N):
        p = os.path.join(TL, "inpaint", f"f{k + 1:02d}_s7.png")
        if not os.path.exists(p):
            continue
        f = Image.open(p).convert("RGBA"); o = np.array(STOCK.crop((k * W, 0, (k + 1) * W, H))).astype(int); a = np.array(f).astype(int)
        changed = (np.abs(a[..., :3] - o[..., :3]).sum(2) > 30) & (a[..., 3] > 0)
        pale = (a[..., :3].sum(2) > 360) & (a[..., :3].max(2) - a[..., :3].min(2) < 45)
        fr.append(f); ms.append(Image.fromarray(((changed & pale) * 255).astype(np.uint8)))
    save("inpaint", "Inpainted on today's runner (GPU)", fr, ms, list(range(len(fr))),
         "Today's frames with wraps painted onto the lower legs only. Frame 12 isn't made yet.")


def seedance(src, source, name):
    """Every frame of a clip: backdrop out, shrunk to sprite scale in today's colors, pinned level, fitted on today's
    wheel at today's horse size (nose kept inside the frame), then finished like the rest."""
    from seedance_loop import key, stock_palette
    files = sorted(f for f in os.listdir(src) if f.endswith(".png") and f[:4].isdigit())
    fr = [key(Image.open(os.path.join(src, f))) for f in files]
    bb = [f.getbbox() for f in fr if f.getbbox()]
    x0 = min(b[0] for b in bb); y0 = min(b[1] for b in bb); x1 = max(b[2] for b in bb); y1 = max(b[3] for b in bb)
    w, h = round((x1 - x0) / 2), round((y1 - y0) / 2); PAL = stock_palette()
    sheet = Image.new("RGBA", (w * len(fr), h))
    for i, f in enumerate(fr):
        c = f.crop((x0, y0, x1, y1))
        q = c.convert("RGB").resize((w, h), Image.BOX).quantize(palette=PAL, dither=Image.Dither.NONE).convert("RGB")
        q.putalpha(c.getchannel("A").resize((w, h), Image.BOX).point(lambda v: 255 if v > 140 else 0)); sheet.paste(q, (i * w, 0))
    tmp = os.path.join(POOL, f"_{source}_raw.png"); pinned = os.path.join(POOL, f"_{source}_pin.png"); os.makedirs(POOL, exist_ok=True)
    sheet.save(tmp)
    pix = os.path.join(ART, "..", "mockups", "pixel")
    subprocess.run([sys.executable, os.path.join(pix, "fix_pace.py"), os.path.relpath(tmp, pix), str(len(fr)), os.path.relpath(pinned, pix),
                    "--bob", "0", "--anchor", "pad"], check=True, cwd=pix, stdout=subprocess.DEVNULL)
    pin = Image.open(pinned).convert("RGBA"); raw = [pin.crop((i * w, 0, (i + 1) * w, h)) for i in range(len(fr))]
    st = [STOCK.crop((i * W, 0, (i + 1) * W, H)) for i in range(N)]
    area = lambda im: (np.array(im)[:, 70:, 3] > 0).sum()
    ow = np.mean([anchors(s)[0][0] for s in st]); oy = np.mean([anchors(s)[0][1] for s in st])
    k = (np.mean([area(s) for s in st]) / np.mean([area(r.resize((W, H))) for r in raw])) ** .5
    stock_nose = max(nose(s)[0] for s in st)

    def place(r, k):
        f = r.resize((round(W * k), round(H * k)), Image.NEAREST); a = anchors(f)
        c = Image.new("RGBA", (W, H)); c.paste(f, (round(ow - a[0][0]), round(oy - a[0][1])), f); return c
    sample = raw[::max(1, len(raw) // 12)]
    for _ in range(2):
        k *= (np.mean([area(s) for s in st]) / np.mean([area(place(r, k)) for r in sample])) ** .5
    def reach(r, k):                                                    # the nose's x before the frame can clip it
        f = r.resize((round(W * k), round(H * k)), Image.NEAREST); a = anchors(f)
        return round(ow - a[0][0]) + f.getbbox()[2]
    while k > .6 and max(reach(r, k) for r in raw) > stock_nose:          # every frame, not a sample
        k *= .99
    out, ms = [], []
    for i, r in enumerate(raw):
        f, m = finish(place(r, k), i, False); out.append(f); ms.append(m)   # video tails come out as noise: today's tail instead
    sug, stride = suggest_even(src, len(fr))
    note = f"Every frame of the clip ({len(fr)})." + (f" One stride is {stride[1]:.1f} frames, from frame {int(stride[0]) + 1}. Fill takes real frames only." if stride else "")
    save(source, name, out, ms, sug, note, stride)
    for p in (tmp, pinned):
        os.remove(p)


def suggest_even(src, n):
    """12 real frames from one exact stride, spaced by how far the legs travel."""
    try:
        import cv2
        first = cv2.imread(os.path.join(src, "0000.png")); hh, ww = first.shape[:2]
        LEGS = (slice(int(hh * .52), int(hh * .9)), slice(int(ww * .17), int(ww * .82)))   # the legs, at any clip size
        g = [np.ascontiguousarray(cv2.cvtColor(cv2.imread(os.path.join(src, f"{j:04d}.png")), cv2.COLOR_BGR2GRAY)[LEGS]) for j in range(n)]
        dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM); step = []
        for j in range(n - 1):
            fl = dis.calc(g[j], g[j + 1], None); mm = np.hypot(fl[..., 0], fl[..., 1]); step.append(float(mm[(g[j] > 40) & (g[j] < 215)].mean()))
        cum = np.concatenate([[0], np.cumsum(step)])
        look = lambda t: (1 - (t % 1)) * g[int(t)].astype(float) + (t % 1) * g[min(n - 1, int(t) + 1)].astype(float)
        moved = lambda a, b: float(np.interp(b, np.arange(n), cum) - np.interp(a, np.arange(n), cum))
        full = moved(0, n - 1) / (n - 1)
        look_ok = lambda s, p: moved(s, s + p) > full * 7                 # a whole stride of travel, not a nearly-still stretch
        best = min(((np.abs(look(s) - look(s + p)).mean(), s, p) for s in np.arange(10, n - 40, .5) for p in np.arange(9, 44.01, .1) if s + p < n - 1 and look_ok(s, p)))
        _, s, p = best; at = lambda t: np.interp(t, np.arange(n), cum)
        return [int(round(float(np.interp(at(s) + (at(s + p) - at(s)) * kk / N, cum, np.arange(n))))) for kk in range(N)], [float(s), float(p)]
    except Exception:
        return list(range(N)), None


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "seedance":
        seedance(a[1], a[2], a[3] if len(a) > 3 else a[2]); sys.exit()
    stock()
    cycle("run3", "SpriteCook run 3 (shipped earlier)", os.path.join(TL, "run3_clean3.png"), "The animated wrapped runner you reviewed frame by frame.", finished=True)
    for r in (0, 1, 2):
        cycle(f"run{r}", f"SpriteCook run {r}", os.path.join(TL, f"run{r}_cycle.png"), "Another animation run of the wrapped still.")
    inpainted()
    seedance(os.path.join(ART, "seedance_out", "test1_frames"), "seedance1", "Seedance clip 1")
