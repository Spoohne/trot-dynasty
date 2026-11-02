# Review 20 brief: outcome model v4, fitted

Model and fitting per review 19 (v4_outcome.py attached). Two things to review.

## A. The shares decision
A sweep (other settings fixed) showed a 45% rerun repeat comes with a total worth of about 2.0 places per +0.5 (sum over
gate, cruise, kick, grit). The contract's absolute values sum to 1.12. Both are set by the ratio of traits to luck, so
I took the contract's content to be its shape (each trait's share per track) and let the 45% repeat set the scale. The
fit targets shares ±0.05.

## B. Fitted result (untouched seeds: 20,000 races; 400 fields × 24 reruns), every target inside its band
- **Half:** posts 19.8, 16.9, 14.6, 12.4, 10.9, 9.3, 8.3, 7.7 (target 18.6 → 5.9); trips 33/24/14/19/9
  (35/22/15/15/13); shares .36/.30/.22/.11 (.40/.31/.18/.11); absolute .62/.52/.38/.19; rail leads 32%, top three 69%;
  repeat 38%; best horse 53%; margin median 0.90 L; photos 17%.
- **Mile:** posts 10.9 → 8.8 (soft target 13 → 7); trips 30/13/21/20/16 (25/18/17/20/20); shares .18/.24/.50/.08;
  rail top three 36%; repeat 39%; best horse 54%; margin 1.58 L; photos 11%.
- **Parameters (half / mile):**
  - c_post .095 / .013; s_start ≈ 0 / .04; ω .60 / .33;
  - A lead 1.05 / .41, pocket 1.12 / .42, first-over .06 / .03, followed 1.12 / .58 (back 0);
  - g 4.8 / 4.8 (near its bound); s_eps .69 / .34; s_form .02 / .02; s_margin 1.56 / 4.0.

## C. Identifiability (finite differences, targets scaled by tolerance)
Singular values: half 2.7 … 0.18, 0.11, 0.05; mile 2.3 … 0.21, 0.15, 0.04. The weakest direction is almost purely g in
both. Plan: fix g as a design value.

## Questions
1. Is the shares reading defensible, or should the absolute contract be kept and the repeat target given up?
2. Start luck and form came out near zero, so rerun luck is all in ε. Any reason that's bad for the game (form is meant
   to be "how it's going today")? Should s_form be fixed at a design value?
3. Anything here that will make phase 2 (choreography) hard? Phase 2 plan: map roles to drive3 aims (lead → top,
   pocket, first-over or press, followed, back); solve a per-horse hidden capacity offset (cruise/kick in physics)
   iteratively so race3's finish matches the decided order and margins; report the realization rate (order, margins,
   3/4 roles); fall back to the story system.
