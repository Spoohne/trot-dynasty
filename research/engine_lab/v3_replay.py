"""Test replay for race3: the game's HD-2D replay page, fed race3's exact recorded paths (lab only; the real replay
and the live site are untouched). Runs one half-mile and one mile race with the driver, picks a race worth watching
(the winner not off the rail post, at least one move logged), and writes a self-contained folder:
    v3/replay_test/index.html     the replay page, art paths made relative, the races embedded
    v3/replay_test/mock/...        the art files it loads (listed in FILES)
    python research/engine_lab/v3_replay.py"""
import json, os, random, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, ROOT)
import race3 as R, drive3 as DR

OUT = os.path.join(HERE, "v3", "replay_test")
MOCK = os.path.join(ROOT, "mockups")
FILES = ["race.js", "hud.css", "brand/logo_text.png", "brand/marquee/marquee.css",
         "pixel/angles/away12.png", "pixel/angles/front12.png", "pixel/angles/head12.png", "pixel/angles/rear12.png",
         "pixel/drive/drive12.png", "pixel/fe12_cycle.png", "pixel/gatecar_b.png", "pixel/wing_c.png", "pixel/panorama.png",
         "pixel/infield/fountain_jet.png", "pixel/infield/gazebo.png", "pixel/infield/grass.png", "pixel/infield/hedge_c.png",
         "pixel/infield/odds.png", "pixel/infield/tote.png", "pixel/infield/tree_a.png", "pixel/infield/tree_b.png",
         *[f"pixel/infield/sign{i}.png" for i in range(4)],
         "pixel/tack/wraps12.json", "pixel/tack/wraps12.png", "pixel/tack/wraps12_mask.png", "pixel/tack/hood12.png", "pixel/tack/hood12_mask.png",
         "pixel/top/cycle12_h.png", "pixel/top/track_tile.png",
         "pixel/venue/barn.png", "pixel/venue/club.png", "pixel/venue/lot.png", "pixel/venue/stand_grand.png",
         *[f"pixel/venue/car{k}.png" for k in range(8)],
         "pixel/wc/rig.png", "pixel/wc/scene.png", "pixel/wc/horse.png", "pixel/wc/blanket.png", "pixel/wc/circle.png"]
NAMES = ["Copper Lantern", "Midnight Ledger", "Northfield Rose", "Gilded Spoke", "Tally Ho Tess", "Ironwood Ace",
         "Paddock Rumor", "Silver Furlong", "Brass Bell", "Harbor Lights", "Quiet Thunder", "Velvet Hobble"]
COATS = ["bay", "bay", "bay", "brown", "brown", "black", "chestnut", "chestnut", "grey"]
TR = ("gate", "cruise", "kick", "manners", "grit")
HZ = 20


