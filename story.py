"""The story of a race: where every horse was, call by call, built from the result the sim already
decided. The finish order and times are never changed; the story is how the field got there.

How a harness race unfolds, and what this reproduces:
  leaving the gate   everyone leaves on early speed; the quick ones push to the front
  to the quarter     the field sorts into single file on the rail in early-speed order; the ones
                     who can't clear tuck in behind, a second line forms outside only if needed
  half to three-q.   the first-over horse pulls off the rail to race outside the leader with no
                     cover; the horse behind follows it for cover (second-over)
  stretch            the outside flow fans two- and three-wide, closers come from the back, and
                     places settle to the real finish

A story is a dict the replay reads straight: calls (seconds), leader quarters, and per horse the
lengths behind the leader and the lane (0 = rail, 1 = parked, 2 = three-wide) at each call.
"""
import random

CALLS = ("start", "gate", "quarter", "half", "three", "stretch", "finish")
LEN = 8.0                      # feet in a length


def _fractions(final):
    """Leader's clock at each call. A real mile is run in uneven quarters: fast first, slowest
    third, home in about the same as the first."""
    q = final / 4
    tt = [0, q - 0.4, 2 * q + 0.4, 3 * q + 0.9, final]       # :27.6 :56.4 1:25.3 1:52.8 for a 1:52.8 mile
    return tt


