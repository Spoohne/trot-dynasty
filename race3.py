"""Race engine v3 (lab; not used by the game). Built to research/engine_lab/ENGINE_SPEC.md and DESIGN_V3.md (§11 rules).
The actual horses race each other: every step each driver sets a pace and a line, the safety layer resolves every move
together so no body ever touches another, and each horse's power balance decides what it can do. Nothing here knows a
target percentage, and no horse gets a bonus or penalty for its post.

Units: feet, seconds. s = feet along the rail from the start (finish at 5,280); y = feet from the rail to the body's
center; v = physical forward speed. On an arc of radius R a horse at y gains ds = v dt / (1 + y/R).
Traits (0 = breed average, spread about 0.4): gate, cruise, kick, manners, grit; each has one job (DESIGN §3, §11.4)."""
import math
import random

FT_MILE = 5280.0
DT = 0.125
LENGTH = 8.0            # a "length" in results and calls
BODY_L = 14.0           # horse plus sulky, nose to wheel
BODY_W = 5.0            # the body's width; lanes are 7 ft apart, the rail line is y = 3
LANE = 7.0
RAIL_Y = 3.0
HEAD = 1.0              # least clear space nose-to-wheel behind another body
T_REACT = 0.03          # s: drivers anticipate, so a line sits nearly nose to sulky (DECISIONS 198; was 0.1)
BRAKE = 8.0             # ft/s^2: the most any horse slows, for any reason (breaks included); followers count on it
EASE = 4.0              # ft/s^2: the most a driver slows by choice; only the safe-following rule brakes harder (DECISIONS 197)
VY_MAX, AY_MAX = 4.0, 4.0   # lateral speed and acceleration: a lane in about 2 s, a few strides

# The power balance (DESIGN §11.4). Demand per second, in units of an average horse's sustainable power:
#   locomotion C_LOC*v  +  air C_AIR*v^3 (cut to DRAFT when tucked behind)  +  acceleration C_ACC*a*v  (+ a duel's extra)
C_LOC, C_AIR, C_ACC, DRAFT = 0.7 / 46.7, 0.3 / 46.7 ** 3, 0.0031, 0.65   # DRAFT: share of air a covered horse pays (DECISIONS 148)
P = dict(
    form_sd=0.33,         # race-day form: one draw per horse per race added to gate, cruise and kick (fitted to CONTRACTS 6-7)
    pace_k=1.094,         # scales all of demand: sets the clock (fitted to the live game's winning times, stage 3)
    c_turn=0.00034,       # cost of holding a curve (fitted so the half-mile's tight turns are slower than the mile's)
    p_cruise=0.05,        # sustainable power per point of cruise
    v_top=54.0, k_kick=3.5,                     # drive ceiling, and per point of kick
    a0=3.5, a_gate=1.0, burst_gate=1.0, launch_ft=700.0,   # launch: acceleration and a fading early burst from gate
    e_max=18.0, recover=0.3,                    # reserve (sustainable-power seconds) and how fast it refills below
    fade=0.15,            # how the ceiling falls as the reserve empties: (E/e_max)^fade (0.5 = sqrt; lower holds it up longer)
    duel=0.25, k_grit=0.85,                      # a duel's extra cost, and the share of it grit takes off per point
    break_b0=0.000025, break_effort=2.5, break_traffic=0.8, break_manners=2.9,  # breaks per second at average pressure; fitted to the manners curve (DECISIONS 163)
)


