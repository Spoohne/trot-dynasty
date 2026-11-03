"""Standardbred breeding + race simulation core. Run: python sim.py

Everything is hidden genetics -> potential -> race results. No UI. The asserts at
the bottom are the design contract: good matches pay off on average, balance
beats raw power, inbreeding hurts, and freaks still happen.
"""
import random
import statistics as st
from itertools import count

RACE_TRAITS = ["early_speed", "late_speed", "stamina", "gait", "durability"]
TRAITS = RACE_TRAITS + ["precocity", "longevity"]   # the last two shape the career curve
HALF_SLOWER = 2.0                                   # four tight turns: a half-mile track runs ~2s slower for the same horse
RETIRE_AGE = 15                                     # USTA: no racing at 15 or older
LATE = 8                                            # past this, the decline turns steep for most horses
COATS = ["bay"] * 5 + ["brown"] * 2 + ["black"] * 2 + ["chestnut"] * 2 + ["grey"]   # Standardbred frequencies, roughly
MARKINGS = ["none"] * 4 + ["star", "star", "blaze", "snip"]
# Prime (prime position): where a horse likes to sit, independent of how good it is. front = wants the lead; stalk = sits just
# off it (pocket or parked); mid = settles mid-pack and moves after the half; late = drops out and closes
STYLES = ["front", "stalk", "stalk", "mid", "mid", "late"]
STYLE_SEAT = {"front": 1.6, "stalk": 0.6, "mid": -0.6, "late": -1.6}          # added to early speed to decide the seat
POCKET_BOXED, POCKET_BOX_COST = 0.2, 0.25          # the pocket's risk: about 1 trip in 5 is boxed in, a couple of lengths lost
LANE_BOXED, LANE_GAIN, LANE_LEADER = 0.05, 0.08, 0.05   # a passing-lane track: boxed 1 in 20, a little gained up the inside, the leader gives a little back
STYLE_KICK = {"front": 0.0, "stalk": 0.2, "mid": 0.6, "late": 1.0}            # share of the closing bonus off a hot pace


def style_of(h):
    """A horse's Prime; horses from saves before it existed get one from their early/late balance."""
    st = getattr(h, "style", None)
    if st:
        return st
    p = h.potential; g = p["late_speed"] - p["early_speed"]
    return "late" if g > 1 else "mid" if g > .3 else "front" if g < -1 else "stalk"
N_LOCI = 20
MAJOR_LOCI = 2          # first loci of each trait have 3x effect
NOISE_SD = 1.0          # non-genetic potential noise (student-t, heavy tail)
SPREAD = 0.06           # extra foal-to-foal swing per point of gap between the parents' overall race scores
MUTATE = 0.05           # chance each inherited gene is replaced by a fresh one: pulls a bred-up breed back toward average (0.10 before
                        # ratings v2; halved for the launch rules, DECISIONS 243: pedigree holds r ~0.2, S+ stays 3-4%, no runaway)
FOAL_SCALE = 0.8        # shrinks a bred foal's whole deviation from average (genes and luck alike)
FOAL_H = 0.65            # share of a bred foal's genetic value that shows in the horse: foals of stars regress to the mean (genes pass on whole)
N_LINES = 6             # hidden sire/dam bloodlines for nicks
rng = random.Random(42)
NICK = {(a, b): rng.gauss(0, 0.6) for a in range(N_LINES) for b in range(N_LINES)}
_ids = count()


def t_dist(df):
    """Student-t sample: normal / sqrt(chi2/df). Heavy tail -> rare freaks."""
    chi2 = sum(rng.gauss(0, 1) ** 2 for _ in range(df))
    return rng.gauss(0, 1) / (chi2 / df) ** 0.5


