"""A full race program, past performances and all, in the layout of a North American harness program.

    python program.py <seed> <race-id>      e.g. python program.py 2026 3yo-final-2026

Finalists are the same ten showcase.py puts in the race (same crop, same draw). They have no history, so
each is given six earlier starts (preps and an elimination) run through the real sim against other
3-year-olds from the same crop; every line on the page is one of those races. Times are in fifths.
Writes mockups/races/<id>-program.html.
"""
import html, os, random, sys
import sim, story, showcase

TRACKS = [("HwkD", "mile", "Hawkeye Downs"), ("Rdg", "mile", "Ridgeway"), ("Npt", "half", "Newport"), ("Fxb", "half", "Foxboro")]
DRIVERS = ["Corey Lyle", "Tim Dasko", "Aaron Merrill", "Dex Dunning", "Yan Gignac", "Brett Mallory", "Jordan Strand",
           "Dave Palmer", "Tony Hale", "Matt Kearney", "Scott Zeller", "Doug McNeil"]
TRAINERS = ["Ron Burkett", "Tony Alvaro", "Nancy Tackett", "Jim Kingsley", "Linda Tosca", "Brian Browning", "Chris Ryland",
            "Erv Millard", "Rene Allaire", "Jenn Bonner", "Dan Altman", "Steve Carver"]
SIRES = ["Tall Dark Rogue", "Captain Treasure", "Bettor Light", "Some Beach Somewhere Else", "Always A Mickey",
         "Sweet Lewis", "Down By The Bay", "Huntington"]
DAMS = ["Sunny Pockets", "Shadow Lane", "Midnight Belle", "Western Rose", "Lady Tempest", "Copper Kettle",
        "Northern Grace", "Starlight Mist", "River Dancer", "Silk Road", "Painted Sky", "Golden Echo"]
OWNERS = ["Burkett Racing Stable", "Glenwood Stable", "Diamond Ridge Farm", "Hutton Racing Stable", "Brightwater Farms",
          "Northwind Farms", "Crawley Farms", "Bluegrass Acres", "MacNeil Racing", "Winfield Bros"]


def crop(seed, n=3000):
    """The same crop and post draw as showcase.field_for, but keeping the whole crop for the prep races."""
    sim.rng.seed(seed)
    foals = [sim.founder() for _ in range(n)]
    for h in foals:
        h.age = 3
    ranked = sorted(foals, key=lambda h: -h.race_score(3))
    field = ranked[:len(showcase.NAMES)]
    sim.rng.shuffle(field)
    for post, (h, name) in enumerate(zip(field, showcase.NAMES), 1):
        h.post, h.name = post, name
    return field, ranked


def lengths(b):
    """Lengths behind in chart shorthand: ns, hd, nk, then quarters of a length."""
    if b < .05: return ""
    if b < .15: return "ns"
    if b < .3: return "hd"
    if b < .45: return "nk"
    w, q = int(b), round((b - int(b)) * 4) % 4
    return (str(w) if w else "") + ["", "¼", "½", "¾"][q]


def past(field, ranked, rnd):
    """Six earlier starts for every finalist, newest first, each a real sim race in a crop-mates field."""
    pool = ranked[10:60]                                              # the next fifty of the crop: real competition
    names = iter(f"{a} {b}" for a in ["Rocket", "Shadow", "Lucky", "Western", "Royal", "Prairie", "Silver", "Desert", "Ocean",
                                       "Velvet", "Crimson", "Iron", "Golden", "Rapid", "Quiet", "Storm", "Mighty", "Hidden"]
                 for b in ["Art", "Hanover", "Seelster", "Blue Chip", "N", "A", "Deo", "Bluechip", "Lindy", "Kemp", "Rose", "Rocket"])
    for h in pool:
        h.name = next(names, f"H{h.id}")
    finals_day = 28
    lines = {h.id: [] for h in field}
    for h in field:
        h.final_post = h.post
    for k, wk in enumerate(range(1, 7)):                               # six weeks back, the elimination last week
        elim = k == 0
        for h in field:
            mates = [x for x in field if x is not h]
            others = rnd.sample(mates, 2) + rnd.sample(pool, 5)                # usually meets a couple of fellow finalists
            race_field = others + [h]
            rnd.shuffle(race_field)
            tag, kind, _ = rnd.choice(TRACKS[:2] if elim else TRACKS)
            for post, x in enumerate(race_field, 1):
                x.post = post
            order = sim.race(race_field, kind)
            s = story.build(order, kind, random.Random(rnd.random()))
            me = next(r for r in s["horses"] if r["name"] == h.name)
            place = me["place"]
            purse = 50000 if elim else rnd.choice([20000, 25000, 30000, 40000])
            share = [.5, .25, .12, .08, .05][place - 1] * purse if place <= 5 else 0
            wins = [x for x in order[:5]]
            ml = sorted(race_field, key=lambda x: -x.race_score(3)).index(h)   # its rank on paper sets its price
            odds = [0.6, 1.4, 2.8, 4.5, 7.2, 11.0, 18.5, 33.0][ml] * rnd.uniform(.8, 1.25)
            pos = lambda c: (sorted(r["behind"][c] for r in s["horses"]).index(me["behind"][c]) + 1, me["behind"][c])
            lines[h.id].append(dict(
                date=["26Sep26", "19Sep26", "12Sep26", "05Sep26", "29Aug26", "22Aug26"][k], trk=tag, cond=rnd.choices(["ft", "gd", "sy"], [8, 1, 1])[0],
                purse=purse, cls="3YO ELIM" if elim else rnd.choice(["3YO STK", "3YO PREP", "3YO OPEN"]), track=kind,
                q=[story._mt(x) for x in s["quarters"][1:4]], fin=story._mt(s["final"]), post=me["post"],
                calls=[pos(2), pos(3), pos(4), pos(5)], place=place, beaten=me["behind"][6], time=story._mt(me["time"]),
                last_q=story._mt(me["time"] - s["quarters"][3] - me["behind"][4] * 0.18), odds=odds,
                first3=[x.name if x is not h else "<b>" + x.name + "</b>" for x in order[:3]], earn=share,
                trip=me["trip"].split(", ", 1)[1]))
    for h in field:
        h.post = h.final_post                                          # the preps reassigned posts; the final's draw stands
    return lines