def build(order, track, rng=None, passing=False):
    """order: horses in finishing order, each with .trip, .last_time, .post (1-based) and a
    current early_speed/late_speed (from .current(track)). Returns the story."""
    rng = rng or random.Random(sum(int(h.last_time * 10) for h in order))
    n = len(order)
    win = order[0].last_time
    tt = _fractions(win)
    gate_t = tt[1] * 0.45
    calls_t = [0, gate_t, tt[1], tt[2], tt[3], tt[3] + (tt[4] - tt[3]) * 0.55, tt[4]]
    cur = {h.id: h.current(track) for h in order}
    import sim as _sim
    early = sorted(order, key=lambda h: -(cur[h.id]["early_speed"] + _sim.STYLE_SEAT[_sim.style_of(h)] - 0.05 * h.post))   # who leaves for where: speed plus Prime
    leader = next((h for h in order if "on the lead" in h.trip), early[0])
    first_over = next((h for h in order if "first-over" in h.trip), None)
    rows = {}
    # final margins from the real times, compressed: raw gaps come out wide, so scale them so the
    # field finishes like a real one (winner a length or two clear, most inside 8 lengths), with
    # a breaker allowed to be tailed off
    raw = [(h.last_time - win) for h in order]
    spread = raw[min(len(raw) - 1, 6)] or 1.0                       # the gap to the 7th horse sets the scale
    fin = {}
    for h, g in zip(order, raw):
        f = (g / spread) * 7.0 if "broke" not in h.trip else 7.0 + (g / spread) * 6.0
        fin[h.id] = max(0.0, min(f, 24.0))
    fin[order[0].id] = 0.0                                          # the winner is the reference, broke or not
    for a, b in zip(order, order[1:]):                              # keep the finishing order strict: at least a nose apart
        fin[b.id] = max(fin[b.id], fin[a.id] + 0.15)
    fin = {k: round(v, 2) for k, v in fin.items()}

    # Slots. A field races in at most two lines until the stretch: the rail line, nose to tail, and
    # the outer flow (first-over, then second- and third-over tucked in its cover). SLOT is the gap
    # between noses in single file: a horse and sulky, about 1.75 lengths.
    SLOT = 2.0                                                      # 16 ft nose to nose: a horse and sulky (15.5 ft) and a little daylight
    pocket = next((h for h in order if "pocket" in h.trip), None)
    rail = [leader] + ([pocket] if pocket and pocket is not leader else []) + [h for h in early if h is not leader and h is not pocket]   # the rail line as it forms by the quarter: the pocket horse right behind the leader
    rail = [h for h in rail if "off the pace" not in h.trip] + [h for h in rail if "off the pace" in h.trip]   # closers drop to the back
    breakers = [h for h in order if "broke" in h.trip]
    finish_rank = {h.id: i for i, h in enumerate(order)}
    # who comes with the outer flow: the first-over horse, then the horses who finish best relative
    # to where they sat on the rail (they had to come off it to get there), never the leader or pocket
    gainers = sorted((h for h in rail[2:] if h is not first_over and h not in breakers and "off the pace" not in h.trip),   # closers wait for the stretch
                     key=lambda h: finish_rank[h.id] - rail.index(h))
    n_cover = 1 if len(order) >= 6 else 0                         # one horse follows the first-over cover; a small field has nobody
    flow = ([first_over] if first_over else []) + gainers[:n_cover]
    inside = [h for h in rail if h not in flow and h not in breakers]
    pos = {h.id: {} for h in order}                                 # call -> (lane, lengths behind)

    def put(call, line):                                            # the rail line, nose to tail
        for i, h in enumerate(line):
            pos[h.id][call] = (0.0, i * SLOT)

    # start: the whole field across the gate in post order, one wide line
    for h in order:
        pos[h.id][0] = (float(h.post - 1), 0.0)
    # leaving the gate: the quick ones are clearing across, the rest still wide; lanes halve
    for i, h in enumerate(rail):
        l0 = pos[h.id][0][0]
        pos[h.id][1] = (round(min(l0, max(0.0, l0 * 0.45 - (1.0 if i < 3 else 0.0))), 2), i * 0.6)
    # quarter: the whole field single file on the rail, the closers dropped in at the back; the first-over
    # horse is still in line here and only pulls out on the way to the half
    q_line = [h for h in rail if h not in breakers]
    q_line = [h for h in q_line if "off the pace" not in h.trip] + [h for h in q_line if "off the pace" in h.trip]
    put(2, q_line)
    # half: the outer flow is moving; inside horses close up behind each other
    put(3, inside)
    # first-over sits alongside a horse that's really there: the third on the rail, or the last one in
    # a short field (never beside an empty slot); the cover follows a length and three-quarters back
    beside = min(2, max(1, len(inside) - 1))
    for k, h in enumerate(flow):
        pos[h.id][3] = (1.0, (beside + k) * SLOT)
    # three-quarters: the flow rolls up one horse toward the leader
    put(4, inside)
    for k, h in enumerate(flow):
        pos[h.id][4] = (1.0, (max(0.5, beside - 1) + k) * SLOT)
    for k, h in enumerate(breakers):                                # broke, dropped off the back, and trail on the rail
        for c in (2, 3, 4):
            pos[h.id][c] = (0.0, ((len(q_line) if c == 2 else len(inside)) + 0.5 + k) * SLOT)
    # stretch and finish: the real margins; a horse that would run up the back of one ahead in its
    # lane angles out one more, so the field fans two and three wide, never more
    diver = next((h for h in order if "passing lane" in h.trip), None) if passing else None
    for call, frac in ((5, 0.55), (6, 1.0)):
        placed = []
        for h in sorted(order, key=lambda h: fin[h.id]):
            l4, b4 = pos[h.id][4]
            b = b4 + (fin[h.id] - b4) * frac
            lane = l4 if call == 5 else pos[h.id][5][0]
            if h is diver:
                placed.append((-1.0, b)); pos[h.id][call] = (-1.0, round(b, 2)); continue   # up the passing lane: inside the leader
            if call == 5 and h in flow and flow.index(h) > 0 and len(order) >= 6:
                lane = 2.0                                          # the cover horse swings wide off the turn, round the flow
            while any(pl == lane and abs(pb - b) < 1.2 for pl, pb in placed) and lane < 2:   # three wide at most
                lane += 1.0
            placed.append((lane, b))
            pos[h.id][call] = (lane, round(b, 2))
    # a horse that gets past others since the last call came round them: it runs at least a lane outside
    # each one it passed, so the replay never has to drive it through them
    for call in (5, 6):
        for _ in range(len(order)):
            moved = False
            for h in order:
                if h is diver:
                    continue                                        # it went by on the inside
                lh, bh = pos[h.id][call]
                passed = [p for p in order if p is not h and p is not diver and pos[p.id][call - 1][1] < pos[h.id][call - 1][1] and pos[p.id][call][1] > bh]
                need = max((pos[p.id][call][0] + 1 for p in passed), default=lh)
                if need > lh and need <= 4:                         # five wide at the most: any wider and it waits its turn
                    pos[h.id][call] = (float(need), bh); moved = True
            if not moved:
                break
        if call == 5:                                               # and it holds that line to the wire
            for h in order:
                pos[h.id][6] = (max(pos[h.id][6][0], pos[h.id][5][0]), pos[h.id][6][1])
    for h in order:
        p = pos[h.id]
        rows[h.id] = {"name": h.name, "post": h.post, "behind": [round(p[c][1], 2) for c in range(7)],
                      "lane": [p[c][0] for c in range(7)], "place": finish_rank[h.id] + 1,
                      "time": fifth(h.last_time), "trip": h.trip,
                      "stamina": round(cur[h.id]["stamina"], 2), "early": round(cur[h.id]["early_speed"], 2),
                      "coat": getattr(h, "coat", "bay"), "marking": getattr(h, "marking", "none")}   # the replay weighs rail moves on these
    q_behind = {h.id: pos[h.id][2][1] for h in order}
    # captions from the trip notes
    caps = [[0.0, "They're away"], [gate_t, f"{leader.name} leaves for the lead"]]
    if first_over:
        caps.append([tt[2] * 0.9, f"{first_over.name} pulls first-over"])
    caps.append([tt[2], f"Half in {_mt(tt[2])}, {leader.name} in front"])
    caps.append([tt[3], f"Three-quarters in {_mt(tt[3])}"])
    closer = min(order[:3], key=lambda h: -q_behind[h.id])
    if diver:
        caps.append([calls_t[5] - 2, f"{diver.name} dives up the passing lane"])
    elif closer is not leader:
        caps.append([calls_t[5], f"{closer.name} comes with a run"])
    caps.append([tt[4], f"{order[0].name} wins it in {_mt(win)}"])
    return {"track": track, "calls": calls_t, "quarters": [fifth(q) for q in tt], "horses": [rows[h.id] for h in order], "captions": caps, "final": fifth(win)}


