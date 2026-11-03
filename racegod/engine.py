"""RaceGod V5 prototype: one simulated race, and the result is whatever crosses the wire. Not imported by the game.

Same contract as outcome.race: race(field, track, passing) returns the finishing order and sets each horse's trip,
raw_time, last_time, margin_l and why. story(order, track, passing) is the replay's story, read off the run itself
instead of rebuilt from trip text (story.build), so the picture and the result can't disagree.

What the outcome model fitted comes in as inputs: omega, w_k, s_eps and s_margin set each horse's steady speed; c_post
is feet per post to cross at the start; drivers pick trips by the same rule, in the same five roles; breaks follow the
manners curve. What the model had as role bonuses (A_lead, A_pocket...) the run has to earn: cover is cheaper than
racing uncovered, the outside loses ground on the turns, a hot pace empties the leader, a boxed horse can't go.
Units: feet and seconds along the rail. A length is a fifth of a second at the leader's speed (the board's rule)."""
import math, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sim
from outcome import K, LUCK, NOSE, SEC_PER_LENGTH, WITHIN, ROLES, P, DUEL, P_NONE, N_FOLLOW, FO_MAX, bars, best_mile

DT = 0.25
MILE = 5280.0
LANE_FT = 7.0
SLOT = 20.0                    # nose to nose in single file: 16 ft on the screen (the story's length is a fifth of a second, ~10 ft here; the viewer draws 8)
BODY_L = 2.0                   # lengths (fifths of a second) a horse and sulky take up, the viewer's 15.5 ft: the least two in one lane can be apart at the wire
GEOM = {"mile": (1320.0, 1320.0, 320.0), "half": (800.0, 520.0, 300.0)}   # straight, turn, run-in, as race3.Track
E = dict(                      # the run's own knobs, as racegod/engine_fit.py --de left them (2026-11-02, 14 generations; V7)
    launch=0.03, launch_gate=0.024,    # share of steady speed everyone adds leaving the gate, and per unit of gate
    lead_soft=-0.029, lead_hot=0.036,  # the leader's pace off its steady speed: alone (effort-neutral into the wind), or pressed
    push=0.010,                        # a horse going for a spot (the lead, the pocket) runs this much over steady
    push_fo=0.031,                      # the first-over brush: over steady, until it's on the leader's flank (session 2)
    drive_able=0.028,                   # the drive, per model unit of ability under the field's best: class shows at the finish (session 2)
    yield_max=20.000,                    # ft a horse gives up letting others cross at the start, then the line is formed (session 2)
    drive=0.050, drive_kick=0.011,      # the drive: everyone, plus per unit of kick
    prof_kick=0.000,                   # a kick horse sits this much quieter per unit of kick, and has it back in the drive
    draft=0.177, wind=0.056,            # share of effort cover saves; what racing uncovered costs
    turn=0.060,                        # extra effort per lane out on a turn, racing uncovered
    duel=0.072, duel_grit=0.5,         # a duel's extra effort, less this share per unit of grit
    reserve=2.983, reserve_cruise=1.334,  # seconds of over-effort in the tank, and per unit of cruise
    drive_close=0.0,                   # extra drive per unit of kick for a horse that sat covered (the model's k_close; session 3)
    reserve_able=0.0,                  # and per model unit of ability under the field's best: a classy horse can afford a bad trip (session 3)
    fade=0.032,                        # share of steady speed lost per second of overdraft
    follow_k=0.08, lane_rate=1.0,     # the following controller (ft/s per ft off the slot); lanes a second sideways
    move=(0.5, 0.75), move_w=(55, 45),   # where first-over pulls (share of the mile), and how often each
    drive_ft=1400.0, cap=1.08,        # where the drive starts; the speed limit on any instant, over the horse's own mile
    break_s=3.0, accel=3.0,           # seconds a breaker runs at half speed; ft/s^2 a horse changes speed
    ease=4.514,                         # ft/s under the horse inside it a horse takes back to drop in behind
)
rng = random.Random()