def race_story(track, seed):
    T = R.TRACKS[track]
    rng = random.Random(seed + (0 if track == "half" else 500))   # each track gets its own fields
    n = 8 if track == "half" else 10                       # the live game's usual field sizes
    f = [R.Horse(NAMES[(seed * 3 + k + (0 if track == "half" else 5)) % len(NAMES)], {t: rng.gauss(0, .4) for t in TR}, k + 1, T) for k in range(n)]
    drv = DR.Driver()
    o, rec = R.run(f, track, drv, seed=seed, dt=1 / 16)
    dt, fr = rec["dt"], rec["frames"]
    tt = lambda k: (k + 1) * dt
    lead_s = [max(x[0] for x in F) for F in fr]
    def first(cond):
        return next((k for k, s in enumerate(lead_s) if cond(s)), len(fr) - 1)
    q = [0.0] + [tt(first(lambda s, m=m: s >= m)) for m in (1320, 2640, 3960)] + [o[0].time]
    stretch = tt(first(lambda s: s >= T.last_turn_end))
    calls = [0.0, 14.0, q[1], q[2], q[3], stretch, o[0].time]
    win = o[0].time
    horses = []
    for i, h in enumerate(f):
        behind, lane = [], []
        for c in calls[:-1]:
            k = min(len(fr) - 1, max(0, int(round(c / dt)) - 1))
            behind.append(round((lead_s[k] - fr[k][i][0]) / R.LENGTH, 2))
            lane.append(round((fr[k][i][1] - R.RAIL_Y) / R.LANE, 2))
        behind.append(round((h.time - win) * R.FT_MILE / win / R.LENGTH, 2))
        lane.append(lane[-1])
        path = []
        for k in range(int((win + 14) * HZ) + 2):         # resampled to the replay's 20 Hz, held after the last frame
            x = k / HZ / dt - 1
            j = min(len(fr) - 1, max(0, int(x))); j2 = min(len(fr) - 1, j + 1); u = max(0.0, min(1.0, x - j))
            path += [round(fr[j][i][0] + (fr[j2][i][0] - fr[j][i][0]) * u, 2), round(fr[j][i][1] + (fr[j2][i][1] - fr[j][i][1]) * u + 1, 2)]
        base = getattr(h, "t_base", h.t)
        horses.append(dict(name=h.name, post=h.post, coat=COATS[sum(map(ord, h.name)) % len(COATS)], behind=behind, lane=lane,
                           trip=" · ".join(rec["trips"][h.name]), path=path, place=[x.name for x in o].index(h.name) + 1,
                           traits={k: round(base[k], 3) for k in TR}, form=rec.get("form", {}).get(h.name, 0.0)))
    nm = {h.name: h.name for h in f}
    caps = [[0, "They're away. The gate folds clear"]]
    for t, n, what, *_ in rec["events"]:
        if what == "pulled first-over":
            caps.append([t, f"{n} pulls first-over"])
        elif what.startswith("followed"):
            caps.append([t, f"{n} {what.replace('followed', 'follows').replace(chr(39) + 's cover', ' out')}"])
        elif what == "broke stride":
            caps.append([t, f"{n} breaks stride"])
        elif "pressed him" in what:
            caps.append([t, f"{n} won't give it up and presses for the lead"])
        elif "took the lead" in what:
            caps.append([t, f"{n} clears and takes the lead"])
        elif "took back" in what:
            caps.append([t, f"{n} takes back"])
    for label, t in (("Quarter", q[1]), ("Half", q[2]), ("Three-quarters", q[3])):
        k = min(len(fr) - 1, int(round(t / dt)) - 1)
        caps.append([t, f"{label} in {R_fmt(t)}, {f[max(range(len(f)), key=lambda i: fr[k][i][0])].name} on top"])
    caps.append([win, f"{o[0].name} wins it in {R_fmt(win)}"])
    caps.sort(key=lambda c: c[0])
    moves = sum(1 for e in rec["events"] if e[2] in ("pulled first-over",) or e[2].startswith("followed"))
    return dict(track=track, S=T.lap / 2 - 3.141592653589793 * T.R, R=T.R, run_in=T.arcs[0][0], final=round(win, 3),
                quarters=[round(x, 2) for x in q], calls=[round(x, 2) for x in calls], horses=horses, captions=caps,
                title=f"Engine test · {'half-mile' if track == 'half' else 'mile'} · {len(f)} starters · race {seed}"), o[0].post, moves


