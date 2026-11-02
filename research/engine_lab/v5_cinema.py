"""Replay library (DECISIONS 225-226): physics races judged only on how they look.
A candidate is a race3/drive3 race with drivers scripted toward a story. Its cinematic score checks that the story
happened and that it looks right: a compact field, no bursts, a margin that fits the story, a clean safety audit.
    python v5_cinema.py probe <races> ['<json overrides>']     how today's physics looks (no story)"""
import json, os, random, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import race3 as R, drive3 as DR, v3_part1 as P1

DT = 1 / 16


def apply(over):
    """Settings for the library's physics (looks only; the outcome model is untouched): race3 P, drive3 D or a race3 constant."""
    for k, v in over.items():
        if k in R.P:
            R.P[k] = v
        elif k in DR.D:
            DR.D[k] = v
        else:
            setattr(R, k, v)


def looks(rec, f, o):
    """How a recorded race looks: field spread at each call (lengths, leader to last), the biggest burst (a horse
    gaining on the field's median speed, ft/s, over 2 s before the drive), winning margin, place of the winner at the 3/4."""
    fr = rec["frames"]; n = len(f)
    S = np.array([[x[0] for x in F] for F in fr]); V = np.array([[x[2] for x in F] for F in fr])
    lead = S.max(1)
    calls = {}
    for c, s in (("q1", 1320), ("half", 2640), ("q3", 3960)):
        k = int(np.argmax(lead >= s)); calls[c] = k
    spread = {c: float((S[k].max() - S[k].min()) / R.LENGTH) for c, k in calls.items()}
    drive = int(np.argmax(lead >= R.FT_MILE - 1400))
    w = int(2 / DT)
    rel = V[:drive] - np.median(V[:drive], axis=1, keepdims=True)
    burst = float(max(0.0, np.max([np.convolve(rel[:, j], np.ones(w) / w, "valid").max() for j in range(n)]))) if drive > w else 0.0
    win = [h.name for h in f].index(o[0].name)
    place_q3 = int((S[calls["q3"]] > S[calls["q3"], win]).sum()) + 1
    margin = (o[1].time - o[0].time) * R.FT_MILE / o[0].time / R.LENGTH
    a = R.audit(rec)
    return dict(spread=spread, burst=burst, margin=margin, place_q3=place_q3, trip=P1.trip(rec, f, o[0]),
                safe=a["overlaps"] + a["safety"] + a["four_wide_turn_steps"] == 0,
                breaks=sum(1 for e in rec["events"] if e[2] == "broke stride"), time=o[0].time)


if __name__ == "__main__":
    if sys.argv[1] == "probe":
        N = int(sys.argv[2])
        over = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        apply(over)
        rows = []
        for i in range(N):
            rng = random.Random(5150 + i)
            f = P1.field([{t: rng.gauss(0, .4) for t in P1.TR} for _ in range(8)], "half")
            o, rec = R.run(f, "half", DR.Driver(), seed=5150 + i, dt=DT)
            rows.append(looks(rec, f, o))
        med = lambda k: np.median([r[k] for r in rows])
        print(f"{N} races {over}: spread (lengths) q1 {np.median([r['spread']['q1'] for r in rows]):.1f} half {np.median([r['spread']['half'] for r in rows]):.1f}"
              f" q3 {np.median([r['spread']['q3'] for r in rows]):.1f} | biggest burst median {med('burst'):.1f} ft/s, worst {max(r['burst'] for r in rows):.1f}"
              f" | margin median {med('margin'):.2f} L | photos {100*np.mean([r['margin'] < .25 for r in rows]):.0f}% | safe {100*np.mean([r['safe'] for r in rows]):.0f}%")
