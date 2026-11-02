"""Live-clock circuit: one real day = one game week = one race card at post time.
Run: python circuit.py

Owners (AI and player alike) never see the hidden genetics. They see a public
estimate of each horse (mean + spread, shown as a tier S/A/B/C/D) that starts
from pedigree and sharpens with every start. Each week an owner picks one plan
per horse: race, train (with a focus), or rest. A freshness meter ties the
three together; durability sets how fast it drains and refills. No injuries:
nothing random ever damages a horse.
"""
import copy
import os
import outcome
ENGINE = os.environ.get("TD_ENGINE", "outcome")   # race night decided by the outcome engine (outcome.py); TD_ENGINE=live rolls back to sim.race
import statistics as st
from itertools import count
from sim import GAIT_CAP, GAIT_W, W_FINISH, W_SPEED, W_STAM, HALF_SLOWER, RACE_TRAITS, RETIRE_AGE, Horse, founder, breed, race, rng
import sim
from collections import Counter

# --- condition sheet (USTA style). name, eligible, purse, class rating
wins_in = lambda h, n: sum(h.recent[-n:])          # wins in the last n starts (public record)
CONDITIONS = [
    ("NW1", lambda h: h.wins < 1, 8_000, 45),                   # maidens: lifetime (purses measured 2026-10-29: the bottom
    ("NW2L6", lambda h: wins_in(h, 6) < 2, 10_000, 50),         # rungs nudged so a maiden can about cover its board)
    ("NW$20k", lambda h: h.earnings < 20_000, 11_000, 55),      # a horse that stops winning drops back
    ("NW4L10", lambda h: wins_in(h, 10) < 4, 13_000, 58),
    ("NW$50k", lambda h: h.earnings < 50_000, 15_000, 63),
    ("NW2L5", lambda h: wins_in(h, 5) < 2, 17_000, 68),
    ("NW$15kL5", lambda h: sum(h.last5) < 15_000, 14_000, 63),
    # the top of the ladder is one race: rating 88 is the top one or two percent of the circuit, a dozen horses, and
    # splitting them by earnings (the old Winners Over rungs, retired 2026-10-30) left four thin fields and no race at all.
    # A 3-year-old that rates goes up to it; 2-year-olds stay with their own age
    ("Invitational", lambda h: _rated(h) >= 88 and h.age >= 3, 80_000, 92),     # the Free-for-All: the very best, by invitation
    # the top of each young age: a fast 2- or 3-year-old that has outgrown every condition races its own age here,
    # not the veterans in the all-ages Open
    ("2YO Open", lambda h: age_group(h) == "2", 20_000, 72),
    ("3YO Open", lambda h: age_group(h) == "3", 25_000, 75),
    ("Preferred", lambda h: _rated(h) >= 82, 40_000, 86),       # three rungs for an older horse between the top claimer
    ("Open", lambda h: _rated(h) >= 76, 32_000, 78),            # and the Invitational (Aged Open used to catch them all)
    ("Aged Open", lambda h: True, 30_000, 77),                  # the top of the ordinary older horses
]
RETIRED_CLASS = {"NW$6kL5": "NW$20k", "Winners Over $1M": "Invitational", "Winners Over $500k": "Invitational",
                 "Winners Over $200k": "Invitational"}           # classes taken off the sheet: an old order for one lands here
ALL_AGES = ("Invitational", "Preferred", "Open")                 # the top classes take every age; the conditions below them are per age
TOP_MIN = 4                                                      # a top class short of this folds into the one below it
MIXED = ("2YO Open", "3YO Open", "Aged Open")                   # colts and fillies race together here: few qualify, so one card each
# tag, class rating, purse. Every tag is carded
# for each age class (2YO, 3YO, Aged); colts and fillies race together.
# Tags sit a little under what a horse at that level earns (measured 2026-10-28: the old $50k-$1M tags ran 3-4x that),
# so a claim is a real bargain and dropping a good horse in is a real risk. The bottom tag stays above the house's $20k.
# Purses sit just over the condition class at the same rating: the owner is paid a little for the risk, and a computer
# barn (which takes the richer race half its weeks) puts real horses in.
CLAIMERS = [(25_000, 35, 8_000), (40_000, 50, 11_000), (60_000, 58, 14_000), (90_000, 64, 18_000), (125_000, 70, 22_000),
            (200_000, 76, 30_000), (300_000, 82, 42_000), (500_000, 88, 52_000), (1_000_000, 92, 62_000)]
OLD_TAGS = {50_000: 25_000, 100_000: 40_000, 200_000: 60_000, 300_000: 90_000, 500_000: 125_000, 1_000_000: 200_000}


def clm_name(tag):
    return f"CLM{tag // 1_000_000}M" if tag >= 1_000_000 else f"CLM{tag // 1000}k"


def clm_tag(tag):
    """The ladder's tag nearest a given one (an order from an older ladder still lands on a real race)."""
    return min((t for t, _, _ in CLAIMERS), key=lambda t: abs(t - tag))
def _rated(h):
    return on_aged_scale(h.est, age_group(h))


CLASS_RATING = {n: r for n, _, _, r in CONDITIONS} | {clm_name(t): r for t, r, _ in CLAIMERS}
CLAIM_PURSE = {t: p for t, _, p in CLAIMERS}
PURSE_SPLIT = [0.50, 0.25, 0.12, 0.08, 0.05]
DRIVER = 0.05            # the driver's cut of what the horse earns. Racing itself costs nothing:
                         # money only leaves a barn when its owner chooses to spend it.
FIELD = {"mile": 10, "half": 8}   # a mile track gates ten; a half-mile's tight turns hold eight

# The circuit's tracks. Each has a size (mile or half-mile), a purse level, and a slate: the classes it cards.
# Entries are pooled by class and size as before, so fields stay full; each race is then run at a track whose
# slate takes that class (the one an owner asked for, if it does). Every class is on some track's slate.
# Purse levels average out about even between the mile and half-mile tracks, so neither size pays more per start.
CLM_ALL = tuple(clm_name(t) for t, _, _ in CLAIMERS)
CLM_TOP = ("CLM300k", "CLM500k", "CLM1M")
VENUES = [
    dict(id="hp", name="Harness Park", track="mile", purse=1.15, passing=True,
         about="The flagship mile: the Invitational, the Preferred and the big-money claimers. Stakes nights are run here.",
         slate=("Invitational", "Preferred", "Open", "3YO Open", "NW2L5", "NW$15kL5", "CLM90k", "CLM125k", "CLM200k") + CLM_TOP),
    dict(id="rd", day=True, name="Riverside Downs", track="mile", purse=0.95, passing=True,
         about="The proving ground: conditioned and mid-priced claiming stock on a fair, sweeping mile.",
         slate=("Open", "2YO Open", "3YO Open", "NW1", "NW2L6", "NW$20k", "NW4L10", "NW$50k", "NW2L5", "NW$15kL5",
                "CLM25k", "CLM40k", "CLM60k", "CLM90k")),
    dict(id="ml", day=True, name="Meadow Lane", track="half", purse=1.0, passing=True,
         about="The young horses' half-mile: maidens, early conditions and the 2- and 3-year-old Opens.",
         slate=("2YO Open", "3YO Open", "NW1", "NW2L6", "NW$20k", "NW$50k", "NW4L10")),
    dict(id="gh", name="Granite Hill", track="half", purse=1.1,
         about="Tight turns that favour a horse with gate speed: earnings conditions, the Open and the claiming middle.",
         slate=("Open", "NW$20k", "NW$15kL5", "NW2L6", "NW4L10", "NW2L5", "CLM25k", "CLM40k", "CLM60k",
                "CLM90k", "CLM125k", "CLM200k", "Preferred", "Invitational") + CLM_TOP),
    dict(id="bf", day=True, name="Bayview Fair", track="half", purse=0.9, fair=(30, 34),
         about="The county-fair half: maidens and cheap claimers most of the year; fair week (weeks 30-33) pays double.",
         slate=("NW1", "NW2L6", "CLM25k", "CLM40k", "2YO Open")),
]
VENUES += [
    dict(id="cr", name="Capital Raceway", track="mile", purse=1.1, passing=True,
         about="The big-city mile under the lights: the Open, the Preferred and a strong claiming ladder.",
         slate=("Preferred", "Open", "3YO Open", "NW2L5", "NW$15kL5", "NW$50k", "CLM60k", "CLM90k", "CLM125k", "CLM200k") + CLM_TOP),
    dict(id="ls", name="Lakeshore Park", track="mile", purse=1.0, passing=True,
         about="A wide, forgiving mile by the water: where the young horses learn to finish.",
         slate=("2YO Open", "3YO Open", "NW1", "NW2L6", "NW$20k", "NW4L10", "NW$50k", "CLM40k", "CLM60k")),
    dict(id="ng", name="Northgate Raceway", track="mile", purse=0.95, passing=True,
         about="The working-class mile: conditioned veterans and the claiming middle, every week of the year.",
         slate=("Open", "NW$15kL5", "NW4L10", "NW2L6", "NW$20k", "CLM25k", "CLM40k", "CLM60k", "CLM90k")),
    dict(id="sh", day=True, name="Sandhill Downs", track="half", purse=1.05, passing=True,
         about="A sandy half with a long stretch for a half-miler: the Opens and the upper claimers.",
         slate=("Open", "Preferred", "3YO Open", "2YO Open", "NW2L5", "NW$50k", "CLM60k", "CLM90k", "CLM125k")),
    dict(id="pr", name="Pine Ridge", track="half", purse=0.95,
         about="The hill-country half: maidens, early conditions and cheap claimers, with a loyal local crowd.",
         slate=("NW1", "NW2L6", "NW$20k", "NW4L10", "2YO Open", "CLM25k", "CLM40k")),
]
# fair weeks around the circuit, three weeks each where purses double: Bayview's in late summer, four more through the year
for _vid, _wk in (("gh", (12, 15)), ("sh", (20, 23)), ("pr", (40, 43)), ("ml", (45, 48))):
    next(v for v in VENUES if v["id"] == _vid)["fair"] = _wk
