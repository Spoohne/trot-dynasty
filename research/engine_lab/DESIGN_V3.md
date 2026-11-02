# Race engine v3: design (race3.py)

This builds `ENGINE_SPEC.md`. The Part 0 behavior rules hold by construction; the Part 1 results are checked, never
forced. Nothing in race3 knows a horse's post or a target percentage.

## 1. State (per horse, every step; DT = 1/8 s)

- `s`: feet along the rail line from the start. The finish is at 5,280.
- `y`: feet out from the rail. This is continuous; lanes are about 7 ft apart, used only for reading and reporting.
- `v`: forward speed. `vy` is lateral speed.
- `E`: reserve, an aerobic tank of 100. Speeds above a horse's cruising pace draw on it; below that pace it recovers
  slowly.
- `broke`: seconds left off stride.
- Driver: `aim`, `aim_t`, attempt budget, `done_aims`, `target_y`, and `commit` (a lane change in progress).

## 2. Track

Each track is a list of straights and arcs with true radii:
- **Half-mile:** 800 ft straights, 520 ft arcs (radius about 166 ft), 300 ft run-in.
- **Mile:** 1,320 ft straights and 1,320 ft arcs, with about 1,000 ft from the last turn to the wire.

On an arc a horse at offset y covers `(R + y) / R` feet per foot of rail. Ground lost wide is therefore exact and
continuous (π·y per 180° turn), with no lane bookkeeping.
The stretch fans out to about 5 lanes; turns allow 3 lanes of width before the cost is prohibitive. That isn't a
wall: rule 0.4 is enforced by cost and by the driver.

## 3. The horse: five hidden traits (spec 11A)

0 is breed average; the spread is like today's traits.

| Trait | From today's | Its one job in the engine |
|---|---|---|
| Gate | early speed | acceleration, and a short burst ceiling for the first eighth |
| Cruise | stamina | the pace held without drawing on the reserve, and how slowly the reserve drains above it |
| Kick | late speed | top speed in the drive |
| Manners | gait | break hazard, and how cleanly it holds a line in traffic |
| Grit | new | alongside a rival (a duel), its cost multiplier drops and its ceiling rises slightly |

Every trait appears only in terms that help: a higher trait means faster, cheaper or safer, never a worse choice.
The driver may change plans as a trait changes, and the acceptance test (rule 0.13) checks that the net effect is
never harmful on average.

## 4. Physics per step

