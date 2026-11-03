# The retake: ratings, replay and breeding read off one engine

Branch `ratings-v2` (worktree `HarnessSim-v2`), 2026-11-03. Patrick: "Every aspect of the game and vision is officially
yours to perform a re-take on." Astra reviews 21-23 in `research/engine_lab/reviews/`. The walkthrough for the review is
`RATINGS_V2_WALKTHROUGH.md`; the candidate runs on 8113 beside live.

## The rule

One truth, one engine, and everything a player sees is a reading of it. Live's three systems disagreed: the engine
decided races on cruise and kick plus the trip, the clock reported the winner's class for everyone, and the card rated
a hidden Bayesian estimate. The retake makes them one thing, then gives every bar a job you can see.

## 1. The honest clock (`sim.squeeze`, `outcome.race`)

On the 2026-10-27 clock a bar was worth 2.3 s between horses and a fifth of a second inside a field; a beaten horse's
time was the winner's class plus its margin (measured: inside a field 1.2 L a bar, between fields 11.5). Now every
horse's time is its own: `FIG_FIT`'s line from the model's performance (ability, trip, form, luck together), with the
breed's spread pulled in about 1:52 by `SQUEEZE` 0.35, so a bar is worth about 0.8 s, four lengths, at the wire and on
the clock alike. The order, the margins and the clock are one thing; a nose is the least gap. The half-mile's own
allowance stays whole. Tier lines (`circuit.MILE_TIERS`): S+ 1:51.6, S 1:52.2, A 1:52.9, B 1:53.7, C 1:54.8. The
handicapper's clock evidence (`TIME_FIT`) is the same fit on the new clock; `mile_secs` (the rating as a time) is
refitted on 3.7M starts. Saved times, bests, records, replays and form lines move with `retime_v2.py` (`clock_v` 3).

The tail is eased (`EASED` 6 L): a horse beaten by more than six lengths is not driven out, and its margin grows by the
log past there (25 L reads 15, 70 L reads 23), so a field stays within sight; its figure still reads its performance.
Found in review (2026-11-03, Patrick on a Crown replay): with every horse at its own time the last flat horse was a median
25.6 L back (90th 44 L), and the choreographer drew all of it in the stretch. After: last flat horse median 15.2 L, 90th
18.4, max 21; winning margins unchanged (median 3.0, 90th 8.3). The choreographer also starts a well-beaten horse's fade
early enough that it never loses more than a tenth of its speed (`fade_ft`).

Measured on the review copy (400 races on a copy of the live save, before the eased tail): winning time median 1:51.6, fastest 1:45.2
(Northern Star), winning margin median 3.4 L, photo finishes 9%. On the 100-season world's late seasons: 1:51.1,
2.8 L, 10%. A horse's figures sit on its bars' predicted mile with sd 0.60 s (was 1.44 s on the old clock).

**The clock shifted 2.4 s slower (2026-11-03, live, `sim.CLOCK_SHIFT`).** Patrick, reading the 50-year history: half the breed
had run at or near the real record (22.5% of horses with 10+ starts had a best of 1:47.0 or faster; the engine's ceiling,
a 10/10 closer with a sharp night, luck and the bob, was 1:43.1). The whole line moved 2.4 s: ceiling 1:45.6 (the fifth
above his 1:45.5), tier lines S+ 1:54.0 / S 1:54.6 / A 1:55.2 / B 1:56.2 / C 1:57.2, middle horse 1:56.2; the handicapper's
fits (`TIME_FIT`, `MILE_FIT_V2`) follow it; `retime_v3.py` moves a save (clock_v 4). Measured on the kept races: winners'
median 1:49.4 -> 1:51.8, at or near the record 22.5% -> 0.7% of career bests. Order and margins unchanged (a shift).

