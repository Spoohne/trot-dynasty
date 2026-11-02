# race3: cooperative merging (draft for review 15)

**The problem (DECISIONS 130–132).** Admission rules for one horse at a time give a trade-off with no good setting:
- **A margin big enough to be safe** gives zero breaches, but no passing and no sorting at the gate (four-wide on
  turns, about 330 abandoned changes a race).
- **A margin small enough to pass** gives the following horse more braking than it can do (about 125 breaches per
  12 half-mile races).

In real racing a merge involves two drivers: the horse coming over and the horse it ends up in front of. The second
one either lets it in or doesn't.

## Terms
- **M**: the horse changing lanes, one lane at a time (already the rule).
- **Destination band**: the lane M is heading into.
- **F**: the nearest body ahead of M's slot in the destination band.
- **B**: the nearest body behind M's slot in the destination band.
- **Clear-by**: M's nose is ahead of B's nose by at least `BODY_L + HEAD + v_B·T_REACT` (about a length and a half
  at race pace). This is the physical meaning of "clear" when a horse crosses in front (rule 0.21).

## Protocol (every step, resolved jointly before any horse moves)
1. **Requests.** A driver that wants a new line (the gate sort, a slot, pulling out to pass, dropping back in) asks
   for a merge into the next band. A request names M, the band, B and F as they stand.
2. **Pre-checks** (geometry only, nothing negotiable):
   - M is no closer to F than the following rule allows, `need_gap(M, F)`, through the time it takes to cross;
   - the merge doesn't break the turn width cap (rule 0.4);
   - and, in the stretch or moving inward in front of a horse, M is clear-by B (rule 0.21).
3. **B's answer** (B's driver decides; it serves only its own horse):
   - **Yield** when B is sitting or leading at its steady pace, and opening the gap costs it no more than one
     position. B eases at no more than `A_YIELD` (2.5 ft/s², well under the 8 ft/s² braking limit) until
     `gap ≥ need_gap(B, M)`.
   - **Refuse** when B is itself moving or driving for that space, when M isn't clear-by and B would have to give up
     its position, or at the gate when B holds its spot and M isn't clear. A refusal is an event for M: a cooldown
     on that merge, then it drops back for the next gap (no endless retries).
   - **Feasibility:** B must be able to open the needed gap at ≤ A_YIELD before M finishes crossing. If it can't, the
     answer is refuse.
4. **Conflicts.** Two requests for the same slot, or for each other's lanes: the earlier request wins, then the one
   further ahead, then the one nearer the rail. Never list order, never post. The other waits.
5. **Commit.** A granted merge is a pair `(M, B, band, until)`:
   - B's forward controller targets M as the body ahead for the whole merge, so the yield is part of the pace.
   - M moves sideways with the swept and stopping-distance checks against everyone except B, whose gap the yield
     handles. M can't be redirected.
   - If something enters the corridor, M pauses its sideways motion as before. If the pause outlasts the merge
     window, both release and M settles in the nearest lane it holds.
6. **Forward pass.** Front to back as now; breaches stay hard failures.

## What this should change (predictions to test)
- Breaches near zero without the big margin: the space is opened deliberately, not assumed.
- The gate sorts: outside horses get in where inside horses are sitting and choose to let them, and drop back where
  they aren't.
- Passing and pulling out work, because the outer band usually has no B, or a B that isn't moving.
- Fewer abandoned changes: a refusal is an answer, not three seconds of trying.

## Questions for review
1. Is the pair protocol sound as a safety invariant (B's yield decel ≪ BRAKE; M's checks against all others)?
   What can still break it: three-way merges, a B that breaks stride, a cascade behind B?
2. B's yield-or-refuse policy: is "costs no more than one position" a good line, and how do I stop a merge
   cascade turning the line into a slinky?
3. Is clear-by (about a length and a half) the right physical rule for inward merges, and should outward merges
   (pulling out) skip it?
4. Deadlocks: two horses each waiting for the other's lane, the gate's eight-wide sort, a pocket horse and the horse
   outside it.
5. Acceptance tests for the merge layer before any tuning resumes.

---

## v2 after review 15 (accepted; this replaces the pair protocol above)

**Cooperation is a driver choice, never a safety guarantee.**

**Lane changes run as `REQUESTED → PREPARING → COMMITTED → COMPLETE`:**
1. **Snapshot** every body, driver state and reservation.
2. **Request:** the horse names the next lane and a slot. The horses ahead and behind are the slot's edges, not
   the only horses affected.
3. **Prepare:** the horse stays in its own lane and adjusts its pace. The horse behind may choose to ease (the
   cooperation, added later). It can cancel here.
4. **Commit** only if the whole path is safe for everyone affected, from first contact (about 1.7 ft of sideways
   motion) through completion, with a workable emergency fallback:
   - the follow chain in both lanes;
   - the horse ahead breaking stride, or the mover breaking;
   - the turn geometry.
5. **Execute:** the destination is fixed. Both lanes stay reserved until the horse is physically clear of the old
   one. Only the pace is re-planned. An emergency can delay completion but never cancels the commitment.
6. **Complete:** the old lane is released.

**Other rules:**
- A conflict graph picks the compatible requests. Each horse holds at most one active maneuver role.
- Arbitration is stable and logged: physical commitments first, then the feasible requests. Stale requests expire.
  The "nearer the rail" priority is avoided, because it is a geometric bias.
- Inward and outward moves need the same rear safety: the braking-safe gap from first overlap, plus front clearance.
- A move into an empty lane needs no clear-by and no fictional horse behind it.
- **In the stretch, no cutting:** a horse can't make a rival brake to give it the room to cross.

**Build order:**
1. Prepare-then-reserve with full-body checks, no negotiation yet.
2. Prove passing into gaps that are already there.
3. Then add yielding as a driver choice:
   - B's options: hold, take useful cover, avoid a costly contest, concede a slot M gets anyway;
   - a cumulative yield budget with a recovery interval;
   - no promises to several movers at once;
   - the follow chain checked.

**The start:**
- The merge layer can't guarantee rule 0.6 on its own. A gate-sorting planner reserves real slots early.
- Outside horses take back and enter behind when the inside driver holds its spot.
- Patrick's working-in exception still applies.

**The pocket:** a pocket horse that's denied room stays stuck, without chatter. The cooldown applies to that
opportunity, not to the whole lane.

**Acceptance (zero tolerance, all before tuning resumes):**
- **Hard mechanics:** zero overlaps, braking or lateral breaches, and commitment reversals, in these cases:
  - first-contact boundaries;
  - a break at every stage of a merge;
  - follow chains;
  - two horses wanting one slot, opposite swaps, three requests at once;
  - turn entry and exit, and the stretch fan;
  - an interrupted reservation;
  - finishing and the run-out.
- **Progress controls**, so safety can't pass by freezing the field:
  - passing into an empty lane;
  - entering an adequate gap without anyone yielding;
  - preparing a gap and completing;
  - a refusal giving a stable hold or another slot;
  - the eight-abreast gate sort;
  - the pocket opening, and the pocket staying blocked without chatter.
- **Numerical:** order and tie tests, DT 1/8 / 1/16 / 1/32 convergence, continuous swept-body checks, an auditor on
  unrounded trajectories.

**Code defects to fix alongside:**
- the `held_speed` cache key (False collides with 0.0);
- rail-coordinate braking, for both curvature and lateral motion;
- the forward pass mixing time levels (freeze who interacts with whom);
- `lc` clamping and abandon-to-nearest-lane, which redirect a commitment;
- lateral arrival (a bounded profile, not a snap).
