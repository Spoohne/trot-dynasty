"""Race engine prototype (not used by the game yet). The mile is run in half-second steps: each horse has a position,
lane, speed and energy; each step its driver picks a move from its style, its instruction and what is around it;
speed costs energy, racing without cover costs more, a wide trip covers more ground on the turns, a boxed horse
can't go faster than the horse in front of it, and a tired horse slows. The finish order is whoever crosses the
wire first. Every race returns a record (position, lane, speed, energy at each call, and the events) that a
replay can draw as it is.

Stats are the game's racing traits as current() gives them (0 is breed average): early_speed (gate speed and
acceleration), late_speed (top speed in the drive), stamina (energy and how cheaply speed is held), gait (staying
flat under pressure and taking the trip the driver asks for)."""
import math
import random

FT_MILE, LEN = 5280.0, 8.0                 # feet in a mile, in a length
DT = 0.5                                   # seconds per step
LANE_W = 7.0                               # feet between lanes: each lane out adds pi * 7 ft on a 180-degree turn
CRUISE = 46.7                              # ft/s: a 1:53 mile at an even pace
SPRINT = 54.0                              # ft/s: an average horse's flat-out speed
CALLS = (0.25, 0.5, 0.75, 1.0)             # quarter, half, three-quarters, finish
# The engine's tuning, in one place so it can be fitted: see fit_race2 in the test tools.
P = dict(
    lead_soft=0.6,        # ft/s an unchallenged leader backs the pace off
    lead_dig=2.5,         # ft/s a challenged leader picks it up
    duel_until=0.3,       # share of the mile a second leaver keeps pressing the leader
    close_up=0.9,         # ft/s a follower gains to close up behind the horse in front
    kick_late=1.6, kick_early=0.6,    # top speed per point of finish and of speed
    tank_floor=0.86, tank_full=45.0,  # top speed with an empty tank, and the energy at which the kick is whole
    cost_base=0.32, cost_over=0.08, cost_wide=0.12,   # energy per second: just racing, per (ft/s over cruise)^2, without cover
    shelter=0.5,          # share of the cost a horse pays tucked in behind another
    move_stalk=0.72, move_mid=0.6, move_late=0.74,    # where each style usually makes its move, as a share of the mile
    move_sd=0.07,
    accel=3.5, accel_early=0.8,
    break_k=0.0012,
    split=0,              # 1: energy = locomotion (all horses) + air resistance (speed cubed, cut by cover); 0 = the old rule
    air_k=0.2,            # air resistance per second at cruise speed when split is on
    mile_turns=[(0.25, 0.5), (0.75, 0.97)],   # turns on the mile track as shares of the mile (old layout: a 160 ft stretch)
    stretch_at=0.97, stretch_lanes=3,   # where the stretch fans out, and how many lanes wide it can get (3 = the old rule)
    half_turns=[(0.125, 0.25), (0.375, 0.5), (0.625, 0.75), (0.875, 0.97)],   # the half-mile track's four turns (old layout)
    half_stretch_at=0.97, half_angle_at=0.85,   # where its stretch fans out, and where a rail horse angles out for room
    profile=0,            # 1: each horse's position comes from its profile against the field, not a fixed style label
    lead_margin=0.3, gap_per_speed=5.0, gap_stamina=0.3, move_base=0.64, move_stamina=0.04,
    route=0,              # 1: drivers find a way out (angle off the rail before the box shuts; three-wide when blocked)
    route_lead=0.08,      # how far before its move point a boxed-in horse starts angling out
    budget=0,             # 1: a committed horse spends its reserve so it's empty at the wire (0 = the old rule)
    drive_all=0.75,       # share of the mile where every horse not already moving goes for home (0.75 = the old rule)
    surplus_k=0.0,        # ft/s of extra kick per full tank of energy above tank_full (0 = the old rule)       # how readily a horse breaks stride under pressure (times e^(pressure - 0.9 x manners))
    gap_stalk=1.5, gap_mid=4.0, gap_late=7.0,         # lengths behind the leader each style likes to sit
    gap_k=0.35, gap_chase=2.0, gap_give=1.5,          # ft/s per length off that gap, capped both ways
    energy=100.0, energy_stam=12.0,
    open_early=0.8,       # ft/s a non-leaver's first-eighth pace rises per point of early speed (item 96)
    driver=0,             # 1: the aim-scoring driver (drive_plan / drive_decide) picks and re-picks each horse's trip
    aim_gap=dict(top=0.5, pocket=1.2, first_over=2.5, follow=3.5, close=6.0),     # lengths behind the leader for each aim
    aim_move=dict(top=9, pocket=0.9, first_over=0.55, follow=0.62, close=0.78),    # where each aim makes its move
    pocket_open=2.0,      # ft/s over cruise a pocket-seeker leaves at, to get handy without going for the top
    spend_top=14.0,       # energy a horse will spend trying for the top (times 1 + stamina/2) before taking back
    spend_parked=10.0,    # energy spent parked without cover, not yet moving, before the driver gives up the spot
    switch_margin=0.75,   # lengths: a new aim must look this much better to switch, and then holds for hold_s
    hold_s=6.0,
    switch_place=0.3,
    gate_rollout=0,       # passes of gate rollouts: each driver runs the race forward once per aim (0 = value model only)
    rollout_dt=0.25,     # places: with the value model, a new aim must look this much better to switch
    reach_len=0.35, reach_lane=0.6,   # lengths of cost per length to gain and per lane to cross, to reach an aim mid-race
    tuck_back=0.0,        # ft/s a non-leaver eases off early when the lane inside is taken, to drop in behind (item 106)
    ease_early=0.0,       # ft/s of pace per point of early speed that costs nothing extra (0 = the old rule; item 95)
)


