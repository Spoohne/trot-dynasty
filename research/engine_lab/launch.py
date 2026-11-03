"""Launch scenario v1 (DECISIONS 58-74; Patrick 2026-11-02: plan for 50-100 players at the high end).

A fresh world run season after season under the launch breeding rules, with player bots in it:
  - AI Filler Barns (the computer's) never breed. Each year turn their racing strings are topped up with 2-year-olds from a fixed recipe
    (AI_SHIFT, the founders' own stock), holding AI_RACERS racers in all, less what the players race (floor AI_FLOOR).
  - The stud book at Year 0 is a curated set of CURATED stallions (owner "book"). They stand until 20. After that the
    book is only what players list, at LIST_FEE a season. AI stallions never stand.
  - AI horses race in claimers, so players can claim them (2 claims a night each, as live); claimed horses race and breed.
  - Player-Bot Barns (simulated players) arrive as a trickle and some quit each season. Four kinds (STRATS): chasers breed best-to-best from
    the public record, stud farms stand and list their colts, flippers claim and buy house horses, casual players
    do a little of everything. Bots only see what players see: public estimates, never genes.
Recorded beside the encyclopedia's tables (same file layout, so research/encyclopedia/serve.py can open it):
  bots      one row per bot per season: kind, arrival, quit, cash, racers, mares, the season's purses
  foals     every foal: breeder kind, sire and his source (curated or player-listed), its genetic potential and its parents'
  world     one JSON row per season: player herd vs AI, S+ share, stud book, sire concentration, pedigree strength

  python research/engine_lab/launch.py <players> <seed> [seasons=100] [mutate]   -> research/engine_lab/launch/p<players>_s<seed>[_m<mutate>].db
  python research/engine_lab/launch.py check                             2 seasons, 12 players, with self-checks
"""
import importlib.util
import json
import os
import random
import statistics as st
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CHECK = sys.argv[1:2] == ["check"]
PLAYERS, SEED = (12, 7) if CHECK else (int(sys.argv[1]), int(sys.argv[2]))
SEASONS = 6 if CHECK else int(sys.argv[3]) if len(sys.argv) > 3 else 100
MUTATE = float(sys.argv[4]) if len(sys.argv) > 4 else None   # a test of the gene-revert chance (sim.MUTATE; None: the game's own)
OUT = os.path.join(HERE, "launch")
os.makedirs(OUT, exist_ok=True)
DB = os.path.join(OUT, "check.db" if CHECK else f"p{PLAYERS}_s{SEED}" + (f"_m{MUTATE:g}" if MUTATE is not None else "") + ".db")

sys.argv = ["sim100.py", "0", DB]                                # sim100 reads its own argv at import
spec = importlib.util.spec_from_file_location("sim100", os.path.join(ROOT, "research", "encyclopedia", "sim100.py"))
S100 = importlib.util.module_from_spec(spec); spec.loader.exec_module(S100)
app, c, e, sk, sim, O = S100.app, S100.c, S100.e, S100.sk, S100.sim, S100.O
if MUTATE is not None:
    sim.MUTATE = MUTATE

AI_SHIFT = 0.0                 # the AI top-up recipe: founders' stock, every season (Patrick tunes this by hand, D60)
AI_RACERS, AI_FLOOR = 900, 300  # AI racers in all, less the players' racers; never fewer than the floor
CURATED = 25                   # the Year-0 stud book
CURATED_SHIFT = (0.0, 0.8)     # its quality spread: founders' stock up to a clear cut above
LIST_FEE = 25_000              # shortcut: a player's stallion listing, per season; the real fee isn't designed yet (D52)
REG_FEE = e.REG_FEE            # registering a foal at 2
STRATS = (("chaser", .3), ("studfarm", .2), ("flipper", .2), ("casual", .3))
QUIT = {"chaser": .12, "studfarm": .12, "flipper": .2, "casual": .3}   # chance a bot leaves at a year turn
MARES = {"chaser": 12, "studfarm": 12, "flipper": 2, "casual": 3}      # broodmares a bot keeps (its breeding barn caps it too)
MARE_BAR = 58                  # a filly worth breeding from, on her public peak rating
SIRE_BAR = 60                  # a colt worth standing to your own mares (Patrick: a public book is optional; lines are private)
SIRES = {"chaser": 2, "studfarm": 3, "flipper": 0, "casual": 1}    # private stallions a bot keeps for its own mares
FEE_W = {"chaser": .5, "studfarm": 1, "flipper": 2, "casual": 2}    # rating points a bot gives up for each $10k of stud fee
RESERVE = {"chaser": 60_000, "studfarm": 60_000, "flipper": 40_000, "casual": 120_000}
CLAIMS_A_NIGHT = 2