class Horse:
    def __init__(self, genes, line, sire=None, dam=None, recessive=(0, 0),
                 sex=None, age=2):
        self.id = next(_ids)
        self.sex = sex or rng.choice("mf")
        self.age = age
        # looks: a coat from a parent (bay dominates, like the breed), a marking of its own
        self.coat = rng.choice([p.coat for p in (sire, dam) if p and getattr(p, "coat", None)] or COATS)
        self.marking = rng.choice(MARKINGS)
        self.style = rng.choice([p.style for p in (sire, dam) if p and getattr(p, "style", None)] or STYLES) if rng.random() < .5 else rng.choice(STYLES)   # half the time like a parent
        self.genes = genes            # trait -> list of (allele_a, allele_b)
        self.line = line
        self.sire, self.dam = sire, dam
        self.recessive = recessive    # hidden harmful locus; homozygous (1,1) hurts
        self.potential = self._potential()

    def genetic(self, trait):
        return sum((a + b) * (3 if i < MAJOR_LOCI else 1)
                   for i, (a, b) in enumerate(self.genes[trait])) / 8  # /8 -> h2 ~0.35 vs NOISE_SD

    def ancestors(self, depth=3):
        out = set()
        for p in (self.sire, self.dam):
            if p and depth:
                out.add(p.id)
                out |= p.ancestors(depth - 1)
        return out

    def _potential(self):
        pot = {t: self.genetic(t) * (FOAL_H if self.sire else 1) + t_dist(4) * NOISE_SD for t in TRAITS}
        if self.sire and self.dam:
            nick = NICK_W * NICK[self.sire.line, self.dam.line]
            inbred = len(self.sire.ancestors() & self.dam.ancestors()) * INBRED
            gap = abs(self.sire.race_score() - self.dam.race_score())          # the further apart the parents overall, the wider the throw
            swing = rng.gauss(0, SPREAD * gap)
            for t in TRAITS:                                                  # a bred foal's luck is reined in so the breed doesn't spread out generation on generation
                pot[t] = FOAL_SCALE * (pot[t] + swing) + nick - inbred
        if self.recessive == (1, 1):
            pot["durability"] -= 4.0
        return pot

    @property
    def peak_age(self):
        return max(3, min(7, round(5 - 0.8 * self.potential["precocity"])))

    def age_adj(self, age=None):
        """Shift to every racing trait at an age: short of the peak while maturing,
        falling after it. Early peakers also tend to fade faster."""
        age = self.age if age is None else age
        if age < self.peak_age:
            return -min(2.0, 0.5 * (self.peak_age - age))
        decline = 0.2 * 2.718 ** (-0.4 * self.potential["longevity"]) * (1 + 0.15 * self.potential["precocity"])
        adj = -max(0.05, min(1.0, decline)) * (age - self.peak_age)
        if age > LATE:                                    # the cliff: after 8 most horses fall away fast
            hold = max(0.15, min(1.5, 2.718 ** (-0.4 * self.potential["longevity"])))   # the iron horse is rare
            adj -= 0.6 * hold * (age - LATE) ** 1.5
        return adj

    def ceiling(self, trait, age=None):
        return self.potential[trait] + self.age_adj(age)

    def current(self, track="mile"):
        """Stats the horse races with today. The circuit layer overrides this
        with developed stats and freshness; here a horse runs to its ceiling for its age."""
        return {t: self.ceiling(t) for t in RACE_TRAITS}

    def race_score(self, age=None):
        """How good a racehorse this is at its peak (or at `age`). Low gait/stamina
        drag the whole score: speed you can't hold or keep on stride is worth little."""
        adj = self.age_adj(age) if age else 0
        p = {t: soft(self.potential[t] + adj) for t in RACE_TRAITS}
        speed = W_SPEED * p["early_speed"] + W_FINISH * p["late_speed"]
        return speed + W_STAM * p["stamina"] + GAIT_W * min(p["gait"], GAIT_CAP) + 1.0 * min(p["gait"], p["stamina"], 0)


SOFT_AT, SOFT_ROOM = 5.0, 2.5   # past the top of the breed a stat counts for less and less, never more than 2.5 beyond


