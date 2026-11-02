"""Recovery-envelope assay (review 7, item 79). 20 races with an identical-trait leader (L, front) and closer (C, late) are
run to the half and saved. Each saved state is continued four ways (closer moves at 0.55 vs 0.74 × tank_full 45 vs 100)
with the closer on a clear path (traffic off, shelter still real), breaks off, budget off, DT 1/16.
Per continuation: lengths the closer was behind the leader at the half and at the leader's finish, the closer's time capped
by its current ceiling, energy at the move point and at the finish, and an optimistic bound: lengths it could recover running
at its fresh maximum from the move point, with acceleration, ignoring depletion."""
import copy, json, os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race2 as R
DT = 1 / 16
R.P.update(break_k=0.0, budget=0)
OTH = ["stalk", "mid", "mid", "stalk", "mid", "late"]
rng = random.Random(13)
states = []
while len(states) < 20:
    same = {t: rng.gauss(0, .3) for t in ("early_speed", "late_speed", "stamina")}
    f = [R.Runner("L", R.avg(**same, gait=6), "front", 1, {"leave": True}),
         R.Runner("C", R.avg(**same, gait=6), "late", 2, {"move_at": 0.99})]       # the closer just sits until the continuation
    f += [R.Runner(f"H{k}", R.avg(**{t: rng.gauss(0, .4) for t in ("early_speed", "late_speed", "stamina")}, gait=6), s, k + 3) for k, s in enumerate(OTH)]
    for k, h in enumerate(f):
        h.post, h.pos, h.lane = k + 1, -0.05 * R.LEN * k, k
    o, rec = R.run(f, rng=random.Random(len(states)), dt=DT, snap_at=0.5)
    snap = rec.get("snap")
    if snap:
        L = next(h for h in snap if h.name == "L"); C = next(h for h in snap if h.name == "C")
        if L.pos > C.pos:
            states.append(snap)


def fresh_bound(C, L_finish_t, move_f):
    """Lengths the closer could recover if, from its move point, it ran at its fresh maximum (accelerating at its rate)."""
    v, pos, t = C.v, C.pos, 0.0
    vmax = R.SPRINT + R.P["kick_late"] * C.s["late_speed"] + R.P["kick_early"] * C.s["early_speed"]
    acc = R.P["accel"] + R.P["accel_early"] * C.s["early_speed"]
    while pos < R.FT_MILE and t < 200:
        if pos / R.FT_MILE >= move_f:
            v = min(vmax, v + acc * DT)
        pos += v * DT; t += DT
    return t


out = {}
for move in (0.55, 0.74):
    for tank in (45.0, 100.0):
        R.P["tank_full"] = tank
        rows = []
        for i, s0 in enumerate(states):
            f = copy.deepcopy(s0)
            L = next(h for h in f if h.name == "L"); C = next(h for h in f if h.name == "C")
            behind_half = (L.pos - C.pos) / R.LEN
            C.instr.update(move_at=move, clear_path=True, follow=False)
            C.capped_t = 0.0
            o, rec = R.run(f, rng=random.Random(500 + i), dt=DT)
            gap_s = C.time - L.time                                         # >0: closer behind at the wire
            bound_t = fresh_bound(copy.deepcopy(next(h for h in s0 if h.name == "C")), L.time, move)
            rows.append(dict(behind_half=behind_half, gap_s=gap_s, recovered_len=behind_half - gap_s * R.CRUISE * 1.15 / R.LEN,
                             won=C.time < L.time, capped_s=C.capped_t, energy_end=C.energy, bound_beats_leader=bound_t < L.time))
        out[f"move {move} · tank_full {tank:g}"] = {k: round(st.mean(r[k] for r in rows), 3) for k in rows[0]}
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "recovery_envelope.json"), "w"), indent=1)
for k, v in out.items():
    print(k, v)
