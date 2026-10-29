"""Money on the circuit: barn cash, trainers' cuts, stud fees, a yearling auction, private sales,
claims that change hands, and AI barns that buy, sell, breed and cull on a budget.
Run: python economy.py

Everything an AI barn does here uses public information only (tier/estimate, record,
pedigree), so a horse's price follows its reputation, not its hidden ability. The gap
between the two is where a player who reads the bars makes money.
"""
import statistics as st
import circuit as c
import sim
from sim import founder, rng

START_CASH = 150_000
AI_TRADES = [True]       # computer barns claim and bid at auction; the live game turns this off: only players do
UPKEEP, UPKEEP_RET = 500, 150   # a week's board, feed and training: per racer, per retired horse. What makes a weak horse cost you
BOOK = 100               # covers a stallion may sell in a season
REG_FEE = 150_000        # registering a foal to race: dearer than a house horse, since you know what you bred
REG_FROM = 6             # foals booked from this year on stay unregistered until their owner pays
UNREG_SALE = 5_000       # what the house pays for an unregistered horse
MEAN_NET = 375_000       # measured: mean 7-season net earnings of a 2YO on this circuit (median $259k)
HOUSE_EDGE = 1.25        # house-owned studs price a cover above the foal's expected net: most lose a little,
                         # the top third or so beat the price, the odd one by a mile
AI_BREED_WEEK = 26       # until then player-owned studs are for players; AI barns book from here on
AI_RATE = 1.0            # what an AI barn will pay for a cover, as a share of the house price: the AI's own
                         # the computer barns pay their own house price; a player asking more gets no computer mares
REGISTRY = 0.15          # the breed registry's cut of every cover sold: a sink on stud money
COMMISSION = 0.05        # auction and private sale
RESERVE = 25_000         # an AI barn keeps this much before spending
BARN_MAX = 12            # AI stalls
BARN_FULL = 10           # above this an AI barn sells its weakest, so there are always buyers
# A player's barn grows by buying the next level: the sink that purse money is for.
LEVELS = [  # name, stable stalls (racers), can breed, price, breeding-barn head (retired stock)
    ("starter", 5, False, 0, 0),
    ("working barn", 10, False, 60_000, 0),
    ("breeding shed", 10, True, 90_000, 4),
    ("farm", 20, True, 200_000, 10),
    ("estate", 40, True, 500_000, 20),
]
PLAYER_START = 5, 100_000   # horses, cash
level = {}               # human owner -> index into LEVELS
GROOM = (1, 2, 2, 4, 6)  # grooming slots a week, by barn level: free, and the scarcity is the choice
GROOMED_TO = 65.0        # a groom brings a tired horse back to fit, not to fresh
groomed = {}             # human owner -> (week, slots used that week)
# The house sells a random unraced 3YO for a flat price: a loot roll. Odds and the measured
# 5-season purse earnings each class takes on this circuit (scratchpad rtp.py: 60 of each class in a real barn).
# The floor is raised (a common is a C/D racer, not a write-off) and the freaks are rarer. Re-measure if purses change.
HOUSE_HORSE = 130_000    # priced so the roll pays back ~85% after the trainer's and driver's cuts
HOUSE_INTRO = (50_000, 100_000)   # a barn's first two house horses come cheap: a new player's start, never under the roll's worth after
house_bought = {}        # owner -> house horses bought, for good (the app keeps it with the world)


def house_horse_price(owner):
    """What this barn's next house horse costs: the welcome prices for its first two, then the full price."""
    n = house_bought.get(owner, 0)
    return HOUSE_INTRO[n] if n < len(HOUSE_INTRO) else HOUSE_HORSE
LOOT = [  # rarity, genetic shift per trait, odds, measured career net
    ("common", -0.15, 0.50, 93_000),
    ("uncommon", -0.05, 0.33, 141_000),
    ("rare", 0.0, 0.147, 164_000),
    ("epic", 0.2, 0.02, 328_000),
    ("legendary", 0.4, 0.003, 698_000),
]

cash = {}                # owner -> cash
ledger = {}              # owner -> {"purses", "costs", "stud", "sales", "claims", "barn", "stakes"}
settled = {}             # horse id -> (earnings, costs) already booked
owed = {}                # owner -> upkeep not yet covered: taken from the next purses, never below zero
listings = {}            # horse id -> (horse, asking price): on the board until tomorrow's post time
bookings = []            # (mare, stallion) covered this year; foals arrive at the year tick
human = c.HUMAN          # barns run by people: the AI never buys or claims on their behalf


def book(owner, kind, amount):
    cash[owner] = cash.get(owner, 0) + amount
    ledger.setdefault(owner, {})[kind] = ledger.setdefault(owner, {}).get(kind, 0) + amount
    # nothing drains a barn: every spend checks the cash first, so this can only be a bug
    assert cash[owner] >= -1e-6, f"barn {owner} went negative on {kind}"


def stalls(owner):
    """Stable stalls: for racers. Retired stock lives in the breeding barn, counted apart."""
    return LEVELS[level[owner]][1] if owner in human else BARN_MAX


def barn_head(owner):
    return LEVELS[level[owner]][4] if owner in human else 10 ** 6


def retire(h, owner):
    """Move a racer to the breeding barn for good. Needs a place there."""
    if h.owner != owner or h.retired or barn_retired.get(owner, 0) >= barn_head(owner):
        return False
    c.retire(h)
    barn_size[owner] = barn_size.get(owner, 1) - 1
    barn_retired[owner] = barn_retired.get(owner, 0) + 1
    return True


def groom_left(owner, week):
    w, used = groomed.get(owner, (week, 0))
    return GROOM[level[owner]] - (used if w == week else 0)


def groom(h, owner, week):
    """Spend one of this week's grooming slots to bring a tired horse back to fit for tonight.
    Costs nothing but the slot; resting stays the free default."""
    if h.owner != owner or h.retired or h.freshness >= GROOMED_TO or groom_left(owner, week) <= 0:
        return False
    groomed[owner] = (week, GROOM[level[owner]] - groom_left(owner, week) + 1)
    h.freshness = GROOMED_TO
    return True


def can_breed(owner):
    return LEVELS[level[owner]][2] if owner in human else True


def upgrade(owner):
    """Buy the next barn level. Returns its name, or None if there is none or no cash."""
    nxt = level.get(owner, 0) + 1
    if nxt >= len(LEVELS) or cash.get(owner, 0) < LEVELS[nxt][3]:
        return None
    book(owner, "barn", -LEVELS[nxt][3])
    level[owner] = nxt
    return LEVELS[nxt][0]