def page(rid, field, line, lines):
    pad = ["#d8322f", "#1f4fbf", "#f3f3f3", "#1f8f3f", "#1a1a1a", "#f2d233", "#e88fb0", "#9a9a9a", "#6b3fa0", "#7fc4e8"]
    padname = ["Red", "Blue", "White", "Green", "Black", "Yellow", "Pink", "Gray", "Purple", "Lt Blue"]
    dark = {3, 6, 8, 10}
    rnd = random.Random(sum(h.id for h in field))
    blocks = []
    for h in sorted(field, key=lambda x: x.post):
        L = lines[h.id]
        drv, trn, own = rnd.choice(DRIVERS), rnd.choice(TRAINERS), rnd.choice(OWNERS)
        sire, dam, dsire = rnd.choice(SIRES), rnd.choice(DAMS), rnd.choice(SIRES)
        st, w, p2, s3 = len(L), sum(l["place"] == 1 for l in L), sum(l["place"] == 2 for l in L), sum(l["place"] == 3 for l in L)
        earn = sum(l["earn"] for l in L)
        best = min(L, key=lambda l: l["time"])
        prime = sim.style_of(h)
        arrows = "".join(f"<i class={'on' if k == prime else ''}>▸</i>" for k in ("front", "stalk", "mid", "late"))
        def call(c):
            n, b = c
            return f"{n}<sup>{lengths(b)}</sup>" if n > 1 else f"1<sup>{lengths(b)}</sup>" if b else "1"
        rows = "".join(f"""<tr><td>{l['date']}{l['trk']}</td><td>{l['cond']}</td><td>{l['purse']//1000}K</td><td>{l['cls']}</td>
<td>{l['q'][0]}</td><td>{l['q'][1]}</td><td>{l['q'][2]}</td><td>{l['fin']}</td><td>{l['post']}</td>
{''.join(f'<td>{call(c)}</td>' for c in l['calls'])}<td class=fp>{l['place']}<sup>{lengths(l['beaten']) if l['place'] > 1 else ''}</sup></td>
<td>{l['last_q']}</td><td><b>{l['time']}</b></td><td>{l['odds']:.1f}</td><td class=dr>{drv.split()[-1]}</td>
<td class=t3>{', '.join(l['first3'])}</td></tr>""" for l in L)
        p, odds = line[h.id]
        blocks.append(f"""<div class=horse>
 <div class=side><div class=ml>{odds}</div><div class=post style="background:{pad[h.post-1]};color:{'#111' if h.post in dark else '#fff'}">{h.post}</div>
  <div class=pc>{padname[h.post-1]}</div><div class=pc>PP{h.post}</div><div class=pc>{p:.0%}</div></div>
 <div class=body>
  <div class=own>Owner - {own}</div>
  <div class=nameline><h2>{html.escape(h.name.upper())}</h2><span class=bred>{'b' if h.coat=='bay' else h.coat[:2]} {'c' if h.sex=='m' else 'f'} 3 by {sire}-{dam}-{dsire}</span></div>
  <div class=people>Driver - <b>{drv.upper()}</b> · Trainer - <b>{trn.upper()}</b> · Prime <span class=arr>{arrows}</span> {prime} · Rtg {h.race_score(3):.1f}</div>
  <table class=pp><tr><th>Date/Trk</th><th>Cnd</th><th>Purse</th><th>Class</th><th>1Q</th><th>2Q</th><th>3Q</th><th>Finish</th><th>PP</th>
   <th>1Q</th><th>2Q</th><th>3Q</th><th>Str</th><th>Fin</th><th>Last Q</th><th>Time</th><th>Odds</th><th>Driver</th><th>Top 3 Finishers</th></tr>{rows}</table>
 </div>
 <div class=life><table><tr><th></th><th>Sts</th><th>W</th><th>P</th><th>S</th><th>Earnings</th></tr>
  <tr><td>Life</td><td>{st}</td><td>{w}</td><td>{p2}</td><td>{s3}</td><td>${earn:,.0f}</td></tr>
  <tr><td>2026</td><td>{st}</td><td>{w}</td><td>{p2}</td><td>{s3}</td><td>${earn:,.0f}</td></tr>
  <tr><td>2025</td><td>0</td><td>0</td><td>0</td><td>0</td><td>$0</td></tr></table>
  <div class=best>Best {best['time']} {best['trk']}</div><div class=trip>Last: {L[0]['trip']}</div></div>
</div>""")
    fav = max(field, key=lambda h: line[h.id][0])
    css = """
body{margin:0;background:#cfd2d6;font-family:'Roboto Condensed',Arial Narrow,sans-serif;color:#111}
.sheet{max-width:1100px;margin:10px auto;background:#fff;padding:12px 14px 30px;box-shadow:0 2px 10px rgba(0,0,0,.35)}
.mast{display:grid;grid-template-columns:110px 1fr auto;gap:12px;align-items:start;border-bottom:3px solid #111;padding-bottom:8px}
.rn{font:900 74px/0.85 'Roboto Condensed';text-align:center}
.mast h1{margin:0;font:900 26px 'Roboto Condensed';letter-spacing:.3px}.mast .c{font-size:12px;line-height:1.3}
.mast .r{text-align:right;font-size:12px}.mast .r b{display:block;font:900 26px 'Roboto Condensed'}
.post-t{font:700 13px 'Roboto Condensed';margin-top:4px}
.horse{display:grid;grid-template-columns:62px 1fr 196px;gap:8px;border-bottom:2px solid #111;padding:8px 0}
.side{text-align:center}.ml{font:700 15px 'Roboto Condensed'}.post{font:900 40px/58px 'Roboto Condensed';margin:3px 0;border:1px solid #111}
.pc{font-size:11px}
.own{font-size:11px;border-bottom:1px solid #999}
.nameline{display:flex;align-items:baseline;gap:14px}.nameline h2{margin:2px 0;font:900 26px 'Roboto Condensed'}.bred{font-size:11px}
.people{font-size:11px;margin-bottom:3px}.arr i{font-style:normal;color:#bbb}.arr i.on{color:#111;font-weight:900}
table.pp{border-collapse:collapse;width:100%;font-size:10.5px;font-variant-numeric:tabular-nums}
.pp th{font-weight:700;border-bottom:1px solid #111;text-align:left;padding:1px 3px;white-space:nowrap}
.pp td{padding:1px 3px;white-space:nowrap;border-bottom:1px dotted #ccc}
.pp tr:nth-child(even) td{background:#f3f3f3}.pp sup{font-size:8px}.pp .fp{font-weight:700}.pp .t3{white-space:normal;font-size:10px}
.life table{border-collapse:collapse;font-size:11px;width:100%;font-variant-numeric:tabular-nums}
.life th,.life td{border:1px solid #111;padding:1px 4px;text-align:right}.life td:first-child{text-align:left;font-weight:700}
.best,.trip{font-size:11px;margin-top:4px}
.foot{margin-top:10px;font-size:11px;color:#555;display:flex;justify-content:space-between}
.foot a{background:#111;color:#fff;text-decoration:none;padding:8px 12px;font-weight:700}
"""
    return f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Grand Final Program</title><link href="https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@400;700;900&display=swap" rel=stylesheet>