class Track:
    """A one-lap oval as a list of (kind, length_ft, radius_ft), started at run_in feet before the first turn."""

    def __init__(self, name, straight, arc, run_in, width_lanes_turn=3, width_lanes_stretch=5):
        self.name, self.R = name, arc / math.pi
        self.lap = 2 * (straight + arc)
        self.turn_w, self.stretch_w = width_lanes_turn, width_lanes_stretch
        self.passing = True                                   # a stretch passing lane (Patrick, 2026-11-01)
        s, ends = 0.0, []
        while s < FT_MILE:
            for i, (ln, kind) in enumerate([(run_in, 0), (arc, 1), (straight, 0), (arc, 1), (straight - run_in, 0)]):
                if kind:
                    ends.append((s, s + ln))
                s += ln
                if s >= FT_MILE:
                    break
        self.arcs = [(a, b) for a, b in ends if a < FT_MILE]
        self.last_turn_end = max(b for a, b in self.arcs if b <= FT_MILE)

    def kappa(self, s):
        return 1.0 / self.R if any(a <= s < b for a, b in self.arcs) else 0.0

    def path(self, s1, s2, y):
        """Feet travelled from rail position s1 to s2 by a horse holding y out from the rail: the straight part plus
        (R + y)/R on the turns. Following gaps are measured this way, in real feet along the follower's own path."""
        arc = sum(max(0.0, min(b, s2) - max(a, s1)) for a, b in self.arcs)
        return (s2 - s1) + arc * y / self.R

    def advance(self, s, d, y):
        """Rail position after travelling d real feet along the line y from rail position s (the inverse of path), split
        exactly at turn boundaries so a horse crossing one mid-step isn't carried too far."""
        while d > 1e-9:
            arc = next(((a, b) for a, b in self.arcs if a <= s < b), None)
            k = self.R / (self.R + y) if arc else 1.0
            end = arc[1] if arc else min((a for a, b in self.arcs if a > s), default=1e18)
            room = (end - s) / k                              # real feet to the next boundary
            if d <= room:
                return s + d * k
            s, d = end, d - room
        return s

    def on_turn(self, s):
        return any(a <= s < b for a, b in self.arcs)

    def min_y(self, s):
        """The passing lane (DECISIONS 183): in the stretch a lane opens inside the rail line, for passing only."""
        return RAIL_Y - LANE if self.passing and self.last_turn_end <= s < FT_MILE else RAIL_Y

    def max_y(self, s):
        lanes = self.stretch_w if s >= self.last_turn_end else self.turn_w + 1   # turns: up to four-wide physically
        return RAIL_Y + LANE * (lanes - 1)


HALF = Track("half", 800.0, 520.0, 300.0)
MILE = Track("mile", 1320.0, 1320.0, 320.0)
TRACKS = {"half": HALF, "mile": MILE}


def demand(v, a, draft, duel_extra=0.0, curv=0.0):
    """curv = 1 / (R + y) on a turn: holding a curve costs in proportion to v * v^2/r (a tight turn costs more)."""
    return P["pace_k"] * (C_LOC * v + C_AIR * v ** 3 * (DRAFT if draft else 1.0) + C_ACC * max(0.0, a) * v
                          + P["c_turn"] * v ** 3 * curv) + duel_extra


def duel_extra(h, v):
    return P["duel"] * max(0.0, 1.0 - P["k_grit"] * h.t["grit"]) * C_LOC * v * P["pace_k"]


_HELD = {}


def held_speed(h, duel=None):
    """The steady speed this horse can hold forever in its present conditions: its sustainable power against the
    demand of this turn, this cover and this duel (review 14: an empty tank can't keep paying a turn).
    duel=False: the same without the duel (a driver's pace target; the duel is still paid, review 17)."""
    duel = h.duel if duel is None else duel
    key = (round(h.p_sus, 4), bool(h.draft), bool(duel), round(h.t["grit"], 3) if duel else None, round(h.curv, 6))
    if key not in _HELD:
        lo, hi = 10.0, 70.0
        for _ in range(30):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if demand(mid, 0, h.draft, duel_extra(h, mid) if duel else 0.0, h.curv) < h.p_sus else (lo, mid)
        _HELD[key] = lo
    return _HELD[key]