def soft(x):
    """A stat as it tells on the track: itself up to the breed's very top, then diminishing, so a genetic freak is the best
    there has ever been in that stat without one stat carrying everything. Breeding still passes on the raw genes."""
    import math
    return x if x <= SOFT_AT else SOFT_AT + SOFT_ROOM * (1 - math.exp(-(x - SOFT_AT) / SOFT_ROOM))


assert soft(3) == 3 and 7.4 < soft(16.3) < 7.5 and soft(5.82) < 5.82


def founder(shift=None):
    """Random unrelated horse. shift: trait -> add to every allele (makes a strong/weak horse)."""
    shift = shift or {}
    genes = {t: [(rng.gauss(0, 1) + shift.get(t, 0), rng.gauss(0, 1) + shift.get(t, 0))
                 for _ in range(N_LOCI)] for t in TRAITS}
    rec = (int(rng.random() < 0.15), int(rng.random() < 0.15))
    return Horse(genes, rng.randrange(N_LINES), recessive=rec,
                 age=rng.randint(2, 7))


def breed(sire, dam):
    # sex rule (sire male, dam female) is enforced where matings are chosen, not here
    fresh = lambda a: rng.gauss(0, 1) if rng.random() < MUTATE else a    # a gene now and then reverts to the breed's average stock
    genes = {t: [(fresh(rng.choice(s)), fresh(rng.choice(d))) for s, d in zip(sire.genes[t], dam.genes[t])]
             for t in TRAITS}
    rec = (rng.choice(sire.recessive), rng.choice(dam.recessive))
    return Horse(genes, dam.line, sire, dam, rec)


# pace and running styles (tuned so winners split roughly: on the lead a third, stalking a third, closers a quarter+)
PACE_COST, STEAL, CLOSE_GAIN, CLOSER_GAP = 0.5, 0.2, 0.5, 1.0
# Manners -> Prime -> trip -> talent. A well-mannered horse goes where its Prime says (gets the lead, sits the
# pocket, saves ground for the late kick); a rank one gets shuffled to the wrong spot, and from a bad trip it only
# shows part of its speed and stamina. Poor stats aren't hidden by a bad trip: only what's good gets wasted.
TRIP0, TRIP_K, TRIP_LUCK = 0.6, 0.1, 0.05   # trip quality 0..1: ~0.6 at average manners, ~0.9 at +3, ~0.3 at -3; a little luck
GAIT_CAP = (0.9 - TRIP0) / TRIP_K   # manners past this (+3) can't improve a perfect trip, so it earns no more rating
NICK_W = 0.35                 # how much of a line pairing's nick shows in the foal (the scout's grade reads the pairing itself)
INBRED = 0.0                  # no cost to close breeding: inbreeding is the breeder's call (set > 0 to make shared ancestors cost)
# The race clock, in real-world pacing seconds. The race itself is decided on its own internal scale; the clock maps
# that onto real trotting times (a typical overnight winner ~1:53, stakes horses ~1:50-1:51, the world record is 1:48.4)
# by shifting it. Monotonic: it never changes who won. A freak can reach the high 1:47s on a mile; half-mile tracks
# read slower on top of what their turns already cost.
CLOCK_REF, CLOCK_AT, CLOCK_K = 113.8, 112.6, 1.0
CLOCK_OLD = 109.6, 1.25, 104.0   # the clock before 2026-10-27 (anchor, stretch, floor): kept to convert saved times and the rating fit


CLOCK_FLOOR, HALF_FLOOR = 100.5, 1.8   # 1:40.5 on a mile (1.8s more on a half), just past Northern Star (DECISIONS 239): only he gets near it


def clock(t, half=False):
    x = CLOCK_AT + CLOCK_K * (t - CLOCK_REF)
    f = CLOCK_FLOOR + (HALF_FLOOR if half else 0)
    if x < f + 3:                                             # in the last 3s above the floor the gains shrink smoothly toward it
        x = f + 3 * 2.718 ** ((x - f - 3) / 3)
    return x


