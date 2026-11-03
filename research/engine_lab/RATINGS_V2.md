# Ratings v2: one ruler, read off the race

Branch `ratings-v2` (worktree `HarnessSim-v2`), 2026-11-03. A candidate to stand beside the live game; Patrick judges.
Astra reviews 21 and 22 (`research/engine_lab/reviews/`).

## The rule

One truth, one engine, and everything a player sees is a reading of it. Genes set the ceiling; the bars are what the
horse can do today; the engine (`outcome.py`) races the bars and keeps a ledger of what decided it (`h.why`: role, depth,
form, break, and now the kick and cruise it raced with); the choreographer draws that decision; the badge is read off
the race, nothing else.

## What the clock can't do (why the figure isn't the clock)

Inside a field a bar is worth about a fifth of a second (`WITHIN`); between fields the clock moves about two seconds a bar.
A beaten horse's time is the winner's class plus its margin, so the clock rates winners and nobody else. Review 21 made
that call. Saga Spell shows it on the candidate: beaten in 2:03.0 with a figure of 1:54.6.

## What stays

`outcome.race` and its ledger, the choreographer, the tote (prices off `outcome.rating`), classes and claimers (placed
by `h.est`, the handicapper's class rating), breeding, training. Bars on the fixed pip scale: 140 of 200,855 horse-seasons
(3+) sit on a capped Speed bar, 324 on Stamina, so hidden headroom isn't worth a change.

## What changes

1. **A figure for every start** (`outcome.figure`, stored as `results[i]["fig"]`): the ledger's performance with the
   trip taken out (the role's worth, the line's depth, a closer's extra kick), mapped to mile seconds by `FIG_FIT`, a
   per-track line from the model's class units (`omega * cruise + (1 - omega) * kick`, K per bar) to `best_mile`, fitted
   on the live save (777 horses: r -0.96 mile, -0.92 half). A breaker's start has no figure. Starts from before the
   switch have none either; the badge reads the bars until three figures exist.
2. **The badge, one ruler, mile seconds cut at `MILE_TIERS`** (`app.tier_label`):
   - proven (5+ starts): the median of the last ten figures (`badge_secs`), once three exist;
   - retired: the median of its ten best kept figures (its prime);
   - unproven: `pred_mile` of its bars (the same line, so the prediction and the figures are one ruler by construction;
     weanlings and yearlings already read against their crop) placed among the unproven horses its age and cut at the
     proven horses' tier shares; labelled UNPROVEN, hollow;
   - hysteresis `BADGE_HYST` 0.3 s: a line is crossed by that much before the badge moves.
   `h.est` makes no badge anywhere.
3. **Form is visible after the fact:** "sharp tonight" / "flat tonight" in the trip text past 1.3 sd of the night's form.
4. **Tells in the captions, from the ledger:** "X breaks stride" at the quarter; ", sharp tonight" on a sharp winner's
   finish caption. Positions stay the choreographer's.
5. **Pages:** each start shows its figure under the clock (horse page and results page); the header shows the figure the
   badge rests on and how many starts it comes from when fewer than six; the help says a letter is earned from figures,
   read fairly for the trip.

## Measured

**Seven nights on a copy of the live save** (3,876 figured starts): figure - pred_mile median -0.11 s, sd 1.44 s on the
mile (0.05 / 1.82 on the half). The spread is the night's form (0.15 units at 6.4 s a unit, about 1 s) plus freshness,
tonic and driver, not the field. Active horses 3+: S+ 25 of 647 (3.9%) against live's 69 (10.7%) on the same save.

**100-season fresh world** (`sim100.py` on the branch, `world100.db` in the worktree; `compare_badges.py`): 80,616 racing
horse-seasons 2+. Truth = `pred_mile` of the horse's bars that season, cut at the tiers.

| season | truth S+ / S | v2 | live |
|---|---|---|---|
| 5 | 2.3 / 4.9 | 2.9 / 2.3 | 1.8 / 2.7 |
| 20 | 3.4 / 9.8 | 2.4 / 8.1 | 4.3 / 9.7 |
| 60 | 6.4 / 14.2 | 6.4 / 13.0 | 9.4 / 13.8 |
| 99 | 9.5 / 16.0 | 9.0 / 14.4 | 14.8 / 18.2 |

The truth itself drifts (this world runs `sim.MUTATE` 0.10; the launch rule is 0.05): v2 tracks it, live overstates S+.

| | same tier as truth | within one | mean secs off |
|---|---|---|---|
| v2, median of last six | 72.0% | 99.4% | 0.68 s |
| v2, second-best of ten | 48.0% | 96.5% | 1.25 s |
| live est badge | 52.4% | 96.1% | |

Flips while the truth tier held (37,317 season pairs): v2 41.1%, live 51.9%; with 0.3 s hysteresis v2 33.5% (same-tier
71.3%). Decline lag (7,275 declines): both catch it the same season about 60% of the time, 4-5% take three seasons or more.
The jump at the fifth start isn't measurable from season rows (n 1).

**Caveat (Astra, review 22):** the "truth" here is the engine's predicted clean-mile score, which v2 is fitted to, so the
comparison favors v2 by construction; it shows v2 reads the engine faithfully, not that it tells a career better. Gate,
grit, manners and the trip decide races beyond that score. Decline tracking shows no advantage (60% vs 59%). The
residual spread's attribution to form and freshness is a hypothesis. An independent test needs per-start snapshots of
both badges judged against future performance with class controlled, and the handoff at the fifth start logged; not
built. That, and Patrick's own comparison of the candidate on 8113 beside trotdynasty.com, is what's left.

## The window, and the independent test (second 100-season run, every start logged: `badge_windows.py`)

213,824 season ends. Each badge replayed start by start from the logged figures (v2) or the est after the start (live),
scored at each horse's last start of the season: "now" = same tier as the bars' predicted mile that night; flips while
that predicted tier held; and the independent one, rank correlation with **next season's purses per start**, by age.

| badge | now | flips | next-season purses, age 3 / 4 / 5 / 6 |
|---|---|---|---|
| v2 last 4 | 68.2% | 44.7% | .691 / .687 / .594 / .600 |
| v2 last 6 | 72.9% | 39.8% | .706 / .698 / .608 / .612 |
| v2 last 10 | 77.5% | 34.5% | .719 / .706 / .624 / .620 |
| v2 last 15 | 79.9% | 31.2% | .726 / .713 / .628 / .628 |
| live est | 45.4% | 50.9% | .676 / **.741** / **.658** / **.649** |

Decided: the last ten (longer is steadier on every count, but a decline must show within a few starts). **Live's badge
predicts next season's purses better from age 4 on** (hypothesis for why: est folds in who the horse beat, so gate, grit
and manners reach it, and the classes a horse is placed in are set by est, which feeds the same purses); v2 reads the
horse's speed and stamina, the ruler the tiers were cut on. That is the real choice for Patrick: a badge that says how
fast the horse is (v2, honest about decline, no drift) or one that says how it fares (live, a rating in a time's clothes).

## Not in this round

Tells drawn in the positions themselves (the duel's head-bob, a fractious start) belong to the choreographer, which the
RaceGod thread is editing. A forward-looking test (future purses by badge) needs per-start records the encyclopedia
doesn't keep. Bars on a breed-wide fixed scale for the legends race: the pip scale already is one.
