"""Part 1 scorer, exactly as CONTRACTS.md defines each check.
    python research/engine_lab/v3_part1.py race <track> <seed> <races> [form_sd]   items 1-3 and 10: one race per field
    python research/engine_lab/v3_part1.py mc <pop> <seed> <fields> [form_sd]      items 4-7 by reruns (pop: class | mixed)
    python research/engine_lab/v3_part1.py sum [tag]                                pooled report
Writes v3/part1/<mode>_<...>.json; tag is the form_sd used (default 0)."""
import collections, glob, json, os, random, statistics as st, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import race3 as R, drive3 as DR
for k, v in json.loads(os.environ.get("P1_SET", "{}")).items():   # experiments: race3 P / drive3 D overrides
    if k in R.P or k in DR.D:
        (R.P if k in R.P else DR.D)[k] = v
    else:
        setattr(R, k, v)                                    # a race3 constant (T_REACT ...)
OUT = os.path.join(HERE, "v3", os.environ.get("P1_RUN", "part1"))   # P1_RUN: a separate folder per engine version
os.makedirs(OUT, exist_ok=True)
TR = ("gate", "cruise", "kick", "manners", "grit")
MIX = {"half": {8: .908, 7: .046, 6: .022, 5: .008, 4: .007, 3: .005, 2: .005},
       "mile": {10: .879, 9: .024, 8: .028, 7: .020, 6: .012, 5: .011, 4: .005, 3: .010, 2: .010}}
HALF_T = [18.6, 14.9, 12.8, 12.0, 10.0, 7.6, 7.1, 5.9]
MILE_T = [13, 12, 11, 11, 10, 10, 9, 9, 8, 7]
TRIP_T = {"half": dict(lead=35, pocket=22, first_over=15, followed=15, back=13),
          "mile": dict(lead=25, pocket=18, first_over=17, followed=20, back=20)}
DT = 1 / 16


def size(rng, track):
    r, acc = rng.random(), 0.0
    for n, p in MIX[track].items():
        acc += p
        if r <= acc:
            return n
    return max(MIX[track])


def field(stats, track):
    return [R.Horse(f"H{k+1}", dict(s), k + 1, R.TRACKS[track]) for k, s in enumerate(stats)]


def trip(rec, f, w):
    fr = rec["frames"]
    k = next(j for j, F in enumerate(fr) if max(x[0] for x in F) >= 3960)
    F = fr[k]
    i = [h.name for h in f].index(w.name)
    order = sorted(range(len(f)), key=lambda j: -F[j][0])
    lead = order[0]
    if lead == i:
        return "lead"
    s, y = F[i][0], F[i][1]
    lane = (y - R.RAIL_Y) / R.LANE
    ahead = [j for j in range(len(f)) if j != i and 0 < F[j][0] - s < R.BODY_L + 3 * R.LENGTH and abs(F[j][1] - y) < R.BODY_W + R.Y_PAD]
    back = (F[lead][0] - s) / R.LENGTH
    if lane < 0.5:
        rail = [j for j in order if (F[j][1] - R.RAIL_Y) / R.LANE < 0.5]
        if F[lead][1] < R.RAIL_Y + 3.5 and len(rail) > 1 and rail[1] == i and back <= 2.5 + R.BODY_L / R.LENGTH:
            return "pocket"
        return "back"
    if ahead:
        return "followed"
    return "first_over" if back <= 5 + R.BODY_L / R.LENGTH else "back"


def one_race(track, seed, i, form):
    R.P["form_sd"] = form
    rng = random.Random(seed * 100003 + i)
    n = size(rng, track)
    f = field([{t: rng.gauss(0, .4) for t in TR} for _ in range(n)], track)
    o, rec = R.run(f, track, DR.Driver(), seed=seed * 1000 + i, dt=DT)
    w = o[0]
    fr = rec["frames"]
    lead_s = [max(x[0] for x in F) for F in fr]
    cross = [next((j for j, s in enumerate(lead_s) if s >= m), len(fr) - 1) for m in (1320, 2640, 3960)]
    q = [(cross[0] + 1) * DT, (cross[1] - cross[0]) * DT, (cross[2] - cross[1]) * DT, w.time - (cross[2] + 1) * DT]
    margin = ((o[1].time - w.time) * R.FT_MILE / w.time / R.LENGTH) if len(o) > 1 else 9.0
    return dict(n=n, time=w.time, win_post=w.post, posts=[h.post for h in f], trip=trip(rec, f, w), q=q, margin=margin)