for r in (sim.rng, random):
    r.seed(SEED)
rng = sim.rng
ai = set()
bots = {}                       # owner -> {"strat", "arrived", "quit"}
BOOKED = {}                     # owner -> purses booked up to the last season's end


def active():
    return [o for o, b in bots.items() if b["quit"] is None]


def scale(h):
    return c.on_aged_scale(h.est, c.age_group(h))


def pot(h):
    """Genetic quality: the horse's race score at 4 from its inherited potential (no training, no racing). Unseen by bots."""
    return h.race_score(4)


# ---------------------------------------------------------------- the launch rules
def studs(horses):
    """The public stud book: the curated stallions while they stand, and the stallions players list. Best first."""
    return sorted((h for h in horses if h.sex == "m" and h.retired and (h.owner == "book" or getattr(h, "listed", False))),
                  key=lambda s: -c.peak_est(s))


e.studs = studs
e.ai_breeding = lambda *a, **k: None                              # D59: AI barns don't breed
e.AI_TRADES[0] = False                                           # as live: only players claim and bid
# bots live under the players' barn levels (stalls, breeding license, broodmare head), though the trainer enters their
# horses the way it does for AI barns (they're not in c.HUMAN, so no orders are needed)
_stalls, _head, _can = e.stalls, e.barn_head, e.can_breed
e.stalls = lambda o: e.LEVELS[e.level.get(o, 0)][1] if o in bots else _stalls(o)
e.barn_head = lambda o: e.LEVELS[e.level.get(o, 0)][4] if o in bots else _head(o)
e.can_breed = lambda o: e.LEVELS[e.level.get(o, 0)][2] if o in bots else _can(o)
# Patrick 2026-11-02: foals take nursery space, apart from racing stalls and far bigger: two crops per broodmare slot.
# book_mare checks racing stalls + foals on the way, so for a bot "on the way" reads as just enough to pass while the
# nursery has room, and as full when it hasn't. A racing stall is needed only at 2, when the foal is registered.
_on_the_way = e.on_the_way
nursery_cap = lambda o: 2 * e.barn_head(o)
e.on_the_way = lambda o: (-e.barn_size.get(o, 0) if _on_the_way(o) < nursery_cap(o) else 10 ** 6) if o in bots else _on_the_way(o)
AIM = {"chaser": 4, "studfarm": 4, "flipper": 3, "casual": 2}    # the barn level each kind saves up for


def made(shift, age, sex=None, retired=False):
    """A horse from the fixed recipe, rated on what it is (like the founders)."""
    h = sim.founder({t: shift for t in c.RACE_TRAITS})
    while sex and h.sex != sex:
        h = sim.founder({t: shift for t in c.RACE_TRAITS})
    h.age = age
    c.init_public(h)
    if retired:                                                  # a horse with a past: its reputation is its prime
        now, h.age = h.age, h.peak_age
        h.est = c.true_rating(h) + rng.gauss(0, 3)
        h.age = now
        h.peak_est, h.est_sd = h.est, 6.0
        h.developed = {t: h.ceiling(t, h.peak_age) for t in c.RACE_TRAITS}
        c.retire(h)
    return h


def curated_book(horses):
    lo, hi = CURATED_SHIFT
    for k in range(CURATED):
        h = made(lo + (hi - lo) * k / (CURATED - 1), rng.randint(5, 12), "m", retired=True)
        h.owner = "book"
        e.settled[h.id] = (0, 0)
        horses.append(h)
    e.cash["book"], e.ledger["book"] = 0, {}


