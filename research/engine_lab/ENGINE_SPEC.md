# Trot Dynasty race engine v3: spec (decided)

**Decided 2026-11-01:** Patrick took every ★ pick and kept Part 0 as written. The ★ option is the requirement; the
other options stay listed for the record. "Real" = a published figure (see chart_targets.md).

---

## How the engine decides a race

The engine races the actual horses in each race against each other: their traits, posts and drivers. Nothing sets
the result in advance: no dice for posts, no thumb on the scale for favorites.

- **Part 0** is how every race must behave. These rules hold in every race, and you'll see them in the replay.
- **Part 1** is the results over thousands of races. They are checks, not controls. If a check fails, we fix the
  behavior that causes it, never add a bonus or penalty to bend the number.

---

## Part 0: Race behavior (every race, every horse)

The ones marked (seen) are faults we've already caught in the lab.

**Bodies and lanes**
- 0.1 No horse ever passes through another, or overlaps one in the same lane. (seen)
- 0.2 Lane changes are smooth and take room: a horse slides out or in over a few strides, and only into a gap that
  fits it. No snapping sideways.
- 0.3 No weaving: a horse doesn't go in and out repeatedly. Once a driver commits to a lane change, he finishes it.
- 0.4 Nobody races four or more wide on a turn unless it's boxed in and moving, or passing a wall of horses.
  Three-wide on a turn is rare and costly.
- 0.5 The rail is the default. A horse with nothing to gain drops in as soon as there's room.

**The start**
- 0.6 The field leaves the gate side by side and sorts itself out before the first turn. Outside horses either
  clear the field or ease back and tuck in. Nobody goes into the first turn more than three wide without a reason.
  (seen: eight wide) Allowed (Patrick, 2026-11-01): four-wide on the first turn only while a horse is still working in
  from an outside post.
- 0.7 Only the drivers who mean to go for the lead go hard off the gate. Everyone else leaves at a sensible pace.
- 0.8 A horse that can't clear the horse inside it by the first turn takes back. It doesn't stay parked out there
  burning itself up. (seen)

**Pace and energy**
- 0.9 A leader with nobody pressing slows the pace (the breather quarter). A challenged leader picks it up.
- 0.10 A horse runs out of gas gradually: it slows over the final furlongs. It doesn't stop dead unless it broke
  stride.
- 0.11 Racing outside without cover always costs more than racing on the rail or behind a horse.
- 0.12 A horse never runs faster than it's able to.
- 0.13 More of any trait never makes a horse do worse, on average. (seen: early speed did)

**Moves and tactics**
- 0.14 A driver makes one plan, then changes it only when something happens: a hole opens, cover comes, the horse
  is spending too much. He doesn't flip back and forth. (seen)
- 0.15 Once a horse has quit on a tactic, it doesn't try it again straight away. (seen)
- 0.16 Moves happen at believable places: first-over moves usually start from the half to the far turn; closers
  come in the last quarter. A move that starts too early is a mistake by the driver, and it costs.
- 0.17 Cover is real: a horse following another out is sheltered and moves with it.
- 0.18 A horse in the pocket waits for room. It gets out when the stretch opens or the leader drifts, and is
  sometimes stuck there. It never goes through the leader.
- 0.19 Drivers don't all make the same choice. In a typical race some go for the top, some sit, some follow, some
  wait. (seen: everyone wanted the top)

**The stretch**
- 0.20 The stretch fans out: horses fan wide for room, and a closer can come down the middle or the outside.
- 0.21 Horses keep a straight line in the stretch. Small drifts are fine; crossing in front of a rival isn't.

**Breaking stride**
- 0.22 A break is visible and costly: the horse loses ground for a few seconds and is usually out of contention.
  It's likelier under pressure, in traffic, or with rough manners.

**Fairness**
- 0.23 Every horse is raced to win with its driver's best plan. Nobody is told to lose, and the house never adjusts
  a result.
- 0.24 The same race with the same draws gives the same result. Every race can be replayed and audited.

---

## Part 1: Race results the engine must hit (checks over thousands of races)

**1. Wins by post, half-mile (8 starters)**
- ★ A. Your live curve: 18.6 / 14.9 / 12.8 / 12.0 / 10.0 / 7.6 / 7.1 / 5.9 (it matches the real figures).
- B. Steeper, like Yonkers: about 26% from the rail, about 4% from post 8.

**2. Wins by post, mile (10 starters)**
- A. Keep the live curve: 10.9 down to 5.2.
- ★ B. A touch more inside edge: about 13 / 12 / 11 / 11 / 10 / 10 / 9 / 9 / 8 / 7. Big tracks are fairer than half-miles, but not flat.
- C. Wait for real mile-track tables before setting this.

**3. How winners get there (share of wins by trip)**

| Trip | Half-mile ★ | Mile ★ |
|---|---|---|
| On the lead | 35% | 25% |
| Pocket | 22% | 18% |
| First-over | 15% | 17% |
| Second-over / followed cover | 15% | 20% |
| Came from further back | 13% | 20% |

- ★ A. These numbers.
- B. More front-end bias (lead 45% on a half).
- C. More of a closer's game (back markers 25%+).

