"""Barn identity: names for the computer barns, and every barn's emblem (a shape, two colors and a device, drawn as SVG).
Basic shapes and devices are bought for cash; the trophy devices and the titles are only earned, never sold."""
import hashlib

PALETTE = ["#d8322f", "#1f4fbf", "#f2d233", "#1f8f3f", "#f3f3f3", "#1a1a1a", "#e67e22", "#8e44ad", "#e84393", "#16a085",
           "#7f5a3c", "#5ab7e6", "#c0c0c0", "#7a1f2b"]
# shape -> (price, SVG path in a 40x40 box)
SHAPES = {
    "shield": (0, "M4 4h32v14c0 10-8 16-16 19C12 34 4 28 4 18z"),
    "round": (250_000, "M20 2a18 18 0 1 0 0.01 0z"),
    "diamond": (250_000, "M20 1l19 19-19 19L1 20z"),
    "banner": (400_000, "M6 2h28v36l-14-8-14 8z"),
    "hex": (400_000, "M20 1l17 9.5v19L20 39 3 29.5v-19z"),
}
# device -> (price, glyph); the trophy devices are earned: (None, art file)
DEVICES = {
    "horse": (0, "♞"), "star": (250_000, "★"), "shoe": (250_000, "∩"), "diamond": (250_000, "♦"),
    "bolt": (400_000, "ϟ"), "heart": (400_000, "♥"), "moon": (400_000, "☾"), "clover": (500_000, "♣"),
    "letter": (750_000, "A"),                                  # any letter A-Z (em["letter"]); bought once, switched free
    "cup": (None, "cup"), "laurel": (None, "horseshoe"), "crown": (None, "crown"), "clock": (None, "clock"),
    "money": (None, "money"), "medal": (None, "medal"),
    "plaque": (None, "plaque"), "star": (None, "star"), "ribbon": (None, "ribbon"),
}
# what earns each trophy device, and the title that comes with it
EARNED = {"cup": "Stakes Winners", "laurel": "Crown Winners", "crown": "Champions", "clock": "Record Breakers",
          "money": "Millionaire Makers", "medal": "Hard Knockers",
          "plaque": "Track Champions", "star": "Invitational Winners", "ribbon": "Season Openers"}
EARN_HOW = {"cup": "win a stake", "laurel": "win a Crown final", "crown": "train a division champion", "clock": "set a course record",
            "money": "a horse that has earned $1M", "medal": "a horse with 25 wins",
            "plaque": "win a track's signature stake", "star": "win an Invitational", "ribbon": "win a season opener"}
RENAME_FEE = 1_000_000
EMBLEM_LICENSE = 2_000_000  # opens the emblem builder; until then a barn races in its silks
MARQUEE_FEE = 5_000_000  # the elite barns' marquee: bought once, kept for good
# scene -> (name, what unlocks it beyond the purchase, the colors of its glow: the ring other players see on your emblem)
SCENES = {"grandstand": ("Night Grandstand", None, "#fde68a,#f59e0b,#fff7cc,#b45309,#fde68a"),
          "gilded": ("Gilded Hall", None, "#fff3b0,#e8a33a,#8a5a12,#fff3b0"),
          "neon": ("Neon Tote", "clock", "#ff6b3d,#ffd23f,#ff2e63,#ff6b3d"),
          "aurora": ("Aurora Paddock", "career10m", "#5eead4,#a78bfa,#38bdf8,#5eead4"),
          "snow": ("Winter Meet", None, "#e0f2fe,#7dd3fc,#fbbf24,#e0f2fe"),
          "sunset": ("Golden Hour", "crown", "#fdba74,#f97316,#dc2626,#7c3aed,#fdba74")}
FRAMES = {"bulbs": ("Marquee bulbs", None), "brass": ("Engraved brass", None), "wood": ("Carved wood", None),
          "neon": ("Neon tube", "cup"), "diamond": ("Diamond", "laurel"), "chrome": ("Polished chrome", None)}