<style>{css}</style></head><body><div class=sheet>
<div class=mast><div><div class=rn>10</div><div class=post-t>POST - 9:40</div></div>
 <div><h1>HAWKEYE DOWNS - SATURDAY, OCTOBER 3, 2026</h1>
  <div class=c><b>PACE · 1 MILE · GRAND FINAL FOR 3-YEAR-OLDS</b><br>The top ten 3-year-olds of the crop, by rating. Eliminations raced Sep 26.
  Stakes · open · all ages 3 · purse added. W/A Morning Line: favorite {html.escape(fav.name)} {line[fav.id][1]}.</div></div>
 <div class=r>PURSE<b>${showcase.PURSE:,}</b>EXACTA · TRIFECTA · SUPERFECTA</div></div>
{''.join(blocks)}
<div class=foot><span>Every person, stable and track here is invented. Past performances are sim races of this crop; morning line from 4,000 runnings of this field.</span>
<a href="/replay/{rid}">WATCH THE RACE ▶</a></div></div></body></html>"""


if __name__ == "__main__":
    seed, rid = int(sys.argv[1]), sys.argv[2]
    field, ranked = crop(seed)
    line = showcase.morning_line(field)
    lines = past(field, ranked, random.Random(seed * 7 + 1))
    os.makedirs(os.path.join("mockups", "races"), exist_ok=True)
    out = os.path.join("mockups", "races", rid + "-program.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page(rid, field, line, lines))
    print("wrote", out)
