"""What a diligent hand is worth: a fresh world where every even-numbered youngster gets the owner's day sheet each
week (training miles when fresh, a jog when not; yearlings worked every week) and every odd one is left to the stable.
After the seasons, the two halves are compared fresh at the gate and on what they earned. Read-only: nothing is saved."""
import os, sys, statistics as st, time
os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.getcwd())
ARGS = sys.argv[1:]; sys.argv = ["x"]
import app
G, e, c = app.G, app.e, app.c
app.save = app.snapshot = lambda *a, **k: None
SEASONS = int(ARGS[0]) if ARGS else 2

t0 = time.time()
app.new_game(years=8)
print(f"world built in {time.time() - t0:.0f}s", flush=True)
hand = lambda h: h.id % 2 == 0
crop = {h.id for h in G["horses"] if not h.retired and h.age <= 2} | {f.id for f in e.nursery if f.age == 1}   # followed through

def week():
    d = G["day"]
    for f in e.nursery:
        if f.age == 1 and hand(f):
            f.owner_was = f.owner
            e.handle(f, f.owner, d, "train", "early_speed")
    for h in G["horses"]:
        if not h.retired and h.age <= c.YOUNG and hand(h) and not getattr(h, "order", None) and h.freshness < 50:
            h.job = (d, "train" if h.freshness >= 35 else "jog", "early_speed")

for s in range(SEASONS):
    for w in range(c.YEAR):
        week(); app.tick()
    print(f"season {s} done ({time.time() - t0:.0f}s)", flush=True)

yr = c.year_of(G["day"]) - 1
rows = {True: [], False: []}
for h in G["horses"]:
    if h.id in crop and not h.retired:
        fr = h.freshness; h.freshness = 70.0
        rows[hand(h)].append((c.rating_tonight(h), (getattr(h, "seasons", {}) or {}).get(yr, [0] * 5)[4], h.shape["early_speed"]))
        h.freshness = fr
for k, name in ((True, "worked"), (False, "stable")):
    r = rows[k]
    print(f"{name:7} n {len(r):4}  rating at the gate {st.mean(x[0] for x in r):5.1f}  last season purses ${st.mean(x[1] for x in r):>9,.0f}  "
          f"early-speed shape {st.mean(x[2] for x in r):+.2f}")
print(f"edge: {st.mean(x[0] for x in rows[True]) - st.mean(x[0] for x in rows[False]):+.1f} rating (1.5 ~ a length)")