def unclock_old(x):
    """A time read off the old clock, back to race seconds (for converting saved times)."""
    at, k, fl = CLOCK_OLD
    if x < fl + 3:
        import math
        x = fl + 3 + 3 * math.log(max(1e-9, (x - fl) / 3))
    return CLOCK_REF + (x - at) / k


def retime(x, half=False):
    """A saved old-clock time on the new clock."""
    return clock(unclock_old(x), half)


# The honest clock (ratings v2, 2026-11-03): every horse runs its own time, read off the race model's performance, so one bar
# is worth the same at the wire and on the clock. On the 2026-10-27 clock a bar was worth 2.3 s between horses but only a
# fifth of a second inside a field (a beaten horse's time was the winner's class plus its margin). The breed's spread is
# pulled in about SQUEEZE_REF by SQUEEZE: a bar is worth about 0.8 s, four lengths, everywhere. The half-mile's own
# allowance (HALF_SLOWER) is a track's slowness, not ability, and stays whole.
SQUEEZE_REF, SQUEEZE = 112.0, 0.35
CLOCK_SHIFT = 0.0                                   # the whole clock, slower or faster: 2.4 while the trips were worth seconds (2026-11-03), 0 since the trips
                                                    # were cut to variety; the fastest mile the engine can produce stays about 1:45.6-1:45.9 (Patrick)


def squeeze(x, half=False):
    """A time on the 2026-10-27 clock onto the honest clock."""
    hs = HALF_SLOWER if half else 0.0
    return SQUEEZE_REF + (x - hs - SQUEEZE_REF) * SQUEEZE + hs + CLOCK_SHIFT


# seconds a point of each racing stat is worth. Speed is the headline stat by design: the one a player most wants,
# worth the most on both tracks (and most of all on the half-mile's tight turns); Finish next, stamina after.
SPEED_S = {"mile": 0.9, "half": 1.0}
FINISH_S = {"mile": 0.7, "half": 0.6}
# rating weights, measured off race times (seconds per point, scaled so Speed + Finish = 2 as before)
W_SPEED, W_FINISH, W_STAM = 1.15, 0.85, 0.66
GAIT_W = 0.7                  # what a point of manners (to its cap) is worth in a rating, measured off race times
MISFIRE = 0.55                # share of its positive speed and stamina a horse shows from the worst trip
TRIP_LOSS = 2.2               # seconds the worst trip costs: shuffled back, parked wide, checked in traffic


# Post Time Tonic, by kind: the lift to each stat for one start. Sized so a single is worth about half a length on
# average and the premium (all four, each at about three-quarters strength) about a length and a half.
TONIC_D = {"speed": ("early_speed", 0.106), "stamina": ("stamina", 0.18), "finish": ("late_speed", 0.13), "manners": ("gait", 0.23)}
TONIC = {k: {t: d} for k, (t, d) in TONIC_D.items()} | {"premium": {t: d * 0.72 for t, d in TONIC_D.values()}}