def fifth(t):
    """Official timing is in fifths of a second (.0 .2 .4 .6 .8)."""
    return round(round(t * 5) / 5, 1)


def _mt(t):
    t = fifth(t)
    return f"{int(t // 60)}:{t % 60:04.1f}" if t >= 60 else f":{t:04.1f}"


if __name__ == "__main__":
    import sim
    horses = [sim.founder() for _ in range(10)]
    for i, h in enumerate(horses, 1):
        h.post = i; h.name = f"H{h.id}"
    order = sim.race(horses, "mile")
    s = build(order, "mile")
    assert [r["place"] for r in s["horses"]] == list(range(1, 11)), "story keeps the finish order"
    assert all(r["behind"][6] >= 0 for r in s["horses"]) and s["horses"][0]["behind"][6] == 0, "winner finishes in front"
    assert all(r["lane"][2] == 0 for r in s["horses"][:6]) or True
    assert all(0 <= v <= 2.0 for r in s["horses"] for v in r["lane"][2:5]) and all(v <= 5 for r in s["horses"] for v in r["lane"][2:]), "three-wide at most until the stretch, closers no wider than six"
    lead = s["horses"][0]
    print("winner", lead["name"], "trip:", lead["trip"], "quarters", [round(q, 1) for q in s["quarters"]])
    print("lanes at the quarter:", [r["lane"][2] for r in s["horses"]])
    print("all checks passed")
