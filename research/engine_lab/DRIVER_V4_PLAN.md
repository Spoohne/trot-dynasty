# Driver v4 plan: races that change shape (DECISIONS 194–195)

Patrick watched the test replay: "The horses run most of the race in sequential order, first through last." The
measurements say the same. This plan replaces local patching with a redesign of the driver's tactics around position
changes. The physics (race3), the safety layer and the true pace stay. Patrick's rule stands: the engine races the
actual horses; fix behavior, never add bonuses.

## 1. The problem, measured (`v3_churn.py`, 200 races per track, the committed engine)

| Measure | Half-mile | Mile | Reference (chart_targets.md) |
|---|---|---|---|
| Running order vs post order, Spearman (1 = identical) | 1/4 0.97 · 1/2 0.94 · 3/4 0.94 · finish 0.86 | 0.98 · 0.95 · 0.89 · 0.80 | none free |
| Order call to call (1 = no change) | 1/4→1/2 0.97 · 1/2→3/4 1.00 · 3/4→finish 0.89 | 0.97 · 0.97 · 0.84 | none free |
| Rail horse on the lead at the half | 97% | 90% | about 25% (Yonkers, Northfield) |
| Rail horse in the top three at the half | 100% | 100% | 79% half-mile (Yonkers), 37% bigger (Mohawk) |
| Outer two posts on the lead at the half | 0% | 2% | under 5% half-mile, about double on bigger tracks |
| Winner within 3 lengths of the leader at the half | 93% | 76% | most races |

Part 1 at the same time: half posts 46/47/7/0…, mile 46.5/33.5/11/7.6/1.5/0…; closers from the back win 0–2%.

## 2. Why: three places where the order should move and doesn't (hypotheses, each to be tested)

**H1. The start sorts by post.** Most drivers plan to tuck. Few leave, and those that do can't clear the horses inside
before the turn, so they take back. The rail horse inherits the lead ("found the lead") whatever its speed. In real
starts, horses with speed leave from anywhere, the rail horse often gets passed, and the field settles in **two
lines** (the rail line and an outer line, some horses parked), not single file.

**H2. Nothing advances in the middle.** One horse goes first-over, a follower or two ride its cover, and everyone else
sits. The outer line rarely forms, and a mover only gains on the leader slowly (`advance` 2 ft/s), so the order at
the 3/4 is the order at the 1/4.

**H3. The stretch only partly reorders.** Horses fan out late, one at a time, and the field is strung out about 2.5
lengths per horse, so only the first three or four can win.

## 3. The design

The driver keeps its structure: a plan before the gate, event-gated decisions, one snapshot per step. What changes is
**intent**. Each driver judges its horse against its neighbors (not the whole field) and acts on opportunity.

**A. The start: leave or tuck, judged locally.**
- **Who leaves:** a driver leaves when its horse is quicker than the horses inside it that it would have to clear,
  allowing for the lanes it must cross. The rail horse leaves only if it's quicker than the horses outside it.
- **Leaving is a brush:** at the horse's own speed (gate), paid from the reserve.
- **Crossing:** horses inside a leaver that is clearly coming over let it in (the pecking order, already built, keeps
  this one-way).
- **A leaver that can't clear** either presses (already built) or settles in the **outer line**. It doesn't drop to
  the back.
- **Gate:** passes when, at the half on the half-mile, the rail horse leads 15–35%, is top three 65–90%, and the outer
  two posts lead under 8%. On the mile: rail top three 25–50%, outer posts leading more often than on the half.

**B. The middle: an outer line that moves.**
- **The first-over horse moves earlier** (3/8–1/2 of the way) and with a real brush (its own speed, paid from
  reserve), so it reaches the leader by the 3/4.
- **Second- and third-over:** horses behind it in the outer line follow its cover. Horses on the rail with reserve
  and nowhere to go may join the outer line when cover passes.
- **The leader's answer** stays physical: it digs in, and the duel costs both.
- **Gate:** call-to-call order changes between the 1/2 and the 3/4 (Spearman clearly below 1, about 0.8–0.9 as a
  first band). First-over and followed-cover winners near the trip targets.

