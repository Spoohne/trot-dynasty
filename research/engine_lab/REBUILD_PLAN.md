# Race core rebuild: plan for approval

Drafted 2026-11-03 from the Gallop Racer 2006 decode (`C:\Users\spooh\Downloads\horsegame06\race-engine-findings.md`).
Patrick: the current engine was never grounded; the game is pre-launch, so the race core and the horse display can be
replaced outright. We take ideas and structure from Gallop Racer, never its code or data.

## Why the current engine fights back

Today a race is **decided first, then drawn**. `outcome.race` scores every horse with a fitted statistical model
(bars × weights + trip worth + form + luck), sorts them, and the choreographer then animates a replay to match.

- The bars are inputs to a formula, not causes you can see. When a horse loses, nothing in the race shows why. The
  reason is a coefficient (`A_lead`, `k_close`, `s_form`...).
- Every coefficient trades against the others, so one fix moves four things (the trips cut to a tenth, the clock
  shifted and then shifted back, the bar's top moved).
- The replay has to be bent to fit a result it didn't produce (the choreographer pulling horses out a lane so they
  don't run through each other).

Gallop Racer runs the other way: **a small physical sim runs, and the result is whatever happens.** The stats are the
sim's knobs, so every outcome has a visible cause: he was blocked, she went too early, his ability fired.

## The new core: one sim, the replay is the race

Every tick (say 10 a second), for each horse:

1. **The driver decides effort** (how hard to go). The decision depends on the race phase (leave, settle, move, stretch)
   and the horse's position. The default rule is Gallop Racer's: hold a target gap to a target horse, push if behind,
   ease if ahead.
2. **Speed = cruise + push + kick − cost of moving sideways.**
   - *Push* burns **energy**.
   - *Kick* is available only late, and only if enough energy is left.
3. **Energy is the whole game.** Harness racing's trips fall out of it with no fitted trip worths:
   - **Parked out or first-over:** facing the wind costs extra energy per tick.
   - **Pocket or following cover:** drafting saves energy.
   - **Leaving hard for the lead:** burns energy early.

   A closer wins by saving energy and spending it late. A leaver wins by getting the lead cheaply.
4. **Lanes and blocking:** a horse can't move into an occupied lane. Boxed in means no kick until a gap opens. That's
   the pocket's real risk.
5. **Gait:** pressure (high effort, bumping, a hard parked trip) raises the chance to **break stride**. A break costs
   lengths and must go to the outside. This is harness racing's own drama, and Gallop Racer has nothing like it.
6. **Abilities:** each ability is a named, one-shot trigger with a condition and a fixed payoff (see below).

The replay is a recording of this sim, so the choreographer, `outcome.race` and the fitted trip model all retire. The
clock is the sim's own time (distance and speed), so time conversions and clock shifts disappear too.

## The horse

Six race stats. Each one has a single job you can watch happen in a race:

| Stat | Its one job in the sim |
|---|---|
| **Speed** | cruising speed (how fast it goes at normal effort) |
| **Gate** | how fast it leaves, and the energy that leaving costs |
| **Stamina** | the size of the energy tank |
| **Kick** | how much extra speed late energy buys in the stretch |
| **Grit** | effort bonus when another horse is alongside and fighting |
| **Manners** | resistance to breaking stride under pressure |

**Fit** is shown as symbols rather than numbers, and some of it is hidden until racing reveals it:
- half-mile vs. mile track
- sloppy track
- running style (leaver, sitter or closer: the driver's default plan)

**Career and condition:**
- **Growth curve:** early, normal or late bloomer; the existing precocity and longevity genes feed it.
- **Condition:** today's form, shown as a face. It's a small multiplier on the night, not a hidden coin flip.
- **Abilities:** 0 to 3 named traits, inherited through breeding (they can skip a generation). Starting set, about 12:
  - Gate Flyer: extra Gate from posts 6 and wider.
  - Pocket Rocket: a burst when a gap opens from the pocket.
  - Iron Horse: first-over costs half the energy.
  - Stretch Runner: kick +X if 4th or worse at the eighth pole.
  - Front Runner: an energy refund while leading by 1+ length.
  - Steady Gait: never breaks in the first half.
  - Mud Lover: plays up on a sloppy track.
  - Hates Traffic (negative): loses effort when boxed in.

The existing genetics in `sim.py` (loci, heritability, nicks, regression) map onto these six stats and stay as they
are. Only the trait names and how they're shown change.

## How we prove it works (the tests come first)

The goal "the bars predict results" becomes a script (`racegod/audit.py` grows into it). It runs thousands of races
after every change, and a change that breaks any line is reverted.

1. **Better horse wins:** across all pairs, the chance A beats B rises smoothly with the rating gap (about 50% even, 65%
   one step apart, 85% or more three steps apart). Bands for Patrick to confirm.
2. **No blowouts:** a horse one step better almost never loses by 5 lengths or more (Northern Star rule).
3. **Every stat earns:** raising any one stat by one step raises win rate and season earnings. No dead stats, and no
   stat is worth more than about twice another.
4. **Rating predicts earnings:** across a season, horse rating vs. earnings has correlation ≥ 0.7 (band to confirm).
5. **Racing looks real:** the existing `racegod/TARGETS.md` bands (post 1 and post 8 win rates, favorite win rate,
   margins, photos, where winners sit at the half).
6. **Abilities matter but don't dominate:** each one fires in a believable share of races, and none moves win rate more
   than one stat step.

## Build order (one piece at a time, tests re-run after each)

1. **Skeleton.** A new `race4.py` with ticks, energy, cruise and kick, and no lanes yet. Six identical horses must
   finish in a random order; then a stronger horse must win as test 1 says. The game doesn't import it.
2. **Lanes, blocking, drafting.** Trips start to emerge. Test 5 begins to mean something.
3. **Driver phases and styles.** Leavers, sitters and closers become real plans.
4. **Gait breaks.**
5. **Abilities**, a few at a time.
6. **Viewer.** The replay plays the recorded sim directly, and the choreographer is removed.
7. **Horse card redo:** six stats, fit symbols, condition face, abilities, and a past-performance line.
8. **Switch the game over:** `circuit.run_race` calls `race4`, and a fresh world is started. No save migration, since
   there are no real players yet.

Each step is a small commit with its test numbers in the message.

## Decisions for Patrick

1. **Numbers on screen?** The engine lab's ground rules say the Compendium shows no numbers or mechanics. Gallop Racer
   shows 0–99 numbers. Options:
   - keep bars, now tied 1:1 to the six stats
   - letter grades
   - numbers
2. **Hidden fit:** should distance and track preferences start hidden and be revealed by racing?
3. **The bands in tests 1–4:** confirm or change the starting numbers.
4. **Fresh world at the switch:** OK to start a new world rather than convert the old save?
5. **The `ratings-v2` branch** (worktree `HarnessSim-v2`): this plan supersedes its engine work. Archive it, or keep
   pieces (the honest-clock idea becomes automatic here)?
