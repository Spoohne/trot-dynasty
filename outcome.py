"""The outcome engine (engine lab DECISIONS 204-237): who wins a race, decided by the fitted outcome model, with the
same contract as sim.race so race night, ratings, the story and the replay keep working unchanged.

Each horse's racing stats (training, freshness, the Post Time Tonic and the driver's touch, as sim.race uses them)
become the big-four bars on the live pip scale, then model units at K per bar (live fields differ by about 1.1 bars a
stat; the model was fitted on fields differing by 0.4 units). In the order they leave the gate, drivers choose trips
(lead, pocket, first-over, following cover, the line); performance decides the order and the margins.

Off unless TD_ENGINE=outcome (circuit.run_race); this module changes nothing on its own."""
import bisect, math, random

import sim

K = 0.36                     # model units per bar (0.4 / 1.1)
PIP_STEPS = (-3.33, -2.5, -1.67, -0.83, 0.0, 0.83, 1.67, 3.7, 12.5)  # the bar scale: a full bar is the best in the world (the breed's top is
MANNERS_STEPS = (-3.33, -2.5, -1.67, -0.83, 0.0, 0.83, 1.67, 3.7, 6.0)   # ~12; Patrick 2026-11-03, was 6.0). Manners keeps its own: a perfect trip fills it
GRIT_POP = dict(dur=(0.17, 1.424), gait=(0.09, 1.274), raw_sd=1.479, bar=(5.38, 1.58))   # live save 2026-11-02 (v6_convert)
SEC_PER_LENGTH = 0.2         # the replay's own conversion (a length is a fifth of a second)
LUCK = 1.0                    # seconds: the best night a horse can have, beyond its rating's time (two night-swings)
NOSE = 0.05                   # lengths: the least one finisher is behind another
EASED = 6.0                   # lengths: a horse beaten by more is eased home, and its margin grows by the log past here (the honest clock's tail)
RATE_W = dict(gate=.242, cruise=.304, kick=.391, grit=.064)   # the rating: bars weighted by worth (DECISIONS 217/224)
TIME_FIT = (130.94, -2.733)  # mile seconds = a + b * rating: today's racing horses 3+ (n 660, r -0.93, resid 1.2 s)
# Speed sets the clock (Patrick, 2026-11-02: "speed being the thing that directly correlates to how fast a horse can finish;
# the rest of the bars are how often and how well it gets to that finish"). A horse's fastest mile comes from its Speed bar
# (kick), slowed by STAY seconds for each point its Speed outruns its Stamina (it can't hold its top end a mile). Fitted on
# today's racing horses 3+ so times keep their spread (n 660; the time tracks Speed at r 0.97, the old rating time at 0.90).
SPEED_FIT, STAY = (128.26, -2.307), 0.8
WITHIN = 0.1                 # inside one field, ceilings spread on the race model's slope, not the clock's (RaceGod V4: 1.2 L a bar vs 11.5)
ROLES = ("lead", "pocket", "first_over", "followed", "back")
DUEL, P_NONE, N_FOLLOW, BREAK = 0.15, 0.10, 2, 3.0
FO_MAX = {"half": 4, "mile": 5}
P = {   # research/engine_lab/v4/fit_half.json, fit_mile.json (DECISIONS 224 refit); c_post, A_lead, A_pocket, A_fol retuned on real fields (RaceGod V9 candidate B, 2026-11-02)
    # The trips worth little (Patrick 2026-11-03: a trip is variety, never an advantage; a marginally better horse must not lose
    # by nine lengths): the role worths, the closer's kick, the line's depth and the night's form cut to a tenth or so of the
    # fitted values (research/engine_lab/retune_lab.py measured each step; the fitted values are in git before this commit).
    "half": dict(g=0.25, s_form=0.06, s_choice=0.1, c_post=0.12, s_start=0.02017397059465198,
                 omega=0.5938761916108407, A_lead=0.25, A_pocket=0.15, A_fo=0.05,
                 A_fol=0.15, s_eps=0.17798810007780796, s_margin=7.605805514239352, k_close=0.04303554691830236,
                 b_depth=0.06),
    "mile": dict(g=0.25, s_form=0.06, s_choice=0.1, c_post=0.20, s_start=0.8370432667346848,
                 omega=0.4703087097212123, A_lead=0.25, A_pocket=0.15, A_fo=0.05,
                 A_fol=0.15, s_eps=0.027295459447580828, s_margin=6.0407761172731735, k_close=0.10,
                 b_depth=0.06),
}
rng = random.Random()