def top_up(horses):
    """The AI barns' new crop: 2-year-olds from the fixed recipe, holding the AI's share of the racing population."""
    player_racers = sum(1 for h in horses if h.owner in bots and not h.retired)
    want = max(AI_FLOOR, AI_RACERS - player_racers) / len(ai)
    have = {o: 0 for o in ai}
    for h in horses:
        if h.owner in have and not h.retired:
            have[h.owner] += 1
    for o in ai:
        for _ in range(max(0, round(want) - have[o])):
            h = made(AI_SHIFT, 2)
            h.owner = o
            c.assign(h, c.BARN_TRAINER.get(o, c.HOUSE)) or c.assign(h, c.HOUSE)
            e.settled[h.id] = (0, 0)
            horses.append(h)


_new_year = e.new_year


def new_year(horses, ai_):
    horses = _new_year(horses, ai_)
    horses = [h for h in horses if not (h.retired and h.owner in ai)]   # AI breeding stock has no use: it never breeds
    register(horses)
    top_up(horses)
    e.settle(horses)
    return horses


e.new_year = new_year


def register(horses):
    """A bot's crop turns 2: it registers the best it has a racing stall and the fee for; the rest go to the house."""
    grads = [h for h in horses if h.owner in bots and h.age == 2 and getattr(h, "breeder", None) == h.owner and not getattr(h, "reg", False)]
    for h in sorted(grads, key=scale, reverse=True):
        b = bots[h.owner]
        racers = sum(1 for x in horses if x.owner == h.owner and not x.retired and (x not in grads or getattr(x, "reg", False)))
        keep = b["quit"] is None and racers < e.stalls(h.owner) and e.cash.get(h.owner, 0) >= REG_FEE + RESERVE[b["strat"]] / 2 \
            and (b["strat"] == "casual" or scale(h) >= 45)
        if keep:
            e.book(h.owner, "registry", -REG_FEE)
            h.reg = True
        else:
            horses.remove(h)
            e.book(h.owner, "sales", e.UNREG_SALE)


# ---------------------------------------------------------------- the bots
def arrive(horses, owner, strat, season):
    """A new player's start, as start_from_history gives one: a few B/C racers bought out of the AI barns, a broodmare
    from the lower half of the band, the starting cash and a trainer."""
    bots[owner] = {"strat": strat, "arrived": season, "quit": None}
    e.cash[owner], e.ledger[owner], e.level[owner] = e.PLAYER_START[1], {}, 0
    c.BARN_TRAINER[owner] = rng.choice(c.ROSTER)
    lo, hi = e.STARTER
    pool = [h for h in horses if h.owner in ai and not h.retired and 2 <= h.age <= 4 and lo <= scale(h) <= hi and h.id not in c.CLAIMS]
    picks = rng.sample(pool, min(3, len(pool)))
    for h in picks:
        e.drop_auction(h.id)
        if getattr(h, "trainer", None):
            h.trainer.horses -= 1
        h.owner = owner
        c.assign(h, c.BARN_TRAINER[owner]) or c.assign(h, c.HOUSE)
    m = made(AI_SHIFT, rng.randint(6, 10), "f", retired=True)
    m.owner = owner
    e.settled[m.id] = (0, 0)
    horses.append(m)
    e.settle(horses)


def leave(horses, owner, season):
    bots[owner]["quit"] = season
    for f in [f for f in e.nursery if f.owner == owner]:
        e.nursery.remove(f)
    for h in [h for h in horses if h.owner == owner]:
        if getattr(h, "trainer", None):
            h.trainer.horses -= 1
        horses.remove(h)
    for hid in [hid for hid, o in c.CLAIMS.items() if o == owner]:
        del c.CLAIMS[hid]


def pick_sire(mare, owner, strat, horses):
    """Bots read the stud book the way players do: by each stallion's public record and fee."""
    reserve = RESERVE[strat]
    own = [s for s in horses if s.owner == owner and s.retired and s.sex == "m" and s not in studs(horses)]   # covers its own mares free
    ok = [s for s in studs(horses) + own if e.covers_sold(s) < e.BOOK and not e.too_close(s, mare)
          and (s.owner == owner or e.cash.get(owner, 0) - e.stud_fee(s) >= reserve)]
    if not ok:
        return None
    # value for money, with each owner's own taste: a chaser pays up for the record, a flipper wants a bargain; a full
    # book is out (above), so demand spills to the next sire. Your own stallion covers free.
    fee_w, taste = FEE_W[strat], 4 if strat == "casual" else 2
    return max(ok, key=lambda s: c.peak_est(s) - fee_w * (0 if s.owner == owner else e.stud_fee(s)) / 10_000 + rng.gauss(0, taste))


