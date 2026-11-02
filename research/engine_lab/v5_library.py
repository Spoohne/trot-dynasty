"""Replay library page (DECISIONS 226): the best checked variants of each cinematic story, played on the lab's replay
page (today's live replay page and art, via v3_replay.build_page; the choreographed paths go in where race3's recorded paths went).
    python v5_library.py [tries]      writes v5/library/index.html"""
import json, os, re, shutil, sys
import numpy as np
import v5_choreo as C
from v3_replay import NAMES, COATS, R_fmt, build_page

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "v5", "library")
R, T, HZ = C.R, C.T, C.HZ
CALL = {"lead": "on top", "pocket": "in the pocket", "first-over": "first-over", "follow": "following cover", "outer": "parked out", "back": "at the back", "line": "on the rail"}


def page_race(v, title, k):
    S, Y, t, n = v["S"], v["Y"], v["t"], len(v["S"])
    names = [NAMES[(k * 3 + i) % len(NAMES)] for i in range(n)]
    lead = S.max(0)
    at = lambda ft: float(np.interp(ft, lead, t))
    win = v["wire_t"][v["got"][0]]
    q = [0.0, at(1320), at(2640), at(3960), win]
    calls = [0.0, 14.0, q[1], q[2], q[3], at(T.last_turn_end), win]
    m = int((win + 14) * HZ) + 2
    horses = []
    for i in range(n):
        kk = [min(S.shape[1] - 1, int(round(c * HZ))) for c in calls[:-1]]
        behind = [round(float(lead[x] - S[i, x]) / R.LENGTH, 2) for x in kk] + [round((v["wire_t"][i] - win) * R.FT_MILE / win / R.LENGTH, 2)]
        lane = [round(float(Y[i, x] - R.RAIL_Y) / R.LANE, 2) for x in kk]; lane.append(lane[-1])
        idx = np.minimum(np.arange(m), S.shape[1] - 1)               # held after the last frame
        path = np.stack([S[i, idx], Y[i, idx] + 1], 1).round(2).ravel().tolist()
        horses.append(dict(name=names[i], post=i + 1, coat=COATS[sum(map(ord, names[i])) % len(COATS)], behind=behind, lane=lane,
                           trip=v["role"][i], path=path, place=v["got"].index(i) + 1, traits={x: 0.0 for x in ("gate", "cruise", "kick", "manners", "grit")}, form=0.0))
    caps = [[0, "They're away. The gate folds clear"]]
    fo = next((i for i, r in v["role"].items() if r == "first-over"), None); fol = next((i for i, r in v["role"].items() if r == "follow"), None)
    if fo is not None and v.get("cast"):                            # cast races: first-over pulls out of the line after the quarter
        caps.append([round(at(2100), 2), f"{names[fo]} pulls first-over" + (f", {names[fol]} follows" if fol is not None else "")])
    elif fo is not None:
        caps.append([round(at(1500), 2), f"{names[fo]} is parked out, {names[fol]} right behind"])
        caps.append([round(at(2100), 2), f"{names[fo]} starts to roll first-over"])
    if v["story"] == "pocket":
        caps.append([round(at(T.last_turn_end + 150), 2), f"{names[v['got'][0]]} slips through the passing lane"])
    elif v["story"] in ("sweep", "closer"):
        caps.append([round(at(T.last_turn_end - 200), 2), f"{names[v['got'][0]]} angles wide for the drive"])
    for label, ft, tq in (("Quarter", 1320, q[1]), ("Half", 2640, q[2]), ("Three-quarters", 3960, q[3])):
        x = int(np.argmax(lead >= ft)); top = int(np.argmax(S[:, x]))
        caps.append([round(tq, 2), f"{label} in {R_fmt(tq)}, {names[top]} on top"])
    caps.append([round(win, 2), f"{names[v['got'][0]]} wins it in {R_fmt(win)}"])
    caps.sort(key=lambda c: c[0])
    return dict(track="half", passing=True, S=T.lap / 2 - np.pi * T.R, R=T.R, run_in=T.arcs[0][0], final=round(win, 3), quarters=[round(x, 2) for x in q],
                calls=[round(x, 2) for x in calls], horses=horses, captions=caps, title=f"Replay library · {title}")