def bar(v, gait=False):
    """A live stat on the live pip scale, made continuous (1 to 10). Manners tops out at a perfect trip (sim.GAIT_CAP)."""
    if gait and v > MANNERS_STEPS[5]:
        v = min(MANNERS_STEPS[-1], MANNERS_STEPS[5] + (v - MANNERS_STEPS[5]) * (MANNERS_STEPS[-1] - MANNERS_STEPS[5]) / (sim.GAIT_CAP - MANNERS_STEPS[5]))
    xs = (-4.17,) + (MANNERS_STEPS if gait else PIP_STEPS)
    if v <= xs[0]:
        return 1.0
    if v >= xs[-1]:
        return 10.0
    k = bisect.bisect_right(xs, v) - 1
    return 1 + k + (v - xs[k]) / (xs[k + 1] - xs[k])


def grit_bar(h):
    """Grit, seeded from the horse's toughness genes (durability and gait potential), on the stamina bars' spread."""
    (dm, ds), (gm, gs) = GRIT_POP["dur"], GRIT_POP["gait"]
    z = ((h.potential["durability"] - dm) / ds + (h.potential["gait"] - gm) / gs) / GRIT_POP["raw_sd"]
    mu, sd = GRIT_POP["bar"]
    return max(1.0, min(10.0, mu + sd * z))


def bars(h, stats):
    return dict(gate=bar(stats["early_speed"]), cruise=bar(stats["stamina"]), kick=bar(stats["late_speed"]),
                manners=bar(stats["gait"], gait=True), grit=getattr(h, "grit_bar", None) or grit_bar(h))


def best_mile(b, half=False):
    """A horse's own mile on a clean night, in display seconds: its Speed (kick) sets it, less what its Stamina can't hold."""
    return SPEED_FIT[0] + SPEED_FIT[1] * b["kick"] + STAY * max(0.0, b["kick"] - b["cruise"]) + (sim.HALF_SLOWER if half else 0)


# Ratings v2 (research/engine_lab/RATINGS_V2.md): the clock can't rate a beaten horse (inside a field a bar is worth a fifth of a
# second, between fields two: a loser's time is mostly the winner's class), so a start's figure is read off the ledger instead:
# the model's performance with the trip taken out (the role's worth, the line's depth, a closer's extra kick), in mile seconds
# on the clock's own scale. FIG_FIT maps the model's class units (omega * cruise + (1 - omega) * kick, at K per bar) onto best_mile
# over today's horses, so an unraced horse's predicted mile and a raced horse's figures are one ruler.
FIG_FIT = {"mile": (116.968, -6.409), "half": (116.841, -6.106)}   # a + b * units: live save 2026-11-03, 777 horses 2+ (r -0.96 mile, -0.92 half)
FORM_TELL = 1.3                                       # sd of the night's form past which the trip text says so
M_START = 0.3                                         # Manners at the gate: a unit of manners is worth this much of a unit of gate speed
FRACT = 0.15                                          # what a fractious start costs in performance (about a length on a mile)
FOLLOW_EARLY = True                                   # the following trip can be taken before a first-over horse exists (the retune lab)
FIGHT_L, G_FIN = 1.0, 0.1                             # a head-and-head: within a length at the wire, a unit of grit edge is worth G_FIN units


def _A(p):
    return (p["A_lead"], p["A_pocket"], p["A_fo"], p["A_fol"], 0.0)   # what each role is worth in the model (ROLES order)


def _secs(units, track, half=False):
    """Model units to seconds on the honest clock: the fitted line (on the 2026-10-27 clock) squeezed (sim.squeeze)."""
    a, b = FIG_FIT[track]
    return round(sim.squeeze(a + b * units) + (sim.HALF_SLOWER if half else 0.0), 2)


