"""The stakes programme: fixed-date races by age and sex, entered by nomination.
Run: python stakes.py

Overnight racing is free; stakes are the paid tier an owner opts into. Nominate early
and it's cheap, late and it's dear, and after the closing date it's closed. Eight start:
if more nominate, the eight best by public rating draw in and the rest are refunded.
"Find best stakes" ranks a horse's open stakes by expected net, from public info only.
"""
import statistics as st
import circuit as c
import economy as e
from sim import race, rng

PURSE = {"2": 100_000, "3": 150_000, "aged": 200_000}      # the base an unnamed stake would carry (kept for old saves)
# The stakes book, modelled on a real harness season: a winter series for the older horses, the juvenile and sire
# stakes through the summer, the 3-year-old classics (a Derby and an Oaks worth the most outside the finals), memorials
# named for the circuit's own, and the Crown: the year-end championship that names a champion in each division.
# (week, age group, sex, name, purse, kind). Purses are set so the very best horse can take $1.5-2M in a season.
DIVISION = {("2", "open"): "2-Year-Old Colt", ("2", "F&M"): "2-Year-Old Filly", ("3", "open"): "3-Year-Old Colt",
            ("3", "F&M"): "3-Year-Old Filly", ("aged", "open"): "Older Horse", ("aged", "F&M"): "Older Mare"}
