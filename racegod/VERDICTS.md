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

Patrick: yes, session 2 (2026-11-02).

## V7 - The simulated race, session 2: structure, then a real fit, 2026-11-02

**Changed in `racegod/engine.py`:** the first-over horse brushes up to the leader's flank (`push_fo`) and then sits on
it; only the leader pays the duel (the presser arrived with momentum); the drive scales with ability under the field's
best (`drive_able`); a horse stops yielding at the start once it has given up `yield_max` feet (the line is formed).
Then `engine_fit.py --de`: differential evolution, 10 knobs-sets x 14 generations, one run of the 315 fields each,
loss = target bands (the favorite weighted x3) + today's winning-trip shares + laws + stragglers. Loss 28 -> 5.1.
The fit put `yield_max` on its floor (nobody yields, outside horses stay 4-wide to the quarter, 46 pictures broken);
the floor is now 20 ft, which costs some of the trip balance back. Both readings below.

**Measured: 315 real fields x 2 runs each.**

| | Today | Sim, fit as found (yield 5 ft) | Sim, yield 20 ft (kept) | Band |
|---|---|---|---|---|
| Half post 1 / post 8 wins | 20.6 / 8.0 HIGH | 29.4 HIGH / 5.2 | 21.2 / 6.1 (edge) | 19-27 / 1-6 |
| Mile post 1 / post 8 wins | 10.4 LOW / 10.0 | 20.0 / 7.2 | 12.0 LOW / 10.8 (edge) | 15-20 / 6-10 (soft) |
| Winner within 3 L at the half | 45.1 LOW | 81.3 | 82.4 | 60-90 |
| Half winner 4+ L back | 42.3 HIGH | 4.6 | 5.2 | 0-15 |
| Favorite wins | 40.0 | 26.7 LOW | 27.0 LOW | 30-45 |
| Median margin / photos | 1.8 / 11.4 | 1.7 / 12.4 | 1.8 / 10.0 | 1-3 / 5-15 |
| Speed limit set the time | 10.3 HIGH | 0.9 | 0.8 | 0-10 |
| Races with a horse 20 L+ / 40 L+ back | 44.9% / 7.9% | 17.9% / 0% | 24.3% / 0.5% | |
| Winning trips: lead / pocket / fo / mid / behind | 29/16/13/21/22 | 37/29/4/17/12 | 51/29/2/12/6 | |
| Northern Star: wins / time / margin | 4 / 1:46.6 / 12.9 L | 3 / 1:47.6 / 13.0 L | 4 / 1:48.0 / 10.9 L | |
| Laws broken | 0 | 46 of 630 (4-wide at the quarter) | 1 of 630 | |

**Where it stands (measured).** Nine of ten targets in band or on the edge, against six for the live engine, and every
replay true to its result. The pace, the post bias, where the winner sits at the half, stragglers and the speed limit
are all better than today's. Two things are still wrong: **the favorite wins 27% (today 40%)** and **the front end
wins too much** (lead + pocket 80%; first-over 2%, closers 6%). Both come from the same place: a trip in the sim
costs more than a horse's class is worth, and the fit can only trade one against the other (yielding at the start
buys the trip balance back but strands horses wide; the picture or the balance).

**Hypothesis for what would fix it (not tried):** the model's `s_margin` scale is applied to steady speed (a class
difference of one unit = 6 L over the mile), but the sim's trip costs are in seconds of tank, which the fit sized to
make the trips matter at all. The two scales need fitting together, as one: class as a share of the tank as well as
of the speed. That is a design change to the energy model, half a session, and the fit again.

### Proposed (awaiting Patrick)

Three ways to go. (a) **Adopt now behind TD_ENGINE** for a shadow week on a save copy (the nightly audit decides):
better on nine measures, worse on the favorite and the trip mix; players would see more front-end winners and
longer prices winning. (b) **One more session** on the class-vs-tank model, then decide. (c) **Stop**: keep today's
engine, carry the sim's lessons back as V1's retune (post slope, front-end value). RaceGod's pick: (b); it is the one
thing the sim can't be tuned around.

Replays: http://127.0.0.1:8115/ while this session runs (`-sim` and `-today` twins per field).

Patrick: one more session (2026-11-02).

## V8 - Session 3: class as tank, and why the favorite still loses, 2026-11-02