def afford_speed(h, track, margin):
    """The fastest steady speed this horse can hold from here to the wire on its reserve (DECISIONS 201, Patrick: every
    driver knows what's in the tank and times it to run out at the wire or a little before). It spends at most
    E - margin over the distance left, at the remaining turns' average curvature and its present cover, and never
    above the ceiling it will have when the reserve is down to the margin, so it isn't slowing at the line."""
    D = max(1.0, FT_MILE - h.s)
    arc = sum(max(0.0, min(b, FT_MILE) - max(a, h.s)) for a, b in track.arcs)
    curv = arc / D / (track.R + h.y)
    top = P["v_top"] + P["k_kick"] * h.t["kick"]
    lo, hi = 10.0, max(top, 70.0)
    for _ in range(30):                                   # the steady speed it can hold forever here: nothing spent
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if demand(mid, 0, h.draft, 0.0, curv) < h.p_sus else (lo, mid)
    floor_v = lo
    E = h.E - margin
    end_cap = floor_v + max(0.0, top - floor_v) * (max(1e-3, min(P["e_max"], margin)) / P["e_max"]) ** P["fade"]
    if E <= 0:
        return floor_v
    a_, b_ = floor_v, max(floor_v, min(top, end_cap))
    for _ in range(18):
        mid = (a_ + b_) / 2
        if (demand(mid, 0, h.draft, 0.0, curv) - h.p_sus) * D / mid <= E:
            a_ = mid
        else:
            b_ = mid
    return a_


def sus_speed(p_sus, draft=False):
    """The pace a horse can hold forever at steady speed (demand = sustainable power)."""
    lo, hi = 20.0, 70.0
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if demand(mid, 0, draft) < p_sus else (lo, mid)
    return lo


class Horse:
    def __init__(self, name, traits, post, track, cmd=None):
        self.name, self.t, self.post = name, dict(dict(gate=0.0, cruise=0.0, kick=0.0, manners=0.0, grit=0.0), **traits), post
        self.s = 0.0                                         # the gate: side by side, noses level
        self.y = RAIL_Y + LANE * (post - 1)
        self.v, self.vy, self.a = 44.0, 0.0, 0.0
        self.man = None                                      # a committed lane change: from, dest, when (review 15)
        self.req, self.why_not = None, ""                    # a lane change asked for (since, dest), and why it's waiting
        self.draft = self.duel = self.blocked = False
        self.curv = 0.0
        self.p_sus = 1.0 + P["p_cruise"] * self.t["cruise"]
        self.v_sus = sus_speed(self.p_sus)
        self.E = P["e_max"]
        self.broke = 0.0
        self.done, self.time = False, None
        self.cmd = cmd or {}                                 # driver's targets: v (pace), y (line); set each step
        self.log = []

    def ceiling(self):
        """Top speed right now: the drive ceiling, faded smoothly by an emptying reserve, plus the fading launch burst."""
        top = P["v_top"] + P["k_kick"] * self.t["kick"]
        w = max(0.0, 1.0 - max(0.0, self.s) / P["launch_ft"])
        top += P["burst_gate"] * self.t["gate"] * w
        floor = held_speed(self)                              # what it can sustain right here (turn, cover, duel)
        return floor + max(0.0, top - floor) * (max(0.0, self.E) / P["e_max"]) ** P["fade"]

    def accel_cap(self):
        w = max(0.0, 1.0 - max(0.0, self.s) / P["launch_ft"])
        return P["a0"] + P["a_gate"] * self.t["gate"] * w


Y_PAD = 0.3              # side clearance counted as touching, the same in every check
LOOK_V = 1.0             # ft/s: the driver plans gaps with room for one horse to speed up and the other to slow
COMMIT_MARGIN = 0.5      # ft: extra room a lane change needs behind it when it commits
RUNOUT = 400.0           # ft past the wire finished horses stay on the track, pulling up


def body_overlap_y(y1, y2, pad=Y_PAD):
    return abs(y1 - y2) < BODY_W + pad


