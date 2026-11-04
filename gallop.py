"""The Gallop Racer 2006 race model, ported (race-engine-findings.md sections 14 and 14.10; the JS reference is
paddock_ledger.html runRace). Stats and what they do: research/engine_lab/GALLOP_STATS.md.

Pace is km/h x 100 (6300 = 63 km/h), energy E = 25 v^2, 30 frames a second. Every horse in every race of a batch is
one row of a (races, field) array, so a whole race night runs in one frame loop.

    order, times, blocked = run(stats)      stats: (R, n, 10) ints in STAT order, or one (n, 10) field
    python gallop.py                        self-check: the mile's times, the gap at the wire, +10 on a stat
"""
import numpy as np

STATS = ["speed", "staying", "stamina", "breaking", "response", "fierce", "tenacity", "power", "courage", "feel"]
SPD, STAY, STAM, BRK, RESP, FIERCE, TEN, POW, COUR, FEEL = range(10)

# Read from the game's code (FUN_004b56c0): index = stat/10, interpolated.
TOP = np.array([[6850, 6875, 6900, 6950, 7025, 7125, 7250, 7375, 7500, 7625, 7750, 7875, 8000, 8000],
                [6750, 6775, 6800, 6850, 6925, 7025, 7150, 7275, 7400, 7525, 7650, 7775, 7900, 7900]], float)
CRUISE = np.array([[5700, 5725, 5750, 5775, 5825, 5875, 5950, 6025, 6100, 6175, 6250, 6325, 6400, 6400],
                   [5600, 5625, 5650, 5675, 5725, 5775, 5850, 5925, 6000, 6075, 6150, 6225, 6300, 6300]], float)
POOL = np.array([550000, 600000, 650000, 700000, 750000, 900000, 1200000, 1600000, 1800000, 2000000, 2100000, 2200000, 2300000, 2300000], float)
DRAIN_A = np.array([3500, 3400, 3300, 3200, 3100, 3000, 2900, 2800, 2700, 2600, 2500, 2400, 2300, 2300], float)
DRAIN_B = np.array([2500, 2400, 2300, 2200, 2100, 2000, 1900, 1800, 1700, 1600, 1500, 1400, 1300, 1300], float)
DRAIN_C = np.array([2000, 1900, 1800, 1700, 1600, 1500, 1400, 1300, 1200, 1100, 1000, 1000, 1000, 1000], float)
A0, DRAG, FPS = 4_000_000.0, 800_000.0, 30

CFG = {   # everything inferred rather than read from the code, and the rank rule: tune here
    "track_class": 4,           # course class 0..7 in the Power reserve: cap*(1 - class*(99-Power)/10000)
    "surface": 0,               # table row: 0 turf (fast track), 1 dirt (inferred)
    "apt_offset": [[0, -75, -150, -225], [0, 75, 150, 225]],   # pace offset by aptitude 3..0 (row order inferred); all horses apt 3 = 0
    "early_line_m": 350,        # reserve drain halved before this (300 under 1400 m)
    # the harness lane layer (ours, not the game's): posts line the gate, everyone wants the rail, nobody runs through
    # the horse ahead, a held horse may pull out and go round, cover saves energy and racing parked out costs it
    "start_pace": 0.9,          # harness horses are at pace when the gate folds: the share of standard pace they leave at (0: the game's standing start)
    "lane_m": 0.65,             # a lane's width in the sim's lateral metres; lane 0 is the rail
    "body_m": 5.0,              # horse plus sulky: a follower in the same lane sits this far back and can't pass
    "draft_m": 8.0,             # cover: a horse this close ahead in the same lane
    "rating_drain": 0.0,        # the reserve drains at least this share of its table rate even at rating pace (the game: nothing below mid pace), so cover and a parked trip cost something before the drive
    "draft_save": 0.3,          # share of the pool and reserve drain that cover saves
    "parked_cost": 0.3,         # extra drain racing off the rail with no cover (first-over, three wide)
    "wide_cost": 0.0025,        # ground lost per lane out, as a share of speed (a lane is 4 m a mile of extra turn)
    "lat_rate": 0.015,          # metres a frame a horse moves sideways: a lane in a second and a half
    "pull_after_m": 300,        # no pulling out before this: the field files in off the gate
    "pull_range": 1.6,          # a driver pulls only within this many spurt distances of the wire (the move at the half, not the quarter)
    "pull_margin": 50,          # a held driver pulls when its target pace beats the horse ahead by this (km/h x100)
    "pull_p": 0.02,             # per frame, once it wants to: about two seconds' patience
    "leave_m": 200,             # the leave: metres off the gate in which every driver asks for position
    "leave_push": 600,          # the ask a 99-Breaking horse leaves with (scaled by Breaking): a 27 s first quarter, paid for in reserve
    "lead_clear": 3.5,          # metres clear at which the leader rates (the game's 9.75 let it open five lengths on a field still filing in)
    "follow_slack": 1.5,        # metres beyond a body a driver lets the horse ahead get before closing up again
    "cut_behind": 1.0,          # a sideways step never lands closer than this many bodies ahead of a horse in that lane
    "tuck_ahead": 1.2,          # a horse drops in only with this many bodies clear ahead in that lane...
    "tuck_behind": 0.2,         # ...and nobody closer than this behind (that horse eases and gives the spot)
    "rate_push": 600,           # the most a driver asks before the drive, closing a gap (at 800 the field sprinted up to a leader eight lengths clear)
    "ease_push": -500,          # the most a driver takes back before the drive (at -800 the field crawled while the leader opened eight lengths)
    "clock_scale": 1.21,        # reported seconds per sim second: the sim's 94 s mile reads as a trotter's 1:53.5 (dynamics untouched)
    "rank_stats": [SPD, STAY, STAM, FIERCE, TEN, POW, RESP],
    "rank_bands": [(570, "SS"), (500, "S"), (460, "A"), (420, "B"), (370, "C"), (330, "D"), (280, "E"), (0, "F")],
}
MILE = 1609


