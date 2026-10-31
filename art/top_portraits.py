"""S and S+ portraits: each top horse's own portrait laid on one of six scene backdrops (picked from its name, so it
never changes), and for S+ a 12-frame idle loop (ears, breath, mane) made by SpriteCook from that picture.
    python art/top_portraits.py scenes           crop the six raw backdrops to 256px
    python art/top_portraits.py stills            compose every S/S+ horse in the save (free)
    python art/top_portraits.py loops             list the S+ stills that still need a loop (the loop runs through SpriteCook)
Writes mockups/portraits/top/<id>.png and <id>_loop.png (12 frames, one row)."""
import hashlib, os, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SC = os.path.join(ROOT, "mockups", "portraits", "scenes"); TOP = os.path.join(ROOT, "mockups", "portraits", "top")
SCENES = ("circle", "sunrise", "trophy", "rain", "paddock", "snow")
S = 256


def scene_of(name):
    """The horse's scene, fixed by its name."""
    return SCENES[int(hashlib.md5(name.encode()).hexdigest(), 16) % len(SCENES)]


def scenes():
    for k in SCENES:
        Image.open(os.path.join(SC, f"{k}_raw.png")).convert("RGB").resize((S, S), Image.LANCZOS).save(os.path.join(SC, f"{k}.png"))


def stills():
    sys.path.insert(0, ROOT); os.chdir(ROOT)
    import app, recolor
    if len(sys.argv) > 2:
        app.SAVE = sys.argv[2]                                          # another save (the live world's copy)
    app.load(); os.makedirs(TOP, exist_ok=True); n = 0
    for h in app.G["horses"]:
        if h.retired or app.tier_label(h) not in ("S", "S+"):
            continue
        if os.path.exists(os.path.join(TOP, f"{h.id}.png")) and "--redo" not in sys.argv:
            continue
        coat, marking = app.looks(h)
        horse = Image.open(recolor.portrait(coat, marking, app.pattern(h), S)).convert("RGBA").resize((S, S), Image.LANCZOS)
        bg = Image.open(os.path.join(SC, f"{scene_of(h.name)}.png")).convert("RGBA")
        bg.alpha_composite(horse); bg.convert("RGB").save(os.path.join(TOP, f"{h.id}.png")); n += 1
    print(n, "new top portraits")
    need = [h for h in app.G["horses"] if not h.retired and app.tier_label(h) == "S+" and not os.path.exists(os.path.join(TOP, f"{h.id}_loop.webp"))]
    for h in need:
        print("needs loop:", h.id, h.name)


BASE_LOOP = os.path.join(ROOT, "art", "portrait_mock", "base_loop")          # 12 frames of the base head, keyed, 1024px (base_NN.png)


def loops():
    """Every S+ horse's idle loop from the one animated base head: each frame recolored to its coat and marking the way
    recolor.portrait does the still, laid on its scene, saved as a 12-frame WebP strip. Free: no generation per horse."""
    import numpy as np
    sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "art")); os.chdir(ROOT)
    import app, recolor
    if len(sys.argv) > 2:
        app.SAVE = sys.argv[2]
    app.load()
    frames = [np.asarray(Image.open(os.path.join(BASE_LOOP, f"base_{i:02d}.png")).convert("RGBA").resize((S, S), Image.LANCZOS)).astype(np.float32) for i in range(12)]
    n = 0
    for h in app.G["horses"]:
        if h.retired or app.tier_label(h) != "S+" or (os.path.exists(os.path.join(TOP, f"{h.id}_loop.webp")) and "--redo" not in sys.argv):
            continue
        coat, marking = app.looks(h); seed = app.pattern(h)
        bg = Image.open(os.path.join(SC, f"{scene_of(h.name)}.png")).convert("RGBA")
        strip = Image.new("RGB", (S * 12, S))
        for i, f in enumerate(frames):
            out = recolor.dapple_grey(f, seed % 1000) if coat == "grey" else recolor.COATS.get(coat, recolor.chestnut)(f)
            fr = bg.copy(); fr.alpha_composite(Image.fromarray(recolor.mark(f, out, marking))); strip.paste(fr.convert("RGB"), (i * S, 0))
        strip.save(os.path.join(TOP, f"{h.id}_loop.webp"), quality=82, method=6); n += 1
    print(n, "loops")


if __name__ == "__main__":
    {"scenes": scenes, "stills": stills, "loops": loops}[sys.argv[1]]()
    assert len({scene_of(f"Horse {i}") for i in range(60)}) == len(SCENES)   # every scene gets used