def _arcs(straight, turn, run_in):
    s, out = 0.0, []
    while s < MILE:
        for ln, bend in ((run_in, 0), (turn, 1), (straight, 0), (turn, 1), (straight - run_in, 0)):
            if bend:
                out.append((s, s + ln))
            s += ln
            if s >= MILE:
                break
    return [(a, b) for a, b in out if a < MILE]


def _stats(h, track):                                           # the same inputs outcome.race races on
    s = dict(h.current(track))
    for t, d in sim.TONIC.get(getattr(h, "tonic_on", None), {}).items():
        s[t] = s[t] + d
    for t, d in (getattr(h, "drive_on", None) or {}).items():
        s[t] = s[t] + d
    return s


def _choose(out, T, p, half):
    """outcome.race's trip choice, in gate order: role and line depth per horse id; the leader and the first-over mover."""
    w_k = 1 - p["omega"]
    A = [p["A_lead"], p["A_pocket"], p["A_fo"], p["A_fol"], 0.0]
    role, depth = {}, {}
    lead = mover = None; pocket_taken = False; followers = 0; line = 0
    can_move = rng.random() >= P_NONE
    for k, h in enumerate(out):
        t = T[h.id]; kh = t["kick"]
        lg = T[lead.id]["grit"] if lead else 0.0
        v = [-math.inf] * 5
        if lead is None:
            v[0] = A[0] + w_k * kh
        if not pocket_taken:
            v[1] = A[1] + w_k * kh
        press = k == 1
        if mover is None and (press or (2 <= k <= FO_MAX["half" if half else "mile"] and can_move)):
            v[2] = A[2] + w_k * kh + p["g"] * (t["grit"] - lg)
        if mover is not None and followers < N_FOLLOW:
            v[3] = A[3] + (w_k + p["k_close"]) * kh
        v[4] = (w_k + p["k_close"]) * kh - p["b_depth"] * line
        noisy = [x + p["s_choice"] * -math.log(-math.log(rng.random() or 1e-12)) for x in v]
        pick = max(range(5), key=lambda i: noisy[i])
        role[h.id], depth[h.id] = pick, (line if pick == 4 else 0)
        if pick == 0: lead = h
        elif pick == 1: pocket_taken = True
        elif pick == 2: mover = h
        elif pick == 3: followers += 1
        else: line += 1
    if lead is None:
        lead = out[0]; role[lead.id], depth[lead.id] = 0, 0
    return role, depth, lead, mover