def occ(h):
    """The sideways band a horse holds: its body, or, during a committed lane change, the whole way from where it
    started to where it's going (both lanes stay reserved until it's done; review 15)."""
    lo = hi = h.y
    if h.man:
        lo, hi = min(h.y, h.man["from"], h.man["dest"]), max(h.y, h.man["from"], h.man["dest"])
    return lo - BODY_W / 2 - Y_PAD / 2, hi + BODY_W / 2 + Y_PAD / 2


def bands_overlap(p, q):
    return p[0] < q[1] - 1e-9 and q[0] < p[1] - 1e-9


def need_gap(v_back, v_front, brake=BRAKE):
    """Clear space a horse needs behind another so that, if the one ahead slows as hard as any horse can, it can too
    after reacting: HEAD + v T_REACT + max(0, (v_back^2 - v_front^2) / (2 brake))."""
    return HEAD + v_back * T_REACT + max(0.0, (v_back ** 2 - v_front ** 2) / (2 * brake)) + STEP_ALLOW


def merge_gap(v_back, v_front):
    """The gap a driver plans for when it wants to change lanes: the following gap with a little room for one horse
    to speed up and the other to slow (the commit check itself is commit_ok)."""
    return need_gap(v_back + LOOK_V, max(0.0, v_front - LOOK_V)) + COMMIT_MARGIN


BREACH_TOL = 0.02         # ft/s: floating-point slack when a braking chain sits exactly on the limit (real squeezes were 0.1+)
STEP_ALLOW = 0.5          # ft: covers stepping in DT-sized steps when two horses brake in a chain at the limit


def safe_speed(gap, u_lead, dt, brake=BRAKE):
    """The most a horse can do next step (in feet of rail per second) and still have need_gap behind the horse
    ahead; gap is measured to where that horse will be at the end of the step."""
    b = T_REACT + dt
    u = (gap - HEAD - STEP_ALLOW) / b                     # the case u <= u_lead
    if u <= u_lead:
        return max(0.0, u)
    a, c = 1 / (2 * brake), HEAD + STEP_ALLOW - u_lead ** 2 / (2 * brake) - gap
    disc = b * b - 4 * a * c
    return max(u_lead, (-b + math.sqrt(max(0.0, disc))) / (2 * a))


def wide_y(a, b):
    """The line a gap between two horses is measured on: the widest either holds or is committed to. It stays put
    while one of them changes lanes, so a lane change on a turn can't make the gap seem to shrink."""
    ys = [a.y, b.y] + [v for h in (a, b) if h.man for v in (h.man["from"], h.man["dest"])]
    return max(ys)


TURN_LOOK = 300.0        # ft before a turn a follower starts allowing for a wider horse ahead losing rail ground


def turn_weight(track, s):
    """1 on a turn, rising smoothly from 0 over the TURN_LOOK feet before one, 0 elsewhere (so nothing jumps)."""
    if track.on_turn(s):
        return 1.0
    d = min((a - s for a, b in track.arcs if a >= s), default=1e9)
    return max(0.0, 1.0 - d / TURN_LOOK)


def follow(track, h, o, h_dest=None, o_y=None):
    """(clear gap, lead speed) for h following o, in real feet along the innermost line h holds or is committed to.
    That line stays put through an inward lane change, so the measure never slides (moving in on a turn really does
    gain ground: measuring on the inner line counts that gain from the moment the move is committed). A wider horse
    ahead covers less of that line on a turn, so its speed is taken in that frame, phased in over the TURN_LOOK feet
    before the turn so it never jumps."""
    dest = h_dest if h_dest is not None else (h.man["dest"] if h.man else h.y)
    y_m = min(h.y, dest)
    gap = track.path(h.s, o.s, y_m) - BODY_L
    v_lead = o.v
    y_o = o_y if o_y is not None else (max(o.y, o.man["dest"]) if o.man else o.y)   # a horse moving out: judged on where it's going
    if y_o > y_m:
        ke = turn_weight(track, o.s) / track.R
        v_lead = o.v * (1 + ke * y_m) / (1 + ke * y_o)
    return gap, v_lead