**Tried:** (1) class sizes the tank as well as the speed (`reserve_able`); (2) a horse that sat covered gets the
model's extra kick in the drive (`drive_close`, the model's `k_close`). Both as knobs, refit by differential
evolution (14 generations). **The fit set both to zero.** Loss 8.1 against V7's 5.1 (a different run, same noise);
the favorite 26.7% either way. Both knobs are left in at 0; V7's knobs stand.

**The measurement that explains it (315 fields, one run each).** Strip the trip terms out of each engine's
performance and ask how often the field's best horse, by ability alone, wins:

| | Today | Sim |
|---|---|---|
| Best-ability horse wins | **61%** | **29%** |
| Tote favorite wins (odds fitted to today's engine) | 35% | 26% |
| Ability gap, best to second (median) | 1.8 L | 1.1 L |

Real fields on this circuit are tightly tiered: the best horse is a length or two better than the next. In the
outcome model the trip terms are fixed bonuses with almost no noise, so a length of class decides most races. In the
sim a trip is a run through traffic, yielding, wind and tank, and its cost varies by several lengths race to race;
class of a length can't be seen through it. No knob changes that: cheaper trips drift the post and pace targets, and
tank or kick for class were rejected by the fit. **Measured.** The hypothesis that one simulation needs less tuning
than three systems (V5) is **not supported** for the one target players feel most: who wins.

Also noted: "favorite wins" measures the tote as much as the engine. The odds are fitted to today's engine's winners;
a sim engine would need its own tote fit, and even then the best horse at 29% says the race is too much of a lottery.

### RaceGod's verdict

**Stop the sim as the race engine.** Keep today's outcome engine deciding results. Carry back what the sim proved:
- the replay should be the race, not a parse of trip text: the sim's `story()` can choreograph today's *decided*
  result (the engine lab's caster, DECISIONS 229, reached 58% of races; a sim that is handed the finish order and
  margins as constraints is the way to reach 100%), which removes the auditor's whole class of truth bugs;
- the pace: the sim's fractions (a brush, a breather, the drive) in place of the fixed quarters;
- post bias on the half-mile came out right from the crossing-over physics; V1's retune of `c_post` can use the
  sim's numbers as the target curve.

Next for RaceGod, if Patrick agrees: V1 point 2 (post and front-end retune in the engine lab on real fields), then
the choreographer. The prototype stays in `racegod/engine.py` for that.

Patrick: retune next (2026-11-02).

## V9 - Post and front-end retune (V1 point 2), 2026-11-02 (proposal; nothing shipped)

**Method:** `racegod/retune.py`: differential evolution over the outcome model's post cost and trip values per
track (`c_post`, `A_lead`, `A_pocket`, `A_fol`), one run of the 315 real fields per evaluation, loss = the post and
favorite bands, the margin band, and the leaders' share of wins (half 30-45%, mile 22-35%, DECISIONS 207/238).
The fit (loss 0.24 -> 0.04) pushed `c_post` to its ceiling on both tracks, so the proposal below is the fit with the
half's post cost brought back by hand; every row is 3 runs of the 315 fields.

| | Today | Proposed | Band |
|---|---|---|---|
| Half post 1 / post 8 wins | 20.9 / 7.4 HIGH | 23.7 / 3.7 | 19-27 / 1-6 |
| Mile post 1 / post 8 wins | 10.1 LOW / 10.1 | 15.2 / 7.2 | 15-20 / 6-10 (soft) |
| Favorite wins | 41.1 | 38.1 | 30-45 |
| Median margin / photos | 1.7 / 11.2 | 2.0 / 8.1 | 1-3 / 5-15 |
| Leaders' share of wins, half / mile | 36% / 20% | 44% / 34% | 30-45 / 22-35 |
| Winning trips lead / pocket / first-over / mid-pack / behind | 29/17/13/21/20 | 40/12/4/34/11 | |
| Northern Star, 12 starts | 6 wins, 12.9 L | 6 wins, 11.3 L | |

**Proposed values** (`outcome.P`): half `c_post` 0.099 -> 0.15, `A_lead` 0.41 -> 0.78, `A_pocket` 0.31 -> 0.57,
`A_fol` 0.10 -> 0.60; mile `c_post` 0.049 -> 0.25, `A_lead` 0.89 -> 1.24, `A_pocket` 0.77 -> 0.67, `A_fol` 0.26 -> 0.66.

**What it buys (measured):** every post target in band, post 1 beats post 8 on the mile, leaders win at the chart
rate on both tracks, favorite and margins stay in band.
**What it costs (measured):** first-over winners fall from 13% to 4% and mid-pack ("followed") winners rise to 34%
(the chart targets had first-over at 21% on the mile); photos drop a little.
**Not checked:** DECISIONS 215's per-horse rule (more Speed never lowers a horse's win chance at any post) has not
been rerun on these values; it must be before they ship. "Winner within 3 L at the half" and "half winner from the
back" stay out of band under either setting: those are the story system placing winners by trip text, which V8's
choreographer would fix, not this retune.
**Noted in passing:** Northern Star, raced as he stands today, wins 6 of 12 lab starts under either setting
(V4 had him 499 of 500 on day 2626 fields). Worth a look at his card: has he come off the boil, or did a stat move?

