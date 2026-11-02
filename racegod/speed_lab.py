"""RaceGod V4 lab: who absorbs the speed limit? Reruns real fields from a save through outcome.race under each PACE_FROM
setting, with the same random draws for every setting, and prints margins, limits and clocks side by side.
Reads a save copy, never writes it. Horses race as they stand in the save now, not as they were on the night.
    python racegod/speed_lab.py <save.pkl> [first day, default 2626] [reps, default 10]"""
import collections, os, pickle, random, statistics as st, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import outcome, sim                                            # noqa: E402

STAR = "Northern Star"


def fields(save, first):
    F = collections.defaultdict(list)
    for h in save["G"]["horses"]:
        if h.retired:
            continue
        for r in getattr(h, "results", []):
            if r["day"] >= first and r.get("race_id"):
                F[r["race_id"]].append((int(r["trip"].split(",")[0][5:]), h, r["track"]))
    out = []
    for rid, f in sorted(F.items()):
        f.sort(key=lambda x: x[0])
        if len(f) >= 5:
            out.append((rid, [x[1] for x in f], f[0][2]))
    return out


def run(races, pace, reps, carry=True, within=1.0):
    outcome.WITHIN = within                                    # pace and carry variants went with the lab knobs (V4)
    starts = limited = big20 = big40 = photos = 0
    wins, times, star_t, star_m, last = [], [], [], [], []
    for k in range(reps):
        for i, (rid, hs, track) in enumerate(races):
            outcome.rng.seed(f"{k}-{rid}")                     # the same draws for every setting
            o = outcome.race(hs, track)
            starts += len(o)
            limited += sum(h.why["limited"] for h in o)
            big20 += o[-1].why["margin"] >= 20
            big40 += o[-1].why["margin"] >= 40
            last.append(o[-1].why["margin"])
            m = o[1].why["margin"]
            wins.append(m); photos += m <= 0.3
            times.append(o[0].last_time - (sim.HALF_SLOWER if track == "half" else 0))
            if o[0].name == STAR:
                star_t.append(o[0].last_time); star_m.append(m)
    n = reps * len(races)
    return dict(last=st.median(last), limited=100 * limited / starts, big20=100 * big20 / n, big40=100 * big40 / n, margin=st.median(wins),
                photo=100 * photos / n, time=st.median(times), star_t=st.median(star_t) if star_t else None,
                star_fast=min(star_t) if star_t else None, star_m=st.median(star_m) if star_m else None, star_n=len(star_t))


def main():
    path = sys.argv[1]
    first = int(sys.argv[2]) if len(sys.argv) > 2 else 2626
    reps = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    with open(path, "rb") as f:
        races = fields(pickle.load(f), first)
    print(f"{len(races)} real fields since day {first}, {reps} runs each\n")
    print(f"{'winner waits for':34s} {'last':>6s} {'limited':>8s} {'last 20L+':>10s} {'last 40L+':>10s} {'win margin':>11s} {'photos':>7s} {'mile-eq time':>13s}"
          f" | {STAR}: {'median':>7s} {'fastest':>8s} {'margin':>7s}")
    model_per_bar = (1 - outcome.P["mile"]["omega"]) * outcome.K * outcome.P["mile"]["s_margin"] * outcome.SEC_PER_LENGTH   # s per Speed bar, race model
    ratio = round(model_per_bar / abs(outcome.SPEED_FIT[1]), 2)                                                   # vs the clock's s per bar
    for pace, carry, within in ((0, True, 1.0), (3, False, 1.0), (0, True, ratio), (0, True, 0.25), (0, True, 0.0)):
        r = run(races, pace, reps, carry, within)
        name = (("nobody" if pace == 0 else f"top {pace} beaten") + ("" if carry else ", no carry") + (" (today)" if (pace, carry, within) == (0, True, 1.0) else "")
                + (f", within x{within}" if within < 1 else ""))
        print(f"{name:34s} {r['last']:4.1f} L {r['limited']:7.0f}% {r['big20']:9.0f}% {r['big40']:9.0f}% {r['margin']:9.1f} L {r['photo']:6.0f}% {r['time']:13.1f}"
              f" | {r['star_t'] or 0:13.1f} {r['star_fast'] or 0:8.1f} {r['star_m'] or 0:5.1f} L  (wins {r['star_n']})")


if __name__ == "__main__":
    main()
