"""RaceGod's audit: is every race's story true to its result, and do the nights look like racing?
Reads a save (a COPY of the live one), never writes it.
    python racegod/audit.py <save.pkl> [--since DAY] [--json out.json]

Two parts:
  laws     each story against its own result: finish order, margins, times, lanes, fractions (any failure is a bug)
  targets  the night's numbers against racegod/TARGETS.md (post bias, where winners raced, favorites, margins)"""
import argparse, json, os, pickle, re, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                    # the save pickles game classes


def odds(s):
    a, b = s.split("-")
    return int(a) / int(b)


def laws(s):
    """Every way this story disagrees with its own result: [(kind, detail)]."""
    bad, H = [], s["horses"]
    if [r["place"] for r in H] != list(range(1, len(H) + 1)):
        bad.append(("finish order out of place", ""))
    if H[0]["behind"][6] != 0:
        bad.append(("winner not in front at the wire", f"{H[0]['behind'][6]} L"))
    fin = [r["behind"][6] for r in H]
    if any(b < a - 1e-6 for a, b in zip(fin, fin[1:])):
        bad.append(("a beaten horse finishes ahead of one that beat it", ""))
    times = [r["time"] for r in H]
    if any(b < a for a, b in zip(times, times[1:])) or times[0] != s["final"]:
        bad.append(("times out of order or winner's time isn't the final", ""))
    for r in H:
        if max(r["lane"][2:5]) > 2:
            bad.append(("4-wide or more before the stretch", f"{r['name']} {int(max(r['lane'][2:5])) + 1}-wide"))
        if max(r["lane"][2:]) > 4:                           # lane at the start is the post, behind the car
            bad.append(("6-wide or more", f"{r['name']} {int(max(r['lane'][2:])) + 1}-wide"))
        w = r.get("why")
        if w and abs(r["behind"][6] - w["margin"]) > 0.5:
            bad.append(("replay margin differs from the result", f"{r['name']} {r['behind'][6]} L vs {w['margin']} L"))
    q = s["quarters"]
    splits = [b - a for a, b in zip(q, q[1:])]
    if any(x <= 0 for x in splits) or abs(q[-1] - s["final"]) > 0.01:
        bad.append(("quarters don't add up", str(q)))
    elif max(abs(x - s["final"] / len(splits)) for x in splits) > 3:
        bad.append(("a quarter more than 3 s off even pace", str([round(x, 1) for x in splits])))
    return bad


def pct(hits, n):
    return (100 * hits / n if n else None), n


def measure(stories, results):
    """The TARGETS.md numbers: {key: (value, sample size)}."""
    m = {}
    for track in ("half", "mile"):
        rs = [r for r in results if r["track"] == track and r["size"] >= 8]
        for post in (1, 8):
            at = [r for r in rs if r["post"] == post]
            m[f"{track}_post{post}_win"] = pct(sum(r["place"] == 1 for r in at), len(at))
    near = [s["horses"][0]["behind"][3] <= 3 for s in stories]
    m["winner_near_lead_at_half"] = pct(sum(near), len(near))
    half = [s for s in stories if s["track"] == "half"]
    m["half_winner_from_back"] = pct(sum(s["horses"][0]["behind"][3] >= 4 for s in half), len(half))
    priced = [s for s in stories if all("odds" in r for r in s["horses"])]
    m["favorite_win"] = pct(sum(odds(s["horses"][0]["odds"]) == min(odds(r["odds"]) for r in s["horses"]) for s in priced), len(priced))
    second = [s["horses"][1]["behind"][6] for s in stories if len(s["horses"]) > 1]
    m["margin_median_l"] = (st.median(second) if second else None), len(second)
    m["photo_pct"] = pct(sum(b <= 0.3 for b in second), len(second))
    whys = [r["why"] for s in stories for r in s["horses"] if r.get("why")]
    m["limited_pct"] = pct(sum(w["limited"] for w in whys), len(whys)) if whys else (None, 0)
    return m


def targets():
    text = open(os.path.join(HERE, "TARGETS.md"), encoding="utf-8").read()
    return json.loads(re.search(r"```json\n(.*?)```", text, re.S).group(1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("save")
    ap.add_argument("--since", type=int, default=0, help="first race day to audit")
    ap.add_argument("--json")
    a = ap.parse_args()
    with open(a.save, "rb") as f:
        save = pickle.load(f)
    stories = sorted((s for s in save["stories"].values() if s["day"] >= a.since), key=lambda s: (s["day"], s["id"]))
    results = []
    for h in save["G"]["horses"]:
        for r in getattr(h, "results", []):
            p = re.match(r"post (\d+)", r.get("trip", ""))
            if r["day"] >= a.since and p:
                results.append(dict(r, post=int(p.group(1))))
    if not stories:
        sys.exit(f"no stories since day {a.since}")
    days = sorted({s["day"] for s in stories})
    print(f"RaceGod audit: {len(stories)} races, days {days[0]}-{days[-1]}, {len(results)} starts in horse records\n")

    broken = [(s["id"], b) for s in stories if (b := laws(s))]
    print(f"LAWS  {len(stories) - len(broken)} of {len(stories)} races true to their result")
    kinds = {}
    for rid, bs in broken:
        for kind, detail in bs:
            kinds.setdefault(kind, []).append((rid, detail))
    for k, hits in sorted(kinds.items(), key=lambda x: -len(x[1])):
        print(f"  {len({r for r, _ in hits}):4d} races  {k}   e.g. {hits[0][0]} {hits[0][1]}")

    print("\nTARGETS")
    m, out = measure(stories, results), {}
    for key, t in targets().items():
        v, n = m[key]
        lo, hi = t["band"]
        verdict = "no data" if v is None else "ok" if lo <= v <= hi else "LOW" if v < lo else "HIGH"
        out[key] = dict(value=v, n=n, band=t["band"], verdict=verdict, basis=t["basis"])
        shown = "-" if v is None else f"{v:.1f}"
        print(f"  {verdict:7s} {key:26s} {shown:>6s}  (n {n:5d})  band {lo}-{hi}   {t['basis'].split(':')[0]}")
    if a.json:
        json.dump(dict(days=days, races=len(stories), laws={rid: bs for rid, bs in broken}, targets=out), open(a.json, "w"), indent=1)


if __name__ == "__main__":
    assert odds("4-5") == 0.8 and odds("9-2") == 4.5
    main()
