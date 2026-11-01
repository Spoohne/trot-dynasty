# Engine lab decision log

Newest at the bottom. **M** = measured (experiment named), **H** = hypothesis (not yet tested), **D** = decision.

## 2026-10-31

1. **D (Patrick):** Race and breeding are the two driving engines; Astra's outline (capabilities, causal trips, uncertainty
   in specific places, inherit potential not records, guard against creep, progression through understanding, build the
   test environment first) is the direction.
2. **M (code reading):** Today's race engine gives each horse a time from one formula (`sim.race`); the trip is a text
   label; the replay (`story.build`) draws positions after the finish order is decided.
3. **M (race probe, 20,000 races on live horses):** better horse beats worse 52% at a 0–2 rating gap, 73% at 10–12, 95%
   at 20+; strongest horse in an evenly matched 8-horse field wins 17% (12.5% by chance); post 1 wins 23% on a half-mile
   track, 16% on a mile; each running style wins in proportion to its share of starters; breaks 2.3% of starts.
4. **M (league v1, 2 seeds × 30 seasons):** superseded by item 7; its "foal potential is flat" and "strategic breeders
   gain nothing" conclusions were wrong (too short, and measured whole stables instead of foals).
5. **D (Patrick):** break the sire monopoly; drop "stronger pull to average"; keep an S+ label as a percentile only,
   never a cap on ability; hold any close-breeding cost until the monopoly is gone.
6. **D (Patrick, Astra agreeing):** run a diagnostic batch before changing any live rule.
7. **M (league v2, 6 variants × 8 independent histories × 50 seasons, ~300,000 births):**
   - Inflation is genetic and slow under today's rules: potential at age 4 rises from −3.0 (early crops) to −2.2 (late
     crops); public estimate 54.1 → 56.5 ± 1.8 at season 50; S/S+ share 19% → 23%.
   - Every change that makes breeding more effective speeds inflation: strong heredity alone → 36% S/S+; all four
     changes → 49%.
   - Sire concentration: top-5 sires sire 73% of racers today; spreading AI mares alone → ~50%; books of 30 alone → 66%
     and halves relatedness among leading sires (0.20 → 0.10).
   - Informed breeding already pays per foal: best-nick plan +1.4 potential (~8 rating points) over the average AI foal;
     tripled nicks → +3.3, and ordinary breeders fall to −0.7.
   - Better pairings raise useful foals 45% → 55% (worst to best fifth); exceptional foals stay ~5%; full-sibling spread
     ~3.0–3.3 under every rule.
   - Top-3 sire lines cover >99% of racers in every variant (collapsed in the pre-launch history).
