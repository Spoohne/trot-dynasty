# Outcome model spec (draft 1, DECISIONS 204)

**Who wins** is a designed, transparent model. **How it looks** is race3/drive3 choreographing that result (phase 2).
This spec covers the model. The presentation (bars, cards) comes later.

## 1. Stats (hidden traits; the game's stats map onto them)

| Trait | Game stat | Its one job |
|---|---|---|
| `gate` | early_speed | Position: who leaves, who gets the lead or pocket, who gets parked or shuffled back |
| `cruise` | stamina | Surviving the pace and the cost of the trip (leading, being parked, going first-over) |
| `kick` | late_speed | The stretch: closing ground when the horse has something left |
| `grit` | new, heritable | Duels: winning when pressed head and head (lead pressed, first-over alongside) |
| `manners` | gait | Safety only: the chance of a break (DECISIONS 163 curve kept) |

Each trait is drawn Normal(0, σ) within a class, as in the lab. Class (tier) is a shift on the whole performance, so
tier clocks fall out of the same model (§6).

## 2. One race, step by step

**Step A: race-day form.** `form_i ~ N(0, σ_form)`, one draw per horse, the same for every trait: how it's going
today. σ_form sets the 45% rerun repeat.

**Step B: the start (trip draw, part 1).** Early position score:

    e_i = gate_i + form_i − c_post[track] · (post_i − 1) + N(0, σ_start)

The order of `e` is the order out of the gate:
- **The lead:** the top `e` horse.
- **A battle:** if the second-best `e` is within `δ_duel` of the top, the lead is contested (a duel). Its chance
  rises as the gap shrinks.
- **The pocket:** the next horse that tucks. With probability `p_park(post, track)` an outside horse instead stays
  **parked** (no cover).
- **The rest:** the rail line in `e` order.

**Step C: the middle (trip draw, part 2).**
- **First-over:** one horse from mid-pack moves, chosen with weight `exp(a_fo · cruise_i)`; occasionally none moves.
- **Followed:** the horses directly behind it in the line take its cover (second- and third-over), up to `n_follow`.
- **Back:** everyone else stays in line (rail).
- **The pocket's box:** with probability `p_box(track)` the pocket stays boxed until late (the passing lane lowers it
  on our tracks).

**Step D: performance.**

    perf_i = Σ_k W[track, trip_i, k] · trait_{i,k} + T[track, trip_i] + form_i + grit term + ε_i

- `T[track, trip]`: what the trip itself is worth (lead and pocket positive on a half-mile; parked strongly negative;
  back negative on a half, closer to neutral on a mile).
- `W[track, trip, k]`: how much each trait counts given the trip.
  - Kick counts more for followed and back (they close).
  - Cruise counts more for lead, first-over and parked (they burn).
  - Gate counts mostly through Steps B and C (position), with a small direct term.
- **The grit term:** for horses in a duel, `g · (grit_i − grit_rival)`.
- **Breaks:** `ε` is small noise. A break (Bernoulli by manners and pressure) costs a large penalty and sets the trip to
  "broke".

**Step E: result.** Finish order by `perf`. Margins in lengths: `m_i = s_margin[track] · (perf_win − perf_i)`. The
winning time is the class pace for the track minus `s_time · perf_win`, mapped to displayed time (DECISIONS 177).

## 3. Parameters (about 25, all fitted)

- **Start and trips:** `c_post` (×2), `σ_start`, `δ_duel`, `p_park` (shape ×2), `a_fo`, `n_follow`, `p_box` (×2).
- **Performance:** `T` (5 trips × 2 tracks, one fixed as reference), `W` (a structured few: base weight per trait per
  track plus a trip modifier for kick and cruise), `g`, `σ_form`, `σ_ε`.
- **Result:** `s_margin` (×2), `s_time`.

## 4. Targets (fitted by Monte Carlo; each model race takes microseconds)

| Target | Value |
|---|---|
| Wins by post | half-mile: the live curve 18.6 → 5.9; mile: soft, about 13 → 7, falling |
| Winning trips (lead/pocket/first-over/followed/back) | half 35/22/15/15/13; mile 25/18/17/20/20 |
| Rail horse at the half | leads about 25% (half); top three 79% (half), 37% (mile) |
| Places gained for +0.5 in a trait | half gate .45, cruise .35, kick .20, grit .12; mile gate .20, cruise .20, kick .45, grit .12 (DECISIONS 143). Gate's earlier amendment to 0.05 (189) was a physics limit and doesn't apply here. |
| Best horse wins | about 50–55%; rerun repeat 45% (item 7) |
| Upsets | bottom-third wins about 8% |
| Margins | median under 2 lengths; photos 8–17% |
| Breaks | manners curve (163) |
| Favorite | 35–40% by the game's own odds, measured after integration (169) |

## 5. Phase 2: choreography (later)

race3/drive3 get the decided trips (each driver's aim and role), the finish order and the margins. Each horse's hidden
race-day capacity (`p_sus` and the kick offset) is solved so the physics delivers that result, in a few correction
runs. Report the realization rate. If the physics can't deliver believably, the story system draws the race.

## 6. Classes and tiers

Within a race the field is near one class, so the model works on traits relative to the class. Across classes a tier
shift moves performance and time together, so an S horse in a C race wins easily and an S race runs faster.

## 7. Open questions for review

1. Structure: trips drawn first, then performance given the trip. Or performance first, with the trip as a
   consequence? Which better keeps stats meaningful and trips realistic?
2. Is a few structured `W` terms enough, or will balance and trip targets fight? What's the minimal identifiable
   parameter set?
3. How to fit 25 parameters to these targets robustly (objective, noise, avoiding over-fitting the half-mile post
   curve)?
4. What does phase 2 need from the model to choreograph believably (energy budgets per horse, segment times)?
