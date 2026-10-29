"""Builds tracks.html: mockup of the track identities (badge sheet, a program race header, a replay title card) for two tracks.
python mockups/brand/tracks/make_mock.py, view at /mock/brand/tracks/tracks.html"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import circuit as c
import track_id as T

names = {v["id"]: v["name"] for v in c.VENUES}
sheet = "".join(
    f"<div class=tb style='--p:{p};--a:{a}'><img src={b} width=64 height=64 alt=''><b style=\"font-family:{f}\">{names[k]}</b><span>{m}</span></div>"
    for k in T.TRACKS for p, a, f, m, b in [T.look(k)])


def program(k, race, purse):
    p, a, f, m, b = T.look(k)
    return (f"<div class=pgh2 style='--p:{p};--a:{a}'><img src={b} width=48 height=48 alt=''><div class=pgt2><span class=pgtn style=\"font-family:{f}\">{names[k]}</span>"
            f"<span class=pgr2>Race 4 · {race}</span><span class=pgm2>{m}</span></div><div class=pgp2><small>PURSE</small><b>${purse:,}</b><small>8 IN</small></div></div>")


def title(k, race):
    p, a, f, m, b = T.look(k)
    return (f"<div class=tc style='--p:{p};--a:{a}'><img src={b} width=96 height=96 alt=''><div><div class=tcn style=\"font-family:{f}\">{names[k]}</div>"
            f"<div class=tcr>Race 7 · {race}</div><div class=tcm>{m}</div></div></div>")


html = f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Track identities</title>
<link href='https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;800&family=Barlow+Semi+Condensed:wght@500;700&family=Cinzel:wght@900&family=Jersey+10&family=Bungee&display=swap' rel=stylesheet>
<style>
body{{margin:0;background:#070a14;color:#e6e8ec;font:15px 'Barlow Semi Condensed',sans-serif}}main{{max-width:420px;margin:0 auto;padding:16px 14px}}
h1{{font:800 26px 'Barlow Condensed';letter-spacing:.06em;text-transform:uppercase;color:#ffb347;margin:8px 0}}h2{{font:800 17px 'Barlow Condensed';letter-spacing:.06em;text-transform:uppercase;color:#a4acb9;margin:18px 0 8px}}
.sheet{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
.tb{{display:flex;flex-direction:column;align-items:center;gap:3px;text-align:center;padding:10px 6px;background:linear-gradient(var(--p),color-mix(in srgb,var(--p) 55%,#05070d));border:2px solid #05070d;box-shadow:inset 0 0 0 2px var(--a)}}
.tb img{{filter:drop-shadow(0 3px 2px #000a)}}.tb b{{font-size:20px;line-height:1.05;color:#fff;text-shadow:2px 2px 0 #000}}.tb span{{font-size:12px;color:#ffffffcc}}
.pgh2{{display:flex;gap:10px;align-items:center;padding:8px 10px;background:linear-gradient(100deg,var(--p),color-mix(in srgb,var(--p) 60%,#05070d));border-bottom:4px solid var(--a);color:#fff;margin-bottom:10px}}
.pgt2{{flex:1;min-width:0;display:flex;flex-direction:column}}.pgtn{{font-size:22px;line-height:1;text-shadow:2px 2px 0 #000}}.pgr2{{font:800 14px 'Barlow Condensed';letter-spacing:.06em;text-transform:uppercase}}.pgm2{{font-size:12px;opacity:.8}}
.pgp2{{display:flex;flex-direction:column;align-items:flex-end;font:800 12px 'Barlow Condensed';letter-spacing:.08em}}.pgp2 b{{font-size:22px;color:var(--a);text-shadow:1px 1px 0 #000}}
.tc{{display:flex;gap:14px;align-items:center;padding:16px;background:radial-gradient(ellipse at 20% 50%,color-mix(in srgb,var(--p) 80%,#fff 10%),var(--p) 45%,color-mix(in srgb,var(--p) 40%,#05070d));border:3px solid var(--a);box-shadow:0 0 0 3px #05070d,0 6px 14px #000c;margin-bottom:12px}}
.tcn{{font-size:30px;line-height:1;color:#fff;text-shadow:3px 3px 0 #000}}.tcr{{font:800 16px 'Barlow Condensed';letter-spacing:.08em;text-transform:uppercase;color:var(--a);margin-top:4px}}.tcm{{font-size:13px;color:#ffffffcc}}
</style></head><body><main><h1>Track identities</h1>
<h2>All ten badges</h2><div class=sheet>{sheet}</div>
<h2>Program race header</h2>{program("hp", "The Invitational", 51700)}{program("bf", "NW2L6", 13500)}{program("ng", "Open", 28500)}
<h2>Replay title card</h2>{title("cr", "Preferred")}{title("ml", "2YO Open")}
</main></body></html>"""
open(os.path.join(os.path.dirname(__file__), "tracks.html"), "w", encoding="utf-8").write(html)
print("ok")
