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
    app.load(); os.makedirs(TOP, exist_ok=True); n = 0
    for h in app.G["horses"]:
        if h.retired or app.tier_label(h) not in ("S", "S+"):
            continue
        coat, marking = app.looks(h)
        horse = Image.open(recolor.portrait(coat, marking, app.pattern(h), S)).convert("RGBA").resize((S, S), Image.LANCZOS)
        bg = Image.open(os.path.join(SC, f"{scene_of(h.name)}.png")).convert("RGBA")
        bg.alpha_composite(horse); bg.convert("RGB").save(os.path.join(TOP, f"{h.id}.png")); n += 1
    print(n, "top portraits")


if __name__ == "__main__":
    {"scenes": scenes, "stills": stills}[sys.argv[1]]()
    assert len({scene_of(f"Horse {i}") for i in range(60)}) == len(SCENES)   # every scene gets used
