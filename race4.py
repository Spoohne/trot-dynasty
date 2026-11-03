"""Race core rebuild, step 1 (research/engine_lab/REBUILD_PLAN.md): a race is run, not decided. Each tick every horse's
driver picks an effort, effort buys speed and costs energy, and the order at the wire is whatever happened.

Step 1 is the skeleton: one lane, no blocking, no drafting, no breaks, no abilities. Stats are in steps (0 is the
breed's middle, one step is one pip). Only Speed, Gate, Stamina and Kick are read so far. The game doesn't import this.

Run `python race4.py` for the self-check."""
import random

MILE = 1609.3          # metres
DT = 0.1               # seconds a tick
CRUISE = 13.8          # m/s at effort 0 for a middle horse (1:55 pace)
SPEED_STEP = 0.03      # m/s of cruise per step of Speed
PUSH = 1.4             # m/s that full effort adds
TANK = 100.0           # energy of a middle horse
STAMINA_STEP = 0.04    # share of tank per step of Stamina
DRAIN = 4.0            # energy a second at full effort (cost grows with effort squared)
LEAVE_M = 250          # the leave: metres off the gate
GATE_STEP = 0.20       # m/s of leaving speed per step of Gate
STRETCH_M = 400        # the drive home: metres from the wire
KICK = 0.8             # m/s the kick adds on a full tank
KICK_STEP = 0.50       # m/s of kick per step of Kick
TIRED = 0.92           # share of cruise an empty horse keeps
FORM_SD = 0.06         # m/s: the night's form
JITTER_SD = 0.15       # m/s: tick-to-tick stride noise


class Runner:
    def __init__(self, h, rng):
        self.h = h
        self.pos = 0.0
        self.tank = TANK * (1 + STAMINA_STEP * h.get("stamina", 0))
        self.energy = self.tank
        self.cruise = CRUISE + SPEED_STEP * h.get("speed", 0) + rng.gauss(0, FORM_SD)
        self.t = None                 # time at the wire

    def effort(self, dist):
        if self.pos < LEAVE_M:
            return 0.6                # leaving for position
        if dist - self.pos < STRETCH_M:
            return 1.0                # all out home
        return 0.2                    # settle

    def step(self, dist, rng):
        e = self.effort(dist)
        v = self.cruise + PUSH * e
        if self.pos < LEAVE_M:
            v += GATE_STEP * self.h.get("gate", 0)
        if dist - self.pos < STRETCH_M:
            v += (KICK + KICK_STEP * self.h.get("kick", 0)) * self.energy / self.tank
        self.energy -= DRAIN * e * e * DT
        if self.energy <= 0:
            self.energy = 0.0
            v = min(v, self.cruise * TIRED)
        v += rng.gauss(0, JITTER_SD)
        before = self.pos
        self.pos += v * DT
        return before


def race(field, dist=MILE, seed=None):
    """field: list of stat dicts. Returns indexes in finishing order and each horse's time (s)."""
    rng = random.Random(seed)
    rs = [Runner(h, rng) for h in field]
    clock = 0.0
    while any(r.t is None for r in rs):
        clock += DT
        for r in rs:
            if r.t is None:
                before = r.step(dist, rng)
                if r.pos >= dist:     # the tick's fraction past the wire, so ties split inside a tick
                    r.t = clock - DT + DT * (dist - before) / (r.pos - before)
    order = sorted(range(len(rs)), key=lambda i: rs[i].t)
    return order, [r.t for r in rs]


def beats(a, b, n=4000, seed=1):
    """Share of races A finishes ahead of B in a field of A, B and six middle horses."""
    rng = random.Random(seed)
    win = 0
    for _ in range(n):
        order, _ = race([a, b] + [{}] * 6, seed=rng.random())
        win += order.index(0) < order.index(1)
    return win / n


if __name__ == "__main__":
    rng = random.Random(7)
    wins = [0] * 8
    times = []
    for _ in range(4000):
        order, t = race([{}] * 8, seed=rng.random())
        wins[order[0]] += 1
        times.append(min(t))
    share = [w / 4000 for w in wins]
    print("identical field, win share by horse:", [round(s, 3) for s in share])
    assert all(0.10 < s < 0.155 for s in share), "an identical field must be a fair draw"
    times.sort()
    print("winning mile: median %.1f s, fastest %.1f s" % (times[len(times) // 2], times[0]))
    for stat in ("speed", "gate", "stamina", "kick"):
        ps = [beats({stat: k}, {}) for k in (1, 3)]
        print("%-8s +1 step beats middle %.0f%%, +3 steps %.0f%%" % (stat, 100 * ps[0], 100 * ps[1]))
        assert 0.5 < ps[0] < ps[1], stat + " must help, and more must help more"
    print("ok")