- **Ceiling.** `v_cap = V_top(kick) · f(E)`, where `f` falls smoothly from 1 toward about 0.86 as `E` runs low
  (rule 0.10: horses fade, they don't stop). In the first eighth: `v_cap += gate_burst · gate`.
- **Acceleration.** At most `A0 + a_g · gate` ft/s²; braking at most 8 ft/s².
- **Reserve.** `dE/dt = -k · max(0, v - V_cruise(cruise))^p · D(cover) · G(duel) + recover · [v < V_cruise]`, where:
  - `D` is the share of air cost: 1 in the open, about 0.6 tucked behind a horse within about 1.5 lengths;
  - `G` is 1, or less for a high-grit horse in a duel.

  Racing wide without cover costs more automatically (rule 0.11).
- **Bodies.** Each horse plus its sulky is a rectangle: about 2.2 lengths long (horse plus bike) and 5 ft wide.
  - **Longitudinal:** if another body overlaps laterally and is ahead within the gap, the horse's speed is limited to
    that body's speed plus a closing term, so a horse can't pass through another (rule 0.1).
  - **Lateral:** `y` moves toward `target_y` at up to about 2.5 ft/s, and only if the swept rectangle from `y` to the
    next position is clear of every other body over that step. Otherwise the horse holds its line. Changes take
    several strides (rule 0.2).
  - **Commit:** once a change starts it finishes, or reverses only if a body enters the gap (rule 0.3).
- **Breaks.** The hazard is `b0 · exp(pressure − m · manners)`, where pressure counts effort near the ceiling,
  traffic within half a length, and being boxed. A break drops the horse to about 75% speed for 3–4 s and drifts it
  slightly out (rule 0.22). It draws from the horse's own random stream.

## 5. The driver (spec 17A, approved decisions 1–10 from 2026-10-31)

- **Aims:** top, pocket, first-over, follow, close. Each aim turns into targets: a sitting distance to the leader, a
  `target_y` (the rail unless moving or following), a move point, and a spend budget.
- **At the gate:** a rule score for each aim from what a driver reads: the gate rank in the field, the shortfall from
  the quickest, post, cruise, kick, how crowded the aim already is, and the track. Its weights are tuned to the
  Part 1 targets. Best-response passes, quickest first. Optional homework rollouts (spec 22A allows about an hour
  per night) only if the rule score can't reach the targets.
- **During the race:** looks every sixteenth and on events (a hole, cover going by, a rival alongside, over budget,
  the leader tiring), all decided from the field as it stood at the start of the step, then committed.
  - A switch needs a margin and then holds.
  - An exhausted aim is closed for the race (rule 0.15).
  - First-over moves come from the half on; follow goes when its cover goes; close makes its move in the last
    quarter (rule 0.16).
  - A pocket horse leaves only through a gap that fits (rules 0.18, 0.20).
- **Reading:** at the gate, the outside horses that aren't leaving ease back to tuck in (rule 0.6). A horse that
  can't clear by the turn takes back (rule 0.8).

## 6. Tuning (Part 1 targets)

The free settings are:
- in the driver: aim scoring weights, move points, sitting distances, budgets, hysteresis;
- in the physics: k, p, D, the curve of f, b0, gate_burst, and the time scale.

They are fitted against the Part 1 checks on both tracks, with each target's tolerance written down before the fit.
Trait coefficients are fitted only to keep rule 0.13 and items 6–7 (how much better horses win, form). The tier
clocks set the time scale (item 9).

## 7. Record and replay (item 21)

Every step, each horse's `s, y, v` plus events (aim changes with reasons, breaks, moves) go into the record, quantized
to keep it small. The replay draws exactly the record.

## 8. Acceptance suite

Ported from race2:
- trait upgrades, +0.5 per trait, adaptive against fixed, clustered by field;
- post rotation;
- order invariance;
- a determinism and replay audit (rule 0.24);
- the expected-regret bench, for the driver.

New checks:
- a Part 0 auditor that scans every recorded race for overlaps, sideways snaps, weaving (more than 2 reversals in
  10 s), four-wide on a turn without cause, leaders stopping dead, and changes per horse;
- the Part 1 results report against its tolerances.

## 9. Breeding hookup

- Gate, cruise, kick and manners inherit as today's matching traits do. Grit is a new heritable trait with the same
  model.
- The displayed bars map back: Early speed from gate, Late speed from kick, Stamina from cruise, Gait from manners.
  Grit shows only as a trainer note.
- The long-run inflation tests are rerun on the new traits before launch (item 15).

## 10. Order of build

1. Track geometry, bodies, lateral motion, reserve physics, and a scripted test where a horse holds a pace on the
   rail, outside, and behind cover.
2. A Part 0 auditor, running on scripted chaos tests: an eight-wide start, a box, a stretch fan.
3. The driver, with aims and checks.
4. The acceptance suite on random fields.
5. Tuning to Part 1.
6. A replay adapter, and Patrick's look.
7. The breeding hookup and the long-run tests.
8. The developer pilot.

## 11. Changes from review 13 (all accepted; these override sections 1–10 where they differ)

1. **Measurement contracts, frozen before any tuning.**
   - **Half-mile post curve:** Patrick's curve is wins per start across fields of varying size; it sums to 88.9%,
     not 100%. The engine is scored the same way: fields are drawn with the live save's field-size mix, and wins per
     start are reported by post. It is not normalized to 8 starters.
   - **Defined in `CONTRACTS.md` before the fit:** favorite, bottom third, true ability, item 7's rerun protocol,
     photo, horse length, quarter timing and every tolerance.
   - **Trips are classified from the realized trajectory, not the intended aim.** The old provisional bands in
     chart_targets are reference only.
2. **Safety layer by construction** (rules 0.1–0.3, 0.18, 0.21).
   - Following always keeps a distance it can safely brake from, even if the horse ahead breaks stride.
   - All proposed forward and sideways moves in a step are resolved together, with swept-body checks over the step.
   - A lane change reserves its corridor ahead and is rechecked as it goes. If blocked, the horse pauses the
     sideways move and slows; it does not reverse.
   - Ties are broken by a fixed rule, never by list order or post number. Replay and the auditor use the same
     geometry.
3. **A maneuver admissibility layer**, separate from tactics, so rules hold even if expense doesn't stop a horse
   (rules 0.4, 0.6, 0.8, 0.21).
   - Before turn entry each horse predicts whether it can clear or tuck in, and starts yielding while it still can.
   - Four-wide on a turn needs a recorded, checkable reason.
   - Stretch corridors allow fanning into clear space and forbid cutting across a rival's corridor.
   - First integrated test: eight abreast at the gate on the half-mile.
4. **Physics as a power balance.**
   - Demand counts speed, acceleration, exposure and the path round turns. Cruise sets the workload a horse can
     sustain; demand above it spends the reserve, and recovery below it is gradual.
   - Cover cuts only the air part.
   - Grit discounts only the extra cost of a duel, so a duel is never cheaper than racing alone.
   - Racing outside in the open costs more than the rail even below cruise.
   - Each trait keeps one job: Gate for launch and a smoothly fading early burst, Kick for the drive, Grit for duels
     only. A higher trait is something the horse can use, never something it must use.
   - Every change in capability is smooth, with bounded acceleration and braking.
5. **Units.** `v` is physical forward speed, and `ds/dt = v / (1 + κy)` on arcs.
   - Horse length (for results), horse-plus-sulky footprint and safe headway are separate measured values in feet,
     not tuning knobs.
   - Lateral motion limits acceleration as well as speed.
6. **Breaks.** The chance of a break in one step is `1 − e^(−λΔt)`, measured from body edges. Each break records
   which factor caused it. A break is a constrained recovery path, so safety still applies. Freshness and training
   feed in (spec 14A).
7. **The driver is an event-gated state machine.** It holds four things:
   - short-horizon feasibility: clear, yield, tuck, follow, pass;
   - a value for its own horse: expected position, reserve, risk of being trapped, chances still to come;
   - maneuver memory: commitment, plus a cooldown for each opportunity, so a failed aim closes until something
     changes rather than for the whole race;
   - continuous controllers for pace, following gap and line.

   Other rules:
   - The leader has a breather target when unpressed and answers a challenge, with hysteresis.
   - When a horse has nothing to gain outside, it tucks in.
   - Best-response passes are tested in different orders.
   - Each driver serves only its own horse; no aim quotas.
   - Rollouts are an offline regret diagnostic first.
8. **Fit staging, each block frozen before the next:**
   1. contracts, field generators, trait distributions, condition inputs;
   2. geometry, units, bodies, safety (no fitting);
   3. single-horse capability, workload, fatigue and tier clocks in physical units (no later global time rescale);
   4. tactical competence and Part 0 behavior, with breaks off;
   5. trip, post and pace patterns, with the physics held;
   6. breaks, then items 4–7 and rule 0.13 together.

   Item 7 note: a repeat-winner rate of 45% and a best-horse win rate of 30% must be jointly feasible, since the
   repeat rate equals the sum of p_i². This is checked before fitting. No noise is added just to pass it.
9. **Build order change:** the replay adapter and the exact-trajectory audit move into steps 1–2. Measure first:
   - safety margins;
   - gate sorting: width at turn entry, time to clear or tuck, time parked;
   - single-horse mechanics: rail, outside and cover at matched pace;
   - the canonical tactical cases;
   - trait counterfactuals, logging the first point where decisions differ.

   Aggregate win rates come only after all of those.