def R_fmt(t):
    m, s = int(t // 60), t % 60
    return f"{m}:{s:04.1f}" if m else f":{s:04.1f}"


def pick(track):
    for seed in range(1, 60):
        story, win_post, moves = race_story(track, seed)
        if win_post != 1 and moves >= 2:
            return story
    return race_story(track, 1)[0]


def build_page(races, links, out):
    """The live replay page (mockups/replay_hd2d.html as it is today) with lab races fed in: art copied to out/mock,
    paths made relative, the adapter and Field panel added. links: the race buttons' HTML. Returns the page text."""
    os.makedirs(out, exist_ok=True)
    live = open(os.path.join(MOCK, "replay_hd2d.html"), encoding="utf-8").read() + open(os.path.join(MOCK, "race.js"), encoding="utf-8").read()
    asked = set(re.findall(r"/mock/([A-Za-z0-9_./-]+?\.(?:png|json|css|js|jpg|webp))", live))   # every file the game asks for: the copy can't fall behind
    for rel in sorted(set(FILES) | asked):                # the art, at the same relative paths the page asks for
        src, dst = os.path.join(MOCK, rel), os.path.join(out, "mock", rel)
        if not os.path.isfile(src):
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    page = open(os.path.join(MOCK, "replay_hd2d.html"), encoding="utf-8").read()
    page = page.replace('"/mock/', '"mock/').replace("`/mock/", "`mock/").replace("'/mock/", "'mock/").replace('("/mock/', '("mock/')
    page = page.replace('src.slice("/mock/pixel/".length)', 'src.slice("mock/pixel/".length)').replace('src.replace("/mock/pixel/"', 'src.replace("mock/pixel/"')
    page = page.replace('const INJ = "__RACE_ID__"', 'const INJ = "v3test"')
    old = "const L = d / .2;"
    assert old in page, old
    page = page.replace(old, "const L = d;   // lab fix: the story's final margin is already in lengths (DECISIONS 200)")
    # the engine's own start positions (no cosmetic stagger), and a lake that fits a half-mile infield
    for old, new in (('const gateLag = h => Math.max(0, 1 - Math.max(0, h.d) / 220) * h.i * 1.6;', 'const gateLag = h => 0;   // race3 paths: exact positions'),
                     ('const LAKE = [1250, 620], LZ = -60;', 'const LAKE = [Math.min(1250, RACE.S + RACE.R * .9), Math.min(620, RACE.R * 1.25)], LZ = -Math.min(60, RACE.R * .15);'),
                     # a half-mile oval (R 165, the game's is 490): the infield camera would look through the final turn's
                     # hedge and the odds board, and the video board (set 255 ft out) would stand on the wire camera
                     ('const hh = straightAt(d) ? 5 : H;', 'const hh = straightAt(d) || (RACE.R < 300 && (p.z > 0 || p.x < 0)) ? 5 : H;'),
                     ('if (side < 0) b.rotation.y = Math.PI;\n', 'if (side < 0) b.rotation.y = Math.PI;\n    if (RACE.R < 300) sponsorBoards.push(b);\n'),
                     ('g.position.set(w.x - 78, 0, 255);', 'g.position.set(w.x - 78, 0, Math.min(255, RACE.R - 130));')):
        assert old in page, old
        page = page.replace(old, new)
    # the races, and the adapter: set the oval to the raced track's shape and hand over the recorded paths
    adapter = """<script>
window.V3 = %s;
(function () {
  const m = /^#(half|mile)(\\d)?$/.exec(location.hash) || [0, "half", "1"];
  RACE.load = async (id, myName) => {
    const s = V3[m[1]][Math.min(V3[m[1]].length, +(m[2] || 1)) - 1];
    RACE.S = s.S; RACE.R = s.R; RACE.L = 2 * s.S + 2 * Math.PI * s.R; RACE.SF = s.S - s.run_in;   // the finish: run_in before turn 1
    RACE.title = s.title; RACE.venue = "Engine lab"; RACE.tlook = null; RACE.REC = null;
    RACE.TT = s.quarters; RACE.DD = [0, 1320, 2640, 3960, 5280]; RACE.CT = s.calls; RACE.FIN = s.final; RACE.END = s.final + 12;
    RACE.H = s.horses.map(h => Object.assign([h.name, "#5a3420", h.behind, h.lane], { coat: h.coat, odds: "", owner: "", stable: "", player: false,
      silks: null, wraps: "", mask: "", driver: "", emblem: "", marquee: "", stamina: 0, early: 0 }));
    RACE.PICK = ""; RACE.HERO = -1; RACE.MATINEE = false; RACE.PASSING = false; RACE.DIVER = -1;
    RACE.real = true; RACE.CAPS = s.captions; RACE.ME = 0;
    RACE.rebuild();
    RACE.simulate = () => {                       // race3 already ran the race: these are its paths, at 20 Hz
      RACE.paths = s.horses.map(h => Float32Array.from(h.path)); RACE.pathN = s.horses[0].path.length / 2;
    };
    return true;
  };
  addEventListener("hashchange", () => location.reload());
})();
</script>
<div id="v3pick" style="position:fixed;z-index:50;top:calc(8px + env(safe-area-inset-top,0px));right:calc(8px + env(safe-area-inset-right,0px));display:flex;flex-wrap:wrap;justify-content:flex-end;max-width:60vw;gap:4px;font:700 12px 'Barlow Condensed',sans-serif;letter-spacing:.08em;text-transform:uppercase">
%s<a href="#" onclick="document.getElementById('v3field').classList.toggle('on');return false" style="background:#e8a33a;color:#2a1a03;border:1px solid #2b3a55;padding:6px 8px;border-radius:4px;text-decoration:none">Field</a></div>
<div id="v3field"></div>
<style>
#v3field{display:none;position:fixed;z-index:60;inset:auto calc(8px + env(safe-area-inset-right,0px)) calc(8px + env(safe-area-inset-bottom,0px)) auto;top:calc(104px + env(safe-area-inset-top,0px));width:min(380px,calc(100vw - 16px));overflow:auto;background:#0b1430f2;border:2px solid #2b3a55;border-top:3px solid #e8a33a;padding:8px 10px;font:600 12px 'Barlow Semi Condensed',sans-serif;color:#e6e8ec}
#v3field.on{display:block}
#v3field h4{margin:2px 0 6px;font:800 13px 'Barlow Condensed',sans-serif;letter-spacing:.08em;text-transform:uppercase;color:#ffb347}
#v3field .fc{border:1px solid #2b3a55;background:#111a2b;padding:6px 8px;margin-bottom:6px}
#v3field .fh{display:flex;align-items:center;gap:6px;margin-bottom:4px}
#v3field .fh b.pp{display:inline-grid;place-items:center;width:20px;height:20px;font-size:12px;border:1px solid #05070d}
#v3field .fh .nm{font:800 14px 'Barlow Condensed',sans-serif}
#v3field .fh .fin{margin-left:auto;color:#a4acb9}
#v3field .fh .fin.w{color:#3fb96b}
#v3field .br{display:grid;grid-template-columns:54px 1fr 22px;align-items:center;gap:6px;margin:2px 0}
#v3field .br span{color:#a4acb9}
#v3field .br.hid span{color:#6f7886}
#v3field .st{height:8px;position:relative;background:#1b2539}
#v3field .st i{display:block;height:8px}
#v3field .st:after{content:'';position:absolute;inset:0;background:repeating-linear-gradient(90deg,transparent 0 calc(10%% - 2px),#000 calc(10%% - 2px) 10%%)}
#v3field .br b{text-align:right;text-shadow:1px 1px 0 #000}
#v3field .nt{color:#a4acb9;font-weight:400;margin-top:3px}
</style>
<script>
(function () {
  const hh = location.hash.slice(1) || "half1", tk = hh.startsWith("mile") ? "mile" : "half", ix = +((hh.match(/[0-9]+/) || ["1"])[0]);
  const s = V3[tk][Math.min(V3[tk].length, ix) - 1];
  // the game's bars from the lab's hidden traits: 5 pips for an average horse, 2 pips per spread (0.4) of the trait
  const pips = v => Math.max(1, Math.min(10, 5 + 2 * v / 0.4));
  const color = n => n <= 3 ? "#5b6270" : n <= 6 ? "#d4c13a" : n <= 8 ? "#3fb96b" : "linear-gradient(90deg,#8b5cf6,#38bdf8 70%%,#67e8f9)";
  const bar = (label, v, hid) => { const p = pips(v), n = Math.round(p);
    return `<div class="br${hid ? " hid" : ""}"><span>${label}</span><div class="st"><i style="width:${p * 10}%%;background:${color(n)}"></i></div><b>${n}</b></div>`; };
  const ord = k => ["1st", "2nd", "3rd"][k - 1] || k + "th";
  const pad = p => `<b class="pp" style="background:${RACE.PAD[p - 1]};color:${RACE.DARK.includes(p) ? "#111" : "#fff"}">${p}</b>`;
  const f = n => (n > 0 ? "+" : "") + n.toFixed(2);
  document.getElementById("v3field").innerHTML = `<h4>The field · ${s.title.split(" · ").slice(1).join(" · ")}</h4><div class="nt" style="margin:-2px 0 6px">Bars as the game would show them. Race-day form is how the horse is going today (added to Speed, Stam and Finish for this race). Grit is hidden in the game.</div>` + [...s.horses].sort((a, b) => a.post - b.post).map(h =>
    `<div class="fc"><div class="fh">${pad(h.post)}<span class="nm">${h.name}</span><span class="fin${h.place === 1 ? " w" : ""}">${ord(h.place)}</span></div>`
    + bar("Speed", h.traits.gate) + bar("Stam", h.traits.cruise) + bar("Finish", h.traits.kick) + bar("Manners", h.traits.manners)
    + bar("Grit", h.traits.grit, true)
    + `<div class="nt">Race-day form ${f(h.form)}</div></div>`).join("");
})();
</script>
""" % (json.dumps(races, separators=(",", ":")), links)
    page = page.replace('<script src="mock/race.js"></script>', '<script src="mock/race.js"></script>\n' + adapter, 1)
    # the artifact skeleton supplies doctype, html, head and body
    page = re.sub(r"<!doctype html>\s*", "", page, flags=re.I)
    page = re.sub(r"</?html[^>]*>|</?head>|</?body[^>]*>", "", page)
    page = re.sub(r"<meta name=\"?viewport\"?[^>]*>", "", page)
    page = re.sub(r"<title>.*?</title>", "", page, flags=re.S)
    return '<title>Engine Test Replay</title>\n' + page


if __name__ == "__main__":
    N_RACES = 6                                          # the next races as they come: no picking, an honest sample to judge
    races = {t: [race_story(t, seed)[0] for seed in range(1, N_RACES + 1)] for t in ("half", "mile")}
    page = build_page(races, "".join(
        f'<a href="#{t}{k}" style="background:#111a2b;color:#e8a33a;border:1px solid #2b3a55;padding:6px 8px;border-radius:4px;text-decoration:none">{"Half" if t == "half" else "Mile"} {k}</a>'
        for t in ("half", "mile") for k in range(1, N_RACES + 1)), OUT)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)
    for t, ss in races.items():
        for s in ss:
            w = min(s["horses"], key=lambda h: h["behind"][-1])
            print(s["title"], "| won by", w["name"], "from post", w["post"], "in", s["final"], "|", w["trip"])
    print("page", round(os.path.getsize(os.path.join(OUT, "index.html")) / 1e6, 2), "MB")