OPENS = ("Open", "2YO Open", "3YO Open", "Aged Open")   # every track cards the Open and an Open for each age
for v in VENUES:
    v["slate"] = tuple(dict.fromkeys(OPENS + tuple(v["slate"])))
VENUE_BY = {v["id"]: v for v in VENUES}


def hosts(name, track):
    """The tracks of this size that card this class."""
    return [v for v in VENUES if v["track"] == track and name in v["slate"]]


def venue_purse(v, purse, day=None):
    """A class's purse at a given track: its purse level, doubled in its fair week."""
    wk = (DAY[0] if day is None else day) % YEAR + 1
    fair = v.get("fair") and v["fair"][0] <= wk < v["fair"][1]
    return int(round(purse * v["purse"] * (2 if fair else 1), -2))


def wanted(h):
    """The track a horse was entered at (o[5] of an entry), or None."""
    o = getattr(h, "order", None)
    return o[5] if isinstance(o, tuple) and o[0] == "enter" and len(o) > 5 else None


def make_splits(name, track, entries):
    """Divide a class's entries into races: one race at each track an owner asked for (if it cards the class and
    enough horses can make a field there), the rest filling out in turn; an owner's horses go to different races
    when there are races enough. Returns [(venue, field)]."""
    vs = hosts(name, track)
    ids = [v["id"] for v in vs]
    n = max(1, -(-len(entries) // FIELD[track]))
    asked = []
    for h in entries:
        w = wanted(h)
        if w in ids and w not in asked:
            asked.append(w)
    n = max(n, min(len(asked), len(entries) // 4))             # a race per requested track, if each can field four
    seats = asked[:n] + [ids[(k + DAY[0]) % len(ids)] for k in range(n - len(asked[:n]))]   # a player's horses may meet, like stablemates
    races = [(VENUE_BY[v], []) for v in seats]
    cap = -(-len(entries) // n)
    rng.shuffle(entries)
    entries.sort(key=lambda h: wanted(h) not in seats)          # those who asked for a track seat first
    for h in entries:
        w = wanted(h)
        open_ = [r for r in races if len(r[1]) < cap] or races
        mine_ = [r for r in open_ if r[0]["id"] == w] if w else []
        r = sorted(mine_ or open_, key=lambda r: (sum(x.owner == h.owner for x in r[1]), len(r[1])))[0]
        r[1].append(h)
    return [(v, f) for v, f in races if f]


def pick_venue(name, track, field, i):
    """Where a split runs: the track an entrant asked for if it cards the class, else the tracks share the class
    in turn (by split and week, so it's settled before post time)."""
    vs = hosts(name, track)
    for h in field:
        o = getattr(h, "order", None)
        if isinstance(o, tuple) and o[0] == "enter" and len(o) > 5 and o[5] in [v["id"] for v in vs]:
            return VENUE_BY[o[5]]
    return vs[(i + DAY[0]) % len(vs)]
UNFILLED = []            # races that couldn't be made even with fillers (should stay empty)
DAY = [0]                # the circuit's current day, for stamping results
STORIES = {}             # race id -> story (how the race unfolded, for the replay); last ~400 kept
RECORDS = {}             # track -> course records: the fastest leader's time at the quarter, half, three-quarters and wire


def set_records(track, quarters):
    """Fold one race's quarters into the course records; returns the records as they stood before it."""
    before = RECORDS.get(track)
    RECORDS[track] = [min(a, b) for a, b in zip(before, quarters)] if before else list(quarters)
    return before
import story as _story
import names as _names
EPOCH = [0]              # the game day that is Year 0, week 1: before it lies the simulated history (Years -20 to -1)


def year_of(day):
    return (day - EPOCH[0]) // YEAR


def lineage(horses):
    """Every horse in the stud book: the living, the nursery's, and all their ancestors, however long gone."""
    seen, stack = {}, list(horses)
    while stack:
        h = stack.pop()
        if h is None or id(h) in seen:
            continue
        seen[id(h)] = h
        stack += [getattr(h, "sire", None), getattr(h, "dam", None)]
    return list(seen.values())
TIERS = [(80, "S"), (68, "A"), (55, "B"), (40, "C"), (0, "D")]
AGE_CLASS = {"2": "2YO", "3": "3YO", "aged": "Aged"}   # conditions are written for one age class; the Open takes all ages


TAKE = 0.17               # the track's cut of the win pool: every price is a little shorter than the chance


def tote_odds(field):
    """The public's win odds on a field, from the public ratings alone: money follows the estimate, the track
    takes its cut, and prices land on the tote's own steps (4-5, 5-2, 9-2...). Returns {horse id: (to, over)}."""
    w = ({h.id: 2.718 ** (1.9 * outcome.rating(h)) for h in field} if ENGINE == "outcome"   # the card's rating, fitted to who wins (DECISIONS 240)
         else {h.id: 2.718 ** (h.est / 15) for h in field})
    tot = sum(w.values())
    steps = [(1, 9), (1, 5), (2, 5), (1, 2), (3, 5), (4, 5), (1, 1), (6, 5), (7, 5), (3, 2), (8, 5), (9, 5), (2, 1), (5, 2),
             (3, 1), (7, 2), (4, 1), (9, 2), (5, 1), (6, 1), (8, 1), (10, 1), (12, 1), (15, 1), (20, 1), (30, 1), (50, 1), (99, 1)]
    out = {}
    for h in field:
        o = (1 - TAKE) * tot / w[h.id] - 1
        out[h.id] = min(steps, key=lambda s: abs(s[0] / s[1] - max(0.1, o)))
    return out


def race_title(group, name):
    if name.startswith("CLM"):                               # open-entry claimers: every age, one card per tag
        amt = int(name[3:-1]) * (1_000_000 if name.endswith("M") else 1000)   # CLM25k -> $25,000, written out in full
        return f"{AGE_CLASS.get(group, 'Aged')} Claiming ${amt:,}"   # one per age class: 2YO, 3YO, Aged
    if name == "Aged Open":
        return name
    return name if name in ALL_AGES or name[:3] in ("2YO", "3YO") else f"{AGE_CLASS[group]} {name}"


GROUP_STATS = {"2": (55.0, 15.0), "3": (55.0, 15.0), "aged": (55.0, 15.0)}   # public: (mean, sd) of est per age group


def on_aged_scale(x, group):
    """Standardize a rating within its age group onto a fixed public scale (mean 55, sd 15),
    so a tier means the same rank in any year and any group: S is the top ~5%, D the bottom ~16%."""
    m, s = GROUP_STATS[group]
    return 55 + 15 * (x - m) / (s or 1)
OBS_SD = 8.0             # how noisy one finishing position is as evidence of rating
TIME_FIT = {"mile": 784.5, "half": 780.9 + 6.2 * HALF_SLOWER}, -6.2, 13.5   # rating ~ a[track] + b*seconds, residual sd, on the race's
                                                                             # internal seconds (h.raw_time); the clock is for show
DROP_MARGIN = 0          # owner drops to a claimer once est is under the class it would race in
YEAR = 52                # game weeks (real days) per game year
SHAPE_CAP = 1.0          # how far training can push one trait above (or below) the genetic ceiling. With DEV_W, two seasons of the
                         # owner's day sheet measure ~+0.8 rating, half a length, over the stable's jogging (train_edge.py)
SHAPED = ["early_speed", "late_speed", "stamina", "gait"]   # durability isn't trained into a horse
FOAL_DISCOUNT = 15       # shortcut: a 2YO rates ~15 under its parents' public est; upgrade when the public sees maturity

for attr in ("starts", "wins", "places", "shows", "earnings", "costs", "owner", "claimed", "ran_claimer", "retired", "handled"):
    setattr(Horse, attr, 0)
Horse.job = None         # the day sheet's stamp: (day, job, focus) once the owner has worked the youngster this week
BREEDING_UNTIL = 20      # retired stock leaves the game at this age


def retire(h):
    """End the racing career. Irreversible: the horse leaves its trainer and can now breed."""
    if getattr(h, "trainer", None):
        h.trainer.horses -= 1
    h.trainer, h.retired, h.order, h.ship = HOUSE, True, None, None
    h.last = "retired"
    # the card becomes the reputation: career-best rating and the best each stat ever showed
    h.est = peak_est(h)
    h.developed = {t: max(h.developed[t], getattr(h, "peak_dev", h.developed)[t]) for t in RACE_TRAITS}
    h.tier = max(public_tier(h), getattr(h, "peak_tier", "D"), key=TIER_ORDER.index)   # the best it was ever shown as


def rating_tonight(h, track="mile"):
    """What the horse brings to the gate tonight: fitness, shaping and the trainer's hand included."""
    s = h.current(track)
    return 70 + 6 * (W_SPEED * s["early_speed"] + W_FINISH * s["late_speed"] + W_STAM * s["stamina"] + GAIT_W * min(s["gait"], GAIT_CAP) + min(s["gait"], s["stamina"], 0))


def true_rating(h):
    """What the horse is today, fresh: ceiling for its age plus the trainer's shaping.
    Scale: prime-age mean ~55, sd ~15, so S is the top ~4%."""
    if not hasattr(h, "shape"):
        return max(0, min(99, 70 + 6 * h.race_score(h.age)))
    s = {t: min(h.developed[t], h.ceiling(t)) + h.shape[t] for t in RACE_TRAITS}
    score = W_SPEED * s["early_speed"] + W_FINISH * s["late_speed"] + W_STAM * s["stamina"] + GAIT_W * min(s["gait"], GAIT_CAP) + min(s["gait"], s["stamina"], 0)
    return max(0, min(99, 70 + 6 * score))


def init_public(h, sire=None, dam=None):
    """Public estimate. Foals start from pedigree; founders from their (unseen) record."""
    h.name = _names.make(sire, dam, h.sex)                     # a racing name, often echoing the family
    h.last5, h.recent = [], []
    if sire and dam:                                           # pedigree: the parents at their best, not today
        h.est, h.est_sd = (peak_est(sire) + peak_est(dam)) / 2 - FOAL_DISCOUNT, 12.0
    else:
        h.est, h.est_sd = true_rating(h) + rng.gauss(0, 8), 8.0
    h.peak_est = h.est
    h.tier = public_tier(h)
    h.freshness = 70.0
    gap = 2.0 if sire and dam else 0.0                         # a foal has yet to be trained up
    h.developed = {t: h.ceiling(t) - gap for t in RACE_TRAITS}
    h.shape = {t: 0.0 for t in RACE_TRAITS}                    # what the trainer has made of it


def tier_of(est, current=None):
    """Band on the estimate, with hysteresis: a horse has to clear a line by 2 to change tier."""
    for cut, name in TIERS:
        if est >= cut + (2 if current and current != name and est > cut else 0):
            if current and name != current and abs(est - cut) < 2:
                return current
            return name
    return "D"


TIER_ORDER = "DCBAS"


def public_tier(h):
    """Tier against the horse's own age group: a top 2YO is an S among 2YOs. Remembers the
    best tier the horse was ever shown as, which is what a retired horse keeps."""
    t = tier_of(on_aged_scale(h.est, age_group(h)), getattr(h, "tier", None))
    if h.starts >= 10:                                    # a reputation is earned on the track, not guessed
        h.peak_tier = max(t, getattr(h, "peak_tier", "D"), key=TIER_ORDER.index)
    return t


def peak_est(h):
    """Career-best public estimate: what a horse's reputation rests on once it's aged."""
    return max(getattr(h, "peak_est", h.est), h.est)


def observe(h, implied, sd=OBS_SD):
    """Fold one piece of evidence into the estimate, precision-weighted."""
    w = h.est_sd ** 2 / (h.est_sd ** 2 + sd ** 2)
    h.est += w * (implied - h.est)
    h.peak_est = peak_est(h)
    h.est_sd = max(3.0, (h.est_sd ** -2 + sd ** -2) ** -0.5)
    h.tier = public_tier(h)


def drain(h):
    return max(0.6, min(1.4, 1 - 0.05 * h.potential["durability"]))


DEV_W = 0.12             # how much of the gap between developed and ceiling shows at the gate: a green 2YO (2 under
                         # everywhere) is ~6 rating, four lengths, short of its ceiling until work and racing close it
JOBS = {   # the owner's day sheet for a youngster: development step, shaping step, freshness cost. "stable" is the idle week
    "stable": (0.14, 0.0, 4), "jog": (0.2, 0.06, 4), "school": (0.2, 0.09, 8), "train": (0.5, 0.15, 15)}
YOUNG = 3                # the day sheet covers yearlings through this age; older horses are kept sound, not made


def current(self, track="mile"):
    """What the horse races with today: its genetic ceiling for its age, short by a share of what training hasn't
    developed yet, plus the shape its owner's hands have given it, dulled when tired. Being idle never hurts a horse."""
    shape = getattr(self, "shape", {})
    s = {t: self.ceiling(t) - DEV_W * max(0, self.ceiling(t) - self.developed[t]) + shape.get(t, 0.0) for t in RACE_TRAITS}
    if self.freshness < 50:
        for t in s:
            s[t] -= (50 - self.freshness) / 8
    return s


Horse.current = current


def plasticity(h):
    """How much a week of work can reshape a horse: young ones most, old ones little."""
    return {2: 2.0, 3: 1.5}.get(h.age, 0.5 if h.age >= 7 else 1.0)


def train(h, focus, hard, job=None):
    """A week's work. job names the day sheet's job (see JOBS); without one, hard/light is the old trainer's week."""
    tr = trainer_of(h)
    job = job or ("train" if hard else "jog")
    gain, shaping, cost = JOBS[job]
    gain *= 0.5 if tr.quirk == "slow to fit" else 1
    for t in RACE_TRAITS:
        step = gain if t == focus else gain / 5
        h.developed[t] = min(h.ceiling(t), h.developed[t] + step)
    # shaping: the focus comes up, the rest give a little. Genetics fix the total, the owner's hands the shape.
    boost = 2 if tr.perk == "good with 2YOs" and h.age <= 3 else 1
    d = min(shaping * plasticity(h) * boost, SHAPE_CAP - h.shape[focus])
    if d > 0 and focus in SHAPED:
        for t in SHAPED:
            h.shape[t] = max(-SHAPE_CAP, h.shape[t] + (d if t == focus else -d / (len(SHAPED) - 1)))
    h.freshness = max(0, h.freshness - cost * drain(h))


def rest(h):
    h.freshness = min(100, h.freshness + 25 / drain(h))


# --- owner decisions. Only public info: est/tier, record, freshness, developed stats.
def age_group(h):
    return str(h.age) if h.age <= 3 else "aged"


def entry(h):
    """Where the owner enters the horse: (group, sex, class name, purse, tag)."""
    group, sex = age_group(h), "F&M" if h.sex == "f" else "open"
    o = getattr(h, "order", None)
    if isinstance(o, tuple) and o[0] == "enter":              # an owner picked a race off the sheet
        clm = o[1].startswith("CLM")                          # claimers: one card per age class, colts and fillies together
        return ("all" if o[1] in ALL_AGES else group, "open" if o[1] in MIXED or clm else sex, o[1], o[2], o[3])
    if isinstance(o, tuple) and o[0] == "claim":              # a tag chosen: open entry, every age and sex together
        tag = clm_tag(o[1])
        return (group, "open", clm_name(tag), CLAIM_PURSE[tag], tag)
    name, _, purse, _ = next(c for c in CONDITIONS if c[1](h))
    if group == "aged" and o != "stay" and h.owner not in HUMAN and (h.id + DAY[0]) % 2 == 0:
        # half the weeks an owner also looks at the claiming ladder: the richest tag it can win at, if that pays more
        # than its own race. The tag is the risk it takes for the purse (decided by id and week, so the program drawn
        # at the start of the week is what races)
        tag = max((t for t, _, _ in CLAIMERS if CLASS_RATING[clm_name(t)] <= h.est + 3), default=None)
        if tag and CLAIM_PURSE[tag] > purse:
            return (group, "open", clm_name(tag), CLAIM_PURSE[tag], tag)
    if name in ALL_AGES:
        return ("all", sex, name, purse, 0)                   # the top classes are for every age
    if name in MIXED:
        return (group, "open", name, purse, 0)
    if group == "aged" and o != "stay" and h.owner not in HUMAN \
            and h.est < CLASS_RATING[name] - DROP_MARGIN:          # can't win here: find a tag
        tag = max((t for t, _, _ in CLAIMERS if CLASS_RATING[clm_name(t)] <= h.est + 3),
                  default=CLAIMERS[0][0])
        return (group, "open", clm_name(tag), CLAIM_PURSE[tag], tag)
    return (group, sex, name, purse, 0)


# --- trainers. An owner hires one per barn; the trainer makes the week's call for every horse.
def _school(h, focus):
    """Shape a young horse on an off week; an aged horse just rests (shaping it costs more starts than it returns)."""
    return ("train", focus, True) if h.age <= 3 and h.freshness >= 35 and h.shape[focus] < SHAPE_CAP else "rest"


def _journeyman(h):
    h.ship = None
    if h.freshness >= 50:
        return "race"
    if h.freshness >= 35:
        gap = {t: h.ceiling(t) - h.developed[t] for t in RACE_TRAITS}
        focus = max(gap, key=gap.get)
        return ("train", focus, gap[focus] > 1.0)
    return "rest"


def _patient(h):
    h.ship = None
    return "race" if h.freshness >= 65 else _school(h, "stamina")


def _grinder(h):
    h.ship = None
    return "race" if h.freshness >= 40 else "rest"


def _speed(h):
    h.ship = "half"
    return "race" if h.freshness >= 50 else _school(h, "early_speed")


def _closer(h):
    h.ship = "mile"
    return "race" if h.freshness >= 50 else _school(h, "late_speed")


def _horseman(h):
    cur = h.current()
    closer = cur["late_speed"] >= cur["early_speed"]
    h.ship = "mile" if closer else "half"
    return "race" if h.freshness >= 50 else _school(h, "late_speed" if closer else "early_speed")


STYLES = {   # name: (what the owner is told, the policy)
    "journeyman": ("races them when fresh, works on whatever's lacking", _journeyman),
    "patient": ("never races a tired horse; builds stamina into the young ones", _patient),
    "grinder": ("races every week he can; no break work", _grinder),
    "speed": ("ships to the half-mile; makes leavers of the young ones", _speed),
    "closer": ("ships to the mile; teaches the young ones to finish", _closer),
    "horseman": ("reads each horse: ships it where it fits, builds on its strength", _horseman),
    "neutral": ("races a horse when it's fit, rests it when it isn't", lambda h: "race" if h.freshness >= 50 else "rest"),
}
PERKS = {   # what the owner is told -> effect, applied in plan()/train()/current()
    "good with 2YOs": "break work takes twice as well on 2- and 3-year-olds",
    "fixes breakers": "works gait into a bad-gaited horse before anything else",
    "half-mile man": "ships everything to the half; horses leave sharper there",
    "miler": "ships everything to the mile; horses finish better there",
    "keeps them sound": "horses lose less freshness to a start",
    "none": "",
}
QUIRKS = {
    "overraces": "sends a horse that's only 40 fresh",
    "no fillies": "won't take a filly or mare",
    "slow to fit": "a horse takes twice as long to get racing fit",
    "dear": "takes 5% more of the purse than the going rate",
    "vague": "his reports are rough: your stat bars are a pip off either way",
    "none": "",
}
CUT = 0.10          # going trainer's cut of purses; a full trainer asks up to double, an empty one less
NAMES = ["Alder", "Brisco", "Cullen", "Dyer", "Enright", "Fallon", "Garrity", "Hobbs", "Ingram", "Jessup",
         "Keane", "Lavery", "Mahon", "Nolan", "Orr", "Pruett", "Quigley", "Rusk", "Sayer", "Toole",
         "Upton", "Vance", "Wrenn", "Yates", "Zell", "Abbot", "Beck", "Coyle", "Dunne", "Ewing"]
_tnames = count()


class Trainer:
    """A trainer: a public style, perk and quirk, a hidden skill the record reveals over the
    years, a fee, and only so many stalls. Owners hire one per horse (a barn has a default)."""

    def __init__(self, style=None, skill=None, stalls=None, perk=None, quirk=None):
        i = next(_tnames)
        self.name = NAMES[i % len(NAMES)] + ("" if i < len(NAMES) else f"{i // len(NAMES) + 1}")   # Keane, Keane2, ...
        self.style = style or rng.choice(list(STYLES))
        self.perk = perk or rng.choice(list(PERKS))
        self.quirk = quirk or rng.choice(list(QUIRKS))
        self.skill = skill if skill is not None else max(0.7, min(1.3, rng.gauss(1.0, 0.12)))
        self.stalls = stalls or rng.choice([15, 25, 35, 50])   # 30 trainers ~ 940 stalls for a 600-900 horse circuit
        self.cut = CUT + (0.05 if self.quirk == "dear" else 0)
        self.years = 0
        self.starts = self.wins = self.earnings = 0
        self.horses = 0                                    # stalls in use (kept by assign())

    def takes(self, h):
        return self.horses < self.stalls and not (self.quirk == "no fillies" and h.sex == "f")

    def plan(self, h):
        order = STYLES[self.style][1](h)
        if self.perk in ("half-mile man", "miler"):
            h.ship = "half" if self.perk == "half-mile man" else "mile"
        if self.perk == "fixes breakers" and isinstance(order, tuple) and order[0] == "train" \
                and h.current()["gait"] < 0 and h.shape["gait"] < SHAPE_CAP:
            order = ("train", "gait", order[2])
        if self.quirk == "overraces" and order != "race" and h.freshness >= 40:
            order = "race"
        return order

    def edge(self, track):
        """Hidden: what a good hand is worth on the clock, per trait (skill 1.2 ~ a length a mile).
        More on their own track."""
        e = 1.5 * (self.skill - 1)
        if (self.perk, track) in (("half-mile man", "half"), ("miler", "mile")):
            e += 0.15
        return e

    def record(self):
        return f"{self.starts}-{self.wins}  ${self.earnings / max(1, self.starts):,.0f}/start"


HOUSE = Trainer("journeyman", 0.9, 10 ** 6, "none", "none")  # the track's public stable: always room, free
HOUSE.name, HOUSE.cut = "house", 0.0
TRAINING = Trainer("neutral", 1.0, 10 ** 9, "none", "none")  # the one stable every horse is with: perfect, flat fee
TRAINING.name, TRAINING.cut = "stable", CUT
ROSTER = []         # trainers for hire
BARN_TRAINER = {}   # owner -> Trainer: where a barn's new horses go
HUMAN = set()       # barns run by people: their trainer never risks a horse in a claimer unasked


def assign(h, t):
    """Trainers are off: every horse stays with the one neutral stable (see trainer_of), so a move changes nothing."""
    h.trainer = TRAINING
    return True


def trainer_of(h):
    """One neutral stable trains every horse, perfectly, for the going fee: no styles, perks, quirks or skill.
    shortcut: the trainer market is off for now (ROSTER etc. are kept so old saves load); bring it back here."""
    h.trainer = TRAINING
    return TRAINING


def new_roster(n=30):
    ROSTER.clear()
    ROSTER.extend(Trainer() for _ in range(n))
    for t in ROSTER:
        t.years = rng.randint(0, 20)
    return ROSTER


def trainers_year(horses):
    """Two or three trainers retire each year and as many new ones hang out a shingle.
    Cuts follow demand. Barns whose trainer left fall back to the house until they rehire."""
    for t in ROSTER:
        t.years += 1
        if t.horses >= 0.9 * t.stalls:
            t.cut = min(2 * CUT, t.cut + 0.02)
        elif t.horses < 0.5 * t.stalls:
            t.cut = max(CUT / 2, t.cut - 0.01)
    leaving = sorted(ROSTER, key=lambda t: -t.years)[:rng.randint(2, 3)]
    for t in leaving:
        ROSTER.remove(t)
        for h in horses:
            if getattr(h, "trainer", None) is t:
                h.trainer = None
        for o, bt in list(BARN_TRAINER.items()):
            if bt is t:
                BARN_TRAINER[o] = HOUSE
    ROSTER.extend(Trainer() for _ in leaving)
    for h in horses:
        trainer_of(h)
    return leaving


def eligible_races(h):
    """The entry sheet: every condition this horse qualifies for tonight, on either track,
    and every claimer, which are open entry. (name, purse, tag, track)."""
    if h.retired:
        return []
    group = age_group(h)
    out = []
    for name, ok, purse, _ in CONDITIONS:
        if ok(h):
            out += [(name, purse, 0, t) for t in ("mile", "half")]
    out += [(clm_name(tag), CLAIM_PURSE[tag], tag, t) for tag, _, _ in CLAIMERS for t in ("mile", "half")]
    return out


def offerings(h):
    """The entry sheet by track: (venue, name, base purse, purse there, tag, size) for every race this horse can
    enter tonight at every track that cards it. The base purse is what the entry carries; the track sets the pay."""
    return [(v, name, purse, venue_purse(v, purse), tag, track)
            for name, purse, tag, track in eligible_races(h) for v in hosts(name, track)]


def growth_type(h):
    """The shape of a career, in the words a trainer would use. From the hidden genes, so only
    shown to an owner once the trainer has seen the horse enough."""
    p = h.peak_age
    holds = 2.718 ** (-0.4 * h.potential["longevity"]) < 0.5
    if holds:
        return "sustained"
    return "early" if p <= 3 else "late" if p >= 7 else "standard"


# The mile rating: a horse's rating shown as the mile it paces, one absolute scale for every horse at every age
# ("a 1:47.2 horse"). Fitted on this circuit's results: rating -> median recent mile time (r = 0.94, +/-1.5 s),
# and true ability by age -> rating (r = 0.89) for the trainer's projection. Re-fit if the clock or purses change.
MILE_FIT = 128.63, -0.2857        # seconds = a + b * est
ABILITY_FIT = 53.58, 3.121        # est ~= a + b * race_score(age)


def mile_secs(est):
    """The rating as seconds for a mile, leaning against the same floor as the race clock."""
    x = MILE_FIT[0] + MILE_FIT[1] * est                          # fitted on the old clock's linear part:
    at, k, _ = sim.CLOCK_OLD
    return sim.clock(sim.CLOCK_REF + (x - at) / k)               # back to race seconds, then onto today's clock


def mile_rating(h):
    """The horse's current mile rating, e.g. '1:47.8'."""
    return mile_time(mile_secs(h.est))


def growth_curve(h):
    """The trainer's projection of a horse's career: its true ceiling by age, on the public
    scale, with a little of the trainer's own error. Ages 2 to 12."""
    err = (h.id % 7 - 3) * 1.5
    return [(a, round(70 + 6 * h.race_score(a) + err)) for a in range(2, 13)]


def growth_secs(h):
    """The trainer's projection as a mile rating by age (seconds), on the same scale as mile_rating: the horse's
    true ability at each age, with the same small trainer's error as growth_curve."""
    err = (h.id % 7 - 3) * 0.4
    return [(a, mile_secs(ABILITY_FIT[0] + ABILITY_FIT[1] * h.race_score(a)) + err) for a in range(2, 13)]


def plan(h):
    """One decision per horse per week. The trainer conditions the horse; the owner enters it.
    An AI owner's trainer enters for them. A human barn's horse races only on an order:
    nothing is entered without a visit."""
    if h.retired:
        return "retired"
    if getattr(h, "order", None) == "retire":
        retire(h)
        return "retired"
    if getattr(h, "order", None) and h.order != "rest":
        return h.order
    job = getattr(h, "job", None)                              # the owner's day sheet: this week's job for a youngster
    if job and job[0] == DAY[0] and h.age <= YOUNG:
        return "rest" if job[1] == "out" else ("train", "gait" if job[1] == "school" else job[2], job[1] == "train", job[1])
    p = trainer_of(h).plan(h)
    if h.owner in HUMAN and p == "race":
        p = "rest"                                             # fresh, fit, and not entered
    if p == "rest" and h.age <= YOUNG and h.freshness >= 35:   # the stable jogs an idle youngster: development, no shaping
        gap = {t: h.ceiling(t) - h.developed[t] for t in RACE_TRAITS}
        return ("train", max(gap, key=gap.get), False, "stable")
    return p


CLAIMS = {}              # horse id -> the barn that has a claim in on it tonight (a player's claim, made off the program)


def tonic_fee(h, fee):
    """Hook: economy pays the vet for a Post Time Tonic at post time. False when the barn can't cover it."""
    return True


def player_claim(h, buyer, tag):
    """Hook: economy.py pays for a player's claim. Without an economy the horse just changes hands."""
    h.owner = buyer


def draw_claimers(horses, ai):
    """Draw tonight's claiming cards as the week opens, so the program can be posted before post time. Every AI
    horse its trainer would race this week and whose owner would drop it into a claimer is entered now and held
    to it (h.drawn), with its track; anything else is decided on the night, as before."""
    for h in horses:
        if h.owner not in ai or h.retired or getattr(h, "order", None):
            continue
        if plan(h) != "race":
            continue
        group, sex, name, purse, tag = entry(h)
        if tag:
            h.order, h.drawn = ("claim", tag), True
            h.ship = getattr(h, "ship", None) or rng.choice(("mile", "half"))
    # the race office fills each claimer now rather than on the night, so the program shows a full field: fit, idle
    # AI horses of the same age and sex that belong at that level (rated no better than the class + 15)
    cards = claiming_cards(horses)
    for key in list(cards):                                   # a class drawn on both tracks goes to the fuller card
        twin = next((k for k in cards if k != key and k[:5] == key[:5]), None)
        if twin and key in cards and len(cards[key]) <= len(cards[twin]):
            for h in cards.pop(key):
                h.ship = twin[5]
                cards[twin].append(h)
    for (group, sex, name, purse, tag, track), field in cards.items():
        short = FIELD[track] - len(field)
        if short <= 0:
            continue
        pool = [h for h in horses if h.owner in ai and not h.retired and not getattr(h, "order", None) and h.freshness >= 50
                and age_group(h) == group and (sex == "open" or ("F&M" if h.sex == "f" else "open") == sex) and h.est <= CLASS_RATING[name] + 15]
        rng.shuffle(pool)
        for h in pool[:short]:
            h.order, h.drawn, h.ship = ("claim", tag), True, track


def claiming_cards(horses):
    """Tonight's claiming races as drawn: {(group, sex, name, purse, tag, track): [horses]}."""
    cards = {}
    for h in horses:
        o = getattr(h, "order", None)
        if isinstance(o, tuple) and o[0] == "claim" and not h.retired:
            cards.setdefault(entry(h) + (getattr(h, "ship", None) or "mile",), []).append(h)
    return cards


def claim_decision(h, tag_rating):
    """Another owner buys a horse that looks better than its tag, from public info only."""
    return h.est > tag_rating + 5 and rng.random() < 0.5


def claimant(h, tag):
    """Who takes the horse. Without an economy it's just 'someone else'; economy.py pays for it."""
    return h.owner + 1


def week_passes(h):
    """The week between cards restores some freshness by itself; durable horses can race weekly.
    Horses change with age, so last month's evidence is worth a little less each week."""
    h.freshness = min(100, h.freshness + 25 / drain(h))   # avg horse: race ~8 weeks, then needs one off
    h.est_sd = min(12.0, (h.est_sd ** 2 + 1.0) ** 0.5)


def age_up(horses):
    """Everyone ages a year; 15-year-olds retire; retired stock leaves at 20; the roster turns over.
    The public rating at the end of each season is kept: that's the horse's visible history."""
    for h in horses:
        if not h.retired:
            h.history = getattr(h, "history", []) + [(h.age, round(on_aged_scale(h.est, age_group(h))))]
        if not getattr(h, "ageless", False):                  # the owner's giga horse stays a 3-year-old for good
            h.age += 1
        if h.age >= RETIRE_AGE and not h.retired:
            retire(h)
    horses = [h for h in horses if h.age < BREEDING_UNTIL]
    trainers_year(horses)
    return horses


def foal(sire, dam):
    """shortcut: foals appear as 2YOs the year they are conceived, upgrade with gestation + yearling time."""
    f = breed(sire, dam)
    f.owner = f.breeder = dam.owner
    init_public(f, sire, dam)
    return f


def new_year(horses, crop=150):
    """Age up, then a 2YO crop. AI breeders pick sires by public estimate, so the population
    improves under selection. economy.py replaces this with a stud book that charges fees."""
    horses = age_up(horses)
    ai_retire(horses, {h.owner for h in horses})
    sires = sorted((h for h in horses if h.sex == "m" and h.retired), key=lambda h: -peak_est(h))[:20]
    dams = [h for h in horses if h.sex == "f" and h.retired]
    for _ in range(crop):
        if sires and dams:
            horses.append(foal(rng.choice(sires), rng.choice(dams)))
    return horses


def ai_retire(horses, ai):
    """AI owners retire a horse worth breeding once it is past its best: aged and rated well
    under its career peak, or simply old; mares a little sooner, to get foals from them.
    (Horses not worth breeding are the economy's to cull.)"""
    for h in horses:
        if h.owner not in ai or h.retired or peak_est(h) < 58:
            continue
        # a good horse races on: real veterans carry the older divisions into their 8s and 9s. Retire one that has
        # clearly lost it (well off its peak at 7+), a mare from 9 for her foals, and anyone at 12.
        still_good = on_aged_scale(h.est, age_group(h)) >= 75
        faded = h.est < peak_est(h) - 15
        if h.age >= 12 or (h.sex == "f" and h.age >= 9) or (h.age >= 7 and faded and not still_good):
            retire(h)



STUDS_AT_START = 12


def seed_studs(horses, ai, n=STUDS_AT_START):
    """A circuit can't breed without sires. Mares retire at 7, stallions only once they've faded,
    so a new circuit has broodmares and no stallions. Stand the best aged AI horses until n do."""
    have = sum(h.retired and h.sex == "m" for h in horses)
    pool = sorted((h for h in horses if h.owner in ai and not h.retired and h.sex == "m" and h.age >= 6),
                  key=peak_est, reverse=True)
    for h in pool[:max(0, n - have)]:
        retire(h)


def mile_time(t):
    """A mile in racing notation, timed in fifths of a second like an official chart: 108.7 s is 1:48.6."""
    t = round(t * 5) / 5
    return f"{int(t // 60)}:{t % 60:04.1f}"


def record_result(h, name, track, place, purse, field_est, size=None):
    """Everything one start does to a horse and its connections: record, purse, cuts,
    freshness, a little development, the trainer's book, and the public estimate."""
    assert not h.retired, "a retired horse never races"
    won = purse * PURSE_SPLIT[place] if place < len(PURSE_SPLIT) else 0
    h.last = (name, track, place + 1, h.last_time, won)
    cur = h.current(track)
    finish = ("held on" if "lead" in h.trip else "kicked home late" if "behind" in h.trip and cur["late_speed"] > 0
              else "ground it out") if place < 3 else ("faded" if "broke" not in h.trip and "behind" not in h.trip
                                                       else "never a factor" if place > 4 else "closed some ground")
    chart = f"{name} {track}: {h.trip}, {finish}; {place + 1}th of {size or FIELD[track]} in {mile_time(h.last_time)}" \
        .replace("1th", "1st").replace("2th", "2nd").replace("3th", "3rd")
    h.form = (getattr(h, "form", []) + [chart])[-10:]
    h.results = (getattr(h, "results", []) + [{"day": DAY[0], "race": name, "track": track, "place": place + 1, "time": h.last_time,
                                                 "won": won, "trip": h.trip, "finish": finish, "purse": purse, "size": size or FIELD[track]}])[-30:]
    h.best = min(getattr(h, "best", 999), h.last_time)
    yr = getattr(h, "seasons", None)                          # the season ledger: {year: [starts, wins, places, shows, earnings, best]}
    if yr is None:
        yr = h.seasons = {}
    row = yr.setdefault(year_of(DAY[0]), [0, 0, 0, 0, 0.0, 999.0])
    row[0] += 1; row[1] += place == 0; row[2] += place == 1; row[3] += place == 2; row[4] += won
    row[5] = min(row[5], h.last_time)
    h.starts += 1
    h.wins += place == 0
    h.places += place == 1
    h.shows += place == 2
    if h.last_time < getattr(h, "best", 999):
        h.best_track = track
    h.last5 = (h.last5 + [won])[-5:]
    h.recent = (h.recent + [place == 0])[-10:]
    tr = trainer_of(h)                            # the trainer's public record
    tr.starts, tr.wins, tr.earnings = tr.starts + 1, tr.wins + (place == 0), tr.earnings + won
    h.costs += (DRIVER + tr.cut) * won            # only ever a share of what was won
    h.freshness = max(0, h.freshness - 30 * drain(h) * (0.85 if tr.perk == "keeps them sound" else 1))
    for t in RACE_TRAITS:                         # racing develops a horse too
        h.developed[t] = min(h.ceiling(t), h.developed[t] + 0.05)
    h.peak_dev = {t: max(getattr(h, "peak_dev", h.developed)[t], min(h.developed[t], h.ceiling(t))) for t in RACE_TRAITS}
    h.earnings += won
    observe(h, field_est + ((size or FIELD[track]) / 2 - 0.5 - place) * 4)   # mid-field finish reads as the field's level
    a, b, sd = TIME_FIT
    observe(h, a[track] + b * getattr(h, "raw_time", h.last_time), sd)    # the clock anchors the whole scale


def public_stats(horses):
    """What the public scale is tonight: estimate and stat spreads per age group."""
    for g in GROUP_STATS:
        ests = [h.est for h in horses if age_group(h) == g and not h.retired]   # racers only: retired stock is locked at its peak and would drag the scale up
        if len(ests) > 8:
            GROUP_STATS[g] = (st.mean(ests), max(8.0, st.pstdev(ests)))   # a crop that all looks alike isn't all S


DRIVER_STATS = {}   # driver -> {"starts", "wins", "earned", "seasons": {year: [starts, wins, earned]}}


def driver_prefs(owner):
    """Hook: a player barn's top three drivers, best first (the app supplies it). Computer barns have none."""
    return []


def assign_drivers(field):
    """Who drives what tonight, one driver to a horse in a race. Player barns first, the better horse (by rating) first,
    each getting the first of its barn's top three still free; then everyone else from the drivers left over."""
    import drivers as _drivers
    taken, out = set(), {}
    for h in sorted((h for h in field if h.owner in HUMAN), key=lambda h: -h.est):
        name = next((n for n in driver_prefs(h.owner) if n in _drivers.STYLE and n not in taken), None)
        if name:
            out[h.id] = name
            taken.add(name)
    free = [n for n in _drivers.NAMES if n not in taken]
    rng.shuffle(free)
    for h in field:
        if h.id not in out:
            out[h.id] = free.pop()
    return out


def drive(field, names, track):
    """Put the drivers up: each horse carries its driver's small edge into the race."""
    import drivers as _drivers
    for h in field:
        h.driver = names.get(h.id) or names.setdefault(h.id, assign_drivers([h])[h.id])
        h.drive_on = _drivers.lift(h.driver, track)


def drove(order, rows, year):
    """After the race: the drivers' records, the driver on each result, and his colors on the replay."""
    import drivers as _drivers
    for place, h in enumerate(order):
        name, won = getattr(h, "driver", None), h.results[-1]["won"]
        h.drive_on = None
        if not name:
            continue
        d = DRIVER_STATS.setdefault(name, {"starts": 0, "wins": 0, "earned": 0.0, "seasons": {}})
        row = d["seasons"].setdefault(year, [0, 0, 0.0])
        d["starts"] += 1; d["wins"] += place == 0; d["earned"] += won
        row[0] += 1; row[1] += place == 0; row[2] += won
        h.results[-1]["driver"] = name
    for row in rows or []:
        h = next((x for x in order if x.name == row["name"]), None)
        if h and getattr(h, "driver", None):
            row["driver"], row["silks"] = h.driver, list(_drivers.SILKS[h.driver])


TONIC_FEE = 0.02    # the vet's fee for giving a Post Time Tonic: a share of that race's purse
CARD = {}           # tonight's drawn program: {"day", "races": [{key, i, v, field (in post order), odds}]}


RACING = ("race", "stay")


VISITOR = -1           # the owner of a horse shipped in for the night (no barn here)
MIN_FIELD = 8          # every race goes to the gate with at least this many
SHIPPERS = ("Cedar Downs", "Millbrook Raceway", "Ashford Downs", "Pine Hollow", "Riverbend Downs", "Hartwell Fair",
            "Stony Creek", "Willow Run")   # out-of-town tracks (invented) a visiting horse ships in from
_visitor_ids = count(-1, -1)


def visitor(key, field, everyone):
    """A horse shipped in for one night to fill a short field: a copy of a horse of the same age and sex whose rating
    sits nearest the class, under a new name and no owner here. It races, takes its purse home and is gone."""
    group, sex, name, purse, tag, track = key
    level = CLASS_RATING.get(name) or (st.mean(h.est for h in field) if field else 60)
    pool = [h for h in everyone if not h.retired and (group == "all" or age_group(h) == group) and (sex != "F&M" or h.sex == "f")]         or [h for h in everyone if not h.retired]
    t = min(rng.sample(pool, min(30, len(pool))), key=lambda h: abs(h.est - level))
    v = copy.copy(t)                                              # shallow: a deep copy would drag the whole pedigree along
    for k, x in vars(v).items():
        if isinstance(x, (dict, list, set)):
            setattr(v, k, copy.copy(x))                           # its own record and development, never the original's
    v.id, v.owner, v.visitor = next(_visitor_ids), VISITOR, rng.choice(SHIPPERS)
    v.name = _names.make(sex=v.sex); _names.USED.discard(v.name)   # a visitor's name isn't kept off the book
    v.sire = v.dam = v.breeder = None
    v.order = v.tonic = v.tonic_on = v.ship = None
    v.freshness, v.results, v.form, v.seasons = 100, [], [], {}
    return v


def top_up(key, field, idle_all, drafted):
    """No short fields: fit AI horses of the same age group come off the bench (any class, but never into a top
    class), then visitors ship in for whatever's still short."""
    group, sex, name, purse, tag, track = key
    if name not in ALL_AGES:
        for h in idle_all:
            if len(field) >= MIN_FIELD:
                break
            if h.id not in drafted and (group == "all" or age_group(h) == group) and (sex != "F&M" or h.sex == "f"):
                field.append(h); drafted.add(h.id)
    everyone = idle_all or field
    while len(field) < MIN_FIELD:
        field.append(visitor(key, field, everyone))


def draw_card(day, horses, skip=()):
    """The draw for the card of `day`: every entry is carded, short fields are filled, splits are made and posts drawn.
    Done right after the previous card runs, so the program is up all day; race_day then runs exactly these fields.
    Each horse's plan for the night is kept on it (h.wk) and the week passes for the ones not racing once the card
    has run (pass_week). An owner's entry is consumed here: the horse is on the program now. skip: horses held
    for the night's stakes."""
    DAY[0] = day
    public_stats(horses)
    cards, plans = {}, {}
    for h in horses:
        p = plans[h.id] = h.wk = "stakes" if h.id in skip else plan(h)
        if p in RACING or (isinstance(p, tuple) and p[0] in ("claim", "enter")):
            track = p[4] if isinstance(p, tuple) and p[0] == "enter" else \
                getattr(h, "ship", None) or rng.choice(("mile", "half"))   # no preference: whichever is nearer
            cards.setdefault(entry(h) + (track,), []).append(h)
    # The racing office fills short fields with AI horses that were going to sit the week out,
    # so an entry always gets a race. Idle, fit, eligible, and not a human's horse.
    idle_all = [h for h in horses if h.owner not in HUMAN
                and plans[h.id] not in ("race", "stay", "stakes", "retired", "sell")
                and not (isinstance(plans[h.id], tuple) and plans[h.id][0] in ("claim", "enter"))]
    rng.shuffle(idle_all)
    idle_all = [h for h in idle_all if h.freshness >= 35]   # never a tired horse: a filler must be fit to race
    idle = [h for h in idle_all if h.freshness >= 50]       # and the first picks are fresh
    for key in list(cards):                                   # no track of this size cards the class: ship to the other size
        if not hosts(key[2], key[5]):
            other = key[:5] + ("half" if key[5] == "mile" else "mile",)
            cards.setdefault(other, []).extend(cards.pop(key))
    # a class short on one track and entered on the other: everyone ships to the fuller card
    for base in {k[:5] for k in cards}:
        keys = [k for k in cards if k[:5] == base]
        if len(keys) == 2:
            a, b = sorted(keys, key=lambda k: len(cards[k]))
            if len(cards[a]) < FIELD[a[5]]:
                cards[b].extend(cards.pop(a))

    def fits(h, key, strict):
        group, sex, name, purse, tag, track = key
        if (group != "all" and age_group(h) != group) or (strict < 2 and name not in MIXED and not name.startswith("CLM") and ("F&M" if h.sex == "f" else "open") != sex):
            return False
        if strict:
            return True
        return (name.startswith("CLM") and h.est <= CLASS_RATING[name] + 8
                or any(n == name and ok(h) for n, ok, _, _ in CONDITIONS))

    drafted = set()
    for key, entries in cards.items():
        asked = {wanted(h) for h in entries} & {v["id"] for v in hosts(key[2], key[5])}
        short = max((-len(entries)) % FIELD[key[5]], len(asked) * MIN_FIELD - len(entries))
        for strict in ((0,) if key[2] in ALL_AGES else (0, 1, 2)):   # top classes take only horses that meet the condition; below, same group+sex, then same group
            for h in (idle if strict < 2 else idle_all):
                if short == 0:
                    break
                if h.id not in drafted and fits(h, key, strict):
                    entries.append(h)
                    drafted.add(h.id)
                    short -= 1
    # a top class runs short rather than padded, but below TOP_MIN it folds into the class under it (then the <2 rule)
    for name, below in (("Invitational", "Preferred"), ("Preferred", "Open")):
        for key in [k for k in cards if k[2] == name and len(cards[k]) < TOP_MIN]:
            purse = next(c[2] for c in CONDITIONS if c[0] == below)
            cards.setdefault((key[0], key[1], below, purse, 0, key[5]), []).extend(cards.pop(key))
    # still alone: the office rewrites the condition and the horse races in the fullest card
    # of its age group tonight, whatever the class
    for key in [k for k, v in cards.items() if len(v) < 2]:
        others = [k for k in cards if k != key and k[0] == key[0] and len(cards[k]) >= 2] \
            or [k for k in cards if k != key and len(cards[k]) >= 2]   # nobody its age racing: any card
        if others:
            cards[max(others, key=lambda k: len(cards[k]))].extend(cards.pop(key))
    races = []
    for key, entries in cards.items():
        group, sex, name, purse, tag, track = key
        for i, (v, field) in enumerate(make_splits(name, track, entries)):   # balanced, by track, stablemates apart
            top_up(key, field, idle_all, drafted)
            if len(field) < 2:                               # a walkover isn't a race (can't happen once topped up)
                UNFILLED.append((group, sex, name, track))
                for h in field:
                    rest(h)
                    h.last = f"entered {race_title(group, name)}, nobody else came; rested"
                continue
            rng.shuffle(field)                               # the post-position draw
            for post, h in enumerate(field, 1):
                h.post = post
                if h.owner in HUMAN and getattr(h, "order", None) not in (None, "sell", "retire", "rest"):
                    h.order = h.ship = None                  # the entry is used: it's on the program (tomorrow's is a new one)
            races.append({"key": key, "i": i, "v": v, "field": field, "odds": tote_odds(field), "drivers": assign_drivers(field)})
    for h in horses:
        if h.id in drafted:
            h.wk = "drafted"                                  # a filler: it races, no week's work for it
    post_times(races)
    CARD.clear()
    CARD.update(day=day, races=races)
    return CARD


def pass_week(day, horses, raced):
    """The week goes by for everyone once the card has run: freshness comes back, and the horses that didn't race
    rest or do the week's work by the plan kept at the draw (h.wk), or the owner's day sheet for a youngster."""
    DAY[0] = day
    for h in horses:
        week_passes(h)
        if h.retired or h.id in raced or getattr(h, "order", None) == "stakes":
            continue
        p = getattr(h, "wk", None)
        job = getattr(h, "job", None)                          # the day sheet beats the plan: this week's job for a youngster
        if job and job[0] == day and h.age <= YOUNG:
            p = "rest" if job[1] == "out" else ("train", "gait" if job[1] == "school" else job[2], job[1] == "train", job[1])
        if p is None:
            p = plan(h)                                        # a card drawn before plans were kept (the first night)
        if p == "drafted" or p in RACING or isinstance(p, tuple) and p[0] in ("claim", "enter"):
            continue                                           # it was carded and its race came apart: already rested
        h.last = None
        if p in ("rest", "sell"):                             # a listed horse sits while it's sold
            rest(h)
            h.last = "rested" if p == "rest" else "listed for sale"
            if p == "rest" and h.owner in HUMAN and not getattr(h, "order", None) and h.freshness >= 50:
                h.last = "not entered; rested"
        elif isinstance(p, tuple) and p[0] == "train":
            job = p[3] if len(p) > 3 else None
            train(h, p[1], p[2], job)
            h.last = {"stable": "jogged by the stable", "jog": f"jogged, {p[1].replace('_', ' ')}", "school": "break work on its gait",
                      "out": "turned out"}.get(job, f"trained {p[1].replace('_', ' ')}{' hard' if p[2] else ''}")
        h.wk = None


POST_FROM, POST_SPAN = 19 * 60, 230   # first post 7:00 PM New York time; each track's last post 230 minutes later (10:50)


def post_times(races):
    """Each track runs its own card through the evening: its races in program order, spaced evenly from first post
    to last. r["post"] is minutes after midnight, New York time."""
    by = {}
    for r in sorted(races, key=lambda r: (r["key"][5], str(r["key"][0]), -r["key"][3])):
        by.setdefault(r["v"]["name"], []).append(r)
    for rs in by.values():
        for k, r in enumerate(rs):
            r["post"] = POST_FROM + (round(k * POST_SPAN / (len(rs) - 1)) if len(rs) > 1 else POST_SPAN // 2)


def run_race(r, alive, log):
    """One race off at its post time: the vet, the drive, the race, the result, the story and the claims."""
    (group, sex, name, purse, tag, track), i, v = r["key"], r["i"], r["v"]
    taken_ids, raced = CARD.setdefault("taken", {}), CARD.setdefault("raced", set())
    field = [h for h in r["field"] if (id(h) in alive or getattr(h, "visitor", None)) and not h.retired and getattr(h, "order", None) != "stakes"]
    if len(field) < 2:                                   # lost its field since the draw (a stake, a sale): no race
        for h in field:
            rest(h)
            h.last = f"entered {race_title(group, name)}, the field came apart; rested"
        r["done"] = True
        return
    if r.get("settling"):                               # a retry after a failure partway through settling: a result is never
        r["done"] = True                                # applied twice (starts, purses, claims); this race stays as far as it got
        return
    vpurse = venue_purse(v, purse)
    drive(field, r.setdefault("drivers", {}), track)
    order = (outcome.race if ENGINE == "outcome" else race)(field, track, v.get("passing", False))
    story = _story.build(order, track, passing=v.get("passing", False))   # everything that can fail, before any result is written
    line = tote_odds(field)
    r["settling"] = True                                # from here the result is being applied: no retry may apply it again
    for h in field:
        h.tonic_on = None
    field_est = st.mean(h.est for h in field)        # who you beat, not where you ran
    if name in CLASS_RATING:                          # a card drawn before a class was retired still runs
        CLASS_RATING[name] += 0.1 * (field_est - CLASS_RATING[name])   # what the class really is
    base = f"{DAY[0]}-{v['id']}-{track}-{name.replace('$', '').replace('&', 'and')}"   # plain letters: it travels in a URL
    rid = f"{base}-{taken_ids.setdefault(base, -1) + 1}"             # the same class for two age groups gets its own id
    taken_ids[base] += 1
    for place, h in enumerate(order):
        record_result(h, race_title(group, name), track, place, vpurse, field_est, len(field))
        h.results[-1]["race_id"] = rid
        h.results[-1]["venue"] = v["name"]
        raced.add(h.id)
    STORIES[rid] = dict(story, id=rid, name=race_title(group, name), purse=vpurse, day=DAY[0], venue=v["name"],
                        passing=v.get("passing", False))
    STORIES[rid]["records"] = set_records(v["id"], STORIES[rid]["quarters"][1:])   # each track keeps its own records
    drove(order, STORIES[rid]["horses"], year_of(DAY[0]))
    for row, h in zip(STORIES[rid]["horses"], order):              # the story is in finishing order, like order
        row["odds"] = "%d-%d" % line[h.id]
    for old in list(STORIES)[:-400]:
        del STORIES[old]
    if tag:
        for h in field:
            h.ran_claimer = 1
        taken = set()
        for h in field:                                    # a claim made off the program is binding: the horse
            if h.id in CLAIMS and CLAIMS[h.id] != h.owner:  # is the claimant's once it races, whatever the result
                player_claim(h, CLAIMS.pop(h.id), tag)
                taken.add(h.id)
        for h in [x for x in order[:3] if x.id not in taken and not getattr(x, "visitor", None)]:   # one claim per horse per race; a visitor ships home
            if claim_decision(h, CLASS_RATING[name]) and (to := claimant(h, tag)) != h.owner:
                h.owner, h.claimed, h.order = to, h.claimed + 1, None
    log.append((group, sex, name, track, field, order[0]))
    r["done"] = True


def run_due(horses, minute, log=None):
    """Every race on tonight's card whose post time has come: run now, in post order. Returns how many went off."""
    alive = {id(h) for h in horses}
    due = sorted((r for r in CARD.get("races", []) if not r.get("done") and r.get("post", 0) <= minute), key=lambda r: r["post"])
    for r in due:
        run_race(r, alive, [] if log is None else log)
    return len(due)


def race_day(day, horses, log):
    """The close of race night: any race that hasn't gone off yet runs now (all of them, when the clock isn't running
    races live), then the week goes by for everyone. The card is drawn now if it wasn't."""
    if CARD.get("day") != day:
        draw_card(day, horses)
    DAY[0] = day
    alive = {id(h) for h in horses}
    for r in sorted(CARD.get("races", []), key=lambda r: r.get("post", 0)):
        if not r.get("done"):
            run_race(r, alive, log)
    raced = CARD.get("raced", set())
    CARD.clear()
    pass_week(day, horses, raced)                            # the card has run: the week goes by for everyone else


# ---------------------------------------------------------------- self-checks
if __name__ == "__main__":
    horses = [founder() for _ in range(600)]
    new_roster()
    for o in range(60):
        BARN_TRAINER[o] = rng.choice(ROSTER)
    for h in horses:
        h.owner = rng.randrange(60)                          # 60 barns of ~10
        init_public(h)
        trainer_of(h)
    # (the trainer market is off: every horse is with the one neutral stable)
    assert all(t.horses <= t.stalls for t in ROSTER), "no trainer may be over his stalls"
    first_roster = set(t.name for t in ROSTER)
    err0 = st.mean(abs(h.est - true_rating(h)) for h in horses)
    start_est = {h.id: h.est for h in horses}
    founders = list(horses)
    log = []
    for day in range(3 * YEAR):
        if day % YEAR == 0 and day:
            horses = new_year(horses)
        race_day(day, horses, log)

    # (trainer skill is off: every horse trains perfectly, so records no longer separate trainers)

    old = [h for h in horses if h.age >= 9]
    prime = [h for h in horses if 4 <= h.age <= 6 and h.id in start_est]
    print(f"after 3 years: {len(horses)} horses; {len(old)} aged 9+, public est moved "
          f"{st.mean(h.est - start_est[h.id] for h in old):+5.1f}; "
          f"{len(prime)} founders now in their prime, moved {st.mean(h.est - start_est[h.id] for h in prime):+5.1f}")
    below = st.mean(h.est - peak_est(h) for h in old)
    print(f"old horses sit {below:+5.1f} under their career-best public rating")
    assert below < -4, "the public must see old horses decline from their peak"
    assert all(h.retired for h in horses if h.age >= RETIRE_AGE) and all(h.age < BREEDING_UNTIL for h in horses)
    print(f"retired horses in the population: {sum(h.retired for h in horses)} of {len(horses)}")
    ret = [h for h in horses if h.retired and hasattr(h, 'peak_dev')]
    assert all(h.est == peak_est(h) and all(h.developed[t] >= h.peak_dev[t] - 1e-9 for t in RACE_TRAITS) for h in ret), "a retired horse's card is its career peak"

    raced = [h for h in horses if h.starts >= 10]
    err1 = st.mean(abs(h.est - true_rating(h)) for h in raced)
    order = [t for _, t in TIERS]
    # truth on the same footing: rank the true rating within the group's *true* spread
    true_stats = {}
    for g in GROUP_STATS:
        xs = [true_rating(h) for h in horses if age_group(h) == g]
        true_stats[g] = (st.mean(xs), max(1.0, st.pstdev(xs)))
    def true_tier(h):
        m, s = true_stats[age_group(h)]
        return tier_of(55 + 15 * (true_rating(h) - m) / s)
    off = [abs(order.index(h.tier) - order.index(true_tier(h))) for h in raced]
    exact, near = st.mean(o == 0 for o in off), st.mean(o <= 1 for o in off)
    print(f"public estimate error: day 0 {err0:4.1f}  after 10+ starts {err1:4.1f}; "
          f"public tier exact {exact:4.2f}  within one {near:4.2f}")
    # error floors near 5: results are noisy and show form, not the ceiling. That gap is the game.
    # (within-one runs 0.89-0.92 across seeds since manners shapes the trip: results reward manners a touch more
    # than the true rating weights it, so 0.88 is the floor, not the typical)
    assert exact >= 0.5 and near >= 0.88, "racing must teach owners about their horses"

    tiers = {t: sum(1 for h in horses if h.tier == t and not h.retired) for _, t in TIERS}   # racers; retired cards are reputations
    print("tiers", tiers)
    assert tiers["S"] < tiers["A"] < tiers["B"] and tiers["S"] <= len(horses) * 0.08, "tiers must form a pyramid"
    two = [h for h in horses if h.age == 2]
    t2 = {t: sum(1 for h in two if h.tier == t) for _, t in TIERS}
    print(f"2YO tiers (group mean {GROUP_STATS['2'][0]:4.1f} sd {GROUP_STATS['2'][1]:4.1f} vs aged "
          f"{GROUP_STATS['aged'][0]:4.1f}/{GROUP_STATS['aged'][1]:4.1f})", t2)
    assert 0 < t2["S"] <= len(two) * 0.08 and t2["D"] < len(two) * 0.5, "2YOs are rated against 2YOs"

    racing = [h for h in horses if not h.retired]                   # the Open takes every age, so the elite is ranked across all of them
    elite = set(sorted(racing, key=lambda h: -h.race_score(h.age))[:len(racing) // 10])
    by_class = {}
    for g, s, n, t, f, w in log[-len(log) // 3:]:              # the last year, when ages have moved
        by_class.setdefault(n, []).append((f, w))
    cheap = []
    for name, races in sorted(by_class.items(), key=lambda kv: -len(kv[1])):
        fav = st.mean(w is max(f, key=lambda h: h.race_score(h.age)) for f, w in races)
        el = st.mean(w in elite for f, w in races)
        in_elite = st.mean(h in elite for f, _ in races for h in f)
        print(f"{name:7} races {len(races):4}  favorite won {fav:4.2f}  elite won {el:4.2f}  elite entered {in_elite:4.2f}")
        if name == "Invitational":
            assert el > 0.6, "elite must dominate the Invitational"
        if name in ("CLM25k", "CLM40k"):
            cheap += [h in elite for f, _ in races for h in f]
    # the few that slip through are under-rated elites: the bargains the market is meant to have
    assert st.mean(cheap) < 0.05, "owners who can see tiers don't drop elite horses in cheap claimers"
    short = sum(1 for g, s, n, t, f, w in log if len(f) < FIELD[t])
    print(f"races {len(log)}; short fields {short} ({short / len(log):.0%}); entries that got no race: {len(UNFILLED)}")
    assert len(UNFILLED) == 0, "an entry always gets a race"
    claim_races = sum(len(r) for n, r in by_class.items() if n.startswith("CLM"))
    year_races = sum(len(r) for r in by_class.values())
    print(f"claimers: {claim_races / year_races:4.0%} of races; horses claimed "
          f"{sum(1 for h in horses if h.claimed)} of {sum(1 for h in horses if h.ran_claimer)}")
    # shortcut: ~6% claimers vs ~40% in US harness; recent-form conditions and filled fields let
    # horses find their level without a tag. Revisit with the purse ladder once the economy is tuned.
    assert 0.04 <= claim_races / year_races <= 0.6

    # Freshness: among eight equal horses, one raced every week vs on a race/race/rest rhythm.
    h = founder(); h.age = 5; h.potential["durability"] = 0.0; init_public(h)   # average durability
    rival = [founder() for _ in range(7)]
    for r in rival:
        r.age = 5; r.potential = dict(h.potential); init_public(r)
    def campaign(rhythm, weeks=24):
        h.freshness, wins = 70.0, 0
        for w in range(weeks):
            week_passes(h)
            step = rhythm[w % len(rhythm)]
            if step == "race":
                for r in rival: r.freshness = 70.0
                field = [h] + rival
                rng.shuffle(field)
                wins += race(field)[0] is h
                h.freshness = max(0, h.freshness - 30 * drain(h))
            elif step == "rest":
                rest(h)
            else:
                train(h, "stamina", False)
        return wins
    every = st.mean(campaign(["race"]) for _ in range(150)) / 24
    rhythm = st.mean(campaign(["race", "race", "rest"]) for _ in range(150)) / 16
    print(f"win rate vs equals: raced every week {every:5.3f}  race/race/rest {rhythm:5.3f} (fresh equals ~0.125)")
    assert rhythm > 1.5 * every, "racing tired must cost, resting must restore"

    # Development: an untrained 2YO closes most of the gap to its ceiling in a season.
    y = founder(); y.age = 2; init_public(y)
    y.developed = {t: y.ceiling(t) - 2.0 for t in RACE_TRAITS}
    gap0 = sum(y.ceiling(t) - y.developed[t] for t in RACE_TRAITS)
    for _ in range(26):
        week_passes(y)
        p = plan(y)
        if p == "rest": rest(y)
        elif p == "race":
            y.freshness -= 30 * drain(y)
            for t in RACE_TRAITS: y.developed[t] = min(y.ceiling(t), y.developed[t] + 0.05)
        else: train(y, p[1], p[2])
    gap1 = sum(y.ceiling(t) - y.developed[t] for t in RACE_TRAITS)
    print(f"2YO gap to ceiling: start {gap0:4.1f}  after 26 weeks {gap1:4.1f}")
    assert gap1 < gap0 / 2, "the stable's jogging closes most of a green 2YO's gap in a season"
    # The day sheet: an owner's job is the week's order, a stable week develops without shaping, and the green gap shows at the gate.
    y = founder(); y.age = 2; init_public(y)
    y.developed = {t: y.ceiling(t) - 2.0 for t in RACE_TRAITS}
    y.freshness = 70.0; green = rating_tonight(y)
    y.developed = {t: y.ceiling(t) for t in RACE_TRAITS}
    print(f"a green 2YO races {rating_tonight(y) - green:.1f} rating under its made self")
    assert 4 < rating_tonight(y) - green < 10, "a green 2YO is a few lengths short, not a class"
    y.owner = 0; HUMAN.add(0); y.freshness = 70.0
    assert plan(y)[3] == "stable", "an idle youngster gets the stable's jog"
    y.job = (DAY[0], "school", "stamina")
    assert plan(y) == ("train", "gait", False, "school"), "School is gait work whatever the focus"
    y.job = (DAY[0], "train", "early_speed"); y.shape = {t: 0.0 for t in RACE_TRAITS}
    train(y, *plan(y)[1:]); sh = y.shape["early_speed"]
    y.shape = {t: 0.0 for t in RACE_TRAITS}; train(y, "early_speed", False, "stable")
    assert sh > 0 and y.shape["early_speed"] == 0, "only the owner's hand shapes a horse"
    y.job = (DAY[0] - 1, "train", "early_speed")
    assert plan(y)[3] == "stable", "a stale stamp is last week's job"
    y.age = YOUNG + 1; y.job = (DAY[0], "train", "early_speed")
    assert plan(y) == "rest", "the sheet ends at three: older horses are kept, not made"
    HUMAN.discard(0)

    # Shaping: 10 hard weeks on gate speed move a 2YO's shape by ~+1 there and down elsewhere,
    # the total stays near zero, and a shape cannot exceed the cap.
    y = founder(); y.age = 2; init_public(y)
    for _ in range(10):
        train(y, "early_speed", True)
    print("shape after 10 hard weeks on gate speed:", {t[:4]: round(v, 2) for t, v in y.shape.items()})
    assert y.shape["early_speed"] == SHAPE_CAP and all(v < 0 for t, v in y.shape.items() if t in SHAPED[1:])
    assert abs(sum(y.shape.values())) < 0.01, "shaping moves ability around, it doesn't create any"

    # Pedigree: a foal's starting estimate follows its parents', and the truth is near it.
    sires = [h for h in horses if h.sex == "m"][:60]
    dams = [h for h in horses if h.sex == "f"][:60]
    foals = []
    for s in sires:
        for d in dams:
            f = breed(s, d); init_public(f, s, d); foals.append(f)
    # Pedigree ranks foals a little (better-rated parents, better foals) while any one is a gamble: only part of a
    # foal's genes show in it (sim.FOAL_H), so the best-bred quarter beats the worst by a few points, not a class.
    foals.sort(key=lambda f: f.est)
    q = len(foals) // 4
    peak = lambda f: 70 + 6 * f.race_score()
    lo, hi = st.mean(map(peak, foals[:q])), st.mean(map(peak, foals[-q:]))
    spread = st.pstdev(map(peak, foals))
    print(f"foals by pedigree (n={len(foals)}): bottom quarter peak {lo:4.1f}, top quarter {hi:4.1f}; any one foal sd {spread:4.1f}")
    assert lo + 2 < hi < lo + 15 and spread > 8, "pedigree must inform without deciding"
    print("all checks passed")
