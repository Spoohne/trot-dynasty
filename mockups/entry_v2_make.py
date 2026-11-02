"""Mockup: a concise entry screen (Patrick, 2026-11-02). Built from a horse's real race book in a save copy; writes
mockups/entry_v2.html (static, outside the game). Races are grouped by race, not by track: one row per race showing
the best-paying track, the field's level against this horse, and the other tracks folded underneath. Stakes and the
best fits come first; claimers are folded at the bottom.
    python mockups/entry_v2_make.py <save.pkl> [horse name]"""
import html, os, shutil, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); os.chdir(ROOT)
import app

c, sk = app.c, app.sk
esc = html.escape


def level(r):
    """The tier of a horse rated r: how good this class's fields are."""
    return next((t for cut, t in app.MILE_TIERS if c.mile_secs(r) <= cut), "D")


def edge(h, r):
    d = h.est - r
    return ("Favorite", "fav") if d >= 10 else ("Contender", "con") if d >= 3 else ("Even match", "even") if d >= -3 else ("Up against it", "long")


if __name__ == "__main__":
    app.load(sys.argv[1])
    name = sys.argv[2] if len(sys.argv) > 2 else "Lake Road"
    h = next(x for x in app.G["horses"] if x.name == name)
    day, wk = app.G["day"], app.G["day"] % c.YEAR
    her = "her" if h.sex == "f" else "him"
    coat, marking = app.looks(h)
    os.makedirs(os.path.join(HERE, "entry_v2"), exist_ok=True)
    shutil.copyfile(app.recolor.portrait(coat, marking, app.pattern(h), 256), os.path.join(HERE, "entry_v2", "portrait.png"))
    tags = {c.clm_name(t): t for t, _, _ in c.CLAIMERS}
    races = defaultdict(list)
    for v, rname, purse, vpurse, tag, track in c.offerings(h):
        races[rname].append((vpurse, v, track))
    rows = []
    for rname, offers in races.items():
        offers.sort(key=lambda o: -o[0])
        r = c.CLASS_RATING.get(rname, 55)
        lab, cls = edge(h, r)
        rows.append(dict(name=c.race_title(c.age_group(h), rname), raw=rname, tag=tags.get(rname, 0), offers=offers,
                         best=offers[0][0], level=level(r), edge=lab, ecls=cls, score=offers[0][0] * {"fav": 1.0, "con": .7, "even": .45, "long": .2}[cls]))
    conds = sorted([x for x in rows if not x["tag"]], key=lambda x: -x["score"])
    claims = sorted([x for x in rows if x["tag"]], key=lambda x: -x["best"])
    picks = conds[:3]
    stakes = sorted((s for s in sk.CALENDAR if not s.result and s.week >= wk and s.eligible(h)), key=lambda s: s.week)[:4]

    def track_chip(v, track):
        p, a, f, about, badge = app.TI.look(v["id"])
        return (f"<span class=trk style='--tp:{p};--ta:{a}'><b>{esc(v['name'])}</b><i>{'mile' if track == 'mile' else 'half'}"
                f"{' · passing lane' if v.get('passing') else ''}</i></span>")

    def race_row(x, open_=False):
        top = x["offers"][0]
        more = x["offers"][1:]
        others = "".join(f"<div class=alt>{track_chip(v, t)}<span class=money>${p:,}</span><button class=sec>Enter</button></div>" for p, v, t in more)
        return (f"<details class=race{' open' if open_ else ''}><summary><div class=rmain><div class=rname>{esc(x['name'])}</div>"
                f"<div class=rmeta><span class='lvl t{x['level'].replace('+', 'p')}'>Field {x['level']}</span><span class='edge {x['ecls']}'>{x['edge']}</span></div></div>"
                f"<div class=rright><span class=money>${top[0]:,}</span>{track_chip(top[1], top[2])}</div></summary>"
                f"<div class=rbody><div class=alt best>{track_chip(top[1], top[2])}<span class=money>${top[0]:,}</span><button>Enter</button></div>{others}</div></details>")

    def stake_row(s):
        nom = h in s.noms
        out = s.week - wk
        when = "next week" if out == 1 else "this week" if out == 0 else f"in {out} weeks"
        act = "<span class=nomd>✓ Nominated</span>" if nom else f"<button class=sec>Nominate · ${s.fee(day):,.0f}</button>"
        return (f"<div class='stk{' nom' if nom else ''}'><div><div class=sname>{esc(s.name)}</div><div class=sub>{when} · purse <span class=money>${s.purse:,.0f}</span></div></div>{act}</div>")

    pick_html = "".join(
        f"<div class=pick><div class=pk>{k + 1}</div><div class=pm><b>{esc(x['name'])}</b><div class=sub>{esc(x['offers'][0][1]['name'])} · "
        f"{'mile' if x['offers'][0][2] == 'mile' else 'half-mile'} · field {x['level']}</div></div><div class=pr><span class=money>${x['best']:,}</span>"
        f"<span class='edge {x['ecls']}'>{x['edge']}</span></div><button>Enter</button></div>" for k, x in enumerate(picks))
    page = f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Entry Sheet</title>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800&family=Barlow+Semi+Condensed:wght@400;600;700&display=swap" rel=stylesheet>
