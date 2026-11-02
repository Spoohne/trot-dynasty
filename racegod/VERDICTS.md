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

Patrick: fix all three. Deployed 2026-11-02, commit 746b033. The live save was backed up before the rebuild
(save.before-stakesrebuild-*). The 8 replays were rebuilt with `racegod/rebuild_stakes.py`. Live audit: 326 of 326
races true to their result. Watched on the site, Clover Stakes no longer shows a photo.

## V3 - The 40-length wall (found while checking V2), 2026-11-02

**Measured, on the live page and a copy of tonight's card.** `story.build` stops every beaten horse at 40 L, a nose
apart. When a winner is far clear, everyone behind piles into one blob. Clover Stakes had 2nd-12th beaten 47-73 L by
the clock; on the replay they finish within half a length of each other. The replay's board then calls the wrong
places: it shows Chief Frost 2nd, but Fancy Charger was 2nd. The camera frames the post with nobody in shot as the
winner finishes. On a copy, tonight's overnight card had 26 of 84 races with a horse beaten 40 L or more (69 of 732
starters). The speed limit set 64% of starters' times (V1, point 3).

**Hypothesis:** the root is the speed limit stretching beaten margins. The 40 L cap only hides the damage.
(Confirmed in V4.)
**Proposed:** fix V1 point 3 first, so margins come from the race and huge margins become rare. Then keep true margins
and let the replay show a tailed-off horse as tailed off (beyond 40 L, keep the order but space horses evenly).

## V4 - The speed limit: the clock and the race model disagree ten to one, 2026-11-02

**Measured (315 real fields from the live save since day 2626, each rerun 10 times with the same draws per variant;
`racegod/speed_lab.py`).** Two scales decide a beaten horse's margin, and they don't agree:
- the clock (`SPEED_FIT`): one Speed bar is worth 2.3 s, about **11.5 lengths**. Fitted across the whole population,
  claimers to stakes horses, so it's right about what class a horse belongs in;
- the race model (`s_margin`, `K`, `omega`): one Speed bar is worth about **1.2 lengths** between horses in the same race.
  Fitted on real charts, so it's right about how a field finishes.

The speed limit takes each horse's ceiling from the clock's slope and applies it inside the race. In a real field the
ceilings span 40 L (median; 51 L in the top quarter), while the race model has the last horse 18 L back. So the limit
overrules the model for 65% of starters, and 40% of races end with a horse 40 L or more behind.

Moving the limit around (the winner waiting for the beaten horses, no carrying of delays) helps a little and costs the
clock: Northern Star's median win slows from 1:46.4 to 1:53.3 and the field's times slow by 2 s.

