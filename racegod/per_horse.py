"""The per-horse rule (DECISIONS 215, Patrick: "speed gives options, never obligations"): a bar more of Speed, Stamina or
early speed never lowers a horse's win chance. Checked on real fields with common random numbers: one horse per field,
its win share over reruns as it is, then with each bar one step up (via drive_on, the same door the drivers' edge uses).
    python racegod/per_horse.py <save.pkl> [fields, default 100] [reruns, default 60] [--retune racegod/retune.json]"""
import bisect, json, os, pickle, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import outcome                                                 # noqa: E402
from racegod.speed_lab import fields                           # noqa: E402

BARS = {"late_speed": "Speed", "stamina": "Stamina", "early_speed": "gate"}


def one_bar(v):
    """Stat units that lift this live value one pip on the bar scale (the step it sits in)."""
    xs = (-4.17,) + outcome.PIP_STEPS
    k = min(max(bisect.bisect_right(xs, v) - 1, 0), len(xs) - 2)
    return xs[k + 1] - xs[k]


def win_share(h, hs, track, reruns):
    wins = 0
    for k in range(reruns):
        outcome.rng.seed(f"ph-{k}-{h.id}")
        wins += outcome.race(hs, track)[0] is h
    return 100 * wins / reruns


def main():
    path = sys.argv[1]
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    n_fields = int(args[0]) if args else 100
    reruns = int(args[1]) if len(args) > 1 else 60
    if "--retune" in sys.argv:
        for k, v in json.load(open(sys.argv[sys.argv.index("--retune") + 1])).items():
            t, kk = k.split("."); outcome.P[t][kk] = v
    with open(path, "rb") as f:
        races = fields(pickle.load(f), 2626)[:n_fields]
    drops, worst = {b: [] for b in BARS}, {b: (0.0, "") for b in BARS}
    for i, (rid, hs, track) in enumerate(races):
        h = hs[i % len(hs)]                                    # one horse per field, posts spread across fields
        saved = getattr(h, "drive_on", None)
        base = win_share(h, hs, track, reruns)
        for stat, name in BARS.items():
            h.drive_on = dict(saved or {}); h.drive_on[stat] = h.drive_on.get(stat, 0) + one_bar(h.current(track)[stat])
            up = win_share(h, hs, track, reruns)
            d = base - up
            drops[stat].append(d)
            if d > worst[stat][0]:
                worst[stat] = (d, f"{h.name} post {hs.index(h) + 1} {track} {rid}: {base:.0f}% -> {up:.0f}%")
        h.drive_on = saved
    print(f"{len(races)} horses, {reruns} reruns each, common random numbers\n")
    for stat, name in BARS.items():
        ds = drops[stat]
        print(f"{name:8s} +1 bar: win share up on average {-sum(ds) / len(ds):+.1f} points; dropped more than 2 points in {sum(d > 2 for d in ds)} of {len(ds)}"
              f" (more than 5: {sum(d > 5 for d in ds)}); worst {worst[stat][0]:.0f} points, {worst[stat][1]}")


if __name__ == "__main__":
    assert one_bar(0.0) == outcome.PIP_STEPS[5] - outcome.PIP_STEPS[4]
    main()