def class_units(b, track="mile"):
    """A horse's class in the model's units, from its bars: what it brings to any trip."""
    p = P[track]
    return K * (p["omega"] * (b["cruise"] - 5) + (1 - p["omega"]) * (b["kick"] - 5))


def pred_mile(b):
    """The mile a horse's bars predict, on the figure ruler."""
    return _secs(class_units(b), "mile")


def figure(h, track):
    """A start's figure: the ledger's performance with the trip taken out, as mile seconds. A breaker's start has none."""
    why = getattr(h, "why", None)
    if not why or "kick" not in why or why.get("broke"):
        return None
    p = P[track]
    closing = why["role"] in ("followed", "back")
    units = why["perf"] - (_A(p)[ROLES.index(why["role"])] - p["b_depth"] * why["depth"]) - p["k_close"] * closing * why["kick"]
    return _secs(units, track)                                  # as a mile: the half's allowance is the track's, not the horse's


def race(field, track="mile", passing=False):
    """One race. Returns the finishing order; sets each horse's trip, raw_time and last_time like sim.race."""
    p, n, half = P["half" if track == "half" else "mile"], len(field), track == "half"
    stats = {}
    for h in field:                                            # the same inputs sim.race races on
        s = dict(h.current(track))
        for t, d in sim.TONIC.get(getattr(h, "tonic_on", None), {}).items():
            s[t] = s[t] + d
        for t, d in (getattr(h, "drive_on", None) or {}).items():
            s[t] = s[t] + d
        stats[h.id] = s
    T = {h.id: {k: K * (v - 5.0) for k, v in bars(h, stats[h.id]).items()} for h in field}
    form = {h.id: rng.gauss(0, 1) * p["s_form"] for h in field}
    for h in field:
        for k in ("gate", "cruise", "kick"):
            T[h.id][k] += form[h.id]
    # the start (ratings v2): Manners get a horse away clean. A settled horse gains at the gate; a rank one on a bad night is
    # fractious behind the car, leaves last and gives up ground (FRACT) it has to make back.
    e, fractious = {}, {}
    for post, h in enumerate(field):
        z = rng.gauss(0, 1)
        fractious[h.id] = T[h.id]["manners"] < 0 and z < -2.0 - 0.8 * T[h.id]["manners"]   # the worse the manners, the easier the bad night (Astra, review 23)
        e[h.id] = T[h.id]["gate"] + M_START * T[h.id]["manners"] - p["c_post"] * post + p["s_start"] * z - (3.0 if fractious[h.id] else 0.0)
    out = sorted(field, key=lambda h: -e[h.id])                # order out of the gate
    w_k = 1 - p["omega"]
    A = _A(p)
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
        press = k == 1 and e[out[0].id] - e[out[1].id] < DUEL
        if mover is None and (press or (2 <= k <= FO_MAX["half" if half else "mile"] and can_move)):
            v[2] = A[2] + w_k * kh + p["g"] * (t["grit"] - lg)
        if (mover is not None or FOLLOW_EARLY) and followers < N_FOLLOW:   # a fast leaver may take the cover that comes (Patrick 2026-11-03)
            v[3] = A[3] + (w_k + p["k_close"]) * kh
        v[4] = (w_k + p["k_close"]) * kh - p["b_depth"] * line
        noisy = [x + p["s_choice"] * -math.log(-math.log(rng.random() or 1e-12)) for x in v]   # Gumbel: imperfect drivers
        pick = max(range(5), key=lambda i: noisy[i])
        role[h.id], depth[h.id] = pick, (line if pick == 4 else 0)
        if pick == 0: lead = h
        elif pick == 1: pocket_taken = True
        elif pick == 2: mover = h
        elif pick == 3: followers += 1
        else: line += 1
    if lead is None:                                           # nobody wanted it: the first one out leads anyway
        lead = out[0]; role[lead.id], depth[lead.id] = 0, 0
    gdiff = {h.id: 0.0 for h in field}
    if mover is not None:                                      # the head-and-head with the leader: grit decides
        gdiff[mover.id] = T[mover.id]["grit"] - T[lead.id]["grit"]
        gdiff[lead.id] = -gdiff[mover.id]
    perf, broke = {}, {}
    for h in field:
        t, r = T[h.id], role[h.id]
        broke[h.id] = rng.random() < 0.005 * math.exp(-2.88 * t["manners"])   # the manners curve (DECISIONS 163)
        closing = r in (3, 4)
        perf[h.id] = (p["omega"] * t["cruise"] + (w_k + p["k_close"] * closing) * t["kick"] + A[r] - p["b_depth"] * depth[h.id]
                      + p["g"] * gdiff[h.id] + p["s_eps"] * rng.gauss(0, 1) - BREAK * broke[h.id] - FRACT * fractious[h.id])
    order = sorted(field, key=lambda h: -perf[h.id])
    # the finish (ratings v2): Grit decides the head-and-heads. Two horses within FIGHT_L of each other at the wire fight it out,
    # and the grittier one gets the bob.
    fight = {h.id: False for h in field}
    for a, b in zip(order, order[1:]):
        if perf[a.id] - perf[b.id] < FIGHT_L / p["s_margin"]:
            swing = G_FIN * (T[a.id]["grit"] - T[b.id]["grit"]) / 2
            perf[a.id] += swing; perf[b.id] -= swing
            fight[a.id] = fight[b.id] = True
    order = sorted(field, key=lambda h: -perf[h.id])
    # times (ratings v2, the honest clock): every horse runs its own time, read off its performance tonight (ability, trip,
    # form and luck together) on one line, so the order, the margins and the clock are one thing and a beaten horse's time
    # is its own. Two horses are never closer than a nose.
    times, prev = {}, None
    win = _secs(perf[order[0].id], track, half)
    for h in order:
        m = (_secs(perf[h.id], track, half) - win) / SEC_PER_LENGTH
        if m > EASED:                                          # a beaten horse is not driven out: the tail of a field
            m = EASED + EASED * math.log1p((m - EASED) / EASED)   # stays within sight (25 L -> 15, 70 L -> 23)
        t = win + m * SEC_PER_LENGTH
        if prev is not None:
            t = max(t, prev + NOSE * SEC_PER_LENGTH)
        times[h.id], prev = t, t
    win_raw = times[order[0].id]
    for post, h in enumerate(field, 1):
        r = role[h.id]
        beat_leader = perf[h.id] > perf[lead.id]
        trip = f"post {post}, " + {0: "on the lead",
                                   1: "sat in the pocket, up the passing lane" if passing and beat_leader else "sat in the pocket",
                                   2: "parked first-over", 3: "sat mid-pack, moved after the half",
                                   4: "sat in behind, came from off the pace" if depth[h.id] >= 2 and order.index(h) < 3 else "sat in behind"}[r]
        if fractious[h.id]:
            trip += ", fractious at the start"
        if broke[h.id]:
            trip += ", broke stride"
        if fight[h.id] and order.index(h) < 3:
            trip += ", fought it out at the wire"
        if abs(form[h.id]) > FORM_TELL * p["s_form"]:               # the night's form, once it was big enough to tell
            trip += ", sharp tonight" if form[h.id] > 0 else ", flat tonight"
        h.trip = trip
        h.raw_time = h.last_time = times[h.id]
        h.margin_l = (times[h.id] - win_raw) / SEC_PER_LENGTH   # lengths behind the winner, as the clock has it
        h.why = dict(out=out.index(h) + 1, role=ROLES[r], depth=depth[h.id], perf=round(perf[h.id], 3),   # RaceGod's ledger: what decided it
                     form=round(form[h.id], 3), broke=broke[h.id], model_l=round((perf[order[0].id] - perf[h.id]) * p["s_margin"], 2),
                     margin=round(h.margin_l, 2), limited=False, ceiling=times[h.id], fractious=fractious[h.id], fight=fight[h.id],
                     kick=round(T[h.id]["kick"], 3), cruise=round(T[h.id]["cruise"], 3))                 # as raced tonight (form in): the figure reads them back
    return order


def rating(h):
    """The horse's rating on its card today: its bars (training, not race-night form) weighted by worth."""
    b = bars(h, h.developed)
    return sum(RATE_W[k] * b[k] for k in RATE_W)