def mc(pop, seed, j, form, K=24):
    """One field, K reruns with fresh form and streams: win shares, split in halves to pick and to score."""
    R.P["form_sd"] = form
    rng = random.Random(seed * 7919 + j)
    sd = 0.55 if pop == "mixed" else 0.4
    track = ("half", "mile")[j % 2]
    n = size(rng, track) if pop == "mixed" else 8
    stats = [{t: rng.gauss(0, sd) for t in TR} for _ in range(n)]
    winners, top3 = [], []
    for r in range(K):
        o, _ = R.run(field(stats, track), track, DR.Driver(), seed=seed * 1000003 + j * 101 + r, dt=DT, record=False)
        winners.append(o[0].name); top3.append([h.name for h in o[:3]])
    names = [f"H{k+1}" for k in range(n)]
    out = {}
    for a, b in ((range(0, K // 2), range(K // 2, K)), (range(K // 2, K), range(0, K // 2))):
        p = {x: sum(winners[r] == x for r in a) for x in names}
        best = max(names, key=lambda x: (p[x], -int(x[1:])))
        bottom = sorted(names, key=lambda x: (p[x], x))[: -(-n // 3)]
        out.setdefault("best_win", []).append(sum(winners[r] == best for r in b) / len(b))
        out.setdefault("best_top3", []).append(sum(best in top3[r] for r in b) / len(b))
        out.setdefault("bottom_win", []).append(sum(winners[r] in bottom for r in b) / len(b))
    pairs = [(x, y) for x in range(K) for y in range(x + 1, K)]
    out["repeat"] = sum(winners[x] == winners[y] for x, y in pairs) / len(pairs)
    return {k: (st.mean(v) if isinstance(v, list) else v) for k, v in out.items()} | dict(track=track, n=n)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "race":
        track, seed, n = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
        form = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
        rows = [one_race(track, seed, i, form) for i in range(n)]
        json.dump(rows, open(os.path.join(OUT, f"race_{form}_{track}_{seed}.json"), "w"))
    elif mode == "mc":
        pop, seed, n = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
        form = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
        rows = [mc(pop, seed, j, form) for j in range(n)]
        json.dump(rows, open(os.path.join(OUT, f"mc_{form}_{pop}_{seed}.json"), "w"))
    else:
        tag = sys.argv[2] if len(sys.argv) > 2 else "0.0"
        for track, T in (("half", HALF_T), ("mile", MILE_T)):
            rows = [r for fn in glob.glob(os.path.join(OUT, f"race_{tag}_{track}_*.json")) for r in json.load(open(fn))]
            if not rows:
                continue
            starts, wins = collections.Counter(), collections.Counter()
            for r in rows:
                starts.update(r["posts"]); wins[r["win_post"]] += 1
            curve = [round(100 * wins[p] / starts[p], 1) if starts[p] else 0 for p in range(1, len(T) + 1)]
            miss = [round(c - t, 1) for c, t in zip(curve, T)]
            trips = collections.Counter(r["trip"] for r in rows)
            tp = {k: round(100 * trips[k] / len(rows)) for k in TRIP_T[track]}
            q2_slow = sum(r["q"][1] == max(r["q"]) for r in rows) / len(rows)
            last_fast = sum(sorted(r["q"]).index(r["q"][3]) <= 1 for r in rows) / len(rows)
            margins = sorted(r["margin"] for r in rows)
            print(f"== {track}, {len(rows)} races, form_sd {tag}")
            print(f"   1/2 wins per start by post {curve}  (sum {sum(curve):.0f}; target {T}; off by {miss})")
            print(f"   3 trips {tp}  (target {TRIP_T[track]})")
            print(f"   10 second quarter slowest {q2_slow:.0%}, last quarter fastest or 2nd {last_fast:.0%};"
                  f" median margin {margins[len(margins)//2]:.2f} lengths; winning time {st.median(r.get('time', 0) for r in rows):.1f} s; photos {sum(m < 0.25 for m in margins) / len(rows):.0%}")
        for pop in ("class", "mixed"):
            rows = [r for fn in glob.glob(os.path.join(OUT, f"mc_{tag}_{pop}_*.json")) for r in json.load(open(fn))]
            if not rows:
                continue
            m = lambda k: (st.mean(r[k] for r in rows), st.stdev(r[k] for r in rows) / len(rows) ** 0.5)
            print(f"== reruns, {pop} fields ({len(rows)} fields x 24), form_sd {tag}")
            if pop == "class":
                print(f"   6 best horse wins {m('best_win')[0]:.0%} ±{m('best_win')[1]:.0%} (target 30), top three {m('best_top3')[0]:.0%} (65);"
                      f"   7 same winner on a rerun {m('repeat')[0]:.0%} ±{m('repeat')[1]:.0%} (45)")
            else:
                print(f"   4 favorite wins {m('best_win')[0]:.0%} ±{m('best_win')[1]:.0%} (35-40);   5 bottom third wins {m('bottom_win')[0]:.0%} ±{m('bottom_win')[1]:.0%} (8)")
