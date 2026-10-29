"""Builds prestige.html: a mockup of the 10 Prestige tiers of the Marquee (python mockups/brand/marquee/make_prestige.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import crest as CR

EM = {"shape": "shield", "c1": "#1f4fbf", "c2": "#f2d233", "dev": "horse"}
NAME = "Spoon Hill Stables"
T = "/mock/brand/trophies/"
# one look that grows: the same gilded nameplate and gold light throughout; the early tiers add touches,
# from V on each tier is a step change (new gold scene, the emblem dressed up, rays, a taller banner, the crown)
# tier: (name, milestone, scene or None, frame, bulb, font, shimmer, trophies shown, extra classes)
TIERS = [
    ("Nameplate", "Buy the Marquee", None, "brass", "gold", "gilded", False, 0, "pt-dim"),
    ("Spotlight", "Win a stake", None, "brass", "gold", "gilded", False, 0, "pt-spot"),
    ("Grandstand", "$2.5M earned by your horses", "grandstand", "brass", "gold", "gilded", False, 0, "pt-dusk"),
    ("Flashbulbs", "10 stakes won", "grandstand", "brass", "gold", "gilded", False, 1, ""),
    ("Marquee Lights", "Win a Crown final", "grandstand", "bulbs", "gold", "gilded", False, 1, "pt-spill"),
    ("Gilded Hall", "Train a division champion", "gilded", "bulbs", "gold", "gilded", True, 2, "pt-spill pt-wreath"),
    ("Golden Hour", "Set a course record", "sunset", "bulbs", "gold", "gilded", True, 2, "pt-spill pt-wreath pt-embers"),
    ("Grand Marquee", "$10M earned by your horses", "sunset", "bulbs", "gold", "gilded", True, 3, "pt-spill pt-wreath pt-embers pt-rays pt-double pt-tall"),
    ("Gold Halo", "5 Crown finals won", "gilded", "goldspin", "gold", "gilded", True, 3, "pt-wreath pt-embers pt-rays pt-glow pt-sweep pt-tall"),
    ("Dynasty", "3 Horse of the Year titles", "sunset", "goldspin", "gold", "gilded", True, 3, "pt-wreath pt-embers pt-rays pt-glow pt-sweep pt-tall pt-crown px-dynasty"),
]
TROPHIES = ["cup", "horseshoe", "crown"]


def marquee(i, t):
    name, _, scene, frame, bulb, font, shim, n, extra = t
    bg = f"--bg:url(/mock/brand/marquee/{scene}.png)" if scene else "--bg:linear-gradient(#2a2016,#120d08)"
    imgs = [f"<img src={T}{k}.png alt=''>" for k in TROPHIES[:n]]
    return (f"<div class='mqx mqbig {'sc-' + scene if scene else 'sc-plain'} fr-{frame} {extra}' style='{bg};--bulb:{CR.BULBS[bulb]}'>"
            f"<i class=mqfx></i>{'<i class=mqboom></i>' if 'dynasty' in extra else ''}<span class='mqshelf l'>{''.join(imgs[0::2])}</span>"
            f"<div class=mqmid><span class=mqped>{CR.svg(EM, 56)}{f'<img class=pcrown src={T}crown.png alt=''>' if 'pt-crown' in extra else ''}</span>"
            f"{'<i class=pember></i>' if 'pt-embers' in extra else ''}"
            f"<span class='mqn nf-{font}{' shim' if shim else ''}' data-t='{NAME}'>{NAME}</span></div>"
            f"<span class='mqshelf r'>{''.join(imgs[1::2])}</span><b class=pxbadge>{'I II III IV V VI VII VIII IX X'.split()[i]}</b></div>")


rows = "".join(f"<section><div class=hd><b>Prestige {i + 1} · {t[0]}</b><span>{t[1]}</span></div>{marquee(i, t)}</section>" for i, t in enumerate(TIERS))
html = f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>Marquee Prestige</title><link rel=stylesheet href=/mock/brand/marquee/marquee.css?v=3>
<link href='https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;800&display=swap' rel=stylesheet>
<style>
body{{margin:0;background:#0b0e16;color:#d7dceb;font:15px 'Barlow Condensed',sans-serif}}main{{max-width:760px;margin:0 auto;padding:16px}}
h1{{font-size:28px;letter-spacing:.06em;text-transform:uppercase;color:#ffd36b;margin:8px 0 4px}}p{{color:#9aa3b8;margin:0 0 14px}}
section{{margin:0 0 18px}}.hd{{display:flex;justify-content:space-between;gap:10px;margin-bottom:6px;font-size:16px}}.hd b{{color:#ffd36b;letter-spacing:.04em;text-transform:uppercase}}.hd span{{color:#9aa3b8}}
.pxbadge{{position:absolute!important;top:6px;right:10px;z-index:6!important;font:800 12px 'Cinzel',serif;color:#ffe9a8;text-shadow:0 1px 2px #000}}
.pt-spill:before{{content:'';position:absolute;inset:0;z-index:2;pointer-events:none;box-shadow:inset 0 0 26px #ffd36b88}}
.pt-wreath .mqped{{box-shadow:0 0 0 3px #e9cf86,0 0 0 5px #3a2a06,0 0 0 8px #a8701a,0 0 18px #ffd36baa}}
.pember{{position:absolute!important;inset:0;z-index:2!important;pointer-events:none;
  background:radial-gradient(circle,#ffd36b 0 1.4px,#0000 2.2px) 0 0/29px 23px,radial-gradient(circle,#fff3b0 0 1px,#0000 1.8px) 9px 5px/41px 37px;animation:pember 5s linear infinite}}
@keyframes pember{{to{{background-position:14px -92px,-20px -148px}}}}
.pt-rays .mqmid:before{{content:'';position:absolute;left:-60px;top:50%;width:200px;height:200px;margin-top:-100px;z-index:-1;border-radius:50%;
  background:repeating-conic-gradient(#ffd36b55 0 6deg,#0000 6deg 18deg);-webkit-mask:radial-gradient(#000 20%,#0000 68%);mask:radial-gradient(#000 20%,#0000 68%);animation:prays 14s linear infinite}}
.mqmid{{position:relative}}.sc-sunset{{background:linear-gradient(90deg,#000d,#000a 55%,#000d),var(--bg) center/cover,#05070d}}@keyframes prays{{to{{transform:rotate(360deg)}}}}
.pt-tall{{min-height:130px!important}}.pt-tall .mqn{{font-size:40px}}.pt-tall .mqped{{width:78px;height:78px}}.pt-tall .mqped .crest{{width:64px;height:64px}}
.mqped{{position:relative}}.pcrown{{position:absolute;width:34px;top:-24px;left:50%;margin-left:-17px;filter:drop-shadow(0 2px 3px #000)}}
.px-dynasty .mqboom:before,.px-dynasty .mqboom:after{{animation-iteration-count:infinite;animation-duration:2.4s}}
.pt-glow .mqn{{filter:drop-shadow(0 0 8px #ffd36b)}}
.pt-dim .mqn{{filter:saturate(.6) brightness(.85)}}
.pt-spot{{--bg:radial-gradient(ellipse at 50% 50%,#5a4320,#120d08 70%)!important}}
.pt-dusk{{background:linear-gradient(90deg,#000e,#000b 55%,#000d),var(--bg) center/cover!important}}.pt-dusk .mqfx{{display:none}}
.pt-sweep .mqfx:after{{background:linear-gradient(105deg,#0000 30%,#ffe9a866 47%,#fff9 50%,#ffe9a866 53%,#0000 70%) 0 0/50% 100% no-repeat;animation:mqsweep 4.5s ease-in-out infinite}}
.pt-double{{box-shadow:inset 0 0 0 9px #0000,inset 0 0 0 12px #e9cf86,inset 0 0 0 13px #000}}
.fr-goldspin:after{{border:6px solid;border-image:conic-gradient(from var(--ang),#fff6c8,#f2c14e,#a8701a,#fff6c8,#e8a33a,#7a5a1c,#fff6c8) 1;
  box-shadow:inset 0 0 14px #ffd36b66,0 0 12px #ffd36b88;animation:mqspin 3s linear infinite}}
.prog{{background:#151a28;border:1px solid #2a3148;padding:12px;margin:0 0 20px}}.bar{{height:10px;background:#05070d;margin:8px 0 4px}}.bar i{{display:block;height:100%;width:62%;background:linear-gradient(90deg,#b45309,#ffd36b)}}
</style></head><body><main>
<h1>Marquee Prestige</h1>
<p>Mockup. The Marquee grows with the barn: each milestone graduates it one tier, from a plain plate to the Dynasty marquee. One look throughout (the gilded nameplate, gold light, the grandstand); each tier adds to the one before. The owner only chooses which unlocked tier to display and which trophies sit on the shelf.</p>
<div class=prog><b style='color:#ffd36b'>PRESTIGE 4 · FLASHBULBS</b> &nbsp;Next: Marquee Lights, win a Crown final<div class=bar><i></i></div><span style='color:#9aa3b8'>The progress bar a player would see on the Emblem page.</span></div>
{rows}</main><script>document.querySelectorAll('.mqn').forEach(n=>{{let z=parseFloat(getComputedStyle(n).fontSize);while(n.scrollWidth>n.clientWidth&&z>11)n.style.fontSize=(z-=1)+'px'}})</script></body></html>"""
open(os.path.join(os.path.dirname(__file__), "prestige.html"), "w", encoding="utf-8").write(html)
print("ok")
