"""Phase 2 (DECISIONS 210): race3/drive3 race the outcome model's decided result.

The model decides each horse's trip (lead, pocket, first-over, followed, back; duels), the finish order and the
margins. The physics gets a script (each driver's aim) and a bounded per-horse nudge for the day (added to cruise and
kick), corrected over a few reruns until the physics finishes in the decided order by about the decided margins.
Realization is measured, never assumed; a race the physics can't deliver goes to the story system.

    python v4_choreo.py <track> <races>       realization report
"""
import json, os, random, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import race3 as R, drive3 as DR, v4_outcome as V, v3_part1 as P1

AIM = {0: "top", 1: "pocket", 2: "first_over", 3: "follow", 4: "close"}
NUDGE_MAX = 0.5          # cap on a horse's hidden nudge for the day (trait units; the class spread is 0.4)
ITERS, GAIN = 6, 0.06    # correction runs, and nudge per length off target


def decide(traits, track, p, seed):
    """One race from the outcome model: traits (n, 5) gate, cruise, kick, manners, grit."""
    n = traits.shape[0]
    D = V.draws(1, n, seed)
    D["traits"] = traits[None].copy()
    P, role, rank = V.race(p, D, track)
    P, role, rank = P[0], role[0], rank[0]
    order = list(np.argsort(-P))
    margin = (P[order[0]] - P) * p["s_margin"]                   # lengths behind the winner
    duel = role[np.argmax(rank == 1)] == 2
    return dict(order=order, margin=margin, role=role, rank=rank, duel=bool(duel))


def stage(traits, track, dec, seed, nudge=None):
    """Run the physics with the script and the nudges. Returns finish order, lengths behind, record, driver."""
    n = traits.shape[0]
    nudge = np.zeros(n) if nudge is None else nudge
    aims = {}
    for i in range(n):
        r = dec["role"][i]
        aims[f"H{i+1}"] = "press" if (r == 2 and dec["rank"][i] == 1) else AIM[int(r)]
    f = []
    for i in range(n):
        g, c, k, m, gr = traits[i]
        f.append(R.Horse(f"H{i+1}", dict(gate=g, cruise=c + nudge[i], kick=k + nudge[i], manners=m, grit=gr), i + 1, R.TRACKS[track]))
    d = DR.Driver(gate_aims={k: (v if v != "press" else "top") for k, v in aims.items()}, local_leave=0)
    o, rec = R.run(f, track, d, seed=seed, dt=1 / 16)
    win = o[0].time
    behind = np.array([(h.time - win) * R.FT_MILE / win / R.LENGTH for h in f])
    return [int(h.name[1:]) - 1 for h in o], behind, rec, d, f


def choreograph(traits, track, dec, seed):
    """Solve the bounded nudges: a few runs, each correcting every horse toward its decided margin."""
    n = traits.shape[0]
    target = dec["margin"]
    nudge = np.zeros(n)
    for it in range(ITERS):
        order, behind, rec, d, f = stage(traits, track, dec, seed, nudge)
        err = behind - target                                       # + : further back than decided
        if order[0] == dec["order"][0] and np.all(np.abs(err) < 1.0):
            break
        nudge = np.clip(nudge + GAIN * err, -NUDGE_MAX, NUDGE_MAX)
    return order, behind, rec, d, f, nudge, it + 1


def report(track, N):
    p = json.load(open(os.path.join(V.OUT, f"fit_{track}.json")))["params"]
    p = dict(V.FIXED, **p)
    rng = np.random.default_rng(2026)
    n = V.N_STARTERS[track]
    ok = dict(winner=0, top3=0, order=0, margin=0, trip=0, safe=0)
    nudges, runs, by_trip = [], [], {}
    for i in range(N):
        traits = rng.normal(0, V.SD, (n, 5))
        dec = decide(traits, track, p, 1000 + i)
        order, behind, rec, d, f, nudge, it = choreograph(traits, track, dec, 7000 + i)
        a = R.audit(rec)
        w = dec["order"][0]
        trip_dec = V.ROLES[int(dec["role"][w])]
        trip_real = P1.trip(rec, f, f[order[0]]) if order[0] == w else "-"
        good = dict(winner=order[0] == w, top3=order[:3] == dec["order"][:3], order=order == dec["order"],
                    margin=abs(behind[dec["order"][1]] - dec["margin"][dec["order"][1]]) < 0.75,
                    trip=trip_real == trip_dec, safe=a["overlaps"] + a["safety"] + a["four_wide_turn_steps"] == 0)
        for k in ok:
            ok[k] += good[k]
        by_trip.setdefault(trip_dec, []).append(good["winner"])
        nudges.append(np.abs(nudge).max()); runs.append(it)
    pc = lambda k: f"{100 * ok[k] / N:.0f}%"
    print(f"== {track}, {N} decided races: winner {pc('winner')} | top three in order {pc('top3')} | whole order {pc('order')}"
          f" | 2nd's margin within 3/4 L {pc('margin')} | winner's trip as decided {pc('trip')} | safety clean {pc('safe')}")
    print(f"   largest nudge per race: median {np.median(nudges):.2f}, 90th {np.percentile(nudges, 90):.2f} (cap {NUDGE_MAX})"
          f" | physics runs per race: mean {np.mean(runs):.1f}")
    print("   winner delivered, by decided trip:", {k: f"{100 * np.mean(v):.0f}% of {len(v)}" for k, v in by_trip.items()})


if __name__ == "__main__":
    report(sys.argv[1], int(sys.argv[2]))
