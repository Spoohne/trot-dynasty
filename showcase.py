"""Build a one-off showcase race for the replay: a Grand Final for 3-year-olds, the ten best of a whole
crop, run through the real sim and story builder. Also writes the race program with a morning line.

    python showcase.py                      the original final (seed 3) -> 3yo-grand-final
    python showcase.py <seed> <race-id>     a fresh crop -> <race-id>

Writes mockups/races/<id>.json (served at /race/<id>.json, plays at /replay/<id>) and
mockups/races/<id>-program.html (served at /mock/races/<id>-program.html).
"""
import html, json, os, random, sys
import sim, story

RID = "3yo-grand-final"
NAMES = ["Thunder Ridge", "Midnight Express", "Royal Command", "Steel Resolve", "Bold Horizon",
         "Iron Duchess", "Captain Velocity", "Silver Tempest", "Northern Majesty", "Wildfire Hanover"]
PURSE = 1_000_000


def field_for(seed, crop=3000, names=NAMES):
    """The final is filled the way a real one is: the ten best of a crop of 3-year-olds by rating,
    posts drawn at random."""
    sim.rng.seed(seed)
    foals = [sim.founder() for _ in range(crop)]
    for h in foals:
        h.age = 3
    field = sorted(foals, key=lambda h: -h.race_score(3))[:len(names)]
    sim.rng.shuffle(field)                                            # the post draw
    for post, (h, name) in enumerate(zip(field, names), 1):
        h.post, h.name = post, name
    return field


def morning_line(field, runs=4000, takeout=0.16):
    """Each horse's chance from running this exact field many times, turned into the usual tote odds
    with the track's take out. The real race is run afterwards from its own seed, so this can't peek."""
    state = sim.rng.getstate()
    wins = {h.id: 0 for h in field}
    for _ in range(runs):
        wins[sim.race(field)[0].id] += 1
    sim.rng.setstate(state)
    LADDER = [(1, 5), (2, 5), (1, 2), (3, 5), (4, 5), (1, 1), (6, 5), (7, 5), (3, 2), (8, 5), (9, 5), (2, 1),
              (5, 2), (3, 1), (7, 2), (4, 1), (9, 2), (5, 1), (6, 1), (8, 1), (10, 1), (12, 1), (15, 1), (20, 1),
              (30, 1), (50, 1), (99, 1)]
    out = {}
    for h in field:
        p = max(wins[h.id] / runs, 0.005)
        fair = (1 - takeout) / p - 1                                   # what a $1 win bet would pay in profit
        a, b = min(LADDER, key=lambda r: abs(r[0] / r[1] - fair))
        out[h.id] = (p, f"{a}-{b}")
    return out


def build(seed=3, field=None):
    field = field or field_for(seed)
    order = sim.race(field, "mile")
    s = story.build(order, "mile", random.Random(seed))
    s.update(name="Grand Final · 3YO", purse=PURSE)
    return s


