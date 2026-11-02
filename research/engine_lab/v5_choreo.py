"""Replay library choreographer (DECISIONS 226): cinematic races authored as formations, not simulated.

A story is a sequence of formations at set points of the mile (the way a harness race shapes up: the rail line of
leader, pocket and three-hole; an outer flow of first-, second- and third-over; the stretch fan). Each horse plays a
role; between formations it moves smoothly (monotone cubic in lengths-behind and lane), and the leader runs a real
pace from the quarters. Variants randomize posts, gaps, move timing and margins; each one is checked: no two bodies
overlap, nobody bursts, the field stays compact. Only variants that pass go in the library.
    python v5_choreo.py <story> <variants> [seed]      try variants of one story and report how many pass"""
import json, math, os, random, sys
import numpy as np
from scipy.interpolate import PchipInterpolator

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import race3 as R

LEN, BODY, WIDE, HZ = 8.0, 15.5, 5.4, 20          # a length (ft), nose to wheel, a sulky's width, path rate
T = R.HALF
STRETCH_FAN = 3960                                  # from the 3/4 on, horses fanning out drift wider as room opens
FAN = bool(int(os.environ.get("FAN", "1")))
D = [0, 150, 300, 820, 1320, 1980, 2640, 3300, 3960, 4400, 4780, 5050, 5280]   # formation points (ft of the mile)
STORIES = ("wire", "pocket", "first_over", "sweep", "closer", "photo")
TITLE = {"wire": "Wire to wire, ran away with it", "pocket": "Pocket trip, out the passing lane",
         "first_over": "First-over, ground it out", "sweep": "Followed cover, swept by late",
         "closer": "From far back, through traffic", "photo": "Head and head, a photo"}