def rank(stats):
    """Rank letter(s) from the seven racing stats; stats (..., 10)."""
    s = np.asarray(stats)[..., CFG["rank_stats"]].sum(-1)
    letters = np.full(s.shape, "F", dtype="<U2")
    for cut, L in reversed(CFG["rank_bands"]):
        letters[s >= cut] = L
    return letters


def lerp(table, stat):
    s = np.clip(stat, 0, 129).astype(float)
    i = (s // 10).astype(int)
    return table[i] + (table[np.minimum(13, i + 1)] - table[i]) / 10 * (s % 10)


def run(stats, dist=MILE, rng=None, apt=None, record=False):
    """Race every field in stats (R, n, 10). Returns place (R, n) 1-based, time in seconds (R, n), frames blocked (R, n);
    with record, also every frame's progress (m) and lane (m) as an array (frames, R, n, 2)."""
    rng = rng or np.random.default_rng()
    st = np.asarray(stats, float)
    one = st.ndim == 2
    if one:
        st = st[None]
    R, n, _ = st.shape
    row = CFG["surface"]
    top, cruise = lerp(TOP[row], st[..., SPD]), lerp(CRUISE[row], st[..., STAY])
    std = cruise + 0.2 * (top - cruise)
    d = top - cruise
    pool = lerp(POOL, st[..., STAM])
    reserve = 1_200_000 * (1 - CFG["track_class"] * (99 - st[..., POW]) / 10000)
    apt_off = np.asarray(CFG["apt_offset"][row], float)[3 - (np.full((R, n), 3) if apt is None else np.asarray(apt))]
    drain_a = lerp(DRAIN_A, st[..., STAY]) * (1 + (70 - st[..., FIERCE]) / 5000)
    drain_b = lerp(DRAIN_B, st[..., STAY]) * (1 + (70 - st[..., FIERCE]) / 5000)
    drain_c = lerp(DRAIN_C, st[..., TEN])
    fierce_k = 1 + (70 - st[..., FIERCE]) / 5000
    accel = 2 * (A0 - 12000 * (99 - st[..., BRK]))
    step_brk, step_resp = st[..., BRK] // 5 + 1, st[..., RESP] // 5 + 1
    push_up = st[..., RESP] / 5 + 52
    early = CFG["early_line_m"] if dist >= 1400 else CFG["early_line_m"] - 50
    phase1, phase2 = (300, 450) if dist >= 1400 else (250, 350)
    mps10 = lambda p: p / 100 * 1000 / 3600 / 10

    leave = 30 * rng.integers(0, (st[..., BRK] // 6 + 1).astype(int), endpoint=False)      # FUN_00483de8 (Breaking)
    v = np.where(CFG["start_pace"] > 0, CFG["start_pace"] * std + leave, 3500 + leave)      # a running start behind the gate, or the game's standing one
    E = 25 * v * v
    LANE, BODY = CFG["lane_m"], CFG["body_m"]
    prog = np.zeros((R, n)); tgt = np.tile(np.arange(n), (R, 1)); lat = tgt * LANE   # post 1 on the rail
    effort = np.full((R, n), 10.0); push = np.zeros((R, n)); brk = np.zeros((R, n))
    phase = np.zeros((R, n), int); spurted = np.zeros((R, n), bool); blocked = np.zeros((R, n), int); pulled = np.zeros((R, n), bool)
    held = np.zeros((R, n), bool)                                                  # last frame's: read before this frame's traffic is known
    done = np.full((R, n), -1.0)
    frames = []
    for frame in range(1, FPS * 400):
        live = done < 0
        if not live.any():
            break
        lead = prog.max(1, keepdims=True)
        gap = lead - prog
        # who is where: the nearest horse ahead in my lane, whether it gives me cover, whether I'm parked
        dp = prog[:, None, :] - prog[:, :, None]                                   # [r, me, other]: how far ahead
        same = (np.abs(lat[:, None, :] - lat[:, :, None]) < 0.95 * LANE) & live[:, None, :]   # any lateral overlap: a horse half a lane over still can't be run through
        dp_ahead = np.where(same & (dp > 0), dp, np.inf)
        j_ahead = dp_ahead.argmin(2)
        gap_ahead = np.take_along_axis(dp_ahead, j_ahead[..., None], 2)[..., 0]
        lane = np.rint(lat / LANE).astype(int)
        cover = gap_ahead < CFG["draft_m"]
        mult = np.where(cover, 1 - CFG["draft_save"], np.where(lane >= 1, 1 + CFG["parked_cost"], 1.0))
        left = dist - prog
        start = prog < 100
        phase = np.where((phase < 1) & (prog > phase1), 1, phase)
        phase = np.where((phase < 2) & (prog > phase2), 2, phase)
        # spurt point (FUN_00476638 via FUN_0047b820): go when the reserve can sustain spurt pace to the wire
        Rr = np.clip(reserve, 500000, 1000000)
        v60 = cruise + 0.6 * d
        vR = v60 + (top - v60) * (Rr - 500000) / 500000
        vAvg = np.maximum(cruise + 0.2 * d, np.minimum(v60, v))
        n1 = (Rr - 500000) / drain_a + 1
        n2 = np.maximum(1, (v60 - vAvg) / (0.4 * d) * 250000 / drain_b)
        spurt_dist = ((mps10(vR) + mps10(v60)) * n1 * 0.5 + (mps10(v60) + mps10(vAvg)) * n2 * 0.5) * 0.8
        phase = np.where((phase < 5) & (left < spurt_dist), 5, phase)
        # driver's push (FUN_00476be0): keep up with the leader, everything once the spurt is on
        second = np.sort(prog, 1)[:, -2:-1]                                        # the leader eases only when clear by 9.75 m (14.6)
        # with a horse ahead in the lane a driver keeps to its wheel (a body and a little slack); with nobody ahead it
        # keeps within 9.75 m of the leader (14.6). From the end of the start zone, not the game's phase 1 at 300 m
        slack = np.where(np.isfinite(gap_ahead), gap_ahead - BODY > CFG["follow_slack"], gap > 9.75)
        leaving = prog < CFG["leave_m"]                                            # the leave: everyone asks for position, the quick-gaited ask hardest
        more = (phase >= 5) | (~start & slack & (cover | pulled | (lane == 0)))
        stray = ~leaving & (phase < 5) & (lane >= 1) & ~cover & ~pulled             # wide with nobody to follow once the leave is over: take back and find cover
        less = ~more & (((phase >= 1) & (prog - second > CFG["lead_clear"])) | stray)
        push = np.clip(push + np.where(more, push_up, 0) - np.where(less, 120, 0), -800, 800)
        push = np.where(leaving & ~held, np.minimum(push + push_up, CFG["leave_push"] * st[..., BRK] / 99), push)
        push = np.where(phase >= 5, push, np.clip(push, CFG["ease_push"], CFG["rate_push"]))   # before the drive: close a gap or take back at a rating pace
        push = np.where(more | less, push, push - np.sign(push) * np.minimum(np.abs(push), 60))   # the dead band: the ask fades
        # effort follows the push (FUN_00485b50)
        step = np.where(start, step_brk, step_resp)
        brk = np.where(start, 2 * st[..., BRK], np.maximum(brk - 1, 0))
        up = np.where(push >= 600, 30, step)
        down = np.where(push < -600, -25, np.floor(push * 12 / 100) + 1)
        effort = np.clip(effort + np.where(push > effort, up, np.where(push < 0, down, 0)), -999, 999)
        # the pace the spurt reserve still allows (FUN_0048fcf0)
        Rs = reserve
        minp = np.where(start, 3500.0, 5000.0)
        max_avail = np.where(Rs >= 1000000, top,
                    np.where(Rs >= 500000, cruise + 0.6 * d + (0.4 * d) * (Rs - 500000) / 500000,
                    np.where(Rs >= 250000, cruise + 0.2 * d + 0.4 * d * (Rs - 250000) / 250000,
                             minp + (cruise + 0.2 * d - minp) * Rs / 250000)))
        # target pace and the energy step
        T = np.clip(std + (top + brk - std) * effort / 1000, minp, max_avail)
        dv = np.abs(T - v)
        a = np.where(dv < 150, accel * dv / 150, accel)
        E = E + np.where(T >= v, 1, -1) * a * (1 - v / (1.25 * top)) - DRAG
        E = np.clip(E, 25 * minp * minp, 25 * (max_avail + brk) ** 2)
        lim = np.where(push < 800, max_avail - 100, max_avail - (1000 - push) / 2)
        v = np.clip(np.sqrt(E / 25), minp, np.minimum(max_avail, lim))
        # stamina pool, drained by pace band (FUN_0048f2d8)
        dr = np.where(v < cruise - 25, 0, np.where(v < cruise, 750, np.where(v < std, 750 + 250 * (v - cruise) / (std - cruise),
                      np.where(v < top, 1000 + 1000 * (v - std) / (top - std), 2000))))
        pool = np.maximum(0, pool - dr * mult)
        # spurt reserve drain (FUN_004d1960) and the exhausted penalty (FUN_004d2368)
        base = np.where(Rs >= 500000, drain_a / fierce_k, np.where(Rs >= 250000, drain_b / fierce_k, drain_c))
        mid = (std + top) / 2
        f_hi = np.clip((v - mid) / (top - mid), 0, 1) * np.where(prog < early, 0.5, 1)
        f = np.maximum(CFG["rating_drain"], np.where(Rs >= 500000, f_hi, (v >= max_avail - 100).astype(float)))
        reserve = reserve - (base * f * fierce_k + np.where(pool == 0, 0.05 * base, 0)) * mult
        rebase = ~spurted & (left < 800) & (phase >= 5)
        reserve = np.where(rebase, np.minimum(reserve, np.clip(650000 + gap * 100 * 25, 0, 1500000)), reserve)
        spurted |= rebase
        reserve = np.maximum(0, reserve)
        # nobody runs through the horse ahead: a follower in the same lane is held to its back, and its pace with it
        spd = (v + apt_off) / 100 * 1000 / 3600 / FPS
        free = spd.copy()
        for _ in range(2):                                                         # twice, so a line of three settles
            room = np.take_along_axis(spd, j_ahead, 1) + np.clip((gap_ahead - BODY) * 0.05, -0.03, np.inf)   # eases back onto its wheel
            spd = np.where(np.isfinite(gap_ahead), np.minimum(spd, room), spd)
        held = live & (spd < free - 1e-9)
        blocked += held
        v = np.where(held, np.maximum(minp, spd * FPS * 3600 / 1000 * 100 - apt_off), v)
        E = np.where(held, 25 * v * v, E)
        # drivers: settled in a lane, drop in when the inner lane is clear; a held driver
        # who wants to go faster than the horse ahead pulls out a lane when that lane is clear, with a little patience
        settled = np.abs(lat - tgt * LANE) < 1e-6
        def clear(k):                                                              # lane k beside me: its nose past the horse there's middle, nobody at my wheel behind (that horse eases and gives the spot)
            at = np.abs(lat[:, None, :] - (k * LANE)[:, :, None]) < 0.75 * LANE
            return ~(at & (dp > -CFG["tuck_behind"] * BODY) & (dp < CFG["tuck_ahead"] * BODY) & live[:, None, :] & ~np.eye(n, dtype=bool)).any(2)
        v_ahead = np.take_along_axis(v, j_ahead, 1)
        want_in = settled & (lane > 0) & clear(lane - 1)
        want_out = settled & ~want_in & held & (prog > CFG["pull_after_m"]) & (left < CFG["pull_range"] * spurt_dist)             & (T > v_ahead + CFG["pull_margin"]) & (lane < np.where(phase >= 5, 4, 2)) & clear(lane + 1) & (rng.random((R, n)) < CFG["pull_p"])
        tgt = np.where(want_in, lane - 1, np.where(want_out, lane + 1, tgt))
        pulled = (pulled | want_out) & ~want_in
        # the sideways step, held while a horse sits within a body ahead of where it would go, or close behind (that one eases)
        cand = lat + np.clip(tgt * LANE - lat, -CFG["lat_rate"], CFG["lat_rate"])
        bump = ((np.abs(cand[:, :, None] - lat[:, None, :]) < 0.95 * LANE) & (dp < BODY) & (dp > -CFG["cut_behind"] * BODY)
                & live[:, None, :] & ~np.eye(n, dtype=bool)).any(2)
        lat = np.where(bump, lat, cand)
        spd = spd * (1 - lane * CFG["wide_cost"])                                  # the ground lost out wide
        prog = prog + np.where(live, spd, 0)
        over = live & (prog >= dist)
        done = np.where(over, frame - (prog - dist) / np.maximum(spd, 1e-9), done)
        if record:
            frames.append(np.stack([prog, lat], -1))
    done = np.where(done < 0, frame, done)
    place = done.argsort(1).argsort(1) + 1
    times = done / FPS * CFG["clock_scale"]
    out = [place, times, blocked] + ([np.array(frames)] if record else [])
    if one:
        out = [x[0] for x in out[:3]] + [out[3][:, 0] for _ in out[3:]]
    return tuple(out)


def field(n, rng):
    """A test field, the ledger's population capped at the game's 99: 30 + U(0,70) + U(0,22) a stat."""
    return np.minimum(99, 30 + rng.integers(0, 70, (n, 10)) + rng.integers(0, 22, (n, 10))).astype(float)


if __name__ == "__main__":
    rng = np.random.default_rng(1)
    N = 400
    base = np.stack([field(12, rng) for _ in range(N)])
    raw = CFG["clock_scale"]; CFG["clock_scale"] = 1.0                 # the game's own seconds first
    pl, t, bl = run(base, rng=np.random.default_rng(2))
    win = t.min(1); second = np.sort(t, 1)[:, 1]
    print(f"{N} twelve-horse miles: winner {win.mean():.1f} s (range {win.min():.1f}..{win.max():.1f}), "
          f"first two {np.mean(second - win):.2f} s apart, blocked {bl.mean():.0f} frames a horse")
    assert 88 < win.mean() < 97 and np.mean(second - win) < 1.0
    print(f"as a trotter's clock (x{raw}): {win.mean() * raw:.1f} s")
    rows = []
    for k, name in enumerate(STATS):
        alt = base.copy(); alt[:, 0, k] = np.minimum(99, alt[:, 0, k] + 10)
        p0, t0, _ = run(base, rng=np.random.default_rng(3)); p1, t1, _ = run(alt, rng=np.random.default_rng(3))
        rows.append((name, (t1[:, 0] - t0[:, 0]).mean(), (p1[:, 0] - p0[:, 0]).mean(), (p0[:, 0] == 1).mean() * 100, (p1[:, 0] == 1).mean() * 100))
    rows.sort(key=lambda r: r[1])
    print("+10 on one stat of horse 0, same field and seed\nstat        dTime(s)  dPlace   win%")
    for name, dt, dp, w0, w1 in rows:
        print(f"{name:<11}{dt:8.3f}{dp:8.2f}   {w0:.1f}->{w1:.1f}")
    got = dict((r[0], r[1]) for r in rows)
    # the JS reference on these same fields (apt 3, no abilities): Staying -0.30 s, Speed -0.33 s, winner 89.3 s, gap 0.46 s;
    # its own population (random aptitudes and abilities) gave -0.49 / -0.37
    assert -0.6 < got["staying"] < -0.2 and -0.6 < got["speed"] < -0.2, "Staying and Speed must each be worth 0.2-0.6 s at a mile"
    CFG["clock_scale"] = raw
    print("ok")