<style>
:root{{--paper:#070a14;--sky:#0b1430;--panel:#111a2b;--rule:#2b3a55;--rule2:#1b2539;--edge:#05070d;--ink:#e6e8ec;--ink2:#a4acb9;--ink3:#6f7886;
--tote:#e8a33a;--tote-ink:#2a1a03;--led:#ffb347;--ledglow:rgba(255,179,71,.55);--win:#3fb96b;--loss:#e0704f}}
*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(var(--sky),var(--paper) 320px);color:var(--ink);font:400 15px 'Barlow Semi Condensed',sans-serif;font-variant-numeric:tabular-nums}}
.wrap{{max-width:420px;margin:0 auto;padding:10px 12px 40px;overflow-x:hidden}}
h1{{font:800 22px 'Barlow Condensed',sans-serif;letter-spacing:.06em;text-transform:uppercase;margin:4px 0 10px;text-shadow:2px 2px 0 #000}}
.sec-h{{font:800 13px 'Barlow Condensed',sans-serif;letter-spacing:.1em;text-transform:uppercase;color:var(--led);margin:16px 2px 6px;display:flex;justify-content:space-between}}
.sec-h span{{color:var(--ink3);letter-spacing:.04em}}
.card,.race,.stk,.pick{{background:var(--panel);border:1px solid var(--rule);border-radius:4px}}
.horse{{display:flex;gap:10px;align-items:center;padding:8px}}.horse img{{width:64px;height:64px;image-rendering:pixelated;border:3px solid #c084fc;border-radius:2px}}
.horse b{{font:800 19px 'Barlow Condensed',sans-serif;letter-spacing:.02em}}.sub{{color:var(--ink2);font-size:13px}}
.tierb{{display:inline-block;font:800 13px 'Barlow Condensed',sans-serif;padding:0 6px;background:conic-gradient(from 30deg,#f0abfc,#818cf8,#38bdf8,#67e8f9,#fde68a,#f0abfc);color:#1a0b2e;margin-left:6px}}
.when{{display:flex;gap:4px;margin-top:8px}}.when button{{flex:1;min-width:0}}.horse>div{{min-width:0}}
button{{font:800 13px 'Barlow Condensed',sans-serif;letter-spacing:.06em;text-transform:uppercase;padding:7px 12px;border:2px solid var(--edge);border-radius:3px;
background:linear-gradient(#ffd36b,#e8a33a 55%,#c27c1c);color:var(--tote-ink);box-shadow:2px 2px 0 var(--edge);cursor:pointer;white-space:nowrap}}
button.sec{{background:linear-gradient(#1a2338,#121a2b);color:var(--ink);border-color:#0a0f1c}}button.off{{opacity:.45}}
.money{{font-weight:700;color:var(--led);text-shadow:0 0 6px var(--ledglow)}}
.stk{{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:8px 10px;margin-bottom:6px;border-left:4px solid var(--rule)}}.stk>div{{min-width:0}}.stk>button{{flex:none;padding:6px 8px}}
.stk.nom{{border-left-color:var(--tote);background:linear-gradient(100deg,#e8a33a1f,var(--panel) 60%)}}.sname{{font-weight:700}}.nomd{{color:var(--win);font-weight:700;font-size:13px;white-space:nowrap}}
.pick{{display:grid;grid-template-columns:20px minmax(0,1fr) auto;grid-template-areas:'k m r' 'k m b';gap:4px 8px;align-items:center;padding:8px 10px;margin-bottom:6px}}.pick .pk{{grid-area:k}}.pick .pm{{grid-area:m;min-width:0}}.pick .pr{{grid-area:r}}.pick>button{{grid-area:b;justify-self:end}}
.pk{{font:800 18px 'Barlow Condensed',sans-serif;color:var(--tote)}}.pm b{{font-size:15px}}.pr{{display:flex;flex-direction:column;align-items:flex-end;gap:2px}}
.chips{{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;margin:4px 0}}.chips a{{flex:none;font:800 12px 'Barlow Condensed',sans-serif;letter-spacing:.06em;text-transform:uppercase;
padding:5px 10px;border:1px solid var(--rule);color:var(--ink2);text-decoration:none;border-radius:3px}}.chips a.on{{background:var(--tote);color:var(--tote-ink);border-color:var(--tote)}}
.race{{margin-bottom:6px}}.race summary{{list-style:none;display:flex;justify-content:space-between;gap:8px;padding:9px 10px;cursor:pointer}}.rmain{{min-width:0}}.rright{{flex:none;max-width:48%}}.race summary::-webkit-details-marker{{display:none}}
.rname{{font-weight:700}}.rmeta{{display:flex;gap:6px;margin-top:3px}}.rright{{display:flex;flex-direction:column;align-items:flex-end;gap:3px;text-align:right}}
.lvl{{font:800 11px 'Barlow Condensed',sans-serif;letter-spacing:.06em;padding:1px 6px;color:#fff;border-radius:2px}}
.tSp{{background:linear-gradient(90deg,#c084fc,#38bdf8)}}.tS{{background:#b45309}}.tA{{background:#1f4fbf}}.tB{{background:#1f7a3f}}.tC{{background:#6b7280}}.tD{{background:#3b3f46}}
.edge{{font:800 11px 'Barlow Condensed',sans-serif;letter-spacing:.06em;text-transform:uppercase;padding:1px 6px;border-radius:2px}}
.edge.fav{{background:#3fb96b26;color:#4ade80}}.edge.con{{background:#e8a33a26;color:var(--led)}}.edge.even{{background:#a4acb926;color:var(--ink)}}.edge.long{{background:#e0704f26;color:#f87171}}
.trk{{display:inline-flex;flex-direction:column;font-size:12px;line-height:1.15;padding-left:6px;border-left:3px solid var(--ta)}}.trk b{{font-size:12.5px}}.trk i{{font-style:normal;color:var(--ink3)}}
.rbody{{border-top:1px solid var(--rule2);padding:4px 10px 8px}}.alt{{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:8px;align-items:center;padding:5px 0}}
.clm{{margin-top:14px;border:1px solid #e0704f55;border-radius:4px;background:#e0704f0d}}.clm>summary{{list-style:none;padding:9px 10px;cursor:pointer;font:800 13px 'Barlow Condensed',sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--loss)}}
.clm .race{{margin:0 6px 6px}}
.note{{font-size:12px;color:var(--ink3);margin:6px 2px}}
</style></head><body><div class=wrap>
<h1>Enter {esc(h.name)}</h1>
<div class='card horse'><img src="entry_v2/portrait.png" alt=""><div style=flex:1><b>{esc(h.name)}</b><span class=tierb>{app.tier_label(h)}</span>
<div class=sub>{h.age}yo {'mare' if h.sex == 'f' else 'horse'} · Fit {h.freshness:.0f} · best {app.best_time(h)} · sits off the pace</div>
<div class=when><button>Tonight</button><button class=sec>Tomorrow</button></div></div></div>

<div class=sec-h>Stakes<span>{sum(h in s.noms for s in stakes)} nominated</span></div>
{''.join(stake_row(s) for s in stakes)}

<div class=sec-h>Best fits tonight<span>purse × her chances</span></div>
{pick_html}

<div class=sec-h>All races<span>{len(conds)} races · {sum(len(x['offers']) for x in conds)} cards</span></div>
<div class=chips><a class=on href=#>Best fit</a><a href=#>Purse</a><a href=#>Mile</a><a href=#>Half-mile</a><a href=#>Passing lane</a></div>
{''.join(race_row(x, open_=(k == 0)) for k, x in enumerate(conds))}

<details class=clm><summary>Claiming races ({len(claims)}) · any barn can take {her} for the tag</summary>
{''.join(race_row(x) for x in claims)}</details>
<p class=note>Mockup from the live save copy: {esc(h.name)}'s real book ({sum(len(x['offers']) for x in rows)} cards at {len({o[1]['id'] for x in rows for o in x['offers']})} tracks). Field level is the class's typical rating; the chance label compares {her} to it.</p>
</div></body></html>"""
    open(os.path.join(HERE, "entry_v2.html"), "w", encoding="utf-8").write(page)
    print("wrote mockups/entry_v2.html |", len(conds), "conditioned races,", len(claims), "claimers,", len(stakes), "stakes | picks:", [x["name"] for x in picks])
