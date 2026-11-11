"""Does a sim race look like a real one? Real Woodbine Mohawk charts (Standardbred Canada's public results, saved in
charts/) against gallop.run on the same measures, side by side, pass or fail. Run it after every sim change: a change
goes in only if nothing that passed before fails now.

    python research/engine_lab/realism.py [races]          default 400 sim races
    python research/engine_lab/realism.py --charts         the real numbers only

A chart call is "position/lengths behind the leader" (the leader's figure is its margin over second), @ = racing one wide, @@ = two out; x = a break. Calls: 1/4, 1/2, 3/4, stretch (about an eighth out), finish.
"""
import glob
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

CALL = re.compile(r"^[A-Za-z]?(\d+)([@xX]*)[A-Z]*/([0-9]*(?:NS|HD|NK|H|Q|T|DIS)?)$")
FRAC = {"": 0, "H": .5, "Q": .25, "T": .75, "NS": .05, "HD": .1, "NK": .2}
CALLS = ["1/4", "1/2", "3/4", "str", "fin"]


def lengths(s):
    if s.endswith("DIS"):
        return 25.0
    m = re.match(r"(\d*)(NS|HD|NK|H|Q|T)?$", s)
    return (int(m.group(1)) if m.group(1) else 0) + FRAC[m.group(2) or ""]


def parse(path):
    """Every one-mile race in a night's chart: a list of horses, each {pp, pos[5], behind[5], wide[5], broke}."""
    races, cur, mile = [], None, False
    for line in open(path, encoding="utf8"):
        if re.match(r"\s*1 MILE,", line):
            mile = True
        if line.startswith("Horse ") and "1/4" in line:
            cur = [] if mile else None
            mile = False
            continue
        if cur is None:
            continue
        toks = line.split()
        idx = [i for i, t in enumerate(toks) if CALL.match(t)]
        if len(idx) < 5 or not toks[idx[0] - 1].isdigit():
            if line.startswith("Time:"):
                if len(cur) >= 5:
                    races.append(cur)
                cur = None
            continue
        calls = [CALL.match(toks[i]) for i in idx[:5]]
        cur.append({"pp": int(toks[idx[0] - 1]), "pos": [int(c.group(1)) for c in calls],
                    "behind": [0.0 if int(c.group(1)) == 1 else lengths(c.group(3)) for c in calls],
                    "wide": [c.group(2).count("@") for c in calls],
                    "broke": any("x" in toks[i].lower() for i in idx[:5])})
    return races


def measures(races):
    """The numbers both sides are judged on, from races as lists of horses (chart form)."""
    out = {}
    n = len(races)
    for k, c in enumerate(CALLS[:3]):
        out[f"off the rail at {c} (% of field)"] = 100 * np.mean([np.mean([h["wide"][k] >= 1 for h in r]) for r in races])
        out[f"two out or wider at {c} (%)"] = 100 * np.mean([np.mean([h["wide"][k] >= 2 for h in r]) for r in races])
    for k, c in enumerate(CALLS[:4]):
        out[f"leader to last at {c} (lengths)"] = np.median([max(h["behind"][k] for h in r) for r in races])
    win = [next(h for h in r if h["pos"][4] == 1) for r in races]
    out["winner led at 1/2 (%)"] = 100 * np.mean([w["pos"][1] == 1 for w in win])
    out["winner 2nd-3rd at 1/2 (%)"] = 100 * np.mean([w["pos"][1] in (2, 3) for w in win])
    out["winner 4th or worse at 1/2 (%)"] = 100 * np.mean([w["pos"][1] >= 4 for w in win])
    out["winner was outside at 1/2 or 3/4 (%)"] = 100 * np.mean([max(w["wide"][1:3]) >= 1 for w in win])
    out["1/4 leader wins (%)"] = 100 * np.mean([next(h for h in r if h["pos"][0] == 1)["pos"][4] == 1 for r in races])
    out["leader changes 1/4 to finish"] = np.mean([sum(a != b for a, b in zip(lead[:-1], lead[1:]))
                                                  for lead in ([next(i for i, h in enumerate(r) if h["pos"][k] == 1) for k in range(5)] for r in races)])
    marg = [sorted(h["behind"][4] for h in r)[1] for r in races]
    out["winning margin (median lengths)"] = np.median(marg)
    out["won by under a length (%)"] = 100 * np.mean([m < 1 for m in marg])
    out["last beaten (median lengths)"] = np.median([max(h["behind"][4] for h in r) for r in races])
    for p in (1, 2, 3, 5, 8):
        out[f"post {p} wins (%)"] = 100 * np.mean([any(h["pp"] == p and h["pos"][4] == 1 for h in r) for r in races if any(h["pp"] == p for h in r)])
    out["races"] = n
    return out