SCHEDULE = [
    (6, "aged", "open", "Winter Classic", 200_000, "trophy"),
    (8, "aged", "F&M", "Snowdrop Stakes", 150_000, "trophy"),
    (14, "3", "open", "Spring Prep", 150_000, "trophy"),
    (14, "3", "F&M", "Spring Filly Prep", 120_000, "trophy"),
    (18, "aged", "open", "Mayor's Cup", 350_000, "trophy"),
    (18, "aged", "F&M", "Matron Stakes", 250_000, "trophy"),
    (22, "3", "open", "Sapphire Cup", 250_000, "trophy"),
    (22, "3", "F&M", "Lady Grace Memorial", 250_000, "memorial"),
    (26, "2", "open", "Juvenile Cup", 200_000, "trophy"),
    (26, "2", "F&M", "Debutante Stakes", 180_000, "trophy"),
    (28, "aged", "open", "Old Mill Memorial", 400_000, "memorial"),
    (28, "aged", "F&M", "Duchess Memorial", 300_000, "memorial"),
    (31, "3", "open", "Founders Derby", 700_000, "classic"),
    (31, "3", "F&M", "Founders Oaks", 500_000, "classic"),
    (35, "2", "open", "Sire Stakes Final", 300_000, "trophy"),
    (35, "2", "F&M", "Filly Sire Stakes Final", 250_000, "trophy"),
    (38, "aged", "open", "Governor's Gold Cup", 500_000, "trophy"),
    (38, "aged", "F&M", "Empress Cup", 350_000, "trophy"),
    (40, "3", "open", "Harvest Memorial", 350_000, "memorial"),
    (40, "3", "F&M", "Tiara Stakes", 300_000, "trophy"),
    (43, "2", "open", "Pioneer Memorial", 250_000, "memorial"),
    (43, "2", "F&M", "Rosebud Memorial", 200_000, "memorial"),
    # sire stakes legs: a summer series for the young horses, by nomination like any stake. The 2-year-olds' four legs
    # lead to their Sire Stakes Finals (week 36); the 3-year-olds' run between their classics. Fast youngsters get a
    # real season against their own age, and the purses count toward a Crown invitation.
    *[(w, "2", sx, f"{'Filly ' if sx == 'F&M' else ''}Juvenile Sire Stakes Leg {k + 1}", 45_000 if sx == "open" else 40_000, "leg")
      for k, w in enumerate((15, 19, 23, 31)) for sx in ("open", "F&M")],
    *[(w, "3", sx, f"{'Filly ' if sx == 'F&M' else ''}Sophomore Sire Stakes Leg {k + 1}", 60_000 if sx == "open" else 50_000, "leg")
      for k, w in enumerate((11, 17, 25, 34)) for sx in ("open", "F&M")],
    # the season openers: the older horses' winter series, so the year starts with something to win
    *[(w, "aged", sx, nm if sx == "open" else nm.replace("Stakes", "Mare Stakes"), 80_000 if sx == "open" else 65_000, "opener")
      for w, nm in ((0, "New Year Stakes"), (2, "Frost Stakes"), (4, "Thaw Stakes")) for sx in ("open", "F&M")],
    # the Invitational series: eight legs a year for the best older horses and mares, the circuit's bread and butter
    *[(w, "aged", sx, f"{'Mares ' if sx == 'F&M' else ''}Invitational Series Leg {k + 1}", 90_000 if sx == "open" else 75_000, "invitational")
      for k, w in enumerate((9, 13, 21, 27, 33, 37, 42, 46)) for sx in ("open", "F&M")],
    # each track's signature stake, named for it, rotating through the divisions
    *[(w, g, sx, f"{v} Cup", 125_000 if sx == "open" else 100_000, "signature")
      for w, v, (g, sx) in zip((1, 3, 5, 7, 12, 16, 20, 24, 30, 36),
                               ("Harness Park", "Riverside Downs", "Meadow Lane", "Granite Hill", "Bayview Fair", "Capital Raceway",
                                "Lakeshore Park", "Northgate Raceway", "Sandhill Downs", "Pine Ridge"),
                               (("aged", "open"), ("aged", "F&M"), ("3", "open"), ("3", "F&M"), ("3", "open"), ("aged", "open"),
                                ("3", "F&M"), ("aged", "F&M"), ("2", "open"), ("2", "F&M")))],
    # the smaller stakes: a step a mid-sized barn can win, for the 3-year-olds through the year and the 2-year-olds late
    *[(w, g, sx, f"{nm}{' (Fillies)' if sx == 'F&M' else ''}", 60_000 if sx == "open" else 50_000, "trophy")
      for w, g, nm in ((10, "3", "Bluebonnet Stakes"), (12, "3", "Primrose Stakes"), (24, "3", "Midsummer Stakes"),
                       (29, "3", "Clover Stakes"), (32, "3", "Lantern Stakes"), (36, "3", "Equinox Stakes"),
                       (39, "2", "Acorn Stakes"), (41, "2", "Sapling Stakes"), (44, "2", "Maple Leaf Stakes"),
                       (45, "2", "First Frost Stakes"), (47, "2", "Kindling Stakes"), (48, "2", "Hearthside Stakes"))
      for sx in ("open", "F&M")],
    # the Crown: by invitation only, the ten top earners of the season in each division
    (49, "2", "open", "Crown Championship", 600_000, "final"),
    (49, "2", "F&M", "Crown Championship", 500_000, "final"),
    (50, "3", "open", "Crown Championship", 750_000, "final"),
    (50, "3", "F&M", "Crown Championship", 600_000, "final"),
    (51, "aged", "open", "Crown Championship", 1_000_000, "final"),
    (51, "aged", "F&M", "Crown Championship", 800_000, "final"),
]
CHAMPIONS = {}   # year -> {division: horse name}: the limited titles, one per division per year
HALL = []        # every horse that ever won a stake: kept for good, so the honour roll and trophies always link
RATING0 = {"2": 70, "3": 70, "aged": 75}    # first-year class rating on the standardized scale (75 ~ top 10%); learned after
WEEKS = (20, 40)                            # two stakes a year per division
FIELD, BIG_FIELD = 10, 12   # stakes go on the mile: ten on the gate, a second tier to twelve
BIG_NOMS = 2 * FIELD         # only when nominations double the gate: an occasional, oversubscribed stake
NOM_MARGIN = {"2": 10, "3": 10, "aged": 4}   # AI nominates a horse rated within this of the class; the aged pool is big, so pickier
EARLY, LATE, CLOSE = 8, 2, 2                # weeks out: 1% of purse until EARLY, 3% until LATE, then closed
CALENDAR = []
_ids = iter(range(1, 10 ** 6))


def stake_name(s):
    """A named stake keeps its name ('Founders Derby', 'Crown Championship · Older Mare'); an unnamed one from an old
    save reads '2YO F&M Stakes $80k': the age class, the sex only when it's restricted, then the purse."""
    if getattr(s, "title", None):
        return s.title + (f" · {DIVISION[(s.group, s.sex)]}" if s.kind == "final" else "")
    age = {"2": "2YO", "3": "3YO", "aged": "Aged"}[s.group]
    return f"{age}{' F&M' if s.sex == 'F&M' else ''} Stakes ${s.purse / 1000:.0f}k"


