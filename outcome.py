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
PIP_STEPS = (-3.33, -2.5, -1.67, -0.83, 0.0, 0.83, 1.67, 3.7, 6.0)   # app.PIP_STEPS: the live bar scale
GRIT_POP = dict(dur=(0.17, 1.424), gait=(0.09, 1.274), raw_sd=1.479, bar=(5.38, 1.58))   # live save 2026-11-02 (v6_convert)
SEC_PER_LENGTH = 0.2         # the replay's own conversion (a length is a fifth of a second)
LUCK = 1.0                    # seconds: the best night a horse can have, beyond its rating's time (two night-swings)
NOSE = 0.05                   # lengths: the least one finisher is behind another
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
P = {   # research/engine_lab/v4/fit_half.json, fit_mile.json (DECISIONS 224 refit)
    "half": dict(g=0.25, s_form=0.15, s_choice=0.1, c_post=0.0994314106733373, s_start=0.02017397059465198,
                 omega=0.5938761916108407, A_lead=0.4122946448648809, A_pocket=0.31396172750867324, A_fo=0.09299566675668958,
                 A_fol=0.09574834786072772, s_eps=0.17798810007780796, s_margin=7.605805514239352, k_close=0.04303554691830236,
                 b_depth=0.39885805717373174),
    "mile": dict(g=0.25, s_form=0.15, s_choice=0.1, c_post=0.04926660027735483, s_start=0.8370432667346848,
                 omega=0.4703087097212123, A_lead=0.8944309419378034, A_pocket=0.7728020645420891, A_fo=0.8026769007091834,
                 A_fol=0.2615173160574591, s_eps=0.027295459447580828, s_margin=6.0407761172731735, k_close=1.1015350803998327,
                 b_depth=0.13223734814640054),
}
rng = random.Random()


def bar(v, gait=False):
    """A live stat on the live pip scale, made continuous (1 to 10). Manners tops out at a perfect trip (sim.GAIT_CAP)."""
    if gait and v > PIP_STEPS[5]:
        v = min(PIP_STEPS[-1], PIP_STEPS[5] + (v - PIP_STEPS[5]) * (PIP_STEPS[-1] - PIP_STEPS[5]) / (sim.GAIT_CAP - PIP_STEPS[5]))
    xs = (-4.17,) + PIP_STEPS
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
    e = {h.id: T[h.id]["gate"] - p["c_post"] * post + p["s_start"] * rng.gauss(0, 1) for post, h in enumerate(field)}
    out = sorted(field, key=lambda h: -e[h.id])                # order out of the gate
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
        press = k == 1 and e[out[0].id] - e[out[1].id] < DUEL
        if mover is None and (press or (2 <= k <= FO_MAX["half" if half else "mile"] and can_move)):
            v[2] = A[2] + w_k * kh + p["g"] * (t["grit"] - lg)
        if mover is not None and followers < N_FOLLOW:
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
                      + p["g"] * gdiff[h.id] + p["s_eps"] * rng.gauss(0, 1) - BREAK * broke[h.id])
    order = sorted(field, key=lambda h: -perf[h.id])
    # times (DECISIONS 216, 239): the bars estimate the mile time. The winner runs its own rating's time, give or take a
    # night's variation; everyone else is the winner plus its margin. Board, clock and replay agree.
    # The speed limit (Patrick, 2026-11-02: "there's just a hard limit on how fast a horse can go. Period."): no horse, winner
    # or beaten, runs faster than its own rating's time less LUCK. A beaten horse that would have to be quicker than that to
    # be this close is beaten by more; the order stands, and the margins are re-read from the times.
    to_raw = (sim.CLOCK_REF - sim.CLOCK_AT) / sim.CLOCK_K                # display seconds back to race seconds (the clock is linear above its floor)
    limit = {h.id: best_mile(bars(h, stats[h.id]), half) - LUCK + to_raw for h in field}
    w = order[0]
    limit = {h.id: limit[w.id] + WITHIN * (limit[h.id] - limit[w.id]) for h in field}   # the winner's class sets the clock; the rest sit behind on the model's scale
    win_raw = max(limit[w.id] + LUCK + rng.gauss(0, 0.5), limit[w.id])
    for post, h in enumerate(field, 1):
        r = role[h.id]
        beat_leader = perf[h.id] > perf[lead.id]
        trip = f"post {post}, " + {0: "on the lead",
                                   1: "sat in the pocket, up the passing lane" if passing and beat_leader else "sat in the pocket",
                                   2: "parked first-over", 3: "sat mid-pack, moved after the half",
                                   4: "sat in behind, came from off the pace" if depth[h.id] >= 2 and order.index(h) < 3 else "sat in behind"}[r]
        if broke[h.id]:
            trip += ", broke stride"
        h.trip = trip
        h.margin_l = (perf[order[0].id] - perf[h.id]) * p["s_margin"]   # lengths behind the winner: the story shows these as run
        h.why = dict(out=out.index(h) + 1, role=ROLES[r], depth=depth[h.id], perf=round(perf[h.id], 3),   # RaceGod's ledger: what decided it
                     form=round(form[h.id], 3), broke=broke[h.id], model_l=round(h.margin_l, 2))
    prev = prev0 = None
    for h in order:                                            # the speed limit, then the order: a horse pushed back carries the delay
        t0 = win_raw + h.margin_l * SEC_PER_LENGTH             # to those behind it, who keep their gaps (at least a nose)
        t = max(t0, limit[h.id])
        if prev is not None:
            t = max(t, prev + max(NOSE * SEC_PER_LENGTH, t0 - prev0))
        h.raw_time, prev, prev0 = t, t, t0
        h.margin_l = (t - win_raw) / SEC_PER_LENGTH
        h.last_time = sim.clock(t, half)
        h.why["limited"] = t > t0 + 1e-9                         # the speed limit, not the model, set this horse's time
        h.why["margin"] = round(h.margin_l, 2)
        h.why["ceiling"] = round(limit[h.id], 2)               # race seconds: the fastest this horse could go tonight
    return order


def rating(h):
    """The horse's rating on its card today: its bars (training, not race-night form) weighted by worth."""
    b = bars(h, h.developed)
    return sum(RATE_W[k] * b[k] for k in RATE_W)
