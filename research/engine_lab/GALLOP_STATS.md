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
| **Fierce** | reserve drain −(Fierce−70)/5000 (its lane-change odds went with the game's lateral layer) | – | Grit |
| **Tenacity** | the drain table once the reserve is under 250k | `gait` (part) | Manners |
| **Power** | size of the spurt reserve (−trackClass·(99−Power)/10000) | – | – |
| **Courage** | nothing yet (its lane-change odds went with the game's lateral layer) | – | – |
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
the aptitude offset table's row order, the early-race line (350 m), and the clock scale.

**The harness lane layer** (ours, replacing the game's random stalls, wobble and 2 % bump; all of it in
`gallop.CFG`): posts line the gate with post 1 on the rail; a follower in the same lane sits a body (5 m)
off the horse ahead and cannot pass through it; a settled driver drops to the inner lane when it is clear;
a held driver whose target pace beats the horse ahead pulls out a lane once within range of the wire
(1.6 spurt distances, never before 300 m) and goes round, tucking back in once clear; cover (a horse
within 8 m ahead in the lane) saves 30 % of the pool and reserve drain, racing off the rail without cover
costs 30 % more, and each lane out loses a quarter percent of ground. A driver with cover rates off the
horse ahead rather than the leader; a horse wide off the gate with nobody to follow eases back for cover;
the leader eases only when clear by 9.75 m (the game's own rule).
