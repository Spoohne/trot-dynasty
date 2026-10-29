"""Builds v2.html: mockup of the redrafted Marquee art (SpriteCook pixel scenes, Jersey 10 pixel nameplate) across all
10 Prestige tiers (python mockups/brand/marquee/make_v2.py, view at /mock/brand/marquee/v2.html)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import crest as CR

EM = {"shape": "shield", "c1": "#1f4fbf", "c2": "#f2d233", "dev": "horse"}
NAME = "Spoon Hill Stables"
T = "/mock/brand/trophies/"
TROPHIES = ["cup", "horseshoe", "crown", "clock", "money", "medal"]   # the six trophy kinds a barn can earn


def marquee(t, shelf=None):
    name, key, n, scene, frame, shim, slots, fx = CR.PRESTIGE[t - 1]
    metal = "gold" if t >= 7 else "silver" if t >= 4 else "iron"
    bg = f"url(/mock/brand/marquee/v2/{scene or 'plate'}.png)"
    imgs = [f"<img src={T}{k}.png alt=''>" for k in (shelf or TROPHIES)[:slots]]
    return (f"<div class='mqx mqbig v2 sc-{scene or 'plain'} fr-{frame} {fx}' style='--bg:{bg};--bulb:{CR.BULBS['gold']}'>"
            f"<i class=mqfx></i>{'<i class=mqboom></i>' if 'pt-dynasty' in fx else ''}{"<i class=sparks><i class=sp style='left:14%;top:22%;animation-delay:0s'></i><i class=sp style='left:31%;top:70%;animation-delay:1.1s'></i><i class=sp style='left:47%;top:18%;animation-delay:2.3s'></i><i class=sp style='left:63%;top:62%;animation-delay:0.6s'></i><i class=sp style='left:78%;top:28%;animation-delay:1.7s'></i><i class=sp style='left:91%;top:68%;animation-delay:2.9s'></i><i class=sp style='left:56%;top:40%;animation-delay:3.4s'></i></i>" if 'pt-embers' in fx else ''}{"<i class=corners><b></b><b></b><b></b><b></b></i>" if 'pt-corners' in fx else ''}"
            f"<span class='mqshelf l'>{''.join(imgs[:1])}</span>"
            f"<div class=mqmid><span class='mqped ld-{metal}'>{CR.svg({**EM, 'rim': metal}, 64)}"
            f"{'<img class=pcrown src=/mock/brand/trophies/crown.png alt=>' if 'pt-crown' in fx else ''}</span>"
            f"<span class=mqname><span class='mqn np np-{metal}' data-t='{NAME}'>{NAME}</span>"
            + (f"<span class=mqunder>{''.join(imgs[2:])}</span>" if imgs[2:] else "") + "</span></div>"
            f"<span class='mqshelf r'>{''.join(imgs[1:2])}</span><b class=pxbadge>{CR.NUMERAL[t - 1]}</b></div>")


rows = "".join(f"<section><div class=hd><b>Prestige {CR.NUMERAL[t - 1]} · {CR.PRESTIGE[t - 1][0]}</b>"
               f"<span>{CR.milestone(*CR.PRESTIGE[t - 1][1:3])}</span></div>{marquee(t)}</section>" for t in range(1, 11))
rows += ("<section><div class=hd><b>Fully decked · Prestige X</b><span>8 trophies: one each side, six in the tray</span></div>"
         + marquee(10, ["cup", "crown"] + TROPHIES) + "</section>")
html = f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>Marquee v2</title><link rel=stylesheet href=/mock/brand/marquee/marquee.css?v=6>
<link href='https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;800&family=Jersey+10&display=swap' rel=stylesheet>
<style>
body{{margin:0;background:#070a14;color:#d7dceb;font:15px 'Barlow Condensed',sans-serif}}main{{max-width:420px;margin:0 auto;padding:16px 14px}}
h1{{font-size:26px;letter-spacing:.06em;text-transform:uppercase;color:#ffb347;margin:8px 0 4px}}p{{color:#a4acb9;margin:0 0 14px}}
section{{margin:0 0 18px}}.hd{{display:flex;justify-content:space-between;gap:10px;margin-bottom:6px;font-size:15px}}.hd b{{color:#ffb347;letter-spacing:.04em;text-transform:uppercase}}.hd span{{color:#a4acb9}}
/* v2: the pixel scenes need only a light scrim behind the name; the plate tiers sit on the walnut board */
.mqx.v2{{background:linear-gradient(90deg,#0009,#0003 30%,#0003 70%,#0009),var(--bg) center/cover,#05070d}}
.mqx.v2.sc-plain{{background:var(--bg) center/100% 100%,#2a1a0c}}
.v2.pt-dusk{{background:linear-gradient(#0008,#0008),var(--bg) center/cover}}
.v2.pt-spot.sc-plain{{background:radial-gradient(ellipse at 50% 50%,#ffd36b40,#0000 60%),var(--bg) center/100% 100%}}
/* the pixel nameplate: Jersey 10, a metal fill by Prestige, a hard 1px outline and drop shadow */
.np{{font-family:'Jersey 10',sans-serif;font-size:34px;letter-spacing:.02em;-webkit-background-clip:text;background-clip:text;color:transparent;
  filter:drop-shadow(1px 0 0 #1a0f04) drop-shadow(-1px 0 0 #1a0f04) drop-shadow(0 1px 0 #1a0f04) drop-shadow(0 -1px 0 #1a0f04) drop-shadow(0 3px 0 #000a)}}
.mqbig.pt-tall .np{{font-size:44px}}
.np-iron{{background-image:linear-gradient(#d9cbb8,#9a8a76 55%,#6d5f50)}}
.np-silver{{background-image:linear-gradient(#ffffff,#c9d2de 50%,#8793a3)}}
.np-gold{{background-image:linear-gradient(#ffe58a,#f5b83d 50%,#d08a1e 62%,#9a6212)}}
.v2 .mqshelf{{gap:2px}}.v2 .mqshelf img{{width:26px;height:26px;padding:1px 2px 3px}}.mqbig.v2 .mqshelf img{{width:28px;height:28px}}
.mqbig.v2.pt-tall .mqped{{width:70px;height:70px}}.mqx.v2{{gap:8px;padding-left:12px;padding-right:12px}}
.pt-glow .np{{filter:drop-shadow(1px 0 0 #1a0f04) drop-shadow(-1px 0 0 #1a0f04) drop-shadow(0 1px 0 #1a0f04) drop-shadow(0 -1px 0 #1a0f04) drop-shadow(0 0 8px #ffd36b)}}
 /* the emblem stands free on a little metal ledge (no circle), metal by Prestige */
.v2 .mqped,.v2.pt-wreath .mqped{{background:none;box-shadow:none;border-radius:0;width:auto!important;height:auto!important;padding:0 6px 9px}}
.v2 .mqped .crest{{filter:drop-shadow(0 3px 2px #000c)}}
.v2 .mqped:after{{content:'';position:absolute;left:0;right:0;bottom:0;height:7px;
  background:linear-gradient(var(--l1) 0 2px,var(--l2) 2px 5px,var(--l3) 5px);box-shadow:0 3px 3px #000a,inset 0 0 0 1px #0006}}
.v2 .mqped:before{{content:'';position:absolute;left:8px;right:8px;bottom:-4px;height:4px;background:var(--l3);box-shadow:0 2px 2px #0008}}
.ld-iron{{--l1:#a8977f;--l2:#6d5f50;--l3:#3b3128}}.ld-silver{{--l1:#ffffff;--l2:#aeb8c6;--l3:#5d6876}}.ld-gold{{--l1:#fff1a8;--l2:#e2a53a;--l3:#8a5a12}}
.v2.pt-wreath .mqped{{background:radial-gradient(ellipse at 50% 100%,#ffd36b55,#0000 65%)}}
 /* layout: emblem on its ledge at the far left, the name centered in the space that's left, trophies at the ends */
.mqx.v2{{justify-content:flex-start}}.v2 .mqmid{{display:contents}}
.v2 .mqped{{order:0;flex:none}}.v2 .mqshelf.l{{order:1;flex:0 0 auto}}.v2 .mqname{{position:relative;z-index:3;order:2;flex:1 1 0;min-width:0;display:flex;flex-direction:column;align-items:flex-start;padding-left:4px}}.v2 .mqn{{max-width:100%}}.mqunder{{align-self:stretch;display:flex;justify-content:center;align-items:center;gap:6px;margin-top:3px;min-height:28px;padding:2px 8px;background:linear-gradient(#050302,#140d06);border:2px solid #8a5a12;border-top-color:#5a3a0c;border-bottom-color:#c9922e;box-shadow:inset 0 3px 6px #000,inset 0 0 0 1px #000,0 2px 4px #000c}}.mqunder img{{width:22px;height:22px;filter:drop-shadow(0 1px 1px #000) drop-shadow(0 0 5px #ffd36b88)}}.v2 .mqshelf.r{{order:3;flex:0 0 auto}}
.v2.pt-rays .mqped:before{{content:none}}
 /* sparkles: pixel glints twinkling in turn (static and half-lit with reduced motion) */
.sparks{{position:absolute!important;inset:0;z-index:2!important;pointer-events:none}}
.sp{{position:absolute;width:16px;height:16px;margin:-8px;background:url(/mock/brand/marquee/v2/spark.png) center/contain no-repeat;
  filter:drop-shadow(0 0 4px #ffd36b);transform:scale(.15);opacity:0;animation:twinkle 3.6s ease-in-out infinite}}
.mqbig .sp{{width:20px;height:20px;margin:-10px}}
@keyframes twinkle{{0%,100%{{transform:scale(.15) rotate(0);opacity:0}}12%{{transform:scale(1) rotate(45deg);opacity:1}}24%{{transform:scale(.2) rotate(90deg);opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.sp{{opacity:.7;transform:scale(.6)}}}}
/* VIII up: gold filigree corner pieces with rubies, set over the frame's corners */
.corners{{position:absolute!important;inset:0;z-index:5!important;pointer-events:none}}
.corners b{{position:absolute;width:30px;height:30px;background:url(/mock/brand/marquee/v2/corner.png) center/contain no-repeat;filter:drop-shadow(0 1px 1px #000)}}
.mqbig .corners b{{width:40px;height:40px}}
.corners b:nth-child(1){{left:-3px;top:-3px}}.corners b:nth-child(2){{right:-3px;top:-3px;transform:scaleX(-1)}}
.corners b:nth-child(3){{left:-3px;bottom:-3px;transform:scaleY(-1)}}.corners b:nth-child(4){{right:-3px;bottom:-3px;transform:scale(-1)}}
.pxbadge{{font-family:'Jersey 10',sans-serif!important;font-size:16px!important;font-weight:400!important}}
</style></head><body><main>
<h1>Marquee v2</h1>
<p>Mockup: new pixel-art scenes and the Jersey 10 pixel nameplate. The name's fill follows Prestige like the emblem rim: iron, silver from IV, gold from VII.</p>
{rows}</main><script>document.querySelectorAll('.mqn').forEach(n=>{{let z=parseFloat(getComputedStyle(n).fontSize);while(n.scrollWidth>n.clientWidth&&z>18)n.style.fontSize=(z-=1)+'px'}})</script></body></html>"""
open(os.path.join(os.path.dirname(__file__), "v2.html"), "w", encoding="utf-8").write(html)
print("ok")