def follow_gap(track, h, o):
    return follow(track, h, o)[0]


def man_time(dy):
    """Seconds a lane change of dy feet takes with the lateral speed and acceleration limits."""
    d = abs(dy)
    ramp = VY_MAX ** 2 / AY_MAX
    return 2 * math.sqrt(d / AY_MAX) if d <= ramp else d / VY_MAX + VY_MAX / AY_MAX


def commit_ok(h, dest, live, track, kf):
    """May this lane change start now? Everyone it will share a band with must already be in a safe following order
    with it (nobody alongside); then the reservation keeps it safe, because each of them follows the band from now
    on. In the stretch an inward move may not make a rival brake to give it room (rule 0.21)."""
    if dest > h.y and (dest > track.max_y(h.s) + 1e-6 or dest > track.max_y(h.s + h.v * man_time(dest - h.y)) + 1e-6):
        return False, "too wide here"                    # only moves outward are limited by width
    if dest < h.y and dest < track.min_y(h.s) - 1e-6:
        return False, "no passing lane here"
    corridor = (min(h.y, dest) - BODY_W / 2 - Y_PAD / 2, max(h.y, dest) + BODY_W / 2 + Y_PAD / 2)
    mine = occ(h)
    inward = dest < h.y
    for o in live:
        if o is h or not bands_overlap(occ(o), corridor):
            continue
        ds = o.s - h.s
        if bands_overlap(occ(o), mine) and abs(ds) >= BODY_L:
            if ds > 0:                                    # ahead in its own lane: the gap is re-measured on the new line
                gap, vl = follow(track, h, o, dest)
                if gap < need_gap(h.v, vl):
                    return False, f"too close behind {o.name} for the new line"
            if ds < 0 and dest > h.y:                     # behind it in its own lane, and it's moving out: re-judged too
                gap, vl = follow(track, o, h, o_y=dest)
                if gap < need_gap(o.v, vl):
                    return False, f"{o.name} too close behind for the new line"
            continue
        if abs(ds) < BODY_L + HEAD:
            return False, f"{o.name} alongside"
        if ds > 0:                                        # it will follow o: the same rule the forward pass uses
            gap, vl = follow(track, h, o, dest)
            if gap < need_gap(h.v, vl) + COMMIT_MARGIN:
                return False, f"too close behind {o.name}"
        else:                                             # o will follow it, judging it on the line it's heading for
            gap, vl = follow(track, o, h, o_y=max(h.y, dest))
            if gap < need_gap(o.v, vl) + COMMIT_MARGIN:
                return False, f"no room in front of {o.name}"
            if inward and h.s >= track.last_turn_end and not o.done and gap - max(0.0, o.v - vl) * man_time(dest - h.y) < need_gap(o.v, vl):
                return False, f"would cut off {o.name}"
    return True, ""