def race(field, track="mile", passing=False, decided=None):
    """decided: the finishing order as another engine decided it (each horse with .why, .raw_time, .margin_l, .trip): the run
    then choreographs that result (the gate order and trips from the ledger, the finish steered to the decided times) and
    returns it unchanged, with .run set for story(). Traffic is still real: nobody goes through anybody."""
    half = track == "half"
    p = P["half" if half else "mile"]
    straight, turn, run_in = GEOM["half" if half else "mile"]
    R, arcs = turn / math.pi, _arcs(straight, turn, run_in)
    last_turn = max(b for a, b in arcs)
    on_turn = lambda s: any(a <= s < b for a, b in arcs)
    stats = {h.id: _stats(h, track) for h in field}
    T = {h.id: {k: K * (v - 5.0) for k, v in bars(h, stats[h.id]).items()} for h in field}
    form = {h.id: rng.gauss(0, 1) * p["s_form"] for h in field}
    for h in field:
        for k in ("gate", "cruise", "kick"):
            T[h.id][k] += form[h.id]
    w_k = 1 - p["omega"]
    to_raw = (sim.CLOCK_REF - sim.CLOCK_AT) / sim.CLOCK_K
    lim = {h.id: best_mile(bars(h, stats[h.id]), half) - LUCK + to_raw for h in field}
    able = {h.id: p["omega"] * T[h.id]["cruise"] + w_k * T[h.id]["kick"] + p["s_eps"] * rng.gauss(0, 1) for h in field}
    ref = max(field, key=lambda h: able[h.id])                   # the best horse's class sets the clock (outcome.race: the winner's)
    t_ref = max(lim[ref.id] + LUCK + rng.gauss(0, 0.5), lim[ref.id])
    steady = {h.id: MILE / (t_ref + (able[ref.id] - able[h.id]) * p["s_margin"] * SEC_PER_LENGTH) for h in field}
    cap = {h.id: E["cap"] * MILE / (lim[ref.id] + WITHIN * (lim[h.id] - lim[ref.id])) for h in field}
    e = {h.id: T[h.id]["gate"] - p["c_post"] * post + p["s_start"] * rng.gauss(0, 1) for post, h in enumerate(field)}   # outcome.race's start: gate, post, luck
    leave = {h.id: steady[h.id] * (1 + E["launch"] + E["launch_gate"] * (e[h.id] + p["c_post"] * post)) for post, h in enumerate(field)}   # how each one leaves the car
    out = sorted(field, key=lambda h: -e[h.id])                 # the order the drivers expect to be in, and plan their trips on
    role, depth, lead, mover = _choose(out, T, p, half)
    fin_t = {}
    if decided:                                                # the ledger's gate order and trips; speeds from the decided times
        out = sorted(field, key=lambda h: h.why["out"])
        role = {h.id: ROLES.index(h.why["role"]) for h in field}
        depth = {h.id: h.why.get("depth", 0) for h in field}
        lead = next((h for h in field if role[h.id] == 0), out[0]); role[lead.id] = 0
        mover = next((h for h in field if role[h.id] == 2), None)
        fin_t = {h.id: h.raw_time for h in field}
        steady = {h.id: MILE / fin_t[decided[0].id] for h in field}   # the field travels at the winner's pace until the drive; the drive sorts the finish
        e = {h.id: -0.6 * h.why["out"] for h in field}         # they leave in the ledger's gate order, a clear step apart
        leave = {h.id: steady[h.id] * (1 + E["launch"] + E["launch_gate"] * e[h.id]) for h in field}
        cap = {h.id: math.inf for h in field}
        fade_ft = {h.id: max(E["drive_ft"], (fin_t[h.id] - fin_t[decided[0].id]) * steady[h.id] / 0.10) for h in field}   # a well-beaten horse
    else:                                                      # starts giving way early enough never to lose more than a tenth of its speed
        fade_ft = {h.id: E["drive_ft"] for h in field}
    yield_max = math.inf if decided else E["yield_max"]
    push = 0.04 if decided else E["push"]                    # choreographing, a horse going for its spot gets there
    ease = 2.0 if decided else E["ease"]       # choreographing, a horse keeps taking back until the file has a slot for it
    peck = {h.id: (0 if role[h.id] == 0 else 1 if role[h.id] == 1 else 2 + out.index(h)) for h in field}   # who yields to whom crossing over: the leader, the pocket, then gate order (DECISIONS 193)
    tank = {h.id: math.inf if decided else max(0.5, E["reserve"] + E["reserve_cruise"] * T[h.id]["cruise"] + E["reserve_able"] * (able[h.id] - able[ref.id])) for h in field}   # class is tank as well as speed (session 3)
    S = {}
    for post, h in enumerate(field):
        S[h.id] = dict(h=h, s=0.0, lane=float(post), tgt=post, v=0.85 * steady[h.id], E=tank[h.id],
                       fin=None, limited=0.0, broke=("broke" in h.trip) if decided else rng.random() < 0.005 * math.exp(-2.88 * T[h.id]["manners"]),
                       break_at=rng.uniform(300.0, 0.6 * MILE), break_until=None, path=[], gave=0.0, out=out.index(h) + 1)
    move_s = rng.choices(E["move"], weights=E["move_w"])[0] * MILE
    t, quarters = 0.0, []
    while any(d["fin"] is None for d in S.values()) and t < 200:
        states = list(S.values())
        front = max(states, key=lambda d: d["s"])
        while len(quarters) < 3 and front["s"] >= (len(quarters) + 1) * 1320.0:
            quarters.append(t - (front["s"] - (len(quarters) + 1) * 1320.0) / max(front["v"], 1.0))
        for d in states:
            d["path"].append((d["s"], d["lane"], d["v"]))
        plan = {}
        for d in states:
            h, s, ln = d["h"], d["s"], round(d["lane"])
            st, r = steady[h.id], role[h.id]
            drive = s >= MILE - fade_ft[h.id]
            ahead = min((o for o in states if o is not d and round(o["lane"]) == ln and o["s"] > s), key=lambda o: o["s"], default=None)
            gap = ahead["s"] - s if ahead else math.inf
            covered = gap < SLOT + 8
            free = st * (1 - E["draft"]) ** (-1 / 3) if covered else st   # the pace cover pays for
            quiet = E["prof_kick"] * T[h.id]["kick"]                     # a closer's profile: quieter early, all of it back in the drive
            if decided and drive:
                want = max(0.8 * st, (MILE - s) / max(fin_t[h.id] - t, DT))   # steered to the decided time at the wire
            elif s < 1320 and r != 0:
                want = leave[h.id]                                # the first quarter is run on gate speed
            elif drive:
                want = st * (1 + E["drive"] + (E["drive_kick"] + E["drive_close"] * (r in (3, 4))) * T[h.id]["kick"] + E["drive_able"] * (able[h.id] - able[ref.id])
                             + quiet * (MILE - E["drive_ft"]) / E["drive_ft"])   # a closer's kick counts for more (the model's k_close)
            elif r == 0:
                clear = all(o is d or o["s"] < s - 0.6 * SLOT for o in states)
                pressed = any(o is not d and round(o["lane"]) >= 1 and o["s"] > s - SLOT for o in states)
                want = (leave[h.id] if s < 1320 else st * (1 + (E["lead_hot"] if pressed else E["lead_soft"]))) if clear else st * (1 + push) if s < MILE / 3 else free   # brushes to the quarter, then a breather
            elif r == 1 and s < MILE / 3 and not (ahead is lead or (ahead and ahead["s"] <= S[lead.id]["s"])):
                want = st * (1 + push)                       # the pocket: get in right behind the leader
            elif r == 2 and s >= move_s and S[lead.id]["s"] - s > 2.0:
                want = st * (1 + E["push_fo"])                    # first-over: brushes up to the leader's flank
            elif r == 2 and s >= move_s:
                want = S[lead.id]["v"] + 0.5                      # on the flank: sits on the leader, who has to answer
            else:
                want = free * (1 - quiet)
            lane_max = 4 if s >= last_turn else 2
            if r == 1 and s < 1320 and ahead is not S[lead.id] and S[lead.id]["s"] > s:
                want = max(want, st * (1 + push))            # the pocket: up behind the leader
            if ahead and gap < 2 * SLOT:                          # a horse in front in this lane: sit on it, or get round it
                v_f = ahead["v"] + E["follow_k"] * (gap - SLOT)
                if want > v_f and gap < 1.5 * SLOT:
                    if drive and ln < lane_max and _clear(states, d, ln + 1):
                        d["tgt"] = ln + 1
                    elif drive and passing and ln == 0 and s >= last_turn and _clear(states, d, -1) and (not decided or "passing lane" in h.trip):
                        d["tgt"] = -1
                    else:
                        want = v_f                                # boxed
                else:
                    want = min(want, max(v_f, 0.9 * st))
            if r == 2 and s >= move_s and ln == 0:
                d["tgt"] = 1
            if r == 3 and mover and s >= move_s and S[mover.id]["s"] > s + 0.5 * SLOT and round(S[mover.id]["lane"]) == 1 and ln == 0:
                d["tgt"] = 1                                      # pull out behind the first-over horse, into its cover
            if ln > 0 and d["tgt"] >= ln and not (r in (2, 3) and s >= move_s) and not drive:
                senior_behind = any(o is not d and peck[o["h"].id] < peck[h.id] and round(o["lane"]) >= ln and 0 < s - o["s"] < 2 * SLOT for o in states)
                if _clear(states, d, ln - 1, 0.6 * SLOT) and not senior_behind:   # get to the rail when there's room, and nobody who ranks above it is still coming
                    d["tgt"] = ln - 1
                else:
                    inner = [o for o in states if o is not d and round(o["lane"]) == ln - 1 and abs(o["s"] - s) < SLOT]
                    if inner and all(peck[h.id] < peck[o["h"].id] for o in inner):
                        want = max(want, leave[h.id] * (1 + push))   # it ranks above what's inside: push on and cross in front (they yield)
                    elif inner and d["gave"] < yield_max:
                        want = min(want, min(o["v"] for o in inner) - ease)   # take back and drop in behind
            seniors = [o for o in states if o is not d and round(o["lane"]) == ln + 1 and abs(o["s"] - s) < SLOT and peck[o["h"].id] < peck[h.id]]
            if not drive and s < 0.6 * MILE and d["gave"] < yield_max and seniors:
                want = min(want, min(o["v"] for o in seniors) - ease)   # a horse that ranks above it wants in: let it cross
            d["gave"] += max(0.0, d["v"] - want) * DT             # what it has given up so far
            if d["broke"] and d["break_until"] is None and s >= d["break_at"]:
                d["break_until"] = t + E["break_s"]; d["broke_t"] = t
            if d["break_until"] is not None and t < d["break_until"]:
                want = 0.5 * st
            over = (d["v"] / st) ** 3 * ((1 - E["draft"]) if covered else 1 + E["wind"] + (E["turn"] * max(0, ln) if on_turn(s) else 0)) - 1
            if r == 0 and any(o is not d and round(o["lane"]) >= 1 and abs(o["s"] - s) < SLOT for o in states):
                over += E["duel"] * max(0.0, 1 - E["duel_grit"] * T[h.id]["grit"])   # the leader pays for being pressed; the presser arrived with momentum
            d["E"] = min(tank[h.id], d["E"] - max(over, -0.3) * DT) if not decided else d["E"]
            if d["E"] < 0:
                want = min(want, st * (1 + E["fade"] * d["E"]))
            if want > cap[h.id]:
                want, d["limited"] = cap[h.id], d["limited"] + DT
            plan[h.id] = max(d["v"] - E["accel"] * DT, min(d["v"] + E["accel"] * DT, want))
        for d in states:
            d["v"] = plan[d["h"].id]
            tgt = d["tgt"]
            d["lane"] += max(-E["lane_rate"] * DT, min(E["lane_rate"] * DT, tgt - d["lane"]))
            ln = d["lane"]
            d["s"] += d["v"] * DT * (R / (R + ln * LANE_FT) if ln > 0 and on_turn(d["s"]) else 1.0)
            if d["fin"] is None and d["s"] >= MILE:
                d["fin"] = t + DT - (d["s"] - MILE) / d["v"]
        t += DT
    for d in S.values():
        if d["fin"] is None:
            d["fin"] = t + (MILE - d["s"]) / max(d["v"], 1.0)
    global _LAST
    _LAST = S                                                  # the last run's states, for the lab to look at
    order = list(decided) if decided else sorted(field, key=lambda h: S[h.id]["fin"])
    win = S[order[0].id]["fin"]
    prev = None
    for h in ([] if decided else order):                       # a decided result keeps its times
        d = S[h.id]
        tf = d["fin"] if prev is None else max(d["fin"], prev + NOSE * SEC_PER_LENGTH)
        h.raw_time, prev = tf, tf
        h.margin_l = (tf - win) / SEC_PER_LENGTH
        h.last_time = sim.clock(tf, half)
    # the story's calls, and the trips as they were run (not as the drivers planned them)
    q1, q2, q3 = (quarters + [win] * 3)[:3]
    calls_t = [0.0, 0.45 * q1, q1, q2, q3, q3 + 0.55 * (win - q3), win]
    at = {h.id: [_at(S[h.id]["path"], tc) for tc in calls_t] for h in field}
    for c in range(7):
        s_lead, v_lead = max((at[h.id][c][0], at[h.id][c][2]) for h in field)
        for h in field:
            s, ln, _ = at[h.id][c]
            at[h.id][c] = (round(float(round(ln)), 1), round((s_lead - s) / (SEC_PER_LENGTH * max(v_lead, 1.0)), 2))
    for h in field:
        at[h.id][6] = (at[h.id][6][0], round(h.margin_l, 2))
    if decided:                                                # hold the stretch line to the wire; two in a lane never closer than a body
        for h in field:
            at[h.id][6] = (at[h.id][5][0], at[h.id][6][1])
        taken = []
        for h in order:
            ln, b = at[h.id][6]
            while any(pl == ln and abs(pb - b) < BODY_L for pl, pb in taken) and ln < 4:
                ln += 1.0
            taken.append((ln, b))
            at[h.id][6] = (ln, b); at[h.id][5] = (ln, at[h.id][5][1])
        def crossed(h, o):                                     # the two swap order between the stretch call and the wire
            return (at[o.id][5][1] < at[h.id][5][1]) != (at[o.id][6][1] < at[h.id][6][1])
        for _ in range(6):                                     # a pass inside one lane can't be drawn (the viewer won't run a horse
            moved = False                                      # through another): the passer pulls out a lane, until the picture is clean
            for h in order:
                ln, b = at[h.id][6]
                while ln < 4 and any(o is not h and at[o.id][6][0] == ln and (abs(at[o.id][6][1] - b) < BODY_L or (crossed(h, o) and b < at[o.id][6][1])) for o in field):
                    ln += 1.0; moved = True
                at[h.id][6] = (ln, b); at[h.id][5] = (ln, at[h.id][5][1])
            if not moved:
                break
    leader3 = max(field, key=lambda h: -at[h.id][3][1])
    rail3 = sorted((h for h in field if at[h.id][3][0] == 0 and h is not leader3), key=lambda h: at[h.id][3][1])
    pocket3 = rail3[0] if rail3 and at[leader3.id][3][0] == 0 else None
    outside4 = sorted((h for h in field if at[h.id][4][0] >= 1), key=lambda h: at[h.id][4][1])
    for post, h in enumerate(field, 1):
        d, r = S[h.id], role[h.id]
        if decided:
            h.run = dict(calls=calls_t, quarters=[0.0, q1, q2, q3, win], at=at[h.id], post=post, leader=leader3.name, fo=outside4[0].name if outside4 else None,
                         fo_at=next((calls_t[c] for c in (3, 4) if outside4 and at[outside4[0].id][c][0] >= 1), None), passing=passing, broke_at=d.get("broke_t"))
            continue
        if h is leader3:
            how = "on the lead"
        elif h is pocket3:
            how = "sat in the pocket, up the passing lane" if at[h.id][6][0] == -1 and order.index(h) < order.index(leader3) else "sat in the pocket"
        elif outside4 and h is outside4[0]:
            how = "parked first-over"
        elif h in outside4:
            how = "sat mid-pack, moved after the half"
        else:
            how = "sat in behind, came from off the pace" if at[h.id][3][1] >= 4 and order.index(h) < 3 else "sat in behind"
        h.trip = f"post {post}, {how}" + (", broke stride" if d["broke"] else "")
        h.why = dict(out=d["out"], role=ROLES[r], depth=depth[h.id], perf=round(able[h.id], 3), form=round(form[h.id], 3), broke=d["broke"],
                     model_l=round((able[ref.id] - able[h.id]) * p["s_margin"], 2), limited=d["limited"] > 2.0, margin=round(h.margin_l, 2),
                     ceiling=round(lim[ref.id] + WITHIN * (lim[h.id] - lim[ref.id]), 2), at_half=at[h.id][3][1], tank=round(d["E"], 2))
        h.run = dict(calls=calls_t, quarters=[0.0, q1, q2, q3, win], at=at[h.id], post=post, leader=leader3.name, fo=outside4[0].name if outside4 else None,
                     fo_at=next((calls_t[c] for c in (3, 4) if outside4 and at[outside4[0].id][c][0] >= 1), None), passing=passing, broke_at=d.get("broke_t"))
    return order


