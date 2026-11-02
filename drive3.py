"""The race3 driver (lab): one per horse, serving only its own horse (ENGINE_SPEC items 17A, Part 0; DESIGN_V3 §11.7).
Before the gate each driver reads its horse and the field and picks an aim (top, pocket, first-over, follow, close),
best-response passes so drivers answer each other. In the race it is an event-gated state machine: it looks every
sixteenth and the moment something happens (a hole, cover going by, a rival alongside, over budget, the leader
tiring), commits to a change for a while, closes a failed opportunity until something changes, and runs continuous
controllers for pace, following gap and line. Every choice is logged with its reason.
    driver = Driver(); race3.run(field, track, driver, seed)"""
import random
import race3 as R

AIMS = ("top", "pocket", "first_over", "follow", "close")
# Every setting here is a driver habit, tuned to the spec's results (stage 4-5); none is a bonus for any horse or post.
D = dict(
    # gate scoring: a driver's read of its horse against this field
    s_top=1.5, s_top_short=6.0, s_top_post=0.9, s_top_post_half=-0.51, s_top_rival=1.2, s_top_cruise=0.8,
    s_pocket=3.0, s_pocket_short=2.5, s_pocket_post=0.30, s_pocket_rival=1.0,
    s_fo=1.0, s_fo_cruise=1.0, s_fo_rival=0.6,
    s_follow=0.8, s_follow_kick=0.8, s_follow_rival=1.0,
    s_close=0.4, s_close_kick=1.2, s_close_half=0.6, s_close_rival=0.4,
    passes=3,
    # execution
    leave_budget=3.0,            # reserve a horse will spend trying for the top (x (1 + cruise/2))
    park_budget=2.5,             # reserve spent parked without cover before the driver takes back (rule 0.8)
    breather=1.6,                # ft/s an unpressed leader backs off its sustainable pace (rule 0.9)
    dig=2.0,                     # ft/s a pressed leader picks it up (pace comes from the race: DECISIONS 180)
    press_margin=0.3,            # a leaver that can't clear presses instead of taking back when its gate+cruise is within this of the leader's
    press_budget=2.0,            # reserve a presser will spend on the leader's flank (x (1 + cruise/2)) before it takes back
    sit_gap=0.5,                 # clear lengths a sitter keeps behind the horse in front: the line is tight
    follow_k=0.075,               # ft/s per ft off the wanted gap: a sitter closes or opens the gap firmly
    follow_look=0.0,             # s ahead a sitter reads the horse in front's speed change (no lag, no accordion)
    follow_band=0.0,             # ft either side of the wanted gap a sitter just matches the horse in front
    pace_rate=0.5,               # ft/s per s a pace-setter changes its pace: smooth, so the line behind doesn't accordion (DECISIONS 203)
    sit_room=1.0,                # ft over the safe following gap a sitter keeps, so the horse in front can still pull out on a turn
    close_take_back=2.0,         # ft/s more a closer eases at the start, to settle near the back
    move_fo=0.55,                # first-over moves from this share of the mile
    drive_ft=1400.0,             # everyone goes for home from about the three-quarters
    advance=2.0,
    press=1,                     # 1: a first-over horse that gets alongside sits on the leader's flank; 0: it keeps going
    lead_push=2.5,               # ft/s a pace-setter runs above what it can hold: a true race pace (DECISIONS 189)
    lead_push_mile=0.5,          # extra lead_push on the mile (fitted)
    lead_held=1,                 # 1: a leader paces at what it can hold right there (turns included), not straight-line pace                 # ft/s a first-over horse gains on the leader as it comes up to press him
    commit_s=4.0,
    line_hold_s=4.0,
    turn_look=600.0,             # ft before a turn a driver stops going four wide (time to pass and get back in)             # a driver holds a new line at least this long before coming back in                # a non-safety change holds at least this long (rule 0.14)
    lock_s=3.0,                  # s a sitter waits beside a horse it can't get in on before tucking in behind it
    cooldown_s=12.0,             # a failed opportunity stays closed this long unless something changes (rule 0.15)
    yield_ft_s=1.5,
    leave_until=0.3,
    leave_push=3.0,              # ft/s over its steady pace a leaver brushes at until it's clear             # a leaver keeps at it to here (clearing around the first turn), unless it gives up first              # how much a horse that isn't going for the lead eases to let a leaver cross in front
    gate_pace=0.0,               # ft/s per point of gate a non-leaver uses to find its spot at the start (fitted, stage 3)
    gate_take_back=0.0,          # no easing by lane at the start: a horse not leaving still goes at race speed (DECISIONS 198)
    ease_out=1.0,                # ft/s under the horse in front a boxed horse eases to make room to pull out
    start_floor=0.92,            # share of its steady pace a horse easing at the start never goes under (rule 0.10)
    local_leave=1,               # stage A: a horse leaves when it's quicker than every horse inside it (DRIVER_V4_PLAN A, DECISIONS 197)
    rail_look=2,                 # the rail horse leaves unless one of this many horses just outside it is quicker
    leave_look=2,                # a horse leaves if it looks quicker than this many horses just inside it (DECISIONS 199)
    read_sd=0.15,
    pocket_wait_s=8.0,           # s a pocket-seeker keeps trying to get in behind the leader before settling in the line                # how far off a driver's read of a rival's gate speed can be
    budget=1,                    # Patrick (DECISIONS 201): every driver times its reserve to run out at the wire or a little before
    budget_margin=1.0,           # reserve a driver plans to cross the wire with
    budget_dt=0.5,               # s between a driver's looks at its tank
    rank_post=0.15,              # the start's pecking order: gate minus this per post out (farther to cross); drivers yield only upward (DECISIONS 193)
    gate_drop=1.5,               # ft/s under the horse inside an outside horse eases to, to drop in behind it before the turn          # ft/s per lane out a non-leaver eases at the start, to slide in (rule 0.6)
)


