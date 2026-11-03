# Ratings v2: one ruler, read off the race

Branch `ratings-v2` (worktree `HarnessSim-v2`), 2026-11-03. A candidate to stand beside the live game; Patrick judges.

## The rule

One truth, one engine, and everything a player sees is a reading of it. Genes set the ceiling; the bars are what the
horse can do today; the engine (`outcome.py`) races the bars and keeps a ledger of what decided it (`h.why`: role, depth,
form, break); the choreographer draws that decision; the badge is read off the clock, nothing else.

## What stays

- `outcome.race` and its ledger, the choreographer, the tote (prices off `outcome.rating`), classes and claimers (they
  still place horses by `h.est`, the handicapper's class rating), breeding, training.
- Bars on the fixed pip scale (`outcome.bar`). Measured: 140 of 200,855 horse-seasons (3+) sit on a capped Speed bar,
  324 on Stamina, so hidden headroom isn't worth a change.

## What changes

1. **A figure for every start.** `outcome.figure(h, track)` after each race: the horse's raw time, less the half-mile
   allowance, less what its trip was worth in the model (`A[role] - b_depth * depth`, in seconds at `s_margin` lengths a
   unit and a fifth of a second a length), shifted by one measured constant `FIG_REF` so that a horse's figures sit on
   its own `best_mile` (the clock its bars predict). A start with a break has no figure (the time means nothing).
   Stored as `results[i]["fig"]`, display seconds. Older starts without a ledger get the clock less the half allowance.
2. **The badge: one ruler, mile seconds, cut at `MILE_TIERS`.**
   - Proven (5+ starts): the median of the best three figures of the last ten starts. A horse in decline drops a tier
     as its figures slow; nothing is remembered for it.
   - Retired: the median of its best three figures ever (its prime).
   - Unproven (under 5 starts): its predicted figure, `best_mile` of its bars (weanlings and yearlings already read
     against their crop through `young_bar`), placed among the unproven horses its age and cut at the proven horses'
     tier shares, as live does today with `bars_grade`; the score is the engine's own prediction instead of `CARD_W`.
   `h.est` no longer makes a badge anywhere.
3. **Form is visible after the fact.** The ledger's `form` draw (`s_form` is one sd) goes into the trip text when it
   was big: "sharp tonight" over +1.3 sd, "flat tonight" under -1.3 sd. An upset reads as what it was.
4. **Tells in the replay captions, from the ledger:** "X breaks stride" at the quarter for a breaker, "sharp tonight"
   on the winner's caption when it was. Positions are the choreographer's; the captions only name what it drew.
5. **The horse page:** each start shows its figure beside the clock; the header shows the figure the badge rests on;
   the hollow badge is labelled UNPROVEN, not PEDIGREE.

## Checks

- `research/encyclopedia/sim100.py` 100 seasons on this branch: the tier shares season by season (live drifted from
  4% S+ in season 5 to 25% in season 99 for active horses 3+), and whether the badge follows the career: purses by
  badge at 3 and 4, and how many seasons a badge lags a decline.
- `FIG_REF` measured on that world: median of (figure - best_mile) over horses 3+ with 5+ starts, by track.
- The candidate served on 8113 from a copy of the live save (`TD_STORY=choreo`), beside trotdynasty.com.

## Not in this round

Tells drawn in the positions themselves (the duel's head-bob, a fractious start) belong to the choreographer, which the
RaceGod thread is editing. Bars on a fixed breed-wide scale for the legends race: the pip scale already is one.