def choreograph(order, track, passing=False):
    """The replay's story for a result another engine decided: the run plays the ledger's trips to the decided finish."""
    field = sorted(order, key=lambda h: h.post)
    rng.seed(sum(int(h.raw_time * 10) for h in order))
    race(field, track, passing, decided=order)
    return story(order, track, passing)


def _clear(states, d, lane, behind=SLOT):
    """Room in that lane: a slot ahead; `behind` ft behind (a horse crossing in front of one it has beaten needs less, the one behind takes back)."""
    return not any(o is not d and (round(o["lane"]) == lane or o["tgt"] == lane) and (o["s"] - d["s"] < SLOT if o["s"] > d["s"] else d["s"] - o["s"] < behind) for o in states)


def _at(path, tc):
    i = tc / DT
    k = min(int(i), len(path) - 1)
    a, b = path[k], path[min(k + 1, len(path) - 1)]
    f = i - k
    return tuple(x + (y - x) * f for x, y in zip(a, b))


def story(order, track, passing=False):
    """The replay's story, in story.build's shape, read straight off the run."""
    from story import fifth, _mt
    run = order[0].run
    k = order[0].last_time / run["quarters"][4]                 # the run's seconds onto the clock (sim.clock), so the quarters add up to the final
    tt, calls_t = [q * k for q in run["quarters"]], [c * k for c in run["calls"]]
    cur = {h.id: h.current(track) for h in order}
    rows = []
    for place, h in enumerate(order, 1):
        at = h.run["at"]
        rows.append({"name": h.name, "post": h.run["post"], "behind": [min(b, 40.0) for _, b in at], "lane": [ln for ln, _ in at], "place": place,   # 40 L: the viewer's wall, as story.build (RaceGod V3, open)
                     "time": fifth(h.last_time), "trip": h.trip, "stamina": round(cur[h.id]["stamina"], 2), "early": round(cur[h.id]["early_speed"], 2),
                     "coat": getattr(h, "coat", "bay"), "marking": getattr(h, "marking", "none"),
                     "broke_at": round(h.run["broke_at"] * k, 1) if h.run.get("broke_at") is not None else None,
                     "fractious": bool(getattr(h, "why", {}).get("fractious"))})   # when it broke, on the clock (the viewer's tell)
    rows[0]["behind"][6] = 0.0
    caps = [[0.0, "They're away"], [calls_t[1], f"{run['leader']} leaves for the lead"]]
    if run["fo"] and run["fo_at"]:
        caps.append([run["fo_at"] - 3, f"{run['fo']} pulls first-over"])
    caps.append([tt[2], f"Half in {_mt(tt[2])}, {run['leader']} in front"])
    caps.append([tt[3], f"Three-quarters in {_mt(tt[3])}"])
    closer = max(order[:3], key=lambda h: h.run["at"][2][1])
    if "passing lane" in order[0].trip:
        caps.append([calls_t[5] - 2, f"{order[0].name} dives up the passing lane"])
    elif closer.name != run["leader"]:
        caps.append([calls_t[5], f"{closer.name} comes with a run"])
    caps.append([tt[4], f"{order[0].name} wins it in {_mt(tt[4])}"])
    caps.sort(key=lambda c: c[0])
    return {"track": track, "calls": calls_t, "quarters": [fifth(q) for q in tt], "horses": rows, "captions": caps, "final": fifth(order[0].last_time)}


if __name__ == "__main__":
    horses = [sim.founder() for _ in range(9)]
    for i, h in enumerate(horses, 1):
        h.post = i; h.name = f"H{h.id}"
    for track in ("mile", "half"):
        order = race(horses, track, passing=True)
        s = story(order, track, True)
        assert [r["place"] for r in s["horses"]] == list(range(1, 10))
        assert s["horses"][0]["behind"][6] == 0 and all(b >= a for a, b in zip([r["behind"][6] for r in s["horses"]], [r["behind"][6] for r in s["horses"]][1:]))
        assert all(x > 0 for x in [b - a for a, b in zip(s["quarters"], s["quarters"][1:])]), s["quarters"]
        print(track, "winner", order[0].name, order[0].trip, "in", s["final"], "quarters", s["quarters"], "margins", [r["behind"][6] for r in s["horses"]])
        print("  lanes at the three-quarters", [r["lane"][4] for r in s["horses"]], "behind at the half", [r["behind"][3] for r in s["horses"]])
    print("all checks passed")