def mare_cap(o, strat, horses):
    """How many broodmares a bot keeps, and the stallions it keeps (they share the breeding barn)."""
    mine = sorted((s for s in horses if s.owner == o and s.retired and s.sex == "m"), key=c.peak_est, reverse=True)
    keep_m = [s for s in mine if getattr(s, "listed", False)] + [s for s in mine if not getattr(s, "listed", False)
                                                               and c.peak_est(s) >= SIRE_BAR][:SIRES[strat]]   # private stallions
    return max(1, min(MARES[strat], e.barn_head(o) - len(keep_m))), keep_m


def want_racers(o, strat, horses):
    """Racing stalls a bot fills, keeping a few open for the best of each crop it registers at 2."""
    mares = sum(1 for h in horses if h.owner == o and h.retired and h.sex == "f")
    keep = 0 if strat == "flipper" or not e.can_breed(o) else min(e.stalls(o) // 3, (mares + 1) // 2)
    return max(2, e.stalls(o) - keep)


def bot_week(horses, d, season):
    week = d % c.YEAR
    for o in active():
        strat = bots[o]["strat"]
        nxt = e.level.get(o, 0) + 1
        if nxt <= AIM[strat] and e.cash.get(o, 0) > e.LEVELS[nxt][3] + RESERVE[strat]:
            e.upgrade(o)
        mine = [h for h in horses if h.owner == o]
        for h in mine:
            if h.retired:
                continue
            past = h.age >= 10 or (h.age >= 7 and h.est < c.peak_est(h) - 12)
            sires = sum(1 for s in horses if s.owner == o and s.retired and s.sex == "m")
            breed_now = (strat in ("chaser", "studfarm") and h.sex == "f" and h.age >= 5 and c.peak_est(h) >= 62) \
                or (e.can_breed(o) and h.sex == "m" and h.age >= 5 and c.peak_est(h) >= SIRE_BAR + 4 and sires < SIRES[strat])
            if past or breed_now:
                c.retire(h)
            elif h.age >= 4 and scale(h) < 38:
                e.scrap(h, o, horses)
        cap, keep_m = mare_cap(o, strat, horses)
        mares = sorted((h for h in horses if h.owner == o and h.retired and h.sex == "f"), key=c.peak_est, reverse=True)
        if e.can_breed(o):                                               # a breeder fills its band from its own good fillies,
            for h in sorted((h for h in horses if h.owner == o and not h.retired and h.sex == "f" and h.age >= 4   # claimed ones too
                             and c.peak_est(h) >= MARE_BAR), key=c.peak_est, reverse=True)[:max(0, cap - len(mares))]:
                c.retire(h)
            mares = sorted((h for h in horses if h.owner == o and h.retired and h.sex == "f"), key=c.peak_est, reverse=True)
        stallions = [h for h in horses if h.owner == o and h.retired and h.sex == "m"]
        for h in mares[cap:] + [m for m in mares if c.peak_est(m) < 55] + [s for s in stallions if s not in keep_m]:
            if h in horses:
                e.scrap(h, o, horses)                                    # stock it has no room or use for goes to the house
        racers = sum(1 for h in horses if h.owner == o and not h.retired)
        if racers < want_racers(o, strat, horses) and e.cash.get(o, 0) > e.house_horse_price(o) + RESERVE[strat] and rng.random() < .5:
            e.buy_house_horse(o, horses)
        if 1 <= week <= 20:                                              # players have the books early (AI never books)
            for m in [h for h in horses if h.owner == o and h.retired and h.sex == "f" and h.age < c.BREEDING_UNTIL - 1]:
                if e.booked_to(m) is None and (s := pick_sire(m, o, strat, horses)):
                    e.book_mare(m, s, o, horses, day=d)


def bot_claims(horses):
    """Before post time: bots claim out of tonight's claimers on the public record (never their own, two a night)."""
    races = [r for r in c.CARD.get("races", []) if r["key"][4]]
    for o in active():
        strat = bots[o]["strat"]
        n = {"flipper": 2, "chaser": 1}.get(strat, 1 if rng.random() < .05 else 0)
        room = want_racers(o, strat, horses) - sum(1 for h in horses if h.owner == o and not h.retired)
        for r in sorted(races, key=lambda r: -r["key"][4]):
            if n <= 0 or room <= 0:
                break
            tag = r["key"][4]
            if e.cash.get(o, 0) < tag + RESERVE[strat]:
                continue
            best = max((h for h in r["field"] if h.owner != o and not getattr(h, "visitor", None) and h.id not in c.CLAIMS),
                       key=lambda h: h.est, default=None)
            if best and best.est >= c.CLASS_RATING[r["key"][2]] + (4 if strat == "flipper" else 8):   # a horse rated over its class
                c.CLAIMS[best.id] = o
                n -= 1; room -= 1
        # a breeder short of mares claims a filly to retire to its band (bot_week retires her): one a night
        cap, _ = mare_cap(o, strat, horses)
        short = e.can_breed(o) and sum(1 for h in horses if h.owner == o and h.retired and h.sex == "f") < cap
        if short and strat != "flipper" and e.barn_size.get(o, 0) < e.stalls(o):
            fillies = [(h, r["key"][4]) for r in races for h in r["field"] if h.sex == "f" and h.age >= 4 and h.owner != o
                       and not getattr(h, "visitor", None) and h.id not in c.CLAIMS and c.peak_est(h) >= MARE_BAR
                       and e.cash.get(o, 0) >= r["key"][4] + RESERVE[strat]]
            if fillies:
                c.CLAIMS[max(fillies, key=lambda x: c.peak_est(x[0]))[0].id] = o


def year_turn_bots(horses, season):
    """Quits, then this season's listings (each pays the fee or comes down)."""
    for o in active():
        b = bots[o]
        broke = e.cash.get(o, 0) < 10_000 and not any(h.owner == o and not h.retired for h in horses)
        if broke or rng.random() < QUIT[b["strat"]]:
            leave(horses, o, season)
    for o in active():
        strat = bots[o]["strat"]
        bar = {"studfarm": 60, "chaser": 70}.get(strat)
        for s in [h for h in horses if h.owner == o and h.retired and h.sex == "m"]:
            want = bar is not None and c.peak_est(s) >= bar
            if want and e.cash.get(o, 0) >= LIST_FEE + RESERVE[strat] / 2:
                e.book(o, "listing", -LIST_FEE)
                s.listed = True
            else:
                s.listed = False


def arrivals_for(season, horses):
    """How many bots arrive this season: 60% of the target in Year 0, the rest in Year 1, then replacements for those
    who quit. Spread over the season's weeks."""
    if season == 0:
        n = round(PLAYERS * .6)
    else:
        n = PLAYERS - len(active())
    weeks = sorted(rng.randrange(0, 30 if season == 0 else c.YEAR) for _ in range(max(0, n)))
    return weeks


# ---------------------------------------------------------------- what the world looks like each season
def measure(season, horses, born):
    racers = [h for h in horses if not h.retired and h.age >= 2]
    grp = lambda h: "ai" if h.owner in ai else "bred" if getattr(h, "breeder", None) in bots else "player"
    out = {"season": season, "players": len(active()), "groups": {}}
    for g in ("ai", "bred", "player"):
        hs = [h for h in racers if grp(h) == g]
        if hs:
            out["groups"][g] = {"n": len(hs), "rating": st.mean(O.rating(h) for h in hs), "pot": st.mean(pot(h) for h in hs),
                                "s_plus": sum(app.tier_label(h) == "S+" for h in hs) / len(hs),
                                "purses": sum(h.earnings - getattr(h, "season0", 0) for h in hs)}
    out["s_plus_all"] = sum(app.tier_label(h) == "S+" for h in racers) / len(racers)
    book = studs(horses)
    out["book"] = {"curated": sum(s.owner == "book" for s in book), "listed": sum(s.owner != "book" for s in book)}
    out["foals"] = len(born)
    if born:
        by = {}
        for f in born:
            by[f.sire.id] = by.get(f.sire.id, 0) + 1
        top = sorted(by.values(), reverse=True)
        out["sires_used"], out["top5_share"] = len(by), sum(top[:5]) / len(born)
        out["foal_pot"] = st.mean(pot(f) for f in born)
        out["from_curated"] = sum(f.sire.owner == "book" for f in born) / len(born)
        out["own_sire"] = sum(f.sire.owner == f.owner for f in born) / len(born)       # bred to the barn's own stallion
        if len(born) >= 20:
            mid = [(pot(f.sire) + pot(f.dam)) / 2 for f in born]
            out["pedigree_r"] = st.correlation(mid, [pot(f) for f in born])
    herds = {}                                                     # each breeding barn's homebred racers: how far apart the lines are
    for h in racers:
        if h.owner in bots and getattr(h, "breeder", None) == h.owner:
            herds.setdefault(h.owner, []).append(pot(h))
    means = sorted(st.mean(v) for v in herds.values() if len(v) >= 3)
    if len(means) >= 3:
        out["herd_top"], out["herd_median"] = means[-1], st.median(means)
    purses = {}                                                    # each barn's purses booked this season (a claimed horse's
    for o, led in e.ledger.items():                                # earlier earnings stay with the barn that won them)
        purses[o] = led.get("purses", 0) - BOOKED.get(o, 0)
        BOOKED[o] = led.get("purses", 0)
    total = sum(v for v in purses.values() if v > 0) or 1
    out["player_purse_share"] = sum(v for o, v in purses.items() if o in bots) / total
    out["top_barn_share"] = max((v for o, v in purses.items() if o in bots), default=0) / total
    return out, purses


def main():
    db = S100.open_db(DB)
    db.executescript("""
      CREATE TABLE bots(owner TEXT, season INTEGER, strat TEXT, arrived INTEGER, quit INTEGER, cash REAL, racers INTEGER,
        mares INTEGER, stallions INTEGER, purses REAL, level INTEGER, PRIMARY KEY(owner, season));
      CREATE TABLE foals(id INTEGER PRIMARY KEY, season INTEGER, owner TEXT, strat TEXT, sire INTEGER, dam INTEGER,
        sire_src TEXT, pot REAL, mid REAL);
      CREATE TABLE world(season INTEGER PRIMARY KEY, json TEXT);
    """)
    rec = S100.Recorder(db)
    c.HUMAN.clear(); c.STORIES.clear(); c.RECORDS.clear(); sk.CHAMPIONS.clear(); sk.HALL.clear(); sk.RATINGS.clear(); app._names.USED.clear()
    e.ROLLED[0] = None; c.EPOCH[0] = 0
    horses = e.world(barns=app.BARNS)
    ai.update(range(app.BARNS))
    horses = [h for h in horses if not h.retired]                  # the AI's founding broodmares and stallions: no use under D59
    for h in horses:
        h.foundation = True
    curated_book(horses)
    e.settle(horses)
    sk.new_calendar()
    db.execute("INSERT OR REPLACE INTO meta VALUES('seasons_planned', ?)", (str(SEASONS),))
    db.execute("INSERT OR REPLACE INTO meta VALUES('launch', ?)", (json.dumps({"players": PLAYERS, "seed": SEED, "ai_shift": AI_SHIFT,
               "curated": CURATED, "list_fee": LIST_FEE, "mutate": sim.MUTATE, "book": e.BOOK, "strats": STRATS, "quit": QUIT}),))
    t0, n_bots, log = time.time(), 0, []
    due = arrivals_for(0, horses)
    for d in range(SEASONS * c.YEAR):
        c.DAY[0] = d
        season, week = divmod(d, c.YEAR)
        if week == 0 and d:
            born = [f for f in e.nursery if f.age == 0]
            rec.season_end(season - 1, horses)
            m, purses = measure(season - 1, horses, born)
            db.execute("INSERT INTO world VALUES(?,?)", (season - 1, json.dumps(m)))
            db.executemany("INSERT INTO foals VALUES(?,?,?,?,?,?,?,?,?)", [
                (f.id, season - 1, str(f.owner), bots.get(f.owner, {}).get("strat"), f.sire.id, f.dam.id,
                 "curated" if f.sire.owner == "book" else "listed" if getattr(f.sire, "listed", False) else "own",
                 pot(f), (pot(f.sire) + pot(f.dam)) / 2) for f in born])
            db.executemany("INSERT INTO bots VALUES(?,?,?,?,?,?,?,?,?,?,?)", [
                (o, season - 1, b["strat"], b["arrived"], b["quit"], e.cash.get(o, 0),
                 sum(1 for h in horses if h.owner == o and not h.retired),
                 sum(1 for h in horses if h.owner == o and h.retired and h.sex == "f"),
                 sum(1 for h in horses if h.owner == o and h.retired and h.sex == "m"), purses.get(o, 0), e.level.get(o, 0))
                for o, b in bots.items() if b["quit"] is None or b["quit"] == season - 1])
            year_turn_bots(horses, season)
            sk.year_tick(horses, ai, d)
            due = arrivals_for(season, horses)
            db.execute("INSERT OR REPLACE INTO meta VALUES('season_done', ?)", (str(season),))
            db.commit()
            g = m["groups"]
            print(f"season {season}/{SEASONS}: {len(active())} players, {len(horses)} horses, S+ {m['s_plus_all']:.1%}, "
                  f"filler pot {g.get('ai', {}).get('pot', 0):.1f} bred pot {g.get('bred', {}).get('pot', float('nan')):.1f}, "
                  f"foals {m['foals']} top5 {m.get('top5_share', 0):.0%}, {(time.time() - t0) / season:.1f} s a season", flush=True)
        while due and due[0] <= week:
            due.pop(0)
            strat = rng.choices([s for s, _ in STRATS], [w for _, w in STRATS])[0]
            arrive(horses, f"p{n_bots:03d}", strat, season)
            n_bots += 1
        sk.ai_nominate(horses, ai | set(active()), d)
        sk.run_today(d, horses)
        if week:                                                    # a year turn draws its card after the roll
            c.draw_card(d, horses)
            bot_claims(horses)
        log.clear()
        horses = e.day(d, horses, ai, log)
        for hid in [hid for hid, o in c.CLAIMS.items() if o in bots]:   # a claim on a horse that didn't race in a claimer lapses
            del c.CLAIMS[hid]
        bot_week(horses, d, season)
        rec.night(d, horses)
        for h in horses:
            if getattr(h, "order", None) == "stakes":
                h.order = None
    rec.season_end(SEASONS - 1, horses)
    m, _ = measure(SEASONS - 1, horses, [f for f in e.nursery if f.age == 0])
    db.execute("INSERT OR REPLACE INTO world VALUES(?,?)", (SEASONS - 1, json.dumps(m)))
    db.execute("INSERT OR REPLACE INTO meta VALUES('season_done', ?)", (str(SEASONS),))
    db.execute("INSERT OR REPLACE INTO meta VALUES('finished', ?)", (time.strftime("%Y-%m-%d %H:%M"),))
    db.commit()
    if CHECK:
        self_check(db, horses)
    print("done", DB, flush=True)


def self_check(db, horses):
    foals = db.execute("SELECT owner, sire_src FROM foals").fetchall()
    assert foals, "bots bred no foals"
    assert all(o.startswith("p") for o, _ in foals), "a foal from a non-player dam: the AI must not breed"
    assert all(s.owner == "book" or (s.owner in bots and s.listed) for s in studs(horses)), "only curated or listed stallions stand"
    assert not any(h.retired and h.owner in ai for h in horses), "AI breeding stock is cleared"
    ai_pot = [json.loads(j)["groups"]["ai"]["pot"] for (j,) in db.execute("SELECT json FROM world ORDER BY season")]
    assert max(ai_pot) - min(ai_pot) < 3, f"the AI recipe drifted: {ai_pot}"
    claimed = sum(1 for h in horses if h.owner in bots and getattr(h, "claimed", 0))
    print(f"self-check ok: {len(foals)} foals, {len(bots)} bots, {claimed} claimed horses in bot barns, AI pot {ai_pot}")


if __name__ == "__main__":
    main()