def half_layout(run_in=300.0, straight=800.0, arc=520.0):
    """A half-mile oval raced twice: turns as shares of the mile, the stretch start, and where a rail horse angles out.
    The start is run_in feet before the first turn, so the last turn ends straight - run_in feet before the wire."""
    lap, out, x = 2 * (straight + arc), [], run_in
    for _ in range(2):
        out += [(x / FT_MILE, (x + arc) / FT_MILE), ((x + arc + straight) / FT_MILE, (x + 2 * arc + straight) / FT_MILE)]
        x += lap
    assert abs(out[-1][1] * FT_MILE + straight - run_in - FT_MILE) < 1e-6
    return dict(half_turns=out, half_stretch_at=out[-1][1], half_angle_at=out[-1][1] - 0.025)


def turns(track):
    """(start, end) of each turn as a share of the mile. A mile track: two turns; a half-mile track: four."""
    if track == "half":
        return P["half_turns"]
    return P["mile_turns"]


class Runner:
    def __init__(self, name, stats, style, post, instr=None):
        self.name, self.s, self.style, self.post = name, stats, style, post
        self.instr = instr or {}                          # e.g. {"leave": True, "move_at": 0.4, "follow": True, "pull": False}
        self.pos = -0.05 * LEN * (post - 1)               # a moving start: the field side by side behind the gate car, post 1 on the rail
        self.lane = post - 1
        self.v = CRUISE * 0.9
        self.energy = P["energy"] + P["energy_stam"] * stats["stamina"]
        self.ground = 0.0                                 # extra feet travelled wide
        self.broke = 0.0                                  # seconds left off stride
        self.done, self.time = False, None
        self.moving = False                               # committed to a move
        self.boxed_t = 0.0
        self.shelter_t = 0.0
        self.log = []

    @property
    def top(self):                                        # flat-out speed now; falls away once the tank runs low
        base = SPRINT + P["kick_late"] * self.s["late_speed"] + P["kick_early"] * self.s["early_speed"]
        surplus = P["surplus_k"] * max(0.0, self.energy - P["tank_full"]) / P["tank_full"]   # a reserve beyond the full kick lifts it a little
        return base * (P["tank_floor"] + (1 - P["tank_floor"]) * min(1.0, max(0.0, self.energy) / P["tank_full"])) + surplus   # the kick is the energy saved for it


def budget_speed(h, dist):
    """The fastest speed this horse can hold over `dist` feet on the energy it has, paying the full exposed cost (no
    cover), capped by its flat-out speed now."""
    eff = 1.0 - 0.06 * h.s["stamina"]
    cost = lambda v: eff * (P["cost_base"] + P["cost_over"] * max(0.0, v - CRUISE) ** 2 + P["cost_wide"])   # per second
    lo, hi = CRUISE * 0.9, max(CRUISE, h.top)
    for _ in range(30):
        mid = (lo + hi) / 2
        if cost(mid) * dist / mid <= max(0.0, h.energy):
            lo = mid
        else:
            hi = mid
    return lo


def plan_race(field):
    """The driver's plan for each horse, from its own profile against this field (no fixed running style): go for the
    lead if it's among the quickest away (or quick enough from an inside post); otherwise sit about as far back as its
    early speed falls short of the quickest (not its rank: close fields stay close), a stayer a touch closer; move
    earlier the more stamina it has. Late speed never changes the plan, so a better finish can only help (review 9).
    Explicit instructions in h.instr still win."""
    order = sorted(field, key=lambda h: (-h.s["early_speed"], h.post))   # ties go to the inside post: one leader
    top = order[0].s["early_speed"]
    for k, h in enumerate(order):
        e, st_ = h.s["early_speed"], h.s["stamina"]
        lead = h.instr.setdefault("leave", k == 0 or (k == 1 and h.post <= 2 and top - e < P["lead_margin"]))
        h.want_gap = 0.5 if lead else max(0.8, min(9.0, P["gap_per_speed"] * (top - e) - P["gap_stamina"] * st_))
        h.instr.setdefault("move_at", 9 if lead else max(0.5, min(0.85, P["move_base"] - P["move_stamina"] * st_)))
        h.style = "front" if lead else "stalk" if h.want_gap < 2.0 else "mid" if h.want_gap < 4.5 else "late"   # for reporting only


AIMS = ("top", "pocket", "first_over", "follow", "close")
AIM_MODEL = {}            # (track, aim) -> coefficients from drive_fit: predicted lengths behind the winner


def aim_features(h, field):
    """What a driver reads before the gate: the horse's bars, its post, and the speed it's up against."""
    e = h.s["early_speed"]
    others = [o.s["early_speed"] for o in field if o is not h]
    quicker_inside = sum(1 for o in field if o is not h and o.post < h.post and o.s["early_speed"] > e - 0.1)
    return [1.0, e, h.s["late_speed"], h.s["stamina"], h.s["gait"], h.post - 1, max(others) - e, quicker_inside,
            sum(others) / len(others) - e, len(field)]


def crowd(h, aim, others):
    """How many rivals already aim for the same thing: in all, quicker away than this horse, drawn inside it."""
    same = [o for o, a in others if a == aim]
    return [len(same), sum(o.s["early_speed"] > h.s["early_speed"] - 0.1 for o in same), sum(o.post < h.post for o in same)]


def aim_scores(h, field, track, aims=None):
    """Predicted lengths behind the winner for each aim, given the rivals' aims (aims: {name: aim}; unknown ones skipped)."""
    x = aim_features(h, field)
    others = [(o, (aims or {}).get(o.name)) for o in field if o is not h]
    return {a: sum(c * v for c, v in zip(AIM_MODEL[(track, a)], x + crowd(h, a, others))) for a in AIMS if (track, a) in AIM_MODEL}