def step(field, track, t, dt, rng_of, rec):
    """One step (review 15): lane changes are asked for, then committed only when everyone in the new lane is in a
    safe following order with the horse; a committed change keeps both lanes reserved and is carried through.
    Then forward speeds front to back on one snapshot, in feet of rail per second, under the safe-following rule and
    the braking limit (a breach is logged as a hard failure). Then the power balance, breaks and finishes.
    Finished horses stay on the track (pulling up) until RUNOUT feet past the wire."""
    live = [h for h in field if h.s < FT_MILE + RUNOUT]
    racing = [h for h in live if not h.done]
    kf = {h.name: 1.0 / (1.0 + track.kappa(h.s) * h.y) for h in live}
    # ---- requests: the next lane toward the driver's line; the oldest request is looked at first
    for h in live:
        want = max(min(track.min_y(h.s), h.y), min(max(track.max_y(h.s), h.y), h.cmd.get("y", h.y)))
        nxt = None
        if h.man is None and abs(want - h.y) > 0.3 and h.broke <= 0:
            nxt = h.y + max(-LANE, min(LANE, want - h.y))
            if abs(want - h.y) > LANE + 0.3:
                nxt = RAIL_Y + LANE * round((nxt - RAIL_Y) / LANE)
        if nxt is None or h.req is None or abs(h.req[1] - nxt) > 0.3:
            h.req = (t, nxt) if nxt is not None else None    # a new or changed request starts its clock again
    for h in sorted((h for h in live if h.req), key=lambda h: (h.req[0], -h.s, h.name)):
        ok, why = commit_ok(h, h.req[1], live, track, kf)
        if ok:
            h.man = dict(**{"from": h.y, "dest": h.req[1], "t": t})
            h.req = None
            rec.setdefault("commits", 0)
            rec["commits"] += 1
        else:
            h.why_not = why
    # ---- committed lane changes move: bounded sideways acceleration, landing on the line
    for h in live:
        if not h.man:
            if h.vy:
                h.vy = 0.0
            continue
        dist = h.man["dest"] - h.y
        sgn = (dist > 0) - (dist < 0)
        if abs(dist) <= 1e-9:
            h.man, h.vy = None, 0.0
            continue
        vy_t = sgn * min(VY_MAX, math.sqrt(2 * AY_MAX * abs(dist)))
        vy = h.vy + max(-AY_MAX * dt, min(AY_MAX * dt, vy_t - h.vy))
        if abs(vy * dt) >= abs(dist):                         # arrives this step (within the acceleration limit)
            h.y, h.vy, h.man = h.man["dest"], 0.0, None
            continue
        h.y += vy * dt
        h.vy = vy
    kf = {h.name: 1.0 / (1.0 + track.kappa(h.s) * h.y) for h in live}
    band = {h.name: occ(h) for h in live}
    s0 = {h.name: h.s for h in live}
    # ---- forward: front to back on the snapshot; who follows whom is fixed before anyone moves
    for h in sorted(live, key=lambda h: (-s0[h.name], h.name)):
        k = kf[h.name]
        cap = h.ceiling()
        target = min(h.cmd.get("v", h.v_sus), cap) if not h.done else 0.85 * h.v_sus
        if h.broke > 0:
            target = min(target, 0.75 * h.cmd.get("v_break_from", h.v))
        a_up = h.accel_cap()
        if not h.done and target > h.v:                   # speeding up costs: never more than the tank holds this step
            base = demand(h.v, 0, h.draft, duel_extra(h, h.v) if h.duel else 0.0, h.curv)
            a_up = min(a_up, max(0.0, (h.p_sus + h.E / dt - base) / (P["pace_k"] * C_ACC * max(1.0, h.v))))
        v_new = max(0.0, h.v + max(-EASE * dt, min(a_up * dt, target - h.v)))
        ahead = [o for o in live if o is not h and (s0[o.name], o.name) > (s0[h.name], h.name) and bands_overlap(band[o.name], band[h.name])]
        h.blocked = False
        if ahead:                                         # every body ahead in its band counts, not just the nearest
            vmax, o = min(((safe_speed(*follow(track, h, o), dt), o) for o in ahead), key=lambda x: x[0])
            if vmax < h.v - BRAKE * dt - BREACH_TOL:
                rec.setdefault("safety", []).append((round(t, 2), h.name, o.name, round(follow_gap(track, h, o), 2),
                                                     round(h.v - BRAKE * dt - vmax, 3)))
            v_new = max(h.v - BRAKE * dt, min(v_new, vmax), 0.0)    # never brakes harder than any horse can
            h.blocked = vmax < target - 0.5
        h.a = (v_new - h.v) / dt
        h.v = v_new
        h.s_prev = h.s
        h.s = track.advance(h.s, h.v * dt, h.y)              # exact across turn boundaries
        kf[h.name] = 1.0 / (1.0 + track.kappa(h.s) * h.y)   # followers see its rate where it now is (turn entry included)
    # ---- power balance, duels, breaks
    for h in racing:
        draft = any(o is not h and 0 < o.s - BODY_L - h.s < 1.5 * LENGTH and body_overlap_y(o.y, h.y, -1.0) for o in live)
        rival = [o for o in racing if o is not h and abs(o.s - h.s) < BODY_L * 0.6 and LANE * 0.6 < abs(o.y - h.y) < LANE * 1.4]
        duel = bool(rival) and h.v > h.v_sus and any(o.v > o.v_sus for o in rival)
        curv = 1.0 / (track.R + h.y) if track.on_turn(h.s) else 0.0
        w = demand(h.v, h.a, draft, duel_extra(h, h.v) if duel else 0.0, curv)
        h.E += (-(w - h.p_sus) if w > h.p_sus else P["recover"] * (h.p_sus - w)) * dt
        if h.E < 0:
            rec["overdraw"] = rec.get("overdraw", 0.0) - h.E    # demand beyond an empty tank (should stay ~0)
        h.E = max(0.0, min(P["e_max"], h.E))
        h.draft, h.duel, h.curv = draft, duel, curv
        if h.broke > 0:
            h.broke -= dt
            continue
        effort = h.v / max(1.0, h.ceiling())
        on_tail = any(o is not h and 0 < o.s - BODY_L - h.s < need_gap(h.v, o.v) + 2 and body_overlap_y(o.y, h.y) for o in live)
        boxed = h.blocked and any(o is not h and abs(o.s - h.s) < BODY_L and 0 < o.y - h.y < LANE + 1 for o in live)
        lam = P["break_b0"] * math.exp(P["break_effort"] * (effort - 0.9) + P["break_traffic"] * (on_tail + boxed) - P["break_manners"] * h.t["manners"])
        if rng_of(h).random() < 1 - math.exp(-lam * dt):
            h.broke = 3.5
            h.cmd["v_break_from"] = h.v
            rec["events"].append((round(t, 2), h.name, "broke stride", dict(effort=round(effort, 2), on_tail=on_tail, boxed=boxed)))
    for h in racing:
        if h.s >= FT_MILE:
            frac = (FT_MILE - h.s_prev) / max(1e-9, h.s - h.s_prev)
            h.done, h.time = True, t + dt * frac


