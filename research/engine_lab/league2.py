"""Test league v2 (PC copy only, nothing saved). One independent history of the live world under one isolated rule change.
    python league2.py <variant> <seasons> <seed>
variants: base | book30 | spread | nick3 | herit | combo (book30 + spread + nick3 + herit)
Every variant has the same 12 strategy barns ($5M each) and uses the same seed for the same history number, so
variants compare on matching starting worlds and random inputs.

Definitions (also in the report):
  potential   a horse's fixed genetic peak: race_score at age 4 from its inherited potential (no training, no racing).
  true        what it is today on the 0-99 scale (circuit.true_rating): ceiling for its age, development, training shape.
  est         the public's estimate, from results; tiers are graded on it.
  midparent   the mean of the sire's and dam's potential."""
import os, sys, json, random, statistics as st, collections, math
VARIANT, SEASONS, SEED = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
sys.argv = ["x"]
os.chdir(r"C:\Users\spooh\HarnessSim"); sys.path.insert(0, ".")
import app, circuit as c, economy as e, sim
SP = os.path.dirname(os.path.abspath(__file__))
app.SAVE = os.path.join(SP, "live", "live_save.pkl")
app.load()
app.save = lambda *a, **k: None
app.snapshot = lambda *a, **k: None
sim.rng.seed(SEED); c.rng.seed(SEED); e.rng.seed(SEED); random.seed(SEED)
c.HUMAN.clear()
H = lambda: app.G["horses"]
POT = lambda h: h.race_score(4)

PKG = {"book30", "spread", "nick2"}
ON = {"book30": {"book30"}, "spread": {"spread"}, "nick3": {"nick3"}, "herit": {"herit"},
      "combo": {"book30", "spread", "nick3", "herit"},
      "pkg": PKG, "pkg_dim": PKG | {"dim"}, "pkg_reset": PKG | {"reset"}, "pkg_both": PKG | {"dim", "reset"}}.get(VARIANT, set())
if "nick2" in ON:
    sim.NICK_W = 0.35 * 2
if "dim" in ON:                                                    # stronger diminishing returns at the top of each trait
    sim.SOFT_AT, sim.SOFT_ROOM = 3.5, 2.0
if "reset" in ON:                                                  # slightly more genes reset toward the breed average
    sim.MUTATE = 0.15
if "book30" in ON:
    e.BOOK = 30
if "nick3" in ON:
    sim.NICK_W = 0.35 * 3
if "herit" in ON:
    sim.FOAL_H, sim.MUTATE = 0.9, 0.05

# ---- strategy barns: 12 barns, same budget, each with a plan. "ordinary" picks any affordable sire at random.
STRATS = ["top_sire"] * 2 + ["speed"] * 2 + ["balanced"] * 2 + ["nick"] * 2 + ["inbreed"] * 2 + ["ordinary"] * 2
ai = sorted(app.G["ai"], key=lambda o: -e.cash.get(o, 0))
STRAT = dict(zip(ai[:12], STRATS))
for o in STRAT:
    e.cash[o] = 6_000_000


def pick_sire(mare, stallions, strat):
    if strat == "top_sire":
        return max(stallions, key=POT)
    if strat == "speed":
        return max(stallions, key=lambda s: s.potential["early_speed"] + s.potential["late_speed"])
    if strat == "balanced":
        weak = min(sim.RACE_TRAITS, key=lambda t: mare.potential[t])
        return max(stallions, key=lambda s: s.potential[weak] + 0.5 * POT(s))
    if strat == "nick":                                           # the best known nick, then quality
        return max(stallions, key=lambda s: sim.NICK[s.line, mare.line] * 3 + POT(s))
    if strat == "inbreed":
        return max(stallions, key=lambda s: POT(s) + 0.5 * len(s.ancestors() & mare.ancestors()))
    return random.choice(stallions)


BIRTHS = []                                                       # (season, strat or None, midparent, nick, foal potential, sire id, dam id)
SEASON = [0]
_book = e.book_mare


def book_logged(mare, stallion, owner, horses, fee=None, day=None):
    r = _book(mare, stallion, owner, horses, fee, day)
    if r is not None:
        f = e.nursery[-1]
        BIRTHS.append((SEASON[0], STRAT.get(owner), (POT(stallion) + POT(mare)) / 2, sim.NICK[stallion.line, mare.line], POT(f), stallion.id, mare.id))
    return r


e.book_mare = book_logged
orig_ai = e.ai_breeding