VALUE_MODEL = {}          # aim -> {"mean", "std", "coef", "b"}: predicted finish place from the race as it stands (value_fit)


def aim_state(h, field, track):
    """What a driver sees when it looks: the horse's bars and post, where it is now (share of the mile, lane, lengths off
    the leader, place in the order), what it has left, the speed it's up against, the leader's tank, cover and traffic."""
    live = [o for o in field if not o.done] or field
    lead = max(live, key=lambda o: o.pos)
    others = [o for o in field if o is not h]
    order = sorted(live, key=lambda o: -o.pos)
    e = h.s["early_speed"]
    cover_out = any(o.lane == h.lane + 1 and 0 < o.pos - h.pos < 2 * LEN for o in live)
    boxed = any(o.lane == h.lane and 0 < o.pos - h.pos < 1.4 * LEN for o in live) and any(o.lane == h.lane + 1 and abs(o.pos - h.pos) < 1.2 * LEN for o in live)
    return [e, h.s["late_speed"], h.s["stamina"], h.s["gait"], h.post - 1, max(0.0, h.pos) / FT_MILE, h.lane,
            min(15.0, (lead.pos - h.pos) / LEN), order.index(h) / max(1, len(order) - 1) if h in order else 1.0,
            (h.energy - P["energy"]) / 10, (h.v - CRUISE) / 3, max(o.s["early_speed"] for o in others) - e,
            sum(o.s["early_speed"] for o in others) / len(others) - e, (lead.energy - P["energy"]) / 10,
            float(cover_out), float(boxed), float(track == "half")]


def aim_x(h, field, track, aim, t=0.0, aims=None):
    """The value model's input for one candidate aim: what the driver sees, how crowded that aim is, and its own plan so
    far (current aim, hold time left, what this attempt has cost; all zero at the gate)."""
    x = aim_state(h, field, track)
    others = [(o, (aims or {}).get(o.name, getattr(o, "aim", None))) for o in field if o is not h]
    cur = getattr(h, "aim", None) if h.pos > 0 and getattr(h, "aim_t", None) is not None else None
    hist = [float(cur == a) for a in AIMS] + [
        max(0.0, P["hold_s"] - (t - h.aim_t)) / P["hold_s"] if cur else 0.0,
        (getattr(h, "att_e0", h.energy) - h.energy) / 10 if cur else 0.0, float(cur == aim)]
    return x + crowd(h, aim, others) + hist


def quad(x):
    return x + [x[i] * x[j] for i in range(len(x)) for j in range(i, len(x))]


def feasible(h, aim, field):
    """Aims a driver can still reach from here: the top or the pocket only from close up and not far out (a little
    looser for the aim it already has, so a horse isn't forced off its plan by a stride), and never an aim this
    horse has already spent itself on and given up."""
    if aim in getattr(h, "done_aims", ()):
        return False
    lead = max((o for o in field if not o.done), key=lambda o: o.pos, default=h)
    gap, mine = (lead.pos - h.pos) / LEN, aim == getattr(h, "aim", None)
    if aim == "top":
        return h.pos <= 0 or gap <= (2.5 if mine else 1.5)
    if aim == "pocket":
        return h.pos <= 0 or (gap <= (4.5 if mine else 3.0) and h.lane <= 1)
    return True


def aim_values(h, field, track, aims=None, t=0.0):
    """Predicted finish place for each feasible aim (lower is better)."""
    out = {}
    for a, m in VALUE_MODEL.items():
        if feasible(h, a, field):
            z = quad(aim_x(h, field, track, a, t, aims))
            out[a] = m["b"] + sum(c * (v - mu) / sd for c, v, mu, sd in zip(m["coef"], z, m["mean"], m["std"]))
    return out


def set_aim(h, aim, t, rec, why="", gain=None):
    old = getattr(h, "aim", None)
    if old == aim:
        return
    if old and why:
        h.trip.append(f"{why}: {aim.replace('_', '-')}")
        rec["events"].append((round(t, 1), h.name, f"{why}: now {aim}"))
        rec.setdefault("aim_changes", []).append(dict(t=round(t, 2), h=h.name, old=old, new=aim, why=why,
                                                      gain=None if gain is None else round(gain, 2), dwell=round(t - h.aim_t, 2)))
    h.aim, h.aim_t, h.style = aim, t, aim
    h.att_e0, h.parked_e = h.energy, 0.0             # this attempt's own budget
    h.instr["leave"] = aim == "top"
    h.want_gap = P["aim_gap"][aim]
    h.instr["move_at"] = P["aim_move"][aim]
    h.instr["follow"] = aim != "first_over"


def drive_plan(field, track, rec):
    """Before the gate: each driver scores every aim for its horse, post and field, counting who else wants the same
    spot, and takes the best. Three passes, quickest horses first, so drivers answer each other's choices: a crowded
    top sends the horse with less to gain to its next-best trip, and two who both need it duel.
    h.instr["aim"] forces an aim (no scores, events only); h.instr["start_aim"] sets the gate aim but keeps the scores."""
    aims = {}
    for h in field:
        h.trip, h.spent0, h.aim, h.parked_e, h.done_aims = [], h.energy, None, 0.0, set()
        if h.instr.get("aim"):
            aims[h.name] = h.instr["aim"]
    order = sorted(field, key=lambda h: (-h.s["early_speed"], h.post))
    for _ in range(3):
        for h in order:
            if not h.instr.get("aim"):
                sc = aim_values(h, field, track, aims) if VALUE_MODEL else aim_scores(h, field, track, aims)
                if sc:
                    aims[h.name] = min(sc, key=sc.get)
    if P["gate_rollout"] and not _ROLLING:
        gate_rollouts(field, track, aims, order)
    for h in field:
        score = aim_values if VALUE_MODEL else aim_scores
        h.scores = {} if h.instr.get("aim") else score(h, field, track, aims)
        solo = score(h, field, track, {o.name: None for o in field}) if h.scores else {}
        set_aim(h, h.instr.get("aim") or h.instr.get("start_aim") or aims.get(h.name, "follow"), 0.0, rec)
        h.aim0 = h.aim                                 # the aim at the gate, for reports
        if solo and min(solo, key=solo.get) == "top" and h.aim != "top":
            rival = next((o.name for o in order if aims.get(o.name) == "top"), "the speed")
            h.trip.append(f"Let {rival} have the top")
        else:
            h.trip.append({"top": "Sent for the top", "pocket": "Looked for the pocket", "first_over": "Planned to go first-over",
                           "follow": "Planned to follow cover", "close": "Sat back to close"}[h.aim])
    rec["trips"] = {h.name: h.trip for h in field}


