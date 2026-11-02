"""Casting (DECISIONS 229): the outcome model decides a race; the choreographer draws exactly that race. The library's
stories become templates: the model's trips give the formation (leader, pocket and the rail line; first-over and its
followers outside), its finish order and margins give the stretch, and each horse takes the lane it needs to get
past whoever was in front of it. Variants are tried until one passes the library's checks and finishes in the
model's order.
    python v5_cast.py <races> [seed]      cast that many model races (Race Lab field draws) and report how many cast"""
import json, os, random, sys, time
import numpy as np
import v5_choreo as C
import v4_outcome as V

R, D, LEN, G = C.R, C.D, C.LEN, 2.1
LEAD, POCKET, FO, FOL, LINE = range(5)                              # v4_outcome.ROLES order
STORY = {LEAD: "wire", POCKET: "pocket", FO: "first_over", FOL: "sweep", LINE: "closer"}


def story_of(res):
    """The library story a result tells: the winner's trip, or a photo when the margin is under a quarter-length."""
    w = res["order"][0]
    if res["margin"][res["order"][1]] < 0.25:
        return "photo"
    return STORY[res["role"][w]]


def formations(res, rng, at34=None):
    """Lengths-behind and lane for every horse at every formation point, from the model's result. at34: where the
    horses actually were at the 3/4 on a first run (lengths behind, lane); the stretch is planned from there."""
    n, role, start = len(res["role"]), res["role"], res["start"]
    j = lambda: rng.uniform(-0.1, 0.1)
    by_start = sorted(range(n), key=lambda i: start[i])
    lead = next(i for i in by_start if role[i] == LEAD)
    pocket = next((i for i in by_start if role[i] == POCKET), None)
    fo = next((i for i in by_start if role[i] == FO), None)
    fols = [i for i in by_start if role[i] == FOL] if fo is not None else []
    rest = [i for i in by_start if i not in (lead, pocket) and i not in fols]
    if fo is not None and fo in rest:                               # followers settle right behind the horse whose cover they'll take
        k = rest.index(fo) + 1; rest[k:k] = fols
    rail = [lead] + ([pocket] if pocket is not None else []) + rest
    pos = {h: k * G + (j() if k else 0.0) for k, h in enumerate(rail)}
    beh = np.zeros((n, len(D))); lane = np.zeros((n, len(D)))
    for i in range(n):                                              # the gate folds into one line on the rail
        p = res["post"][i]
        lane[i, 0] = p - 1
        beh[i, 1] = 0.0 if i == lead else (0.25 if i == pocket else 0.6 + 0.2 * (p - 1))
        lane[i, 1] = max(0.0, (p - 1) * 0.7 - (1.0 if i in (lead, pocket) else 0.0))
        beh[i, 2] = pos[i] * 0.5; lane[i, 2] = 0.0 if i in (lead, pocket) else min(1.5, (p - 1) * 0.35)
        for c in range(3, len(D)):
            beh[i, c] = pos[i] + (j() * 0.5 if c == 4 else 0.0)
    if fo is not None:                                              # first-over pulls out after the quarter and rolls up to the
        out_at = rng.choice([5, 5, 6])                              # leader's flank by the 3/4; its followers come out behind it
        for c, g in {5: 0.6, 6: 1.6, 7: 2.8, 8: 3.9}.items():
            if c < out_at:
                continue
            beh[fo, c] = max(0.5, pos[fo] - g); lane[fo, c] = 1.0
            for k, h in enumerate(fols):                            # followers come out a call later, once first-over is clear
                beh[h, c] = beh[fo, c] + G * (k + 1); lane[h, c] = 1.0 if c > out_at else 0.0
    # the stretch: finish in the model's order at its margins. A horse that beats someone who was ahead of it in its
    # own lane at the 3/4 has to come round them, a lane wider; the pocket horse that beats the leader uses the passing lane
    order, fin = res["order"], np.array([res["margin"][i] for i in res["order"]])
    if at34 is not None:
        beh[:, 8], lane[:, 8] = at34[0], np.round(at34[1])
    sl = {}
    for rank, h in enumerate(order):
        l = lane[h, 8]
        beaten_near = [x for x in order[rank + 1:] if beh[x, 8] < beh[h, 8] + 1.0]   # ahead (however far), or alongside within a length
        if h == pocket and lead in beaten_near and all(lane[x, 8] > 0 or x == lead for x in beaten_near) \
                and res["margin"][lead] - res["margin"][h] >= 2.4:   # up the passing lane only if clear to cross back after the wire
            l = -1.0
        else:                                                       # outside everyone it beats that's ahead or alongside
            for x in sorted(beaten_near, key=lambda x: sl.get(x, lane[x, 8])):
                if sl.get(x, lane[x, 8]) >= l:
                    l = sl.get(x, lane[x, 8]) + 1
            for x in order[:rank]:                                  # can't finish within a length of someone in front in the same lane
                if sl[x] == l and res["margin"][h] - res["margin"][x] < 2.2 and beh[x, 8] <= beh[h, 8] + 1.0:
                    l += 1
            l = min(l, 4.0)
        sl[h] = l
    late = {h for h in order if sl[h] >= 2 and beh[h, 8] - min(beh[:, 8]) > 6}  # coming from far back: swing out at the 3/4
    diver = next((h for h in order if sl[h] < 0), None)
    for h in range(n):
        f = fin[order.index(h)]; b8 = beh[h, 8]
        if h in late:
            lane[h, 8] = sl[h] - 1
        # a leader with the pocket horse diving under it holds on until the passing lane opens, then gives way
        fr = ((9, 0.1), (10, 0.4), (11, 0.78), (12, 1.0)) if diver is not None and h in (lead, diver) else ((9, 0.33), (10, 0.62), (11, 0.83), (12, 1.0))
        for c, frac in fr:
            beh[h, c] = b8 + (f - b8) * frac; lane[h, c] = sl[h]
    return beh, lane


