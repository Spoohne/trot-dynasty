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

## Review 6 follow-up (2026-10-31)

75. **D:** the two flawed tests repaired: the clear-path switch now removes traffic only (shelter always reads the real
    field); a committed horse now requests its real top speed (so a surplus kick is asked for, not clipped). Added
    `split` (energy = locomotion for every horse + air resistance ∝ (v/cruise)³ cut by cover; base cost lowered by
    `air_k` so a lone horse at cruise spends the same) — off by default.
76. **M (closer_assay, budget on, 300 matched races each, DT 1/8):** fatigue threshold `tank_full` 45 (step) vs 100
    (gradual) × split off/on × closer move point 0.55/0.68:
    - 45, no split: closers 5.0% / 2.0%; front 31%; closer energy left 15.
    - 45, split: 4.0% / 0.7%; front 40%; energy left 10.
    - 100 (gradual), no split: 1.7% / 0.7%; front 55%; energy left 27.
    - 100, split: 1.0% / 0.3%; front 59%; energy left 22.
    Gradual fatigue *helps front-runners* and leaves closers with more energy unspent: a fresher closer is only slightly
    faster than a tiring leader (at most ≈1.5 ft/s for a 20-point energy gap), not enough to close 4–6 lengths, and a
    field that is a little slower everywhere favours whoever is in front. The air-resistance split alone doesn't change
    closer viability. **H10:** the closer's kick ceiling is the binding limit; the late-race speed a fresh horse can reach
    must exceed a tired leader's by enough to recover its deficit (≈2.2 ft/s over the last quarter for 7 lengths).

## Review 7 (Astra, reviews/07_*.md)

77. **Accepted (test flaw):** raising `tank_full` from 45 to 100 made fatigue start earlier but *weakened* its
    sensitivity (0.168 → 0.076 ft/s per energy point for an average horse), so item 76 tested earlier, shallower fatigue,
    not "freshness matters more". `budget_speed` still uses the old cost formula; budget is off for mechanism tests. The
    base-cost normalization for `split` was done in the assay config (closer_assay.py), as item 75 says.
78. **Accepted (direction):** separate maximum speed, sustainable effort and a finite reserve for effort above
    sustainable, identically for every horse; some deficits should be unrecoverable. No combined ceiling/cost/pacing
    changes in one step.
79. **Next (Astra):** recovery-envelope assay — 20 saved half-mile states with identical-trait leader and closer;
    continuations move 0.55 vs 0.74 × tank_full 45 vs 100; clear path with prescribed exposure, breaks and budget off,
    DT 1/16; record distance recovered, what limits speed (request, acceleration, fatigue ceiling, fresh maximum), the
    energy trajectory, and an optimistic recovery bound at the fresh maximum. Predeclared readings: earlier commitment
    recovers enough → driver timing; fresh bound catches but actual doesn't → fatigue/expenditure; even the fresh bound
    can't → don't tune fatigue; budget-off much better → fix the controller.
80. **M (recovery_envelope.json, 20 saved half-mile states, identical-trait leader and closer, clear path, breaks and
    budget off, DT 1/16):** recovered lengths / closer beats leader: move 0.55 + tank 45 → 6.4 / 10%; 0.55 + tank 100 →
    8.6 / 70%; 0.74 + tank 45 → 7.0 / 45%; 0.74 + tank 100 → 5.7 / 10%. The fresh-maximum bound beats the leader in 95–100%
    of states. Reading (predeclared): ability isn't the limit; with an unobstructed run an equal closer can catch the
    leader, and an early move pairs with gradual fatigue (Patrick's "save early, spend from the far turn").
81. **M (repaired closer_traffic, 400 paired races per arm; shelter kept, traffic only removed):** closer wins traffic vs
    clear: move 0.74 + tank 45 1.3% vs 12.0%; 0.55 + 100 2.2% vs 10.7%; 0.55 + 45 5.8% vs 7.2%; 0.74 + 100 0.5% vs 1.0%;
    boxed 3–11 s with traffic. **Item 63's conclusion ("traffic is not the main cause") is withdrawn** — that test was
    flawed (item 64). Traffic is a main cause of closer failure. Next lever: how closers find a route (outside flow,
    second- and third-over, pulling before the box shuts), not physiology.

## Route-finding and track geometry (2026-10-31)

82. **D:** added `route` (angle off the rail before the move; three-wide when the outside is blocked), `mile_turns`,
    `stretch_at` / `stretch_lanes` (how wide the stretch may fan), `gap_late` / `gap_mid` env overrides in the assays, and a
    box trace. All default to the old behaviour.
83. **M (route on vs off, 400 paired races and 300 field races per arm):** no change (closer wins and boxed time
    unchanged). **M (box trace, 150 races, 4,063 boxed steps):** ~80% of closer boxing happens in the last fifth of the
    mile, mostly in lanes 1–2 behind other movers; 38% while already three-wide, the widest the engine allowed.
84. **M (code reading):** the mile track's last turn ended at 0.97 of the mile — a ≈160 ft homestretch. **H11:** the short
    stretch and three-wide cap, not physiology, are what deny closers a run.
85. **M (closer_assay, 300 races, route on):** an eighth-mile homestretch fanning five wide (turns 0.125–0.375 and
    0.625–0.875) vs the old layout: closer boxed time 7.0 → 3.4 s; front-runner wins 35% → 10%; mid 12% → 20%; stalkers
    52% → 67%; closers 1% → 2%. Adding closer sitting distance (gap_late) 7 / 5 / 3 lengths, tank 45, move 0.68: closers
    2.0 / 6.3 / 8.7%, stalkers 67 / 64 / 58%. With tank 100 and move 0.6 front-runners stay at ≈33%.
    Current best combination (long stretch, five wide, tank 45, move 0.68, gap_late 3): front 11%, stalk 58%, mid 23%,
    late 9% (starter shares 17 / 33 / 33 / 17). Closers fixed by geometry and position, not a bonus; stalkers now dominate.

## Review 8 (Astra, reviews/08_*.md)

86. **Accepted (narrower H11):** longer, wider finishing geometry cuts boxing; a smaller sitting gap lifts closers further;
    "closers fixed" is not claimed. Geometry alone mainly helped stalkers.
87. **Code findings accepted:** drive thresholds 0.8 / 0.85 / 0.97 are hard-coded and don't follow the turn layout;
    wide-ground cost uses the first turn's length for every turn (should use each turn's own arc; a semicircle adds π·y
    for an offset y regardless of radius); `route` can angle out and then tuck straight back in, so its null result isn't
    conclusive; there is no dedicated inside passing lane in race2 (venue feature to add separately).
88. **Plan (Astra):** (1) geometry isolation: old/new layout × three/five wide at fixed gaps and move points, reporting
    paired subject times, extra ground, boxed time and energy; (2) per-venue geometry (circumference, turns, straights,
    finish offset, width, passing lane), with provisional synthetic defaults ≈1,000 ft turn-exit-to-wire on a mile and
    ≈500 ft on a half, sensitivity 660–1,200 / 400–660 ft, to be replaced by real venue specs; (3) a pocket diagnostic
    (shelter on/off × exit open/blocked) before tuning stalkers; (4) continuous lateral motion with swept-footprint
    collisions — an acceptance blocker for any fit; (5) then a first-stage fit freeing only desired gaps, move points,
    lead_soft/lead_dig and break_k (break_k calibrated on break metrics), with geometry, collisions, acceleration,
    fatigue, costs and trait-speed coefficients fixed; style balance a soft target across field compositions and venues.

## Profile positioning (Patrick, 2026-10-31: position from stats, not a fixed style label)

89. **Built:** `race2.plan_race` (P `profile=1`). Each horse's lead decision, sitting gap and move point come from its
    early speed rank in the field, its late-minus-early speed and its stamina; the style label is only a report tag.
90. **M (profile_assay, long stretch five wide, tank 45, same random fields):**
    | | speed / balanced / finisher wins (starters ≈33% each) | leader at 3/4 wins | best-rated wins |
    |---|---|---|---|
    | fixed labels (gap_late 3), 600 races | 27 / 32 / 41% | 25% | 19% |
    | profile, gap_per_rank 1.0, 600 races | 45 / 38 / 17% | 41% | 25% |
    | profile, gap_per_rank 0.5, 300 races | 31 / 37 / 32% | 20% | 17% |
    | profile, 0.5 + move_base 0.58, 300 | 27 / 45 / 28% | 17% | 15% |
    | profile, 0.35 + gap_finish 0.5 + move 0.58, 300 | 19 / 43 / 38% | 14% | 16% |
    Under fixed labels a finisher stuck as a "front" runner still wins on its stats; profile mode sends it back.
    gap_per_rank sets the trade: 1.0 favours speed and the best horse; 0.5 balances the three profiles.
    (300-race rows: ±3 points.)
91. **H12:** across every setting the best-rated horse wins only 15–25% of 8-horse fields (chance is 12.5%), so trip
    and traffic outweigh ability. How often the best horse should win is a player-experience choice, not a fit: ask
    Patrick with a measured menu once the review agrees the measurement is sound.

## Review 9 (Astra, reviews/09_*.md)

92. **Accepted and fixed in plan_race:** the "stalk" label still raised the opening speed (label leaked into behavior;
    profile mode now ignores it); tied early speed made every tied horse lead (ties now go to the inside post, at most
    two go for the lead); a "don't leave" instruction didn't reach the gap or label (fixed); better late speed made a
    horse sit further back and move later (late speed no longer enters the plan); gap is now proportional to the early
    speed shortfall from the quickest (gap_per_speed 5), not rank. Self-checks for all four are in ability_probe.py.
    Items 90's claims "gap_per_rank 1.0 favors the best horse" and H12's cause are **withdrawn** (rate() is not the
    engine's true favorite; fields are deliberately close at SD 0.4).
93. **M (ability_probe, 20 fields × 8 subjects, breaks off, DT 1/16, deterministic):** +0.5 late speed: faster in 89% of
    runs, +0.11 s, +0.49 places; frozen and replanned are identical (planner ignores late speed by design).
    +0.5 early speed: **slower in 37% of runs with plans frozen** (+0.08 s mean), 39% replanned (+0.06 s, +0.30 places).
    By the predeclared reading this is a physics problem, not a planner one: more early speed hurts a third of horses.
94. **M (profile_assay after the fixes, 600 races):** speed / balanced / finisher wins 24 / 36 / 41%; leader at 3/4 wins
    22%; winner 6th or worse at 3/4 in 30%. Consistent with item 93's early-speed penalty.
    **Next:** trace where early speed costs a horse (opening target `CRUISE + 0.8·early` burns energy; leaving-lane
    width; acceleration), fix that, rerun ability_probe until every trait helps in ≥ 85% of runs.

## Early-speed penalty (item 94 follow-up)

95. **M (early_diag, plans frozen, subject alone = ghost + clear path):** +0.5 early speed made a sitter slower in 56%
    of runs even with no traffic, with less energy at the wire. Cause 1: effort cost is measured over a fixed cruise,
    so a quicker horse pays the same at the same pace and pays more for its quicker opening. Added `ease_early`
    (ft/s of pace per point of early speed that costs nothing extra; 0 = old rule).
96. **M:** with ease_early 0.8, a sitter alone was still slower in 19%: its quicker opening (`CRUISE + 0.8·early`) put it
    alongside rivals so it couldn't tuck in (+5 ft of ground). Added `open_early` (0.8 = old rule); 0 lets the gap plan
    place sitters. ease 0.8 + open 0: sitter alone slower 10%, leaver 4%.
97. **M (ability_probe, ease 0.8, open 0):** late +0.5: faster 96%, +0.12 s. Early +0.5 frozen: worse place 10%, +0.33 s;
    replanned: worse place 19%, +1.17 places (becomes leader in 65/160; of the sitters that now sit closer, 24% finish
    worse, 8 of 17 through boxing). ease 0.4 + open 0: early frozen slower 18% (fails monotonicity).
98. **M (profile_assay, ease 0.8, open 0, 600 races):** speed / balanced / finisher wins 46 / 31 / 24%; leader at 3/4
    wins 28%; best-rated wins 32%; late-plan horses 4% of wins from 22% of starts.
    **H13:** monotonicity is now close (frozen 90%), but a point of early speed is worth ≈3× a point of late speed in
    time, so the balance has tipped to speed. Trait weights are a fit/design question, not a monotonicity fix.

## Review 10 (Astra, reviews/10_*.md)

99. **Accepted:** ghost + clear path is "collision-disabled", not alone (still tracks the leader, checks rivals when
    tucking, gets shelter); "faster" and "not a worse place" are different metrics; the ≥85% gate is withdrawn;
    deterministic reversals are interaction sensitivity, not variance; `ease_early` also lowers break pressure (it
    feeds `over`). `open_early 0` kept as a driver-policy candidate; `ease_early` experimental. Trait weights not
    rebalanced before lateral motion and the held-out fit.
100. **M (solo_pace: one horse, fixed pace on the rail to the 3/4 then drive, DT 1/32, best over a 46.7–53.5 ft/s menu):**
    | +0.5 in | old rule | ease_early 0.8 |
    |---|---|---|
    | early speed | 0.07 s | 0.68 s |
    | late speed | 0.16 s | 0.16 s |
    | stamina | 0.34 s | 0.34 s |
    Under the old rule early speed is physically worth little; its value is position, so item 93's penalty was the
    driver spending it badly, not the horse. ease_early turns early speed into the strongest trait by giving it
    stamina's job. **Asking Patrick** what early speed should mean (it changes what players' horses are worth).

## The aim-scoring driver (Patrick, 2026-10-31: decisions 1B 2B 3B+event checks 4B+take-a-better-aim 5B 6B 7B 8B 9B+free summaries 10B)

101. **Free summaries collected:** `chart_targets.md`, with sources and a strength rating per figure. Provisional bands
    for 8-horse fields: mile post 1 about 15–20% and post 8 about 6–10%; half-mile post 1 about 19–27% and post 8 about
    1–6%. Not found free: the leader at the 3/4 win rate, and pocket or parked win rates.
102. **Built (race2, P `driver=1`):** five aims: top, pocket, first-over, follow, close. Each aim sets go-for-the-lead,
    a sitting gap, a move point and follow. `drive_plan` scores every aim and makes three best-response passes,
    quickest first, counting rivals with the same aim, so a crowded top sends the horse with less to gain elsewhere.
    `drive_check` runs every sixteenth and on events:
    - cover going by outside (follow, close);
    - over the spend limit for the top, or parked without cover;
    - a hole inside a parked horse.

    A switch needs a margin of 0.75 lengths and then holds 6 s. Trip notes go into `rec["trips"]`.
    The scores come from the engine itself (`drive_fit.py`): least squares of lengths behind the winner on the
    horse's bars, its post, the field's speed and crowding, fitted only on horses given a random aim (30% after
    round 0), pooled over driver rounds. Without pooling, the coefficients swung between rounds.
103. **M (v1, no crowding):** every driver scored the top best; 52% yielded it and 35% sat back to close. First-over
    and follow were never picked. Crowding raised r² for top and pocket from about 0.3 to 0.43 and 0.37.
104. **M (v2, model round 4, 600 races):**
    - Gate aims: top 26%, yielded 29%, close 30%, pocket 15%; follow 0% and first-over 0%.
    - Winners' aim at the wire: pocket 47%, top 34%, close 20%.
    - Wins by post: post 1 43%, 2 28%, 3 10%, 8 1.8%. Far steeper than the mile band, and steeper than a half-mile.
    - The winner was within 2 lengths at the half in 65% of races; the leader at the 3/4 won 29%.
    - Profiles won speed 26%, balanced 34%, finisher 40%.
    - Ability (20 fields × 8 subjects, place change, clustered by field):
      - late +0.5: +0.28 places frozen, +0.25 replanned, 5–7% finish worse;
      - stamina +0.5: +0.74 frozen, +0.72 replanned, 9–11% finish worse;
      - early +0.5: +0.13 frozen (±0.15), **−0.48 replanned** (±0.18), 46% finish worse.

    **Read:** the driver now penalizes early speed, and it over-rewards the inside posts. **H14:** a linear,
    field-averaged score with r² 0.13–0.43 is too blunt to choose trips. It sends a quicker horse into contested
    spots, and it hands the pocket to posts 1–2.

## Review 11 (Astra, reviews/11_*.md)

105. **Accepted:**
    - Training doesn't match deployment: forced-aim rows switch only on events, while deployed drivers also re-score.
    - Mid-race scoring reuses the pre-race scores instead of valuing the current state.
    - `start_aim` "frozen" isn't frozen: best-response passes still run for the rivals.
    - Crowding is partly an outcome of the randomized aim.
    - Lengths behind is not a win or place utility.
    - Quickest-first passes depend on order.

    Low r² alone doesn't condemn a linear score; use held-out action regret instead.
    The benchmark is corrected: Rideau-Carleton is a five-eighths-mile oval, and its column is wins per start. Its
    figures are now soft targets.
    **Replacement agreed in principle:** feasibility checks plus a small state-action value model, fitted on paired
    counterfactual continuations (clone a state, try each feasible aim, same opponents and continuation rules), with
    mid-race scoring from the current snapshot.
106. **M (post_rotation: 20 fields × 8 cyclic post rotations, breaks off, DT 1/16):**
    - Each horse on one fixed aim: posts 1–4 won 22–27% each and posts 5–8 won 0.6–2.5%. Outside posts carried
      35–39 ft of extra ground. They reached the first turn still five to eight wide, because nobody gave way and the
      tuck rule needs a clear length inside.
    - **The engine is the main cause.** Added `tuck_back`: a non-leaver eases off early when the lane inside is
      taken, so it drops in behind. Default 0 keeps the old rule.
    - Fixed-aim wins by post, posts 1–8:
      - tuck_back 2: 17.5, 8.8, 6.9, 16.2, 19.4, 15.0, 8.8, 7.5%;
      - tuck_back 4: 21.9, 18.8, 8.8, 11.2, 13.8, 14.4, 8.1, 3.1%.

      With 160 races per arm, each post's figure is good to about ±3 points.
    - With tuck_back 4, the learned driver still gives posts 1–2 78% of the wins (48 + 30). That is driver
      amplification: its model was fitted before tuck_back, and it leans on post and the pocket.
107. **Next:** tuck_back 4 as the engine candidate. Then the counterfactual aim experiment (20 fields × 8 subjects × 5
    opening aims, opponents on one declared policy) to see whether first-over and follow ever help. Then build the
    snapshot value model and refit.
108. **Patrick:** the live game's half-mile post curve (18.6% from the rail down to 5.9% from post 8) is the closest to
    real racing. It is now the lab's half-mile target (chart_targets.md). The lab hasn't yet been run on the half-mile
    layout, and the mile target stays open.

## The value-model driver (review 11's replacement)

109. **Built:**
    - Per-track layouts in race2. Lab half-mile settings:
      - turns (0.03–0.155), (0.28–0.405), (0.53–0.655), (0.78–0.905);
      - the stretch fans out at 0.905;
      - a rail horse angles out at 0.88;
      - from the start to the first turn is about 160 ft.
    - Saved race states carry their clock, so they can be continued.
    - `aim_state` is what a driver sees: the horse's bars and post, then where it is now (share of the mile, lane,
      lengths off the lead, place in the order), what it has left in the tank, the speed it's up against, the
      leader's tank, cover outside and boxed.
    - `feasible`: the top only from the gate or within 1.5 lengths; the pocket only from the gate or within 3 lengths
      and no wider than the second lane.
    - `aim_values`: a ridge model per aim on quadratic terms of state plus crowding. It predicts finish place, and
      prediction is plain Python (no libraries on the server).
    - The value model is used at the gate (best-response passes) and at every check: a switch needs a 0.3-place
      margin, then the 6 s hold.
    - Data: `value_fit.py` saves states at the gate, 0.2, 0.35, 0.5 and 0.62, and continues each one with every
      feasible aim for one subject. Everyone else stays on the same policy and the same random draws.
      - Round 0: 4,800 states under the linear driver.
      - Round 1: 4,800 under value_0. Pooled.