_ROLLING = False


def gate_rollouts(field, track, aims, order):
    """The drivers' homework before the gate (the fields are drawn a day ahead): each, quickest first, runs the race
    forward once per aim with everyone else on their current plans, and keeps the aim that finishes best (the value
    model breaks ties). P["gate_rollout"] passes; inner races are coarse (rollout_dt) and never roll out themselves."""
    global _ROLLING
    _ROLLING = True
    try:
        for _ in range(int(P["gate_rollout"])):
            for h in order:
                if h.instr.get("aim") or h.instr.get("start_aim"):
                    continue
                tie = aim_values(h, field, track, aims) if VALUE_MODEL else {}
                best = None
                for a in AIMS:
                    g = [Runner(o.name, o.s, o.style, o.post, {k: v for k, v in o.instr.items() if k not in ("leave", "move_at", "follow")}
                                | {"start_aim": a if o is h else aims.get(o.name, "follow")}) for o in field]
                    o_, _ = run(g, track, rng=random.Random(f"rollout:{h.name}"), record=False, dt=P["rollout_dt"])
                    key = ([x.name for x in o_].index(h.name), tie.get(a, 0.0))
                    if best is None or key < best[0]:
                        best = (key, a)
                aims[h.name] = best[1]
    finally:
        _ROLLING = False


def drive_decide(h, live, P0, L0, f, t, lead, track="mile"):
    """During the race: every sixteenth of a mile, and the moment something happens, the driver asks whether the aim
    still fits. Back off when the trip costs past its limit; take a better spot when one turns up; hold a new aim a while.
    Reads the field as it stood at the start of the step and returns what to do; drive_commit does it."""
    if h.moving or f >= P["drive_all"] or not hasattr(h, "trip"):
        return None
    lane_free = lambda ln: ln >= 0 and not [o for o in live if o is not h and L0(o) == ln and abs(P0(o) - P0(h)) < 1.1 * LEN]
    cover = [o for o in live if o is not h and L0(o) == h.lane and 0 < P0(o) - P0(h) < 1.4 * LEN]
    if h.lane > 0 and not cover:                       # energy this attempt has spent parked without cover
        h.parked_e += getattr(h, "e_last", h.energy) - h.energy
    h.e_last = h.energy
    stam = 1 + 0.5 * h.s["stamina"]
    # event: cover comes by on the outside, for a horse that wants to follow it out
    if h.aim in ("follow", "close") and f >= 0.4:
        by = [o for o in live if o.moving and L0(o) == h.lane + 1 and 0 < P0(o) - P0(h) < 1.5 * LEN]
        if by and (h.aim == "follow" or f >= 0.6):
            return ("follow", by[0].name)
    # safety exits: over this attempt's spending limit (immediate, and that aim is done for this race)
    if h.aim == "top" and h is not lead and f < P["duel_until"] + 0.1 and h.att_e0 - h.energy > P["spend_top"] * stam:
        return ("quit", "pocket" if h.lane <= 1 else "follow", f"Couldn't clear {lead.name}, took back")
    if h.aim in ("pocket", "first_over", "follow") and h.lane > 0 and not cover and f > 0.15 and h.parked_e > P["spend_parked"] * stam:
        return ("quit", "close", "Parked too long, took back")
    # the periodic look (every sixteenth), or a hole opening on the inside of a horse that's parked
    sixteenth = int(f * 16) != int(getattr(h, "last_f", f) * 16)
    hole = h.lane > 0 and not cover and lane_free(h.lane - 1) and h is not lead
    h.last_f = f
    forced = not feasible(h, h.aim, live)              # the plan can't be reached any more: no hold, no margin
    if not (sixteenth or hole or forced) or (t - h.aim_t < P["hold_s"] and not forced) or not h.scores:
        return None
    gap = (P0(lead) - P0(h)) / LEN
    if VALUE_MODEL:
        v = aim_values(h, live, track, t=t)
        if not v:
            return None
        here = v.get(h.aim)
        best = min(v, key=lambda a: v[a] - (P["switch_place"] if a == h.aim else 0))
        if best != h.aim:
            return ("aim", best, "Saw a hole, dropped in" if hole and best == "pocket" else "Changed plan",
                    None if here is None else here - v[best])
        return None

    def now(a):                                        # the pre-race score plus what it costs to get there from here
        lanes = h.lane if a in ("top", "pocket") else 0
        return (h.scores[a] + P["reach_len"] * max(0.0, gap - P["aim_gap"][a]) + P["reach_lane"] * lanes
                - (P["switch_margin"] if a == h.aim else 0))
    best = min(h.scores, key=now)
    return ("aim", best, "Saw a hole, dropped in" if hole else "Changed plan", None) if best != h.aim else None