def program_html(rid, field, line):
    """The race program, dressed like the replay: night-panorama masthead, pixel type, amber LED odds, and
    each horse drawn in its own coat and silks from the replay's SpriteCook stride, pacing in place."""
    st_txt = {"front": "WANTS THE LEAD", "stalk": "SITS JUST OFF IT", "mid": "MID-PACK, MOVES LATE", "late": "DROPS OUT, CLOSES"}
    def bar(v):                                                     # -3..+7 onto 10 pixel cells
        n = max(0, min(10, round(v + 3)))
        cls = "hi" if v >= 3 else "lo" if v < 0 else "md"
        return f"<span class='bar {cls}'>" + "".join(f"<i class={'f' if k < n else 'e'}></i>" for k in range(10)) + f"</span><b>{v:+.1f}</b>"
    entries, data = [], []
    for h in sorted(field, key=lambda h: h.post):
        c, st = h.current("mile"), sim.style_of(h)
        p, odds = line[h.id]
        data.append({"name": h.name, "coat": h.coat, "post": h.post})
        arrows = "".join(f"<i class={'on' if k == st else 'off'}></i>" for k in ("front", "stalk", "mid", "late"))
        entries.append(f"""<section class=entry>
 <div class=pp data-p={h.post}>{h.post}</div>
 <canvas class=horse id=h{h.post} width=208 height=101></canvas>
 <div class=info>
  <h2>{html.escape(h.name)}</h2>
  <div class=meta>{'COLT' if h.sex == 'm' else 'FILLY'} · {h.coat.upper()} · AGE 3 · RTG {h.race_score(3):.1f}</div>
  <div class=prime><span>PRIME</span><span class=arr>{arrows}</span><em>{st_txt[st]}</em></div>
  <div class=stats>
   <label>EARLY</label>{bar(c['early_speed'])}<label>LATE</label>{bar(c['late_speed'])}
   <label>STAMINA</label>{bar(c['stamina'])}<label>GAIT</label>{bar(c['gait'])}
  </div>
 </div>
 <div class=led><div class=ml>{odds}</div><div class=pc>{p:.0%} WIN</div></div>
</section>""")
    fav = max(field, key=lambda h: line[h.id][0])
    css = """
:root{--bg:#05070d;--panel:#0d1220;--edge:#26324a;--ink:#e8ecf4;--dim:#8b96ad;--amber:#ffb347;--amberD:#a86a1c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:'VT323',monospace;font-size:20px}
.wrap{max-width:900px;margin:0 auto;padding:14px}
.mast{position:relative;height:220px;overflow:hidden;border:4px solid var(--edge);box-shadow:0 0 0 4px #000;
  background:#0b1430 url(/mock/pixel/panorama.png) 38% bottom/auto 100% repeat-x;image-rendering:pixelated}
.mast:after{content:'';position:absolute;inset:0;background:linear-gradient(rgba(5,7,13,.15),rgba(5,7,13,.25) 40%,rgba(5,7,13,.95))}
.mast .t{position:absolute;left:18px;right:18px;bottom:14px;z-index:1}
.k{font-family:'Press Start 2P';font-size:10px;color:var(--amber);letter-spacing:2px}
h1{font-family:'Press Start 2P';font-size:22px;margin:10px 0 8px;line-height:1.45;text-shadow:3px 3px 0 #000}
.sub{color:var(--dim);font-size:22px}
.purse{position:absolute;right:18px;top:16px;z-index:1;text-align:right;background:rgba(5,7,13,.7);padding:6px 10px;border:3px solid #000}
.purse b{display:block;font-size:46px;color:var(--amber);text-shadow:0 0 8px rgba(255,179,71,.7),3px 3px 0 #000;line-height:1;font-weight:400}
.note{color:var(--dim);margin:16px 4px;font-size:19px;line-height:1.25}.note b{color:var(--ink);font-weight:400}
.entry{display:grid;grid-template-columns:56px 156px 1fr 110px;align-items:center;margin-bottom:14px;border:4px solid var(--edge);
  box-shadow:0 0 0 4px #000;background:linear-gradient(90deg,#0d1220,#121c30)}
.pp{align-self:stretch;display:flex;align-items:center;justify-content:center;font-family:'Press Start 2P';font-size:20px;border-right:4px solid #000}
.horse{width:156px;image-rendering:pixelated;margin:6px 0 2px}
.info{padding:8px 12px;min-width:0}
h2{font-family:'Press Start 2P';font-size:13px;margin:0 0 6px;line-height:1.4;text-shadow:2px 2px 0 #000}
.meta{color:var(--dim);font-size:18px}
.prime{display:flex;align-items:center;gap:8px;margin:4px 0 6px;font-size:17px;color:var(--dim);flex-wrap:wrap}
.arr{display:inline-flex;gap:3px}.arr i{width:17px;height:12px;background:#1d2738;clip-path:polygon(0 0,62% 0,100% 50%,62% 100%,0 100%,38% 50%)}
.arr i.on{background:var(--amber)}.prime em{font-style:normal;color:var(--ink)}
.stats{display:grid;grid-template-columns:auto auto 1fr auto auto 1fr;gap:3px 8px;align-items:center;font-size:17px}
.stats label{color:var(--dim)}.stats b{font-weight:400;min-width:36px}
.bar{display:inline-flex;gap:2px}.bar i{width:7px;height:11px;background:#1a2232}
.bar.hi i.f{background:#58d36a}.bar.md i.f{background:#5aa8ff}.bar.lo i.f{background:#e05a4f}
.led{align-self:stretch;display:flex;flex-direction:column;align-items:center;justify-content:center;border-left:4px solid #000;
  background:#0a0702 radial-gradient(rgba(255,179,71,.09) 1px,transparent 1.6px) 0 0/4px 4px}
.ml{font-size:48px;line-height:1;color:var(--amber);text-shadow:0 0 6px rgba(255,179,71,.85),0 0 16px rgba(255,140,0,.35)}
.pc{font-size:16px;color:var(--amberD)}
.foot{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:18px 4px 30px;color:var(--dim)}
.btn{font-family:'Press Start 2P';font-size:11px;background:var(--amber);color:#2a1a03;text-decoration:none;padding:14px 16px;border:4px solid #000;box-shadow:4px 4px 0 #000}
@media (max-width:640px){.entry{grid-template-columns:44px 1fr 84px}.horse{display:none}.ml{font-size:36px}.stats{grid-template-columns:auto auto 1fr}h1{font-size:15px}.purse b{font-size:34px}}
"""
    js = """
const COAT = { brown: [.62, .5, .45], black: [.26, .24, .24], chestnut: [1.25, .82, .55] };
RACE.H = FIELD.map(f => [f.name]); RACE.silks();
const img = new Image(); img.src = "/mock/pixel/fe12_cycle.png";
img.onload = () => {
  const sheets = FIELD.map((f, i) => {
    const c = document.createElement("canvas"); c.width = img.width; c.height = img.height; const g = c.getContext("2d"); g.drawImage(img, 0, 0);
    const d = g.getImageData(0, 0, c.width, c.height), p = d.data, silk = [1, 3, 5].map(k => parseInt(RACE.SILK[i].slice(k, k + 2), 16)), k = COAT[f.coat];
    for (let j = 0; j < p.length; j += 4) {
      if (!p[j + 3]) continue; const r = p[j], gg = p[j + 1], b = p[j + 2];
      if (b > r + 40 && b > gg + 20) { const l = Math.min(1.3, (r + gg + b) / 3 / 70); p[j] = silk[0] * l; p[j + 1] = silk[1] * l; p[j + 2] = silk[2] * l; continue; }
      const warm = r > gg + 12 && r > b + 25;
      if (f.coat === "grey") { const v = (r + gg + b) / 3; if (warm) { const w = Math.min(235, 70 + v * 1.25); p[j] = w; p[j + 1] = w; p[j + 2] = w + 6; } else if (v < 60 && Math.abs(r - b) < 18) { const w = 40 + v * 1.4; p[j] = w; p[j + 1] = w; p[j + 2] = w + 4; } }
      else if (k && warm) { p[j] = Math.min(255, r * k[0]); p[j + 1] = Math.min(255, gg * k[1]); p[j + 2] = Math.min(255, b * k[2]); }
    }
    g.putImageData(d, 0, 0);
    const dark = RACE.DARK.includes(i + 1);
    g.font = "bold 16px monospace"; g.textAlign = "center"; g.textBaseline = "middle";
    for (let fr = 0; fr < 12; fr++) { g.fillStyle = RACE.PAD[i]; g.fillRect(fr * 208 + 105, 25, 18, 21); g.fillStyle = dark ? "#111" : "#fff"; g.fillText(i + 1, fr * 208 + 114, 36); }
    const pp = document.querySelector(`.pp[data-p="${f.post}"]`); pp.style.background = RACE.PAD[i]; pp.style.color = dark ? "#111" : "#fff";
    return c;
  });
  const t0 = performance.now();
  (function tick(now) {
    FIELD.forEach((f, i) => { const g = document.getElementById("h" + f.post).getContext("2d"); g.imageSmoothingEnabled = false; g.clearRect(0, 0, 208, 101);
      g.drawImage(sheets[i], (Math.floor((now - t0) / 1000 * 18 + i * 3) % 12) * 208, 0, 208, 101, 0, 0, 208, 101); });
    requestAnimationFrame(tick);
  })(t0);
};
"""
    return ("<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>Grand Final Program</title>"
            "<link href='https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap' rel=stylesheet>"
            f"<style>{css}</style></head><body><div class=wrap>"
            f"<header class=mast><div class=purse><span class=k>PURSE</span><b>${PURSE:,}</b></div>"
            "<div class=t><div class=k>RACE 10 · STAKES FINAL · ONE MILE PACE</div><h1>GRAND FINAL<br>FOR 3-YEAR-OLDS</h1>"
            "<div class=sub>The ten best of the crop</div></div></header>"
            "<p class=note>Morning line from 4,000 simulated runnings of this field. Bars run from below breed average to the top of the crop. "
            f"Favorite: <b>{html.escape(fav.name)}</b> at {line[fav.id][1]}.</p>"
            + "".join(entries) +
            f"<div class=foot><span>ODDS ARE A PROJECTION, NOT A RESULT</span><a class=btn href='/replay/{rid}'>WATCH THE RACE ▶</a></div></div>"
            f"<script src='/mock/race.js'></script><script>const FIELD = {json.dumps(data)};{js}</script></body></html>")


if __name__ == "__main__":
    seed, rid = (int(sys.argv[1]), sys.argv[2]) if len(sys.argv) > 2 else (3, RID)
    field = field_for(seed)
    line = morning_line(field)
    s = build(seed, field)
    assert [h["place"] for h in s["horses"]] == list(range(1, len(NAMES) + 1)), "story keeps the finish order"
    os.makedirs(os.path.join("mockups", "races"), exist_ok=True)
    with open(os.path.join("mockups", "races", rid + ".json"), "w") as f:
        json.dump(s, f)
    with open(os.path.join("mockups", "races", rid + "-program.html"), "w", encoding="utf-8") as f:
        f.write(program_html(rid, field, line))
    byname = {h.name: h for h in field}
    print(f"{rid}: program at /mock/races/{rid}-program.html, race at /replay/{rid}")
    for h in s["horses"]:
        print(f"  {h['place']:2} {h['name']:<18} post {h['post']:2}  ML {line[byname[h['name']].id][1]:>5}  {story._mt(h['time'])}  {h['trip']}")