110. **M (review 11's test, all states):**
    | Aim | Best or tied best | Wins | States tried |
    |---|---|---|---|
    | Top | 66% | 29% | 2,024 |
    | Pocket | 54% | 32% | 2,185 |
    | First-over | 55% | 13% | 4,800 |
    | Follow | 55% | 11% | 4,800 |
    | Close | 45% | 6% | 4,800 |

    First-over and follow do help, so the old scorer was at fault, not how those aims run.
    Held-out regret (places lost against the best arm), by state:
    - value_0: 0.57 (random aim 1.23);
    - value_1 pooled: 0.70 (random aim 1.16);
    - ridge strength makes no difference;
    - a tree ensemble, as a headroom check only: 0.60.

    Ridge kept for portability.
111. **M (value_1, tuck_back 4, 600 races per track, DT 1/8):**
    - **Mile:**
      - gate aims: top 31%, first-over 29%, close 20%, pocket 13%, follow 7%;
      - winners' last aim: first-over 34%, follow 28%, pocket 25%, top 8%, close 6%;
      - profiles won speed 29%, balanced 36%, finisher 36%;
      - posts 1–8: 19.7, 27.3, 14.5, 12.0, 9.8, 7.5, 5.8, 3.3;
      - the leader at the 3/4 won 23%, and the winner was within 2 lengths at the half in 54%;
      - post rotation with the driver: 23, 23, 15, 11, 10, 9, 4, 6 (fixed aims: 22, 19, 9, 11, 14, 14, 8, 3).
    - **Half:**
      - the post 1 horse led at the half in 86% of races;
      - posts 1–8: 52.3, 13.2, 8.5, 14.3, 3.3, 5.2, 2.3, 0.8 (target 18.6 down to 5.9);
      - fixed-aim rotation: 26, 21, 11, 2, 7, 9, 12, 12 (erratic).

      The half-mile layout is wrong: about 160 ft from the start to the first turn, and the rail horse holds the
      lead.
    - **Ability, place change, ±se clustered by field:**
      | | early frozen | early replanned | late frozen | late replanned | stamina frozen | stamina replanned |
      |---|---|---|---|---|---|---|
      | Mile | +0.04 ±0.10 | +0.16 ±0.14 | +0.38 | +0.46 | +0.55 | +0.71 |
      | Half | +0.21 | +0.39 | +0.46 | +0.31 | +0.51 | +0.38 |

      Every mean is now positive, but on the mile about 41% of early-speed runs finish worse, against 44% better.
    - **Plan changes per horse (mile):** 3 or more in 52% of horses. Likely too twitchy for the replay.
    - **Runtime:** 270 ms per race. A 300-race night takes about 80 s.

## Review 12 (Astra, reviews/12_*.md)

112. **Accepted:**
    - The half-mile layout is consistent. A 160 ft run to the first turn can be legitimate. Fixed-aim rail wins were
      26%, against 52% with the driver, so the driver amplifies the rail edge as well as the geometry causing it.
    - "3+ plan changes" was counted from trip notes, so it includes "followed cover". The count needs real
      old → new aim logs.
    - Decisions read horses that have already moved this step. Spend-limit switches skip hysteresis.
    - `parked_e` and `spent0` never reset per attempt, so a driver can re-enter a tactic it has already exhausted.
    - Feasibility can drop the current aim, which loses its switching margin.
    - The model lacks decision history: current aim, hold time left, spend so far.
    - Regret is hindsight regret against one seed. It should be expected-action regret over about 20 seeds per arm on
      untouched states, with a seed split.
    - "55% best" counts ties, so strict wins should be reported instead. Models should be compared on one fixed bank.
    - The mile curve's post 2 coming in above post 1 needs explaining.
    - Weak early speed may be the controller giving back position it gained. The test is a fixed schedule against
      adaptive driving, recording first-turn position, energy spent getting there, ground, time and place.

    Rejected nothing. Continuous lateral motion, swept collisions and DT validation are still acceptance blockers.
113. **Plan (in order):**
    1. Half-mile synthetic default: 800 ft straights, 520 ft arcs, a 500 ft stretch, a 300 ft run to the first
       turn. Sensitivity runs at 200, 300 and 400 ft.
    2. A one-snapshot decision step, attempt budgets, an aim-change log, and the decision-history features.
    3. The early-speed fixed-against-adaptive test.
    4. The expected-regret bench (20 states × aims × 20 seeds).
    5. Refit the model on the new geometry.
    6. A 10-season integration smoke test with versions frozen, its conclusions labeled provisional.

## Engine v3 (Patrick, 2026-11-01)

114. **Decided:** rebuild the race engine from the ground up, targets first. The stats players see are a presentation
    layer over hidden traits with one job each. race2 patching stops; its tests become the acceptance suite. The draft
    spec with questions for Patrick is in `ENGINE_SPEC_DRAFT.md` (25 items).
    The last race2 run (gate rollouts, 2 and 3 passes) is kept as a cost reference for a planning driver.
115. **M (race2 gate rollouts, value_2, 100 races per arm):**
    | Passes | Track | Posts 1–8 |
    |---|---|---|
    | 2 | mile | 33, 23, 14, 7, 10, 4, 5, 4 |
    | 2 | half | 38, 23, 9, 11, 6, 7, 3, 3 |
    | 3 | mile | 20, 21, 14, 17, 15, 3, 7, 3 |
    | 3 | half | 35, 24, 18, 6, 6, 3, 4, 4 |

    Gate aims stay spread (top about 34%), but the rail bias on the half-mile remains. The planner alone doesn't fix
    it in race2. Cost was 14 s per race for 2 passes and 20 s for 3, measured with 16 processes sharing the CPU; about
    4–7 s alone is likely. That is the cost reference for a planning driver in v3. ±5 points per post at n = 100.
116. **Patrick:** the engine races the actual horses under race-like behavior rules. The results in Part 1 are checks,
    never controls: a failed check is fixed in behavior, never by a bonus or a penalty. Part 0 of the spec (24
    behavior rules, the faults already seen marked) was added for Patrick to mark up.
117. **Patrick:** took every ★ pick in the spec and kept Part 0 as written. `ENGINE_SPEC.md` is the requirement; the
    draft stays for the record.
118. **Review 13 (Astra, fresh thread; design review before the build):** every point is accepted and folded into
    DESIGN_V3 §11. The headline: the half-mile reference is wins per start over fields of varying size (it sums to
    88.9%), so the engine is scored against the live save's field-size mix and the curve is not normalized.
    The other blockers:
    - collision safety as a hard invariant, with joint swept resolution and no reversals;
    - an admissibility layer for rules 0.4, 0.6, 0.8 and 0.21;
    - power-balance physics, with grit discounting only the extra cost of a duel;
    - a state-machine driver with per-opportunity cooldowns;
    - staged fitting, and contracts frozen before tuning;
    - replay and audit moved into the first build step.

    The repeat-winner target (45%) and the best-horse target (30%) must be checked as jointly feasible.

## Engine v3 build, steps 1–2

119. **Built `race3.py`:**
    - Real track geometry:
      - half-mile: 800 ft straights, 520 ft arcs, R 166, 300 ft run-in, 500 ft stretch;
      - mile: 1,320 ft straights and arcs, R 420, 1,000 ft stretch.
    - Continuous lateral position `y`; physical speed with `ds = v·dt/(1 + y/R)`.
    - Bodies 14 × 5 ft.
    - The safe-following invariant: braking at 10 ft/s² beats a horse ahead breaking at 6 ft/s².
    - Lateral moves resolved together with swept checks, including room for the horse behind. A blocked change
      pauses; it never reverses.
    - A power balance:
      - locomotion, plus air cut 50% in cover, plus acceleration, plus a duel's extra (grit discounts only that);
      - cruise sets sustainable power, and the reserve is 12 sustainable-power seconds with gradual recovery;
      - the ceiling fades smoothly with the reserve (sqrt), with the gate's launch burst fading out over 700 ft;
      - break hazard `1 − e^(−λΔt)` from body edges, a factor log for each break, and its own random stream for
        each horse.
    - Every step recorded. `audit()` reads only the record: overlaps, sideways snaps, reversals, four-wide on a turn,
      stopping dead, safety violations.
    - `to_xy` for the oval, and a lab viewer (`v3_view.py`, then `v3/gate_test_half.html`).
120. **M (v3_mechanics):**
    - **Lone average horse at sustainable pace:** 1:53.5.
    - **Matched pace 47.5 ft/s to the 3/4:**
      | Trip | Reserve used | Time to the 3/4 |
      |---|---|---|
      | Rail, alone | 2.76 | 83.75 s |
      | Outside, no cover | 2.79 | 84.62 s (the ground) |
      | Behind a horse | 0.00 | 83.75 s |
    - **Eight abreast on the half-mile:** zero overlaps and zero safety violations, min gap 1.5 ft, no snaps, at most
      1 reversal.
    - **Lateral speed:** at 2.5 ft/s the outside posts were still 4–6 wide entering the first turn. Raised to
      4 ft/s (a lane in about 2 s), giving posts 6–8 at 3.8 / 4.6 / 5.3 lanes.
    - **H15 (geometry, not tuning):** from post 8 a horse would have to move 35 ft sideways in about 6.5 s to be no
      wider than three at the first turn. Rule 0.6 can't hold on a 300 ft run-in.
      The auditor now counts "four-wide while still working in from the gate" separately (58 steps here). Patrick is
      asked to approve that exception in the wording.
    - Moves paused 5,076 times in one race: the safety layer is working hard at the gate. To watch.
121. **Patrick:** rule 0.6 allows four-wide on the first turn only while a horse is still working in from an outside
    post. The auditor counts that case separately; any other four-wide turn trip still fails.

## Engine v3 build, step 3 (driver v0, `drive3.py`)

122. **Built:**
    - Gate plan: a rule score for each aim (gate shortfall, post, cruise, kick, crowding, track), three
      best-response passes, everyone answering the same picture.
    - An event-gated state machine. Its events:
      - a failed bid for the top (over its leave budget), which closes the top for 12 s;
      - parked too long, where parking is costed as the air a covered horse wouldn't pay;
      - cover going by;
      - a hole inside a parked horse, after the first turn only.
    - A 4 s commitment, with safety exits.
    - Controllers:
      - the start: outside horses ease back to slide in, and closers ease more;
      - the lead: a breather in the second quarter, and digs in when pressed;
      - sitting: a tight line half a length clear, easing to slot in behind;
      - moving: a committed outside line, back in when nothing is gained outside, and the pocket waits for the
        stretch.
    - Every change is logged with its reason, and trip notes go in `rec["trips"]`.
123. **Bugs fixed on the way (all measured):**
    - The safe-gap formula let a follower close up and overlap. Now one braking limit (8 ft/s²) applies to everyone,
      and the gap is HEAD + v·T + max(0, Δv²/2B).
    - A leader with no plan for leading braked itself to a standstill and went backwards. Speed is now floored at 0,
      and the lone leader sets a fair pace.
    - Side clearance differed between checks; there is now one `Y_PAD`.
    - The lane-change check treated horses already ahead and behind in the same lane as new conflicts, so a tight
      line froze every move out.
    - Breaks ran at 10× too many (96% of races). The base rate is cut 10× to about 32% of races having one break,
      against roughly 28% for the 4%-of-starters target.
    - Sitters kept their aim's distance from the horse in front, which strung the field out. The line is now tight.
124. **M (200 random races per track, untuned):**
    | Check | Half-mile | Mile |
    |---|---|---|
    | Overlaps | 0 | 0 |
    | Safety breaches | 397 | 57 |
    | Four-wide-on-turn steps | 8,036 | 24,524 |
    | Unfinished races | 0 | 6 |
    | Posts 1–8 | 87, 5.5, 4.5, 2, 1, 0, 0, 0 | 66, 14, 8.5, 4.5, 4, 1.5, 1.5, 0 |
    | Best horse on paper wins | 12.5% | 17.5% |
    | Mean winning time | 1:51.5 | 1:45.4 (too fast) |

    Gate aims: follow 62–71%, first-over 20–27%, top 7–8%. The traced race (viewer `v3/first_driver_race_half.html`)
    shows a real first-over move, cover followed, and a pocket horse coming back on the rail.
    **Next (stage 3–4, before any Part 1 fitting):**
    1. Turn admissibility for movers: no third or fourth lane on a turn without a recorded reason.
    2. Find the 6 stuck mile races.
    3. Find the safety breaches.
    4. Calibrate the single-horse clocks to the tier times, before any tactics tuning.
    5. Then tactical competence: the inside bias is the first thing to explain.
125. **Clean-up (measured):**
    - Movers are capped at three-wide on and just before turns, and work back in. Four-wide-on-turn steps fell from
      8,036 to about 75 (half) and from 24,524 to about 150 (mile).
    - The drive starts 1,400 ft out on both tracks. The mile's had started 2,460 ft out.
    - **Deadlock:** the six stuck mile races were a rail horse tracking an outside rival's speed while that rival
      eased to drop in behind it, until the whole field stopped. Sitters now track only a horse in their own line,
      never below 0.8 of their steady pace.
    - **Safety:** following now checks every body ahead in the band, not just the nearest. Lane changes leave a
      look-ahead margin (±2 ft/s). With breaks off, breaches fell from about 1 per race to 4 in 30 half-mile races,
      with no overlaps.
    - **Bug:** the reserve could go negative. It is now floored at 0, where a horse is held to its sustainable pace.
126. **M (stage 3 clock fit, 40 races per point):** `pace_k` 1.02 and `c_turn` 0.0007, a new cost of holding a curve,
    in proportion to v·v²/(R + y). Median winners: mile 1:53.6 (live 1:53.4), half 1:56.1 (live 1:55.9). A lone
    average horse runs 1:54.5 on the mile.
127. **M (tactics, 200 races per track per setting):**
    - **Root cause of the inside bias:** the post 1 horse led at the half in 99.5–100% of races. Leavers couldn't
      clear and cross in 300 ft, the rail horse never gave way, and leavers sprinted flat out for a quarter mile.
    - **Fixes (all driver habits):**
      - non-leavers yield to a leaver crossing in front, through the first quarter;
      - a leaver brushes at its steady pace + 5 ft/s until clear, then settles;
      - `s_top` 4, so about 20% of starters go for the top.
    - **Results with the fixes:**
      | | Half-mile | Mile |
      |---|---|---|
      | Posts 1–8 | 30, 24, 11, 10, 7, 9, 6, 3 | 46, 20, 8, 11, 4, 6, 2, 3 |
      | Leader at the half from post 1 | 35% | 24% |
      | Best horse on paper wins (target 30%) | 27% | 22% |
      | The horse on the lead at the 3/4 wins | 91% (target ~35%) | 45% |
    - **Open:** leaders win far too often on the half-mile, and post 1 too often on the mile. On the mile, post 1
      mostly wins from a pocket or rail trip that reached the drive with a full tank.

## Review 14 (Astra, reviews/14_*.md)

128. **Accepted:**
    - **Turn cost:** on the half-mile rail it is about 0.43 sustainable-power units, roughly 3× what drafting saves
      (0.15).
    - **First-over timing:** first-over goes flat out from 2,904 ft, right into the third turn. The leader drives
      only from 3,880 ft.
    - **Empty reserve:** at E = 0 the ceiling ignores the turn, the draft and the duel, so the floor is inconsistent.
    - **Passing room:** a lane change needs about 32 ft clear at 50 ft/s, against about 6 ft for following.
    - **Driver:** it mixes up "move out", "leave cover" and "spend everything". The drive starts from each horse's own
      progress, not from the field. Following cover ends at the last turn.
    - **Correctness defects, which block attribution:**
      - Driver state is mutated mid-loop, and ties are broken by input order.
      - Safety still applies braking beyond the limit after logging it, so "zero overlaps" can be bought illegally.
      - The swept lateral check is not a full swept-body check in consistent geometry.
      - There is no committed lane-change state, and a pause stops `vy` instantly.
      - The start controller runs through the whole first turn (820 / 1,640 ft).
      - "Couldn't clear" is budget-based, not based on turn feasibility.
      - The sixteenth recheck isn't implemented.
      - `park_e` uses `R.DT`.
      - Traffic break pressure is unreachable at a legal headway.
      - Finishers vanish from the physics.
      - The auditor's gate exception is too loose.
      - `plan()` crashes on a one-horse field.

    **Narrowed:**
    - Leader-at-the-3/4 is not the trip metric; a trajectory-based trip classifier gets frozen.
    - The half-mile curve isn't "close" yet (30/24 against 18.6/14.9), and the field-size mix contract still
      applies.
    - The bias fix was a bundle of changes, not an isolated cause.
    - The clocks match pooled medians only, not the tier clocks.
    - Breaks get measured per starter.
129. **Plan, in order:**
    1. Freeze the build: parameters, seeds and code version saved with every report.
    2. Fix the correctness defects:
       - one snapshot for driver state;
       - a lawful braking limit;
       - a committed lane-change state;
       - an empty-reserve workload rule;
       - the timestep (`park_e`);
       - finishers kept in the physics;
       - the auditor's gate exception;
       - turn-feasibility gate sorting;
       - the sixteenth recheck.
    3. Run order, tie and DT 1/8, 1/16, 1/32 tests.
    4. Run trait-upgrade tests: frozen against adaptive, plus manners with breaks on.
    5. Run the mechanism assays from saved pre-drive states:
       - turn cost × commitment point;
       - access only (route held, exposure fixed);
       - drive activation and a pace menu;
       - shelter × exit;
       - the recovery budget.
    6. Revalidate the tier clocks.
    7. Only then tune tactics against Part 1.

## Review 14 fixes, first pass

130. **Engine (race3):**
    - The braking limit is now lawful: a breach is logged and the horse brakes at no more than 8 ft/s², so a breach
      can no longer be hidden.
    - Following works in rail-coordinate rates (v·k).
    - Lane changes are committed:
      - they start one lane at a time, and only if the whole path is clear;
      - each step checks its sweep plus the stopping distance;
      - a pause eases off rather than stopping dead, and a change waiting 3 s is abandoned to the nearest lane;
      - it lands on the line with no overshoot;
      - a change under way claims its new lane, so the horse behind eases off early;
      - the gap must still hold when the horse is across.
    - The drive start and the slot finder use one shared `merge_gap` rule.
    - An empty tank holds the horse to the steady speed it can hold right there (`held_speed`: turn, cover, duel).
      Acceleration is limited to what's in the tank, and overspending is logged.
    - Finishers stay on the track 400 ft past the wire.
    - Break pressure counts being on another horse's tail (within need + 2 ft) and being boxed in, each break
      recording its causes.
    - The auditor's gate exception now applies only to horses from outside posts that are moving in.
131. **Driver (drive3):**
    - One snapshot of every driver's phase per step; ties go to the horse nearer the rail.
    - The start controller runs only to the first turn. At the turn, a leaver that hasn't cleared takes back.
    - The drive starts when the leader reaches 1,400 ft out (a field event).
    - A positional move phase: first-over advances on the leader at +2 ft/s, then presses on its flank, and followers
      stay on cover until the drive.
    - The sixteenth look: if nobody has moved by 0.55–0.7, a fresh horse goes first-over; a pocket horse that isn't
      in the pocket sits in the line instead.
    - Line hysteresis: a new line holds 4 s.
    - `slot()`: a horse outside the line paces itself to a real gap in the lane inside.
    - `park_e` uses the run's dt; `plan()` no longer crashes on a one-horse field.
132. **M (12 races, 6 per track):**
    | Check | Half-mile | Mile |
    |---|---|---|
    | Overlaps | 0 | 0 |
    | Most line reversals by one horse | 4 (was 221) | 6 |
    | Lateral breaches | 24 | 50 |
    | Safety breaches (now honest) | 125 | 46 |
    | Four-wide-on-turn steps | 597 | 1,089 |
    | Changes abandoned | 340 | 325 |
    | Winning time | 2:00.5 | 1:54.8 |

    **Read:** the trade-off is between merging and passing on one side and breaches on the other. Raising the
    margin removes the breaches and passing with them. Per-horse admission rules (who may move) can't settle it.
    **H16:** merging has to be cooperative and resolved jointly. The horse in the destination lane yields when a
    lawful merge starts (it "lets him in"); a merge is claimed and granted as a pair. A design question for Astra
    before more patching.
    **Not done yet:** order, tie and DT tests; trait-upgrade tests; mechanism assays; re-fitting the clocks (the
    empty-tank rule slowed the half-mile by about 4.5 s).
133. **Review 15 (Astra; merge design):** the pair protocol is rejected as a safety invariant. Safety is needed from
    first lateral overlap (about 1.7 ft, roughly 0.9 s), not from completion. B can't be exempt from the checks, and
    expiring a reservation can reverse a move.
    The clear-by in the draft was miscounted: 20 ft is 2.5 lengths, and the rule should depend on relative speed.
    "Costs no more than one position" is no yield rule.
    **Adopted:** MERGE_DESIGN v2: prepare, then reserve, as a state machine. Cooperation comes later, as a driver
    choice. A gate-sorting planner is separate from the merge layer. The cooldown applies to each opportunity.
    Acceptance gates are zero-tolerance, with progress controls. Five code defects are listed.

## MERGE_DESIGN v2 built (review 15)

134. **Built (race3):**
    - **Lane changes:** asked for one lane at a time, then committed only when every horse sharing the new lane is
      already in a safe following order (nobody alongside). The check is `commit_ok`:
      - it measures on the widest line the change involves;
      - width limits only moves outward;
      - in the stretch, an inward move can't make a rival brake.
    - **A committed change:**
      - reserves both lanes (`occ`): from that moment every horse in either lane follows the mover, and the mover
        follows both;
      - moves with bounded sideways acceleration and lands on the line;
      - can't be redirected or abandoned;
      - the oldest request is looked at first, with no rail or post priority.
    - **Forward pass:** who follows whom comes from one snapshot. Gaps are measured in real feet along the line of
      the horse being followed (`track.path`), at physical speeds. A breach is a hard failure. The following gap
      carries a 0.5 ft step allowance for braking chains.
    - **Other fixes:**
      - the `held_speed` cache key (False collided with 0.0);
      - turn-entry rates are refreshed after each horse moves;
      - break drift was dropped (a breaking horse holds its line);
      - the gate exception covers outside posts until they're in;
      - the start's drop-back is 5 ft/s under the horse inside.
135. **M (`v3_merge_tests.py`, scripted, zero tolerance):** all 9 cases pass, with no overlaps, braking breaches or
    snaps:
    1. passing into an empty lane;
    2. an adequate gap, with no yielding;
    3. a boundary sweep from 2 to 38 ft;
    4. breaks mid-merge (F, M or B, at 0.2 / 0.6 / 1.2 / 2.0 s);
    5. a follow chain;
    6. two horses wanting one slot;
    7. an opposite swap;
    8. merges at turn entry and exit;
    9. a pocket blocked, then out.
136. **M (random fields with drive3, 10 per track):**
    - **Mile:** 0 breaches, 0 overlaps, 0 four-wide-on-turn steps.
    - **Half-mile:** 0 overlaps, about 4.5 marginal breaches per race (each about 0.01–0.1 ft/s past the braking
      limit), and about 10 four-wide steps per race.
    - **Tried and rejected, all measured:**
      - measuring on the widest line: case 4 failed;
      - a curvature allowance that switches on at turn entry: 211 breaches;
      - measuring on the follower's line or the leader's line: about the same.

    **H17:** the remaining half-mile breaches come from rail-coordinate gaps on the 166 ft radius turns while
    horses change lanes, plus braking chains. The cleaner fix is following on the physical track geometry rather than
    the rail coordinate. To decide next.

## Following on the real track shape (H17)

137. **Built (race3 `follow`):**
    - Gaps are real feet along the innermost line the follower holds or is committed to. That line stays put through
      an inward lane change, so the measure never slides. Moving in on a turn really gains ground, and committing to
      the inner line counts that gain from the moment of the commit.
    - A wider horse ahead covers less rail on a turn, so its speed is taken in the follower's frame. This is phased in
      over the 100 ft before a turn (`turn_weight`), so it never jumps. A horse moving out is judged on the line it's
      heading for.
    - **The commit check uses the same rule, and re-judges:**
      - horses ahead in the mover's own lane, on the new line;
      - for outward moves, horses behind in its own lane.
    - Breach tolerance is 0.02 ft/s. A braking chain sitting exactly on the limit gives about 0.001; the real
      squeezes were 0.1 and up.
138. **M:**
    - **Scripted merge suite:** all 9 cases still pass.
    - **40 random races with drive3:**
      | | Half-mile | Mile |
      |---|---|---|
      | Overlaps | 0 | 0 |
      | Braking breaches | 4 | 0 |
      | Snaps / stopping dead | 0 | 0 |
      | Four-wide-on-turn steps outside the gate exception | 85 | 0 |

      Of the 4 half-mile breaches, 3 sit right at the tolerance (0.020–0.024 ft/s). One is 0.35 ft/s in a same-lane
      line entering the last turn in the drive; its cause isn't found yet.
    - **Breaches by version:**
      | Half-mile | Breaches |
      |---|---|
      | Per-horse admission | about 125 per 12 races |
      | Reserved changes | 47 per 20 |
      | Own-lane re-check at commit | 18 per 20 |
      | Outward movers judged on their destination | 4 per 20 |

## Acceptance checks (review 14, items 3–4)

139. **M (order and ties, breaks off, 20 fields per track):**
    - Shuffling the horse list changes the result in 1 of 20 half-mile races (likely float summation order), and
      0 of 20 on the mile.
    - Renaming the horses changes no places.
    - Identical fields rerun identically, 5 of 5.
140. **M (time step, 15 fields per track, breaks off), against DT 1/32:**
    | | DT 1/8, half | DT 1/8, mile | DT 1/16, half | DT 1/16, mile |
    |---|---|---|---|---|
    | Same winner | 93% | 80% | 100% | 100% |
    | All places identical | 85% | 81% | 92% | 96% |
    | Winner's time error | 0.30 s | 0.14 s | 0.06 s | 0.03 s |

    **Read:** DT 1/8 is too coarse for results. Use DT 1/16 for real races, at twice the cost.
141. **M (+0.5 in one trait, 16 fields × 8 subjects; manners with breaks on, 6 seeds):**
    | Trait | Half, gate aims frozen | Half, adaptive | Mile, frozen | Mile, adaptive |
    |---|---|---|---|---|
    | Gate | +0.05 | −0.14 (23% finish worse) | +0.06 | −0.11 (25% worse) |
    | Cruise | +0.72 | +0.68 | +0.52 | +0.53 |
    | Kick | +0.01 | −0.02 | +0.09 | +0.12 |
    | Grit | 0.00 | 0.00 | +0.02 | +0.02 |
    | Manners | +0.01 | +0.01 | +0.02 | +0.02 |

    Places gained; ±se clustered by field is 0.01–0.13.
    **Read:**
    - Cruise (stamina) decides races almost alone.
    - Kick barely matters. **H18:** horses reach the drive with little reserve, and the ceiling fades with the
      square root of the reserve toward the steady pace cruise sets.
    - Gate helps a little with the plan frozen, but the driver turns it into a loss when it re-plans (rule 0.13
      fails), as it did in race2.
    - Grit and manners do almost nothing: duels and breaks are rare.

    This is the stage 3 single-horse capability calibration (DESIGN §11.8), still open. Each trait needs a fair
    share of the race before any trip tuning.
142. **M (single-horse balance, 10 fields × 8 subjects per point, breaks off, DT 1/16, gate aims frozen):**
    - **The drain:** horses reached the drive with a median of 23% of their reserve (2.8 of 12). The cornering cost
      fitted in item 126 (`c_turn` 0.0007) drains everyone through every turn, because pace is set by straight-line
      sustainable speed. A duel lasts 14–16 s per race, but grit's discount is too small to matter.
    - **Grid over `c_turn` 0–0.0004 × `pace_k` 0.94–1.02:**
      - `c_turn` 0 gives a reserve at the drive of about 0.8. At 0.0004 it falls to 0.3–0.6.
      - Lower `pace_k` means faster clocks (1:46–1:48), and kick then counts more: +0.25 places for +0.5.
      - Higher `pace_k` gives clocks nearer the live game, and stamina dominates (+0.6).
      - Gate is worth 0–0.2 everywhere; grit about 0–0.15.
    - The clocks and the trait balance are coupled through the margin between top speed and steady pace, and through
      how long the reserve lasts in the drive. Each figure is good to about ±0.1 places.

    **Read:** every trait can be made to count. The balance between them is the fit target, and what each stat should
    be worth is a player-experience choice. Asking Patrick before fitting.
143. **Patrick (2026-11-01): the stat balance is track-shaped.** Stamina is steady on both tracks. Early speed
    counts most on the half-mile, kick most on the mile. Grit and manners are each worth about a third of the big
    three.
    **Written down before the fit (contract):**
    - Places gained for +0.5 in a stat, 8 starters, gate aims frozen, breaks off, DT 1/16:
      | Stat | Half-mile | Mile |
      |---|---|---|
      | Cruise | 0.35 | 0.35 |
      | Gate | 0.45 | 0.20 |
      | Kick | 0.20 | 0.45 |
      | Grit | 0.12 | 0.12 |

      Tolerance ±0.08 each.
    - Manners: 0.12, measured with breaks on during stage 6.
    - Clocks: mile 1:53.4 and half 1:55.9 median winners, ±0.5 s.
    - The adaptive driver must not reverse any trait's sign (rule 0.13), as a gate.
144. **M (stage 3 fit, first attempt):**
    - **Random search** (`v3_fit.py`): 4 rounds of 8 candidates over 12 settings, 12 fields × 4 subjects per track.
      It stalled at a loss of about 47 after round 1. Best: half gate 0.04, cruise 0.40, kick 0.06, grit 0.19,
      1:56.8; mile gate 0.10, cruise 0.29, kick 0.17, grit 0.13, 1:53.4.
    - **One dial at a time around that best:**
      - `k_kick` 3.5 puts mile kick at 0.35, but the half-mile only reaches 0.10.
      - `p_cruise` moves cruise as expected.
      - Grit responds to `duel` and `k_grit` (0.27–0.29).
      - Gate stays between −0.02 and 0.13 even with `gate_pace` 3 or 6. That new driver habit has a non-leaver use
        its gate to settle further up at the start.
    - **Noise:** with 48 subjects, each figure is good to about ±0.12, enough to swamp the contract's ±0.08.

    **H19:** early position buys little in this engine, because forward placing costs reserve and the trip rules
    don't turn it into a finishing edge. Gate can't be worth 0.45 on a half-mile until position itself is worth
    something. That is the leader/trip question from review 14 again.
145. **Review 16 (Astra, fresh thread; fit strategy):**
    - **The broad fit is stopped. H19 isn't established:** gate buys little *under this controller*. Leavers ask
      for `v_sus + leave_push`, so the burst rarely binds. `gate_pace` is overridden by drop-in and yield rules.
      Everyone starts at 44 ft/s. "Frozen aims" isn't frozen execution.
    - **Cruise also sets `v_sus`, which feeds several of the driver's paces.** And kick lifts the ceiling all race,
      not just in the drive. So the measured values mix capability with the controller.
    - **The ±0.12 is variation between fields, not rerun noise** (breaks off is deterministic). The fix:
      - 64–128 fields per track to screen, 256–512 untouched fields to validate;
      - errors estimated from field-level means;
      - confidence intervals inside each tolerance band.
    - **Order:**
      1. baseline physiology;
      2. gate acquisition;
      3. trait sensitivities;
      4. a joint, constrained refinement with a sensitivity matrix.

      Not `duel` to make grit valuable, not `c_turn` to set the clock gap, and not reserve or fade as compensation
      knobs.
    - **Feasibility:** manners at 0.12 is likely infeasible at a 4% break rate (about 0.04).
    - **Three assays come first:**
      - A: does gate change position (opening acceleration, what binds, clears, places at the first turn and the
        quarter, ground, reserve);
      - B: is position worth anything at equal resources (slot swaps from saved states: lead, pocket, forward and
        rear covered lines, first-over);
      - C: does getting position cost more than it returns.
    - **Rejected:** buying balance through more duels, starving reserves, guaranteed pocket exits, artificial
      traffic, or track-specific bonuses; and declaring success on total loss while one cell fails.
146. **M (assay A, 64 fields × 8 subjects, normal driving):** +0.5 gate does change position:
    | | Half-mile | Mile |
    |---|---|---|
    | Places gained at the first turn | +1.30 | +1.41 |
    | Places gained at the quarter | +1.12 | +1.34 |
    | Reserve given up by the quarter | 0.54 of 12 | 0.49 of 12 |
    | Places gained at the wire | −0.10 | −0.13 |

    Horses that cleared for the lead rose from 12% to 42–43%; the commonest aim change was follow → top. Time
    bound by acceleration in the first 700 ft fell from 4.0 to 2.9 s. The gain at the quarter grows with post: 0.4
    from post 1, about 2 from posts 7–8.
    **Read:** gate gets position. The position is lost later.
147. **M (assay B, 63–64 saved states per track at the quarter):** two identical horses (mean traits, mean reserve)
    in two spots on the rail line, raced on. The forward spot is worth:
    | Pair | Half-mile | Mile |
    |---|---|---|
    | 2nd vs last on the rail | +5.0 | +5.8 |
    | 3rd vs 5th | +1.5 | +2.1 |
    | Pocket (2nd) vs 4th | +1.1 | +1.8 |
    | Lead vs 4th | +0.02 (±0.20) | −0.95 (±0.19); the leader finished ahead only 21% of the time |

    **Read:** position is valuable; the lead isn't. H19 is rejected. The engine undervalues leading, and gate turns
    its advantage into taking the lead, which is why gate is worth about nothing.
    The spec's trip targets put the lead at 35% of half-mile wins and 25% of mile wins, so the lead has to be a good
    spot. **Next:**
    1. Find what makes leading costly: the air share and draft value, being pressed by first-over, how the leader
       paces the turns, and the breather. Measure each.
    2. The driver: gate should buy the best attainable spot, not the lead by default.
148. **M (lead assay, about 60 saved quarter states per track; two identical horses, the leader and 4th on the rail):**
    | Change, one at a time | Lead worth: half | Lead worth: mile | Reserve at the drive, leader vs 4th (mile) |
    |---|---|---|---|
    | None | −0.13 | −1.05 | 2.2 vs 7.2 |
    | No draft for anyone | +2.32 | +2.15 | |
    | Leader paces at what it can hold on the turn | +0.17 | +0.55 | 5.8 vs 8.1 |
    | First-over doesn't sit on the flank | no change | no change | |
    | No breather | +0.35 | −0.48 | |
    | Breather 3 | −0.22 | −0.92 | |

    On the half-mile the leader reached the drive completely empty, against 3.6 for the 4th horse.
    **With turn pacing, by draft:**
    | Draft | Half | Mile |
    |---|---|---|
    | 0.65 | +1.47 | +1.58 |
    | 0.8 | +1.77 | +1.77 |
    | 0.65, with `c_turn` 0.0003 | +1.25 | +1.58 |

    **Adopted:**
    - `lead_held` = 1, a driver competence: a horse setting the pace paces at the steady speed it can hold right
      there, turns included, for leaders and for sitters with nobody in front.
    - DRAFT 0.65: a covered horse pays 65% of the air, so cover saves about 10% of demand at cruise, not 15%.
      Provisional physics, to be confirmed against the trip targets in stage 5.
149. **M (after the change):**
    - **Merge suite:** all 9 pass.
    - **Slot assay:**
      | Forward spot vs rear spot | Half | Mile |
      |---|---|---|
      | Lead vs 4th | +1.50 | +1.70 |
      | Pocket vs 4th | +1.14 | +2.05 |
      | 3rd vs 5th | +1.83 | +2.49 |
      | 2nd vs last | +4.67 | +5.48 |
    - **Gate assay:** +0.5 gate still gains about 1.2–1.4 places by the quarter, and now keeps some of it: +0.12 at
      the wire on the half-mile, +0.38 on the mile.

      That's the wrong way round for the contract (half 0.45, mile 0.20).
150. **M (trait check after the lead fix; 16 fields × 8 subjects):**
    | Trait | Half, frozen | Half, adaptive | Mile, frozen | Mile, adaptive |
    |---|---|---|---|---|
    | Gate | +0.02 | +0.09 | +0.09 | **+0.48** (was −0.11) |
    | Cruise | +0.73 | +0.74 | +0.47 | +0.48 |
    | Kick | −0.02 | −0.07 | +0.11 | +0.14 |
    | Grit | +0.03 | +0.03 | +0.06 | +0.06 |
    | Manners | +0.01 | +0.01 | +0.02 | +0.02 |

    **Read:**
    - Rule 0.13 now holds for gate on average: adaptive driving no longer turns it into a loss.
    - Gate's value comes almost entirely through the plan. With gate aims frozen, a gate horse can't take the top
      its speed earns, so a frozen measure undervalues gate by design (review 16: gate is an option).
    - Cruise still dominates. Kick is about zero on the half-mile. The single-horse settings (`pace_k`, `c_turn`,
      `k_kick`, `e_max`, `fade`) still have their pre-fit defaults.
    **Measurement change (mine; Patrick's track-shaped targets are unchanged):** the contract's trait values are
    measured with **adaptive** driving, which is what players will see. Frozen-aim values stay as a diagnostic,
    and rule 0.13 stays a gate.
    **Next:** stage 3 refit with review 16's plan:
    - paired designs on 64–128 fields per track;
    - single-dial sensitivities first: `k_kick`, `p_cruise`, `a_gate`/`burst_gate`, `k_grit`, and the clock pair
      `pace_k`/`c_turn`;
    - then a small constrained step toward the contract.

## Stage 3 refit, round 1 (`v3_sens.py`: 64 fields per track, every horse upgraded in turn, adaptive driving, breaks off, DT 1/16; ± is the field-level se)

151. **M:**
    | Setting | Half time | Half reserve at the drive | Half gate | Half cruise | Half kick | Half grit | Mile time | Mile gate | Mile cruise | Mile kick | Mile grit |
    |---|---|---|---|---|---|---|---|---|---|---|---|
    | **Base** | 2:01.9 | 0.42 | +0.06±0.07 | +0.77±0.05 | −0.04±0.04 | +0.05 | 1:56.8 | +0.36 | +0.46 | +0.13 | +0.05 |
    | `k_kick` 1.6 → 2.6 | | | | | about no change | | | | | +0.19 | |
    | `p_cruise` 0.06 → 0.04 | | | −0.04 | +0.53 | | | | +0.28 | +0.27 | | |
    | `a_gate` +1, `burst_gate` +1.5 | | | no change | | | | | no change | | | |
    | `k_grit` 0.8 | | | | | | +0.07 | | | | | +0.10 |
    | `pace_k` +0.03 | +2 s | | | cruise up | | | +2 s | | cruise up | | |
    | `c_turn` 0.0007 → 0.0004 | 1:58.1 | 0.53 | +0.13 | +0.64 | | | 1:54.8 | | +0.40 | | |

    **Read:**
    1. The clocks slipped after the lead fix: half 2:01.9, mile 1:56.8, against live 1:55.9 and 1:53.4. Leaders
       now pace the turns at what they can hold, so the whole race is slower. The clocks have to be refit.
    2. Kick has almost no lever. A 60% stronger kick adds +0.06 on the mile and nothing on the half-mile. The drive
       starts 1,400 ft out, which is mid-turn on the half-mile, where the turn's held speed and traffic bind; the
       stretch is only 500 ft. Kick's one job (top speed in the drive) isn't getting a chance to work.
    3. Gate's value comes only through the driver's plan. The physical gate dials do nothing, so gate is set by
       driver habits (when a quick horse goes for the top), not by acceleration.
    4. Cruise has a strong, roughly linear lever (`p_cruise`). Grit has a weak one.
    **Next (round 2):**
    - Clock pair: `c_turn` lower, `pace_k` lower.
    - Kick's mechanism: where the drive begins on each track, kick applying through the drive with a gentler
      fade, and open lanes in the stretch.
    - Gate through the driver: how strongly a gate shortfall puts a horse off the top, and post penalties by track.
    - Cruise down toward 0.35.
    All measured with the same paired design.
152. **M (refit round 2, same design; base 2 = `c_turn` 0.0003, `pace_k` 0.99):**
    | Setting | Half time | Half gate | Half cruise | Half kick | Half grit | Mile time | Mile gate | Mile cruise | Mile kick | Mile grit |
    |---|---|---|---|---|---|---|---|---|---|---|
    | Base 2 | 1:54.9 | +0.22 | +0.61 | +0.04 | +0.06 | 1:52.3 | +0.54 | +0.31 | +0.16 | +0.06 |
    | Fade 0.3 | | −0.04 | +0.68 | | | | +0.62 | | +0.16 | |
    | Fade 0.3, `k_kick` 3.0 | | | | +0.03 | | | | | **+0.30** | |
    | `e_max` 18 | 1:54.1 | **+0.46** | +0.41 | +0.11 | +0.10 | 1:51.6 | +0.79 | +0.19 | +0.18 | +0.04 |
    | Drive from 1,000 ft | | +0.21 | +0.42 | | | | +0.71 | +0.21 | +0.13 | |
    | `s_top_short` 4 | | +0.06 | | | | | +0.46 | +0.39 | | |
    | Half post penalty −0.3 | | +0.20 | | | | | no change | | | |
    | `p_cruise` 0.045 | | | +0.44 | | | | | +0.23 | | |

    Each figure is good to about ±0.04–0.09.
    **Read:**
    - The tank size is the big lever: it makes position (gate) pay on the half-mile.
    - Kick needs a strong coefficient and a gentle fade.
    - The mile is the problem. Gate is worth far too much there (0.5–0.8, target 0.20), kick is short (target
      0.45), and cruise reverses its track shape (high on the half, low on the mile).
    **Round 3:** combine `e_max` 18, `k_kick` 4.5 and fade 0.3, then single changes on top of that.
153. **M (refit round 3; candidate c1 = base 2 + `e_max` 18, `k_kick` 4.5, fade 0.3):**
    | Setting | Half time | Half gate | Half cruise | Half kick | Half grit | Mile time | Mile gate | Mile cruise | Mile kick | Mile grit |
    |---|---|---|---|---|---|---|---|---|---|---|
    | c1 | 1:53.2 | +0.44 | +0.38 | +0.41 | +0.11 | 1:51.1 | +0.78 | +0.17 | +0.55 | +0.04 |
    | `c_turn` 0.0001 | 1:50.8 | | | | | | | | | |
    | `pace_k` 1.01 | 1:54.5 | | | | | 1:52.3 | | | | |
    | Post penalty 0.6 | | +0.24 | | | | | +0.47 | | | |
    | `k_kick` 6 | | | | +0.56 | | | | | +0.67 | |
    | `p_cruise` 0.05 | | | +0.35 | | | | | +0.18 | | |
    | DRAFT 0.75 | | | | | | | | | about no change | |
    | Drive from 1,800 ft | | | | | | | +0.71 | | | |

    **Read:**
    - **On target on the half-mile:** gate, cruise and grit. Kick there is too high (0.41 against 0.20).
    - **Mile:** gate is far too high (0.78 against 0.20) and cruise too low (0.17 against 0.35).
    - **Clocks:** about 2.5 s fast.
    - The mile reserve at the drive is 0.86: leaders pace exactly at what they can hold, so nothing makes stamina
      count until the stretch.
    **New driver habit, `lead_push`** (ft/s a pace-setter runs above what it can hold), so a race pace spends
    reserve. Round 4 combines that with a track-specific post penalty for going to the top, a gentler kick and a
    clock correction.
154. **M (refit round 4):** base r4_c = `c_turn` 0.0003, `pace_k` 1.03, `e_max` 18, `k_kick` 3.5, fade 0.3, top-post
    penalty 0.6, half-mile modifier −0.27.
    - **Half-mile, all inside tolerance:** 1:55.8; gate +0.39, cruise +0.41, kick +0.21, grit +0.10.
    - **Mile:** clock 1:53.7 and kick +0.37 are in tolerance; gate +0.43, cruise +0.12 and grit +0.04 are not.
    - **`lead_push` 1–2 on both tracks:** mile cruise up to 0.17–0.25, but half gate falls to 0.25 or below.
    - **Post penalty 0.9 / half −0.51:** the half-mile's effective penalty is unchanged, and mile gate falls to 0.14.
    - **`e_max` 15:** worse on both tracks.

    **Round 5:** r4_c plus the mile post penalty, with `lead_push` on the mile only (`lead_push_mile`, a new driver
    habit: big tracks race to a stiffer pace), plus stamina and grit variants.
155. **M (refit round 5):** r5_c = r4_c with the top-post penalty at 0.9 and the half-mile modifier at −0.51.
    - **Half-mile, all inside tolerance:** 1:55.8; gate +0.39, cruise +0.42, kick +0.20, grit +0.10.
    - **Mile:**
      - in tolerance: gate +0.20, kick +0.40, grit +0.05;
      - the clock is 1:54.0, 0.1 s outside its ±0.5;
      - **cruise is +0.16 against 0.35 and fails.**
    - **Mile-only `lead_push` 2 or 3:** mile cruise rises to 0.21 / 0.29, but the clock goes fast (1:51.0 / 1:49.6)
      and gate collapses (+0.08 / −0.04).
    - **`p_cruise` 0.07:** mile cruise 0.25, half cruise 0.46 (at the top of its tolerance).
    - **`k_grit` 0.9:** grit half 0.18, mile 0.07–0.09.

    **Read:** with these mechanisms, stamina is worth about twice as much on the half-mile as on the mile, because
    the half's tight turns tax sustainable power. Lifting mile stamina to 0.35 breaks the mile clock and gate, or
    pushes the half-mile out of tolerance. **Patrick to choose:**
    - accept mile stamina at about 0.2, so stamina is a half-mile asset;
    - or a mechanism that taxes stamina on the mile (a stiffer early pace on big tracks), refitting its clocks;
    - or revise the stamina target.
156. **Patrick: accept mile stamina at about 0.2.** Stamina is mainly a half-mile asset; the mile stays a speed and
    kick track. Contract amended: mile cruise target 0.20 ±0.08. Everything else is unchanged.
    **New defaults (round-5 r5_c):**
    - race3: `c_turn` 0.0003, `pace_k` 1.03, `e_max` 18, `k_kick` 3.5, fade 0.3; DRAFT 0.65 (item 148).
    - drive3: `s_top_post` 0.9, `s_top_post_half` −0.51, `lead_held` 1.
    - Driver habits added this round and left at 0: `lead_push`, `lead_push_mile`, `gate_pace`.

    Next: confirm on 256 untouched fields per track (seed 913), and recheck safety at the new speeds.
157. **M (confirmation: 256 untouched fields per track, seed 913, new defaults, adaptive driving, breaks off, DT 1/16):**
    | | Half result | Half target | Mile result | Mile target |
    |---|---|---|---|---|
    | Clock | 1:55.7 | 1:55.9 ✓ | 1:54.1 | 1:53.4, **0.2 s outside** |
    | Gate | +0.48 ±0.04 | 0.45 ✓ | +0.19 ±0.02 | 0.20 ✓ |
    | Cruise | +0.44 ±0.03 | 0.35, **0.01 over** | +0.17 ±0.01 | 0.20 ✓ |
    | Kick | +0.23 ±0.02 | 0.20 ✓ | +0.37 ±0.01 | 0.45, at the edge |
    | Grit | +0.12 ±0.01 | 0.12 ✓ | +0.03 ±0.01 | 0.12, **0.01 under** |

    Seven of ten trait cells and one of two clocks are inside tolerance on the point estimates. Three miss by a hair.
    Review 16's stricter test, the whole confidence interval inside each band, isn't met yet for half cruise, mile
    kick or mile grit.
    **Safety at the new settings (DT 1/16, 20 races per track):**
    - Merge suite: all 9 pass.
    - Mile: clean.
    - Half-mile: 0 overlaps and 3 breaches, but 1,520 four-wide-on-turn steps outside the gate exception (was 85
      before the refit). The stronger kick and drive likely send more horses three or four wide on the last turn.
      Needs a fix before going on.
158. **Four-wide fix (half-mile):**
    - **Cause:** all 1,520 steps were on the final turn, in the drive (follow 1,328, first-over 192). On the
      backstretch before it, horses fanned out to the fourth lane to pass. The driver only barred the fourth lane
      within 300 ft of a turn, about 6 s at drive speed. The turn then arrived with the third lane full, and they
      stayed four wide. Half the spells began before the turn and half were already wide.
    - **Fix (drive3 `turn_look` 600):** no fourth lane once the next turn is within 600 ft.
    - **M:**
      - 40 races at DT 1/16: zero four-wide-on-turn steps on both tracks, zero overlaps.
      - Mile breaches: 0.
      - Half breaches rose from 3 to 7 in 20 races, sized 0.11–1.0 ft/s over the limit, all as yet unexplained.
      - Merge suite: all 9 pass.
      - Stat balance on the same 64 fields: unchanged within error (half gate +0.41, cruise +0.41, kick +0.21,
        grit +0.09; mile identical).
159. **The half-mile breaches, traced and fixed:**
    1. **Turn-boundary stepping.** All 7 new breaches had the follower crossing into or out of the final turn
       mid-step. It moved by its rail rate from the start of the step, so a horse wide out was carried about 0.3 ft
       too far along the rail, and the gap shrank. **Fix:** `Track.advance(s, d, y)`, the exact inverse of `path`,
       split at turn boundaries. Self-checked. Result: 40 races at DT 1/16, zero breaches on both tracks.
    2. **Phasing in the turn allowance.** With breaks on, one more episode turned up: 7 consecutive steps, each
       0.03–0.06 ft/s over. A horse moving in toward the rail just before a turn was following a horse braking at the
       limit in the lane it was leaving. The 100 ft phase-in of a wider leader's speed added a little apparent
       braking. **Fix:** `TURN_LOOK` 200 ft.
    **M (100 races per track, DT 1/16, breaks on at the default rate: 59–61 breaks per 100 races):**
    - **Both tracks, all zero:** overlaps, braking breaches, sideways snaps, stopping dead, unfinished races, and
      four-wide on a turn outside the gate exception.
    - At most 5–6 line reversals for one horse in a race.
    - Merge suite: all 9 pass.
    - **Stat balance after the exact stepping** (64 fields): half gate +0.40, cruise +0.44, kick +0.26, grit +0.12;
      mile unchanged.
    **Part 0's safety rules hold in every race tested.**
160. **Test replay (Patrick: private test link):** `v3_replay.py` builds a copy of the game's HD-2D replay page. The
    real replay and the live site are untouched.
    - It loads two embedded race3 races (half-mile, and mile on `#mile`), each picked so the winner isn't from post 1
      and at least two moves are logged.
    - The replay's oval is set to the shape of the track raced (S, R, finish at the run-in before turn 1).
    - Its own story simulation is replaced by race3's recorded paths, resampled to 20 Hz, with o = y + 1.
    - The cosmetic gate stagger is off, and the infield lake is scaled to fit the half-mile.
    - The art is published alongside: 49 files, 8 MB.
    - **Link:** https://claude.ai/artifact/QqNSqTyw4LXRs2PpZvfQ8T (private).
    - Scripts parse. Rendering is **unverified**: my browser pane isn't signed in to claude.ai.
161. **Patrick's notes on the test replay** (held for the replay camera and asset review after the engine is done):
    - A hedge blocks the view of the final turn.
    - A building blocks the shot down to the wire.
    - Some camera angles are zoomed in too far.

    **Cause:** the replay lays out its scenery from the oval's size and the finish position, and was only ever tuned
    for its own mile oval (1,100 / 490, wire 150 ft before turn 1). race3's tracks differ: mile 1,320 / 420, half
    800 / 166, wire 300–320 ft before turn 1.
    **Direction (proposed, to settle at the replay hookup):** fit race3's mile to the replay's oval and keep that
    scenery; give the half-mile its own layout. Then review cameras on both tracks.
162. **Near misses closed (64 fields):** nm_a = `p_cruise` 0.05, `k_grit` 0.85, `lead_push_mile` 0.5. It put every cell
    and clock inside tolerance. nm_b and nm_c were close but missed (half grit 0.15–0.18; mile clock).
163. **Patrick (2026-11-01): manners is a safety stat, not a racing stat.** Breaks should be pretty darn rare unless a
    horse is very low in manners.
    **Contract replaced:** break rate by manners level, no longer places gained:
    | Manners | Target |
    |---|---|
    | +0.4 | about 1 in 500 starts |
    | 0 | about 1 in 200 |
    | −0.8 | about 1 in 20 |
    | −1.2 | about 1 in 7 |

    **Fit:** `break_b0` 0.000025, `break_manners` 2.9. Pressure and traffic terms unchanged.
    **M (subject at a set manners level, normal driving, DT 1/16):**
    | Manners | Measured | Starts |
    |---|---|---|
    | +0.4 | 1 in 600 | 1,800 |
    | 0 | 1 in 150 | 1,800 |
    | −0.8 | 1 in 18 | 600 |
    | −1.2 | 1 in 8 | 600 |
    | Random field horses (spread 0.4) | 1 in 153 | 33,600 |
164. **Confirmation (256 untouched fields per track, seed 914, adaptive, breaks off, DT 1/16): all 10 trait cells
    and both clocks are inside tolerance.**
    | | Half | Mile |
    |---|---|---|
    | Clock | 1:55.6 | 1:53.0 |
    | Gate | +0.41 ±0.05 | +0.15 ±0.02 |
    | Cruise | +0.38 ±0.03 | +0.15 ±0.01 |
    | Kick | +0.23 ±0.02 | +0.37 ±0.01 |
    | Grit | +0.19 ±0.01 | +0.05 ±0.01 |

    Edges: half grit and mile kick sit at the tolerance limit, and the mile clock is 0.4 s fast. Review 16's stricter
    test (the whole interval inside the band) isn't met for half grit, mile kick or mile grit.
    **Safety (100 races per track, breaks on):** one half-mile episode at 0.026 ft/s (a horse moving in on the
    backstretch while following a horse braking at the limit, with the turn allowance phasing in). `TURN_LOOK`
    300 ft → **zero on both tracks**:
    - overlaps, breaches, snaps, stopping dead, unfinished races and four-wide-on-turn steps;
    - breaks: 7 and 9 per 100 races;
    - merge suite: all 9 pass.

    The stat balance wasn't remeasured after `TURN_LOOK` 300, a follower-only safety parameter; expected to be
    negligible.

## Part 1, first readings (CONTRACTS.md; `v3_part1.py`)

165. **Built:**
    - `CONTRACTS.md`: the Part 1 measurements, frozen.
    - The live field-size mix: mile 88% ten starters; half-mile 91% eight starters.
    - Race-day form in race3: `form_sd`, one draw per horse per race added to gate, cruise and kick.
    - `v3_part1.py`: the scorer.
166. **M (200 races per track; reruns: 32 fields × 24):**
    | Check | Form 0 | Form 0.3 | Target |
    |---|---|---|---|
    | Half posts 1–8 | 40.5, 23, 15, 11.5, 3, 2.5, 4.1, 0.5 | 37.5, 19.5, 12, 15, 5.6, 3, 7.1, 0.5 | 18.6 → 5.9 |
    | Mile posts 1–10 | 54, 25.5, 11.6, 9.1, then 0 for posts 5–10 | 45, 32, 11.6, 11.1, 0.5, then 0 | 13 → 7 |
    | Half trips (lead / pocket / first-over / followed / back) | 56 / 0 / 28 / 8 / 7 | 71 / 2 / 16 / 6 / 4 | 35 / 22 / 15 / 15 / 13 |
    | Mile trips | 60 / 31 / 0 / 0 / 8 | 69 / 24 / 0 / 1 / 6 | 25 / 18 / 17 / 20 / 20 |
    | Second quarter slowest | 96% | 95–99% | ✓ |
    | Last quarter fastest or 2nd | 100% | 100% | ✓ |
    | Median winning margin (half / mile) | 2.6 / 1.9 lengths | 3.2 / 2.4 | < 2 |
    | Photos (half / mile) | 2% / 6% | 1% / 4% | 8–17% |
    | Best horse wins (class fields) | 100% | 62% ±4 (top three 89%) | 30% |
    | Same winner on a rerun | 99% | 50% ±4 | 45% |
    | Favorite wins (mixed fields) | 98% | 68% ±5 | 35–40% |
    | Bottom third wins | 1% | 7% | 8% |

    **Read:**
    1. **Front-runners dominate under the real field sizes,** above all the mile's ten-horse fields. The fitting
       used eight. Posts 5–10 never win the mile. Moves from outside never win the mile. The half-mile has no
       pocket winners. Finishes are too strung out (photos 1–6%).
    2. **Items 6 and 7 are infeasible together as written.** A field's repeat rate is the sum of p_i², which is at
       most p_max. A 45% repeat needs the best horse at 45% or more, so 30% for the best horse and 45% for repeats
       can't both hold on one population. Patrick to choose.
    3. Race-day form is the lever for items 4–7. 0.3 gives a 50% repeat but 62% for the best horse.
167. **Patrick:** of items 6 and 7, the 45% repeat wins: form holds. Item 6 becomes whatever goes with a 45% repeat
    (expected around 50–55% for the best horse), reported and not fitted. CONTRACTS.md is amended.
168. **M (reruns at more race-day form, 32 fields × 24):**
    | Form | Best horse wins (class) | Same winner on a rerun | Favorite wins (mixed) | Bottom third wins |
    |---|---|---|---|---|
    | 0.4 | 44% | 35% | 57% | 8% |
    | 0.5 | 41% | 32% | 51% | 10% |

    Interpolating from 0.3 (50% repeat) and 0.4 (35%): **`form_sd` 0.33** for a 45% repeat. The best horse is then
    about 55%, the favorite on mixed fields about 63%, and the bottom third about 7%. **Set as the default.** To be
    confirmed in the next run.
    **Item 4 (favorite 35–40%) can't be met while "favorite" means the true best.** With form holding (item 7), the
    true best wins far more than 40%. Real favorites win less because the betting public misjudges true ability.
    **Proposal:** measure item 4 against the game's own odds-making, from the public information players see, once
    the engine is wired in. Until then, report it as true best. To ask Patrick with the next report.
169. **Patrick:** item 4 (favorite 35–40%) is measured against the game's own odds-making, from what players can
    see, once race3 is wired in. CONTRACTS.md is amended. Until then the lab reports the true best on mixed fields as
    a reference only.

## Part 1, front dominance (2026-11-01)

170. **M (`v3_front_diag.py`, `v3_e_trace.py`, `v3_e_parts.py`, 30–60 races):** at the drive the field is strung out
     about 2.5 lengths per horse, single file (mile 22 lengths, half 16). The back half carries the least reserve,
     not the most: it was uncovered 50–70 s and re-accelerated after braking. A post-10 horse slowed to 7.5 ft/s at
     the start. The cause: each outside horse eased to 5 ft/s under the one inside it, chaining outward.
     **Fix:** `start_floor` 0.85 (rule 0.10 applies at the start too). It restored the reserve at the back; the
     Part 1 results were unchanged.
171. **Fixed: two driver bugs.**
     - A horse that planned first-over and found itself on the lead "pulled first-over" on itself at the half and
       sprinted for 40 s. It now takes the top aim ("found the lead").
     - Up to five horses pulled first-over at once. Now only one goes; the rest wait for cover.

     Part 1 results unchanged (mile: lead 72%, posts 5–10 0 wins in about 800 starts).
172. **M: `fade` isn't the lever.** Lead/pocket win shares at fade 0.3 / 0.6 / 1.0 are 96 / 97 / 97% on the mile,
     with posts 5–10 still at zero. Reserve differences don't move results, so the block is in passing itself (the
     drive), not in energy. Next: trace a drive.
173. **Fixed: a drive deadlock.** In the drive every horse pressed at full speed into the one ahead, so each sat at the
     minimum safe gap. An outward move on a turn needs slightly more than that, so nobody could pull out (one mile
     race: 14 s boxed). Two driver habits:
     - `ease_out` 1 ft/s: a boxed horse eases to get out, in the drive and in a move;
     - `sit_room` 2.5 ft: a sitter keeps that much over the safe gap.

     **M:** the mile's first-over horse now pulls out (at the drive: lane 0 → 1, 3.6 → 1.8 lengths back, a cover
     train of 1.2). Part 1 results stayed front-dominated.
