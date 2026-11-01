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
    budget=0,             # 1: a committed horse spends its reserve so it's empty at the wire (0 = the old rule)
    drive_all=0.75,       # share of the mile where every horse not already moving goes for home (0.75 = the old rule)
    surplus_k=0.0,        # ft/s of extra kick per full tank of energy above tank_full (0 = the old rule)       # how readily a horse breaks stride under pressure (times e^(pressure - 0.9 x manners))
    gap_stalk=1.5, gap_mid=4.0, gap_late=7.0,         # lengths behind the leader each style likes to sit
    gap_k=0.35, gap_chase=2.0, gap_give=1.5,          # ft/s per length off that gap, capped both ways
    energy=100.0, energy_stam=12.0,
)


def turns(track):
    """(start, end) of each turn as a share of the mile. A mile track: two turns; a half-mile track: four."""
    if track == "half":
        return [(0.125, 0.25), (0.375, 0.5), (0.625, 0.75), (0.875, 0.97)]
    return [(0.25, 0.5), (0.75, 0.97)]


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


def run(field, track="mile", rng=None, record=True, dt=None):
    """field: Runners in post order. Returns (finish order, record). Every horse decides from the field as it stood at
    the start of the step, all move together, traffic is resolved, then finishes are read."""
    DT = dt or globals()["DT"]
    rng = rng or random.Random()
    T = turns(track)
    on_turn = lambda f: any(a <= f < b for a, b in T)
    rec = {"calls": [], "events": []}
    t, call_i = 0.0, 0
    leader_pace = []
    while not all(h.done for h in field) and t < 200:
        live = [h for h in field if not h.done]
        S = {id(o): (o.pos, o.lane, o.v) for o in live}                 # the field as it stood
        solid = [o for o in live if not o.instr.get("ghost")]
        P0, L0, V0 = (lambda o: S[id(o)][0]), (lambda o: S[id(o)][1]), (lambda o: S[id(o)][2])
        order = sorted(live, key=lambda h: -P0(h))
        lead = order[0]
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
                target = SPRINT + 1.2 * h.s["early_speed"] if want_lead else CRUISE + 0.8 * h.s["early_speed"] - (0 if h.style == "stalk" else 1.5)
            if not h.moving and f < 0.7 and h.lane > 0 and not [o for o in live if L0(o) == h.lane - 1 and abs(P0(o) - P0(h)) < 1.1 * LEN]                     and not (want_lead and h is not lead and f < P["duel_until"]):
                h.lane -= 1                                # tuck in toward the rail when there's room
            if f >= 0.12 and f < 0.97 and not h.moving and not (want_lead and f < P["duel_until"] and h is not lead and P0(lead) - h.pos < 1.5 * LEN):
                move_at = h.instr.get("move_at")
                if move_at is None:                        # no instruction: the style's habit, with the driver's read
                    move_at = {"front": 9, "stalk": P["move_stalk"], "mid": P["move_mid"], "late": P["move_late"]}[h.style] + rng.gauss(0, P["move_sd"])
                    h.instr["move_at"] = move_at
                if f >= move_at and h is not lead:
                    h.moving = True
                    rec["events"].append((round(t, 1), h.name, "pulled first-over" if not [o for o in live if L0(o) == 1 and P0(o) > h.pos and P0(o) - P0(h) < 3 * LEN] else "moved out behind cover"))
                elif h is lead:
                    rivals = [o for o in live if o is not h and P0(h) - P0(o) < 1.2 * LEN and L0(o) > h.lane]
                    target = CRUISE + 0.5 * h.s["early_speed"] + (P["lead_dig"] if rivals else -P["lead_soft"])   # a challenged leader digs in; alone, he slows the pace
                else:                                      # the pace response: keep the gap your style wants to the leader, at any distance
                    want = {"front": 0.5, "stalk": P["gap_stalk"], "mid": P["gap_mid"], "late": P["gap_late"]}[h.style]
                    gap = (P0(lead) - P0(h)) / LEN
                    target = V0(lead) + max(-P["gap_give"], min(P["gap_chase"], P["gap_k"] * (gap - want)))
            if h.moving or f >= P["drive_all"]:            # committed horses go from their own move point; the rest at the drive
                if h.moving and h.lane == 0 and (ahead_same or h.instr.get("pull", True)):
                    if not outside:
                        h.lane = 1                         # out to go
                follow_cover = h.instr.get("follow", True) and h.lane >= 1 and ahead_same and f < 0.8
                target = (V0(ahead_same[0]) if follow_cover else SPRINT + P["kick_late"] * h.s["late_speed"] + P["kick_early"] * h.s["early_speed"])
                if P["budget"] and h.moving:               # the driver spends what's left so the horse is empty at the wire
                    vb = budget_speed(h, FT_MILE - P0(h))
                    target = V0(ahead_same[0]) if follow_cover and V0(ahead_same[0]) >= vb else vb
            if f >= 0.85 and h.lane == 0 and ahead_same and not outside:
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
            # ---- the horse answers
            target = min(target, h.top)
            if h.broke > 0:
                target, h.broke = CRUISE * 0.8, h.broke - DT
            accel = P["accel"] + P["accel_early"] * h.s["early_speed"]         # ft/s per second
            h.v += max(-8.0 * DT, min(accel * DT, target - h.v))   # braking at most 8 ft/s per second
            # ---- what it costs: effort over cruise, more without cover or out in front
            over = max(0.0, h.v - CRUISE)
            sheltered = bool(ahead_same) and h is not lead and not h.instr.get("no_shelter")
            shelter = P["shelter"] if sheltered else 1.0
            h.shelter_t += DT if sheltered else 0
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
        # traffic: no horse runs through the one in front of it in its lane; it checks to that horse's speed a length back
        for h in sorted(live, key=lambda h: -h.pos):
            ahead = [o for o in live if o is not h and not o.instr.get("ghost") and o.lane == h.lane and o.pos >= h.pos and o.pos - h.pos < LEN]
            if ahead and not h.done and not h.instr.get("clear_path"):
                a = min(ahead, key=lambda o: o.pos)
                wants = h.moving or h.pos / FT_MILE >= P["drive_all"] or (h.instr.get("leave", h.style == "front") and h.pos / FT_MILE < 0.3)
                room = h.lane < 2 and not [o for o in live if not o.instr.get("ghost") and o.lane == h.lane + 1 and abs(o.pos - h.pos) < LEN]
                if wants and room:
                    h.lane += 1                            # swing out for room and keep going
                    continue
                if wants:
                    h.boxed_t += DT                        # wants to go, can't: boxed
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
                target = SPRINT + 1.2 * h.s["early_speed"] if want_lead else CRUISE + 0.8 * h.s["early_speed"] - (0 if h.style == "stalk" else 1.5)
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