class Stake:
    def __init__(self, week, group, sex, title=None, purse=None, kind="trophy"):
        self.id = f"S{next(_ids)}"
        self.week, self.group, self.sex = week, group, sex
        self.title, self.kind = title, kind
        self.purse = purse or PURSE[group] * (0.8 if sex == "F&M" else 1)
        self.name = stake_name(self)
        self.rating = RATINGS.setdefault((group, sex), RATING0[group])
        self.noms = []
        self.result = None

    def eligible(self, h):
        if self.kind == "final":                              # the Crown crowns a colt and a filly in every age: boys and girls apart
            return c.age_group(h) == self.group and h.sex == ("f" if self.sex == "F&M" else "m") and not h.retired
        if c.age_group(h) != self.group or h.retired:
            return False
        if self.sex == "F&M":
            return h.sex == "f"
        # an open stake takes colts and fillies, unless the fillies have their own race in this division that week:
        # then it's the colts', so a filly never has two stakes to choose between
        return h.sex == "m" or not any(x.sex == "F&M" and x.week == self.week and x.group == self.group and x is not self for x in CALENDAR)

    def fee(self, day):
        if self.kind == "final":                              # the Crown is by invitation: nobody nominates
            return None
        out = self.week - day % c.YEAR
        return None if out < CLOSE else self.purse * (0.01 if out >= EARLY else 0.03)


RATINGS = {}   # division -> learned class rating
LEGS = ("leg",)   # the Sire Stakes legs: no trophy, only their finals (the Invitational Series has no final, so its legs keep theirs)
KIND_OF = {t: k for *_, t, _p, k in SCHEDULE}   # a stake's title -> its kind: which trophy icon a win earns


def new_calendar():
    CALENDAR.clear()
    for week, group, sex, title, purse, kind in SCHEDULE:
        CALENDAR.append(Stake(week, group, sex, title, purse, kind))


