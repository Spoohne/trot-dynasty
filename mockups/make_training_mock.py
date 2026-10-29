"""Mockup of the Training tab (decision B): the trainer's day sheet for every youngster, yearlings through
3-year-olds, built on the game's own page() and cards so it matches the skin. Read-only; writes mockups/training_mock.html."""
import os, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.getcwd()); sys.argv = ["x"]
import app
G, e, c = app.G, app.e, app.c
app.save = app.snapshot = lambda *a, **k: None
app.load()
app.ME = 0
app.P(0).setdefault("events", [])

# a yearling from the nursery and two 2-3YOs: shown as the player's for the mock
year = next(f for f in e.nursery if f.age == 1)
twos = [h for h in G["horses"] if not h.retired and h.age == 2 and h.starts >= 3][:2]
three = next(h for h in G["horses"] if not h.retired and h.age == 3 and h.starts >= 6)
for h in (year, *twos, three):
    h.owner = 0
twos[0].freshness, twos[1].freshness, three.freshness = 82, 44, 70

CSS = """
.tsheet{margin-top:8px}
.ts .bname{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.ts .bname .age{font-family:'Barlow Semi Condensed',sans-serif;font-size:13px;font-weight:400;color:var(--ink2)}
.sheet{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:8px}
.sheet button{width:100%;padding:8px 2px;font-size:13px;letter-spacing:.04em}
.sheet button.done,.sheet button.done:hover{background:var(--tote);color:var(--tote-ink);border-color:var(--edge)}
.sheet button[disabled]{opacity:.35;box-shadow:none;transform:none}
.sheet .foc{grid-column:1/-1;display:flex;gap:6px;align-items:center;font-size:13px;color:var(--ink2);flex-wrap:wrap}
.sheet .foc a{color:var(--ink);background:var(--well);border:2px solid var(--rule);padding:1px 8px;text-decoration:none}
.sheet .foc a.on{border-color:var(--tote);color:var(--tote)}
.didnote{font-size:13px;color:var(--ink2);margin-top:6px}
.didnote b{color:var(--win)}
.tabs a .tbadge{position:absolute;top:3px;right:8px;background:var(--tote);color:var(--tote-ink);font-size:10px;font-weight:800;line-height:1;padding:2px 4px;border-radius:8px;border:2px solid var(--edge);min-width:8px;text-align:center}
.tabs a{position:relative}
.stablehead h2 .stallct{margin-left:8px}
"""

def sheet(h, done=None, focus="gait", note=""):
    btn = lambda key, label: (f"<button class='sec{' done' if done == key else ''}'{' disabled' if done and done != key else ''}>{label}</button>")
    foc = "".join(f"<a href='#' class='{'on' if k == focus else ''}'>{t}</a>" for k, t in (("gait", "Gait"), ("early_speed", "Early speed"), ("late_speed", "Late speed"), ("stamina", "Stamina")))
    return (f"<div class=sheet>{btn('jog', 'Jog')}{btn('train', 'Train')}{btn('school', 'School')}{btn('out', 'Turn out')}"
            + ("" if done else f"<div class=foc><span>Training focus</span>{foc}</div>") + "</div>"
            + (f"<div class=didnote>{note}</div>" if note else ""))

def row(h, what, done=None, focus="gait", note=""):
    bars = "".join(app.stat_bar(h.developed[t], h, k.capitalize(), trait=t, goal=h.ceiling(t, 2) - 2.0 if h in e.nursery else None) for k, t in app.FOCUS.items())
    return (f"<div class='card brow hc ts' style='--tc:{app.TIER_RGB[app.tier_base(h)]}'><div class=pcol>{app.square_portrait(h)}</div><div style='flex:1;min-width:0'>"
            f"<div class=bname><a href='/horse/{app.urlname(h.name)}'>{app.esc(h.name)}</a><span class=age>{what}</span></div>"
            f"<div class=bbars>{bars}</div>"
            f"<div class=row style='gap:4px 10px;margin-top:4px;flex-wrap:wrap'>{app.condition(h)}</div>"
            f"{sheet(h, done, focus, note)}</div></div>")

body = (
    "<a href='#' style='display:block;margin:8px 0;padding:10px 12px;border-radius:6px;background:#e8a33a;color:#111;font-weight:700;text-decoration:none'>"
    "2 youngsters not worked today ›</a>"
    "<div class=stablehead><h2>Day sheet <span class='stallct st-grn'>2/4</span></h2></div>"
    "<div class=sub style='margin:-4px 0 8px'>Yearlings, 2 and 3-year-olds: one job a day, your call. The stable jogs any you don't get to.</div>"
    + row(year, "yearling filly", note="")
    + row(twos[0], "2yo colt", done="train", focus="gait", note="<b>Trained today</b>, gait miles. Gaited better by the third mile.")
    + row(twos[1], "2yo filly", done="out", note="<b>Turned out</b>. Back fit by the weekend.")
    + row(three, "3yo colt")
    + "<div class=card><div class=sub><b>Jog</b> keeps a youngster ticking over. <b>Train</b> is training miles: the big step, on the focus you pick, and it takes something out of the horse. "
      "<b>School</b> is gait work. <b>Turn out</b> is a day off that brings freshness back. Older horses are kept sound, not trained: see them in the Barn.</div></div>"
)
html = app.page("Training", body)
html = html.replace("<style>", f"<style>{CSS}", 1)
# the fifth tab, with its badge, in second place
tab = ("<a href=/training class=on aria-current=page><svg viewBox='0 0 24 24' width=22 height=22 fill=none stroke=currentColor stroke-width=1.8 stroke-linejoin=round aria-hidden=true>"
       "<circle cx='12' cy='13' r='8'/><path d='M12 9v4l3 2M9 2h6'/></svg>Training<span class=tbadge>2</span></a>")
html = html.replace("<a href=/market", tab + "<a href=/market", 1).replace("<a href=/ class=on aria-current=page", "<a href=/", 1)
for h in (year, *twos, three):                                # portraits are a live route: point at the rendered file
    coat, marking = app.looks(h)
    html = html.replace(f"/portrait/{app.urlname(h.name)}.png", "/" + app.recolor.portrait(coat, marking, app.pattern(h), 256).replace("\\", "/").split("HarnessSim/")[-1])
html = html.replace("src=/mock/", "src=/mockups/").replace("src='/mock/", "src='/mockups/").replace('src="/mock/', 'src="/mockups/').replace("url(/mock/", "url(/mockups/")   # the static server has no /mock route
open("mockups/training_mock.html", "w", encoding="utf-8").write(html)
print("wrote mockups/training_mock.html", year.name, twos[0].name, twos[1].name, three.name)
