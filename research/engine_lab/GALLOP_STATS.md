# The ten stats (Gallop Racer framework)

Trot Dynasty's race core is being rebuilt on the Gallop Racer 2006 race model
(`C:\Users\spooh\Downloads\horsegame06\race-engine-findings.md`, sections 14 and 14.10). The project is
pre-launch with no players, so the model's ten stats are adopted outright rather than squeezed out of the
old five traits. `gallop.py` is the port; this note says what each stat does there and where the old
traits and the six stats of `REBUILD_PLAN.md` land.

| Gallop stat | Its job in the race step (`gallop.py`) | Old trait (`sim.py`) | Plan's six |
|---|---|---|---|
| **Speed** | top pace, through the top table | `early_speed` (part) | Speed |
| **Staying** | cruise pace table; how fast the spurt reserve drains | `late_speed` | Kick |
| **Stamina** | size of the stamina pool (550k–2.3M); empty = extra reserve drain each frame | `stamina` | Stamina |
| **Breaking** | start pace, acceleration, the leave's ask (`leave_push`, `leave_pow`) and what the leave costs (`leave_saving`) | `early_speed` (part) | Gate |
| **Response** | effort step, acceleration (the game's player formula, for every horse), how soon a held driver pulls (`resp_pull`) | – | – |
| **Fierce** | reserve drain −(Fierce−70)/5000; the duel in the drive, pace +`duel_scale` per point over the nearest rival within 19.5 m | – | Grit |
| **Tenacity** | how much an empty stamina pool costs (`exhaust`), and the drain table once the reserve is under 250k | `gait` (part) | Manners |
| **Power** | size of the spurt reserve (`track_class`) | – | – |
| **Courage** | how soon a held driver pulls (`courage_pull`) | – | – |
| **Feel** | how far the driver misjudges the spurt point (`feel_judge`) | – | – |

Scale: 0..99 as the game shows them (the tables run to 130). Trot Dynasty's old traits were steps around
a breed middle; a step is roughly 10 Gallop points.

**Rank letter** (tunable in `gallop.CFG`): the sum of the seven racing stats (Speed, Staying, Stamina,
Fierce, Tenacity, Power, Response), SS ≥ 570, S ≥ 500, A ≥ 460, B ≥ 420, C ≥ 370, D ≥ 330, E ≥ 280, F below.
Equal weights to start (decision of 3 Nov 2026).

**At a mile** (the only distance Trot Dynasty races), measured by `research/encyclopedia/gallop_sens.py`: +10 buys
Speed 0.30 s, Staying 0.22 s, Stamina, Tenacity and Power about 0.08 s each, the rest under 0.05 s. The game's own
constants left Power, Tenacity, Fierce, Courage and Feel worth nothing at a mile, so `track_class`, `rebase_share`,
`exhaust`, `duel_scale` and the pull and judgement settings are ours, tuned against that test. `CFG["clock_scale"]`
stretches the reported time to a trotter's (about 1:53.5) without touching the dynamics.

Inferred, not read from the game's code, so kept in `gallop.CFG`: trackClass (4) for the Power reserve,
the aptitude offset table's row order, the early-race line (350 m), and the clock scale.

**The harness lane layer** (ours, replacing the game's random stalls, wobble and 2 % bump; all of it in
`gallop.CFG`): posts line the gate with post 1 on the rail; a follower in the same lane sits a body (5 m)
off the horse ahead and cannot pass through it; a settled driver drops to the inner lane when it is clear;
a held driver whose target pace beats the horse ahead pulls out a lane once within range of the wire
(2 spurt distances, never before 300 m) and goes round, tucking back in once clear; cover (a horse
within 8 m ahead in the lane) saves 30 % of the pool and reserve drain, racing off the rail without cover
costs 10 % more, and each lane out loses a quarter percent of ground. A driver with cover rates off the
horse ahead rather than the leader; a horse wide without having pulled to pass takes back until there's a slot;
the leader rates after the leave at `lead_push`, slower than standard but faster than `ease_push`, so wide horses can drop behind the line (the game's rule, easing once 9.75 m clear, is not used).