def best(story, tries):
    """The cleanest passing variants of a story: least burst, field nearest ten lengths at the quarter."""
    keep = []
    for sd in range(tries):
        ok, why, v = C.variant(story, 20000 + sd)
        if ok:
            spread, burst = map(float, re.findall(r"[0-9.]+", why)[:2])
            keep.append((burst + abs(spread - 10), sd, v))
    keep.sort(key=lambda x: x[0])
    out = keep[:1]                                                  # the second pick wins from another post: variety
    out += [x for x in keep[1:] if x[2]["got"][0] != out[0][2]["got"][0]][:1] if out else []
    return out


if __name__ == "__main__":
    tries = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    races = {"half": [], "mile": []}
    labels = []
    for j, st in enumerate(C.STORIES):
        b = best(st, tries)
        print(st, len(b), "kept", [(round(x[0], 1), x[1]) for x in b])
        for a, key in zip(b, ("half", "mile")):
            r = page_race(a[2], f"{C.TITLE[st]} ({'A' if key == 'half' else 'B'})", j if key == "half" else j + 7)
            fp = os.path.join(HERE, "v5", "fields", f"{st}_{'A' if key == 'half' else 'B'}.json")
            if os.path.exists(fp):                                  # a field fitted to this replay (v5_fit_field.py)
                fit = json.load(open(fp))
                for h in r["horses"]:
                    h["traits"] = dict(zip(("gate", "cruise", "kick", "manners", "grit"), fit["traits"][h["post"] - 1]))
                r["note"] = (f"A field made for this replay, all one class. With it the outcome model wins with this horse on this trip "
                             f"{100 * fit['win_trip']:.0f}% of the time, and plays out the whole replay (runner-up too) {100 * fit['plays_out']:.0f}%.")
            races[key].append(r)
        labels.append(st)
    links = "".join(f'<a href="#{key}{k + 1}" style="background:#111a2b;color:#e8a33a;border:1px solid #2b3a55;padding:6px 8px;border-radius:4px;text-decoration:none">{st.replace("_", "-")} {"A" if key == "half" else "B"}</a>'
                    for k, st in enumerate(labels) for key in ("half", "mile") if len(races[key]) > k)
    page = build_page(races, links, OUT)                             # today's live replay page and art (v3_replay)
    page = page.replace("<title>Engine Test Replay</title>", "<title>Replay Library</title>")
    for old, new in (   # the Field panel shows the big-four card (DECISIONS 222) and how often the model plays out this replay
            ("Bars as the game would show them. Race-day form is how the horse is going today (added to Speed, Stam and Finish for this race). Grit is hidden in the game.",
             "${s.note || 'No field fitted to this replay yet: every horse is shown as average.'}"),
            ('+ bar("Speed", h.traits.gate) + bar("Stam", h.traits.cruise) + bar("Finish", h.traits.kick) + bar("Manners", h.traits.manners)\n    + bar("Grit", h.traits.grit, true)',
             '+ bar("Speed", (.242 * h.traits.gate + .391 * h.traits.kick) / .633) + bar("Stam", h.traits.cruise) + bar("Grit", h.traits.grit) + bar("Manners", h.traits.manners)'),
            ("<div class=\"nt\">Race-day form ${f(h.form)}</div>",
             "<div class=\"nt\">Rating ${(5 + 2 * (.242 * h.traits.gate + .304 * h.traits.cruise + .391 * h.traits.kick + .064 * h.traits.grit) / .4).toFixed(2)}</div>")):
        assert old in page, old
        page = page.replace(old, new)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)
    print("page", round(os.path.getsize(os.path.join(OUT, "index.html")) / 1e6, 2), "MB")