### Proposed (awaiting Patrick)

Run the per-horse check on the proposed values; if it passes, ship them in `outcome.py` (a deploy, no save change)
and read the first real night with the audit. Or hold the trip-value changes and ship the post costs alone.

**Per-horse check run (Patrick: "yes, run the check", 2026-11-02).** `racegod/per_horse.py`: 100 real fields, one horse
each, 60 reruns with common random numbers, each bar one pip up through the drivers' own door (`drive_on`).

| +1 bar | Today's values | V9 as proposed | Candidate B (mid-pack value 0.35 / 0.40) |
|---|---|---|---|
| Speed: average gain / cases down 2+ pts | +7.3 / 0 of 100 | +6.8 / 0 | +6.4 / 0 |
| Stamina | +7.6 / 0 | +6.7 / 0 | +6.5 / 0 |
| Gate (early speed) | +4.5 / 2 (worst -3) | +3.2 / **8 (worst -33)** | +5.2 / 3 (worst -20) |

Speed and Stamina pass everywhere. **The proposal as written fails on gate:** with mid-pack worth 0.6, a bar more of
early speed puts a horse out first into a trip that loses (Captain Pine, post 4 on the half: 55% -> 22%). Candidate B
(mid-pack 0.35 on the half, 0.40 on the mile, the rest as proposed) keeps the posts in band (half 27.0 / 3.5, mile
17.3 / 6.1; favorite 38.5; margin 2.0 L; photos 10.2%; trips lead 46 / pocket 15 / first-over 5 / mid-pack 21 /
behind 13) and brings the gate failures down to today's count, with one bad case left: the same horse, 35% -> 15%,
one more gate bar putting him on the lead against a gritty rival he'd have followed. Today's engine has that case
too, at 3 points. `racegod/retune_b.json` holds candidate B.

