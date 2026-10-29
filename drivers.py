"""The circuit's drivers: homages to the great reinsmen, past and present. Each wears his own colors in every race (a
driver's silks go with him, not the horse) and has a style: a small edge the horse feels on the night. Barns set a top
three; the better horse gets a contested driver."""
# style -> (what the owner reads, the lift to the horse's stats for that drive; half: only on a half-mile track)
STYLES = {
    "gate": ("Gets a horse away from the gate and into position", {"early_speed": 0.05}),
    "late": ("Patient. Sits, waits, and times the late move", {"late_speed": 0.06}),
    "half": ("A half-mile track specialist: knows every turn", {"early_speed": 0.04, "late_speed": 0.04}),
    "hands": ("Soft hands: settles a rank horse and keeps it flat", {"gait": 0.15}),
    "stamina": ("Rates a horse beautifully: always has something left", {"stamina": 0.08}),
}

# name, era, style, silks (main, trim); Abbatelli and Filliard keep their colors by request
ROSTER = [
    ("Stan Prancer", "Legend", "late"), ("Billy Hoyton", "Legend", "stamina"), ("Hervé Filliard", "Legend", "gate"),
    ("Del Millbrook", "Legend", "stamina"), ("Joe O'Bannon", "Legend", "hands"), ("Ben Whitcomb", "Legend", "late"),
    ("Ralph Baldridge", "Legend", "hands"), ("Sep Palinski", "Legend", "stamina"), ("Frank Ervington", "Legend", "late"),
    ("Clint Hodgeman", "Legend", "half"), ("Howard Bayer", "Legend", "stamina"), ("George Sholtz", "Legend", "gate"),
    ("Keith Wappler", "Legend", "half"), ("Jimmy Crossley", "Legend", "hands"), ("Lucien Fortier", "Legend", "half"),
    ("Glen Garnet", "Legend", "late"), ("Joe Marcello", "Legend", "gate"), ("Gene Riggins", "Legend", "stamina"),
    ("Tommy Winn", "Legend", "half"), ("Buddy Gilbert", "Legend", "late"),
    ("Johnny Campion", "Record era", "late"), ("Mike LaChapelle", "Record era", "hands"), ("Bill O'Dowell", "Record era", "gate"),
    ("Cat Manzello", "Record era", "half"), ("Walt Casey Jr.", "Record era", "gate"), ("Ron Pearce-Waite", "Record era", "late"),
    ("Ray Remington", "Record era", "stamina"), ("Ron Wapley", "Record era", "half"), ("Dave Palisade", "Record era", "gate"),
    ("Luc Ouelton", "Record era", "hands"), ("Jack Moseley", "Record era", "stamina"), ("Wally Hennigan", "Record era", "half"),
    ("Tony Morrow", "Record era", "gate"), ("Mickey McNiel", "Record era", "late"), ("George Brennigan", "Record era", "stamina"),
    ("Ted Wingate", "Record era", "hands"), ("Norm Jolliet", "Record era", "half"), ("Carmine Abbatelli", "Record era", "gate"),
    ("Tim Tetrault", "Today", "gate"), ("Yannick Gingrich", "Today", "late"), ("Dexter Dunmore", "Today", "stamina"),
    ("David Millbank", "Today", "hands"), ("Andy McCarran", "Today", "late"), ("Jody Jamison-Clark", "Today", "half"),
    ("Brian Sayers", "Today", "stamina"), ("Scott Zerling", "Today", "gate"), ("Doug McNairn", "Today", "hands"),
    ("Matt Kakely", "Today", "half"), ("Jason Bartley", "Today", "late"), ("Aaron Merriwether", "Today", "stamina"),
    ("Åke Svanberg", "Today", "hands"),
]
FIXED = {"Carmine Abbatelli": ("#d8322f", "#f2d233"), "Hervé Filliard": ("#1f4fbf", "#d8322f")}
PALETTE = ["#d8322f", "#1f4fbf", "#f2d233", "#1f8f3f", "#f3f3f3", "#1a1a1a", "#e67e22", "#8e44ad", "#e84393", "#16a085",
           "#7f5a3c", "#5ab7e6", "#c0c0c0", "#7a1f2b"]


def _silks():
    """Every driver a pair of colors no one else wears: the fixed ones first, then distinct pairs from the palette."""
    used = set(FIXED.values())
    n = len(PALETTE)                                       # jackets cycle through the palette, trims step further each lap
    pairs = (p for k in range(1, n) for i in range(n) for p in [(PALETTE[i], PALETTE[(i + k) % n])] if p not in used)
    out = {}
    for name, *_ in ROSTER:
        out[name] = FIXED.get(name) or next(pairs)
    return out


SILKS = _silks()
NAMES = [n for n, *_ in ROSTER]
ERA = {n: e for n, e, _ in ROSTER}
STYLE = {n: s for n, _, s in ROSTER}

assert len(ROSTER) == 51 and len(set(NAMES)) == 51 and len(set(SILKS.values())) == 51
assert SILKS["Carmine Abbatelli"] == ("#d8322f", "#f2d233") and SILKS["Hervé Filliard"] == ("#1f4fbf", "#d8322f")


def lift(name, track):
    """What this driver gives a horse tonight."""
    style = STYLE.get(name)
    if not style or (style == "half" and track != "half"):
        return {}
    return STYLES[style][1]