def cast(res, tries=40, seed=0):
    """A replay of exactly this result, or None. res: post, role, start (gate order), order (finish), margin (lengths)."""
    for t in range(tries):
        rng = random.Random(seed * 1000 + t)
        final = res.get("final", 115.9) + rng.uniform(-.3, .3)
        lead_s, quarters = C.leader_clock(final, rng)
        state = rng.getstate()
        beh, lane = formations(res, rng)
        S, Y, ts, ty = C.paths(beh, lane, lead_s)                   # first run: where they really are at the 3/4
        k = int(np.argmax(S.max(0) >= 3960))
        rng.setstate(state)
        beh, lane = formations(res, rng, ((S[:, k].max() - S[:, k]) / LEN, (Y[:, k] - R.RAIL_Y) / R.LANE))
        S, Y, ts, ty = C.paths(beh, lane, lead_s)
        ok, why = C.check(S, Y)
        wire_t = [float(np.interp(R.FT_MILE, s, lead_s[:, 0])) for s in S]
        got = sorted(range(len(S)), key=lambda i: wire_t[i])
        if ok and got != list(res["order"]):
            ok, why = False, "order"
        if ok:
            return dict(S=S, Y=Y, t=lead_s[:, 0], quarters=quarters, wire_t=wire_t, got=got, tries=t + 1, why=why)
    return None


def model_races(N, seed, track="half"):
    """N outcome-model races on fresh class fields, as cast inputs."""
    p = dict(V.FIXED, **json.load(open(os.path.join(V.OUT, f"fit_{track}.json")))["params"])
    n = V.N_STARTERS[track]
    Dr = V.draws(N, n, seed); Dr.pop("present")
    P, role, rank = V.race(p, Dr, track)
    out = []
    for r in range(N):
        order = [int(i) for i in np.argsort(-P[r])]
        margin = {i: float((P[r, order[0]] - P[r, i]) * p["s_margin"]) for i in range(n)}
        out.append(dict(post=list(range(1, n + 1)), role=[int(x) for x in role[r]], start=[int(x) for x in rank[r]], order=order,
                        margin=[margin[i] for i in range(n)], traits=Dr["traits"][r].round(3).tolist()))
    return out


if __name__ == "__main__":
    N = int(sys.argv[1]); seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    from collections import Counter
    t0 = time.time(); got, by = 0, Counter()
    for k, res in enumerate(model_races(N, 600 + seed)):
        c = cast(res, seed=k)
        by[(story_of(res), c is not None)] += 1
        got += c is not None
    print(f"cast {got}/{N} in {time.time() - t0:.0f}s |", {s: f"{by[(s, True)]}/{by[(s, True)] + by[(s, False)]}" for s in sorted({s for s, _ in by})})
