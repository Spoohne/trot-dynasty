"""Shadow comparison (DECISIONS 235, 4A): today's engine (sim.race) and the outcome engine (outcome.py) on the same
real fields from recent race nights, many runs each. Read-only on a copy of the live save.
    python v6_shadow.py <save.pkl> [runs per field]"""
import os, statistics as st, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, ROOT)


def summarize(name, rows):
    n = len(rows)
    pct = lambda k: 100 * sum(r[k] for r in rows) / n
    print(f"{name:8} | favorite wins {pct('fav'):4.1f}% | best-rated wins {pct('best'):4.1f}% | post 1 wins {pct('p1'):4.1f}%"
          f" | winner time {st.mean(r['time'] for r in rows):6.2f}s (sd {st.pstdev(r['time'] for r in rows):.2f})"
          f" | margin median {st.median(r['margin'] for r in rows):.2f} L, photos {pct('photo'):.0f}% | breaks {st.mean(r['breaks'] for r in rows):.2f}/race")
    print(" " * 9 + "| winner's trip:", {k: f"{100 * v / n:.0f}%" for k, v in Counter(r["trip"] for r in rows).most_common()})


if __name__ == "__main__":
    save = sys.argv[1]; runs = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    os.chdir(ROOT)
    import app, sim, outcome
    import v6_convert as V6
    app.load(save)
    byname = {h.name: h for h in app.G["horses"]}
    fields = []
    for rid, s in app.c.STORIES.items():
        hs = [byname.get(r["name"]) for r in sorted(s["horses"], key=lambda r: r.get("post", 0))]
        if all(h is not None and not h.retired for h in hs) and len(hs) >= 5:
            fields.append((hs, s.get("track") or rid.split("-")[2], bool(s.get("passing"))))
    print(f"{len(fields)} real fields × {runs} runs each")
    for track in ("half", "mile"):
        print(f"--- {track}")
        for name, eng in (("today", sim.race), ("outcome", outcome.race)):
            rows = []
            for hs, tr, passing in fields:
                if tr != track:
                    continue
                fav = max(hs, key=lambda h: h.est)
                rate = {h.id: sum(V6.W[k] * b for k, b in (("gate", outcome.bar(h.developed["early_speed"])), ("stam", outcome.bar(h.developed["stamina"])),
                                                         ("finish", outcome.bar(h.developed["late_speed"])), ("grit", outcome.grit_bar(h)))) for h in hs}
                best = max(hs, key=lambda h: rate[h.id])
                for _ in range(runs):
                    o = eng(hs, tr, passing)
                    trip = o[0].trip.split(", ", 1)[1] if ", " in o[0].trip else o[0].trip
                    rows.append(dict(fav=o[0] is fav, best=o[0] is best, p1=o[0] is hs[0], time=o[0].raw_time,
                                     margin=(o[1].raw_time - o[0].raw_time) / 0.2, photo=(o[1].raw_time - o[0].raw_time) / 0.2 < 0.25,
                                     breaks=sum("broke" in h.trip for h in hs), trip=trip.split(",")[0]))
            summarize(name, rows)