**The fix that works: ceilings inside a field spread on the race model's scale.** The winner's ceiling stays its own
(its class sets the clock, Northern Star keeps his records); each beaten horse's ceiling sits that much behind the
winner's on the race model's slope (`WITHIN` = 0.1 of the clock's slope, the measured ratio 1.2 / 11.5).

| | limited starters | last horse 40 L+ | last horse (median) | win margin | photos | times | Northern Star median / fastest / margin |
|---|---|---|---|---|---|---|---|
| Today | 65% | 40% | 34.5 L | 3.1 L | 7% | 1:54.2 | 1:46.4 / 1:44.4 / 34.5 L |
| Winner waits for top 3, no carry | 21% | 15% | 23.3 L | 1.8 L | 11% | 1:56.0 | 1:53.3 / 1:48.2 / 11.3 L |
| **Within-field ceilings x0.1** | **10%** | **7%** | **18.1 L** | **1.8 L** | **10%** | **1:54.2** | **1:46.4 / 1:44.4 / 11.3 L** |

Nothing else moves: the clock, the order and who wins are the same; only beaten horses' times and margins change.
The hard limit still holds: no horse runs faster than its own ceiling, relative to the field it's in.

**Left open (measured, not fixed):** even with the limit out of the way, the race model itself has the last horse 18 L
back on median and 43% of races with a horse 20 L+ behind. That's the model's own margin scale (`s_margin`), which
V1 point 2's retune should look at together with post and front-end value.

### Proposed (awaiting Patrick)

Ship `WITHIN = 0.1` in `outcome.py` (the lab knobs `PACE_FROM` and `CARRY` come out). Then re-read the 40 L wall (V3)
on the next night's card; if tailed-off horses are now rare, the story can show them as tailed off.

Patrick: ship it (2026-11-02). Tonight's card on a save copy with WITHIN 0.1: 84 races, no law broken, 14% of starters
limited (was 64%), 4 races with a horse 40 L+ back (was 26), median last horse 16.8 L, median winning margin 1.6 L.

Deployed 2026-11-02, commit 7a1a7bf. Live: service active, login 200, WITHIN 0.1 on the server. Backup
save.before-within-20261102-190405.pkl.

## V5 - The engine's shape is the problem, 2026-11-02 (proposal; Patrick asked for it straight)

V1-V4 were patches on one structural fault: **the game never runs a race.** It decides a result (outcome.py), then a
second system (story.py) invents where everyone was from one line of text per horse, and a third set of formulas
(clock fit, model margins, speed limit) argues over the times. Every bug so far was two of these disagreeing: the photo
finish that was a 47 L win, the 40 L wall, 65% of times set by a ceiling instead of the race. The auditor's laws exist
only because the picture and the result are produced separately and can drift apart. Pace doesn't exist at all: every
race runs the same fixed quarters, so a speed duel and a soft lead look identical, and the replay shows moves ("moved
after the half") that nothing in the engine made.

**Proposal: one time-stepped race, and the result is whatever crosses the wire.** Each horse has a speed curve and an
energy budget from its bars; drivers make the trip choices the outcome model already has (leave, tuck, pull first-over,
wait) at the calls, with a cost for racing outside; the pace sets the fractions, and fast fractions tire the leader.
Positions at every call come out of the run, the replay plays them back, and times, margins, order, photos, trips and
fractions are consistent because there's only one of each. The outcome model's fitted knowledge (post effect, role
advantages, grit in the duel) becomes the driver and physics parameters, so nothing learned is thrown away.

**What it costs and what it doesn't.** It replaces `outcome.py` and most of `story.py`; it keeps the contract
(`race(field, track, passing)` returns the order with trip, times and the ledger), so `circuit.py`, `stakes.py`, the
pages and the replay viewer are untouched, and it goes in behind the existing TD_ENGINE switch. Calibration is the same
lab: the 315 real fields, TARGETS.md, Northern Star's records, the 1-3 L winning margins. **This reverses the engine
lab's direction (DECISIONS 226-234: outcome first, then a caster that choreographs it).** The caster reached 58% of
races; a simulation reaches 100% by construction.

**Measured basis:** V1 (post and front-end targets missed), V3 (40 L wall), V4 (three time scales). **Hypothesis:** a
single simulation will hit the targets with less tuning than the three-system design; proven only by building the
prototype and running the same audit on it.

### Proposed (awaiting Patrick)

Build the prototype in `racegod/engine/` (not imported by the game), run it on the 315 fields, publish the audit side
by side with today's engine, and show three replays. About two sessions' work before there's anything to judge.

Patrick: build the prototype (2026-11-02).

## V6 - The simulated race, first side by side, 2026-11-02 (session 1 of 2)

**Built (nothing in the game touched):** `racegod/engine.py`, one simulated race at a quarter-second step, feet along the
rail, lanes 7 ft apart, the two tracks' real turn geometry (an outside horse covers more ground on a turn). Same contract
as `outcome.race`, plus `story()` that reads the replay straight off the run. The outcome model's fitted knowledge goes
in as inputs: `omega`, `w_k`, `s_eps`, `s_margin` set each horse's steady speed; the start is the model's own (gate + luck
- `c_post` x post) and the drivers pick the same five trips by the same rule; the manners curve breaks them. Everything
the model had as a trip bonus the run has to earn: cover is cheaper than wind, the outside loses ground on turns, a hot
pace empties the leader's tank, a boxed horse can't go. Drivers yield only upward crossing over (DECISIONS 193).
Lab: `engine_lab.py` (today vs sim on the same fields, through the same audit), `engine_fit.py` (random search on the
run's knobs, 40 trials, one run each), `replay_server.py` (lab stories in the game's viewer).

**Measured: 315 real fields x 2 runs each, horses as they stand now.**

| | Today (outcome + story) | Sim | Band |
|---|---|---|---|
| Half post 1 wins | 20.6 ok | 21.5 ok | 19-27 |
| Half post 8 wins | 8.0 HIGH | 4.0 ok | 1-6 |
| Mile post 1 wins | 10.4 LOW | 10.4 LOW | 15-20 (soft) |
| Mile post 8 wins | 10.0 ok | 7.6 ok | 6-10 (soft) |
| Winner within 3 L at the half | 45.1 LOW | 83.0 ok | 60-90 |
| Half winner 4+ L back at the half | 42.3 HIGH | 9.0 ok | 0-15 |
| Favorite wins | 40.0 ok | **23.8 LOW** | 30-45 |
| Median winning margin | 1.8 ok | 2.7 ok | 1-3 |
| Photos | 11.4 ok | 7.0 ok | 5-15 |
| Speed limit set the time | 10.3 HIGH | 5.7 ok | 0-10 |
| Races with a horse 40 L+ back | 7.9% | 4.6% | |
| Winning time, mile-eq (median / fastest) | 1:54.1 / 1:44.7 | 1:55.2 / 1:44.5 | |
| Northern Star (4 fields): wins / median time / margin | 4 / 1:46.6 / 12.9 L | 4 / 1:47.3 / 9.2 L | |
| Winning trips: lead / pocket / first-over / mid-pack / behind | 29 / 16 / 13 / 21 / 22 | **50 / 33 / 1 / 13 / 3** | |
| Laws broken | 0 of 630 | 0 of 630 | |

**What the sim gets right, by construction or by physics.** Truth: the replay is the race, 630 of 630 (the 40 L viewer
wall is kept for now, V3). Post bias comes out of the crossing-over, not a fitted slope, and lands in band on three of
four (the mile's post 1 reads the same as today's engine, against a soft target). The pace is run: a brush to the
quarter, a breather, the drive; the leader at the quarter wins 50%, not 29% with the winner 4 L back at the half.
Tailed-off horses are rarer and the speed limit rarely speaks. Watched in the viewer (served by `replay_server.py`):
the field crosses over from the posts and strings out properly, the first-over horse pulls when the caption says,
the stretch fans two and three wide, the board's margins are the finish.

**What it gets wrong, and this is structural, not knobs (measured; 40 fit trials moved it from loss 28 to 18.5 and
changed none of it).** The lead and the pocket win 83% of races (today, and the chart targets behind it, 45%); a
first-over horse wins 1 in 100, a closer 3. The favorite wins 24%: the trip lottery outweighs ability.
**Hypothesis, from watching the runs:** three things are missing. (1) **The flow doesn't box the pocket.** The outside
line is one or two horses who fade, so the pocket horse always gets out in the drive with a full tank. Real: second- and
third-over sit outside the pocket into the stretch. (2) **Pressing costs the presser more than the leader.** A first-over
horse pays wind and the turn to get to the leader's flank and fades before it gets there; the leader's hot pace costs
it less. Real: the presser arrives with momentum; the leader pays for the fractions. (3) **Ability counts too little:**
the drive runs everyone at nearly the same push, so the order at the three-quarters mostly holds; the yield cascades
at the start cost more than a horse's class is worth.

### Proposed (awaiting Patrick)

Session 2: the three structural changes above, then a proper fit (the engine lab's differential evolution on the real
fields, not 40 random trials), then the same table again. Decision after that: adopt behind TD_ENGINE, or stop. The
replays to watch meanwhile: `2629-stake-S6705-sim` (Clover Stakes, Northern Star from mid-pack in 1:47.4),
`2626-gh-half-CLM1M-0-sim` (half-mile, won from mid-pack), `2626-ng-mile-NW2L6-2-sim` (mile, won from behind); each
also has a `-today` twin from the live engine on the same field.
