# Review 17 brief: front-runner dominance and the pace regime (race3 v3 lab)

Context: race3.py (physics) and drive3.py (driver) attached. Traits are hidden Normal(0, 0.4) per horse: gate, cruise,
kick, manners, grit; race-day form adds one N(0, 0.33) draw to gate, cruise and kick. Part 1 targets (CONTRACTS.md):
- winning trips at the 3/4: half lead/pocket/first-over/followed/back = 35/22/15/15/13; mile 25/18/17/20/20;
- wins by post falling gently (half 18.6 -> 5.9; mile 13 -> 7);
- the stat balance: places gained for +0.5 in a trait, half gate .45, cruise .35, kick .20, grit .12;
  mile gate .20, cruise .20, kick .45, grit .12 (±0.08);
- clocks half 115.9 s, mile 113.4 s.
Rule from the owner: the engine races the actual horses; fix behavior or physics, never add bonuses (no post buffs).

## Measured (200 races per track unless noted)
1. Old settings (lead paces at its held speed, +0.5 ft/s on the mile, 1.6 ft/s breather in Q2): balance and clocks
   on target, but leaders win 72-76%, pocket 3-24%, closers from the back 2-4%; mile posts 5-10 never win.
2. Diagnosis:
   - Driver bugs fixed: a start chain stopping outside horses; no-one-leads case; 5 simultaneous first-over moves;
     a turn deadlock where tight sitters could never pull out.
   - `fade` 0.3 -> 1.0 changed nothing.
   - At the drive, sitters are at the reserve cap (E 18/18) and the leader at 16; below threshold, saved effort
     refills at `recover` 0.3, so sitting buys about 2-3 reserve units over a mile.
   - A tighter line (`T_REACT` 0.05) changed nothing.
3. Hard pace (`lead_push` 3 ft/s above held speed, every race), clocks refit with `pace_k` 1.094, `c_turn` 0.00034:
   - half trips 32/11/35/20/2, mile 43/8/26/22/1;
   - posts 5+ still almost never win; median margin 3.1-3.4 lengths;
   - BUT the balance collapses: half gate -0.02, cruise +0.65, kick 0.00, grit .11; mile gate -0.12, cruise +0.64,
     kick +0.21, grit +0.24. Reserve at the drive is 0.31 (half) / 0.54 (mile) of the cap.
4. Pressure-driven pace instead (soft unpressed pace, `dig` 3, `duel` 0.5): leaders still win 62-82%.

## Questions
A. Is "the race pace is above the leader's threshold" the right physical regime to rely on for realistic trips? Or
   is there a better structural cause I'm missing (e.g. the `recover` asymmetry, the reserve cap, pace variance)?
B. Under a hard pace, what's the cleanest way to restore gate and kick worth without bonuses? Candidates: a bigger
   `e_max` with lower `p_cruise`; kick acting on acceleration as well as top speed; pace hardness varying by race
   (who leads, pressure) instead of a constant.
C. Outside posts: mile posts 5-10 win ~0% in ten-horse fields (320 ft to the first turn; lanes 7 ft; post 10 starts
   63 ft out). What's the most defensible fix: gate geometry (two trailers behind posts 1-2), a longer run to the
   first turn, or driver behavior (outside leavers taking mid-line spots)?
D. Name the 2-3 cheapest experiments that would tell these apart. Be blunt; agreement isn't evidence.