174. **M: the pace regime is the root cause (review 17's experiment 2, short form, `v3_drive_solo.py`).** Each race
     is frozen at the drive and every horse runs the rest alone from its exact state. Drive leaders that win, of 50:

     | | Soft pace (old) | True pace (`lead_push` 3) |
     |---|---|---|
     | Half, alone | 33 | 6 |
     | Half, actual | 38 | 16 |
     | Mile, alone | 29 | 12 |
     | Mile, actual | 40 | 23 |

     **Read:**
     - Under a soft pace the leader wins most races even with no traffic: sitters reach the reserve cap and refill
       at only `recover` 0.3, so sitting buys about 2–3 units.
     - Traffic adds about 20 points for the leader in both regimes (a separate, smaller passing problem).
     - **A true race pace is needed** (`lead_push` 3, `lead_push_mile` 0; clocks refit to `pace_k` 1.094,
       `c_turn` 0.00034; Part 1: half trips 32/11/35/20/2, mile 43/8/26/22/1).
     - **It breaks the stat balance** (64 fields; half gate −0.02, cruise +0.65, kick 0.00; mile gate −0.12, cruise
       +0.64, kick +0.21, grit +0.24).
     - Safety is clean (200 races: zero hard failures; merge suite 9/9).
175. **Review 17 (Astra):** don't rely on a constant hard pace alone. It caught a bug:
     - **Bug:** a pressed leader's pace target included the duel's cost, so pressure lowered its pace.
     - **Fix:** `held_speed(h, duel=False)` for driver targets; the duel is still paid.
     - **Re-test:** soft pace with pressure (`dig` 3, `duel` 0.5) still gives leaders 82–85%. Pressure alone isn't
       enough.

     Its other points:
     - The start can't sort ten horses onto the rail in 320 ft (post 10 needs about 16 s laterally): outside
       posts need mid-line slots.
     - Non-leavers get nothing from gate (`gate_pace` 0).
     - Measure behavior first, then geometry.
176. **Next, running:** the balance refit under the true pace (`v3_fit.py`, log `v3/fit_hardpace.jsonl`,
     `lead_push` held at 3). Physics knobs plus the gate habits `s_top`, `s_pocket`, `gate_pace`. Then Part 1 again,
     then the outside-post start (review 17 C).
177. **Patrick (2026-11-01): displayed times may be mapped onto real-world times.** If the sim races right but a
     horse that should go 1:50 goes 1:52, players can be shown a mapped time.
     **Applied as:**
     - a per-track linear map, display = a + b·sim, fitted to real winning times by class;
     - the same map on the final time and every fraction, so quarters add up and fast horses stay fast;
     - this also covers item 9 (tier clocks).

     **In the lab:** the clock leaves the fit, except a ±3 s plausibility band (`FIT_CLOCK_BAND`) so the physics
     can't drift to absurd speeds. The refit restarted on this basis.
178. **Patrick (2026-11-01): what gate speed means.** "A horse with good gate speed can rapidly fire off the gate to
     grab an early lead or secure a prime pocket position around the first turn. A horse with slow gate speed gets
     left behind or trapped on the outside, forcing the driver to work harder."
179. **Built: pocket-leaving.** A pocket-aim horse now leaves like a leaver: it brushes to the leader's back, tucks in,
     and takes back if it can't clear by the first turn. Kept, since it is Patrick's definition.
     **M (64 fields, true pace, adaptive aims; places gained for +0.5 gate, half / mile):**
     | Setting | Half | Mile |
     |---|---|---|
     | True pace, old habits | −0.02 | −0.12 |
     | + pocket-leaving | −0.22 | −0.01 |
     | + habits valuing the pocket (`s_top` 1.5, `s_pocket` 3) | −0.10 | −0.22 |
     | + `gate_pace` 1 | −0.12 | −0.20 |
     | + an early-speed reserve sized by gate (3 or 6 units, launch only) | −0.01 / −0.05 | −0.14 |

     The early-speed reserve was removed again (no effect).
     **Read:**
     - Under a constant true pace, anything that puts a horse near the front is a liability, because the leader is
       made to burn: `lead_push` is a habit of whoever leads.
     - Under a soft pace, gate is worth its target, but leaders win 70–80% even with no traffic (174).
     - **Neither constant pace fits the sport:** soft fractions favor the leader, hot fractions the closers.
       Real pace comes from the race itself: a clear lead is rated soft; a battle for the lead or early pressure makes
       it hot.
     **Stop rule triggered:** three gate fixes failed. Brought to Patrick instead of more knobs.
180. **Built (Patrick: "Yes, build it"): pace from the race.**
     - A clear leader rates the pace (soft defaults again: `lead_push` 0, mile 0.5; clocks `pace_k` 1.035,
       `c_turn` 0.00032).
     - A leaver that can't clear presses on the leader's flank instead of taking back, when its gate + cruise is
       within `press_margin` 0.3 of the leader's. It keeps pressing until `press_budget` is spent, then takes back.
     - A pressed or headed leader digs in (`dig`).
181. **M: it doesn't fix front dominance.** Part 1, 200 races per track: leaders win 84% on both tracks; clocks
     1:55.3 / 1:53.0.
     **Battles:** 25% of half-mile races, but about 2% on the mile, where plans aim for the lead about once a race.
     **Half-mile races split by battle (120 races):**
     | Setting | Leader wins, no battle | Leader wins, battle | Half, no battle / battle |
     |---|---|---|---|
     | `press_budget` 2, `dig` 2 | 74% | 92% | 59.9 / 59.5 s |
     | `press_budget` 5, `dig` 4, `duel` 0.5 | 72% | 67% | 60.0 / 58.4 s |
     | `press_budget` 8, `dig` 5, `duel` 0.8 | 75% | 75% | 59.9 / 58.8 s |

     **Read:**
     - A fought duel makes the half 1–1.5 s faster, but whoever survives it at the 3/4 still wins two times in
       three. Local battles don't drain the front the way a whole-race true pace does (174).
     - The hypothesis is falsified in this form. The press behavior is kept for race variety (hot fractions do
       happen); it is untested for balance.
182. **Where the evidence now points:**
     - **Realistic trips need a true pace over the whole race** (174).
     - Under it, gate can only pay through the pocket, and the pocket wins just 8–11%: it's boxed behind the leader
       with the first-over horse outside.
     - The real-world feature that makes the pocket pay is the inside **passing lane** in the stretch, which many
       North American harness tracks have. It's track geometry, not a bonus.
     - **To Patrick:** do our tracks have passing lanes?
183. **Patrick (2026-11-01): our tracks have a stretch passing lane.** Built:
     - `Track.min_y`: a lane inside the rail line from the end of the last turn to the wire;
     - `commit_ok` refuses inward moves where there's no passing lane;
     - the driver takes it when boxed on the rail in the stretch, never as the leader.
184. **Fixed: three safety regressions from pressing and pocket-leaving.** In 400 races there were 254 four-wide-on-turn
     steps and 13 near-miss braking episodes (0.025 ft/s).
     - **Press:** a presser went one lane outside a leader that was already two-wide. It is now capped at three-wide
       on turns.
     - **Urgent slot:** a wide sitter near a turn may ease up to 6 ft/s to find a slot (was 2.5).
     - **Lock:** two horses sat side by side for 20 s matching speed, the outer one unable to get in. After `lock_s`
       3 s beside a horse it can't get in on, the outer one tucks in 3 ft/s under it.

     **M (400 races):** zero overlaps, breaches, snaps, stops, four-wide turn steps and unfinished races; merge suite
     9/9.
185. **M: passing lane, Part 1 (200 races per track):**
     | Pace | Track | Trips (lead/pocket/first-over/followed/back) | Clock |
     |---|---|---|---|
     | Race-driven (soft) | Half | 82/4/10/4/0 | 1:55.4 |
     | Race-driven (soft) | Mile | 81/4/10/4/0 | 1:53.0 |
     | True (`lead_push` 3, `pace_k` 1.094, `c_turn` 0.00034) | Half | 26/18/35/21/1 | 1:56.2 |
     | True | Mile | 42/16/19/20/2 | 1:53.4 |

     Targets: half 35/22/15/15/13, mile 25/18/17/20/20.
     **Read:** under a true pace the pocket now pays (18/16%, up from 8–11%). Under a soft pace nothing changes
     (leaders never tire).
     **Still off:** closers from the back (1–2%), half first-over (35%), outside posts (5+ about 1%).
     **Gate's worth (64 fields, true pace + passing lane):**
     | Drivers | Half | Mile |
     |---|---|---|
     | Old habits | −0.30 | −0.11 |
     | Valuing the pocket (`s_top` 1.5, `s_pocket` 3) | 0.00 | −0.08 |

     With pocket habits, cruise is at its target on the half (+0.36), but kick is −0.10 on the half.
     **Gate still doesn't pay under a true pace:** getting position costs about what it's worth.
     **Stop rule (178):** back to Patrick on the targets.
186. **Patrick: "Try the speed reserve."** M (64 fields; true pace, passing lane, pocket-valuing drivers; places gained
     for +0.5 gate, half / mile):
     | Setting | Half | Mile |
     |---|---|---|
     | Baseline (185) | 0.00 | −0.08 |
     | Gate speed reserve, 3 units | not recorded | not recorded |
     | Gate speed reserve, 6 or 10 units (identical: a quick horse gets out free at 6) | +0.04 | −0.05 |
     | + 3× launch (`burst_gate` 3, `a_gate` 2.5) | +0.05 | −0.06 |
     | + leavers brush at their own speed (`leave_gate` 6, `gate_pace` 2) | +0.05 | −0.05 |

     **Read:**
     - The cost of getting out was never what made gate worthless.
     - Neither was the drivers ignoring gate speed.
     - Under a true pace, the position gate buys converts to almost no finishing advantage.
     - The thread is closed. The reserve and `leave_gate` were removed again (no effect).
     - Back to Patrick: gate's target.
187. **Tooling: PyPy 3.12 v8.0.1** (Patrick approved the download).
     - **Source:** pypy.org, sha256 225aa62d… matches; at `C:\Users\spooh\tools\pypy3.12-v8.0.1-win64\pypy3.exe`.
     - **Results:** identical to CPython bit for bit (12 mile races).
     - **Speed:** 2.8× faster on 40 races (16.2 s vs 45.8 s); short runs don't gain (JIT warm-up).
     - **Use:** `PY=<pypy3.exe> sh p1run.sh`; v3_sens follows the interpreter it's started with.
     - **Process:** screen ideas at 16 fields and confirm at 64.
188. **Patrick (2026-11-01):**
     - "Races play out like real trips": trips take priority over early speed's worth.
     - He takes the suggestions and wants an engine he can watch and review for better decisions.

     **Plan:**
     1. Measure the pace dial (`lead_push` 1.5–3, pocket-valuing drivers).
     2. Pick the setting whose trips are closest to the targets.
     3. Amend gate's target to what that setting gives, then refit cruise, kick, grit and the clock band.
     4. Publish a test replay.
189. **M: the pace dial** (`lead_push` 1.5–3.0, pocket-valuing drivers `s_top` 1.5 / `s_pocket` 3; Part 1 200 races per
     track; trait worth 32 fields; PyPy). Trips are lead/pocket/first-over/followed/back.
     | `lead_push` | Half trips | Mile trips | Half gate / cruise / kick / grit | Mile gate / cruise / kick / grit |
     |---|---|---|---|---|
     | 1.5 | 76/12/9/4/0 | 65/14/12/8/1 | −.09 / .27 / −.04 / .05 | −.10 / .28 / .36 / .20 |
     | 2.0 | 62/22/12/5/0 | 60/16/13/8/2 | −.05 / .31 / −.03 / .03 | −.14 / .26 / .36 / .17 |
     | 2.5 | **39/36/16/10/0** | 53/16/16/14/0 | −.04 / .35 / −.04 / .05 | −.09 / .33 / .23 / .18 |
     | 3.0 | 28/39/18/14/0 | **40/26/16/15/2** | −.02 / .32 / −.08 / .07 | −.15 / .38 / .25 / .18 |

     **Read:**
     - With drivers who value the pocket, gate's worth is about zero at every dial setting.
     - Half kick is slightly negative: a better finisher's driver plans a closing trip, and closers don't win yet.
     - Under the hard pace the mile's second quarter is seldom the slowest (6–25%).

     **Chosen (Patrick 188: trips first):**
     - half `lead_push` 2.5;
     - mile 3.0 (`lead_push` 2.5 + `lead_push_mile` 0.5);
     - `pace_k` 1.094, `c_turn` 0.00034;
     - `s_top` 1.5, `s_pocket` 3.0.

     Clocks are within the ±3 s band (display map, 177).
     **Contract amended (CONTRACTS):** gate's worth target is now 0.05 on both tracks, the floor: extra gate speed
     never costs places.
     **Also corrected:** `v3_fit.py` still had the mile cruise target at 0.35. Patrick's 0.20 (143) is restored.
     **Refit:** `v3_fit.py` on PyPy; knobs add `s_close_kick` and `s_follow_kick` (kick mustn't cost places).
     **Still open after the refit:**
     - closers from the back (0–2%);
     - outside posts;
     - the mile's second quarter.
190. **Refit A rejected.** `v3_fit.py` scores balance only. Its best candidate set `s_top` 0.13: nobody aims for the
     lead and post 1 drifts to the front.
     **M (Part 1):**
     - half trips 73/14/10/4/0; post 1 wins 73% of half-mile races;
     - balance not confirmed either (64 fields): half cruise .15, mile gate −.13.

     **Lesson:** the fit must score trips and balance together. Next fitter: Part 1 trips plus balance in one loss.
191. **M: committed engine** (dial setting, 189), Part 1 on PyPy, 200 races per track:
     | Track | Trips (lead/pocket/first-over/followed/back) | Wins by post |
     |---|---|---|
     | Half | 39/36/16/10/0 | 37.5, **54**, 7.5, 1, then 0 for posts 5–8 |
     | Mile | 40/26/16/15/2 | 40, 36, 15, 8.6, 0.5, then 0 |

     **Read:** the trip shares are near target, but they come from posts 1–2. Post 1 leads; post 2 pockets and uses
     the passing lane. **The start (outside posts) is now the top problem** (review 17 C).
192. **Test replay updated** (artifact QqNSqTyw4LXRs2PpZvfQ8T, version 2), for Patrick to watch.
     - 4 half-mile and 4 mile races: seeds 1–4, unpicked; mile fields of 10.
     - Captions for pressing and taking the lead.
     - Built on PyPy by `v3_replay.py`; checked loading locally in headless Chrome (no script errors).
     - Seeds 1–4 share horse traits across the two tracks, so it's 4 fields, not 8.
     - 7 of the 8 races are won from post 1.
193. **The start (Patrick: "Fix the start next").**
     **M (`v3_start_diag.py`, 80 races):** the running order after turn 1 is the post order (average place by post
     1.0, 2.0, 3.1 … 9.9), and so is the order at the 3/4.
     **Found and fixed: circular yielding.** Each horse eased for any horse a foot ahead or level, inside or coming
     over, so whole fields coasted down to the 0.85 floor together.
     **Built: a pecking order.** Before the gate, drivers rank who expects to get there first: gate minus `rank_post`
     0.15 per post out. A horse yields only to horses above it, so circular yielding can't happen. Only lead-seekers
     are let across. `gate_drop` 5 → 3.
     **M:**
     - zero hard failures in 400 races; merge suite 9/9;
     - Part 1: half trips 48/30/15/7/0, posts 46/47/7/0…; mile 52/23/12/11/2, posts 46.5/33.5/11/7.6/1.5/0…
     - The order by post is unchanged at every setting tried: `rank_post` 0.05–0.3, `gate_pace` 3–6,
       `gate_take_back` 0, and `VY_MAX`/`AY_MAX` 4 → 10.
     - Gate speed doesn't open enough room in 300 ft, and sideways speed isn't the limit.
194. **Patrick, watching the replay: "The horses run most of the race in sequential order, first through last."**
     That matches every measurement: the engine is a conveyor.
     - Post order forms at the start, and nothing reorders it mid-race.
     - Moves and covers happen, but the order at the 3/4 still equals the post order.
     - Closers from the back win 0–2%.

     **Read:** today's fixes were local, at the start, the drive, pressing and the pocket. None of them changes the
     structure. **Plan: stop patching and redesign the driver around position changes,** with one guiding metric:
     how far the running order departs from the post order at each call (rank correlation) and from call to call.
195. **Driver v4 plan written** (DRIVER_V4_PLAN.md), with `v3_churn.py` measuring position change against the free
     chart summaries.
     **Baseline (200 races per track):**
     - rail horse on the lead at the half 97% (half) / 90% (mile), reference about 25%;
     - rail horse top three at the half 100%, reference 79% / 37%;
     - order vs post at the half 0.94 / 0.95.

     **Review 18 (Astra) adopted (plan section 7):**
     - a paired 2×2 diagnostic (start challenged × earlier middle) before building, with checks that each treatment
       executed;
     - a second line needs the slot, lock, parked-budget and rail-intent rules changed together;
     - audit `crossing` (lead-seekers bypass the pecking order);
     - measure moves as attempt → exit → advance → cover;
     - monitor joint outcomes at every stage;
     - churn bands are guides, not tuning targets.
196. **The 2×2 diagnostic** (review 18; `v3_2x2.py`; 40 paired races per cell per track; same fields, posts and seeds).
     - **Start treatment:** the quickest non-rail horse is held to the lead aim.
     - **Middle treatment:** `move_fo` 0.375, `advance` 4.

     **Two execution obstructions were found and fixed first:**
     - **Half-mile first-over couldn't get out** (3% exited). The move starts 33 ft before the far turn, and the rail
       horse behind sat too close for an outward move on a turn. **Fix:** a sitter eases `ease_out` when the horse in
       front is waiting to pull out and it is the one too close. Exits: 3% → 100%.
     - **Leavers gave up at the first turn** whenever they hadn't cleared, after only 300 ft. **Fix:** they take back
       there only if they'd be four-wide (rule 0.4); otherwise they go round parked until the leave budget runs out.
       Remaining take-backs: posts 6–8 four-wide at the turn (as the chart reference expects), or parked and giving
       up later.

     Safety after both: zero hard failures in 400 races; merge suite 9/9.
     **M (after the fixes):**
     | Cell | Track | Rail leads at the half | Order ~ post at the finish | 3/4 → finish | Posts 1–2 win | Winner 5th+ at the 3/4 |
     |---|---|---|---|---|---|---|
     | Baseline | Half | 100% | 0.82 | 0.86 | 92% | 0% |
     | Middle | Half | 100% | 0.71 | 0.71 | 75% | 5% |
     | Start | Half | 62% | 0.62 | 0.78 | 75% | 0% |
     | Both | Half | 62% | 0.60 | 0.72 | 60% | 8% |
     | Baseline | Mile | 92% | 0.84 | 0.87 | 72% | 0% |
     | Middle | Mile | 92% | 0.74 | 0.73 | 48% | 8% |
     | Start | Mile | 25% | 0.63 | 0.81 | 52% | 2% |
     | Both | Mile | 25% | 0.58 | 0.72 | 45% | 5–8% |

     Start execution (on the lead at the 1/4 / took back): half 22% / 78%, mile 70% / 30%. First-over gain on the
     leader: 1.3–3.1 lengths.
     **Read:**
     - Both causes are real, and their effects roughly add.
     - The start sets the early order: on the mile, rail leads at the half fall from 92% to 25%, the chart reference.
     - The middle drives late churn and the closers.
     - Neither alone is enough; with both, inside-post dominance roughly halves.
     - Movers still gain only 1–3 lengths.

     **Next: stage A.** Real drivers' leave decisions, judged against the horses inside them, to replace the forced
     treatment. Then stage B (an earlier, budgeted brush; followers).
197. **Stage A built and confirmed: leave or tuck, judged locally.** In `plan()` (`local_leave` 1):
     - a horse aims for the lead when its gate is above every horse inside it;
     - the rail horse goes unless one of the `rail_look` 2 horses just outside it is quicker;
     - a horse planned for the lead that doesn't qualify tucks for the pocket.

     **Screened:** margins 0–0.3 and a per-lane cost of 0–0.05 change little; the simplest rule was taken (margin 0).
     **Safety regression, found and fixed:** 26 near-miss braking episodes in 400 races (0.021–0.025 ft/s, tolerance
     0.02). Horses moving in sat behind horses braking at the absolute limit on purpose (take-backs).
     **Fix (physics):** `EASE` 4 ft/s², the most a driver slows by choice. Only the safe-following rule brakes up to
     `BRAKE` 8. **Result:** zero hard failures in 400 races; merge suite 9/9.
     **M (200 races per track):**
     | Measure | Half (stage A) | Mile (stage A) | Half before | Mile before |
     |---|---|---|---|---|
     | Rail leads at the half | 46% | 26% | 97% | 90% |
     | Rail top three at the half | 98% | 93% | 100% | 100% |
     | Order ~ post at the half | 0.77 | 0.82 | 0.94 | 0.95 |
     | Order ~ post at the finish | 0.58 | 0.62 | 0.86 | 0.80 |
     | Trips (lead/pocket/first-over/followed/back) | 32/22/14/31/2 | 41/34/11/12/2 | | |
     | Wins by post | 33/33/19/9/1.5/3/1/0.5 | 40/31/13/8.6/3.5/2.1/0.5/1.6/0/0 | | |

     Clocks 1:56.5 / 1:52.4; median margin 3.9 / 4.4 lengths; photos 4%.
     **Still open (stage B and C):**
     - call to call from the 1/2 to the 3/4 is unchanged on the half (0.97);
     - the rail horse almost always top three;
     - closers 2%; margins wide;
     - half-mile followed-cover winners too many (31%).

     **Replay:** version 3, 6 half-mile and 6 mile races, unpicked, separate fields per track. Loads with no script
     errors (headless check). The four half-mile races 1–4 were all won from post 1; with 6 races, 4 of 6 are.
198. **Patrick's replay notes, Half race 1:** "the rest of the pack is basically stuck in mud, 6+ lengths back… by
     1:40 the 1 leads, the 5 is 2½ back, the next closest is 10 back. It's just not even a race."
     **Trace:** within 2 s of the gate every non-leaver dropped to 37–41 ft/s while the two leavers went 50.6. By 8 s
     the pack was 8–12 lengths back, then burned reserve chasing (51 ft/s at 20 s).
     **Causes:**
     - `gate_take_back` 1 ft/s per lane: post 8 gave up 7 ft/s;
     - yielding 2.5–3 ft/s under the horse yielded to, chaining (post 2 yielded to post 3, which was itself easing);
     - single-file spacing at about 2.8 lengths nose to nose (14 ft body, 6 ft safety gap mostly reaction time,
       2.5 ft sitter room).

     Post 1 in that race is also a strong horse (gate 1.0, cruise 1.06).
     **Changed:**
     - `gate_take_back` 0;
     - `gate_drop` 1.5, `yield_ft_s` 1.5;
     - `start_floor` 0.92;
     - `leave_push` 3;
     - `sit_room` 1.0;
     - `T_REACT` 0.1 → 0.03 s (drivers anticipate, so a line sits nearly nose to sulky).

     **Safety:** zero hard failures in 400 races; merge suite 9/9.
     **M (spread from the leader to the last horse, lengths, 60 races):**
     | Call | Half before | Half after | Mile before | Mile after |
     |---|---|---|---|---|
     | 1/4 | 22.8 | 20.9 | 32.5 | 24.3 |
     | 3/4 | 23.6 | 16.5 | 26.9 | 19.9 |

     **Part 1:**
     - half trips 24/28/23/24/2, posts 31/33.5/21/7/5/2/0.5/0;
     - mile trips 36/22/16/24/2, posts 26.5/34/13.5/14/5.6/5/1/0.5/0/0;
     - margins 3.6 / 3.1 lengths.

     **Trade-off:** rail leads at the half rose (half 46% → 60%, mile 26% → 36%): softer leaving, with the pack no
     longer giving way.
     **Read:** single file is now near its physical minimum (about 2.2 lengths per horse). The rest of the spread
     comes from racing in one line. Stage B's second line is the fix.
     **Replay:** version 4, same 12 races.
199. **Patrick's replay notes, Half race 1 again:** "the 1 and the 5 shoot out again. The 5 has a clear opportunity for
     the rail to tuck behind the leader, and doesn't… Why are those the only two horses doing a push for the top?"
     **Why only two:** stage A sent a horse for the lead only if it was quicker than every horse inside it. Post 1 is
     the quickest horse in that race, so nobody else qualified. #5 was the only pocket-seeker.
     **Changed: who leaves.** A horse leaves if it looks quicker than the `leave_look` 2 horses just inside it. A
     driver's read of a rival's gate is uncertain (`read_sd` 0.15, drawn per race), so near-matches sometimes both go
     and battle.
     **Why #5 didn't tuck (traced), four faults:**
     1. **The pocket-seeker controller:** it ran 0.5 ft/s under a leader it was level with, too little to drop a length
        before the turn. **Now:** it aims at the spot behind the leader (gain 0.5, −3 to +`leave_push` ft/s).
     2. **The four-wide threshold:** it fired at lane 2.1+. **Now:** it fires only in the fourth lane and not moving
        in (rule 0.6 allows working in).
     3. **The turn decision:** my four-wide change had removed the press-or-tuck decision at the turn, so #5 kept
        pushing alongside until its budget ran out at 13.6 s, by which time #2 had the pocket. **Restored:** at the turn
        a leaver presses (near-match) or takes the pocket if nobody's in it, from any lane, otherwise settles. A
        pocket-seeker gives up only if the pocket is taken, it's stuck four-wide at the turn, or after `pocket_wait_s`
        8 s. The leave budget applies to lead-seekers only.
     4. **Coming over:** a rail horse charged up to the leader and blocked the seeker for 8 s. **Now:** a sitter eases
        `ease_out` when a horse clear ahead of it is waiting to come over and is held only by it (the mirror of
        173/196's "give room").

     **Result in race 1:** #5 takes the pocket by about 13 s, sits 2.2–2.9 lengths behind #1, and reaches the drive
     with reserve 9.5 vs the leader's 5.3.
     **Safety:** zero hard failures in 400 races; merge suite 9/9.
     **M (Part 1, 200 races per track):**
     - half trips 24/29/20/24/2, posts 29/37.5/18.5/10.5/2.5/2/0/0;
     - mile trips 44/28/13/13/2, posts 26/34/9/12/8.6/5/2.6/2.7/0/0.6;
     - rail leads at the half 59% / 39%.

     **Replay:** version 5.
200. **Patrick:** "The 20¾ win was on the results board," and he wants to see every horse's bars for the crop.
     **Margin bug (display, not engine):** the TV results board (`drawResults` in `mockups/replay_hd2d.html`, `marg`)
     treats `behind[6]` as seconds behind (`L = d / .2`). Both the lab replay and the live game's `story.py` (`fin`,
     lengths) store **lengths**. Half race 1's 4.17-length margin showed as 20¾.
     - **Lab copy fixed:** `v3_replay.py` swaps in `L = d`.
     - **Live fix pending:** the live page probably shows margins about 5× too big on its TV results board. That's a
       one-line change to the live mockup and needs Patrick's deploy approval. Not touched.

     **Field panel added to the test replay** (a Field button), one card per horse:
     - the four game bars from the lab traits, mapped to pips as 5 + 2 × trait / 0.4 (average 5; +1 spread = 7);
     - the game's colors (grey ≤3, yellow ≤6, green ≤8, iridescent 9–10);
     - Grit, marked hidden;
     - race-day form;
     - finish place.

     Checked in headless Chrome. Replay version 6.
201. **Patrick (2026-11-01): pacing rule.** "Every horse should behave in a similar fashion, where the driver knows what
     it has in the tank, and will always look to maximize its reserve, timing it to expire just as they cross the
     finish, or a little before." Also: "If it's crossing the finish line with 0 reserves and decelerating, that's a
     colossal failure on the driver."
     **Built:**
     - `R.afford_speed`: the fastest steady speed to the wire on E − margin, at the remaining turns' average curvature
       and present cover, capped at the ceiling the horse will have when down to the margin, so it isn't slowing at
       the line;
     - the driver never commands above it (`budget` 1, `budget_margin` 1, looks every 0.5 s);
     - `v3_card.py`, the joint scorecard.

     **M (scorecard, 100 races per track):**
     | Setting | Leader at 3/4 wins (half / mile) | Median margin | Reserve at the wire (median) | Empty and slowing, unforced |
     |---|---|---|---|---|
     | No budget | 32% / 37% | 3.1 / 3.5 | 0 | 4% |
     | Budget, margin 1 | 91% / 83% | 7.8 / 7.9 | 11–12 | 0% |
     | Budget, margin 3 | 79% / 50% | 5.2 / 5.0 | 3.3–3.9 | 0% |
     | Budget, margin 1, `fade` 0.15 | 72% / 43% | 4.0 / 4.1 | 1.0–1.3 | 0% |

     With margin 1, horses were capped at the near-empty ceiling (about 48 ft/s) and couldn't sprint, so they finished
     with 12 left.
     **Correction (my error, told to Patrick):** "best horse wins 18%" counted the best by gate + cruise + kick. Item 6's
     measure is the true best by reruns: **46%** without the budget, **51%** with budget + `fade` 0.15 (32 class
     fields × 24). Repeat 36% / 39% (target 45).
     **Committed (lab):** budget on, `fade` 0.15.
     **Bug fixed:** `afford_speed`'s steady-speed search stopped at its first failure, under-reading by a few ft/s
     (tired horses crawled at 37 ft/s).
     **Half race 1 still bad after the fix:** #1 wins by 4.5 s (about 26 lengths). At the 3/4 #1 had 8.0 reserve, the
     chasers 4.2–7.0, and the budget holds that gap all the way home.
     **Open safety regression:** 200 four-wide-on-turn steps in 400 races, not yet traced. The replay is not updated
     (still version 6, pre-budget).
202. **M: why the chasers have less than the leader (`v3_e_parts.py`, 30 half-mile races).**
     - The leader spends 2.2 on acceleration and 8.7 on uncovered air.
     - Positions 2–6 spend 3.0–6.3 on acceleration and 3.3–3.7 on air: they're out of the draft (more than 1.5
       lengths behind) 35–40 s even sitting in line.
     - The back two: 6.2 on acceleration, 4.3–4.8 on air, 47–53 s uncovered.

     **Read:** the drafting saving (about 5 units) is eaten by the following controller's speed churn and gaps opening.
     That, not the budget, is why leaders keep as much as the horses behind them.
     **Next:** steady following, holding a tight, stable gap inside the draft without braking and re-accelerating.
     Stop rule: two budget variants failed on margins and the leader share; back to Patrick.
203. **Steady following (Patrick: "Yes, fix following").**
     **M (`v3_follow_diag.py`):** mid-race sitters have a median clear gap of 5.5 ft (90th percentile 18–20 ft), are out
     of the draft 18–22% of the time, and brake away about 110 ft/s per race, 90%+ of it from the controller.
     **Tried:**
     1. A firmer controller: `follow_k` 0.5 ft/s per ft, 0.4 s look at the front horse's acceleration, a 1 ft dead
        band. Braking ×4 (470), a string instability.
     2. Screened gentler settings: `follow_k` 0.075–0.25, dead band 0–4 ft. Higher gain or a band means more braking;
        0.075 / 0 is no worse than before. Kept as the default (same as the old law, clamp ±3).
     3. `pace_rate` 0.5 ft/s per s on an unpressed pace-setter. Braking 103–111 (no material change), kept as harmless.

     **The decisive measurement (40 races per track), reserve at the drive by rank:**
     | Track | Leader | Pocket | 3rd | Rest |
     |---|---|---|---|---|
     | Half | 7.5 | 11.1 | 9.9 | 8.8 |
     | Mile | 6.8 | 8.3 | 9.0 | 9.2 |

     **On average the trip pays: followers reach the drive with more than the leader.** DECISIONS 202's reading (that
     following wastes the saving) was wrong for the average. Half race 1 is an outlier: #1's cruise is +1.06 (+2.6
     spreads), so it spends less at any pace, and under the budget it never comes back.
     **Read:** leaders win too often under the budget because the better-stocked pocket horse can't get out in time. The
     drive starts on the final turn, the half-mile stretch is 500 ft, and the first-over horse boxes it. That fits 174's
     traffic effect (about 20 points). **Stage C (stretch access) is the lever.** Stop rule: two following attempts
     with no gain; back to Patrick.

