"""What a house horse returns under today's rules, bills included. A fresh world; two estate barns buy 40 house
horses each at full price and race them five seasons by the trainers' book. Barn A keeps every horse; barn B sells
a horse to the house after a season that didn't cover its bills. Read-only: nothing is saved."""
import os, sys, time
os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.getcwd())
ARGS = sys.argv[1:]; sys.argv = ["x"]
import app
G, e, c = app.G, app.e, app.c
app.save = app.snapshot = lambda *a, **k: None
N, SEASONS = 40, 5
YEARS = int(ARGS[0]) if ARGS else 8   # seasons of history before Year 0: 50 is what the live world had

t0 = time.time()
app.new_game(years=YEARS)
app.P(0)["user"] = "a"
b, err = app.signup("barnb", "secret1"); assert b is not None, err
BARNS = (0, b)
for o in BARNS:                                               # an estate with empty stalls and the cash for 40 rolls
    for h in [h for h in G["horses"] if h.owner == o]:
        if h.retired:
            h.owner = -1; G["horses"].remove(h)
        else:
            e.scrap(h, o, G["horses"])
    e.level[o] = 4; e.cash[o] = N * e.HOUSE_HORSE; e.ledger[o] = {}
    e.house_bought[o] = 99                                    # full price, no welcome discount
    e.settle(G["horses"])
    for _ in range(N):
        assert e.buy_house_horse(o, G["horses"]), "a roll failed"
bought = {o: {h.id for h in G["horses"] if h.owner == o} for o in BARNS}
print(f"built in {time.time() - t0:.0f}s; {N} house horses each at ${e.HOUSE_HORSE:,}", flush=True)

def week(o, cull):
    mine = [h for h in G["horses"] if h.owner == o]
    for h in mine:
        if h.retired:                                        # retired stock would sit on the farm: not what we're measuring
            h.owner = -1; G["horses"].remove(h); e.barn_retired[o] = e.barn_retired.get(o, 1) - 1
        elif getattr(h, "order", None) in (None, "rest") and c.trainer_of(h).plan(h) == "race":
            h.order = "race"
    if cull and G["day"] % c.YEAR == 0:
        yr = c.year_of(G["day"]) - 1
        for h in [h for h in G["horses"] if h.owner == o and not h.retired]:
            s = (getattr(h, "seasons", {}) or {}).get(yr)
            if s and s[0] >= 8 and s[4] * 0.886 < 26_000:
                e.scrap(h, o, G["horses"])

for s in range(SEASONS):
    for w in range(c.YEAR):
        week(0, False); week(b, True)
        app.tick()
    print(f"season {s} done", flush=True)
for o, name in ((0, "keep all"), (b, "cull losers")):
    L = e.ledger[o]
    back = L.get("purses", 0) + L.get("costs", 0) + L.get("training", 0) + L.get("board", 0) + L.get("sales", 0) + N * e.HOUSE_HORSE
    print(f"{name:11} purses {L.get('purses', 0):>10,.0f}  cuts {L.get('costs', 0):>9,.0f}  training {L.get('training', 0):>9,.0f}  "
          f"board {L.get('board', 0):>7,.0f}  house sales {L.get('sales', 0) + N * e.HOUSE_HORSE:>8,.0f}  "
          f"=> back per horse ${back / N:,.0f}  return {back / (N * e.HOUSE_HORSE):.0%}")
left = {o: sum(1 for h in G["horses"] if h.owner == o) for o in BARNS}
print("still in the barn after 5 seasons:", left, f"({time.time() - t0:.0f}s)")