def sim_races(R, seed=5):
    """R ten-horse sim miles, read at the chart's calls: lane from the sim's lateral position, lengths from progress.
    Fields are real cards from the 100-season world (classed like a real night, posts as drawn), not random horses."""
    import gallop
    import sqlite3
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "encyclopedia"))
    from gallop100 import AGE_K
    db = sqlite3.connect(f"file:{os.path.join(os.path.dirname(HERE), 'encyclopedia', 'gallop100.db')}?mode=ro", uri=True)
    rng = np.random.default_rng(seed)
    keys = db.execute("SELECT season, week, race FROM races ORDER BY RANDOM() LIMIT ?", (R,)).fetchall()
    cols = ", ".join("h." + s for s in gallop.STATS)
    st = np.array([[[*row[:-1]] for row in db.execute(f"SELECT {cols}, s.age FROM starts s JOIN horses h ON h.id = s.id WHERE s.season=? AND s.week=? AND s.race=? ORDER BY s.post", k)]
                   for k in keys], float)
    ages = np.array([[row[0] for row in db.execute("SELECT age FROM starts WHERE season=? AND week=? AND race=? ORDER BY post", k)] for k in keys])
    st = st * np.vectorize(AGE_K.get)(ages)[..., None]
    place, times, _, f = gallop.run(st, rng=rng, record=True)
    prog, lane = f[..., 0], np.rint(f[..., 1] / gallop.CFG["lane_m"])
    L = 2.44
    races = []
    for r in range(R):
        lead = prog[:, r].max(1)
        ks = [int(np.argmax(lead >= m)) for m in (gallop.MILE / 4, gallop.MILE / 2, gallop.MILE * 3 / 4, gallop.MILE - 201)]
        hs = [{"pp": i + 1, "pos": [], "behind": [], "wide": [], "broke": False} for i in range(10)]
        for k in ks:
            order = np.argsort(-prog[k, r])
            for p, i in enumerate(order):
                hs[i]["pos"].append(p + 1); hs[i]["behind"].append(float(lead[k] - prog[k, r, i]) / L)
                hs[i]["wide"].append(int(lane[k, r, i]))   # a chart marks every horse racing outside, covered or not (39 % of the field at the 3/4 is the whole outer flow)
        t = times[r]
        for i in range(10):
            hs[i]["pos"].append(int(place[r, i])); hs[i]["behind"].append(float((t[i] - t.min()) / 0.2))   # at the wire a chart's length is a fifth of a second, off the teletimer; hs[i]["wide"].append(0)
        races.append(hs)
    return races


def main():
    real = [r for p in sorted(glob.glob(os.path.join(HERE, "charts", "*.txt"))) for r in parse(p)]
    want = measures(real)
    if "--charts" in sys.argv:
        for k, v in want.items():
            print(f"{k:<40}{v:7.1f}")
        return
    R = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    got = measures(sim_races(R))
    # the band: within a quarter of the real value, or 5 points / a length when the value is small
    fails = 0
    print(f"{'measure':<40}{'real':>7}{'sim':>7}   ")
    for k, v in want.items():
        if k == "races":
            print(f"{k:<40}{v:7.0f}{got[k]:7.0f}")
            continue
        tol = max(0.25 * abs(v), 5 if "%" in k else 1.0)
        ok = abs(got[k] - v) <= tol
        fails += not ok
        print(f"{k:<40}{v:7.1f}{got[k]:7.1f}   {'pass' if ok else 'FAIL'}")
    print(f"{fails} of {len(want) - 1} measures outside the real range")


if __name__ == "__main__":
    main()
