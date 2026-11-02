# Part 1 measurement contracts (frozen before tuning; DESIGN_V3 §11.1, review 13)

Every Part 1 check is measured exactly as written here. Changing a definition is logged in DECISIONS.md with its
reason, never done quietly to make a number pass. Engine, driver, field generator and seeds are recorded with each
report.

## Fields
- **Traits:** five traits per horse, each Normal(0, 0.4), independent. This is the lab's "one class".
- **Field size:** drawn from the live game's mix (read-only save copy, 2026-10-31):
  - half-mile: 8 starters 90.8%, 7 4.6%, 6 2.2%, 5 0.8%, 4 0.7%, 3 0.5%, 2 0.5%;
  - mile: 10 starters 87.9%, 9 2.4%, 8 2.8%, 7 2.0%, 6 1.2%, 5 1.1%, 4 0.5%, 3 1.0%, 2 1.0%.
- **Posts:** 1 to n, in random order of horses.
- **Race-day form:** each horse's traits for a race are its base traits plus a fresh draw for that race (`form_sd`,
  item 7's rerun protocol). Breaks on at the calibrated manners curve (DECISIONS 163). DT 1/16.

## The ratings the checks use
- **Expected chance `p_i`:** a horse's win probability in that field and draw, before form is known. Estimated as
  its win share over K = 24 reruns of the same field and posts, each with fresh race-day form and fresh random
  streams.
- **True best:** the horse with the highest `p_i`.
- **Favorite:** the horse the public would make favorite. The lab has no betting public, so it uses `p_i`
  (favorite = true best). Items 4 and 6 are then told apart by their populations; see item 4.
- **Bottom third:** the horses ranked in the bottom ⌈n/3⌉ by `p_i`.

## Item by item
1. **Half-mile wins by post:** wins per start by post, over races drawn from the half-mile field-size mix.
   - Target: Patrick's curve 18.6, 14.9, 12.8, 12.0, 10.0, 7.6, 7.1, 5.9.
   - Tolerance: ±3 points per post, and the curve sum within ±3.
2. **Mile wins by post:** wins per start by post over the mile mix.
   - Target (2B, soft): 13, 12, 11, 11, 10, 10, 9, 9, 8, 7.
   - Tolerance: ±3 per post. It must fall from the inside to the outside.
3. **How winners get there:** classified from the winner's actual path at the three-quarter call:
   - **on the lead:** first at the 3/4 call;
   - **pocket:** on the rail line (lane < 0.5), directly behind the leader, within 2.5 lengths;
   - **first-over:** outside (lane ≥ 0.5), within 5 lengths of the leader, with no horse within 3 lengths ahead in
     its band;
   - **followed cover:** outside, with a horse within 3 lengths ahead in its band;
   - **from further back:** everything else.

   Targets (3A):
   | Trip | Half | Mile |
   |---|---|---|
   | Lead | 35 | 25 |
   | Pocket | 22 | 18 |
   | First-over | 15 | 17 |
   | Followed cover | 15 | 20 |
   | Further back | 13 | 20 |

   Tolerance ±6 each.
4. **Favorite's win rate:** the share of races won by the betting favorite, priced by the game's own odds-making from
   the information players see. **Amended (Patrick, 2026-11-01, DECISIONS 169).** Target 35–40%. It is measured once
   race3 is wired into the game. Until then the lab reports the true best's win rate on mixed fields (traits
   Normal(0, 0.55), the live field-size mix) as a reference only.
5. **Upsets:** the share of races won by a bottom-third horse, on the item-4 population. Target about 1 in 12
   (8%), ±3 points.
6. **Best horse:** the true best's win rate and top-three rate in one-class fields (traits Normal(0, 0.4), 8
   starters). **Amended (Patrick, 2026-11-01, DECISIONS 167):** item 7's 45% repeat takes priority, and 30% can't
   coexist with it (repeat = sum of p_i², at most p_max). The target is now whatever goes with a 45% repeat
   (expected around 50–55%), reported and not fitted. Top three is reported.
7. **Form (rerun):** the same field, horses and posts, run again on another day with fresh race-day form and
   fresh random streams. Target: the same winner 45% ±6 (7A).
   **Feasibility note:** the repeat rate is the sum of `p_i²`, so items 6 and 7 are checked together. The
   achievable pairs are reported before any fitting.
8. **Breaks:** replaced by DECISIONS 163 (by manners level).
9. **Tier clocks:** measured separately, after Part 1.
10. **Race shape:**
    - **Quarter pattern** (by the leader): the second quarter slowest in at least 60% of races; the last quarter
      fastest or second-fastest in at least 60%.
    - **Winning margin:** median under 2 lengths.
    - **Photo:** a winning margin under a quarter length (2 ft) in about 1 race in 8 (8–17%).

## Report
Each check comes with its estimate and its uncertainty (field-clustered), the population, the field count, and pass
or fail against the tolerance.

## Amendment (Patrick, 2026-11-01, DECISIONS 188-189)
Trips take priority over early speed. Under the true race pace that realistic trips need, gate's worth measures about
zero at every setting tried. The stat balance's gate target becomes **0.05 places per +0.5 on both tracks** (extra gate
speed must never cost places). Cruise, kick and grit keep their track-shaped targets (half .35/.20/.12, mile
.20/.45/.12). Clocks: within ±3 s of target; displayed times are mapped onto real ones (DECISIONS 177).