**4. How often the favorite wins**

Real: the Meadowlands has the lowest rate in the sport; some tracks run over 47%.
- ★ A. 35–40%.
- B. 30%, with more upsets.
- C. 45%, so form holds.

**5. Upsets**
- ★ A. A horse rated in the bottom third of its field wins about 1 race in 12. A true longshot win (your "Rich Strike" idea) stays a rare scripted event, outside the engine.
- B. 1 in 8.
- C. 1 in 20.

**6. How much better horses win**

In a field of 8 drawn from one class, the best horse on true ability:
- ★ A. wins about 30%, is in the top three about 65%;
- B. wins about 40%;
- C. wins about 22%.

**7. Week-to-week form**

Same horse, same field, rerun:
- ★ A. The same winner about 45% of the time. Trip and post decide the rest.
- B. 60%.
- C. 30%.

**8. Breaking stride (trotters)**
- ★ A. About 4% of starters break, more for rough-gaited horses, more under pressure and in traffic. A break nearly always costs the race.
- B. 8%.
- C. 2%.

**9. Mile times**
- ★ A. Keep today's tier clocks: S+ at 1:47.5 or better, D slower than 1:59. The engine is calibrated to them, so badges and appraisals keep their meaning.
- B. Retune the clocks around the new engine.

**10. Race shape**
- ★ A. The typical night-race pattern: a quick first quarter (the leave), a breather second quarter, the pace picks up from the half, the fastest or second-fastest quarter last. Winning margins are mostly under 2 lengths, with a photo about 1 race in 8.
- B. More even, with closer finishes.

---

## Part 2: The horse

**11. Hidden traits** (what the engine uses; one job each, and more of any trait only ever helps)
- ★ A. Five:
  - **Gate speed:** how quickly it gets away and claims position.
  - **Cruising efficiency:** how cheaply it holds a pace; this is stamina.
  - **Kick:** top speed in the drive.
  - **Manners:** stays flat under pressure and handles traffic.
  - **Grit:** answers a challenge alongside; a duel costs it less.
- B. Four (no Grit).
- C. Six (add **Durability**: how well form holds between starts).

**12. What players see**
- ★ A. Keep today's four bars (Early speed, Late speed, Stamina, Gait), each mapped from the hidden traits. Grit shows only as a one-line trainer note ("game when collared"). Nothing new to learn, and the bars mean what they say.
- B. Show all hidden traits as bars.
- C. Fewer bars, plus a "running style" tag.

**13. Pacers too?**
- ★ A. Trotters only, as now.
- B. Add pacers later as a second gait.

**14. Condition and fitness**
- ★ A. Keep today's freshness and training effects feeding the engine as they do now.
- B. Redesign them with the engine.

---

## Part 3: Breeding (new traits mean new inheritance)

**15. Inheritance**
- ★ A. Each hidden trait inherits like today's traits, from the sire, the dam and luck. Redo the long-run tests (inflation, S+ cap, stud book) on the new traits before launch.
- B. Add trait pairings (a speed sire crossed with a stamina dam has its own odds).

**16. Lines**
- ★ A. No set bloodline types. Lines emerge from what players breed.
- B. Named families with tendencies ("the Hanover kick").

---

## Part 4: Driving

**17. Driver**
- ★ A. The five aims and re-checks you already approved, rebuilt for the new engine as a rule-based driver, with each rule's settings tuned to the Part 1 targets. Planning before the gate is allowed if it's needed to hit the targets.
- B. Learned scoring (today's lab approach).

**18. Driver skill**
- ★ A. Equal for now, as decided (8B).
- B. Build it in now.

---

## Part 5: Tracks, the replay, the server

**19. Tracks**
- ★ A. Half-mile and mile, as now, with these layouts:
  - **Half-mile:** 300 ft to the first turn and a 500 ft stretch.
  - **Mile:** about 1,000 ft from the last turn to the wire.
- B. Add a five-eighths track.

**20. Field sizes**
- ★ A. As now: up to 8 on a half, up to 10 on a mile.

**21. Replay**
- ★ A. The engine records every horse's position, lane and speed throughout the race, with smooth lane changes and no horse passing through another. The replay draws exactly that; nothing invented.

**22. Server time**
- ★ A. Up to about 1 hour of computing per race night, spread through the day, since fields are drawn a day ahead. I flag it first if it needs more.
- B. Must run at post time, under 1 second a race.
- C. A second small server is fine if needed.

---

## Part 6: Process

**23. Done means**
- ★ A. Every Part 1 target within its tolerance on both tracks; more of any trait never hurts on average; the post rotation test passes; the replay looks right to you; runtime within item 22. Then you play the developer pilot on it before it goes anywhere near the live game.

**24. Switch-over**
- ★ A. The new engine arrives with the fresh-world launch. The live test world keeps its current engine until then.
- B. Swap it into the live test world once it passes, to see it under real players.

**25. Real data**
- ★ A. Free figures only for now. Revisit paying for full charts if the targets in Part 1 feel off once you've seen races.
- B. Buy chart data now: your call, and outside the agreed budget.
