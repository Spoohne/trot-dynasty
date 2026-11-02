# RaceGod verdicts

RaceGod reviews race results and replays for truth (the replay matches the result) and realism (the nights look like
racing, by `TARGETS.md`). Each verdict says what was measured, on what sample, and what RaceGod proposes. Nothing changes
until Patrick confirms. Every finding is labeled **measured** or **hypothesis**.

Tools: `audit.py <save copy> [--since DAY] [--json out]`. The ledger is each story row's `why` (gate order out, trip
role, depth, performance, form, broke, the model's margin, the final margin, and whether the speed limit set the time).
It's written by `outcome.race` and saved by `circuit.run_race`, and it's only on races run after it deploys.

Rules: read the live save freely (copy it down from `/opt/trotdynasty/game/save.pkl`); never write live or deploy
without Patrick's go-ahead.

---

## V1 - First audit, 2026-11-02 (live save copy, days 2626-2627: outcome engine, 159 races)

**Truth: measured.** All 159 stories (and all 400 kept since day 2623) match their results. Finish order, times, the
winner at the wire, lanes and fractions all pass. The ledger isn't live yet, so story margins could only be checked
against a smoke test. One gap showed there: the story caps a beaten-off horse at 40 L, and the result had it 51 L back.

**Realism: measured, small sample (2 nights).**

| | Live | Target | |
|---|---|---|---|
| Half-mile post 1 wins | 15.1% (n 93) | 19-27 | LOW |
| Half-mile post 8 wins | 7.2% (n 97) | 1-6 | HIGH |
| Mile post 1 wins | 6.9% (n 58) | 15-20 (soft) | LOW: post 1 wins less than post 8 (10.2%) |
| Winner within 3 L at the half | 42.8% | 60-90 (weak) | LOW |
| Half-mile winner 4+ L back at the half | 46.4% | 0-15 (weak) | HIGH |
| Favorite wins | 37.8% | 30-45 (hyp.) | ok |
| Median winning margin | 2.0 L | 1-3 (hyp.) | ok |
| Photos (a neck or less) | 15.1% | 5-15 (hyp.) | edge |

The old engine across days 2623-2627 (results in horse records, n about 4,000 per post) had half-mile post 1 at 17.0%:
also low, but less so.

Winning trips on the mile: first-over 15, mid-pack movers 13, sat in behind 13, lead 11, pocket/passing lane 5,
off the pace 5 (of 62). On the half: lead 25, pocket 21+6, mid-pack movers 20, first-over 16, behind 9 (of 97).
**Hypothesis:** the engine undervalues the trip from the front, and mile posts barely matter. The lab already saw mile
leaders win 16% against a 25% target (DECISIONS 238).

**Speed limit: measured by rerunning the 159 real fields 10 times each through today's `outcome.race` (horses as
they stand now, not as they were on race night).** The speed limit overrides the race model's time on 62% of starts and
39.5% of runners-up. Most beaten margins come from each horse's Speed-bar ceiling, not from how the race was run.
The replay then shows margins the trips don't explain.

### Proposed (awaiting Patrick)

1. **Deploy the ledger** (5 lines, no result changes) so every night's audit sees the engine's reasons.
2. **Retune post and front-end value** so the half-mile hits post 1 at 19-27% and post 8 at 1-6%, and the mile post 1
   beats post 8. Done in the engine lab on real fields, then checked here before going live.
3. **Rework the speed limit** so it applies to the winner's time (the clock) but not beaten margins, or only rarely
   (target: under 10% of starts limited).

Patrick: deployed the ledger (1) on 2026-11-02, commit 1186370.

## V2 - Clover Stakes (2629-stake-S6705), reviewed on request, 2026-11-02

**Measured: the replay shows a photo finish, but the clock has a 47-length win.** Northern Star went 1:41.4 and Fancy
Charger 1:50.8, 9.4 s behind. The replay finishes Fancy Charger a nose back, and the PHOTO graphic fires (watched on the
live page).

**Cause: measured in the code.** Stakes never moved to the outcome engine. `stakes.py` still runs `sim.race` (`from sim
import race`). `story.build` trusts each horse's `margin_l` whenever the engine is "outcome", and `sim.race` never sets it.
So every stakes replay since the switch finishes on margins left over from each horse's *previous* overnight race. The ledger
and tote odds are missing from stakes for the same reason. The odds are priced at view time instead, which is how this
board shows 1-9 and eleven horses at 99-1.

**Scope: measured.** 8 stakes since day 2626, and all 8 used borrowed margins. The new auditor law (replay finish against
the clock's margin) catches 4 of them; the other 4 happened to fall within a length and a half.

### Proposed (awaiting Patrick)

1. `stakes.py` runs the same engine as overnights: `(c.outcome.race if c.ENGINE == "outcome" else race)`. Stakes then get
   true margins, the ledger and odds at post time. On the outcome engine, Northern Star wins his fields by about 9½ L
   (DECISIONS 240), not 47.
2. `story.build` only trusts margins set by this race, so a stale `margin_l` can never steer a replay again.
3. Rebuild the 8 affected stakes replays from their recorded times. Results, purses and trophies stay as they are.