8. **M (training test, corrected):** a first run was invalid (cloned horses shared one id, so they raced on one clone's
   stats). Corrected, 30 horses × 6 programs × 200 races: idle 2–3% wins, trained ~18–24%; finish focus wins 27–29%,
   manners focus 11–13% (at today's DEV_W 0.12 and at 0.4). Training matters a lot; focus choices are unbalanced.
9. **M (race prototype `race2.py`, 5 hand-tuning rounds):** step simulation with lanes, traffic, energy and box-ins
   works structurally; uncalibrated: front-runners win 53%, closers 4%, cover doesn't pay. Automatic fitting started.
10. **D (Patrick):** collaborate with Astra over the API as reviewer under the mandate in `MANDATE.md`.

## Open hypotheses

- **H1:** Stronger diminishing returns at the top of each trait and/or more genes resetting to average can hold inflation
  near flat without removing the breeding edge. (League round 2 running: `pkg`, `pkg_dim`, `pkg_reset`, `pkg_both`.)
- **H2:** Roughly doubled nicks plus spread AI mares plus books of 30 give the best skill edge per unit of inflation.
- **H3:** A fitted step-simulation can meet style balance, closer viability and the scenario directions at once.
- **H4:** The finish-focus training advantage comes from the race formula's weights (Finish 0.7 s/point vs Stamina 0.5)
  rather than from training itself.

## Review 1 (Astra, reviews/01_*.md) and responses

11. **Accepted (method):** judge round 2 by within-history paired differences and late-period slopes, not season-50
    endpoints; add a frozen baseline evaluator so a changed scoring map (`dim`) can't pass for genetic progress.
12. **Accepted (method):** relative "useful/exceptional" thresholds describe position within a population only; add
    fixed-threshold versions before claiming inflation control.
13. **Accepted (wording):** the strategy barns measure an *oracle-policy* advantage (they see hidden potential and nick
    values), not a player's skill edge. Strategy assignment isn't randomized and strategy barns book before the AI.
14. **Accepted (scope):** more genes resetting to average is in tension with Patrick's earlier "drop stronger pull to
    average". `pkg_reset` stays diagnostic; adopting it needs Patrick.
15. **Accepted (priority):** the fitter's targets are hypotheses and its scenarios don't isolate causes (move timing and
    following change together; different horses and draws). The random search was stopped. Next: a mechanics
    falsification gate (sequential vs simultaneous updates, DT 0.5/0.25/0.125, illegal crossings, finish order) before
    any further tuning.
16. **Registered predictions (Astra, hypotheses):** P1 `pkg` cuts top-5 sire share to ~40–60% without restoring founder
    lines; P2 `pkg` still drifts upward, its best-nick edge over AI smaller than `nick3`'s but still above ordinary;
    P3 `pkg_reset` reduces drift and parent–foal association vs `pkg` and keeps a best-nick edge over ordinary; P4
    `pkg_dim` looks more stabilizing on its own scale than on a frozen one; P5 `pkg_both` drifts least, with the
    breeding reward the main risk.

## 2026-10-31, round 2 and the mechanics gate

17. **M (league round 2, 4 variants × 8 histories × 50 seasons, paired against base by seed; `paired_round2.json`):**
    - `pkg` (books of 30 + spread AI mares + doubled nicks): top-5 sire share −23.5 ± 6.0 points (to ~50%); public
      estimate +3.1 ± 1.4 at season 50; S/S+ +7.4 ± 3.4 points (to 30%); late slope (seasons 30–50) unchanged vs base
      (−0.05 ± 0.47 per decade); best-nick minus ordinary +0.93 ± 0.55 over base's.
    - `pkg_dim`: no measurable difference from `pkg` on public estimate or S/S+.
    - `pkg_reset`: lowest drift of the four (estimate 58.3 vs 59.6 for `pkg`; S/S+ 26% vs 30%; late slope 0.28 vs 0.56
      per decade), with the best-nick edge over ordinary kept (2.7 vs 2.5).
    - `pkg_both`: no better than `pkg_reset`.
    - Predictions: P1 confirmed; P2 confirmed (drift continues); P3 confirmed on drift and edge, parent–foal association
      not measured; P4 not supported (no stabilizing on public measures either); P5 not supported.
18. **M (mechanics gate, `mechanics_gate.json`):** no illegal crossings in either update. Sequential updates don't
    converge with step size (front-runner wins 52% → 50% → 37% at DT 0.5/0.25/0.125); simultaneous updates converge
    (front 29% / 29% / 28%, closers 8% / 12% / 12%). Review 1's hypothesis confirmed: much of the front-runner advantage
    was an update artifact. `run()` is now simultaneous; `run_seq` kept for comparison.
19. **M (paired scenarios, simultaneous, 600 pairs):** tactics still don't decide outcomes. Following cover vs refusing it:
    19% vs 19%. Moving at 0.3 vs 0.72: 18% vs 15% (early is not punished). Closer, calm vs duel ahead: 18% vs 17%.
    Leader alone vs with a second leaver: 34% vs 60% (backwards). The fixed box case never registered a box.

## Review 2 (Astra, reviews/02_*.md) and the tests it asked for

20. **M (direct paired, 8 histories):** `pkg_reset − pkg`: late slope −0.29 per decade (se 0.08, lower in 8/8 histories);
    S/S+ at season 50 −4.2 points (se 1.1, 8/8); public estimate −1.3 (se 0.4, 7/8). Factorial interaction
    (`both − reset − dim + pkg`): slope +0.51 (se 0.37), inconclusive. Frozen evaluator still missing (genes not saved).
21. **D (Claude, per review 2):** fixed braking to per second; neighbors recomputed after lane changes; shelter logged;
    `no_shelter` and `press_until` instructions added for mechanism tests. Crossing detection still ignores lane changes
    and traffic is still resolved in position order (noted, not fixed).
22. **M (mechanisms.json):**
    - Pathwise convergence with fixed move points and no breaks: same winner as DT 1/16 in 88% (DT 1/8), 77% (1/4),
      60% (1/2); mean time gap 0.04 / 0.12 / 0.21 s. **D:** the engine needs DT ≤ 0.125.
    - Energy dose, alone in the stretch from the three-quarters: last quarter 28.8 / 28.2 / 27.4 / 26.9 / 26.2 s at energy
      0 / 15 / 30 / 45 / 75. Actual energy at the three-quarters: sheltered ≥20 s 63 vs < 20 s 42; moved before 0.55: 39 vs
      after 0.7: 72 (95% of late movers above the 45 where the kick is whole). Hypothesis (a) rejected: energy differences
      are large and do move the kick; late movers carry energy they can't use.
    - Shelter on vs off, same trip, 500 pairs: win 20.0% vs 15.6%, energy at the three-quarters 47.5 vs 43.9.
    - Duel openings (500 each): subject leads unchallenged 27.6% wins; pressed alongside to the half 98.6% (energy 14.7);
      rival clears ahead 70.2%. **New finding:** the field doesn't respond to the pace (horses more than 6 lengths back
      cruise), so a fast early pace escapes instead of costing the leaders.
    - Forced box: the box held 11.5 s, but the test is confounded (the rival kept outside also pressed the leader). To
      redesign.