def run(field, track_name="mile", driver=None, seed=0, dt=DT, record=True, t_max=200.0):
    """field: Horses. driver(field, track, t, rec) sets each horse's cmd every step (None = hold v_sus on its line).
    Returns (finish order, record): the record holds every step's s, y, v and the events, for the replay and audit."""
    track = TRACKS[track_name]
    rngs = {h.name: random.Random(f"{seed}:{h.name}") for h in field}
    rec = {"track": track_name, "dt": dt, "names": [h.name for h in field], "frames": [], "events": []}
    if P["form_sd"] > 0:                                     # race-day form: how each horse is going today (CONTRACTS item 7)
        rec["form"] = {}
        for h in field:
            if not hasattr(h, "t_base"):
                h.t_base = dict(h.t)
            f = random.Random(f"{seed}:{h.name}:form").gauss(0.0, P["form_sd"])
            h.t = dict(h.t_base, **{k: h.t_base[k] + f for k in ("gate", "cruise", "kick")})
            h.p_sus = 1.0 + P["p_cruise"] * h.t["cruise"]
            h.v_sus = sus_speed(h.p_sus)
            rec["form"][h.name] = round(f, 3)
    t = 0.0
    _HELD.clear()                                            # demand settings may have changed between runs
    while not all(h.done for h in field) and t < t_max:
        if driver:
            driver(field, track, t, rec)
        step(field, track, t, dt, lambda h: rngs[h.name], rec)
        t += dt
        if record:
            rec["frames"].append([(round(h.s, 1), round(h.y, 2), round(h.v, 2), round(h.E, 2), int(h.broke > 0)) for h in field])
    order = sorted(field, key=lambda h: h.time if h.time is not None else 1e9)
    rec["finish"] = [(h.name, round(h.time, 3) if h.time else None) for h in order]
    return order, rec