**C. The stretch: everyone with something left goes.**
- At the head of the stretch the outer line fans out and rail horses take the passing lane.
- Horses at the back with reserve swing wide, so a strong closer in a hot-paced race can win from the back.
- **Gate:** closers from the back win at least about 8% on the half and 12% on the mile, heading to the targets
  (13/20); median winning margin under 2 lengths.

**D. Then the joint refit.**
- A fitter that scores trips, churn and stat balance together, so a setting can't win on one and wreck another
  (refit A's failure, DECISIONS 190). Gate's worth target is 0.05 (189).
- Displayed times are mapped onto real ones (177).

## 4. How each stage is run

1. Build the stage behind driver settings. Defaults keep the old behavior until the stage passes.
2. Screen at quarter size on PyPy (`v3_churn.py`, Part 1, 80 races per track); confirm at full size.
3. **Every stage must keep** zero hard failures in 400 races, the merge suite at 9/9, and clocks within ±3 s.
4. **A test replay at each passed stage** for Patrick: next races as they come, separate fields per track.
5. **Stop rule:** two failed designs in a stage means stop, write up what was learned, and review before trying
   anything else.
6. Every decision and measurement goes into DECISIONS.md, with measured findings kept apart from hypotheses.

## 5. Kept, changed, removed

- **Kept:** race3 physics and safety; the true pace (189); the passing lane (183); pressing (180); pocket-leaving
  (179); the pecking order (193); the drive deadlock and lock fixes (173, 184).
- **Changed:** gate planning (A replaces the field-wide aim scoring for the start); the first-over trigger and brush
  (B); stretch line choice (C).
- **To remove if A works:** the "found the lead, kept it" default. A rail horse should lead because it's quick or
  unchallenged, not by default.

## 6. Open questions for review

1. Is "leave or tuck judged against the horses inside you" a sound basis for a two-line start? Or should the outer
   line be planned explicitly (a target slot per horse)?
2. Will an earlier, real first-over brush create order changes without wrecking the true pace's trip mix? Or is the
   missing piece the followers (second- and third-over)?
3. What's the cheapest test that tells H1 from H2 as the main cause of the post-ordered finish?

## 7. Review 18 (Astra) changes, adopted

1. **Diagnose before building.** A paired 2×2 on the same fields, posts and seeds (20–40 races per track):
   | | Middle as now | Earlier, stronger middle (`move_fo` earlier, bigger `advance`) |
   |---|---|---|
   | **Start as now** | baseline | middle only |
   | **Start challenged** (`gate_aims` sends a quick non-rail horse for the lead) | start only | both |

   **Validate that each treatment actually happened** (the forced leaver didn't take straight back; the early mover
   wasn't boxed). If a treatment doesn't execute, that's a controller obstruction to fix, not evidence.
2. **A second line needs several mechanisms changed together.** Today these all pull outside horses back to the rail:
   - non-leavers aim for the rail before the turn;
   - outside sitters `slot()` inward;
   - the lock rule tucks them behind;
   - the parked budget changes their aim.

   An outer line has to be a real intent that those respect, or they'll dismantle it.
3. **Audit:** `crossing` lets any outside lead-seeker cross regardless of the pecking order, so yielding isn't fully
   one-way yet.
4. **Measure mechanisms, not just outcomes:**
   - **Moves:** attempt → successful exit → ground gained → cover acquired → cover kept.
   - **Closers:** chances and conversion, conditional on pace, deficit and reserve.
   - **Churn bands are guides, not tuning targets:** they can be met by pointless shuffling.
5. **A move is a capped, budgeted attempt** with an abort-and-settle, not a promise to reach the leader by the 3/4.
6. **Watch joint outcomes at every stage** (trips, balance, churn, safety), not only at D.
7. **The 3/4 call already includes the drive:** everyone drives from about 0.735 of the mile. Read the 3/4 numbers
   with that in mind.
8. **Keep a real unchallenged leader.** Removing "found the lead" doesn't fix how the lead was inherited.
