"""A fresh Year-0 world under today's rules, run ten seasons. Read-only: nothing is saved.
Two player barns stand in for the user and their dad: they enter every fit horse where the trainer would,
sell a horse to the house after a losing season, and buy a house horse whenever they can afford one with a stall free."""
import os, sys, json, statistics as st, collections, time
sys.path.insert(0, r"C:\Users\spooh\HarnessSim"); os.chdir(r"C:\Users\spooh\HarnessSim")
SEASONS = int(sys.argv[1]) if len(sys.argv) > 1 else 10
sys.argv = ["x"]
import app
G, e, c, sk = app.G, app.e, app.c, app.sk
app.save = lambda *a, **k: None                              # never touch the save
app.snapshot = lambda *a, **k: None
HISTORY = 12                                                   # enough past for pedigrees and a stud book; the full 50 takes too long here

t0 = time.time()
app.new_game(years=HISTORY)
app.P(0)["user"] = "me"
o2, err = app.signup("dad", "secret1")                            # the second player barn, the way the game makes one
assert o2 is not None, err
c.HUMAN.add(o2)
PLAYERS = (0, o2)
e.AI_TRADES[0] = False
# three stand-in handicappers for the pick'em, barns that never race: chalk takes the morning-line favorite every time,
# form the highest public rating, lucky a horse at random
PICKERS = {}
for nm in ("chalk", "form", "lucky"):
    o, err = app.signup(nm, "secret1"); assert o is not None, err
    c.HUMAN.add(o); PICKERS[nm] = o
    for h in [x for x in G["horses"] if x.owner == o]:                   # no stable: prizes are their only income
        e.scrap(h, o, G["horses"])
    e.cash[o] = 0

def pickers_night():
    import random as _r
    for s in app.stakes_tonight():
        noms = app.nominees(s)
        if len(noms) < 2:
            continue
        line = c.tote_odds(noms)
        G.setdefault("picks", {}).setdefault(PICKERS["chalk"], {})[s.id] = min(noms, key=lambda h: line[h.id][0] / line[h.id][1]).id
        G["picks"].setdefault(PICKERS["form"], {})[s.id] = max(noms, key=lambda h: h.est).id
        G["picks"].setdefault(PICKERS["lucky"], {})[s.id] = _r.choice(noms).id
print(f"world built in {time.time() - t0:.0f}s: {len(G['horses'])} horses, players {sorted(c.HUMAN)}", flush=True)

def player_week(o):
    """A player's night, by the trainer's book: enter what's fit, cut what loses, buy when flush."""
    mine = [h for h in G["horses"] if h.owner == o and not h.retired]
    for h in mine:
        if getattr(h, "order", None) in (None, "rest") and c.trainer_of(h).plan(h) == "race":
            h.order = "race"
    yr = c.year_of(G["day"])
    if G["day"] % c.YEAR == 0:                                   # the year tick: judge last season
        for h in mine:
            s = (getattr(h, "seasons", {}) or {}).get(yr - 1)
            if s and s[0] >= 8 and s[4] * 0.886 < 26_000 and h.age >= 4:   # a full season that didn't cover its bills
                LOG["scrap"] += 1; LOG["scrap_purses"] += s[4]; e.scrap(h, o, G["horses"])
    free = e.stalls(o) - sum(not h.retired for h in G["horses"] if h.owner == o)
    if free > 0 and e.cash.get(o, 0) >= e.house_horse_price(o) + 60_000:
        LOG["buy"] += bool(e.buy_house_horse(o, G["horses"]))
    lv = e.level.get(o, 0)
    if lv + 1 < len(e.LEVELS) and e.cash.get(o, 0) >= e.LEVELS[lv + 1][3] + 100_000:
        e.cash[o] -= e.LEVELS[lv + 1][3]; e.level[o] = lv + 1
        e.book(o, "barn", 0)

rows, claims0 = [], 0
LOG = collections.Counter()
for s in range(SEASONS):
    t1 = time.time()
    for w in range(c.YEAR):
        for o in PLAYERS:
            player_week(o)
        pickers_night()
        app.tick()
    yr = c.year_of(G["day"]) - 1
    ai = [o for o in e.cash if o not in c.HUMAN]
    cs = sorted(e.cash[o] for o in ai)
    racers = [h for h in G["horses"] if not h.retired]
    seas = lambda h: (getattr(h, "seasons", {}) or {}).get(yr, [0] * 5)
    byclm = collections.defaultdict(list)
    for h in racers:
        rs = [r for r in getattr(h, "results", []) if "Claiming" in r["race"] and c.year_of(r["day"]) == yr]
        if len(rs) >= 3:
            import re
            m = re.search(r"\$(\d+)(k|M)", rs[-1]["race"]); tag = int(m.group(1)) * (1000 if m.group(2) == "k" else 1_000_000)
            byclm[tag].append(seas(h)[4] * 0.886 - 26_000)
    wo = collections.Counter(r["race"] for h in racers for r in getattr(h, "results", []) if "Winners Over" in r["race"] and c.year_of(r["day"]) == yr)
    pl = {o: {k: round(v) for k, v in e.ledger.get(o, {}).items()} for o in PLAYERS}
    row = {"season": yr, "players_ledger": pl, "log": dict(LOG), "p_starts": {o: sum(seas(h)[0] for h in G["horses"] if h.owner == o) for o in PLAYERS}, "ai_med": round(st.median(cs)), "ai_p10": round(cs[len(cs) // 10]), "ai_p90": round(cs[int(.9 * len(cs))]),
           "ai_broke": sum(x < 50_000 for x in cs), "p0": round(e.cash.get(0, 0)), "p1": round(e.cash.get(PLAYERS[1], 0)),
           "p0_lvl": e.level.get(0, 0), "p1_lvl": e.level.get(PLAYERS[1], 0), "p0_horses": sum(h.owner == 0 and not h.retired for h in G["horses"]),
           "claims": round(-sum(e.ledger.get(o, {}).get("claims", 0) for o in e.cash)), "total": round(sum(e.cash.values())),
           "losing_racers_pct": round(100 * st.mean(seas(h)[4] * 0.886 < 26_000 for h in racers if seas(h)[0] >= 8) if any(seas(h)[0] >= 8 for h in racers) else 0),
           "clm_net_median": {str(k): round(st.median(v)) for k, v in sorted(byclm.items())},
           "wo_starts": sum(wo.values()), "house_price_p0": e.house_horse_price(0),
           "pickers": {nm: G.get("pickers", {}).get(yr, {}).get(o, [0, 0]) + [round(e.cash.get(o, 0))] for nm, o in PICKERS.items()}}
    rows.append(row)
    print(json.dumps(row), f"({time.time() - t1:.0f}s)", flush=True)
json.dump(rows, open(os.path.join("exports", "econ_fresh.json"), "w"), indent=1)
print("done", round(time.time() - t0), "s")