def spread_ai(horses, ai_, day=None):
    """AI mares spread over the stud book: weighted toward quality and the pairing's nick, not 70% to the leader."""
    stallions = [s for s in e.studs(horses) if e.covers_sold(s) < e.BOOK]
    for d in [h for h in horses if h.sex == "f" and h.retired and h.owner in ai_]:
        if e.barn_size.get(d.owner, 0) >= e.BARN_MAX or any(m is d for m, _ in e.bookings):
            continue
        ok = [s for s in stallions if e.covers_sold(s) < e.BOOK and e.cash.get(d.owner, 0) - e.AI_RATE * e.house_price(s) > e.RESERVE]
        if ok:
            w = [math.exp(0.6 * POT(s) + 1.5 * sim.NICK[s.line, d.line]) for s in ok]
            s = random.choices(ok, w)[0]
            e.book_mare(d, s, d.owner, horses, e.AI_RATE * e.house_price(s), day)


def league_breeding(horses, ai_, day=None):
    stallions = [s for s in e.studs(horses) if e.covers_sold(s) < e.BOOK]
    for d in [h for h in horses if h.sex == "f" and h.retired and h.owner in STRAT]:
        room = [x for x in stallions if e.covers_sold(x) < e.BOOK]
        if any(m is d for m, _ in e.bookings) or not room:
            continue
        s = pick_sire(d, room, STRAT[d.owner])
        e.book_mare(d, s, d.owner, horses, e.stud_fee(s), day)
    rest = [o for o in ai_ if o not in STRAT]
    (spread_ai if "spread" in ON else orig_ai)(horses, rest, day)


e.ai_breeding = league_breeding

RACES = []
_run = c.run_race


def logged(r, alive, log):
    _run(r, alive, log)
    f = [h for h in r["field"] if getattr(h, "results", None) and h.results[-1].get("day") == c.DAY[0]]
    if len(f) >= 2:
        w = min(f, key=lambda h: h.results[-1]["place"])
        RACES.append((w is max(f, key=lambda h: h.est), sim.style_of(w)))


c.run_race = logged


def root(h, k=0):
    """The sire line's founder: follow sires up until there is none."""
    while getattr(h, "sire", None) is not None and k < 40:
        h, k = h.sire, k + 1
    return h.id


def related(a, b):
    A, B = a.ancestors(3), b.ancestors(3)
    return len(A & B) / max(1, len(A | B))


rows, at4 = [], collections.defaultdict(list)                     # crop season -> true ratings of that crop at age 4
for season in range(SEASONS + 1):
    SEASON[0] = season
    racers = [h for h in H() if not h.retired]
    crop2 = [h for h in H() if h.age == 2]
    for h in H():
        if h.age == 4 and not getattr(h, "_seen4", False):
            h._seen4 = True
            at4[season - 2].append((c.true_rating(h), POT(h), h.retired))
    sires = collections.Counter(h.sire.id for h in racers if h.sire)
    lines = collections.Counter(root(h) for h in racers)
    studs = e.studs(H())[:12]
    rel = [related(a, b) for i, a in enumerate(studs) for b in studs[i + 1:]]
    tiers = collections.Counter(app.tier_label(h) for h in racers)
    rs = RACES[:]; RACES.clear()
    pot_all = sorted(POT(h) for h in crop2) or [0]
    rows.append(dict(
        season=season, racers=len(racers),
        crop2_n=len(crop2), crop2_pot=round(st.mean(pot_all), 3), crop2_p90=round(pot_all[int(.9 * (len(pot_all) - 1))], 3),
        racer_pot=round(st.mean(POT(h) for h in racers), 3), racer_true=round(st.mean(c.true_rating(h) for h in racers), 2),
        racer_est=round(st.mean(h.est for h in racers), 2), racer_age=round(st.mean(h.age for h in racers), 2),
        s_share=round((tiers["S"] + tiers["S+"]) / max(1, len(racers)), 4),
        top5=round(sum(n for _, n in sires.most_common(5)) / max(1, sum(sires.values())), 3), uniq_sires=len(sires),
        top3_lines=round(sum(n for _, n in lines.most_common(3)) / max(1, len(racers)), 3), uniq_lines=len(lines),
        stud_related=round(st.mean(rel), 3) if rel else None,
        fav_win=round(st.mean(x[0] for x in rs), 3) if rs else None,
        stud_income={o: round(e.ledger.get(o, {}).get("stud", 0)) for o in list(STRAT)[:0]},
        strat_cash={s: round(st.mean(e.cash.get(o, 0) for o in STRAT if STRAT[o] == s)) for s in set(STRATS)}))
    if season % 10 == 0:
        print(VARIANT, SEED, json.dumps(rows[-1]), flush=True)
    if season < SEASONS:
        for _ in range(c.YEAR):
            app.tick()
json.dump(dict(rows=rows, births=BIRTHS, at4={k: v for k, v in at4.items()}), open(os.path.join(SP, "l2", f"{VARIANT}_{SEED}.json"), "w"))
print("done", VARIANT, SEED)