## Outcome-first (2026-11-01)

204. **Patrick: outcome-first design.** "If that requires a full rehash from the top down on stat categories/weights
     etc, the under the hood stuff is better hashed out between you and Astra. The presentation layer of how a horse's
     rating is shown to players is an afterthought."
     **Replaces "the engine races the actual horses" (spec principle, 2026-10-31):**
     - **Who wins:** decided by a transparent, designed model (stats, trip and form), with every Part 1 target as a
       dial.
     - **How it looks:** race3/drive3 choreograph the decided result; the story system is the fallback.
     - **Delegated:** stat categories, weights and model structure, to Claude and Astra, with experiments as evidence.
     - **Not yet:** presentation (bars and cards), decided later.
205. **Review 19 (Astra) on OUTCOME_SPEC, adopted.**
     **Model:** start order e = gate + form − c_post·(post − 1) + σ_s·z. The five contracted 3/4 roles come from
     **fixed** design rules (duel, pocket, first-over, followers, back).
     **Performance:** P = w_c·cruise + w_k·kick + A[track, role] + g·duel·(grit − rival's grit) + σ_ε·u, with
     effective traits = trait + form (form counted once).
     - No direct gate weight: gate earns places only through position.
     - Breaks are the manners curve with a fixed penalty.
     - About 19 fitted parameters; one role offset per track and the cruise + kick weight sum are fixed for
       identifiability.

     **Fitting:**
     - common random numbers, a moments loss that is zero inside tolerance bands;
     - one monotone post slope per track;
     - check the sensitivity of parameters, and validate on untouched seeds with K = 24 plus a high-K diagnostic.

     **Constraints:** repeat ≤ max p_i (so best horse is reported, not fitted); the favorite is measured by game odds
     after integration; a single margin scale may not satisfy both the median and the photo rate (check
     feasibility).
     **Contract amendment (gate):** the 0.05 floor (189) was a physics limit of the true-pace engine. Under
     outcome-first, gate's places-gained target returns to Patrick's 143 values (half 0.45, mile 0.20). Cruise, kick
     and grit are unchanged.
     **Phase 2 needs from the model:** positions and lanes at the calls, pace bounds, cover/park/box windows, duel
     partners and timing, workload budgets, break timing, then order, margins and clock.
206. **M (outcome model v4, first fit; differential evolution, 40 generations, untouched seeds):**
     - **Half (loss 4.4):** posts 20.2 → 8.6; trips 41/15/4/19/20; worth gate .56 / cruise .48 / kick .29 / grit .17;
       rail leads 34%, top three 71%; repeat 28%; best horse 45%; margin 1.85 lengths; photos 8%.
     - **Mile (loss 16):** posts flat at about 10%; trips 21/21/9/19/31; worth .37/.34/.63/.19; rail top three 37%;
       repeat 19%.

     **Conflict found (sweep of `s_eps` × `s_form` with the other half-mile settings fixed):** a 45% repeat comes with
     a worth total of about 2.0 places (contract 1.12). Both are set by the same ratio of traits to luck.
     **Decision (delegated, under the hood):** the balance contract's content is its **shape**, each trait's share of
     the total worth per track (half gate .40 / cruise .31 / kick .18 / grit .11; mile .21 / .21 / .46 / .12). The
     absolute size is set by the 45% repeat. The fit targets shares ±0.05.
     **Also widened:** `c_post` to 0.4, `g` to 5, `s_form` to 0.02. Flagged for review 20.
207. **M (outcome model v4, refit to shares; differential evolution, 60 generations; untouched seeds, 20,000 races plus
     400 fields × 24 reruns):** every target is inside its band on both tracks (loss 0.03 / 0.00).
     | Measure | Half | Mile |
     |---|---|---|
     | Wins by post | 19.8, 16.9, 14.6, 12.4, 10.9, 9.3, 8.3, 7.7 | 10.9, 10.3, 10.3, 10.5, 10.4, 10.0, 9.9, 9.7, 9.3, 8.8 |
     | Trips | 33/24/14/19/9 | 30/13/21/20/16 |
     | Worth shares (gate/cruise/kick/grit) | .36/.30/.22/.11 | .18/.24/.50/.08 |
     | Absolute places for +0.5 | .62/.52/.38/.19 | .53/.68/1.42/.24 |
     | Rail at the half (leads / top three) | 32% / 69% | 13% / 36% |
     | Repeat | 38% | 39% |
     | Best horse (reported) | 53% | 54% |
     | Margin median / photos | 0.90 L / 17% | 1.58 L / 11% |

     **Parameters:**
     - **Half:** c_post .095, s_start ≈ 0, ω .60, A lead 1.05 / pocket 1.12 / first-over .06 / followed 1.12 /
       back 0, g 4.8, s_eps .69, s_form .02, s_margin 1.56.
     - **Mile:** c_post .013, ω .33, A .41/.42/.03/.58, g 4.8, s_eps .34, s_form .02, s_margin 4.0.

     **Caveats:**
     - The repeat sits at the bottom of its band.
     - Start luck and form came out near zero: rerun luck is all in ε.
     - g is near its bound.
     - The mile post curve is flatter than the soft target, though inside ±3.
     - Fields are fixed at 8/10 starters (the live size mix is not applied yet).
     - Identifiability and sensitivity aren't checked yet (review 19, step 6).

     **Next:** review 20 on the share decision and identifiability; then phase 2, choreography (race3/drive3 deliver
     the decided trips, order and margins; report the realization rate).
208. **Identifiability (`v4_sens.py`):** ten of eleven settings are pinned down by the targets (singular values to
     about 0.1). The weakest direction is almost purely `g` (grit).
     **Review 20 (Astra): not ready to call fitted.**
     **Correction to my report to Patrick:** the half repeat 38% was outside its 39–51 band.
     **Measurement fixes adopted:**
     - the live field-size mix (wins per start);
     - best horse picked on half the reruns and scored on the other;
     - one-class rerun fields of 8 starters;
     - upsets on mixed fields (spread 0.55, the live mix);
     - "rail at the half" documented as the start order;
     - the rail and margin bands documented as our choices, not contract.

     **Design fixes:**
     - `g` fixed at 1.0 (at 4.8 a duel swung performance by about 2.7 units against cruise/kick's 0.4);
     - `s_form` fixed at 0.15 (form shapes the whole race);
     - new checks: how often extra gate costs places, and a duel audit.

     **The old fit on the corrected measures (half):** repeat 20%, best horse 28%, upsets 19%, extra gate cost places
     15% of the time, **duels in 93% of races**.
     **Duel rule changed:** the second horse presses only when its driver judges the duel worth more than the pocket
     (`A_fo` + g·(grit₂ − grit₁) > `A_pocket`). That ends forced presses and the gate penalty.
     **Running:** the refit in shares mode, plus the Pareto check: the same fit against the contract's absolute worths
     (`V4_ABS` = 1) to see what repeat it allows.
209. **M (refit on the corrected measures, untouched seeds):**
     - **Shares mode:** half loss 3.0 (repeat 34%, back 2%, grit share .02, gate cost places 10%); mile loss 1.3
       (repeat 36%, grit .03).
     - **Pareto check, the absolute contract** (`V4_ABS`): half loss 7.6, repeat 31%, first-over 0%; mile loss 23,
       repeat 22%, pocket and first-over 0%, upsets 15%.

     **Read:** the absolute worths can't coexist with the repeat target in this model. The shares decision (206) is
     supported by evidence, not just argument.
     **The audit had a bug:** "duels 91%" counted every first-over move. It now counts the second horse out pressing:
     11%.
     **Model pieces added** (each targets a measured miss):
     - `A_FO` 6: the first-over horse is mostly the one with the most stamina (less random reruns);
     - grit also counts when the first-over horse arrives alongside the leader (spec: "first-over alongside");
     - `k_close`: extra kick weight for followed and back horses (closers can win);
     - `b_depth`: a cost per place deeper in the line for back horses.

     **Gate check traced:** of the 14% of horses that lose places with +0.5 gate, most go from followed to back (they
     start ahead of the mover and lose its cover), then pocket to lead (exposed). That's "too quick for its own good,"
     which real races have. Reported as gains and losses, not forced to zero.
210. **M (outcome model v4.2; training loss 0.00 on both tracks; untouched seeds: 20,000 races, 400 class and 400
     mixed fields × 24 reruns):**
     | Measure | Half (loss 0.38) | Mile (loss 0.12) |
     |---|---|---|
     | Posts | 21.0, 17.7, 14.7, 12.1, 10.3, 9.8, 8.4, 7.6 | 12.4, 12.1, 11.2, 11.4, 10.8, 10.1, 9.6, 9.2, 8.7, 8.3 |
     | Trips | 42/21/13/17/7 | 22/15/14/25/24 |
     | Shares (gate/cruise/kick/grit) | .32/.33/.24/.11 | .25/.18/.48/.09 |
     | Rail at the half (start order): leads / top three | 33% / 71% | 18% / 46% |
     | Repeat | 39% | 37% |
     | Best horse (split halves) | 50% | 47% |
     | Upsets | 6% | 6% |
     | Margin / photos | 1.11 L / 14% | 1.48 L / 10% |
     | Extra gate: gains / costs | 45% / 16% | 47% / 19% |
     | Duels | 2% | 8% |
     | Worth total | 2.50 | 3.40 |

     **Misses:**
     - half: lead trips 42 (band ≤ 41), back 7 at the band's edge, repeat at the band's edge;
     - mile: repeat 37 (band ≥ 39).

     **Parameters:**
     - **Half:** c_post .106, s_start .026, ω .88, A lead .45 / pocket .35 / first-over −.48 / followed .33,
       s_eps .10, s_margin 3.5, k_close .70, b_depth .33.
     - **Mile:** c_post .036, s_start .004, ω .43, A .11/.22/−.27/.28, s_eps .14, s_margin 5.1, k_close .85,
       b_depth .17.
     - **Fixed:** g 1.0, s_form 0.15, A_FO 6, DUEL 0.15, P_NONE 0.10, N_FOLLOW 2.

     **Next:** phase 2, choreography. Review 20: a coarse segment plan (positions and lanes at the calls, pace bounds,
     cover/box windows, duel timing, workload budgets) and bounded per-horse capacities, with feasibility tested
     before rendering. Realization reported on order, margins, roles and believable pace.
211. **Phase 2, physics choreography: first measurements (`v4_choreo.py`; the model decides, race3/drive3 get a
     script plus bounded nudges).**
     **Nudges** (cruise + kick ±0.5, 6 correction runs; 6 half races): right winner 50%; top three in order 0%; margins
     0%; nudges at the cap in every race.
     **Scripted trips, realized at the 3/4** (20 races per track):
     | Decided trip | Half | Mile |
     |---|---|---|
     | Lead | 80% | 95% |
     | Pocket | 35% | 15% |
     | First-over | 12% (76% end up "followed") | 18% |
     | Followed | 64% | 64% |

     Field spread at the wire: physics 31–34 lengths vs the model's 10–13.
     **Read:** as review 20 warned, scalar nudges can't bridge a physics that strings the field out three times
     wider and misses pocket and first-over trips. Fixing that means fixing the physics behaviors that took the last
     week.
     **Stop rule:** two failed attempts; to Patrick, since it changes what replays look like.
     **Alternative found:** the live game's `story.py` is already a choreographer for an outcome-first design: given the
     finish order, times and trips, it builds positions and lanes at each call for the HD-2D replay ("the finish order
     and times are never changed; the story is how the field got there"). The outcome model can feed it directly.
212. **Patrick: "Story system now."** The outcome model decides; the story system draws the replay.
     **Built (lab only; live `story.py` untouched):**
     - `v4_story.py`: a variant of `story.build` that takes the model's decisions as given (start order, trips,
       finish order, margins in lengths, clock) instead of re-deriving them. Live `build()` rescales margins so the
       7th horse is 7 lengths back; the variant keeps the decided margins.
     - `v4_replay.py`: 6 half-mile + 6 mile races, unpicked. It reuses the lab replay page (art, buttons, Field panel,
       margin fix) with the race data and loader swapped to the live story loader's logic.
     - Clock: base time + 1.2 × the winner's edge over the field mean (provisional; the display map comes later).

     **Sample:**
     - **Winners:** from posts 2, 4, 5, 7, 8 and 9, on every trip type.
     - **Margins:** 0.15 (a photo) to 4.75 lengths.
     - **Clocks run about 1.3–2 s fast** (winners are above the mean by construction): to recentre at the time mapping.

     **Checked:** no script errors in headless Chrome. The page's loaded state is verified: 10 horses, decided margins,
     flow horses one lane out at the 3/4. Animation can't be checked headless (the earlier page behaves the same).
     **Replay:** version 7 (title "Outcome Engine Replay").
213. **Patrick's replay note (Half race 1, v7):** "at around 55 seconds the 5 horse pulls out, and makes an insane
     burst forward… shoots up to 3rd by 1:04."
     **Cause:** the model's first-over pick (most stamina among start ranks 2+) was 7th in line, 12 lengths back at the
     quarter. The story put it 4 lengths back at the half: 8 lengths in 29 s, with the lane change in the last 6 s
     before the call.
     **Fixes:**
     - **Model:** first-over comes from mid-pack (`FO_MAX` start rank ≤ 4 half, ≤ 5 mile; 0-based).
     - **Story:** at the half a mover has just pulled out (at most 2 lengths gained); at the 3/4, at most 3.5 more.

     **Refit (untouched seeds), all bands met on both tracks:**
     - **Half (loss 0.01):** posts 20.8 → 6.4; trips 41/16/15/19/8; shares .38/.28/.23/.10; rail leads 33%, top three
       70%; repeat 39%; best horse 48%; upsets 6%; margin 1.87 L; photos 8%; extra gate +47% / −13%; duels 5%.
     - **Mile (loss 0.01):** posts 12.5 → 8.4; trips 27/13/20/17/24; shares .23/.19/.50/.08; rail top three 44%;
       repeat 41%; best horse 52%; upsets 5%; margin 1.29 L; photos 12%; gate +46% / −14%; duels 12%.

     **Replay:** rebuilt and published as version 8. The largest mid-race gain by a mover is now capped.
214. **Race Lab (Patrick: rerun this race 100 times, then build a horse into the field).**
     - **Page:** the artifact https://claude.ai/artifact/1VD7EcfFE1kmr9eWjLdpc6 (source in the scratchpad; the model is
       copied to `v4/racelab_model.js`).
     - **Model:** a line-for-line JS port of `v4_outcome.race`. **Parity M (200,000 races per track, Half race 1 and
       Mile race 1 fields):** JS and Python win% agree within 0.1 point for every horse.
     - **What the page does:**
       - runs 100, 1,000 or 10,000 times with fresh form and luck;
       - shows a results table: wins, 2nd, 3rd, win %, top three, average finish, usual trip, median beaten
         margin, breaks;
       - **Build a horse:** name, five bar sliders 1–12 (bar = 5 + 2 × trait / 0.4), post (scratches the horse there or
         adds one up to 8/10).

     **Checked headless:** run 100, build into post 3, run again. A default all-7s horse won 47%, mostly first-over.
     **Noted:** Mile race 1 has a standout (post 5 wins about 86% over 200,000 runs).
216. **Patrick (2026-11-01): tiers come from the bars.**
     - "Manners won't count towards the stat weight. We have that as a stat still, but we don't weigh it in the horse's
       tier rating total."
     - "The bars are what makes the tiers. The bars are what estimates a horse's mile time."

     **So:**
     - a horse's estimated mile time, and its tier, is a function of its racing bars only (Speed, Stamina, Finish
       and Grit; not Manners);
     - today's live game does it the other way (tier from the estimated time, bars only loosely related; the save
       copy's tier medians of four-bar totals are S+ 28, S 25, A 23, B 21, C 17, D 13, overlapping heavily).

     **Open:** how the bars combine into the rating, equal or weighted by what each bar is worth in a race.