def leader_clock(final, rng):
    """The leader's distance against time: a mobile-gate start at 44 ft/s, then quarters in the classic shape (quick
    first, slowest second, home strong), speed changes eased over a few seconds."""
    q = final / 4
    qt = [q - 0.6 + rng.uniform(-.2, .2), q + 1.2 + rng.uniform(-.3, .3), q + 0.2 + rng.uniform(-.2, .2)]
    qt.append(final - sum(qt))
    v_q = [1320 / x for x in qt]
    t, s, v, out = 0.0, 0.0, 44.0, []
    while s < R.FT_MILE + 600:
        k = min(3, int(s // 1320))
        target = v_q[k] if s < R.FT_MILE else v_q[3] * 0.8                 # past the wire: easing up
        v += max(-1.5, min(1.5, target - v)) * (1 / HZ) * (1.6 if s < 400 else 0.9)
        s += v / HZ; t += 1 / HZ
        out.append((t, s))
    return np.array(out), [round(sum(qt[:i + 1]), 2) for i in range(4)]


def formations(story, posts, rng):
    """Roles, then lengths-behind and lane for every horse at every formation point. posts[i] is horse i's post (1-8).
    The classic shape: a rail line (leader, pocket, then the rest nose to tail) and an outer flow of the horses that left
    and couldn't fold in (first-over, then its follower). Every spot is its own, so the plan never asks two horses for
    the same piece of track. Returns behind (n, len(D)), lane (n, len(D)), finish order (indices), roles."""
    n = len(posts)
    by_post = sorted(range(n), key=lambda i: posts[i])
    j = lambda: rng.uniform(-0.1, 0.1)
    G = 2.1                                                         # nose to nose in a line, lengths
    lead = rng.choice(by_post[:3]) if rng.random() < 0.85 else by_post[3]
    pocket = next(i for i in by_post if i != lead)
    if rng.random() < 0.3:
        pocket = next(i for i in by_post if i not in (lead, pocket))
    outside = [i for i in by_post[4:] if i not in (lead, pocket)]
    fo, fol = rng.sample(outside, 2)
    rail = [lead, pocket] + [i for i in by_post if i not in (lead, pocket, fo, fol)]
    back = rail[-1]
    role = {i: "line" for i in range(n)}
    role.update({lead: "lead", pocket: "pocket", fo: "first-over", fol: "follow", back: "back"})
    pos = {h: k * G + (j() if k else 0.0) for k, h in enumerate(rail)}
    pos[fo] = 2 * G + 0.3 + j(); pos[fol] = pos[fo] + G               # parked alongside the three-hole, follower behind
    beh = np.zeros((n, len(D))); lane = np.zeros((n, len(D)))
    for i in range(n):
        out = i in (fo, fol)
        lane[i, 0] = posts[i] - 1
        beh[i, 1] = 0.0 if i == lead else (0.25 if i == pocket else 0.6 + 0.2 * (posts[i] - 1))
        lane[i, 1] = max(1.0 if out else 0.0, (posts[i] - 1) * 0.7 - (1.0 if i in (lead, pocket) else 0.0))
        beh[i, 2] = pos[i] * 0.5; lane[i, 2] = 1.0 if out else (0.0 if i in (lead, pocket) else min(1.5, (posts[i] - 1) * 0.35))
        for c in range(3, len(D)):
            beh[i, c] = pos[i] + (j() * 0.5 if c == 4 else 0.0); lane[i, c] = 1.0 if out else 0.0
    # the flow rolls: first-over sits parked to the half, then grinds up to the leader's flank by the 3/4
    gain = {5: 0.6, 6: 1.6, 7: 2.8, 8: 3.9}
    for c, g in gain.items():
        beh[fo, c] = max(0.5, pos[fo] - g); beh[fol, c] = beh[fo, c] + G
    if story == "closer":                                           # the back horse swings out early and comes wide
        for c in (7, 8):
            lane[back, c] = 1.0
        beh[back, 8] = max(beh[back, 8], beh[fol, 8] + G)
    top = {"wire": [lead, pocket, fo], "pocket": [pocket, lead, fo], "first_over": [fo, lead, pocket],
           "sweep": [fol, fo, lead], "closer": [back, fo, lead], "photo": [fo, lead, pocket]}[story]
    order = top + [h for h in sorted(range(n), key=lambda i: beh[i, 8]) if h not in top]
    first = {"wire": 3.0 + rng.uniform(0, 1.5), "photo": rng.uniform(0.03, 0.12), "closer": rng.uniform(0.2, 0.5),
             "pocket": rng.uniform(2.2, 3.0)}.get(story, rng.uniform(0.5, 1.5))   # pocket: clear of the leader to cross back over
    fin = np.cumsum([0.0, first] + [rng.uniform(0.3, 1.4) for _ in range(n - 2)])
    # the stretch: who wins from behind goes a lane wider than whoever is in front of them; the pocket dives inside
    wide = {"pocket": {pocket: -1.0}, "sweep": {fol: 2.0}, "closer": {back: 2.0}}.get(story, {})
    for h in range(n):
        f = fin[order.index(h)]; b8 = beh[h, 8]
        for c, frac in ((9, 0.33), (10, 0.62), (11, 0.83), (12, 1.0)):              # gains spread evenly down the lane
            beh[h, c] = b8 + (f - b8) * frac
            lane[h, c] = wide.get(h, lane[h, 8])
    return beh, lane, order, role


def paths(beh, lane, lead_s, savers=()):
    """Continuous paths: rail distance s and lane offset y (ft) for every horse at HZ. Each horse steers toward its
    formation target with eased speed and lane changes, and never into another sulky: it holds its lane when the
    lane it wants is occupied alongside, and checks off rather than run up on the horse in front.
    savers: closers driven to save ground (Patrick, DECISIONS 231): once out, they sit in the second lane, go
    three-wide only when a horse in front of them in their lane is in the way, and tuck back in once there's room."""
    n = beh.shape[0]
    d = np.clip(lead_s[:, 1], 0, R.FT_MILE)
    ts = np.array([lead_s[:, 1] - PchipInterpolator(D, beh[i])(d) * LEN for i in range(n)])
    ty = np.array([R.RAIL_Y + R.LANE * PchipInterpolator(D, lane[i])(d) for i in range(n)])
    m = ts.shape[1]; dt = 1 / HZ
    vt = np.gradient(ts, axis=1) * HZ                                   # the target's own speed (feed-forward)
    S = np.zeros((n, m)); Y = np.zeros((n, m)); V = np.zeros(n) + 44.0
    S[:, 0] = np.maximum(ts[:, 0], 0); Y[:, 0] = ty[:, 0]; dest = ty[:, 0].copy()
    GAP, ACC, LAT = BODY + 1.0, float(os.environ.get("ACC", 3.0)), 3.0
    band = lambda y0, y1: (min(y0, y1) - WIDE / 2, max(y0, y1) + WIDE / 2)   # the strip a horse occupies or is moving across
    hit = lambda p, q: p[0] < q[1] and q[0] < p[1]
    fanned, set_out = set(), set()
    for k in range(1, m):
        S0, Y0, V0 = S[:, k - 1].copy(), Y[:, k - 1].copy(), V.copy()
        fan = set(fanned)                                           # who fans out (once out, stays out): the rail horse alongside a passing-lane horse
        divers = [j for j in range(n) if Y0[j] < R.RAIL_Y - 0.5 and S0[j] >= R.FT_MILE - 80]   # in its last strides, then anyone
        if divers:                                                  # alongside on the outside of a horse that's fanning
            edge = [j for j in range(n) if abs(Y0[j] - R.RAIL_Y) < 1.0 and abs(dest[j] - R.RAIL_Y) < 1.0
                    and j not in divers and any(abs(S0[j] - S0[d]) < BODY + 0.5 for d in divers)]
            while edge:
                fan.update(edge); fanned.update(edge)
                edge = [j for j in range(n) if j not in fan and j not in divers and Y0[j] > R.RAIL_Y - 0.5
                        and any(0 < Y0[j] - Y0[f] < R.LANE + WIDE and abs(S0[j] - S0[f]) < BODY + 0.5 for f in edge)]   # anyone its drift would reach
        for i in range(n):
            s, y = S0[i], Y0[i]
            lo = R.RAIL_Y - R.LANE if s >= T.last_turn_end else R.RAIL_Y
            want = max(lo, ty[i, k])
            if s >= 700:                                                # once settled, horses race in whole lanes
                want = R.RAIL_Y + R.LANE * round((want - R.RAIL_Y) / R.LANE)
            if i in savers and want > R.RAIL_Y + 0.5 and 2000 <= s < R.FT_MILE:
                cap = max(2, round((want - R.RAIL_Y) / R.LANE))         # the plan's lane is as wide as it ever needs to go
                cur = int(round((y - R.RAIL_Y) / R.LANE)); yl = lambda l: R.RAIL_Y + R.LANE * l
                in_way = lambda l, reach: any(j != i and abs(Y0[j] - yl(l)) < WIDE * 0.8 and 0 < S0[j] - s < reach and ts[i, k] > S0[j] - GAP
                                              for j in range(n))
                alongside = lambda l: any(j != i and abs(Y0[j] - yl(l)) < WIDE and abs(S0[j] - s) < BODY + 0.5 for j in range(n))
                if cur < cap and in_way(cur, GAP + 2 * LEN):
                    want = yl(cur + 1)                                  # someone in front in my lane: out one more
                elif cur > 1 and not alongside(cur - 1) and not in_way(cur - 1, GAP + 4 * LEN):
                    want = yl(cur - 1)                                  # room inside: tuck back in and save the ground
                else:
                    want = yl(max(1, cur))
            if i in fan:                                                # pulling up, the field fans out a lane to let the
                if i not in set_out:                                    # passing-lane horse back across before the rail closes
                    dest[i] = y + R.LANE; set_out.add(i)
                want = None
            elif s >= R.FT_MILE and y < R.RAIL_Y - 0.5:                 # past the wire the passing lane closes: back out to the rail line
                if not any(j != i and abs(S0[j] - s) < BODY + 0.5 and abs(Y0[j] - R.RAIL_Y) < WIDE for j in range(n)):
                    dest[i] = R.RAIL_Y                                      # once nobody on the rail is alongside
                want = None
            elif s >= 700 and want > y + 0.5 and (s < STRETCH_FAN or not FAN):   # moving out: whole moves only, once the strip is clear (the stretch fan drifts)
                if abs(want - dest[i]) > 1.0 and abs(y - dest[i]) < 0.5:
                    mine = (y + WIDE / 2 + 0.5, want + WIDE / 2)                # the new strip, not the lane I am leaving
                    if not any(j != i and abs(S0[j] - s) < BODY + 0.5 and hit(mine, band(Y0[j], dest[j])) for j in range(n)):   # a sulky's length clear, ahead or behind
                        dest[i] = want
                want = None
            nd = want                                                   # folding in (and the start): as far as room allows
            for j in ([] if want is None else range(n)):
                if j == i or abs(S0[j] - s) >= BODY + 0.3:
                    continue
                lo_j, hi_j = band(Y0[j], dest[j])
                if want < y and hi_j <= y + 1e-6 and hi_j > nd - WIDE / 2:
                    nd = hi_j + WIDE / 2 + 0.3
                elif want > y and lo_j >= y - 1e-6 and lo_j < nd + WIDE / 2:
                    nd = lo_j - WIDE / 2 - 0.3
            if want is not None:
                dest[i] = nd if (nd - y) * (want - y) > 0 else y
            mine = band(y, dest[i])
            v = vt[i, k] + 0.6 * (ts[i, k] - s)
            for j in range(n):                                          # check off behind anyone in my strip
                if j != i and 0 < S0[j] - s < GAP + 12 and hit(mine, band(Y0[j], dest[j])):
                    v = min(v, (S0[j] - s - GAP) * 1.5 + V0[j])
            v = min(V0[i] + ACC / HZ, max(V0[i] - (4 if s >= R.FT_MILE else 2) * ACC / HZ, v)) if s > 60 else v   # past the wire they pull up
            V[i] = max(v, 0.0)
            S[i, k] = s + V[i] / HZ; Y[i, k] = y + max(-LAT / HZ, min(LAT / HZ, dest[i] - y))
    return S, Y, ts, ty


def check(S, Y):
    """No two bodies overlap; nobody bursts (2-s gain on the field's median speed, before the stretch); compact field."""
    n, m = S.shape
    for a in range(n):
        for b in range(a + 1, n):
            close = (np.abs(S[a] - S[b]) < BODY) & (np.abs(Y[a] - Y[b]) < WIDE) & (np.minimum(S[a], S[b]) > 30) & (np.maximum(S[a], S[b]) < R.FT_MILE + 150)
            if close.any():
                return False, f"overlap {a}-{b}"
    sf = T.lap / 2 - np.pi * T.R - T.arcs[0][0]                      # the replay's finish line, along its lap (race.js RACE.SF)
    lap = (S - R.FT_MILE + sf) % T.lap
    inset = np.where(lap < 90, 8 * lap / 90, np.where(lap < sf + 40, 8, np.clip(8 * (1 - (lap - sf - 40) / 90), 0, 8)))
    inside = (Y + 1 - WIDE / 2) < (-3 - inset)                      # the replay's inside rail (race.js RACE.inset), passing lane included
    if (inside & (S > 2000) & (S < R.FT_MILE + 400)).any():
        return False, "rail"
    V = np.diff(S, axis=1) * HZ
    lead = S.max(0)
    pre = (lead[:-1] > 400) & (lead[:-1] < 4400)                          # past the gate fold (the field drops in behind the leader by design)
    rel = V[:, pre] - np.median(V[:, pre], axis=0)
    w = 2 * HZ
    burst = max(np.convolve(r, np.ones(w) / w, "valid").max() for r in rel)
    if burst > 6.5:
        return False, f"burst {burst:.1f}"
    late = (lead[:-1] >= 4400) & (lead[:-1] < R.FT_MILE)            # the drive: closing speed is real, a sprint isn't
    rel = V[:, late] - np.median(V[:, late], axis=0)
    drive = max(np.convolve(r, np.ones(w) / w, "valid").max() for r in rel) if late.sum() > w else 0.0
    if drive > 9.0:
        return False, f"burst {drive:.1f} in the drive"
    k = int(np.argmax(lead >= 1320))
    spread = (S[:, k].max() - S[:, k].min()) / LEN
    if spread > 15:                                                   # single file on a half-mile runs about 14-15 lengths
        return False, f"spread {spread:.1f}"
    return True, f"ok spread {spread:.1f} burst {burst:.1f}"


def variant(story, seed):
    rng = random.Random(seed)
    n = 8
    posts = list(range(1, n + 1))
    final = 115.9 + rng.uniform(-1.5, 1.5)
    lead_s, quarters = leader_clock(final, rng)
    beh, lane, order, role = formations(story, posts, rng)
    S, Y, ts, ty = paths(beh, lane, lead_s, savers={order[0]} if story == "closer" else ())
    ok, why = check(S, Y)
    lead = S.max(0)
    for ft in (1320, 2640, 3960):                                   # the race kept its shape: everyone near their planned spot
        k = int(np.argmax(lead >= ft))
        off_s = np.abs(S[:, k] - ts[:, k]).max() / LEN; off_y = np.abs(Y[:, k] - ty[:, k]).max() / R.LANE
        if ok and (off_s > 1.0 or off_y > 0.4):
            ok, why = False, f"shape at {ft}: {off_s:.1f} L, {off_y:.1f} lanes off"
    wire_t = [float(np.interp(R.FT_MILE, s, lead_s[:, 0])) for s in S]          # each horse's time at the wire
    got = sorted(range(n), key=lambda i: wire_t[i])
    if ok and got[:2] != order[:2]:
        ok, why = False, f"story {got[:3]} not {order[:3]}"
    return ok, why, dict(story=story, seed=seed, S=S, Y=Y, order=order, role=role, quarters=quarters, t=lead_s[:, 0], wire_t=wire_t, got=got)


if __name__ == "__main__":
    story, N = sys.argv[1], int(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    res = [variant(story, seed * 10000 + k)[:2] for k in range(N)]
    from collections import Counter
    print(story, f"{sum(r[0] for r in res)}/{N} pass;", Counter(r[1].split(" ")[0] for r in res if not r[0]).most_common(4), "| e.g.", next((r[1] for r in res if r[0]), "-"))