**RaceGod's read:** ship candidate B's post costs and lead/pocket values; the one failing case is the duel rule
(a horse out first who can't clear is pressed into a fight), which is a V-next of its own, not this retune. Patrick's
call: ship B, or the post costs alone (`c_post` half 0.15, mile 0.25) and leave the trip values for after the duel rule.

Patrick: ship candidate B (2026-11-02). Deployed in commit e9960fd (`outcome.P`: half c_post 0.15, A_lead 0.78,
A_pocket 0.57, A_fol 0.35; mile c_post 0.247, A_lead 1.24, A_pocket 0.67, A_fol 0.40). Smoke test on a save copy, 315
fields x 2: half post 1 / 8 = 26.7 / 3.1, mile 18.8 / 6.0, favorite 38.7, margin 2.0 L, no laws broken. No save change.
Next: read the first real night with `audit.py --since <tonight>` and write V10. Open: the duel rule (the one per-horse
case), the choreographer (V8), the 40 L wall (V3).

## V10 - A week under candidate B, on a copy, 2026-11-02 (Patrick: "what are we waiting for?")

**Method:** `racegod/dry_week.py` runs a copy of the live save (taken after the deploy) forward seven race nights
through `app.checked_tick` (every night check passed); the same seven nights again on another copy under the previous
values (commit 7a1a7bf). The game keeps the last 400 stories, so the audit reads days 2632-2636 (5 nights, 400 races)
of each. Fields are as the game drew them, which the lab couldn't do. Nothing live was touched.

| | Previous values | Candidate B (live now) | Band |
|---|---|---|---|
| Half post 1 / post 8 wins | 20.4 / 4.5 | **29.9 HIGH** / 3.0 | 19-27 / 1-6 |
| Mile post 1 / post 8 wins | 8.7 LOW / 7.7 | 19.0 / **4.9 LOW** | 15-20 / 6-10 (soft) |
| Winner within 3 L at the half | 48.0 LOW | 60.0 | 60-90 |
| Half winner 4+ L back at the half | 34.3 HIGH | 24.6 HIGH | 0-15 |
| Favorite wins | 39.2 | 36.0 | 30-45 |
| Median margin / photos | 1.6 / 8.2 | 2.0 / 11.2 | 1-3 / 5-15 |
| Speed limit set the time | 11.0 HIGH | 8.1 | 0-10 |
| Winning trips lead / pocket / fo / mid / behind | 28/20/13/22/18 | 45/14/6/24/10 | |
| Last horse (median) / 40 L+ races | 15.8 L / 3% | 17.7 L / 4% | |
| Laws broken | 0 of 400 | 0 of 400 | |
| Northern Star | won S6665 in 1:44.4 | won S6665 in 1:44.4 | |

**Measured.** Eight of ten in band against six before; the mile's post 1 now beats post 8 (19.0 vs 4.9) and the
winner is at the half with the leaders. Two misses, both post costs a touch strong on fields as drawn: half post 1 at
29.9 (the lab, on fields as they stood, said 26.7), mile post 8 at 4.9. The drawn fields differ from the lab's because
the retune changes who the computer barns enter where.

**Proposed (awaiting Patrick):** nudge the post costs only: half `c_post` 0.15 -> 0.12, mile 0.247 -> 0.20, then one
more dry week. The trip values stay. Still open: first-over winners 6% (chart target about 20%): the duel rule.

Patrick: nudge and rerun (2026-11-02). Post costs half 0.12, mile 0.20 in `outcome.py` (committed, **not deployed**);
a fresh copy of the live save run forward seven nights, days 2632-2636 audited (400 races, all true):
half post 1 / 8 = 24.4 / 3.9 (both in band), mile 18.5 / 4.3 (post 8 low, soft band, n 258: +-3 of noise),
winner within 3 L at the half 57 (band 60-90), favorite 40.0, margin 2.1 L, photos 9.0%, speed limit 11.4% (was 8.1:
one week's noise either side of 10), trips lead 43 / pocket 13 / first-over 6 / mid-pack 25 / behind 12.
Seven of ten in band, the two post misses gone on the half. RaceGod: deploy the nudge; the mile's post 8 needs a
bigger sample than a week to call.

Patrick: deploy (2026-11-02). Post costs half 0.12 / mile 0.20 live, commit f90a396; no save change. Next: audit the
real nights as they accumulate (`audit.py --since 2630` on a live copy) and write V11 when there's a week of them.

## V11 - The choreographer: the replay from a run of the decided result, 2026-11-02 (Patrick: "build it")

**Why (measured on the Sandhill Downs Cup, 2630-stake-S6697, watched live):** `story.build` placed nine of twelve
horses in one lane at the wire a length apart (a horse and sulky is a length and a half) and moved most of them a lane
between the stretch call and the finish call, which the viewer draws as bodies overlapping and horses passing through
each other. Its one rule for a pass (go outside everyone you passed) can't cope with a closer's race.

**Built:** `racegod/engine.py` `choreograph(order, track, passing)`: the run takes the decided result (the ledger's gate
order and trips, the decided times and margins), plays the trips with real traffic (lanes, slots, nobody within a body
of anybody, drivers yield only upward, juniors can't drop in ahead of a senior still outside), steers each horse to its
decided time through the drive, holds the stretch line to the wire, and returns the result unchanged with positions at
the seven calls. `story.build` uses it when `TD_STORY=choreo` is set and every horse carries a ledger, and falls back to
the placed story on any error (the picture never costs a race night). `racegod/choreo_rebuild.py` rebuilds kept
stories through it and counts picture faults; `replay_server.py` shows them.

**Measured, 93 kept races with a ledger from the live save, both ways:**

| | Placed story (live) | Choreographed |
|---|---|---|
| Races with two horses in one lane within a body, at the stretch call | 170 cases | 21 |
| ... at the wire | 127 | 4 |
| Lane changes between the stretch call and the wire (the "through each other") | 263 | 0 |
| Races with any picture fault | 90 of 93 | 21 of 93 |
| Audit laws broken (truth to the result) | 0 | 0 |
| Time per race | - | about 30 ms |

The Cup itself: 18 faults placed, 0 choreographed; the pocket horse is in the pocket, the first-over horse pulls when
the caption says, Lucky Magic comes three wide from last and the wire is the board. Watched in the viewer.
**Left:** the 21 stretch-call overlaps are horses sitting closer than a body in the drive while blocked (the follow
controller's slot is 16 ft, a body is 14); a slot of 18 ft or a check at the stretch call would clear most. Also
the 40 L wall is still applied (V3). Stories from before the ledger (older stakes) get a ledger read off their trip
text; they rebuild, less faithfully.

### Proposed (awaiting Patrick)

Ship it behind the switch: deploy, set `TD_STORY=choreo` in the service environment, restart; tonight's card is then
choreographed and the audit reads it. Rollback is unsetting the variable. The 93 rebuilt pairs are on
http://127.0.0.1:8115/ (`-choreo` and `-story` per race) while this session runs.

Patrick: deploy (2026-11-02). Code in commit 5eced9a; `TD_STORY=choreo` set in a systemd drop-in
(`/etc/systemd/system/trotdynasty.service.d/choreo.conf`), service restarted, the process sees it, `story.CHOREO`
True on the server. Rollback: delete the drop-in, daemon-reload, restart. Tonight's card is the first choreographed one;
V12 reads it (audit + picture checks via `choreo_rebuild.py`'s checks on the live stories).

## V12 — the half-pulled-out horse (2026-11-02, after the first choreographed night)

Patrick: Northern Star half pulls out and sits there (2654-hp-mile-Open-1); the 2 horse, Desert Melody, is parked out the whole race.

**Measured.** The choreographer spaces the single file 16 ft nose to nose and writes "lengths behind" in the story's unit, a fifth of a second (about 10 ft at race speed). The viewer draws a length as 8 ft and lets no two runners in a lane come inside 15.5 ft (RACE.BODY). So every slot lands on the screen at 13 ft, the viewer treats the whole rail line as held up, and its go-round logic eases each horse half a lane out and leaves it there. Desert Melody in the live story: viewer lane 0.9 from 6 s to 78 s, story lane 0. Northern Star in 2653-hp-mile-Open-1: viewer lane 0.55 from 54 s to 78 s on a story lane of 0.

**Change (racegod/engine.py).** SLOT 16 → 20 ft (16 ft on the screen) and BODY_L 1.5 → 2.0 L (the viewer's 15.5 ft). Not a driver rule; the units.

**Rebuilt through the lab viewer (horse-seconds more than a quarter lane off the story lane):**

| race | live story | slot 20 |
|---|---|---|
| 2654-hp-mile-Open-1 | 285 of 848 (Desert Melody 89) | 176 of 848 (Desert Melody 18) |
| 2650-stake-S6725 | 443 of 1050 | 211 of 1050 |

Desert Melody rebuilt: rail from 24 s to 78 s, out to lane 1 at the three-quarters as the story says. Northern Star in the Crown race: rail to 78 s, one tip-out, straight to the wire.

**Open.** The remainder (about 20% of horse-seconds) is the viewer's own re-simulation: a beaten horse swings a lane wider in the stretch than its story lane (Desert Melody to lane 2 from 90 s in both versions), and the slot still narrows to 15 ft late in the third quarter as the viewer closes gaps. Next: once this is live, a nightly count of horse-seconds off the story lane per race. Stories already kept on live stay as they were; only new nights get the wider slot. AI field fillers are not kept in the save, so `choreo_rebuild.py` now uses stand-ins for them.

Patrick: deploy (2026-11-03). Code in commit 5dd4c44 (deploy commit 0236b97), service restarted, slot 20 / body 2.0 and
`TD_STORY=choreo` confirmed on the server, login 200, no tracebacks. Stories kept before this night keep their old positions.
Next: the first night's stories under the wider slot through the lab viewer (horse-seconds off the story lane per race), and
the leader's drop-in timing (the story's seven calls put it at ~47 s on screen when the engine does it at ~28 s).