215. **Patrick's Race Lab finding:** a 6/8/6/7/6 horse won 43% at Speed 6 and only 47% at Speed 12. Traced: Speed
     only decided trips, and front trips stripped most of a horse's Finish credit (half ω .89; kick counted mainly for
     closers). From post 1, more Speed lowered the win chance (53% → 31%).
     **Fixes (Patrick: "speed gives options, never obligations"; "update the race lab with these fixes"):**
     1. **Finish counts for every horse:** ω ≤ 0.70.
     2. **Trips are chosen, not assigned:** in gate order each driver takes the best trip still open (lead, pocket,
        first-over from mid-pack or pressing from second, following cover, the line), valued A + kick terms + grit vs
        the leader − depth, with choice noise `s_choice` 0.1 (design). The first out may tuck and let the next one
        lead. This replaces the fixed role rules and the take-back patch.
     3. **The per-horse check is part of the fit:** fixed fields, one horse each, every bar +1, common random numbers;
        the penalty is any win-point drop beyond 0.5.

     **Path:**
     - the take-back patch (2.5% of cases bad);
     - driver choice with the old settings (Patrick's horse monotone at all posts);
     - the refit without the check (his curve broke again: post 4, 47% → 31%);
     - the refit with the check (below).

     **M (final refit, untouched seeds):**
     - **Half (loss 0.41):** posts 21.6 → 5.5; trips 43/17/12/10/17; shares .33/.35/.22/.10; repeat 40%; best horse
       49%; upsets 7%; margin 1.89 L; photos 8%. Per-horse check: 0% of cases bad (worst −0.2).
     - **Mile (loss 0.12):** posts 13.2 → 7.7; trips 28/13/13/19/27; shares .24/.20/.49/.07; repeat 37%; best horse
       47%; upsets 6%; margin 1.51 L; photos 10%. Per-horse check: 0% (worst −0.5).
     - **Patrick's horse (win % by Speed 4 → 12):** post 1: 30, 31, 31, 35, 36. Post 8: 5, 22, 48, 55, 55. Post 4: 31,
       46, 44, 42, 42 (a residual dip of about 4.6 points in that one field, where his horse replaces the field's only
       off-the-charts Speed horse; noted, not chased).

     **Race Lab v2:** JS port updated; parity within 0.3 point per horse (200,000 races per track); published.
217. **Patrick: the tier rating is weighted by worth.**
     **Weights:** from the fitted model's per-horse check (average win points per +1 bar), mixed by the live race
     count (half 3,700 / mile 3,000): **Speed .30, Stamina .26, Finish .32, Grit .12**; Manners 0.
     Rating = Σ weight × bar (5 = average).
     **M (live save copy, 667 racing horses 3+; grit set to average because the live game has none yet; today's tier
     shares kept):**
     - **Lines:** D below 3.80, C below 4.74, B below 5.40, A below 5.94, S below 6.54, S+ from 6.54.
     - **Movement:** 437 (66%) keep their tier, 122 move up, 108 move down.
     - **New tiers' average Speed / Stamina / Finish:** S+ 7.2/6.7/7.5, S 6.5/5.9/6.7, A 5.7/5.6/6.0, B 5.3/4.8/5.2,
       C 4.0/4.1/4.5, D 3.0/3.0/3.0.

     **Open (Patrick):** tier sizes. Today S+ is 7% of racing horses; the rating can make it rarer. The pip scale (the
     presentation) decides whether elite bars reach 9–10.
     **Rollout note:** a third of existing horses would change tier. The engine lab's launch scenario is a fresh world
     (memory: harness-engine-lab), where that doesn't matter.
218. **Patrick: "Speed needs to be weighted heavier, at least when displayed… displayed Speed/Stamina indicate to a
     player most of the story, with the other stats filling in smaller gaps."**
     **Agreed design (presentation):**
     - **Speed (headline bar):** gate and kick blended by worth (.30 / .32), about 62% of what wins.
     - **Stamina (headline):** cruise, about 26%.
     - **Style:** an early ↔ late marker (kick bar − gate bar; "fires off the gate" / "comes late" / "even").
     - **Grit and Manners:** small bars.
     - **Rating:** .30·gate + .26·cruise + .32·kick + .12·grit.

     Honest by construction: the headline bars carry about 88% of the real worth. Making gate itself worth more in the
     engine was advised against (that's the balance fought all week).
     **Mockup:** `mockups/headline_card.html` and `.png`, outside the game: 5 lab horses plus a made-up S+.
     **Still open:** S+ size (today 7% of racing horses); the pip scale (whether elite bars reach 9–10 in the live
     game).
219. **Patrick: "rarer S+ and a top tier that's like… galaxy rare. If 2% are S+ then the Galaxy tier should be 0.1%."**
     **Tiers by rating (.30 Speed + .26 Stamina + .32 Finish + .12 Grit; Manners not counted).** Lines from the live
     save copy (667 racing horses; rating mean 5.15, spread 1.01, normal fit):
     | Tier | Rating | Share |
     |---|---|---|
     | **Galaxy** | 8.27 and up | top 0.1% (one horse today, 9.40) |
     | **S+** | 7.23 up to 8.27 | top 2% (empirical top 2% starts at 7.00) |
     | S | 5.94 up to 7.23 | about 18% (S takes the old S+ band below 7.23) |
     | A | 5.40 up to 5.94 | unchanged |
     | B | 4.74 up to 5.40 | unchanged |
     | C | 3.80 up to 4.74 | unchanged |
     | D | below 3.80 | unchanged |

     **Default chosen (not stated by Patrick):** S absorbs the shrink; flag it if he wants different tier sizes.
     **Mockup:** `headline_card.html` / `headline_card_galaxy.png`. Crown of Lexington (8.5) is Galaxy, with a
     starfield card, a glowing edge and a ✦ badge; Paddock Rumor (7.34) stays S+. The final badge and card art follow
     the style skill: pixel art from the image tools, not CSS shapes (the CSS here is placeholder).
220. **Race Lab v3 (Patrick: "yes", plus "we also need a stronger test group around the built horse. Put them in a
     class of A horses.").**
     - **Display:** the field, results and builder show the headline card (Speed = gate/kick blend, Stamina, Style
       lean, small Grit/Manners), the rating and the tier badge (Galaxy ✦ to D).
     - **Builder:** sliders for the underlying gate speed, stamina, finish speed, grit and manners; the preview updates
       live (name included).
     - **A-class fields:** for each track, every opponent is rated A (5.40–5.94), with varied builds drawn by
       rejection from a seed. "Draw a new A field" re-seeds.

     **Checked headless (2,000 runs each, horse in post 3):**
     | Horse | Rating / tier | Field | Win % |
     |---|---|---|---|
     | 9s on the racing bars | 9.0, Galaxy | Half A field | 99% |
     | 9s on the racing bars | 9.0, Galaxy | Mile A field | 92% |
     | 7s | 7.0, S | Half A field | 63% |

     **Caveat:** tier lines are world-scale, and the outcome model has no class term yet. In an A field the opponents'
     higher bars are the whole difference.
221. **Patrick: "Manners won't be displayed then. We want to keep the bars to 4 total."** Manners stays a hidden stat
     (break risk only; not in the rating).
     **Card:** Speed and Stamina (headline), Grit (small), and Style (the early ↔ late marker).
     **To confirm:** that Style counts as the 4th element, versus a 4th bar.
     **Grit is not shown as "Finish":** finishing speed lives in headline Speed and the Style lean (220–221 exchange).
     **Suggested:** a hint for very low Manners (a trainer note such as "can break"), since breaks would otherwise be
     invisible to players.
222. **Patrick (supersedes 221's card): "We need 4 bars. Speed / Stam / (Finish) Grit / Manners. We can keep showing
     them as the big 4."**
     **Card:** four equal bars.
     - **Speed:** gate and kick blended by worth (finishing speed lives here).
     - **Stamina.**
     - **Grit:** in the slot the live game's Finish bar had.
     - **Manners:** shown again; still not in the rating.

     The Style (early ↔ late) line stays as a note under the bars, not a bar.
     **Rating unchanged:** .30 gate + .26 stamina + .32 kick + .12 grit.
223. **Updated to the big four (Patrick: "yes, update both").**
     - **Mockup:** `mockups/big_four_card.html` / `.png`: four equal bars (Speed blend, Stamina, Grit, Manners), a
       style note under them, rating and tier (Crown of Lexington is Galaxy, with the placeholder starfield).
     - **Race Lab v4:** the same four bars in the field list, results and builder preview; A-class fields note
       "Every opponent rated A."
224. **Patrick: "A horse like Tally Ho seems to win more often than Paddock Rumor. Talk through this." Then: "Yes,
     cut and refit."**
     **Traced (Half race 1, 100,000 runs):** Tally Ho Tess (gate 4, stamina 5, finish 8, grit 10; rating 5.9) won 52%;
     Paddock Rumor (gate 11, stamina 6, finish 6, grit 3; rating 7.3) won 16%.
     - Paddock Rumor led 97% of the time; Tally went first-over 55%.
     - When they met head and head, Tally won 91% and Paddock 0%.
     - **The grit swing was ±1.24 performance units, against one stamina bar's 0.137.** A single fight was worth about
       18 bars of stamina. g = 1 was my design value (208), set far too high.

     **Changed:**
     - `g` 1.0 → 0.25 (a 10-vs-3 grit fight is worth about 2 stamina bars);
     - grit's worth share target 11–12% → 5%;
     - refit.

     **M (untouched seeds):**
     | | Half (loss 0.27) | Mile (loss 0.03) |
     |---|---|---|
     | Posts | 20.1 → 6.0 | 12.8 → 8.4 |
     | Trips | 40/27/11/16/7 | 28/13/16/20/22 |
     | Shares (gate/cruise/kick/grit) | .36/.34/.25/.04 | .23/.20/.55/.03 |
     | Repeat | 36% (just under 39) | 38% (just under) |
     | Best horse | 46% | 48% |
     | Upsets | 6% | 7% |
     | Margin / photos | 1.67 L / 9% | 1.44 L / 11% |
     | Per-horse check | 0% (worst −0.3) | 0% (worst −0.0) |
     | Extra gate costs places | 4% | 3% |

     - **Half race 1 now:** Paddock Rumor 48%, Tally Ho Tess 14%, Silver Furlong 20%.
     - **Patrick's horse:** win % rises with Speed from every post (post 4: 35, 49, 67, 73, 74).

     **Rating weights (from the per-bar win gains, by race mix):** finish .391, stamina .304, gate .242, grit .064.
     **Tier lines (live save copy):** Galaxy ≥ 8.49, S+ ≥ 7.38, S ≥ 6.03, A ≥ 5.46, B ≥ 4.73, C ≥ 3.74, D below.
     **Race Lab v5:** the new settings, weights, lines and A band; JS parity within 0.2 point.
     **Not updated:** the `big_four_card` mockup ratings, which still use the old weights.
225. **Patrick's idea, not decided: a replay library.** Authored or curated cinematic replays per scenario; the model's
     result is cast into the best fit.
     **Sizing given:** every finish order is 8! = 40,320 (half) and 10! = 3.6 M (mile). Keying on the winner's post ×
     trip × margin type gives 120 / 150 keys; at 3–5 variants each, about 500–750 replays per track.
     **Proposed:** the 2nd and 3rd and the rest are fitted procedurally; the library is generated offline by
     race3/drive3 scripted toward each key, filtered for quality, with samples for Patrick's approval.
226. **Replay library v1 built (Patrick: "races that aim to look good cinematically first, then a field that fits").**
     **Measured: physics can't make the library.** Today's race3/drive3 races string out to about 21 lengths by the quarter
     (spread forms between 300 and 1320 ft as outside horses drop in single file); no setting tried moved it.
     **Choreography instead (`v5_choreo.py`).** A story is a formation plan (rail line of leader, pocket and the rest; an
     outer flow of the two horses that couldn't fold in, first-over then its follower), rolled at set points, then a
     stretch move. A guided follower drives each horse at the leader's real quarters: eased speed, whole-lane moves only
     when the strip is clear, folding in as room allows, checking off behind traffic.
     **Every kept variant is checked:** no two sulkies overlap; no 2-s burst over 6.5 ft/s before the stretch; field
     within 13 lengths at the quarter; every horse within 1 length / 0.4 lane of its plan at each call; the scripted
     winner and runner-up finish 1-2. Pass rate about 17/30 per story; field about 10.7 L at the quarter, bursts about 4 ft/s.
     **Stories (half-mile, 8):** wire to wire; pocket trip out the passing lane; first-over grinds it out; followed cover
     swept wide; from last, wide; head-and-head photo. Two variants each, on the lab replay page (artifact AY8eReomwRTr7JkeZGJZSZ).
     **Fields (`v5_fit_field.py`):** cross-entropy search for 8 one-class horses (ratings within 1.0 of the field's
     average; within 0.6 is much worse) that the outcome model sends down the replay. Fresh-race results, A variants:

     | Story | Winner on that trip | Whole replay (with runner-up) |
     |---|---|---|
     | Wire to wire | 57% | 45% |
     | Pocket trip | 46% | 34% |
     | First-over | 40% | 18% |
     | Photo (same shape as first-over) | 40% | 18% |
     | Followed cover | 29% | 11% |
     | From last | 25% | 0% |

     **Hypothesis, not tested:** the low rates for late-closing stories are the model (closers rarely win in one class),
     not the search. The search pushes Grit high because it's cheap in the rating; worth a cap before fields are shown.
227. **Library page follows the live replay; fields on all twelve; Grit capped.** The lab page was a stale copy of the
     replay (Patrick saw older-looking horses); `v3_replay.build_page` now builds from today's `mockups/replay_hd2d.html`
     and copies every art file it asks for. Small-oval camera fixes (low final-turn hedge, odds board hidden for the
     infield shot, video board pulled inside the rail) switch on only when the oval radius is under 300 ft; live is untouched.
     Field search: Grit held within one spread (bar 7 at most). Measured, fresh races, winner on the scripted trip
     (A / B): wire 54/57%, pocket 49/56%, first-over 23/29%, sweep 30/38%, from last 22/18%; whole replay incl.
     runner-up: 41/37, 32/38, 12/16, 14/16, 0/6%.
228. **Passing lane drawn properly in the library; Patrick: "looks good now".** The lab adapter had the passing lane off,
     so the rail never swung in and the pocket horse ran through it. Library races now set it on. The pocket story wins
     by 2.2–3 lengths so the winner can angle back to the rail as the lane closes past the wire; the overlap check now
     runs to 150 ft past the wire. Measured: every horse in every kept variant stays at least 3.75 ft off the inside rail
     from 3,000 ft on.
229. **Casting v1 (Patrick: "Casting real results").** `v5_cast.py`: the outcome model decides the race; the caster
     choreographs exactly that race. The model's trips set the formation (single file on the rail; first-over pulls out
     after the quarter, its followers a call later); its finish order and margins set the stretch, planned from where
     the horses really are at the 3/4 (two-pass), each horse going a lane wider than anyone ahead or alongside that it
     beats; the pocket horse that beats the leader uses the passing lane. Kept only if it passes the library checks AND
     finishes in the model's exact order.
     **Measured:** 12/30 and 10/30 fresh half-mile races cast exactly (about 35-40%), about 7 s each. Races cast on the
     first try or not at all: success depends on the result, not on luck. Weakest: photos (0/3, then 1/3), pocket and
     sweep (1/5 each). Burst check now starts past the gate fold (400 ft); quarter spread limit 15 L (single file).
     **Tried and dropped:** easing horses onto exact marks over the last 300 ft (pulled horses into the one in front;
     5/30). Review page: artifact HpXtajpZRDZJv2Z3sjKxA2.
     **Open, Patrick's call:** what race night shows when a race can't be cast.
     **Larger sample (60 races, seed 607):** 18/60 cast (30%). By the winner's story: wire 8/19, pocket 7/15,
     first-over 1/11, sweep 1/6, photo 1/6, from last 0/3. First-over is the weakest here, unlike the 30-race batches.
230. **Patrick: "Fallback, keep improving."** On race night a race the caster can draw gets its cast replay; any other
     race keeps today's replay. Casting keeps improving, off-the-pace trips first (first-over 1/11 is the biggest gap).
231. **Casting fixes; ground-saving closers (Patrick: a savvy driver saves ground).**
     Casting, same 60 races (seed 607): 18 → 27 → 43 → 36/60 legit. Fixes: followers pull out once first-over is a
     sulky's length clear (was 17.5 ft); closers plan around every horse they beat, however far ahead; a beaten leader
     holds until the passing lane opens; a horse finishing within ~2 L of one in front in its lane goes a lane wider;
     the pocket horse waits to cross back until the rail is clear and the beaten horses pull up harder past the wire.
     The 43 included 10 races where a horse ran through the closing rail: the replay's inside rail (passing lane
     included) is now part of every check, and the pocket horse takes the passing lane only if it beats the leader by
     2.4 L or more (otherwise it comes out round him). 36/60 is the honest number.
     Closers (library "from last" and wide cast closers): they sit in the second lane, go three-wide only when a horse
     in front in their lane is in the way, and tuck back in when there's room. Library closer now moves three-wide at
     about 4,800 ft instead of from the 3/4. Closer fields refit: winner on trip A 6% / B 22%.
     **Patrick on the ground-saving closers: "Yes, that's it."**
232. **Cast rate work; library rebuilt through the caster (Patrick: parked all the way, only a top-grade horse lasts).**
     `v5_cast_why.py` classifies failures. Kept: lane-plan settling (whoever must pass someone runs wider, iterated);
     a burst check through the drive (9 ft/s over 2 s). Tried and backed out: narrow passing-lane wins with beaten
     horses pulling up, "everyone eases together" past the wire, slot-in behind the horse ahead (each made overlaps or
     rail hits worse; the library pocket story fell to 1/30). Same 60 races: 36 → 42/60 with settling; the caster now
     also runs the shape check (nobody stuck parked or out of place at 1/4, 1/2, 5/8), which costs 7: **35/60 (58%)**.
     Library: stories are scripted results cast like real races (`library_result`): single file, first-over pulls out
     after the quarter; first-over finishes 5th in wire/pocket/closer, 2nd in sweep, 1st in first-over/photo. No rail
     horse is off the rail early in any of the 11 replays. Wire to wire has only one clean variant in 120 tries (no B).
233. **Library button bug; builds from committed code; messier starts (Patrick: the fold "looks orchestrated").**
     Buttons were numbered as if every story had a B (wire had none), so Pocket B opened First-over B: each button now
     points at its own replay. The builder reads the committed replay page and art (`git show HEAD:`), so unshipped
     work in the checkout can't leak in; the gate-stagger patch now matches the line by name.
     Pocket B review (Patrick): everything after the start looks good. The start: each horse now leaves its own way
     (how hard it leaves follows its start order with scatter; how fast it angles in, when it drops over; a quarter of
     them hang wide a few strides). A first try (big drop-backs by 300 ft) failed the burst check; the drop-back is now
     spread evenly to 820 ft and pass rates are back to before. The first-over and follower captions fire when each
     horse actually pulls out. Fields refit; wire to wire has its B back.
     **Patrick on the new start: "Looks right."**
234. **Paused by Patrick (2026-11-01) for a live deploy of visual changes.** State at pause:
     - Casting: 34-35/60 (about 58%) with the rail and shape checks. Single-try failures on the 60-race set (seed 607):
       order 18, shape at the quarter 11 (a rail-line or follower horse not folded in yet; likely the hang-wide starts),
       burst 4, overlap 1. Next experiment, not run: HANG=0 vs 0.25 (env switch was about to be added).
     - In the code, untested by Patrick: past-the-wire fan-out (the beaten rail horse and anyone alongside outside it
       drift a lane so a passing-lane horse can cross back; cut rail hits 7 → 1, no net cast gain); retries vary the
       stretch plan (PLAN_VARY, no gain); passing-lane minimum is DIVE_MIN default 0.8 L.
     - Library (artifact AY8eReomwRTr7JkeZGJZSZ, v11) is the version Patrick approved: messier starts, own-replay buttons.
     - Nothing from the engine lab touches live.
235. **Patrick: bring the new engine to the current live world (option B), all picks as proposed (2026-11-02).**
     1A rank-preserving stat conversion (early speed → gate, stamina → cruise, late speed → finish, gait → manners;
     durability stays as soundness); 2A grit seeded from each horse's durability and gait genes; 3A tiers come from the
     bars, no grandfathering — Patrick gets the full list of tier changes by barn before the switch; 4A shadow race
     nights on a copy for about a week, then a scheduled switch on a race-night boundary with a save backup; 5A cast
     replays where they work, today's replay otherwise; 6A breeding switches too (genes convert with the same mapping,
     grit inherits, foals in the shed convert). Purses, entries, program, market, names, ownership, records unchanged.
236. **Conversion v1 (`v6_convert.py`, live save copy 2026-11-02; report `v6/tier_changes.md`).**
     Bars stay on the live pip scale made continuous (each a rising function of the live stat: standing preserved).
     Speed = gate and finish blended (.242/.391); Grit seeded from durability and gait potential (z-scored, given the
     stamina bars' spread). The approved fixed lines (Galaxy 8.49 …) were measured on whole-number pips; on continuous
     bars they put 36% of racing horses in S, so lines are re-derived from the approved SIZES on today's racing horses
     3+: Galaxy 10.01, S+ 7.55, S 6.59, A 6.01, B 5.25, C 4.09.
     **Measured:** racing 3+ (661): 410 keep their tier, 112 up, 139 down. Retired (rated at prime): most fall (today
     890 of 1,526 are S+; new: S+ 69, S 376, A 461, B 463): today's retired tier is a career-high public estimate,
     inflated by its noise. Two-year-olds on the world scale fall to C/D (today they're judged within their age group).
     Player barns: 3 (Patrick 17 of 24 change, mostly retired S+ → S; LUCKY 7 FARMS 9 of 21; Doo Dynasty 3 of 4).
     Northern Star (all bars 10) is the one Galaxy.
     **Open (Patrick):** two-year-olds world scale or within their age group.
237. **Patrick: two-year-olds are tiered within their age group.** Same tier sizes as the racing horses 3+, measured
     on the two-year-olds' own ratings (lines Galaxy 5.61, S+ 5.36, S 4.18, A 3.26, B 2.42, C 1.66). 67 of 122 keep
     their tier; Patrick's Clever Frost and Harbor Oak stay S. Report regenerated (`v6/tier_changes.md`).
238. **Outcome engine wired into race night behind a switch (`outcome.py`; `circuit.ENGINE`, env TD_ENGINE=outcome;
     default stays today's engine). Not deployed.**
     Same contract as sim.race: finish order, trip text in the chart caller's words (story/replay keep working),
     raw_time and clock. Inputs are the stats sim.race races on (training, freshness, tonic, driver), made bars, then
     model units at K = 0.36 per bar: live fields differ by about 1.1 bars a stat (385 recent fields), the model was
     fitted on 0.4-unit fields. Times: the field averages what sim.race would run (ratings stay on today's scale); the
     spread is the model's margins at a fifth of a second a length. Pure Python (no numpy in the game).
     **Shadow v1 (`v6_shadow.py`, 345 real fields × 20 runs):**
     | | Favorite (today's est) wins | Best by new rating wins | Post 1 | Margin median | Photos |
     |---|---|---|---|---|---|
     | Half, today | 39% | 37% | 22% | 3.3 L | 5% |
     | Half, outcome | 34% | 38% | 20% | 1.8 L | 9% |
     | Mile, today | 39% | 38% | 15% | 3.2 L | 5% |
     | Mile, outcome | 30% | 42% | 10% | 1.8 L | 8% |
     Winner times within 0.6 s of today's. The tote still prices off today's estimate, which the new engine doesn't
     use: odds pricing must move to the new rating before the switch. Mile front-runners win less than the lab
     targets on real fields (lead 16% vs 25%); to examine in the shadow week.
239. **Patrick: Northern Star sets the records; his marks are the standard everyone else shoots for (2026-11-02).**
     Context: his last six starts all clocked 1:47.4-1:47.5 (the clock floor), and the story system compresses
     margins (his 4.6 s win showed as 4¾ L). Asked which plays best on replay: true margins and no ceiling a real
     horse can hit (records only land as moments if they're rare and breakable).
     **So, for the new engine:** true margins (no story compression; times come from the field's time minus the
     model's margins, so board, clock and picture agree); the clock floor goes just past Northern Star's best, so only
     he can approach it: his runs set each track's record, and those records are the marks the rest of the world
     chases (shown as the track record to beat). Ordinary top horses stay well clear of the floor.
240. **Outcome engine LIVE (Patrick: "Just make it live now", option A), deployed 2026-11-02 06:36 UTC, commit 442fd36
     (engine change in 1390fb6).** Shadow week skipped at Patrick's call.
     - Race night decided by `outcome.py` (circuit.ENGINE default "outcome"; rollback: TD_ENGINE=live and restart).
     - Times: the bars estimate the mile time: winner = 130.94 − 2.733 × rating (+ a night's variation, + 2 s on a
       half), the rest = winner + margin at 0.2 s/L. The story shows true margins (no 7-lengths compression).
     - Clock floor 107.4 → 100.5: Northern Star wins his last field 499/500 by ~9½ L in 1:42.3–1:45.1 (median 1:43.6);
       nobody else gets near the floor. Today's tier counts identical under either floor.
     - Tote prices off the card's rating: weight e^(1.9 × rating), fitted by likelihood to outcome-engine winners on
       339 real fields.
     - Dry run on a live save copy: tonight's 84 races, the close, tomorrow's draw (79) and those 79: night checks
       passed both nights. Winning margins median 1.9 L, 7 photos in 84; winning times median 1:55.0.
     - Shipped with it: breeding-shed tier icons, entry sheet (own races first, claimers under their own heading).
     - Backups: server /opt/trotdynasty/save.before-outcome-engine-20261102-0134.pkl and a copy in the scratchpad.
     - Verified: login page 200, service active, engine "outcome" and floor 100.5 on the server, clean start log.
     **Not yet:** the big-four card and new tiers on the pages (horses still show today's bars/tiers), breeding on
     the new stats (the engine converts live stats each race, so breeding still works), cast replays (replays are the
     story system's, now with true margins). The deploy commit also carried the whip-overlay session's untracked
     runner2 art (unused by the game).
