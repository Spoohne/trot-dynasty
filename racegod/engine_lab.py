"""RaceGod V5 lab: today's engine (outcome.race + story.build) against the simulated race (racegod/engine.py), side by
side on the same real fields from a save copy, through the same audit (racegod/audit.py laws and TARGETS.md).
Reads the save, never writes it. Horses race as they stand now, not as they were on the night.
    python racegod/engine_lab.py <save.pkl> [first day, default 2626] [reps, default 5] [--stories out.json]
--stories keeps the sim's stories of the first rep (and today's, as <id>-today) for racegod/replay_server.py."""
import collections, json, os, pickle, statistics as st, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import circuit, outcome, sim, story as _story                  # noqa: E402
import audit, engine                                           # noqa: E402
from speed_lab import fields, STAR                             # noqa: E402

ENGINES = {"today": (outcome.race, outcome.rng, _story.build), "sim": (engine.race, engine.rng, engine.story)}


def run(races, name, reps, keep=None):
    race, rng, build = ENGINES[name]
    stories, results, extra = [], [], collections.defaultdict(list)
    for k in range(reps):
        for rid, hs, track in races:
            for i, h in enumerate(hs, 1):
                h.post = i
            rng.seed(f"{k}-{rid}")
            order = race(hs, track, passing=False)
            line = circuit.tote_odds(hs)
            s = dict(build(order, track, passing=False), id=f"{rid}-{k}", day=9999, passing=False, name=f"{rid} ({name})", purse=0)
            for row, h in zip(s["horses"], order):
                row["odds"] = "%d-%d" % line[h.id]
                row["why"] = h.why
                results.append(dict(track=track, size=len(hs), post=h.post, place=row["place"]))
            stories.append(s)
            if keep is not None and k == 0:
                keep[f"{rid}-{name}"] = s
            w = s["horses"][0]
            extra["win_time"].append(order[0].last_time - (sim.HALF_SLOWER if track == "half" else 0))
            extra["last"].append(s["horses"][-1]["behind"][6])
            extra["q1"].append(s["quarters"][1])
            extra["q_spread"].append(max(s["quarters"][i + 1] - s["quarters"][i] for i in range(4)) - min(s["quarters"][i + 1] - s["quarters"][i] for i in range(4)))
            extra["lead_q_won"].append(min(s["horses"], key=lambda r: r["behind"][2]) is w)
            extra["trip"].append(w["trip"].split(", ", 1)[1].split(",")[0])
            if order[0].name == STAR:
                extra["star"].append((order[0].last_time, s["horses"][1]["behind"][6]))
    return stories, results, extra


def main():
    path = sys.argv[1]
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    first = int(args[0]) if args else 2626
    reps = int(args[1]) if len(args) > 1 else 5
    keep = {} if "--stories" in sys.argv else None
    with open(path, "rb") as f:
        races = fields(pickle.load(f), first)
    print(f"{len(races)} real fields since day {first}, {reps} runs each\n")
    out = {}
    for name in ENGINES:
        if "--sim" in sys.argv and name != "sim":
            out[name] = out["sim"] if "sim" in out else None
            continue
        stories, results, extra = run(races, name, reps, keep)
        broken = collections.Counter(kind for s in stories for kind, _ in audit.laws(s))
        out[name] = (audit.measure(stories, results), extra, broken, len(stories))
    out["today"] = out["today"] or out["sim"]                  # --sim: the sim in both columns
    print(f"{'':30s} {'today':>14s} {'sim':>14s}   band")
    for key, t in audit.targets().items():
        lo, hi = t["band"]
        cells = []
        for name in ENGINES:
            v, n = out[name][0][key]
            verdict = "-" if v is None else "ok" if lo <= v <= hi else "LOW" if v < lo else "HIGH"
            cells.append(f"{v:7.1f} {verdict:>5s}" if v is not None else f"{'-':>13s}")
        print(f"{key:30s} {cells[0]:>14s} {cells[1]:>14s}   {lo}-{hi}")
    print()
    rows = [("winning time, mile-eq (median)", lambda e: st.median(e["win_time"])),
            ("fastest winning time", lambda e: min(e["win_time"])),
            ("last horse (median L)", lambda e: st.median(e["last"])),
            ("races with a horse 20 L+ back", lambda e: 100 * sum(x >= 20 for x in e["last"]) / len(e["last"])),
            ("races with a horse 40 L+ back", lambda e: 100 * sum(x >= 40 for x in e["last"]) / len(e["last"])),
            ("first quarter (median s)", lambda e: st.median(e["q1"])),
            ("fastest-slowest quarter (median s)", lambda e: st.median(e["q_spread"])),
            ("leader at the quarter wins %", lambda e: 100 * st.mean(e["lead_q_won"])),
            (f"{STAR}: wins", lambda e: len(e["star"])),
            (f"{STAR}: median time", lambda e: st.median(t for t, _ in e["star"]) if e["star"] else 0),
            (f"{STAR}: median margin L", lambda e: st.median(m for _, m in e["star"]) if e["star"] else 0)]
    for label, f in rows:
        print(f"{label:34s} {f(out['today'][1]):10.1f} {f(out['sim'][1]):10.1f}")
    for name in ENGINES:
        trips = collections.Counter(out[name][1]["trip"])
        n = sum(trips.values())
        print(f"\n{name}: winning trips  " + ", ".join(f"{k} {100 * v / n:.0f}%" for k, v in trips.most_common()))
        print(f"{name}: laws broken   " + (", ".join(f"{k} ({v} of {out[name][3]})" for k, v in out[name][2].most_common()) or "none"))
    if keep is not None:
        p = sys.argv[sys.argv.index("--stories") + 1]
        json.dump(keep, open(p, "w"))
        print(f"\n{len(keep)} stories kept in {p}")


if __name__ == "__main__":
    main()