def race(field, track="mile", passing=False):
    """One-mile race on a mile or half-mile track. Returns finishing order.
    Post 1 is inside. Half-mile tracks have four turns: outside posts lose far
    more ground and early speed matters more than the late kick."""
    half = track == "half"
    results = []
    stats = {h.id: {t: soft(v) for t, v in h.current(track).items()} for h in field}   # extremes tell less and less
    for h in field:                                            # Post Time Tonic: a flat lift to its stat for tonight only
        for t, d in TONIC.get(getattr(h, "tonic_on", None), {}).items():
            stats[h.id] = dict(stats[h.id], **{t: stats[h.id][t] + d})
        for t, d in (getattr(h, "drive_on", None) or {}).items():   # and the driver's touch
            stats[h.id] = dict(stats[h.id], **{t: stats[h.id][t] + d})
    trip_q = {h.id: max(0.0, min(1.0, TRIP0 + TRIP_K * stats[h.id]["gait"] + rng.gauss(0, TRIP_LUCK))) for h in field}
    got = {h.id: trip_q[h.id] >= 0.35 for h in field}         # under that, the Prime is lost: the horse ends up somewhere else
    seat = {h.id: stats[h.id]["early_speed"] + (STYLE_SEAT[style_of(h)] if got[h.id]                # where each wants to sit, and can
                                                 else rng.choice(list(STYLE_SEAT.values())) - 0.8) for h in field}   # rank: shuffled somewhere else
    leaders = sorted(field, key=lambda h: -seat[h.id])[:3]
    e = [stats[h.id]["early_speed"] for h in leaders] + [0, 0]
    mean_e = sum(stats[h.id]["early_speed"] for h in field) / len(field)
    # how hard the lead is fought for (1 = a speed duel): two quick ones close together, both clearly faster
    # than the rest; an even field just files in behind whoever is inside
    heat = max(0.0, min(1.0, 1 - (e[0] - e[1]) / 1.2)) * max(0.0, min(1.0, (e[1] - mean_e) / 0.8))
    for post, h in enumerate(field, 1):
        p = stats[h.id]
        g = min(1.0, trip_q[h.id] / 0.9)                     # 0.9 and up is a perfect trip
        q = MISFIRE + (1 - MISFIRE) * g
        x = lambda v: v if v < 0 else q * v                    # the trip lets a horse show what's good in it
        t = 115.0 - SPEED_S[track] * x(p["early_speed"]) \
            - FINISH_S[track] * x(p["late_speed"]) - 0.5 * x(p["stamina"])
        t += HALF_SLOWER if half else 0
        t += (0.15 if half else 0.05) * (post - 1)             # ground lost from the outside
        st = style_of(h); closer = h not in leaders and st == "late"
        pocket = h is leaders[1] if len(leaders) > 1 else False   # second to the front tucks in behind the leader
        boxed = pocket and rng.random() < (LANE_BOXED if passing else POCKET_BOXED)
        lane = pocket and passing and not boxed                # the stretch opens a lane inside the leader: the pocket horse takes it
        trip = f"post {post}, " + ("on the lead" if h is leaders[0] else
                                   ("sat in the pocket, boxed in" if boxed else "sat in the pocket, up the passing lane" if lane else "sat in the pocket") if pocket else
                                   "parked first-over" if h in leaders else
                                   "sat in behind, came from off the pace" if closer else
                                   "sat mid-pack, moved after the half" if st == "mid" else "sat in behind")
        if h in leaders and h is not leaders[0] and not pocket:
            t += 0.3 - 0.1 * p["stamina"]                      # first-over / parked out
        if boxed:
            t += POCKET_BOX_COST                               # nowhere to go till the leader tires or the field fans out
        if lane:
            t -= LANE_GAIN                                     # a clear run up the inside, saving ground
        if passing and h is leaders[0]:
            t += LANE_LEADER                                   # the leader can't drop to the rail and shut the door
        # pace: a contested lead burns the front-runners (stamina softens it) and sets it up for the
        # closers; an uncontested lead lets the leader steal a breather
        if h is leaders[0]:
            t += PACE_COST * heat * (1 - 0.15 * p["stamina"]) - STEAL * (1 - heat)
        elif h in leaders:
            t += (0.25 if pocket else 0.5) * PACE_COST * heat * (1 - 0.15 * p["stamina"])   # the pocket tracks a hot pace; first-over fights it
        elif h not in leaders:                                 # sitting off a hot pace pays, the more so the further back
            t -= CLOSE_GAIN * heat * STYLE_KICK[st] * got[h.id]   # the kick off a hot pace needs the trip that sets it up
        if rng.random() < 1 / (1 + 2.718 ** (0.9 * p["gait"] + 5.0)):   # about 1 start in 25 breaks; a rough-gaited horse 1 in 6
            t += 4.0                                           # broke stride
            trip += ", broke stride"
        t += TRIP_LOSS * (1 - g)
        if not got[h.id]:
            trip += ", never got the trip"
        h.trip = trip                                          # public: what the chart caller saw
        t += rng.gauss(0, 0.8)    # race-day noise; with class-matched fields favorites win ~35-40%; with class-matched fields favorites win ~35-40%
        h.raw_time = t            # the race's own seconds: what ratings are read from
        h.last_time = clock(t, half)    # public: the clock is the one absolute measure of a horse
        results.append((t, h))
    return [h for _, h in sorted(results, key=lambda r: r[0])]


