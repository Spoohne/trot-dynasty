"""Test replay for the outcome-first engine (DECISIONS 212): the outcome model decides each race, the story system
draws it, and the HD-2D replay page plays it the way the live game plays a story. Reuses the lab page built by
v3_replay.py (art, race buttons, Field panel, margin fix) with the race data and the loader swapped.
    python v4_replay.py      writes v4/replay/index.html (+ mock/ art)"""
import json, os, re, shutil
import numpy as np
import v4_outcome as V, v4_story as ST, v4_choreo as C
from v3_replay import NAMES, COATS

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "v3", "replay_test")
OUT = os.path.join(HERE, "v4", "replay")
BASE = {"half": 115.9, "mile": 113.4}          # winning time of an average class field (displayed clocks map onto these)
TR = ("gate", "cruise", "kick", "manners", "grit")
N_RACES = 6


def one(track, k, p):
    n = V.N_STARTERS[track]
    rng = np.random.default_rng(4000 + k + (0 if track == "half" else 500))
    traits = rng.normal(0, V.SD, (n, 5))
    D = V.draws(1, n, 9000 + k + (0 if track == "half" else 500))
    D["traits"] = traits[None].copy()
    P, role, rank = (x[0] for x in V.race(p, D, track))
    form = D["form"][0] * p["s_form"]
    p_break = 0.005 * np.exp(-2.88 * traits[:, 3])
    broke = D["brk"][0] < p_break
    order = list(np.argsort(-P))
    final = BASE[track] - 1.2 * (P[order[0]] - np.mean(P))       # a stronger winner goes a little faster
    names = [NAMES[(k * 3 + i + (0 if track == "half" else 5)) % len(NAMES)] for i in range(n)]
    horses = [dict(name=names[i], post=i + 1, role=int(role[i]), start=int(rank[i]), broke=bool(broke[i]),
                   margin=float((P[order[0]] - P[i]) * p["s_margin"]), coat=COATS[sum(map(ord, names[i])) % len(COATS)],
                   traits={t: round(float(traits[i, j]), 3) for j, t in enumerate(TR)}, form=round(float(form[i]), 3))
              for i in map(int, order)]
    s = ST.build(horses, track, final, passing=True)
    s["title"] = f"Engine test · {'half-mile' if track == 'half' else 'mile'} · {n} starters · race {k}"
    return s


LOADER = """  RACE.load = async (id, myName) => {
    const s = V3[tk][Math.min(V3[tk].length, ix) - 1];
    const horses = [...s.horses].sort((a, b) => a.post - b.post);
    RACE.title = s.title; RACE.venue = "Engine lab"; RACE.tlook = null; RACE.REC = null;
    RACE.TT = s.quarters; RACE.DD = [0, 1320, 2640, 3960, 5280]; RACE.CT = s.calls; RACE.FIN = s.final; RACE.END = s.final + 12;
    horses.forEach(h => { h.lane[0] = h.post - 1; h.behind[0] = 0; });
    RACE.H = horses.map(h => Object.assign([h.name, "#5a3420", h.behind, h.lane], { stamina: 0, early: 0, coat: h.coat, odds: "", owner: "",
      stable: "", player: false, silks: null, wraps: "", mask: "", driver: "", emblem: "", marquee: "" }));
    RACE.PICK = ""; RACE.HERO = -1; RACE.MATINEE = false;
    RACE.PASSING = !!s.passing; RACE.DIVER = horses.findIndex(h => (h.trip || "").includes("passing lane"));
    RACE.real = true; RACE.CAPS = s.captions; RACE.ME = 0;
    RACE.rebuild(); return true;
  };
"""

if __name__ == "__main__":
    races = {}
    for track in ("half", "mile"):
        p = dict(V.FIXED, **json.load(open(os.path.join(V.OUT, f"fit_{track}.json")))["params"])
        races[track] = [one(track, k, p) for k in range(1, N_RACES + 1)]
    page = open(os.path.join(SRC, "index.html"), encoding="utf-8").read()
    page, nd = re.subn(r"window\.V3 = \{.*?\};\n", lambda m: "window.V3 = " + json.dumps(races, separators=(",", ":")) + ";\n", page, count=1, flags=re.S)
    assert nd == 1
    a = page.index("  RACE.load = async (id, myName) => {")
    b = page.index("    return true;\n  };\n", a) + len("    return true;\n  };\n")
    page = page[:a] + "  const hh = location.hash.slice(1) || \"half1\", tk = hh.startsWith(\"mile\") ? \"mile\" : \"half\", ix = +((hh.match(/[0-9]+/) || [\"1\"])[0]);\n" + LOADER + page[b:]
    page = page.replace('<title>Engine Test Replay</title>', '<title>Outcome Engine Replay</title>')
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)
    if not os.path.exists(os.path.join(OUT, "mock")):
        shutil.copytree(os.path.join(SRC, "mock"), os.path.join(OUT, "mock"))
    for t, ss in races.items():
        for s in ss:
            w = s["horses"][0]
            print(s["title"], "| won by", w["name"], "from post", w["post"], f"({w['trip']})", "in", s["final"],
                  "| 2nd by", round(s["horses"][1]["behind"][6], 2), "L | trips", [h["trip"].split(",")[0] for h in s["horses"][:3]])