def season_earnings(h, day):
    """What a horse has won so far this calendar year: the Crown's invitation list. Career earnings less what it had
    when the season opened (set at the year tick); before its first year tick, its starts this year."""
    if hasattr(h, "season0"):
        return h.earnings - h.season0
    yr = day // c.YEAR
    return sum(r["won"] for r in getattr(h, "results", []) if r["day"] // c.YEAR == yr)


def invite(s, horses, day):
    """The Crown's field: the season's ten top earners in the division, fit or not, sound and still racing."""
    pool = [h for h in horses if s.eligible(h) and season_earnings(h, day) > 0]
    s.noms = sorted(pool, key=lambda h: -season_earnings(h, day))[:FIELD]


def nominate(h, s, day):
    """Pay today's fee and enter. Returns the fee, or None if ineligible, closed, in, or broke."""
    fee = s.fee(day)
    if fee is None or not s.eligible(h) or h in s.noms or s.result or e.cash.get(h.owner, 0) < fee:
        return None
    if any(h in x.noms and x.week == s.week and x is not s for x in CALENDAR):
        return None                                           # one stake a week: a filly can't go in the open leg and the filly leg both
    e.book(h.owner, "stakes", -fee)
    s.noms.append(h)
    return fee


def expected_share(h, s):
    """Public info only: the horse's rating against the stake's. A horse 10 over the class
    expects a fair chunk of the purse; one 10 under, a cheque at best."""
    x = (c.on_aged_scale(h.est, c.age_group(h)) - s.rating) / 5
    return 0.35 / (1 + 2.718 ** -x)                           # 30 under the class: a few dollars; 10 over: ~30%


def best_for(h, day):
    """Open stakes this horse can enter, best first: expected net = share of purse after
    the driver's and trainer's cuts, less the fee due today."""
    cut = 1 - c.DRIVER - c.trainer_of(h).cut
    out = []
    for s in CALENDAR:
        fee = s.fee(day)
        if fee is None or not s.eligible(h) or s.result:
            continue
        ev = expected_share(h, s) * s.purse * cut - fee
        out.append((ev, s, fee))
    return sorted(out, key=lambda r: -r[0])


def ai_nominate(horses, ai, day):
    """On the early-closing week AI barns nominate horses that rate near the class, if flush. A filly goes to the
    fillies' stake first, since it's one stake a week."""
    for s in sorted(CALENDAR, key=lambda s: (s.week, s.sex != "F&M")):
        if s.week - day % c.YEAR != EARLY or s.kind == "final":
            continue
        for h in horses:
            if h.owner in ai and s.eligible(h) and c.on_aged_scale(h.est, c.age_group(h)) >= s.rating - NOM_MARGIN[s.group] \
                    and e.cash.get(h.owner, 0) > s.fee(day) + e.RESERVE:
                nominate(h, s, day)


def run_today(day, horses):
    """Stakes on tonight's card: draw the field, race on the mile, pay out, learn the class."""
    alive, ran = set(id(h) for h in horses), set()
    for s in CALENDAR:
        if s.week != day % c.YEAR or s.result:
            continue
        if s.kind == "final":
            invite(s, horses, day)
        noms = [h for h in s.noms if id(h) in alive and s.eligible(h) and id(h) not in ran]   # one start a night: nominated twice (older saves), it draws out of the second
        field = sorted(noms, key=lambda h: -h.est)[:BIG_FIELD if len(noms) >= BIG_NOMS else FIELD]
        for h in [h for h in s.noms if h not in field and id(h) in alive] if s.kind != "final" else []:
            e.book(h.owner, "stakes", s.purse * 0.01)          # drew out (or already ran tonight): nomination refunded
        if len(field) < 2:                                    # a walkover: fees back, no race
            for h in field:
                e.book(h.owner, "stakes", s.purse * 0.01)
            s.result = []
            RATINGS[(s.group, s.sex)] = s.rating - 5          # nobody came: the class was rated too high
            continue
        rng.shuffle(field)                                    # the post-position draw: the best-rated make the field, not the rail
        for post, h in enumerate(field, 1):
            h.order = "stakes"; h.post = post
        s.tonight = {h.id: c.rating_tonight(h) for h in field}   # who was the better horse at the gate
        c.drive(field, c.assign_drivers(field), "mile")
        order = (c.outcome.race if c.ENGINE == "outcome" else race)(field, "mile", True)   # the overnights' engine; Harness Park has a passing lane
        line = c.tote_odds(field)
        field_est = st.mean(c.on_aged_scale(h.est, c.age_group(h)) for h in field)
        RATINGS[(s.group, s.sex)] = s.rating = s.rating + 0.3 * (field_est - s.rating)
        rid = f"{day}-stake-{s.id}"
        for place, h in enumerate(order):
            c.record_result(h, s.name, "mile", place, s.purse, st.mean(h.est for h in field), len(field))
            h.results[-1]["race_id"] = rid
        import story as _story
        c.STORIES[rid] = dict(_story.build(order, "mile", passing=True), id=rid, name=s.name, purse=s.purse, day=day, venue="Harness Park", passing=True,
                              sponsor=getattr(s, "sponsor", None))   # stakes nights are the flagship's; a sponsored stake carries its barn into the replay
        c.tells(c.STORIES[rid], order)
        c.drove(order, c.STORIES[rid]["horses"], c.year_of(day))
        for row, h in zip(c.STORIES[rid]["horses"], order):  # odds at post time and RaceGod's ledger, as overnights keep them
            row["odds"] = "%d-%d" % line[h.id]
            if c.ENGINE == "outcome":
                row["why"] = h.why
        s.result = order
        ran.update(id(h) for h in field)
        champ = order[0]                                      # a stake's winner keeps the trophy; the Crown names a champion
        if s.kind not in LEGS:                                # a series leg pays a purse, not a trophy: the final carries it
            champ.trophies = getattr(champ, "trophies", []) + [f"Year {c.year_of(day)} {s.name}"]
        if champ not in HALL:
            HALL.append(champ)
        if s.kind == "final":
            CHAMPIONS.setdefault(c.year_of(day), {})[DIVISION[(s.group, s.sex)]] = champ.name


def year_tick(horses, ai, day):
    for h in horses:
        h.season0 = h.earnings                                # a fresh season: the Crown counts from here
    new_calendar()


# ---------------------------------------------------------------- self-checks
if __name__ == "__main__":
    horses = e.world()
    ai = set(range(60))
    new_calendar()
    assert len(CALENDAR) == len(SCHEDULE) == 100 and all(any(x.week == w for x in CALENDAR) for w in range(49)) and sum(x.kind == "final" for x in CALENDAR) == 6 and sum(x.kind == "leg" for x in CALENDAR) == 16
    log, ran, years = [], [], []
    for d in range(2 * c.YEAR):
        if d == c.YEAR:
            ran += [s for s in CALENDAR if s.result]; years.append(list(CALENDAR))
            new_calendar()
        ai_nominate(horses, ai, d)
        run_today(d, horses)
        horses = e.day(d, horses, ai, log)
        for h in horses:
            if getattr(h, "order", None) == "stakes":
                h.order = None
    ran += [s for s in CALENDAR if s.result]; years.append(list(CALENDAR))
    print(f"stakes run: {len(ran)} of {2 * len(SCHEDULE)} over two years; fields {sorted(len(s.result) for s in ran)}")
    assert len(ran) >= 1.4 * len(SCHEDULE) and all(len(s.result) <= BIG_FIELD for s in ran)
    finals = [s for s in ran if s.kind == "final" and s.result]
    print(f"Crown finals run: {len(finals)} of 12; champions by year: {CHAMPIONS}")
    # a new world has no 2-year-olds in its second season (foals take two years to reach the track), so year 2 crowns four
    assert len(finals) >= 10 and len(CHAMPIONS[0]) == 6 and len(CHAMPIONS[1]) >= 4, "every division crowns a champion"
    assert all(len(set(v.values())) == len(v) for v in CHAMPIONS.values()), "a horse holds one title a year: boys and girls apart"
    assert all(any(s.name in t for t in getattr(s.result[0], "trophies", [])) for s in ran if s.result and s.kind not in LEGS), "every winner keeps the trophy"
    assert not any("Sire Stakes Leg" in t for h in horses for t in getattr(h, "trophies", [])), "a series leg gives no trophy"
    assert all(s.eligible(h) or h.retired or c.age_group(h) != s.group for s in ran for h in s.result), "every starter was eligible"
    import collections as _co
    for cal in years:
        doubles = [k for k, n in _co.Counter((s.week, id(h)) for s in cal if s.result for h in s.result).items() if n > 1]
        assert not doubles, f"a horse starts in one stake a night: {doubles[:3]}"
        assert not any(h in y.noms for x in cal for y in cal if x is not y and x.week == y.week for h in x.noms), "no horse nominated to two stakes in one week"
    full = [s for s in ran if len(s.result) >= 6]
    night = lambda s, hs: st.mean(s.tonight[h.id] for h in hs)
    better = st.mean(night(s, s.result[:3]) > night(s, s.result[-3:]) for s in full)
    fresh = st.mean(h.freshness for s in full for h in s.result)
    print(f"first three home were the better horses at the gate (fields of 6+, n={len(full)}): {better:.0%}; "
          f"runners' freshness after the race {fresh:.0f}")
    # fields are the eight best by rating, so they're close; what the horses bring on the night must still decide it
    assert better > 0.65 and fresh > 25, "ability on the night must show in stakes, and runners must not arrive exhausted"
    fees = -sum(min(0, v.get("stakes", 0)) for v in e.ledger.values())
    print(f"nomination money taken in ${fees:,.0f}; lowest barn cash ${min(e.cash.values()):,.0f}")
    assert fees > 0 and min(e.cash.values()) >= 0

    # Find best stakes: a top aged horse has a positive-EV stake to aim at; a D horse has none.
    new_calendar()
    aged = sorted((h for h in horses if c.age_group(h) == "aged" and not h.retired), key=lambda h: -h.est)
    top, dud = aged[0], aged[-1]
    for h, want in ((top, True), (dud, False)):
        best = best_for(h, 5)
        line = f"{h.name} ({h.tier}, {h.sex}): " + (
            f"best {best[0][1].name} wk {best[0][1].week}, fee ${best[0][2]:,.0f}, expected net ${best[0][0]:,.0f}" if best else "nothing open")
        print(line)
        assert all(s.eligible(h) for _, s, _ in best)
        assert (best[0][0] > 0) == want, "a good horse has a stake worth paying for; a poor one doesn't"
    print("all checks passed")