BULBS = {"gold": "#ffd36b", "white": "#fff8e6", "red": "#ff5a5a", "ice": "#7dd3fc", "emerald": "#4ade80"}  # or "barn": the barn's rim color
BULB_NAMES = {"gold": "Gold", "white": "White", "barn": "Barn colors", "red": "Ruby", "ice": "Ice blue", "emerald": "Emerald"}
FONTS = {"gilded": "Gilded Serif", "brass": "Engraved Brass", "neon": "Neon Script", "block": "Theater Block", "black": "Old Blackletter"}
NEEDS = {"clock": "set a course record", "cup": "win a stake", "laurel": "win a Crown final", "career10m": "$10M earned by your barn's horses", "crown": "train a division champion"}
MQ_DEFAULT = {"scene": "grandstand", "frame": "bulbs", "bulb": "gold", "font": "gilded", "shim": True, "shelf": []}
# The Marquee's ten Prestige tiers: one look (gilded nameplate, gold light, the track at night) that grows as the barn does.
# Each tier is reached in order once the barn's record meets its milestone, and is kept for good.
# tier: (name, milestone key, how many, scene (None: a plain plate), frame, shimmer, trophy slots, extra classes)
# trophy slots: one either side of the name, the rest (up to 6) in the shadow-box tray under it
PRESTIGE = [
    ("Nameplate", "buy", 1, None, "brass", False, 0, "pt-dim"),
    ("Spotlight", "stakes", 1, None, "brass", False, 0, "pt-spot"),
    ("Grandstand", "career", 2_500_000, "grandstand", "brass", False, 0, "pt-dusk"),
    ("Flashbulbs", "stakes", 10, "grandstand", "brass", False, 1, ""),
    ("Marquee Lights", "crowns", 1, "grandstand", "bulbs", False, 1, "pt-spill"),
    ("Homestretch", "titles", 1, "sunset", "bulbs", True, 2, "pt-spill pt-wreath"),
    ("Golden Hour", "records", 1, "sunset", "bulbs", True, 2, "pt-spill pt-wreath pt-embers"),
    ("Grand Marquee", "career", 10_000_000, "sunset", "bulbs", True, 8, "pt-spill pt-wreath pt-embers pt-rays pt-corners pt-tall"),
    ("Gold Halo", "crowns", 5, "gilded", "goldspin", True, 8, "pt-wreath pt-embers pt-rays pt-glow pt-sweep pt-corners pt-tall"),
    ("Dynasty", "titles", 6, "gilded", "goldspin", True, 8, "pt-wreath pt-embers pt-rays pt-glow pt-sweep pt-corners pt-tall pt-crown pt-dynasty"),
]
NUMERAL = "I II III IV V VI VII VIII IX X".split()


def milestone(key, n):
    """A tier's milestone in words."""
    return {"buy": "Buy the Marquee", "career": f"${n / 1e6:g}M earned by your horses",
            "stakes": "Win a stake" if n == 1 else f"{n} stakes won", "crowns": "Win a Crown final" if n == 1 else f"{n} Crown finals won",
            "titles": "Train a division champion" if n == 1 else f"{n} division championships",
            "records": "Set a course record" if n == 1 else f"{n} course records"}[key]


def prestige(rec):
    """The highest tier a record reaches, climbing in order (rec: stakes, crowns, titles, records, career)."""
    t = 0
    for _, key, n, *_ in PRESTIGE:
        if key != "buy" and rec.get(key, 0) < n:
            break
        t += 1
    return t


def marquee_style(mq):
    """The glow colors a marquee lends its barn's emblem everywhere else."""
    return f"--mqs:{SCENES.get((mq or {}).get('scene'), SCENES['grandstand'])[2]}"