def drive_commit(h, act, t, rec):
    if not act:
        return
    if act[0] == "follow":
        h.moving = True
        h.lane += 1
        h.trip.append(f"Followed {act[1]} out")
        rec["events"].append((round(t, 1), h.name, f"followed {act[1]}'s cover"))
        rec.setdefault("aim_changes", []).append(dict(t=round(t, 2), h=h.name, old=h.aim, new="(followed cover)", why="cover", gain=None, dwell=round(t - h.aim_t, 2)))
    elif act[0] == "quit":
        h.done_aims.add(h.aim)
        set_aim(h, act[1], t, rec, act[2])
    else:
        set_aim(h, act[1], t, rec, act[2], act[3])


def run(field, track="mile", rng=None, record=True, dt=None, snap_at=None):
    """field: Runners in post order. Returns (finish order, record). Every horse decides from the field as it stood at
    the start of the step, all move together, traffic is resolved, then finishes are read."""
    DT = dt or globals()["DT"]
    rng = rng or random.Random()
    T = turns(track)
    on_turn = lambda f: any(a <= f < b for a, b in T)
    rec = {"calls": [], "events": []}
    base = rng.random()
    for h in field:
        if not hasattr(h, "rng"):
            h.rng = random.Random(f"{base}:{h.name}")
    if P["profile"]:
        plan_race(field)
    if P["driver"] and not all(hasattr(h, "trip") for h in field):   # a continuation (a saved race state) keeps its plans
        drive_plan(field, track, rec)
    stretch_at = P["stretch_at"] if track == "mile" else P["half_stretch_at"]
    angle_at = 0.85 if track == "mile" else P["half_angle_at"]
    t, call_i = 0.0, 0
    leader_pace = []
    while not all(h.done for h in field) and t < 200:
        live = [h for h in field if not h.done]
        S = {id(o): (o.pos, o.lane, o.v) for o in live}                 # the field as it stood
        solid = [o for o in live if not o.instr.get("ghost")]
        P0, L0, V0 = (lambda o: S[id(o)][0]), (lambda o: S[id(o)][1]), (lambda o: S[id(o)][2])
        order = sorted(live, key=lambda h: -P0(h))
        lead = order[0]
        if P["driver"]:                                   # every driver decides from the same picture, then all commit
            acts = [(h, drive_decide(h, live, P0, L0, P0(h) / FT_MILE, t, lead, track)) for h in order]
            for h, a in acts:
                drive_commit(h, a, t, rec)
        for h in order:
            f = P0(h) / FT_MILE
            blockers = [] if h.instr.get("clear_path") else solid
            ahead_same = [o for o in blockers if o is not h and L0(o) == h.lane and 0 < P0(o) - P0(h) < 1.4 * LEN]
            near = min((o for o in live if o is not h and L0(o) == h.lane and 0 < P0(o) - P0(h) < 6 * LEN), key=lambda o: P0(o), default=None)
            outside = [o for o in blockers if L0(o) == h.lane + 1 and abs(P0(o) - P0(h)) < 1.2 * LEN]
            cover = bool(ahead_same) and h.lane > 0
            target = CRUISE + 0.5 * h.s["early_speed"]
            # ---- the driver's choice for this step
            want_lead = h.instr.get("leave", h.style == "front")
            if f < 0.12 or (want_lead and f < P["duel_until"] and h is not lead and P0(lead) - h.pos < 1.5 * LEN):
                # leaving the gate: leavers go for the top (and a leaver alongside the leader keeps at him: a duel),
                # the rest find a spot
                target = SPRINT + 1.2 * h.s["early_speed"] if want_lead else CRUISE + (P["pocket_open"] if getattr(h, "aim", None) == "pocket" else 0) + P["open_early"] * h.s["early_speed"] - (0 if h.style == "stalk" or hasattr(h, "want_gap") else 1.5)
                if not want_lead and h.lane > 0 and P["tuck_back"] and [o for o in live if L0(o) == h.lane - 1 and abs(P0(o) - P0(h)) < 1.1 * LEN]:
                    target -= P["tuck_back"]               # can't drop in yet: ease back to tuck in behind (0 = the old rule)
            if not h.moving and f < 0.7 and h.lane > 0 and not [o for o in live if L0(o) == h.lane - 1 and abs(P0(o) - P0(h)) < 1.1 * LEN]                     and not (want_lead and h is not lead and f < P["duel_until"]):
                h.lane -= 1                                # tuck in toward the rail when there's room
            if P["route"] and not h.moving and h.lane == 0 and ahead_same and f >= 0.12                     and f >= h.instr.get("move_at", 9) - P["route_lead"] and not outside:
                h.lane = 1                                 # get off the rail while there's a gap outside, before the move
            if f >= 0.12 and f < 0.97 and not h.moving and not (want_lead and f < P["duel_until"] and h is not lead and P0(lead) - h.pos < 1.5 * LEN):
                move_at = h.instr.get("move_at")
                if move_at is None:                        # no instruction: the style's habit, with the driver's read
                    move_at = {"front": 9, "stalk": P["move_stalk"], "mid": P["move_mid"], "late": P["move_late"]}[h.style] + h.rng.gauss(0, P["move_sd"])
                    h.instr["move_at"] = move_at
                if f >= move_at and h is not lead:
                    h.moving = True
                    rec["events"].append((round(t, 1), h.name, "pulled first-over" if not [o for o in live if L0(o) == 1 and P0(o) > h.pos and P0(o) - P0(h) < 3 * LEN] else "moved out behind cover"))
                elif h is lead:
                    rivals = [o for o in live if o is not h and P0(h) - P0(o) < 1.2 * LEN and L0(o) > h.lane]
                    target = CRUISE + 0.5 * h.s["early_speed"] + (P["lead_dig"] if rivals else -P["lead_soft"])   # a challenged leader digs in; alone, he slows the pace
                else:                                      # the pace response: keep the gap your style wants to the leader, at any distance
                    want = getattr(h, "want_gap", None)
                    if want is None:
                        want = {"front": 0.5, "stalk": P["gap_stalk"], "mid": P["gap_mid"], "late": P["gap_late"]}[h.style]
                    gap = (P0(lead) - P0(h)) / LEN
                    target = V0(lead) + max(-P["gap_give"], min(P["gap_chase"], P["gap_k"] * (gap - want)))
            if h.moving or f >= P["drive_all"]:            # committed horses go from their own move point; the rest at the drive
                if h.moving and h.lane == 0 and (ahead_same or h.instr.get("pull", True)):
                    if not outside:
                        h.lane = 1                         # out to go
                if P["route"] and h.moving and h.lane == 1 and h.lane < 2:   # the outside lane is blocked just ahead: go three-wide if there's room
                    ahead_out = [o for o in blockers if o is not h and L0(o) == 1 and 0 < P0(o) - P0(h) < 1.4 * LEN and V0(o) < h.top - 1.0]
                    room3 = not [o for o in blockers if L0(o) == 2 and abs(P0(o) - P0(h)) < 1.2 * LEN]
                    if ahead_out and room3 and not (h.instr.get("follow", True) and f < 0.8):
                        h.lane = 2
                follow_cover = h.instr.get("follow", True) and h.lane >= 1 and ahead_same and f < 0.8
                target = (V0(ahead_same[0]) if follow_cover else max(SPRINT + P["kick_late"] * h.s["late_speed"] + P["kick_early"] * h.s["early_speed"], h.top))
                if P["budget"] and h.moving:               # the driver spends what's left so the horse is empty at the wire
                    vb = budget_speed(h, FT_MILE - P0(h))
                    target = V0(ahead_same[0]) if follow_cover and V0(ahead_same[0]) >= vb else vb
            if f >= angle_at and h.lane == 0 and ahead_same and not outside:
                h.lane = 1                                 # the stretch opens: angle out for room
            if h.lane == 0 and ahead_same and outside and (h.moving or f >= P["drive_all"]):
                h.boxed_t += DT                            # boxed: nowhere to go
                target = min(target, V0(ahead_same[0]))
            # rivals told to press: alongside the leader, outside, without passing
            pu = h.instr.get("press_until")
            if pu and f < pu and h is not lead:
                h.lane = max(h.lane, L0(lead) + 1)
                gap = P0(lead) - P0(h)
                target = V0(lead) + max(-1.0, min(1.0, gap / 2))
            # ---- neighbors again, now that lanes may have changed (the decision above read the start of the step)
            ahead_same = [o for o in blockers if o is not h and L0(o) == h.lane and 0 < P0(o) - P0(h) < 1.4 * LEN]
            cover = bool(ahead_same) and h.lane > 0
            if "fixed_v" in h.instr and f >= h.instr.get("fixed_until", 9):
                h.instr.pop("fixed_v"); h.instr.pop("lane_lock", None)    # the scripted part is over: the driver takes back
            if "fixed_v" in h.instr:
                target, h.lane = h.instr["fixed_v"], h.instr.get("lane_lock", h.lane)
            # ---- the horse answers (and what limits it: the request, or its ceiling right now)
            h.capped_t = getattr(h, "capped_t", 0.0) + (DT if target > h.top else 0.0)
            target = min(target, h.top)
            if h.broke > 0:
                target, h.broke = CRUISE * 0.8, h.broke - DT
            accel = P["accel"] + P["accel_early"] * h.s["early_speed"]         # ft/s per second
            h.v += max(-8.0 * DT, min(accel * DT, target - h.v))   # braking at most 8 ft/s per second
            # ---- what it costs: effort over cruise, more without cover or out in front
            over = max(0.0, h.v - CRUISE - P["ease_early"] * h.s["early_speed"])   # a quicker horse works less at the same pace
            shield = [o for o in solid if o is not h and L0(o) == h.lane and 0 < P0(o) - P0(h) < 1.4 * LEN]   # shelter: always the real field
            sheltered = bool(shield) and h is not lead and not h.instr.get("no_shelter")
            shelter = P["shelter"] if sheltered else 1.0
            h.shelter_t += DT if sheltered else 0
            eff = 1.0 - 0.06 * h.s["stamina"]
            if P["split"]:                                   # locomotion for every horse; air resistance rises with speed, and cover cuts only that
                air = P["air_k"] * (h.v / CRUISE) ** 3 * (P["shelter"] if sheltered else 1.0)
                h.energy -= DT * eff * (P["cost_base"] + P["cost_over"] * over ** 2 + air + (P["cost_wide"] if h.lane > 0 and not cover else 0))
            else:
                h.energy -= DT * eff * (P["cost_base"] * shelter + P["cost_over"] * over ** 2 * shelter + (P["cost_wide"] if h.lane > 0 and not cover else 0))
            # ---- breaking stride: pressure and a rough gait
            pressure = over / 6 + (0.4 if h.boxed_t > 0 else 0)
            if h.broke <= 0 and h.rng.random() < DT * P["break_k"] * math.exp(pressure - 0.9 * h.s["gait"]):
                h.broke = 3.0
                rec["events"].append((round(t, 1), h.name, "broke stride"))
            # ---- ground: the turns cost the wide ones
            step = h.v * DT
            if on_turn(f) and h.lane:
                extra = step * h.lane * LANE_W * math.pi / (FT_MILE * (T[0][1] - T[0][0]))
                h.ground += extra
                step -= extra
            h.pos += step
        # traffic: no horse runs through the one in front of it in its lane; it checks to that horse's speed a length back
        for h in sorted(live, key=lambda h: -h.pos):
            ahead = [o for o in live if o is not h and not o.instr.get("ghost") and o.lane == h.lane and o.pos >= h.pos and o.pos - h.pos < LEN]
            if ahead and not h.done and not h.instr.get("clear_path"):
                a = min(ahead, key=lambda o: o.pos)
                wants = h.moving or h.pos / FT_MILE >= P["drive_all"] or (h.instr.get("leave", h.style == "front") and h.pos / FT_MILE < 0.3)
                widest = P["stretch_lanes"] - 1 if h.pos / FT_MILE >= stretch_at else 2   # the stretch fans out wider than a turn allows
                room = h.lane < widest and not [o for o in live if not o.instr.get("ghost") and o.lane == h.lane + 1 and abs(o.pos - h.pos) < LEN]
                if wants and room:
                    h.lane += 1                            # swing out for room and keep going
                    continue
                if wants:
                    h.boxed_t += DT                        # wants to go, can't: boxed
                    if h.instr.get("trace"):
                        out1 = [o for o in live if o.lane == h.lane + 1 and abs(o.pos - h.pos) < LEN]
                        rec.setdefault("box_trace", []).append((round(h.pos / FT_MILE, 2), h.lane, a.style, a.moving,
                                                                [o.style for o in out1], h.lane >= 2))
                h.pos, h.v = a.pos - LEN, min(h.v, a.v)
        for a in live:                                     # two horses in one lane closer than a length: an overlap (lane changes included)
            for b in live:
                if a is not b and id(a) < id(b) and a.lane == b.lane and not a.instr.get("ghost") and not b.instr.get("ghost")                         and abs(a.pos - b.pos) < 0.95 * LEN and not (a.pos >= FT_MILE and b.pos >= FT_MILE):
                    rec["overlaps"] = rec.get("overlaps", 0) + 1
        for a in live:                                     # through another horse in its own lane: never allowed
            for b in live:
                if a is not b and L0(a) == L0(b) == a.lane == b.lane and P0(a) < P0(b) and a.pos > b.pos:
                    rec["crossings"] = rec.get("crossings", 0) + 1
        for h in live:
            if h.pos >= FT_MILE and not h.done:
                d = h.pos - P0(h)
                h.done, h.time = True, t + DT * ((FT_MILE - P0(h)) / d if d > 0 else 1)
        t += DT
        lead_f = max(h.pos for h in field) / FT_MILE
        if snap_at is not None and "snap" not in rec and lead_f >= snap_at:   # a saved race state, for continuation tests
            import copy as _copy
            rec["snap"], rec["snap_t"] = _copy.deepcopy(field), t
        if call_i < len(CALLS) - 1 and lead_f >= CALLS[call_i]:
            if record:
                rec["calls"].append({"at": CALLS[call_i], "t": round(t, 2), "horses": [
                    {"name": h.name, "behind": round((max(x.pos for x in field) - h.pos) / LEN, 1), "lane": h.lane,
                     "speed": round(h.v, 1), "energy": round(h.energy, 1)} for h in sorted(field, key=lambda h: -h.pos)]})
            call_i += 1
    order = sorted(field, key=lambda h: h.time if h.time is not None else 1e9)
    rec["finish"] = [{"name": h.name, "time": round(h.time, 2), "ground_ft": round(h.ground, 1), "energy": round(h.energy, 1),
                      "boxed_s": h.boxed_t} for h in order]
    return order, rec