class Driver:
    def __init__(self, gate_aims=None, **over):
        self.d = dict(D, **over)
        self.state = {}
        self.gate_aims = gate_aims or {}             # tests: hold given horses to these gate aims (events still fire)

    # ---------------- before the gate
    def plan(self, field, track):
        d = self.d
        g = sorted((h.t["gate"] for h in field), reverse=True)
        half = track.name == "half"
        aims = {}

        def score(h, aims):
            short = g[0] - h.t["gate"] if h.t["gate"] < g[0] else 0.0
            second = g[1] - h.t["gate"] if len(g) > 1 and h.t["gate"] < g[1] else 0.0
            same = lambda a: [o for o in field if o is not h and aims.get(o.name) == a]
            quicker = lambda a: sum(o.t["gate"] > h.t["gate"] - 0.1 for o in same(a))
            pp = (h.post - 1) * (1 + (d["s_top_post_half"] if half else 0))
            return dict(
                top=d["s_top"] - d["s_top_short"] * short - d["s_top_post"] * pp - d["s_top_rival"] * quicker("top") + d["s_top_cruise"] * h.t["cruise"],
                pocket=d["s_pocket"] - d["s_pocket_short"] * second - d["s_pocket_post"] * pp - d["s_pocket_rival"] * quicker("pocket"),
                first_over=d["s_fo"] + d["s_fo_cruise"] * h.t["cruise"] - d["s_fo_rival"] * len(same("first_over")),
                follow=d["s_follow"] + d["s_follow_kick"] * h.t["kick"] - d["s_follow_rival"] * len(same("follow")),
                close=d["s_close"] + d["s_close_kick"] * h.t["kick"] - (d["s_close_half"] if half else 0) - d["s_close_rival"] * len(same("close")))
        self.rank = {h.name: r for r, h in enumerate(sorted(field, key=lambda h: (-(h.t["gate"] - d["rank_post"] * (h.post - 1)), h.post)))}
        order = sorted(field, key=lambda h: (-h.t["gate"], h.name))
        for _ in range(d["passes"]):
            new = {h.name: max((sc := score(h, aims)), key=sc.get) for h in order}
            aims = new                                     # everyone answers the same picture, then all commit
            aims.update(self.gate_aims)
        if d["local_leave"]:                               # stage A: leave or tuck, judged against the horses next to it
            by_post = sorted(field, key=lambda h: h.post)
            rng = random.Random(round(sum(h.t["gate"] * h.post for h in field), 9))   # this race's reads: a driver knows its own horse, guesses the rest
            read = {(h.name, o.name): o.t["gate"] + rng.gauss(0.0, d["read_sd"]) for h in field for o in field if o is not h}
            for h in by_post:
                if h.post == 1:                            # the rail horse goes unless a horse just outside looks quicker
                    goes = all(h.t["gate"] >= read[(h.name, o.name)] for o in by_post[1:1 + d["rail_look"]])
                else:                                      # anyone else goes if it looks quicker than the horses just inside it
                    goes = all(h.t["gate"] > read[(h.name, o.name)] for o in by_post[max(0, h.post - 1 - d["leave_look"]):h.post - 1])
                if goes:
                    aims[h.name] = "top"
                elif aims[h.name] == "top":
                    aims[h.name] = "pocket"                # not quick enough to clear: tuck in behind the speed
            aims.update(self.gate_aims)
        for h in field:
            self.state[h.name] = dict(aim=aims[h.name], since=0.0, closed={}, att_e=h.E, park_e=0.0, phase="leave",
                                      last16=-1, e_last=h.E, follow=None, trip=[f"gate: {aims[h.name].replace('_', '-')}"])
        return aims

    def change(self, h, st, aim, t, why, rec, safety=False):
        if aim == st["aim"]:
            return
        if not safety and t - st["since"] < self.d["commit_s"]:
            return
        if not safety and st["closed"].get(aim, -1) > t:
            return
        rec["events"].append((round(t, 2), h.name, f"{st['aim']} -> {aim}: {why}"))
        rec.setdefault("aim_changes", []).append(dict(t=round(t, 2), h=h.name, old=st["aim"], new=aim, why=why, safety=safety))
        st["trip"].append(f"{round(h.s / R.FT_MILE, 2)}: {why}, {aim.replace('_', '-')}")
        st.update(aim=aim, since=t, att_e=h.E, park_e=0.0, follow=None)

    def line(self, h, st, live, track, cap):
        """The line for a horse that's going: outside whatever is slower in front of it, committed once chosen, and
        back in toward the rail as soon as that costs nothing (rules 0.3, 0.5, 0.18, 0.20)."""
        band = lambda y: [o for o in live if o is not h and abs(o.y - y) < R.BODY_W + R.Y_PAD]
        lane_y = lambda k: R.RAIL_Y + R.LANE * k
        k_now = round((h.y - R.RAIL_Y) / R.LANE)
        slower_ahead = lambda y: [o for o in band(y) if 0 < o.s - R.BODY_L - h.s < 3 * R.LENGTH
                                  and (o.v < cap - 0.3 or o.ceiling() < cap - 0.3 or (abs(y - h.y) < 1 and h.blocked))]
        free_beside = lambda y: not [o for o in band(y) if -R.BODY_L - R.merge_gap(o.v, h.v) - 1 < o.s - h.s < R.BODY_L + R.merge_gap(h.v, o.v) + 1]
        if st["aim"] == "pocket" and h.s < track.last_turn_end - 100:
            return lane_y(0)                               # the pocket waits for the stretch (rule 0.18)
        next_turn = min((a - h.s for a, b in track.arcs if a >= h.s), default=1e9)
        turnish = track.on_turn(h.s) or next_turn < self.d["turn_look"]   # no fourth lane it can't get back from before a turn
        widest = 2 if turnish else round((track.max_y(h.s) - R.RAIL_Y) / R.LANE)   # turns: three-wide at most (rule 0.4)
        y = st.get("move_y", h.y)
        if (track.min_y(h.s) < R.RAIL_Y and h.y < R.RAIL_Y + 1 and h is not max(live, key=lambda o: o.s)
                and slower_ahead(h.y) and not slower_ahead(lane_y(-1)) and free_beside(lane_y(-1))):
            st["move_y"], st["line_t"] = lane_y(-1), st.get("now", 0)   # boxed on the rail in the stretch: up the passing lane (never the leader)
            return lane_y(-1)
        if k_now > widest:
            y = lane_y(widest)                             # coming into a turn wide: work back in
        if slower_ahead(y) or st.get("move_y") is None:
            for k in range(k_now + (1 if slower_ahead(h.y) or st.get("move_y") is None and st["aim"] == "first_over" else 0), k_now + 4):
                if k > widest:
                    break
                if not slower_ahead(lane_y(k)) and (k == k_now or free_beside(lane_y(k))):
                    y = lane_y(k)
                    break
        settled = st.get("line_t", -99) + self.d["line_hold_s"] <= st.get("now", 0)
        if (k_now > 0 and settled and not slower_ahead(lane_y(k_now - 1)) and free_beside(lane_y(k_now - 1))
                and not slower_ahead(h.y) and abs(h.y - y) < 1):
            y = lane_y(k_now - 1)                          # nothing gained outside, for a while now: drop back in
        if abs(y - st.get("move_y", h.y)) > 1:
            st["line_t"] = st.get("now", 0)                # a new line: hold it a few seconds (rule 0.3, no weaving)
        st["move_y"] = y
        return y

    def slot(self, h, live, urgent=False):
        """A horse outside the line picks the nearest gap in the lane just inside it that it can fit (the back of the
        line always fits) and paces itself to it; the lane change itself waits for the safety layer to say it's clear."""
        k_in = max(0, round((h.y - R.RAIL_Y) / R.LANE) - 1)
        y_in = R.RAIL_Y + R.LANE * k_in
        line = sorted((o for o in live if o is not h and abs(o.y - y_in) < R.BODY_W), key=lambda o: -o.s)
        slots = []                                          # (nose position to aim for, pace there)
        for a, b in zip([None] + line, line + [None]):
            front_s = a.s - R.BODY_L - R.merge_gap(h.v, a.v) - 1 if a else h.s + 4 * R.LENGTH
            back_s = b.s + R.BODY_L + R.merge_gap(b.v, h.v) + 1 if b else -1e9
            if front_s > back_s:
                aim_s = min(front_s, max(back_s, h.s))
                slots.append((abs(aim_s - h.s), aim_s, a.v if a else (b.v if b else h.v_sus)))
        if not slots:
            return None, y_in
        _, aim_s, pace = min(slots)
        return pace + max(-6.0 if urgent else -2.5, min(1.5, 0.5 * (aim_s - h.s) / R.LENGTH)), y_in   # urgent: four-wide into a turn otherwise

    # ---------------- every step
    def __call__(self, field, track, t, rec):
        """All drivers read the same picture (the field and every driver's phase as they stood), then all commit."""
        d = self.d
        dt = rec["dt"]
        if not self.state:
            self.plan(field, track)
            rec["plans"] = {h.name: self.state[h.name]["aim"] for h in field}
        live = [h for h in field if not h.done]
        if not live:
            return
        phase0 = {n: st_["phase"] for n, st_ in self.state.items()}
        lead = max(live, key=lambda o: (o.s, -o.y, o.name))         # ties: the horse nearer the rail
        turn_in = turn_in_ = track.arcs[0][0]
        ahead_of = lambda o, h: self.rank[o.name] < self.rank[h.name]   # the start's pecking order: yield only to a horse above
        drive = lead.s >= R.FT_MILE - d["drive_ft"]                  # the field goes when the leader reaches the drive point
        push = d["lead_push"] + (d["lead_push_mile"] if track.name == "mile" else 0.0)   # big tracks race to a stiffer pace
        cmds = {}
        for h in live:
            st = self.state[h.name]
            st["now"] = t
            f = h.s / R.FT_MILE
            ahead = [o for o in live if o is not h and o.s > h.s and abs(o.y - h.y) < R.BODY_W + R.Y_PAD]
            front = min(ahead, key=lambda o: (o.s, o.y), default=None)
            gap_len = (front.s - R.BODY_L - h.s) / R.LENGTH if front else 99.0
            covered = front is not None and gap_len < 1.5
            parked = h.y > R.RAIL_Y + 2 and not covered
            if parked and phase0[h.name] in ("sit", "lead"):   # what being parked costs: the air a horse in cover wouldn't pay
                st["park_e"] += R.C_AIR * R.P["pace_k"] * h.v ** 3 * (1 - R.DRAFT) * dt
            inside_free = h.y > R.RAIL_Y + 1 and not [o for o in live if o is not h and h.y - R.LANE - 1 < o.y < h.y - 1
                                                       and abs(o.s - h.s) < R.BODY_L + R.HEAD + 3]
            alongside_lead = [o for o in live if o is not lead and abs(o.s - lead.s) < R.BODY_L * 0.8 and o.y > lead.y + 2]
            stam = 1 + 0.5 * h.t["cruise"]
            crossing = [o for o in live if o is not h and o.y > h.y + 1 and -R.BODY_L * 0.5 < o.s - h.s < R.BODY_L * 2.5
                        and ((phase0[o.name] == "leave" and self.state[o.name]["aim"] == "top") or (o.s < turn_in_ and ahead_of(o, h)))]   # a horse above it in the pecking order coming over: let it in
            # ---- events
            if st["aim"] in ("top", "pocket") and phase0[h.name] == "leave" and h is not lead:
                inside_level = [o for o in live if o is not h and o.y < h.y - 1 and h.s - o.s < R.BODY_L + R.need_gap(o.v, h.v) + 2]
                moving_in = (h.man and h.man["dest"] < h.y) or (h.req and h.req[1] is not None and h.req[1] < h.y)
                four_wide = h.y > R.RAIL_Y + 3 * R.LANE - 0.5 and not moving_in   # stuck in the fourth lane (working in is allowed: rule 0.6)
                taken = st["aim"] == "pocket" and [o for o in live if o is not h and o is not lead and o.y < R.RAIL_Y + 1
                                                  and 0 < lead.s - o.s < R.BODY_L + 2 * R.LENGTH]   # someone's already in the pocket
                spent = st["aim"] == "top" and st["att_e"] - h.E > d["leave_budget"] * stam   # a leaver's effort; a pocket-seeker sits behind
                stuck = st["aim"] == "pocket" and t - st["since"] > d["pocket_wait_s"]       # couldn't get in: settle in the line
                at_turn = h.s >= turn_in - 30 and inside_level      # reached the turn without clearing the horse inside
                if (st["aim"] == "top" and (at_turn or spent)) or (st["aim"] == "pocket" and ((at_turn and four_wide) or taken or stuck)):
                    st["closed"][st["aim"]] = t + d["cooldown_s"]       # couldn't clear by the turn
                    mine, his = h.t["gate"] + h.t["cruise"], lead.t["gate"] + lead.t["cruise"]
                    if st["aim"] == "top" and mine >= his - d["press_margin"] and "press" not in st["closed"]:
                        self.change(h, st, "press", t, f"couldn't clear {lead.name}, pressed him", rec, safety=True)
                        st.update(phase="move", rival=lead.name, press_e=h.E)   # a battle for the lead: the pace goes hot
                    else:
                        free = not [o for o in live if o is not h and o is not lead and o.y < R.RAIL_Y + 1
                                    and 0 < lead.s - o.s < R.BODY_L + 2 * R.LENGTH]   # nobody in the pocket yet
                        if st["aim"] == "top" and free:          # take the open pocket behind the horse that beat it out
                            self.change(h, st, "pocket", t, f"couldn't clear {lead.name}, took the pocket", rec, safety=True)
                            st.update(phase="leave", att_e=h.E)
                        else:
                            self.change(h, st, "follow", t, f"couldn't clear {lead.name}, took back", rec, safety=True)   # rule 0.8
                            st["phase"] = "sit"
            if parked and phase0[h.name] == "sit" and st["park_e"] > d["park_budget"] * stam and st["aim"] in ("top", "pocket", "follow", "first_over"):
                st["closed"][st["aim"]] = t + d["cooldown_s"]
                self.change(h, st, "close" if st["aim"] != "first_over" else "follow", t, "parked too long, took back", rec, safety=True)
            if st["aim"] in ("follow", "close") and phase0[h.name] == "sit" and f > 0.35 and not drive:
                by = sorted((o for o in live if phase0[o.name] == "move" and o.y > h.y + 3 and 0 < o.s - h.s < R.BODY_L * 2.2),
                            key=lambda o: (o.s - h.s, o.y))
                if by and (st["aim"] == "follow" or f > 0.6):
                    st["phase"], st["follow"] = "move", by[0].name
                    st["trip"].append(f"{round(f, 2)}: followed {by[0].name} out")
                    rec["events"].append((round(t, 2), h.name, f"followed {by[0].name}'s cover"))
            if st["aim"] == "press" and phase0[h.name] == "move" and not drive:
                if st["press_e"] - h.E > d["press_budget"] * stam:
                    st["closed"]["press"] = t + 999
                    self.change(h, st, "follow", t, f"couldn't get by {st['rival']}, took back", rec, safety=True)
                    st["phase"] = "sit"
                elif h is lead and not [o for o in live if o is not h and h.s - o.s < R.BODY_L + R.need_gap(o.v, h.v) + 2]:
                    self.change(h, st, "top", t, f"cleared {st['rival']}, took the lead", rec, safety=True)
                    st["phase"] = "lead"
            if st["aim"] != "top" and h is lead and h.s > track.arcs[0][1] and h.y < R.RAIL_Y + 1 and phase0[h.name] == "sit":
                self.change(h, st, "top", t, "found the lead, kept it", rec, safety=True)   # nobody went: it's on top, so it rates
            if st["aim"] in ("first_over", "follow", "top") and parked and inside_free and phase0[h.name] == "sit" and h is not lead and h.s > track.arcs[0][1]:
                self.change(h, st, "pocket" if lead.y < h.y and abs(lead.s - h.s) < R.BODY_L * 3 else "follow", t, "a hole opened, dropped in", rec)
            # ---- the sixteenth look (rule 0.14): only when something calls for it
            n16 = int(f * 16)
            if n16 != st["last16"]:
                st["last16"] = n16
                moved = any(phase0[o.name] == "move" for o in live)
                rail_order = sorted((o for o in live if o.y < R.RAIL_Y + 2), key=lambda o: -o.s)
                place = rail_order.index(h) if h in rail_order else 99
                room_out = not [o for o in live if o is not h and h.y + 1 < o.y < h.y + R.LANE + 1 and abs(o.s - h.s) < R.BODY_L * 2]
                if (st["aim"] in ("follow", "close") and phase0[h.name] == "sit" and 0.5 <= f < 0.7 and not moved
                        and h.E > 0.7 * R.P["e_max"] and h is not lead and 2 <= place <= 5 and room_out):   # from mid-pack, not the pocket
                    self.change(h, st, "first_over", t, "nobody moved, went first-over", rec)
                if st["aim"] == "pocket" and phase0[h.name] == "sit" and front is not None and front is not lead and h.s > turn_in + 300:
                    self.change(h, st, "follow", t, "not in the pocket, sat in the line", rec)
            # ---- phase from the aim
            clear = h is lead and not [o for o in live if o is not h and h.s - o.s < R.BODY_L + R.need_gap(o.v, h.v) + 2]
            tucked = st["aim"] == "pocket" and h.y < R.RAIL_Y + 1 and front is lead     # the pocket is its: on the rail at the leader's back
            if st["phase"] == "leave" and (f > d["leave_until"] or (clear and h.y < R.RAIL_Y + 1) or tucked or st["aim"] not in ("top", "pocket")):
                st["phase"] = "lead" if (st["aim"] == "top" and h is lead) else "sit"
            if drive and st["phase"] != "drive":
                st["phase"] = "drive"                              # everyone goes for home together
            if st["aim"] == "first_over" and st["phase"] == "sit" and f >= d["move_fo"] and any(phase0[o.name] == "move" for o in live if o is not h):
                self.change(h, st, "follow", t, "someone's already first-over, waits for cover", rec, safety=True)   # one horse is first-over
            if st["aim"] == "first_over" and st["phase"] == "sit" and f >= d["move_fo"]:
                st["phase"] = "move"
                st["trip"].append(f"{round(f, 2)}: moved first-over")
                rec["events"].append((round(t, 2), h.name, "pulled first-over"))
            if st["phase"] == "lead" and h is not lead:
                st["phase"] = "sit"
            if st["phase"] == "sit" and st["aim"] == "top" and h is lead:
                st["phase"] = "lead"
            # ---- controllers: pace and line
            cap = h.ceiling()
            if h.s < turn_in and st["aim"] != "top" and st["phase"] != "leave":   # the start, to the first turn: find the rail without a fight
                lane = (h.y - R.RAIL_Y) / R.LANE
                v = (h.v_sus + 1.0 + d["gate_pace"] * h.t["gate"] - d["gate_take_back"] * lane      # a quicker horse settles further up
                     - (d["close_take_back"] if st["aim"] == "close" else 0.0))
                inside = [o for o in live if o is not h and o.y < h.y - 1 and -R.BODY_L - R.HEAD - 2 < o.s - h.s < R.BODY_L + R.HEAD + 2
                          and ahead_of(o, h)]                     # a horse above it in the pecking order, inside it: drop in behind
                if inside:
                    v = min(v, min(o.v for o in inside) - d["gate_drop"])   # can't cross in front: drop in behind, soon
                if crossing:                                    # a quicker horse is coming across: let it in (rule 0.7)
                    v = min(v, min(o.v for o in crossing) - d["yield_ft_s"])
                cmds[h.name] = dict(v=max(v, d["start_floor"] * h.v_sus), y=R.RAIL_Y)   # eases, never pulls up (rule 0.10): no chain down the gate
                continue
            if st["aim"] != "top" and st["phase"] == "sit" and f < d["leave_until"] and crossing:
                cmds[h.name] = dict(v=min(o.v for o in crossing) - d["yield_ft_s"], y=R.RAIL_Y)   # still letting it across
                continue
            if st["phase"] == "leave" and st["aim"] == "pocket":   # gate speed buys the spot at the leader's back: get to it, then sit there
                spot = lead.s - R.BODY_L - R.need_gap(h.v, lead.v) - d["sit_room"]
                if h is lead:                                    # out in front by mistake: ease and let the speed go by
                    v = h.v_sus - 2.0
                else:
                    v = lead.v + max(-3.0, min(d["leave_push"], 0.5 * (spot - h.s)))    # level with the leader: drop in behind it
                cmds[h.name] = dict(v=min(cap, v), y=R.RAIL_Y)
            elif st["phase"] == "leave":                        # going for the top: a hard brush, not flat out
                cmds[h.name] = dict(v=min(cap, h.v_sus + d["leave_push"]), y=R.RAIL_Y)
            elif st["phase"] == "lead":
                quarter2 = 0.25 <= f < 0.5
                base = (R.held_speed(h, duel=False) if d["lead_held"] else h.v_sus) + push   # lead_held: the pace it can hold here
                v = base + (d["dig"] if alongside_lead else (-d["breather"] if quarter2 else 0.0))   # pressed: dig in; clear: rate it
                if not alongside_lead:                          # a smooth pace: the line behind it can follow without braking
                    prev = st.get("pace_v", h.v)
                    v = max(prev - d["pace_rate"] * dt, min(prev + d["pace_rate"] * dt, v))
                st["pace_v"] = v
                cmds[h.name] = dict(v=min(v, cap), y=R.RAIL_Y)
            elif st["phase"] == "sit":
                tgt = front                                     # only a horse in its own line: never a rival in another lane
                headed = st["aim"] == "top" and [o for o in live if o is not h and 0 < o.s - h.s < R.BODY_L * 0.8 and 2 < o.y - h.y < R.LANE + 2]
                if tgt is None and headed:                      # headed on the inside: it fights back
                    v = R.held_speed(h, duel=False) + push + d["dig"]
                elif tgt is None:                               # nobody in front in its line: it sets a fair pace for here
                    v = (R.held_speed(h, duel=False) if d["lead_held"] else h.v_sus) + push - (d["breather"] if 0.25 <= f < 0.5 and not alongside_lead else 0.0)
                else:
                    want = max(d["sit_gap"] * R.LENGTH, R.need_gap(h.v, tgt.v) + d["sit_room"])   # ft: tight, inside the draft
                    err = gap_len * R.LENGTH - want
                    err = 0.0 if -d["follow_band"] < err < d["follow_band"] else err   # small wobbles: just match its speed
                    v = tgt.v + tgt.a * d["follow_look"] + max(-3.0, min(3.0, d["follow_k"] * err))   # steady following (DECISIONS 203)
                    if tgt.req and tgt.req[1] > tgt.y + 1 and tgt.why_not.startswith(h.name + " too close behind"):
                        v = min(v, tgt.v - d["ease_out"])         # the horse in front is waiting to pull out: give it room
                cutting = [o for o in live if o.why_not == f"no room in front of {h.name}" and o.s - h.s > R.BODY_L and h.y < o.y < h.y + R.LANE + 1]
                if cutting:                                     # a horse clear ahead is waiting to come over: don't run up on it
                    v = min(v, min(o.v for o in cutting) - d["ease_out"])
                y_in = R.RAIL_Y
                if h.y > R.RAIL_Y + 1:                          # outside the line: head for a real gap in the lane inside
                    nt = min((a - h.s for a, b in track.arcs if a >= h.s), default=1e9)
                    v_slot, y_in = self.slot(h, live, urgent=h.y > R.RAIL_Y + 2 * R.LANE + 1 and nt < d["turn_look"])
                    v = v_slot if v_slot is not None else v
                if h.req and t - h.req[0] > d["lock_s"] and h.why_not.endswith(" alongside"):   # locked beside a horse it can't get in on: tuck behind it
                    beside = next((o for o in live if o.name == h.why_not.split(" ")[0]), None)
                    if beside is not None:
                        v = min(v, beside.v - 3.0)
                cmds[h.name] = dict(v=min(max(v, 0.8 * h.v_sus), cap), y=y_in)   # a sitter never pulls up (rule 0.10)
            elif st["phase"] == "move":                         # the positional move: up to the leader, then press it
                if st["follow"]:
                    cov = next((o for o in live if o.name == st["follow"]), None)
                    if cov and cov.s > h.s:
                        g = (cov.s - R.BODY_L - h.s) / R.LENGTH
                        cmds[h.name] = dict(v=min(cap, cov.v + max(-2.0, min(2.0, 0.8 * (g - 0.4)))), y=cov.y)
                        continue
                rival = next((o for o in live if o.name == st.get("rival")), None) if st["aim"] == "press" else None
                if rival is not None:                           # on the leader's flank, one lane out: head and head
                    y = max(R.RAIL_Y + R.LANE, rival.y + R.LANE) if h.s - rival.s < R.BODY_L + 2 else R.RAIL_Y
                    nt = min((a - h.s for a, b in track.arcs if a >= h.s), default=1e9)
                    if track.on_turn(h.s) or nt < d["turn_look"]:
                        y = min(y, R.RAIL_Y + 2 * R.LANE)       # three-wide at most on a turn (rule 0.4), even pressing
                    cmds[h.name] = dict(v=min(cap, rival.v + (0.3 if abs(rival.s - h.s) < R.BODY_L * 0.6 or h.s > rival.s else d["advance"])), y=y)
                    continue
                y = self.line(h, st, live, track, cap)
                level = lead.s - h.s < R.BODY_L * 0.6
                v = lead.v + (0.3 if level and d["press"] else d["advance"])   # come up alongside, then sit on his flank
                if front and y > h.y + 1 and h.why_not.startswith("too close behind"):
                    v = min(v, max(front.v - d["ease_out"], 0.9 * h.v))   # in tight: ease a touch to get out first
                cmds[h.name] = dict(v=min(cap, v), y=y)
            else:                                               # the drive: everyone goes for home
                if st["follow"]:
                    cov = next((o for o in live if o.name == st["follow"]), None)
                    if cov and cov.s > h.s and not cov.blocked and cov.v >= cap - 0.5:
                        g = (cov.s - R.BODY_L - h.s) / R.LENGTH
                        cmds[h.name] = dict(v=min(cap, cov.v + max(-2.0, min(2.0, 0.8 * (g - 0.4)))), y=cov.y)
                        continue
                    st["follow"] = None                         # cover's done its job: out and go
                y = self.line(h, st, live, track, cap)
                v = cap
                if front and y > h.y + 1 and h.why_not.startswith("too close behind"):
                    v = min(cap, max(front.v - d["ease_out"], 0.9 * h.v))   # boxed in tight: ease a touch to get out (no pressing)
                cmds[h.name] = dict(v=v, y=y)
        if d["budget"]:                                   # every driver paces to the wire: never asks for more than it can afford
            for h in live:
                st = self.state[h.name]
                if h.name in cmds and (st.get("aff_t", -9) + d["budget_dt"] <= t):
                    st["aff"], st["aff_t"] = R.afford_speed(h, track, d["budget_margin"]), t
                if h.name in cmds and "aff" in self.state[h.name]:
                    cmds[h.name]["v"] = min(cmds[h.name]["v"], max(self.state[h.name]["aff"], 0.8 * h.v_sus))
        for h in live:
            if h.name in cmds:
                h.cmd.update(cmds[h.name])
        rec["trips"] = {n: s_["trip"] for n, s_ in self.state.items()}