**The bar's top (2026-11-03, Patrick: "I need bars to tell a clean story").** The tenth pip began at a hidden +6.0 with no
ceiling, so a 6.4 and a 12.1 both filled it (the card hid what the engine knew). `PIP_STEPS` now ends at 12.5, the breed's
top: a full bar is the best in the world. Manners keeps its own steps (`MANNERS_STEPS`): a perfect trip fills it by design.
On the live world 21 of 2,409 bars moved, all past +3.7 (top 1%); one bar in the game is full (Crimson Ivy's Stamina).
The engine reads the same bars, so the top few horses race a little slower and apart from each other.

**The trips cut to variety (2026-11-03, Patrick: "I don't ever want to see a horse like Northern Star get beat by a
marginally better horse to the tune of 9+ lengths"; "preferred position was meant to add variety, not lead to this").**
The ledger of that race: the two horses scored equal (both capped at 10 then), the 9 L were the trip (the following trip
with the closer's kick, 0.53 units) and the night's form (0.36). The fitted trip worths paid the lead 1.24 units (7.5 L) over
sitting back for an ordinary horse, the closer's kick 1.10 per unit of Speed (twice what the Speed itself was worth), and a
fast leaver could not take the following trip (it only existed once a first-over horse had pulled). Now (`outcome.P`):
A_lead 0.25, A_pocket 0.15, A_fo 0.05, A_fol 0.15, k_close 0.10, b_depth 0.06, s_form 0.06; `FOLLOW_EARLY`. Preferred
Position was never an engine input (a label from the early/late balance) and stays as one.
Measured (`research/engine_lab/retune_lab.py`, live copy): Northern Star v Crimson Ivy 1000 Invitationals, NS 64% -> 87%,
CI by 5+ L 18% -> 0%, within 2 L 10% -> 25%; a horse's night-to-night margin sd on the same field 1.5 L (breaks 1.4%);
pairs a length apart: the better ahead 56% -> 63%, its worst loss 13.8 -> 13.0 L (breaks); one more bar: kick +12.2,
cruise +11.2, grit +3.0, gate +0.5, manners +0.2 (the start bars now count only at the start and in a fight: open).
The clock: the trips were seconds, so `CLOCK_SHIFT` goes 2.4 -> 0 (ceiling 1:46.0, tiers S+ 1:51.6 .. C 1:54.8, middle
1:53.8); three dry nights: winners' median 1:52.0 as before, fastest 1:49.0, winning margin median 3.2 -> 1.8 L, last flat
horse 15.5 -> 11.3 L. Times stay as run; stored figures move -2.4 s with `retime_v4.py` (clock_v 5); letters unchanged.

## 2. Every bar races (`outcome.race`)

- **Manners at the start** (`M_START` 0.3): a unit of manners is worth 0.3 of gate speed; a rank horse on a bad night
  (`z < -1.5 + 0.8 * manners`) is **fractious behind the car**, leaves last and loses `FRACT` 0.15 units (about a
  length). 1.5% of starters.
- **Grit at the wire** (`FIGHT_L` 1.0, `G_FIN` 0.1): two horses within a length fight it out and the grittier gets the
  bob. 43% of starters are in a fight; the caption fires only when the winning margin is inside a length (12% of races).

Measured (1,500 random fields of 8 live horses, Spearman of each bar with finishing place): grit .30 -> .37, manners
.40 -> .47, kick .57 -> .59, cruise .50 -> .50, gate .50 -> .47 (manners now shares the start). Astra (review 23) asked
for single-bar interventions on identical fields and draws: 600 fields, one horse given one more bar of one stat, its
win rate from 16.2%: kick +11.5, cruise +5.3, grit +2.5, gate +0.8, manners +0.8 (and its fractious starts 6.3% -> 3.5%).
Review 23 also caught the fractious rule's sign (better manners made the bad night likelier); fixed, and the threshold set
so about 3% of starters (all with poor manners) are fractious: 119 in the review copy's 400 races.

## 3. The letter (`app.tier_label`, `badge_secs`, `letter_line`)

Proven (5+ starts): the median of the last ten figures, where a figure is the start's own time read fairly for the trip
(`outcome.figure`: the role's worth, the line's depth, a closer's extra kick taken out), needs three; hysteresis 0.1 s
(rechecked on the honest clock: flips while the ability tier held 38.8% -> 33.0%, same tier 72.9% -> 70.9%; 0.3 s would
have cost ten points of agreement on the tighter ruler).
Unproven: the bars' predicted mile against age peers mapped onto the proven shares (hollow, UNPROVEN). Retired: the
median of its ten best. The line under the name says why: "A on its last 10 miles, 1:53.1 read fairly · S at 1:52.2 or
better". `h.est` makes no badge; classes, claimers and the tote are unchanged.

Window study (every start of a 100-season world logged, `badge_windows.py`): windows 4..15 all beat shorter ones on
every count; ten chosen so a decline shows within a few starts. On the new world: same tier as the bars' predicted mile
72.9%, flips while it held 38.8%, next-season purses rank correlation .72 / .68 / .59 / .57 at ages 3-6. Decline delay
in starts (5,636 horses whose predicted tier dropped a full tier and stayed down ten starts): the letter follows within
0 starts for half of them, within 4 for three in four, and 4% hadn't dropped after 20. The handoff at the fifth start
(peer letter to earned letter) is still provisional: not measured.

## 4. The replay (`circuit.run_race` captions, `racegod/engine.py` story, `race.js`, `replay_hd2d.html`)

The choreographer draws the decided result as live does. New: it records when a horse broke; the story carries
`broke_at` and `fractious`; the viewer hops the runner behind the car or where it broke; the captions name the tells:
"fractious behind the car", "breaks stride" at the moment, "X and Y go head and head" (first-over within 1.5 L of the
leader at the three-quarters), "X is backing up" (one a race: was within 3 L at the three-quarters, lost 6 L to the
stretch), "fight it out" (margin inside a length), ", sharp tonight" on a sharp winner. On the review copy's 400
races: 81 breaks, 62 fractious, 50 fights, 37 backing up, 12 head and head, 97 sharp.

## 5. Breeding (`economy.foal_outlook`, `app.breed_page`, `sim.MUTATE`)

The mating outlook imagines 160 foals as before, but reads each at its peak on the badge's own ruler (`pred_mile` cut
at `MILE_TIERS`, S+ included); spread words on terciles of today's crosses (tight < 1.9 s, moderate < 2.2). It is
labelled as what it is, "Foals, at their peak": a projection of ability, not the letter a foal will earn (development,
racing and the window stand between). Each stallion shows his produce record (what his raced foals wear, and how many
raced). `MUTATE` 0.10 -> 0.05, the launch rule (DECISIONS 243).

## Drift and pedigree (100 seasons, `world100.db`)

S+ share of racing horses 3+: 4.8% (season 5), 6.3 (30), 6.1 (60), 8.2 (99): the breed gets about a second faster over
a century at the halved mutation and the letter follows it. The handicapper's est drifts up (54 -> 69) as it did on
live; it reaches no page as a letter now. Pedigree r (a horse's best predicted mile vs its parents', foaled season 70+)
measures 0.04 here against 0.13-0.20 in the launch rounds: hypothesis, range restriction (the no-player world breeds
only its top horses, so the parents hardly differ); not resolved in this round.

## Not done

- A manners tell beyond the start and breaks (the engine has none); the duel's head-bob in the positions themselves.
- The replay hop was checked in the story data and caption timing, not watched (the pane runs replays at reduced motion).
  Astra (review 23): watch a break, a fractious start and a close fight at normal motion before judging the replay.
- `SQUEEZE` 0.35 is a retake decision, not a measured optimum (Astra): margins now run 2.8-3.4 L median against the old
  under-2 L target; the knob is `sim.SQUEEZE`, and an affine squeeze changes no order and no win probability.
- `racegod/engine.py` carries two small additions here (break time, fractious flag) that will conflict with the RaceGod
  thread's uncommitted rewrite.
- Live's own badge can't be compared on this world any more (its est reads the new clock); the comparison that counts
  is Patrick's, 8113 beside trotdynasty.com.