23. **M (mating weight, `mating_round3.txt`, 8 paired histories × 50 seasons, everything else as `pkg`):** AI weight on
    sire quality 0.3 and 0.0 (vs 0.6). Selection differential of AI-chosen sires over the eligible pool: +1.16 at 0.3,
    −0.01 at 0.0. Late slope vs `pkg`: +0.31 (se 0.21) and +0.29 (se 0.19), i.e. no reduction in drift; vs `pkg_reset`:
    +0.59 (se 0.27, 7/8 higher) and +0.57 (se 0.24, 8/8 higher). Sire concentration falls sharply: top-5 share 50% →
    37% → 29% (8/8 histories). Best-nick minus ordinary edge kept (2.8 / 2.7 vs 2.5).
    **H5 (new):** AI sire choice isn't the selection engine; stud-book eligibility is (`economy.studs` lets only the 25
    best retired stallions stand), plus which mares are kept and bred.

## Review 3 (Astra, reviews/03_*.md)

24. **Accepted:** H5 narrowed to "selection within the eligible pool isn't the controlling lever". Decisive test now
    running: 2×2 eligibility (top 25 vs every retired stallion with a reputation) × AI quality weight (0.6 vs 0.0), plus
    `pkg_reset`; 8 paired histories × 100 seasons; genes saved for a frozen evaluator; selection logged at each stage.
    **Predeclared "matches reset" criteria (Astra's proposal, adopted for this test):** one-sided 95% upper bound on the
    paired late-slope difference vs reset ≤ +0.10 estimate points per decade over seasons 50–100; S/S+ endpoint upper
    bound ≤ +2 points; ≥ 80% of reset's oracle pairing advantage kept; drift confirmed on the frozen evaluator.
25. **Accepted correction:** energy above 45 isn't stranded: 75 beats 45 by 0.78 s because surplus delays the fall
    below 45. Convergence is improving, not certified.
26. **D (Claude, per review 3):** continuous pace controller replaces the six-length tracking cutoff; scripted
    `fixed_v`/`lane_lock`/`ghost` instructions for the forced-box control. Tests running (`mechanisms2.py`).
27. **Raised to Patrick (mandate: conflicts with his earlier direction; third review round):** is "more genes reset to
    the breed average" still excluded, or may it stay a candidate alongside the selection-based alternatives being tested?
28. **M (mechanisms2.json, DT 1/8):**
    - Scripted forced box (identical leader and blocker trajectories; only the blocker's solidity differs): boxed 12.6 s,
      last quarter 27.03 s vs 26.57 s open. Positive control passes: the box costs 0.46 s.
    - Step size vs 1/32 (200 fixed fields): same winner 91.5% at 1/16 (12 of 17 flips under 0.1 s margin), 86.5% at 1/8;
      mean time gap 0.023 s and 0.081 s. **D:** prototype runs at DT 1/16 for acceptance tests, 1/8 for screening.
    - Pace response by leader's early speed (−1 / 0 / +1 / +2): field gap at the half 6.3 / 6.9 / 7.5 / 8.0 lengths;
      field energy at the three-quarters 45.9 / 44.7 / 42.6 / 40.1; leader 27.7 / 20.5 / 14.2 / 8.5; leader wins 22 / 15
      / 16 / 21%. The field now follows and pays; a fast pace no longer escapes.
    - Duel openings: unchallenged 14.0%, pressed alongside 56.2%, rival clears 46.3% (was 27.6 / 98.6 / 70.2). Still
      backwards: being pressed helps the leader. Cause not yet isolated (**H6:** the challenged leader's dig-in raises its
      own speed, and the pressing rival, exposed outside, fades into the field's path).
29. **D (Patrick, answering item 27):** gene reset stays a candidate, to be compared against the selection-based
    alternatives; Patrick picks the mechanism later. Not adopted yet.
30. **M (duel, 300 per arm, DT 1/8):** with the challenged leader's dig-in at 2.5 ft/s: unchallenged 13.0%, pressed
    55.3% (energy at the three-quarters 24.9 vs 12.1). With dig-in 0: 13.0% vs 18.0% (25.5 vs 24.2). H6 mostly confirmed:
    the dig-in drives the backwards duel (the whole field tracks the faster leader and the exposed presser pays most);
    a small residual remains.
31. **M (100-season stud-book test, `criteria_l3.json`, 8 paired histories per arm, seasons 50–100, vs `pkg_reset`):**
    - `pkg` (top 25 stand): fails drift (upper 95% +0.13) and S/S+ (+0.05); edge 86% of reset's. No match.
    - `pkg_q00`: fails drift, S/S+ and edge (77%). No match.
    - `pkg_all` (every retired stallion with a reputation may stand): passes all three (drift upper +0.087, S/S+ upper
      −0.002, edge 115%); frozen drift same as reset. **Matches reset.**
    - `pkg_all_q00` (open stud book, AI ignores sire quality): passes all three by wide margins: late slope 0.08 vs reset
      0.46 per decade (upper −0.27); S/S+ 20% vs 33%; frozen genetic drift 0.013 vs 0.100 per decade (−0.087, se 0.021);
      top-5 sire share 10%; edge 105% of reset's. **Beats reset.**
    - Even reset drifts over seasons 50–100 (0.46 per decade public, 0.10 frozen); none of the arms is proven stationary.
    - Selection stages at season 100: under the open book with quality-blind AI the herd is weaker (2-year-old males −1.59
      vs −0.68 under `pkg_q00`).
    **H5 confirmed for this model:** stud-book eligibility (top 25) is the main selection engine; opening it matches reset
    without touching inheritance, and opening it with quality-blind AI mating nearly stops drift.
    **Player-experience caveats (for Patrick):** a weaker AI herd changes how hard the AI competition is; an open stud
    book changes stud fees and stud income (not measured).

## Review 4 (Astra, reviews/04_*.md)

32. **Accepted framing:** the open book with quality-blind AI "beats reset" on drift and sire concentration only, not on
    gameplay; H5 is an eligibility × AI-mating-policy interaction (open eligibility with quality-weighted AI only matches
    reset); none of the arms is proven stationary; reset's earlier drift advantage over `pkg` isn't clear in seasons 50–100.
33. **M (edge bound, paired, one-sided 95%):** candidate edge − 0.8 × reset edge: `pkg` +0.11 (lower +0.03), `pkg_q00`
    −0.05 (lower −0.33, not established), `pkg_all` +0.63 (lower +0.33), `pkg_all_q00` +0.45 (lower +0.21). Caveat: this is
    the strategy-barn (oracle) comparison, not the matched-mare assay.
34. **Next (Astra):** breeding — reset vs open book at AI quality weight 0.6 / 0.3 / 0.0, adding public-information player
    policies with equal starting assets, a higher informed-player share, stud economics (fees, covers, sire-owner income,
    failed bookings, births) and absolute player vs AI strength. Race — a small constrained fit at DT 1/16 with hard gates
    (geometry incl. lane changes, 1/32 robustness, energy/shelter, box delay at several durations, scripted pace
    openings, class and gait sanity), soft style/time targets, and a frozen held-out bank (half-mile, field sizes, posts,
    leaver counts, breaks on).
35. **Raised to Patrick:** which breeding direction to carry into that round.
36. **D (Patrick, answering item 35):** open the stud book. Any owner may list a stallion publicly by paying a listing fee.
    Gene reset is dropped from the next round.
37. **Next round (league v3):** listing fee $0 / $100k / $250k per season × AI sire-quality weight 0.6 / 0.3 / 0.0, 8 paired
    histories × 80 seasons. **H7:** a listing fee re-selects for quality (only stallions worth listing stand) and can bring
    drift back; the fee level that keeps drift near the open-book result is the target. Adds stud economics (listing fees,
    covers sold, stud income by owner), a public-information player policy, and absolute player vs AI strength.

## Race fit setup (review 4, item 34)

38. **M (geometry gate):** the prototype's starting layout put up to three horses in one lane a tenth of a length apart
    (8,080 overlap violations in 80 races). **D:** the field now starts side by side, one lane per post, and tucks in;
    0 violations after the fix. All earlier race measurements used the old start; the gates were re-baselined.
39. **M (baseline gates, today's settings, DT 1/8):** geometry, energy dose, shelter (place gain 0.53, energy +4.6), box
    (costs 0.90 s from 0.6 and 0.46 s from 0.75) and class (+1 wins 52%, +2 wins 67%) pass; scripted pace fails; breaks
    implausible (1.14 per start at manners −2); style shares off (closers 0.7%, front 34%, stalk 50%).
40. **D:** pace gate = a fast opening costs the field ≥ 3 energy vs slow and doesn't bring it closer; break plausibility
    gate 0.08–0.35 breaks per start at manners −2; `break_k` made fittable. Screening started (4 workers × 12 configs).
41. **M (bug):** the first listing-fee run charged the fee to barns that couldn't pay; cash went negative and the
    economy's own check stopped two histories. **D:** an owner lists a stallion only if it can pay the fee and keep its
    reserve; the fee is booked as a stud expense. The 72 histories were rerun from scratch into a new folder.

## Launch scenario (Patrick, 2026-10-31)

42. **D (Patrick):** the live game's current players are test accounts and aren't representative. The launch scenario
    starts from a fresh world built on whatever baseline the lab settles on, not from the live save.
43. **M (code reading):** `app.new_game` builds a world by seeding foundation stock and simulating `HISTORY` = 50 seasons
    of history by the full rules before Year 0 (`app.new_world` does this on launch day and gives every player a new
    starter barn). The sire monopoly (73%) and the collapse to three sire lines in today's world were produced by that
    pre-launch history under today's rules.
44. **Plan:** the launch scenario regenerates a world with the candidate rules applied during its history, then adds
    player-like barns in waves from Year 0, and reports seasons 1–10 (what players feel) separately from the 50–100
    season hardening runs. The history length itself (50 seasons) becomes a parameter to test.
45. **Real-time scale:** 1 season = 52 race nights = about 7.5 weeks; 10 seasons ≈ 1.4 years; 50 ≈ 7 years; 100 ≈ 14.
    Long runs are hardening tests; early-season results are what players experience.
46. **D (Patrick):** a developer pilot. Once the launch scenario exists, Patrick plays it himself on a private local
    copy (fresh world, candidate rules) as the first true player, making every decision, with the clock under his
    control (fast-forward between race nights). His experience is evidence the bots can't give; findings go into this log
    as pilot observations, separate from measured results.

## Replay realism (Patrick, 2026-10-31)

47. **D (Patrick):** the race engine must also play well as a replay. Looking realistic on screen is a requirement of
    the engine, not an afterthought.
48. **M (code reading):** today's replay (`mockups/replay_hd2d.html`) is drawn from `story.build`, which invents positions
    after the result; the prototype records only four calls, and its lane changes happen in a single step (a horse
    would jump a full lane between frames).
49. **Plan:**
    - **Record:** the prototype writes every horse's distance, lateral position and speed at a fixed frame rate
      (about 4 per second) plus its events; lane changes become gradual moves across the track over about a second.
    - **Visual gates** (added to the fit, hard): no lateral jump faster than a set rate; no horse moving backward
      through the field without a reason (break, tiring, boxed); field spread at each call inside a plausible band; two-
      and three-wide trips present but not routine; every pass visible as an outside move.
    - **Adapter:** a copy of the replay reads the prototype's record directly instead of `story.build`, on the PC test
      server, so the same race can be watched under the old and new engines side by side.
    - **Review:** Patrick watches a set of replays (also part of the developer pilot) and his notes are logged as pilot
      observations.
50. **M (race fit screen, 48 configs at DT 1/8):** none passed every gate (first failure: class 39, pace 6, shelter 3).
    The class failures were the break plausibility check: the search stayed near today's break rate (0.7–1.2 breaks per
    start at manners −2). With break_k lowered to 0.0002 the best config passes geometry, energy, box, pace and class
    (0.18 breaks per start at manners −2) but fails shelter (place gain 0.29, energy +1.1 < 3). Across all 48 configs
    closers never won more than 5%: **H8:** closer viability is structural (move timing, traffic on the rail, or kick
    size), not a setting the current search range can fix.

## Listing-fee test (log item 37; `listing_l5.json`)

51. **M (72 histories × 80 seasons, each fee paired with the $0 fee at the same AI weight, seasons 40–80):**
    - **$100k per season:** no measurable change from a free book at any AI weight (≈550–585 stallions listed vs
      ≈565–625; drift, S/S+ and top-5 differences within one se). It removes about $55M a season from barns.
    - **$250k:** only ≈16 stallions list (the listing rule is "list if house price × 10 ≥ fee"); top-5 sire share
      +27 to +34 points; S/S+ +5 to +12 points; frozen drift up at every AI weight. **H7 confirmed:** a fee high enough
      to thin the book re-selects for quality and brings the monopoly back.
    - **AI sire-quality weight with a free book:** 0.6 → frozen drift 0.10 per decade, S/S+ 30%, top-5 26%;
      0.3 → 0.05, 24%, 14%; 0.0 → 0.00, 20%, 11%.
    - **Breeding edges (frozen potential over ordinary breeders):** oracle best nick +1.6 to +1.9 everywhere; the
      public-information plan +0.3 to +0.9 (smallest at $250k).
    - Player racers vs AI racers (strategy barns, potential): −0.03 to −0.53 — the strategy barns' racing stables are
      not stronger than the AI's, because their plans only shape foals.
    - Caveat: listing decisions use a simple rule, not expected covers; stud income per owner not yet summarized.

## Review 5 (Astra, reviews/05_*.md)

52. **Accepted:** $250k restored concentration *under the current listing rule*, which is itself a quality cutoff
    (house price × 10 ≥ fee); it doesn't prove every meaningful fee must. Target broad *effective* access (distinct
    sires actually used), not "every stallion lists". Next fee designs: (a) a small flat fee with demand-aware listing
    decisions; (b) a small fee plus a share of realized stud revenue — needs Patrick (it reinterprets "paid listing").
53. **Accepted (baseline):** launch tests start at AI sire-quality weight 0.3, bracketed by 0.0 and 0.6; "best-to-best
    works" still to be shown on matched mares.
54. **Code finding (Astra, confirmed in race2.py):** every horse targets sprint speed at its own 0.75 of the mile
    regardless of `move_at`, so a late move point mostly delays lane behaviour, not acceleration; `kick_late` scales
    late-speed ability, not the closer style. Next: a move-point × traffic-access assay (timing sweep with the 0.75 rule
    toggled; unobstructed path at matched length; kick and energy transplants from identical three-quarter states).
    No closer bonus.
55. **Accepted (gates):** freeze the shelter gate as a paired performance test with uncertainty plus a controlled
    physical-saving test, not a fixed energy margin (the code used > 2, the log said 3). Replay gates: a pass needs a
    continuously clear path (not always outside); losing position needs no event, only consistent velocities; add swept
    footprints in lane changes, track bounds, bounded lateral and longitudinal acceleration, no snapbacks, consistent
    turn distance and finish crossings; spread and wide-trip frequency are soft distributions. Smooth lane changes must
    happen in the simulation; store physics-step trajectories until a 4 Hz export is shown to preserve paths.
56. **Accepted (launch):** pair candidates on foundation stock and world seed with rules applied before history; test
    history lengths 10/25/50; report starter fairness and early vs late entrants; freeze and archive pilot builds and log
    Patrick's information and decisions before showing hidden outcomes; keep breeding conclusions provisional until the
    race engine is settled.
57. **Raised to Patrick:** listing fee design (item 52).
58. **D (Patrick, answering item 57):** AI barns don't list stallions in the public stud book. At launch the book is a
    predefined, curated set of stallions; the game runs on them for a while; as they age out, the public book is kept up
    only by players listing their own stallions (paying the listing fee).
    Consequences to test: (a) the curated book's size and quality spread at Year 0; (b) when the curated stallions age
    out (stallions stand until 20) and whether the player-listed book is big enough by then; (c) concentration once only
    players supply sires — a thin player book can recreate the monopoly; (d) AI barns' mares then breed to player
    stallions, which makes stud fees a player income source; (e) the listing fee only applies to players, so its design
    is about player economics rather than AI behavior.
59. **D (Patrick):** AI barns never breed to player-listed stallions. AI barns don't breed for the public world at all:
    their crop is topped up between seasons to hold set numbers, filling gaps when the human player count is low. They
    exist to supplement the world ("life") and to be healthy but beatable competition.
    Consequences:
    - The breeding engine now serves players only: the curated launch book, then player-listed stallions, bred to
      player mares. Every AI-side breeding experiment (AI sire-quality weight, AI mating spread) no longer applies to the
      launch design; it stays in the log as background.
    - AI horse quality becomes a designed dial (the top-up generator), not an evolving gene pool. Drift and inflation now
      come from player breeding alone, measured against a fixed AI benchmark.
    - **Working assumption (to confirm with Patrick):** the AI top-up draws from a fixed quality distribution, not one
      that follows the players' level, so the competition never secretly adjusts.
    - Launch scenario v1: curated book at Year 0 → player barns breed and list → AI crops topped up each season →
      measure player-herd drift vs the fixed AI level, book size and concentration once curated stallions age out, how
      often AI wins, and how quickly a new player can compete.
60. **D (Patrick, answering item 59's assumption):** AI competitiveness is tuned by hand, year to year, by Patrick (a
    deliberate, visible setting, not automatic rubber-banding). The starting AI crop is competitive. If strong players
    pull away from the AI over time, that softening is accepted (even welcome), on the expectation that a healthy human
    player base carries the competition.
    For the lab: the AI top-up quality is a fixed setting per season; the launch scenario reports the player-vs-AI gap
    each season so Patrick has the numbers for his yearly call, and tests how the gap develops with few vs many players.

## Closer assay (review 5, item 54)

61. **D:** `drive_all` (where horses not already committed go for home; 0.75 = old rule) and `surplus_k` (extra kick from
    energy above the full-kick threshold; 0 = old rule) added to race2.P.
62. **M (closer_assay, 300 matched races per combination, DT 1/8):** drive point 0.75/0.85 × surplus kick 0/1.5 × closer
    move point 0.74/0.85: closers win 0.0–1.3% in every combination (vs ~17% of starters). Closers sit ≈7 lengths back at
    the three-quarters, finish with 13–17 energy unspent, spend ≈4–7 s boxed.
63. **M (closer_traffic.json, 400 paired races):** the same closer with normal traffic vs an unobstructable clear path:
    wins 1.5% vs 2.2%, loses to the winner by 1.07 s vs 1.05 s; with a clear path it spends its reserve (energy left 13.9 →
    5.9) and is no faster. **Traffic is not the main cause.** **H9:** the deficit is: sitting ≈7 lengths back saves too
    little energy relative to leaders, whose top speed barely falls, so the kick can't close ≈5 lengths.

## Review 6 (Astra, reviews/06_*.md)

64. **Accepted (test flaws):** the clear-path switch also removed shelter and following, so item 63 confounds
    obstruction with cover; the surplus-kick test never requested the surplus speed (the sprint target still clipped it),
    so item 62 says nothing about a stronger fresh-horse kick; "1.05 s behind the winner" mixes subject and winner times.
    H9 stays a hypothesis: "the late trip may surrender more distance than its energy advantage can recover".
65. **Next (race):** repair both interventions (separate obstruction, cover and following; let the drive target reach
    the energy-dependent ceiling), rerun paired at DT 1/16 with breaks off, and log the recovery budget (gap at
    commitment, time left, speed advantage and its integral; 7 lengths in 25 s needs ≈2.2 ft/s). Then test, in order:
    split energy into locomotion (speed) and air (exposure, ~airspeed cubed, reduced by shelter) applied to every exposed
    horse; a steeper fatigue curve that a fresher horse can actually use; sitting gap 3/5/7 lengths; a steeper
    high-speed cost for every horse at that speed. No closer bonus and no "pace-setting tax".
66. **Accepted (breeding for launch):** the AI mating-weight sweeps are retired. Launch tests: (1) curated-to-player
    stud supply through the retirement transition, with player arrival and attrition; (2) player-only breeding progress
    on matched mares with public-information plans; (3) listing economics with players as the only customers; (4)
    competition against a fixed, versioned AI benchmark plus scheduled yearly settings.
67. **Open question for Patrick (affects the launch model):** can AI top-up horses pass into player hands (claimed,
    bought on the board, or bred from)? If so they are an extra genetic and economic input.
68. **Patrick's point (2026-10-31):** closers start their move *earlier*, not later — a late finisher gains ground
    first-over or second-over from the far turn. **M (closer_assay, 300 matched races each, drive point 0.75):** closer
    move point 0.55 / 0.62 / 0.68 / 0.74 / 0.85 → closer wins 5.0% / 1.3% / 1.7% / ~1% / ~0.5%; lengths behind at the
    three-quarters 4.2 / 5.0 / 6.1 / 7.0 / 7.8; energy left at the finish ≈12–14 throughout; boxed 9.6 s at 0.55 vs ~7 s.
    Earlier moves help (the only lever so far that moved closer wins), but closers still finish with energy unspent.
    The timing sweep extends earlier; the move point becomes a real driver/owner choice in later work.
69. **D:** `budget` (a committed horse aims for the fastest speed it can hold to the wire on its remaining energy, at full
    exposed cost; it leaves cover when the horse it follows is slower) added to race2.P, off by default.
70. **M (closer_assay with budget on, move points 0.55/0.62/0.68/0.74):** no change (closer wins 5.0 / 1.7 / 2.0 / 0.7%;
    energy left at the finish ≈15 everywhere). The budget speed exceeds the horse's top speed, so the request is capped by
    ability, not energy. **Finding:** in the stretch every horse runs at its ability ceiling; energy only lowers that
    ceiling below the full-kick threshold (45), which leaders rarely reach before the wire. Saved energy therefore has
    nothing to buy. This supports testing Astra's candidate (b) (fatigue that lowers speed continuously as energy falls,
    so a fresher horse is genuinely faster late) together with the energy split (item 65).
71. **D (Patrick, answering item 67):** AI barns never list a horse on the sale board, but they race in claimers, so
    their horses can be claimed by players. For the launch model: claimed AI horses enter player ownership and can be
    raced and bred, so each AI top-up crop is a genetic and economic input to the player world through claiming. The
    launch scenario tracks claimed AI horses (how many, their quality vs player-bred horses, and their share of player
    breeding) and the 2-claims-per-night cap applies.
72. **D (Patrick):** backend complexity isn't a constraint; if the engines need another server, raise it. The lab
    doesn't simplify mechanics to save compute, but reports the live-server cost of anything that runs at race time.
73. **Context (Patrick, 2026-10-31):** realistic dream scenario is a 400–500 player base, arriving as a trickle, not
    thousands. Discussed single-player worlds and small-cohort worlds; at this scale one shared world is the working
    assumption (cohorts would split a small base too thin; single-player gives up the stud book, market, claiming and
    prestige). Not a final decision.
74. **Plan change (launch scenario):** model 20 / 100 / 500 players arriving as a trickle with attrition; add divisions
    (leagues by barn age or earnings, each with its own stakes and champion) as a variant; report seasons 1–10 for a
    launch-day player and separately for a player who joins about a year in.