def run_seq(field, track="mile", rng=None, record=True):
    """The first version: horses update one at a time within a step (kept to compare against run)."""
    rng = rng or random.Random()
    T = turns(track)
    on_turn = lambda f: any(a <= f < b for a, b in T)
    rec = {"calls": [], "events": []}
    t, call_i = 0.0, 0
    leader_pace = []
    while not all(h.done for h in field) and t < 200:
        live = [h for h in field if not h.done]
        order = sorted(live, key=lambda h: -h.pos)
        lead = order[0]
        for h in order:
            f = h.pos / FT_MILE
            ahead_same = [o for o in live if o is not h and o.lane == h.lane and 0 < o.pos - h.pos < 1.4 * LEN]
            near = min((o for o in live if o is not h and o.lane == h.lane and 0 < o.pos - h.pos < 6 * LEN), key=lambda o: o.pos, default=None)
            outside = [o for o in live if o.lane == h.lane + 1 and abs(o.pos - h.pos) < 1.2 * LEN]
            cover = bool(ahead_same) and h.lane > 0
            target = CRUISE + 0.5 * h.s["early_speed"]
            # ---- the driver's choice for this step
            want_lead = h.instr.get("leave", h.style == "front")
            if f < 0.12 or (want_lead and f < P["duel_until"] and h is not lead and lead.pos - h.pos < 1.5 * LEN):
                # leaving the gate: leavers go for the top (and a leaver alongside the leader keeps at him: a duel),
                # the rest find a spot
                target = SPRINT + 1.2 * h.s["early_speed"] if want_lead else CRUISE + 0.8 * h.s["early_speed"] - (0 if h.style == "stalk" or hasattr(h, "want_gap") else 1.5)
            if not h.moving and f < 0.7 and h.lane > 0 and not [o for o in live if o.lane == h.lane - 1 and abs(o.pos - h.pos) < 1.1 * LEN]                     and not (want_lead and h is not lead and f < P["duel_until"]):
                h.lane -= 1                                # tuck in toward the rail when there's room
            if f >= 0.12 and f < 0.97 and not h.moving and not (want_lead and f < P["duel_until"] and h is not lead and lead.pos - h.pos < 1.5 * LEN):
                move_at = h.instr.get("move_at")
                if move_at is None:                        # no instruction: the style's habit, with the driver's read
                    move_at = {"front": 9, "stalk": P["move_stalk"], "mid": P["move_mid"], "late": P["move_late"]}[h.style] + rng.gauss(0, P["move_sd"])
                    h.instr["move_at"] = move_at
                if f >= move_at and h is not lead:
                    h.moving = True
                    rec["events"].append((round(t, 1), h.name, "pulled first-over" if not [o for o in live if o.lane == 1 and o.pos > h.pos and o.pos - h.pos < 3 * LEN] else "moved out behind cover"))
                elif h is lead:
                    rivals = [o for o in live if o is not h and h.pos - o.pos < 1.2 * LEN and o.lane > h.lane]
                    target = CRUISE + 0.5 * h.s["early_speed"] + (P["lead_dig"] if rivals else -P["lead_soft"])   # a challenged leader digs in; alone, he slows the pace
                elif near is not None:                     # settle in close behind the horse in front: the trip saves ground and air
                    target = near.v + (P["close_up"] if near.pos - h.pos > 1.2 * LEN else 0.0)
            if h.moving or f >= 0.75:
                if h.moving and h.lane == 0 and (ahead_same or h.instr.get("pull", True)):
                    if not outside:
                        h.lane = 1                         # out to go
                follow_cover = h.instr.get("follow", True) and h.lane >= 1 and ahead_same and f < 0.8
                target = (ahead_same[0].v if follow_cover else SPRINT + P["kick_late"] * h.s["late_speed"] + P["kick_early"] * h.s["early_speed"])
            if f >= 0.85 and h.lane == 0 and ahead_same and not outside:
                h.lane = 1                                 # the stretch opens: angle out for room
            if h.lane == 0 and ahead_same and outside and (h.moving or f >= 0.75):
                h.boxed_t += DT                            # boxed: nowhere to go
                target = min(target, ahead_same[0].v)
            # ---- the horse answers
            target = min(target, h.top)
            if h.broke > 0:
                target, h.broke = CRUISE * 0.8, h.broke - DT
            accel = P["accel"] + P["accel_early"] * h.s["early_speed"]         # ft/s per second
            h.v += max(-4.0, min(accel * DT, target - h.v))
            # ---- what it costs: effort over cruise, more without cover or out in front
            over = max(0.0, h.v - CRUISE)
            shelter = P["shelter"] if (ahead_same and h is not lead) else 1.0
            eff = 1.0 - 0.06 * h.s["stamina"]
            h.energy -= DT * eff * (P["cost_base"] * shelter + P["cost_over"] * over ** 2 * shelter + (P["cost_wide"] if h.lane > 0 and not cover else 0))
            # ---- breaking stride: pressure and a rough gait
            pressure = over / 6 + (0.4 if h.boxed_t > 0 else 0)
            if h.broke <= 0 and rng.random() < DT * P["break_k"] * math.exp(pressure - 0.9 * h.s["gait"]):
                h.broke = 3.0
                rec["events"].append((round(t, 1), h.name, "broke stride"))
            # ---- ground: the turns cost the wide ones
            step = h.v * DT
            if on_turn(f) and h.lane:
                extra = step * h.lane * LANE_W * math.pi / (FT_MILE * (T[0][1] - T[0][0]))
                h.ground += extra
                step -= extra
            h.pos += step
            if h.pos >= FT_MILE and not h.done:
                h.done, h.time = True, t + DT * (1 - (h.pos - FT_MILE) / max(1e-6, h.v * DT))
        # traffic: no horse runs through the one in front of it in its lane; it checks to that horse's speed a length back
        for h in sorted(live, key=lambda h: -h.pos):
            ahead = [o for o in live if o is not h and o.lane == h.lane and o.pos >= h.pos and o.pos - h.pos < LEN]
            if ahead and not h.done:
                a = min(ahead, key=lambda o: o.pos)
                wants = h.moving or h.pos / FT_MILE >= 0.75 or (h.instr.get("leave", h.style == "front") and h.pos / FT_MILE < 0.3)
                room = h.lane < 2 and not [o for o in live if o.lane == h.lane + 1 and abs(o.pos - h.pos) < LEN]
                if wants and room:
                    h.lane += 1                            # swing out for room and keep going
                    continue
                if wants:
                    h.boxed_t += DT                        # wants to go, can't: boxed
                h.pos, h.v = a.pos - LEN, min(h.v, a.v)
        t += DT
        lead_f = max(h.pos for h in field) / FT_MILE
        if call_i < len(CALLS) - 1 and lead_f >= CALLS[call_i]:
            if record:
                rec["calls"].append({"at": CALLS[call_i], "t": round(t, 2), "horses": [
                    {"name": h.name, "behind": round((max(x.pos for x in field) - h.pos) / LEN, 1), "lane": h.lane,
                     "speed": round(h.v, 1), "energy": round(h.energy, 1)} for h in sorted(field, key=lambda h: -h.pos)]})
            call_i += 1
    order = sorted(field, key=lambda h: h.time if h.time is not None else 1e9)
    rec["finish"] = [{"name": h.name, "time": round(h.time, 2), "ground_ft": round(h.ground, 1), "energy": round(h.energy, 1),
                      "boxed_s": h.boxed_t} for h in order]
    return order, rec


def avg(**k):
    s = {"early_speed": 0.0, "late_speed": 0.0, "stamina": 0.0, "gait": 0.0}
    s.update(k)
    return s


if __name__ == "__main__":
    rng = random.Random(1)
    styles = ["front", "stalk", "mid", "mid", "late", "stalk", "mid", "late"]
    f = [Runner(f"H{k + 1}", avg(), styles[k], k + 1) for k in range(8)]
    order, rec = run(f, rng=rng)
    assert all(h.time and 100 < h.time < 130 for h in order), [h.time for h in order]
    print("winner", order[0].name, order[0].time, "events", rec["events"][:5])