def to_xy(track, s, y):
    """Where a horse is on the oval (feet; the home straight runs left to right along the bottom, the race runs
    counterclockwise with the rail on the left). y is out from the rail line."""
    S = track.lap / 2 - math.pi * track.R
    A, R_ = math.pi * track.R, track.R
    u = (S - (track.arcs[0][0]) + s) % track.lap
    if u < S:
        return u, -y
    if u < S + A:
        th = (u - S) / R_
        return S + (R_ + y) * math.sin(th), R_ - (R_ + y) * math.cos(th)
    if u < 2 * S + A:
        return S - (u - S - A), 2 * R_ + y
    th = (u - 2 * S - A) / R_
    return -(R_ + y) * math.sin(th), R_ + (R_ + y) * math.cos(th)


# ---- the Part 0 auditor: reads only the record, so the replay and the audit see the same race
def audit(rec, field_names=None):
    track = TRACKS[rec["track"]]
    fr, dt = rec["frames"], rec["dt"]
    n = len(rec["names"])
    out = dict(min_gap_ft=1e9, overlaps=0, snaps=0, commits=rec.get("commits", 0), overdraw=round(rec.get("overdraw", 0.0), 2), reversals_max=0, four_wide_turn_steps=0, four_wide_gate_sorting=0, stop_dead=0,
               safety=len(rec.get("safety", [])))
    rev = [0] * n
    last_dir = [0] * n
    for k in range(1, len(fr)):
        a, b = fr[k - 1], fr[k]
        for i in range(n):
            s, y, v, E, br = b[i]
            if s >= FT_MILE + RUNOUT:
                continue
            dy = y - a[i][1]
            if abs(dy) > VY_MAX * dt + 0.02:              # the record rounds y to 0.01
                out["snaps"] += 1
            d = (dy > 0.02) - (dy < -0.02)
            if d and last_dir[i] and d != last_dir[i]:
                rev[i] += 1
            if d:
                last_dir[i] = d
            if track.on_turn(s) and y >= RAIL_Y + 3 * LANE - 0.5:
                # the one allowed reason on the first turn: still working in from the gate (moving in all the way)
                sorting = (s < track.arcs[0][1] and fr[0][i][1] >= RAIL_Y + 3 * LANE - 0.5      # Patrick's exception: an outside
                           and all(fr[m][i][1] <= fr[m - 1][i][1] + 1e-6 for m in range(1, k + 1)))  # post still working in
                out["four_wide_gate_sorting" if sorting else "four_wide_turn_steps"] += 1
            if not br and (a[i][2] - v) / dt > BRAKE + 1e-3:
                out["stop_dead"] += 1
            for j in range(i + 1, n):
                s2, y2 = b[j][0], b[j][1]
                if max(s, s2) >= FT_MILE + RUNOUT:
                    continue
                if abs(y - y2) < BODY_W - 1e-6:
                    gap = abs(s - s2) - BODY_L
                    out["min_gap_ft"] = min(out["min_gap_ft"], gap)
                    if gap < -1e-6:
                        out["overlaps"] += 1
    out["reversals_max"] = max(rev)
    out["min_gap_ft"] = round(out["min_gap_ft"], 2)
    return out


if __name__ == "__main__":
    # self-checks: geometry closes, the sustainable pace is about 1:53, and a lone horse never trips the auditor
    assert [round(b - a) for a, b in HALF.arcs] == [520] * 4 and round(FT_MILE - HALF.last_turn_end) == 500
    assert [round(b - a) for a, b in MILE.arcs] == [1320] * 2 and round(FT_MILE - MILE.last_turn_end) == 1000
    h = Horse("A", {}, 1, MILE)
    assert 45.4 < h.v_sus < 46.3, h.v_sus      # the fitted clock (pace_k 1.03): an average horse holds about 45.8 ft/s
    o, rec = run([h], "mile")
    print("lone average horse at its sustainable pace:", rec["finish"], audit(rec))