_A = ["Hollow Creek", "Iron Gate", "Maple Run", "Silver Birch", "Blackwater", "Cedar Ridge", "Fox Hill", "Willow Bend", "Stone Bridge",
      "Red Barn", "High Meadow", "Lantern", "Oak Hollow", "Crooked Fence", "Bluegrass", "Mill Pond", "Twin Elms", "Copper Kettle",
      "Juniper", "Harvest Moon", "Kingsley", "North Star", "Thistle Down", "Briar Patch", "Four Winds", "Sandy Lane", "Grey Fox",
      "Pinewood", "Old Orchard", "Riverside"]
_B = ["Stables", "Farm", "Racing", "Stable", "Acres", "Standardbreds"]


def _h(o):
    return int(hashlib.md5(f"barn{o}".encode()).hexdigest(), 16)


def ai_name(o):
    """A computer barn's permanent name: no two barns share one (30 x 6 names before any repeats)."""
    k = o % (len(_A) * len(_B))
    return f"{_A[k % len(_A)]} {_B[(k // len(_A) + k) % len(_B)]}"


def ai_emblem(o):
    x = _h(o)
    shapes = list(SHAPES); devs = [d for d in DEVICES if DEVICES[d][0] is not None and d != "letter"]
    c1 = PALETTE[x % len(PALETTE)]
    c2 = PALETTE[(x // 7 + 1 + x % len(PALETTE)) % len(PALETTE)]
    return {"shape": shapes[x // 97 % len(shapes)], "c1": c1, "c2": c2 if c2 != c1 else "#f3f3f3", "dev": devs[x // 991 % len(devs)]}


def ai_silks(o):
    """A computer barn's silks, for good: two colors and a pattern from its number."""
    import emblem_art
    x = _h(o)
    c1 = PALETTE[x % len(PALETTE)]
    c2 = PALETTE[(x // 7 + 1 + x % len(PALETTE)) % len(PALETTE)]
    return {"pat": emblem_art.PATTERNS[x // 13 % len(emblem_art.PATTERNS)], "c1": c1, "c2": c2 if c2 != c1 else "#f3f3f3"}


DEFAULT = {"shape": "shield", "c1": "#1f4fbf", "c2": "#f2d233", "dev": "horse"}


def svg(em, size=32):
    """The emblem as a pixel-art image: the badge in color 1 with a metal rim (em["rim"]: iron, silver or gold, from Prestige),
    the device in color 2. Stored at 128px and scaled down smoothly by the browser."""
    import emblem_art
    if (em or {}).get("pat"):                                   # silks, not an emblem
        return f"<img class=crest src={emblem_art.render_silks(em)} width={size} height={size} alt=''>"
    em = {**DEFAULT, **(em or {})}
    return f"<img class=crest src={emblem_art.render(em, em.get('rim', 'iron'))} width={size} height={size} alt=''>"


KIND_DEVICE = {"signature": "plaque", "invitational": "star", "opener": "ribbon"}


def earned(horses, champions, record_names, kinds=None):
    """The trophy devices a barn has earned from the horses it owns (owner's horses only; the caller keeps them for good)."""
    got = set()
    for h in horses:
        t = getattr(h, "trophies", [])
        if any("Crown" not in x for x in t):
            got.add("cup")
        if any("Crown" in x for x in t):
            got.add("laurel")
        for x in t:                                             # the stake's kind: a track's signature, an Invitational, an opener
            if (d := KIND_DEVICE.get((kinds or {}).get(x))):
                got.add(d)
        if h.name in champions:
            got.add("crown")
        if h.name in record_names:
            got.add("clock")
        if h.earnings >= 1_000_000:
            got.add("money")
        if h.wins >= 25:
            got.add("medal")
    return got


assert len({ai_name(o) for o in range(180)}) == 180, "every computer barn its own name"
assert prestige({}) == 1 and prestige({"stakes": 10, "career": 3e6}) == 4 and prestige({"stakes": 99, "crowns": 9, "titles": 9, "records": 9, "career": 2e7}) == 10
assert len({str(ai_silks(o)) for o in range(180)}) > 120 and "pat" in ai_silks(3)
assert svg(DEFAULT).startswith("<img") and svg({"dev": "crown", "rim": "gold"}) != svg({"dev": "crown"})