def start_player(horses, owner):
    """A new player: a starter barn, a handful of horses, some cash. The rest of the barn's
    founders go to AI barns."""
    n, money = PLAYER_START
    human.add(owner)
    level[owner] = 0
    mine = [h for h in horses if h.owner == owner]
    racers = [h for h in mine if not h.retired]
    rng.shuffle(racers)
    keep = racers[:n]                                     # a new player gets racers; retired stock stays with AI barns
    for h in [h for h in mine if h not in keep]:
        new = rng.choice([o for o in cash if o not in human])
        h.owner = new
        c.assign(h, c.BARN_TRAINER.get(new, c.HOUSE)) or c.assign(h, c.HOUSE)
    settle(horses)                                        # stall counts follow the moves
    cash[owner] = money
    ledger[owner] = {}


STARTER = (52, 57)       # the rating band a new player's racers are drawn from: measured ~$130-180k a first season (median ~$154k)


def start_from_history(horses, owner, racers=3):
    """A new player at Year 0: a few honest racers (B and C class, 2 to 4 years old) bought out of the circuit, a
    broodmare to start a line, and the starting cash. Nothing good is handed over: the top has to be earned."""
    n, money = PLAYER_START
    human.add(owner)
    level[owner] = 0
    for h in [h for h in horses + nursery if h.owner == owner]:   # barn 0 was an AI barn through the history: rehome its string
        new = rng.choice([o for o in cash if o not in human])
        h.owner = new
        if h in horses:
            c.assign(h, c.BARN_TRAINER.get(new, c.HOUSE)) or c.assign(h, c.HOUSE)
    # racers at the B/C line (rated 52-57 against their age group): good enough to win at the bottom of the ladder and pay for a
    # second horse within the first season (~$150-180k), not so good the start is handed over
    pool = [h for h in horses if not h.retired and 2 <= h.age <= 4 and STARTER[0] <= c.on_aged_scale(h.est, c.age_group(h)) <= STARTER[1]]
    rng.shuffle(pool)
    picks = pool[:racers]
    # retired stock keeps the best tier it ever showed (nearly all S), so judge a mare by her best rating instead:
    # one from the lower half of the broodmare band, young enough to breed for years
    mares = sorted((h for h in horses if h.retired and h.sex == "f" and h.age <= 12), key=c.peak_est)
    picks += [rng.choice(mares[:max(1, len(mares) // 2)])] if mares else []
    for h in picks:
        listings.pop(h.id, None); auctions.pop(h.id, None)
        h.owner = owner
        if not h.retired:
            c.assign(h, c.BARN_TRAINER.get(owner, c.HOUSE)) or c.assign(h, c.HOUSE)
    settle(horses)
    cash[owner] = money
    ledger[owner] = {}
    return picks


def buy_house_horse(owner, horses, rig=None):
    """Pay the house for a random unraced 3YO. Returns (horse, rarity) or None (cash, stall).
    rig = (rarity, shift, sex): an admin-set roll instead of the random one."""
    price = house_horse_price(owner)
    if cash.get(owner, 0) < price or barn_size.get(owner, 0) >= stalls(owner):
        return None
    r = rng.random()
    for rarity, shift, odds, _ in LOOT:
        r -= odds
        if r <= 0:
            break
    if rig:
        rarity, shift, sex = rig
    h = founder({t: shift for t in c.RACE_TRAITS})
    while rig and sex and h.sex != sex:
        h = founder({t: shift for t in c.RACE_TRAITS})
    h.age, h.owner, h.rarity = 3, owner, rarity              # rarity is kept, never shown
    c.init_public(h)
    c.assign(h, c.BARN_TRAINER.get(owner, c.HOUSE)) or c.assign(h, c.HOUSE)
    horses.append(h)
    barn_size[owner] = barn_size.get(owner, 0) + 1
    settled[h.id] = (0, 0)
    book(owner, "sales", -price)
    house_bought[owner] = house_bought.get(owner, 0) + 1
    return h, rarity


SCRAP = 20_000           # the least the house pays for any horse you hand it
HOUSE_SHARE = 0.4        # of a proven racer's projected career net: the house buys on the record, never on the card
BOARD_SHARE = 0.6        # what the sale board asks of that same net: above the house, with room for the buyer to profit
MIN_PRICE = 50_000       # nothing goes on the sale board for less


def house_offer(h):
    """What the house pays for a horse tonight: 40% of its projected career net, from its own record (its last two
    seasons' purses less cuts and board, carried over the five seasons ahead with the market's decline from age 4),
    never under $20k. An unraced or losing horse gets the floor: the card alone buys nothing."""
    share = 1 - c.DRIVER - st.mean(t.cut for t in c.ROSTER)
    seasons = getattr(h, "seasons", {}) or {}
    rows = [seasons[y] for y in sorted(seasons)[-2:]]          # its two latest seasons on the books (c.DAY is only set in a tick)
    if h.retired or sum(r[0] for r in rows) < 8:
        return SCRAP
    season = st.mean(r[4] * share - c.YEAR * UPKEEP for r in rows)
    ahead = sum(max(0.3, 1 - 0.12 * max(0, h.age + k - 4)) for k in range(min(5, sim.RETIRE_AGE - h.age)))
    return max(SCRAP, round(HOUSE_SHARE * season * ahead, -3))


def scrap(h, owner, horses):
    """Sell any horse back to the house, at once, for house_offer(): the floor under every horse in the barn.
    The sale board (from $50k) is where a horse worth more to another barn gets its price."""
    if h.owner != owner or h not in horses:
        return None
    paid = house_offer(h)
    if getattr(h, "trainer", None):
        h.trainer.horses -= 1
    horses.remove(h)
    barn_size[owner] = barn_size.get(owner, 1) - 1
    listings.pop(h.id, None); auctions.pop(h.id, None)
    h.owner, h.gone = -1, f"sold to the house for ${paid:,.0f}"
    book(owner, "sales", paid)
    return paid


def value(h):
    """What the market thinks a horse is worth. A racehorse: its public estimate, less for age.
    Breeding stock: its reputation and the breeding years left before the fixed end at 20."""
    if h.retired:
        years = max(0, c.BREEDING_UNTIL - h.age)
        if h.sex == "m":                                       # a stallion: the covers AI mares really buy, at the AI rate, for years
            rank = STUD_RANK.get(h.id)                        # only the standing top 25 get mares, and the leader most of them
            book = 0 if rank is None else BOOK if rank == 0 else 2
            return max(1_000, AI_RATE * house_price(h) * (1 - REGISTRY) * book * years * 0.5)
        return max(1_000, 1_200 * max(0, c.peak_est(h) - 45) * years * 0.1)   # a mare: a foal a year
    v = max(2_000, 1_500 * (c.on_aged_scale(h.est, c.age_group(h)) - 35)) * max(0.3, 1 - 0.12 * max(0, h.age - 4))
    # a proven earner is worth its record: the board asks 60% of the projected career net the house pays 40% of
    return max(v, house_offer(h) * BOARD_SHARE / HOUSE_SHARE) if house_offer(h) > SCRAP else v


def expected_foal_net(s):
    """What a foal by this stallion should earn over a career, from his reputation alone."""
    return MEAN_NET * max(0.3, min(1.5, 0.4 + 0.02 * (c.peak_est(s) - 55)))


def house_price(s):
    """A computer barn's fee for a cover, by his place in the stud book: $50k for the leader down to $10k for the 25th."""
    rank = STUD_RANK.get(s.id, 24)
    return round(50_000 - 40_000 * min(rank, 24) / 24, -3)


def stud_fee(s):
    """What a cover costs: the owner's asking fee if set, else the house price."""
    return getattr(s, "fee", None) or house_price(s)


def set_fee(s, owner, fee):
    if s.owner != owner or s.sex != "m" or not s.retired or fee < 0:
        return False
    s.fee = fee
    return True


def foal_value(s, d):
    """What a yearling by this cross should bring: the market's own formula on the pedigree estimate."""
    return max(2_000, 1_500 * (c.on_aged_scale((c.peak_est(s) + c.peak_est(d)) / 2 - c.FOAL_DISCOUNT, "2") - 35))


def claimant(h, tag):
    """A barn with the cash and a stall takes the horse and pays the owner the tag."""
    if getattr(h, "ageless", False) or not AI_TRADES[0]:      # the owner's giga horse can't be claimed; nor, live, by computer barns
        return h.owner
    buyers = [o for o in cash if cash[o] > tag + RESERVE and o != h.owner and o not in human
              and barn_size.get(o, 0) < BARN_MAX]
    if not buyers:
        return h.owner
    buyer = rng.choice(buyers)
    book(buyer, "claims", -tag)
    book(h.owner, "claims", tag)
    h.gone = f"CLAIMED for ${tag:,}"
    barn_size[buyer] = barn_size.get(buyer, 0) + 1
    barn_size[h.owner] = barn_size.get(h.owner, 1) - 1
    return buyer


c.claimant = claimant


def player_claim(h, buyer, tag):
    """A player's claim goes through after the race: the tag to the old owner (no commission: a claim is a claim),
    the horse to the claimant's barn and trainer. It fails quietly if the claimant can no longer pay or stable it."""
    if cash.get(buyer, 0) < tag or barn_size.get(buyer, 0) >= stalls(buyer) or getattr(h, "ageless", False):
        return
    book(buyer, "claims", -tag)
    book(h.owner, "claims", tag)
    barn_size[buyer] = barn_size.get(buyer, 0) + 1
    barn_size[h.owner] = barn_size.get(h.owner, 1) - 1
    if getattr(h, "trainer", None):
        h.trainer.horses -= 1
    h.owner, h.claimed, h.order, h.ship, h.drawn = buyer, h.claimed + 1, None, None, False
    h.gone = f"CLAIMED for ${tag:,}"
    c.assign(h, c.BARN_TRAINER.get(buyer, c.HOUSE)) or c.assign(h, c.HOUSE)


c.player_claim = player_claim


def tonic_fee(h, fee):
    """The vet's fee for a Post Time Tonic, paid at post time; no cash, no tonic."""
    if cash.get(h.owner, 0) < fee:
        return False
    book(h.owner, "vet", -fee)
    return True


c.tonic_fee = tonic_fee
barn_size = {}       # owner -> racers in the stable
barn_retired = {}    # owner -> retired stock in the breeding barn


def transfer(h, buyer, price, kind):
    book(buyer, kind, -price)
    book(h.owner, kind, price * (1 - COMMISSION))
    barn_size[buyer] = barn_size.get(buyer, 0) + 1
    barn_size[h.owner] = barn_size.get(h.owner, 1) - 1
    h.owner, h.order, h.ship, h.gone = buyer, None, None, f"sold for ${price:,.0f}"


STUD_RANK = {}       # stallion id -> his place among the standing studs (refreshed as the books settle)


def settle(horses):
    """Book purses, less the driver's and trainer's cuts, since last time to each owner."""
    barn_size.clear(); barn_retired.clear()
    STUD_RANK.clear(); STUD_RANK.update({s.id: k for k, s in enumerate(studs(horses))})
    for h in horses:
        (barn_retired if h.retired else barn_size)[h.owner] = (barn_retired if h.retired else barn_size).get(h.owner, 0) + 1
        e0, c0 = settled.get(h.id, (0, 0))
        book(h.owner, "purses", h.earnings - e0)
        book(h.owner, "costs", -(h.costs - c0))
        settled[h.id] = (h.earnings, h.costs)


# ---- the sale board is an auction: each listing runs a real day; bids go up in $10,000 steps; a bid in the last ten
# minutes puts an hour back on the clock. AI barns bid by proxy: each interested barn has a private top price near
# what it thinks the horse is worth and answers a bid at once if it can. Highest bidder at the close takes the horse.
import time as _time
STEP = 10_000
AUCTION_SECS, SNIPE_SECS, EXTEND_SECS = 24 * 3600, 10 * 60, 3600
auctions = {}            # horse id -> {"open": opening bid, "price": high bid, "leader": owner or None, "ends": epoch secs, "proxies": {owner: top}}


def open_auction(h, now=None):
    now = _time.time() if now is None else now
    v = value(h)
    start = max(STEP, round(v * rng.uniform(.6, .8), -4))         # bidding opens under value: the room bids it up
    keen = [o for o in cash if o not in human and o != h.owner and cash.get(o, 0) > start + RESERVE and barn_size.get(o, 0) < BARN_MAX]
    proxies = {o: round(min(cash[o] - RESERVE, v * rng.uniform(.8, 1.25)), -4) for o in rng.sample(keen, min(len(keen), rng.randint(0, 3)))}
    proxies = {o: t for o, t in proxies.items() if t >= start}   # only barns that would pay the opening bid take part
    auctions[h.id] = {"open": start, "price": start, "leader": None, "ends": now + AUCTION_SECS, "proxies": proxies}
    listings[h.id] = (h, start)


def next_bid(hid):
    a = auctions[hid]
    return a["price"] + STEP if a["leader"] is not None else a["price"]


def _answer(hid, h):
    """AI proxies answer the standing bid: the keenest one that can top it does, by one step (or to its limit)."""
    a = auctions[hid]
    if not AI_TRADES[0]:
        return
    rivals = sorted(((top, o) for o, top in a["proxies"].items() if o != a["leader"] and o != h.owner and top >= next_bid(hid)), reverse=True)
    if rivals:
        top, o = rivals[0]
        others = [t for t, x in rivals[1:]] + ([a["proxies"][a["leader"]]] if a["leader"] in a["proxies"] else [])
        a["price"] = min(top, max(next_bid(hid), max(others, default=0) + STEP))
        a["leader"] = o
        listings[hid] = (h, a["price"])


def bid(h, bidder, now=None, amount=None):
    """Bid an amount (at least the next step; the next step if none given). Returns the new price, or None (not listed,
    over, your own horse, below the next step, or can't cover it)."""
    now = _time.time() if now is None else now
    a = auctions.get(h.id)
    if not a or now >= a["ends"] or h.owner == bidder or a["leader"] == bidder:
        return None
    price = next_bid(h.id) if amount is None else round(amount)
    if price < next_bid(h.id) or cash.get(bidder, 0) < price or barn_size.get(bidder, 0) >= stalls(bidder):
        return None
    a["price"], a["leader"] = price, bidder
    if a["ends"] - now <= SNIPE_SECS:
        a["ends"] = now + EXTEND_SECS                       # a late bid: an hour back on the clock
    listings[h.id] = (h, price)
    _answer(h.id, h)
    return a["price"]


def settle_auctions(horses, now=None):
    """Close every auction past its time: the leader (or the keenest AI proxy, if nobody bid) pays and takes the horse."""
    now = _time.time() if now is None else now
    alive = {h.id for h in horses}
    for hid, a in list(auctions.items()):
        if now < a["ends"]:
            continue
        h = listings.get(hid, (None,))[0]
        if h is not None and hid in alive and a["leader"] is None:
            _answer(hid, h)                                 # nobody bid: the proxies settle it among themselves (before it closes)
        auctions.pop(hid); listings.pop(hid, None)
        if h is None or hid not in alive or a["leader"] is None:
            continue                                        # gone, or no sale
        w, price = a["leader"], a["price"]
        if w != h.owner and cash.get(w, 0) >= price and barn_size.get(w, 0) < (stalls(w) if w in human else BARN_MAX):
            transfer(h, w, price, "sales")


def list_for_sale(h, spread=0.2):
    """Put a horse on the board at an asking price around market value. It stays up a day,
    so a player sees it before the AI barns bid tomorrow."""
    if h.id not in auctions:
        open_auction(h)
    h.order = None


def post_listings(horses, ai):
    """Full AI barns list their weakest horse; horses the player listed (order == 'sell')
    go on the same board."""
    for o in ai:
        mine = [h for h in horses if h.owner == o and h.id not in listings and not h.retired]   # racers: spare breeding stock goes to the farm (cull)
        if len(mine) > BARN_FULL:
            list_for_sale(min(mine, key=value))
    for h in horses:
        if getattr(h, "order", None) == "sell":
            list_for_sale(h)


def buy(h, buyer):
    """Take a listed horse at its asking price. Returns the price, or None if it can't be done."""
    if h.id not in listings or cash.get(buyer, 0) < listings[h.id][1] or barn_size.get(buyer, 0) >= stalls(buyer):
        return None
    price = listings.pop(h.id)[1]
    transfer(h, buyer, price, "sales")
    return price


def clear_board(horses, ai):
    """The board is an auction now: close whatever has run its day (see settle_auctions)."""
    settle_auctions(horses)
    return
    """(old) AI barns with cash and a stall buy what's left on the board; the rest comes down unsold."""
    alive = {h.id for h in horses}
    for hid, (h, price) in list(listings.items()):
        buyers = [o for o in ai if o != h.owner and cash.get(o, 0) > price + RESERVE and barn_size.get(o, 0) < BARN_MAX]
        if hid in alive and buyers:
            buy(h, rng.choice(buyers))
        else:
            listings.pop(hid)


def cull(horses, ai):
    """An AI barn sells to the farm ($1k) what it has no use for: an aged racehorse that can't
    earn, or retired stock not worth breeding from. Frees the stall."""
    keep = []
    for h in horses:
        useless = (not h.retired and h.age >= 6 and c.on_aged_scale(h.est, c.age_group(h)) < 35) \
            or (h.retired and c.peak_est(h) < 58)
        if h.owner in ai and useless:
            book(h.owner, "sales", 1_000)
        else:
            keep.append(h)
    return keep


def studs(horses):
    """The stallions standing this year: retired from racing, with a reputation. Best first."""
    return sorted((h for h in horses if h.sex == "m" and h.retired and c.peak_est(h) > 55),
                  key=lambda s: -c.peak_est(s))[:25]


ROLLED = [None]          # a year boundary already rolled by hand, so the first week doesn't roll it twice
nursery = []             # people's foals, born the day the mare is booked; they grow here and join the barn at 2


def on_the_way(owner):
    """Stalls already promised: the barn's foals in the nursery."""
    return sum(f.owner == owner for f in nursery)


def grow(f, d):
    """A youngster's stats this week: from well short of its 2-year-old self at birth up to it on its second birthday."""
    g = min(1.0, (f.age + d % c.YEAR / c.YEAR) / 2)
    f.developed = {t: f.ceiling(t, 2) - 2.0 - 3.0 * (1 - g) for t in sim.RACE_TRAITS}


def nursery_year(horses):
    """The year tick for the nursery: every youngster has a birthday; the 2-year-olds go into the barn to race."""
    grads = []
    for f in nursery[:]:
        f.age += 1
        if f.age >= c.BREEDING_UNTIL:                                     # an unregistered horse lives out its days in the shed
            nursery.remove(f); continue
        if f.age >= 2 and not getattr(f, "unreg", False):
            nursery.remove(f); grow(f, 0); horses.append(f)
            barn_size[f.owner] = barn_size.get(f.owner, 0) + 1
            grads.append(f)
    return grads


def covers_sold(s):
    return sum(1 for _, st_ in bookings if st_ is s)


def book_mare(mare, stallion, owner, horses, fee=None, day=None):
    """Book a retired mare to a standing stallion with room in his book: fee paid now
    (the asking fee unless told otherwise), foal at the year tick."""
    own = stallion.owner == owner and stallion.sex == "m" and stallion.retired   # your own stallion: always standing to your mares, no fee
    fee = 0 if own else stud_fee(stallion) if fee is None else fee
    if mare.owner != owner or mare.sex != "f" or not mare.retired or cash.get(owner, 0) < fee \
            or (stallion not in studs(horses) and not own) or covers_sold(stallion) >= BOOK or too_close(stallion, mare) \
            or any(m is mare for m, _ in bookings) or not can_breed(owner) \
            or barn_size.get(owner, 0) + on_the_way(owner) >= stalls(owner):
        return None
    book(owner, "stud", -fee)
    book(stallion.owner, "stud", fee * (1 - REGISTRY))
    bookings.append((mare, stallion))
    f = c.foal(stallion, mare); f.age = 0; nursery.append(f)                 # the foal is born now and grows up in the nursery
    f.unreg = owner in human and c.year_of(c.DAY[0] if day is None else day) >= REG_FROM   # computer barns register theirs at 2
    grow(f, c.DAY[0] if day is None else day)                               # foals share week 1 as their birthday: a late one is as grown as the rest
    return fee


def register(f, owner, horses):
    """Pay the registration fee and a 2-year-old leaves the shed for the racing barn (its shed slot becomes its stall)."""
    if f not in nursery or f.owner != owner or not getattr(f, "unreg", False) or f.age < 2 or cash.get(owner, 0) < REG_FEE:
        return False
    book(owner, "registry", -REG_FEE)
    nursery.remove(f); f.unreg = False; grow(f, 0); horses.append(f)
    barn_size[owner] = barn_size.get(owner, 0) + 1
    return True


def dump(f, owner):
    """The house takes an unregistered horse off your hands for a flat $5k."""
    if f not in nursery or f.owner != owner or not getattr(f, "unreg", False):
        return False
    nursery.remove(f)
    f.owner, f.gone = -1, f"sold to the house unregistered for ${UNREG_SALE:,.0f}"
    book(owner, "sales", UNREG_SALE)
    return True


SCOUT_FEE = 7_500
scouted = set()          # (sire line, dam line) crosses a pedigree scout has rated; known for every pair of those lines


def nick(s, d):
    """The scout's grade of a cross, or None until it's been scouted. A golden cross is the top ~10% of line pairings."""
    if (s.line, d.line) not in scouted:
        return None
    v = sim.NICK[s.line, d.line]
    return "golden" if v >= 0.75 else "good" if v >= 0.25 else "neutral" if v > -0.25 else "poor"


def scout(s, d, owner):
    """Pay a pedigree scout to rate how this sire's line crosses with this mare's (a nick rating)."""
    if (s.line, d.line) in scouted or cash.get(owner, 0) < SCOUT_FEE:
        return False
    cash[owner] -= SCOUT_FEE
    scouted.add((s.line, d.line))
    return True


def foal_outlook(s, d, horses, n=160):
    """The likely range of this cross at its peak: public tiers at the 10th, 50th and 90th percentile of n imagined
    foals, each ranked against today's racing horses the way the game ranks them. The hidden nick only counts once
    it's been scouted, so the forecast never leaks it."""
    raw = lambda h: 70 + 6 * h.race_score(h.peak_age)
    pop = [raw(h) for h in horses if not h.retired]
    m, sd = st.mean(pop), st.pstdev(pop) or 1
    state, ids, key, nk = sim.rng.getstate(), next(sim._ids), (s.line, d.line), sim.NICK[s.line, d.line]
    if key not in scouted:
        sim.NICK[key] = 0.0
    try:
        r = sorted(55 + 15 * (raw(f) - m) / sd for f in (sim.breed(s, d) for _ in range(n)))
    finally:                                                                  # imagined foals leave no trace on the game
        sim.rng.setstate(state); sim._ids = sim.count(ids); sim.NICK[key] = nk
    return [c.tier_of(r[int(n * q)]) for q in (.1, .5, .9)], r[int(n * .9)] - r[int(n * .1)]


def shared(s, d):
    """The ancestors a stallion and a mare have in common, three generations back: each costs the foal sim.INBRED
    on every trait."""
    common = s.ancestors() & d.ancestors()
    return [h for h in c.lineage([s, d]) if h.id in common]


def too_close(s, d):
    """Matings the registry won't take: a mare to her own sire, or to her own son."""
    if d.sire is s:
        return "her sire"
    if s.dam is d:
        return "her son"
    return None


def why_not_breed(mare, owner, horses):
    """Why this mare can't be booked this season, in a sentence, or None if she can."""
    if any(m is mare for m, _ in bookings):
        return "already booked this season"
    if not can_breed(owner):
        return "your barn needs the breeding shed first (Barn upgrades)"
    if barn_size.get(owner, 0) + on_the_way(owner) >= stalls(owner):
        return "no free stall for the foal: sell, scrap or upgrade the barn first"
    return None


def booked_to(mare):
    return next((s for m, s in bookings if m is mare), None)


def ai_breeding(horses, ai, day=None):
    """Mid-season, AI barns book their retired mares. House studs cover house mares at a nominal
    internal rate (it's the house's own stock). A player's stud gets AI mares only now, after
    the players have had the early season to themselves, and only if the player's fee is no
    more than the house would charge for that reputation."""
    stallions = [s for s in studs(horses) if covers_sold(s) < BOOK]
    for d in [h for h in horses if h.sex == "f" and h.retired and h.owner in ai]:
        if barn_size.get(d.owner, 0) >= BARN_MAX or any(m is d for m, _ in bookings):
            continue
        choices = []
        for s in stallions:
            if covers_sold(s) >= BOOK:
                continue
            fee = AI_RATE * house_price(s) if s.owner in ai else stud_fee(s)
            if s.owner not in ai and (fee > AI_RATE * house_price(s) or not AI_TRADES[0]):
                continue                                       # a player asking over the AI rate gets no AI mares; live, none at all
            if cash.get(d.owner, 0) - fee > RESERVE:
                choices.append((s, fee))
        if not choices:
            continue
        s, fee = choices[0] if rng.random() < 0.7 else rng.choice(choices)   # mostly the best they can get
        book_mare(d, s, d.owner, horses, fee, day)


def auction(foals, ai):
    """Yearling sale: AI breeders list the foals they have no stall for or can't carry.
    Bidders see pedigree and tier only; the board clears tomorrow."""
    for f in foals:
        if f.owner in ai and (barn_size.get(f.owner, 0) > BARN_FULL or cash.get(f.owner, 0) < RESERVE):
            list_for_sale(f, spread=0.35)


def rehire(horses, ai):
    """AI barns read the trainers' public records: a barn on the house, or whose trainer earns
    well under the best available, moves its horses to a better one with room."""
    best = sorted((t for t in c.ROSTER if t.starts >= 100), key=lambda t: -t.earnings / t.starts)
    for o in ai:
        cur = c.BARN_TRAINER.get(o, c.HOUSE)
        per = cur.earnings / max(1, cur.starts)
        if cur is c.HOUSE or (best and per < 0.8 * best[0].earnings / best[0].starts and rng.random() < 0.3):
            mine = [h for h in horses if h.owner == o]
            fresh = [t for t in c.ROSTER if t.starts < 100]                      # a newcomer has no record yet: a barn on the
            rng.shuffle(fresh)                                                    # house takes a chance on one, so new trainers
            for t in best + (fresh if cur is c.HOUSE else []):                   # get horses and build the records others read
                if t.stalls - t.horses >= len(mine):
                    c.BARN_TRAINER[o] = t
                    for h in mine:
                        c.assign(h, t)
                    break


def new_year(horses, ai):
    racing = {h.id for h in horses if not h.retired}
    horses = c.age_up(horses)
    grads = nursery_year(horses)
    c.ai_retire(horses, ai)
    rehire(horses, ai)
    settle(horses)
    horses = cull(horses, ai)
    settle(horses)
    bookings.clear()                                                          # the books reopen; this season's foals are already in the nursery
    settle(horses)
    auction(grads, ai)
    for hid, (h, _) in list(listings.items()):                # a racer listed last week that retired at the year turn:
        if hid in racing and h.retired:                       # its asking price was a racer's; take it down
            listings.pop(hid); auctions.pop(hid, None)
    return horses


def day(d, horses, ai, log):
    """A game week: yesterday's board clears (AI buys), the year ticks if due, the cards run,
    the books settle, and tonight's listings go up for the player to see first."""
    clear_board(horses, ai)
    if d % c.YEAR == 0 and d and ROLLED[0] != d:              # (a new game rolls Year 0 in before its first post time)
        horses = new_year(horses, ai)
    if d % c.YEAR == AI_BREED_WEEK:
        ai_breeding(horses, ai, d)
    for f in nursery:
        grow(f, d)
    c.race_day(d, horses, log)
    settle(horses)
    upkeep(horses)
    post_listings(horses, ai)
    return horses


def bills(owner, horses):
    """A barn's weekly bills: (the trainer's training bill for its racers, the farm's board for its retired stock)."""
    mine = [h for h in horses if h.owner == owner]
    return sum(not h.retired for h in mine) * UPKEEP, sum(h.retired for h in mine) * UPKEEP_RET


def upkeep(horses):
    """Each race night every barn pays its trainer's day rate for its racers (the training bill) and the farm's board for its
    retired stock. Paid from cash (tonight's purses are already in), training first; what can't be covered is owed and comes
    out of the next purses. Cash never goes below zero."""
    due = {}
    for h in horses:
        t, b = due.get(h.owner, (0, 0))
        due[h.owner] = (t, b + UPKEEP_RET) if h.retired else (t + UPKEEP, b)
    for o, (t, b) in due.items():
        t += owed.pop(o, 0)                                    # anything overdue is paid first, with the training bill
        left = max(cash.get(o, 0), 0)
        for kind, amt in (("training", t), ("board", b)):
            pay = min(left, amt)
            if pay:
                book(o, kind, -pay)
                left -= pay
            if amt - pay > 0:
                owed[o] = owed.get(o, 0) + amt - pay


def world(barns=60, each=10):
    horses = [founder() for _ in range(barns * each)]
    for i, h in enumerate(horses):
        h.owner = i % barns
        c.init_public(h)
    cash.clear(); ledger.clear(); settled.clear(); listings.clear(); auctions.clear(); bookings.clear(); nursery.clear(); level.clear()
    c.BARN_TRAINER.clear()
    c.new_roster()
    for o in range(barns):
        cash[o] = START_CASH
        c.BARN_TRAINER[o] = rng.choice(c.ROSTER)              # every barn starts with some trainer
    for h in horses:
        c.trainer_of(h)
    c.ai_retire(horses, set(range(barns)))                   # a circuit starts with breeding stock already standing
    c.seed_studs(horses, set(range(barns)))
    settle(horses)
    for h in horses:
        settled[h.id] = (0, 0)
    return horses


def add_barns(horses, ai, n, racers=10, mares=2):
    """Open n new AI barns on a running circuit, stocked from its own bloodlines: racers of every age (bred from the
    standing stallions and the circuit's mares, already trained up to their age) and a couple of broodmares, with
    starting cash and a trainer. Returns the new owner ids."""
    sires = studs(horses) or [h for h in horses if h.sex == "m"]
    dams = [h for h in horses if h.sex == "f" and h.retired] or [h for h in horses if h.sex == "f"]
    first = max([o for o in cash if isinstance(o, int)] + [max(ai, default=0)]) + 1
    new = list(range(first, first + n))
    ages = [2, 2, 2, 3, 3, 3, 4, 5, 6, 7][:racers]                    # weighted young: the 2- and 3-year-old cards run shortest
    for o in new:
        cash[o] = START_CASH; ledger[o] = {}
        c.BARN_TRAINER[o] = rng.choice(c.ROSTER)
        for k in range(racers + mares):
            h = c.foal(rng.choice(sires), rng.choice(dams))
            h.owner = h.breeder = o
            h.age = ages[k] if k < racers else rng.randint(6, 12)
            h.est = c.true_rating(h) + rng.gauss(0, 6)                # a horse with a past: rated on what it is, not its pedigree
            h.est_sd, h.peak_est = 6.0, h.est
            h.developed = {t: h.ceiling(t) for t in c.RACE_TRAITS}
            h.tier = c.public_tier(h)
            h.retired = k >= racers
            c.trainer_of(h)
            horses.append(h)
            settled[h.id] = (0, 0)
        ai.add(o)
    back_record(horses, [h for h in horses if h.owner in new], c.year_of(c.DAY[0]))
    settle(horses)
    return new


def back_record(horses, arrivals, year):
    """Give horses that join the circuit with no past a made-up one: each takes the seasons it missed (age 2 up to
    this year) from a native horse of its sex and about its quality, so its career line reads like everyone else's."""
    ids = {h.id for h in arrivals}
    pool = [t for t in horses if t.id not in ids and getattr(t, "seasons", None)]
    for h in arrivals:
        full = lambda t: all(year - (t.age - a) in t.seasons for a in range(2, h.age))   # some old ledgers have gaps
        mates = [t for t in pool if t.sex == h.sex and t.age >= h.age and full(t)] or [t for t in pool if full(t)] or pool
        t = min(mates, key=lambda t: abs(c.peak_est(t) - c.peak_est(h)) + rng.random() * 4)
        h.seasons = dict(getattr(h, "seasons", None) or {})
        for a in range(2, h.age):
            row = t.seasons.get(year - (t.age - a))
            y = year - (h.age - a)
            if row and y not in h.seasons:
                h.seasons[y] = list(row)
                h.starts += row[0]; h.wins += row[1]; h.places += row[2]; h.shows += row[3]; h.earnings += row[4]
                if row[5] < 999:
                    h.best = min(getattr(h, "best", 999), row[5])


if __name__ == "__main__":
    horses = world()
    o, h = 0, horses[0]
    human.add(o); level[o] = 0; h.freshness = 40
    assert groom(h, o, 5) and h.freshness == GROOMED_TO, "a groom makes a tired horse fit"
    h.freshness = 40
    assert not groom(h, o, 5) and groom_left(o, 5) == 0, "starter barn: one slot a week"
    assert groom(h, o, 6), "slots come back next week"
    h.freshness = 90
    assert not groom(h, o, 8) and groom_left(o, 8) == 1, "a fresh horse doesn't use a slot"
    human.discard(o); level.clear(); groomed.clear()
    assert len(studs(horses)) >= 10, "a new circuit has stallions standing"
    ai = set(range(60))
    log, totals = [], [sum(cash.values())]
    for d in range(3 * c.YEAR):
        horses = day(d, horses, ai, log)
        if d % c.YEAR == c.YEAR - 1:
            totals.append(sum(cash.values()))
    growth = [b - a for a, b in zip(totals, totals[1:])]
    print(f"circuit cash by year: {[f'${t / 1e6:.1f}M' for t in totals]}  growth/yr {[f'${g / 1e6:.1f}M' for g in growth]}")
    assert growth[2] < 1.5 * growth[0], "no money printer: cash must not grow faster each year"

    racing = [ledger[o].get("purses", 0) + ledger[o].get("costs", 0) for o in ai]
    purses = [ledger[o].get("purses", 0) for o in ai]
    print(f"racing net per barn over 3y: median ${st.median(racing):,.0f} on median purses ${st.median(purses):,.0f}; "
          f"every barn in the black on racing: {all(r > 0 for r in racing)}")
    assert all(r > 0 for r in racing) and min(cash.values()) >= 0, "racing is free: nobody can lose money by racing"

    stud = sorted((ledger[o].get("stud", 0) for o in ai), reverse=True)
    sales = [ledger[o].get("sales", 0) for o in ai]
    claims = [ledger[o].get("claims", 0) for o in ai]
    print(f"stud income: top barn ${stud[0]:,.0f}, barns paying fees {sum(s < 0 for s in stud)}; "
          f"sale/claim money moved ${sum(abs(x) for x in sales) / 2:,.0f} / ${sum(abs(x) for x in claims) / 2:,.0f}")
    assert stud[0] > 50_000 and sum(abs(x) for x in claims) > 0, "stud fees and claims must move money"

    net = {o: cash[o] - START_CASH for o in ai}
    trade = {o: ledger[o].get("stud", 0) + ledger[o].get("sales", 0) + ledger[o].get("claims", 0) for o in ai}
    rich = sorted(ai, key=lambda o: -net[o])[:15]
    poor = sorted(ai, key=lambda o: net[o])[:15]
    print(f"top-15 barns: net ${st.mean(net[o] for o in rich):,.0f}, of which breeding/trading ${st.mean(trade[o] for o in rich):,.0f}; "
          f"bottom-15: net ${st.mean(net[o] for o in poor):,.0f}, trading ${st.mean(trade[o] for o in poor):,.0f}; "
          f"lowest cash ${min(cash.values()):,.0f}")
    assert st.mean(trade[o] for o in rich) > st.mean(trade[o] for o in poor), "the rich barns are the ones breeding and trading well"

    # Prices follow reputation, not truth: bargains exist for a buyer who can see more.
    aged = [h for h in horses if c.age_group(h) == "aged" and not h.retired]   # racers: breeding stock is priced another way
    tr = {h.id: c.true_rating(h) for h in aged}
    tm, ts = st.mean(tr.values()), st.pstdev(tr.values()) or 1                 # truth on the market's own footing: mean 55, sd 15
    truth = {h.id: max(2_000, 1_500 * (55 + 15 * (tr[h.id] - tm) / ts - 35)) * max(0.3, 1 - 0.12 * max(0, h.age - 4)) for h in aged}
    ratio = sorted(value(h) / truth[h.id] for h in aged)
    print(f"market value / true value, aged horses: 10th pct {ratio[len(ratio) // 10]:.2f}  median {ratio[len(ratio) // 2]:.2f}  "
          f"90th pct {ratio[-len(ratio) // 10]:.2f}")
    assert ratio[len(ratio) // 10] < 0.85 < 1.2 < ratio[-len(ratio) // 10], "mispriced horses must exist both ways"

    # A player's barn: 5 stalls and no breeding until bought; each level needs the cash.
    horses = world()
    start_player(horses, 0)
    mine = [h for h in horses if h.owner == 0]
    mare = next(h for h in horses if h.owner != 0 and h.sex == "f" and 4 <= h.age <= 12 and not h.retired)   # a racing mare: she takes a stall
    mare.owner, mine[0].owner = 0, mare.owner
    for s in [h for h in horses if h.sex == "m" and h.owner != 0 and c.peak_est(h) > 60][:5]:
        c.retire(s)                                            # a few stallions standing
    settle(horses)
    assert len(mine) == 5 and cash[0] == 100_000 and stalls(0) == 5
    list_for_sale(next(h for h in horses if h.owner == 1))
    assert buy(next(iter(listings.values()))[0], 0) is None, "a full starter barn can't buy"
    assert all(s.retired for s in studs(horses)) and studs(horses), "only retired horses stand at stud"
    cash[0] += 150_000 + house_price(studs(horses)[-1])        # the levels, and one cover at the house price
    assert upgrade(0) == "working barn" and upgrade(0) == "breeding shed" and stalls(0) == 10
    assert book_mare(mare, studs(horses)[-1], 0, horses) is None, "a racing mare can't be bred"
    assert retire(mare, 0), "the shed gives the breeding barn its first head"
    assert book_mare(mare, studs(horses)[-1], 0, horses), "a retired mare in a barn with a shed can"
    print("player barn: levels gated by cash; stud book and broodmares are retired horses only")
    # Breeding stock is priced on reputation and years left, not on a faded racing estimate.
    champ = studs(horses)[0]
    champ.age = 8
    young = value(champ)
    champ.age = 18
    old = value(champ)
    champ.age = 8
    dud = min((h for h in horses if not h.retired and c.age_group(h) == "aged"), key=lambda h: h.est)
    print(f"breeding value: {champ.name} at 8 ${young:,.0f}, at 18 ${old:,.0f}; an aged D racehorse ${value(dud):,.0f}")
    assert young > 5 * old and young > 10 * value(dud), "a champion stallion with years left is the dearest horse there is"

    # A player's stud: own fee, a 60-cover book, players first, AI mares from week 26 if the
    # fee is in line, none if it's over the odds.
    horses = world()
    start_player(horses, 0)
    ai = set(range(1, 60))
    stud = max((h for h in horses if h.sex == "m" and h.owner != 0 and not h.retired), key=c.peak_est)   # a top stud: the seeded sires are real competition
    stud.owner = 0
    c.retire(stud)
    for s in [h for h in horses if h.sex == "m" and h.owner != 0 and c.peak_est(h) > 60][:5]:
        c.retire(s)
    for m in [h for h in horses if h.sex == "f" and h.owner != 0][:80]:
        c.retire(m)
    settle(horses)
    ai_rate = AI_RATE * house_price(stud)
    assert set_fee(stud, 0, ai_rate) and stud_fee(stud) == ai_rate
    for o in ai:
        cash[o] += 2_000_000                                   # established barns, a few years in
    for d in range(AI_BREED_WEEK):
        horses = day(d, horses, ai, [])
    assert covers_sold(stud) == 0, "before week 26 a player's stud is for players only"
    horses = day(AI_BREED_WEEK, horses, ai, [])
    sold_fair = covers_sold(stud)
    print(f"player stud at the AI rate ${ai_rate:,.0f} (house price ${house_price(stud):,.0f}): {sold_fair} AI covers at week 26, "
          f"fee income ${ledger[0].get('stud', 0):,.0f} after the {REGISTRY:.0%} registry fee; book cap {BOOK}; "
          f"most a stud can draw from AI barns in a season ${BOOK * ai_rate * (1 - REGISTRY):,.0f}")
    assert 0 < sold_fair <= BOOK and abs(ledger[0].get("stud", 0) - sold_fair * ai_rate * (1 - REGISTRY)) < 1
    bookings.clear()
    set_fee(stud, 0, ai_rate * 1.5)
    ai_breeding(horses, ai)
    assert covers_sold(stud) == 0, "over the AI rate, no AI mare comes"

    # The registry: a mare can't go to her own sire or her own son, and shared ancestors are counted for the screen.
    sire_ = next(h for h in horses if h.sex == "m")
    dam_ = next(f for f in (c.foal(sire_, next(h for h in horses if h.sex == "f")) for _ in range(20)) if f.sex == "f")
    assert too_close(sire_, dam_) == "her sire" and shared(sire_, dam_) == []
    dam_.owner, dam_.retired, sire_.retired = 0, True, True
    horses.append(dam_)
    assert book_mare(dam_, dam_.sire, 0, horses) is None, "the registry refuses a mare to her own sire"

    # The house horse: a loot roll with a negative expectation and a real tail.
    assert abs(sum(o for _, _, o, _ in LOOT) - 1) < 1e-9
    share = 1 - c.DRIVER - st.mean(t.cut for t in c.ROSTER)          # purses less the driver's and trainer's cuts
    rtp = share * sum(o * net for _, _, o, net in LOOT) / HOUSE_HORSE
    print(f"house horse ${HOUSE_HORSE:,}: return to player {rtp:.0%} over a full career; "
          f"{sum(o for _, _, o, net in LOOT if net > HOUSE_HORSE):.1%} of rolls beat the price")
    assert 0.8 <= rtp <= 0.95, "the house keeps an edge, but not a cruel one"
    cash[0], level[0], house_bought[0] = HOUSE_HORSE * 3, 1, 99   # a working barn with room for two, past the welcome prices
    before = len([h for h in horses if h.owner == 0])
    got = [buy_house_horse(0, horses) for _ in range(4)]
    print("rolled:", [r for g in got if g for _, r in [g]], "stalls:", before, "->", len([h for h in horses if h.owner == 0]))
    assert all(got[:3]) and got[3] is None, "three rolls on the money, the fourth refused for cash"
    assert cash[0] == 0 and all(g[0].age == 3 and g[0].starts == 0 for g in got[:3])
    assert house_offer(got[0][0]) == SCRAP, "unraced, the house pays the floor"
    assert scrap(got[0][0], 0, horses) == SCRAP and cash[0] == SCRAP
    assert scrap(got[0][0], 0, horses) is None, "can't scrap twice"
    star = got[1][0]
    star.seasons = {9: [20, 8, 4, 2, 400_000, 110.0], 8: [18, 6, 3, 2, 300_000, 111.0], 7: [20, 0, 0, 0, 0, 999.0]}
    assert house_offer(star) > SCRAP and house_offer(star) == round(HOUSE_SHARE * st.mean(
        p * (1 - c.DRIVER - st.mean(t.cut for t in c.ROSTER)) - c.YEAR * UPKEEP for p in (400_000, 300_000)) * (1 + 1 + .88 + .76 + .64), -3)
    star.seasons[9][4] = star.seasons[8][4] = 20_000
    assert house_offer(star) == SCRAP, "a record that didn't cover its board gets the floor"
    star.seasons[9][4] = star.seasons[8][4] = 400_000
    assert abs(value(star) - house_offer(star) * 1.5) < 1, "the board asks half again what the house pays for a proven earner"
    got[1][0].starts = 1
    assert scrap(mare, 1, horses) is None, "only the owner can sell a horse to the house"
    print(f"scrap: a house horse hands back ${SCRAP:,.0f} unraced; a pack-ripper nets {rtp:.0%}-{SCRAP / HOUSE_HORSE:.0%} of price per roll")
    print("all checks passed")