# ---------------------------------------------------------------- self-checks
def mean_score(pairs, n=400):
    return st.mean(breed(s, d).race_score() for s, d in pairs for _ in range(n // len(pairs)))


if __name__ == "__main__":
    good = [founder({t: 0.5 for t in TRAITS}) for _ in range(20)]
    avg = [founder() for _ in range(200)]
    pair = lambda a, b: [(rng.choice(a), rng.choice(b)) for _ in range(40)]

    gg, aa = mean_score(pair(good, good)), mean_score(pair(avg, avg))
    print(f"good x good {gg:6.2f}   avg x avg {aa:6.2f}")
    assert gg > aa + 1, "good matings must beat average ones on average"

    # Balance: a mare weak in gait. Sire A is strong in gait; sire B has the same
    # total genetic merit but spent on early speed. A should produce better racers.
    ma = mb = 0
    for _ in range(8):                                        # eight mares, so one odd draw can't decide it
        mare = founder({"gait": -1.0, "early_speed": 0.5})
        sire_a = founder({"gait": 1.0})
        sire_b = founder({"early_speed": 1.0})
        for h in (mare, sire_a, sire_b):
            h.line = 0
        ma += mean_score([(sire_a, mare)], 500) / 8
        mb += mean_score([(sire_b, mare)], 500) / 8
    print(f"complementary sire {ma:6.2f}   same-strength sire {mb:6.2f}")
    assert ma > mb, "covering the mare's weakness must beat stacking her strength"

    # Heritability: slope of offspring on mid-parent potential, roughly 0.2-0.5.
    xs, ys = [], []
    for _ in range(3000):
        s, d = rng.choice(avg), rng.choice(avg)
        f = breed(s, d)
        xs.append((s.potential["stamina"] + d.potential["stamina"]) / 2)
        ys.append(f.potential["stamina"])
    mx, my = st.mean(xs), st.mean(ys)
    h2 = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    print(f"heritability (slope) {h2:4.2f}")
    assert 0.12 <= h2 <= 0.5, h2                          # FOAL_H/FOAL_SCALE regress foals hard on purpose: ~0.17

    # Freaks: foals clearly better than both parents exist but are rare.
    freaks = 0
    for _ in range(3000):
        s, d = rng.choice(avg), rng.choice(avg)
        f = breed(s, d)
        if f.race_score() > max(s.race_score(), d.race_score()) + 3:
            freaks += 1
    print(f"freak rate {freaks / 30:4.1f}%")
    assert 1 <= freaks / 30 <= 12, freaks

    # Inbreeding: full-sib mating worse than unrelated mating of equal stock.
    s, d = good[0], good[1]
    sibs = [breed(s, d) for _ in range(40)]
    sib_pairs = [(rng.choice(sibs), rng.choice(sibs)) for _ in range(40)]
    # same genes as s and d but new ids: genetically equal, unrelated on paper
    s2, d2 = (Horse(h.genes, h.line, recessive=h.recessive) for h in (s, d))
    out_pairs = [(rng.choice(sibs), breed(s2, d2)) for _ in range(40)]
    ib, ob = mean_score(sib_pairs, 800), mean_score(out_pairs, 800)
    print(f"sib x sib {ib:6.2f}   outcross {ob:6.2f}")
    assert INBRED > 0 or abs(ib - ob) < 1.5, "inbreeding is free: a sib cross scores like an outcross"   # within sampling noise

    # Racing: in class-conditioned fields (24 horses split into 3 classes of 8,
    # shuffled posts) the best horse should win ~35-40%, like real favorites.
    fav = n = 0
    for _ in range(40):                                            # many fields: each horse's Prime is fixed, so few fields swing it
        pool = sorted((founder() for _ in range(24)), key=lambda h: -h.race_score(h.age))
        for start in range(0, 24, 8):
            field = pool[start:start + 8]
            for _ in range(50):
                rng.shuffle(field)
                fav += race(field)[0] is max(field, key=lambda h: h.race_score(h.age))
                n += 1
    print(f"favorite win rate {fav / n:4.2f}")
    assert 0.30 <= fav / n <= 0.45, fav / n
    same = [founder() for _ in range(8)]
    for h in same[1:]:
        h.potential, h.age, h.style = dict(same[0].potential), same[0].age, same[0].style   # same Prime too, or style masks the post
    post_wins = [0] * 8
    for _ in range(2000):
        post_wins[same.index(race(same)[0])] += 1
    print("wins by post, equal horses, mile", post_wins)
    assert post_wins[0] > post_wins[7], "inside post must help"
    half_wins = [0] * 8
    for _ in range(2000):
        half_wins[same.index(race(same, "half")[0])] += 1
    print("wins by post, equal horses, half", half_wins)
    assert half_wins[0] > post_wins[0] and half_wins[7] < post_wins[7], "half-mile post bias must be stronger"

    # Careers: peaks mostly at 4-6 with real early and late types; rise, then fall.
    pop = [founder() for _ in range(3000)]
    peaks = [h.peak_age for h in pop]
    early, late = st.mean(p <= 3 for p in peaks), st.mean(p >= 7 for p in peaks)
    print(f"peak age mean {st.mean(peaks):4.2f} sd {st.pstdev(peaks):4.2f}  early(3) {early:4.2f}  late(7) {late:4.2f}")
    assert 4.6 <= st.mean(peaks) <= 5.4 and 0.08 <= early <= 0.25 and 0.08 <= late <= 0.25
    curve = [st.mean(h.race_score(a) for h in pop) for a in range(2, 13)]
    print("mean ability by age 2..12:", [f"{c:4.1f}" for c in curve])
    assert curve[0] < curve[3] and curve[3] > curve[7] > curve[10], "rise, peak, decline"
    drop = [h.race_score(5) - h.race_score(9) for h in pop]
    print(f"decline 5->9: median {st.median(drop):4.1f}  10% fade less than {sorted(drop)[300]:4.1f}  10% fade more than {sorted(drop)[2700]:4.1f}")
    assert sorted(drop)[2700] > 2 * st.median(drop), "some horses must fall off a cliff while most fade"
    # The cliff: by 10 most horses are far below their 8-year-old selves; a few hold up.
    cliff = [h.race_score(8) - h.race_score(10) for h in pop]
    held = st.mean(x < 4.0 for x in cliff)
    print(f"8 -> 10: median drop {st.median(cliff):4.1f} score (~{6 * st.median(cliff):.0f} rating points); {held:.0%} hold within 4")
    assert st.median(cliff) > 4 and 0.02 <= held <= 0.15, "after 8 most horses fall away; only a few hold up"
    # Heritable: foals of early peakers peak earlier than foals of late peakers.
    def foals_of(pick):
        ps = [h for h in pop if pick(h)]
        return st.mean(breed(rng.choice(ps), rng.choice(ps)).peak_age for _ in range(500))
    fe, fl = foals_of(lambda h: h.peak_age <= 3), foals_of(lambda h: h.peak_age >= 6)
    print(f"foal peak age: early x early {fe:4.2f}  late x late {fl:4.2f}")
    assert fe < fl - 0.5
    print("all checks passed")
