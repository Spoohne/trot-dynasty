"""The outcome model's race, drawn by the story system (DECISIONS 212). A lab variant of story.build that takes the
model's decisions as given: the start order, each horse's trip (lead, pocket, first-over, followed, back, broke), the
finish order, the margins and the clock. The live story.py is untouched; at integration build() gets these inputs.
    import v4_story; s = v4_story.build(horses, track, final, passing=True)
    horses: in finishing order, dicts with name, post, role (0-4 as v4_outcome.ROLES), start (rank out of the gate),
            margin (lengths behind the winner), broke, plus anything to carry through (traits, form, coat)"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import story as S

TRIP = {0: "on the lead", 1: "pocket trip", 2: "first-over", 3: "followed cover", 4: "raced in the line"}


def build(horses, track, final, passing=False):
    n = len(horses)
    tt = S._fractions(final)
    gate_t = tt[1] * 0.45
    calls_t = [0, gate_t, tt[1], tt[2], tt[3], tt[3] + (tt[4] - tt[3]) * 0.55, tt[4]]
    byname = {h["name"]: h for h in horses}
    for h in horses:
        h["trip"] = "broke" if h.get("broke") else TRIP[h["role"]]
    early = sorted(horses, key=lambda h: h["start"])                     # the decided order out of the gate
    leader = next((h for h in horses if h["role"] == 0 and not h.get("broke")), early[0])
    pocket = next((h for h in horses if h["role"] == 1 and not h.get("broke")), None)
    first_over = next((h for h in early if h["role"] == 2 and not h.get("broke")), None)
    followers = [h for h in early if h["role"] == 3 and not h.get("broke")]
    breakers = [h for h in horses if h.get("broke")]
    win = horses[0]
    fin = {h["name"]: max(0.0, min(24.0, h["margin"])) for h in horses}  # the decided margins, as decided
    fin[win["name"]] = 0.0
    for a, b in zip(horses, horses[1:]):                                 # strict order: at least a nose apart
        fin[b["name"]] = max(fin[b["name"]], fin[a["name"]] + 0.15)
    SLOT = 2.0
    rail = [leader] + ([pocket] if pocket else []) + [h for h in early if h is not leader and h is not pocket]
    flow = ([first_over] if first_over else []) + followers
    inside = [h for h in rail if h not in flow and h not in breakers]
    pos = {h["name"]: {} for h in horses}

    def put(call, line):
        for i, h in enumerate(line):
            pos[h["name"]][call] = (0.0, i * SLOT)

    for h in horses:
        pos[h["name"]][0] = (float(h["post"] - 1), 0.0)
    for i, h in enumerate(rail):
        l0 = pos[h["name"]][0][0]
        pos[h["name"]][1] = (round(min(l0, max(0.0, l0 * 0.45 - (1.0 if i < 3 else 0.0))), 2), i * 0.6)
    q_line = [h for h in rail if h not in breakers]
    put(2, q_line)
    put(3, inside)
    beside = min(2, max(1, len(inside) - 1))
    for k, h in enumerate(flow):                                      # the move unfolds: at the half it has just pulled out and gained a little
        q = pos[h["name"]][2][1]
        pos[h["name"]][3] = (1.0, max((beside + k) * SLOT, q - 2.0))
    put(4, inside)
    for k, h in enumerate(flow):                                      # and keeps rolling: about 3½ lengths a quarter at most
        pos[h["name"]][4] = (1.0, max((max(0.5, beside - 1) + k) * SLOT, pos[h["name"]][3][1] - 3.5))
    for k, h in enumerate(breakers):
        for c in (2, 3, 4):
            pos[h["name"]][c] = (0.0, ((len(q_line) if c == 2 else len(inside)) + 0.5 + k) * SLOT)
    # the pocket horse that beats the leader comes up the passing lane on a track that has one
    diver = pocket if (passing and pocket and horses.index(pocket) < horses.index(leader)) else None
    if diver:
        diver["trip"] += ", passing lane"
    for call, frac in ((5, 0.55), (6, 1.0)):
        placed = []
        for h in sorted(horses, key=lambda h: fin[h["name"]]):
            l4, b4 = pos[h["name"]][4]
            b = b4 + (fin[h["name"]] - b4) * frac
            lane = l4 if call == 5 else pos[h["name"]][5][0]
            if h is diver:
                placed.append((-1.0, b)); pos[h["name"]][call] = (-1.0, round(b, 2)); continue
            if call == 5 and h in flow and flow.index(h) > 0 and n >= 6:
                lane = 2.0
            while any(pl == lane and abs(pb - b) < 1.2 for pl, pb in placed) and lane < 2:
                lane += 1.0
            placed.append((lane, b))
            pos[h["name"]][call] = (lane, round(b, 2))
    for call in (5, 6):
        for _ in range(n):
            moved = False
            for h in horses:
                if h is diver:
                    continue
                lh, bh = pos[h["name"]][call]
                passed = [p for p in horses if p is not h and p is not diver and pos[p["name"]][call - 1][1] < pos[h["name"]][call - 1][1] and pos[p["name"]][call][1] > bh]
                need = max((pos[p["name"]][call][0] + 1 for p in passed), default=lh)
                if need > lh and need <= 4:
                    pos[h["name"]][call] = (float(need), bh); moved = True
            if not moved:
                break
        if call == 5:
            for h in horses:
                pos[h["name"]][6] = (max(pos[h["name"]][6][0], pos[h["name"]][5][0]), pos[h["name"]][6][1])
    rows = []
    for place, h in enumerate(horses, 1):
        p = pos[h["name"]]
        rows.append(dict(h, behind=[round(p[c][1], 2) for c in range(7)], lane=[p[c][0] for c in range(7)], place=place,
                         time=S.fifth(final + fin[h["name"]] * S.LEN * final / 5280.0)))
    caps = [[0.0, "They're away"], [gate_t, f"{leader['name']} leaves for the lead"]]
    if first_over:
        caps.append([tt[2] * 0.9, f"{first_over['name']} pulls first-over"])
    caps.append([tt[2], f"Half in {S._mt(tt[2])}, {leader['name']} in front"])
    caps.append([tt[3], f"Three-quarters in {S._mt(tt[3])}"])
    if diver:
        caps.append([calls_t[5] - 2, f"{diver['name']} dives up the passing lane"])
    elif win is not leader:
        caps.append([calls_t[5], f"{win['name']} comes with a run"])
    caps.append([tt[4], f"{win['name']} wins it in {S._mt(final)}"])
    return {"track": track, "calls": calls_t, "quarters": [S.fifth(q) for q in tt], "horses": rows, "captions": caps,
            "final": S.fifth(final), "passing": bool(passing)}
