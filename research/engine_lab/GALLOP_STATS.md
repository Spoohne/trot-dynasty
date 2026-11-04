# The ten stats (Gallop Racer framework)

Trot Dynasty's race core is being rebuilt on the Gallop Racer 2006 race model
(`C:\Users\spooh\Downloads\horsegame06\race-engine-findings.md`, sections 14 and 14.10). The project is
pre-launch with no players, so the model's ten stats are adopted outright rather than squeezed out of the
old five traits. `gallop.py` is the port; this note says what each stat does there and where the old
traits and the six stats of `REBUILD_PLAN.md` land.

| Gallop stat | Its job in the race step (`gallop.py`) | Old trait (`sim.py`) | Plan's six |
|---|---|---|---|
| **Speed** | top pace, through the top table | `early_speed` (part) | Speed |
| **Staying** | cruise pace table; how fast the spurt reserve drains; the driver's target pace | `late_speed` | Kick |
| **Stamina** | size of the stamina pool (550k–2.3M); empty = exhausted, extra reserve drain | `stamina` | Stamina |
| **Breaking** | start pace, acceleration, a 2·Brk early top bonus, early effort step | `early_speed` (part) | Gate |
| **Response** | how fast effort follows the driver's push (push Resp/5+52, step Resp/5+1) | – | – |
| **Fierce** | reserve drain −(Fierce−70)/5000, lane-change odds, lateral cost | – | Grit |
| **Tenacity** | the drain table once the reserve is under 250k | `gait` (part) | Manners |
| **Power** | size of the spurt reserve (−trackClass·(99−Power)/10000) | – | – |
| **Courage** | lane-change odds (against Fierce), lateral cost | – | – |
| **Feel** | nothing in the pace model (pace-judgement window and hold timers in the game's AI only) | – | – |

Scale: 0..99 as the game shows them (the tables run to 130). Trot Dynasty's old traits were steps around
a breed middle; a step is roughly 10 Gallop points.

**Rank letter** (tunable in `gallop.CFG`): the sum of the seven racing stats (Speed, Staying, Stamina,
Fierce, Tenacity, Power, Response), SS ≥ 570, S ≥ 500, A ≥ 460, B ≥ 420, C ≥ 370, D ≥ 330, E ≥ 280, F below.
Equal weights to start (decision of 3 Nov 2026).

**At a mile** (the only distance Trot Dynasty races): Staying and Speed decide races, Stamina third,
Breaking a tie-breaker; the rest live in the traffic layer and move a race by hundredths. The game's clock
gives a thoroughbred mile in about 91 s; `CFG["CLOCK_SCALE"]` stretches the reported time to a trotter's
(1:53 for the same race) without touching the dynamics.

Inferred, not read from the game's code, so kept in `gallop.CFG`: trackClass (4) for the Power reserve,
the aptitude offset table's row order, the lane-change base odds (30 %), the early-race line (350 m),
and the clock scale.
