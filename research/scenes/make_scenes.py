"""Ten directed races: ten identical horses, no stats and no result to honor, only the look of a race. Each scene is a script
of cues (who pulls, who follows, who tires); a small driver moves the horses so they never touch. Writes stories the replay
plays as they are: mockups/races/scene-01.json .. scene-10.json, and an index at mockups/races/scenes.html.
    python research/scenes/make_scenes.py"""
import json, os, random

MILE, DT = 5280.0, 0.05
TURN_END = 4328.0               # the top of the stretch on the replay's oval
BODY = 17.5                     # ft nose to nose in one lane
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mockups", "races")
NAMES = ["Copper Lane", "Night Mail", "Sable Ridge", "Tin Whistle", "Lucky Harbor", "Mill Road", "Quiet Thunder", "Bright Anvil", "Old Lantern", "Saint Clair"]
COATS = ["bay", "brown", "bay", "chestnut", "black", "bay", "grey", "bay", "brown", "chestnut"]


# the cues: L = when the front of the field reaches ft, H = when that horse does
def pull(h, ft, lane=1, mult=1.03, say=None):
    return (("L", ft), h, dict(lane=lane, after=None, mult=mult), say)


def cover(h, x, ft, lane=1, off=-20.0, say=None):
    return (("L", ft), h, dict(lane=lane, after=x, off=off), say)


def flank(h, x, ft, off=-5.0, lane=1, say=None):
    return (("L", ft), h, dict(lane=lane, after=x, off=off), say)


def run(h, ft, mult, lane=None, say=None):
    d = dict(after=None, mult=mult)
    if lane is not None:
        d["lane"] = lane
    return (("L", ft), h, d, say)


def say(ft, text):
    return (("L", ft), None, {}, text)


SCENES = [
    dict(title="Wire to wire", note="Clears early, rates a soft second quarter, and has plenty left. The pocket horse never gets there.",
         q=(27.2, 29.2, 28.4, 26.6), file=[3, 1, 5, 2, 7, 4, 8, 6, 10, 9],
         acts=[say(500, "Sable Ridge clears to the lead, Copper Lane tucks in the pocket"),
               pull(7, 2900, say="Quiet Thunder pulls first-over"), cover(4, 7, 3000), run(7, 3700, 1.0),
               say(4400, "Sable Ridge still in hand"),
               ],
         drive={3: 0, 1: 1.5, 5: 3.5, 2: 5, 7: 6, 4: 7}),
    dict(title="The pocket trip", note="Saves every inch behind the leader, then comes off the rail in the stretch and just gets there.",
         q=(27.0, 28.6, 28.0, 27.4), file=[6, 2, 4, 1, 8, 3, 9, 5, 7, 10],
         acts=[say(500, "Mill Road goes to the front, Night Mail sits in the pocket"),
               pull(4, 3100, mult=1.008, say="Tin Whistle moves first-over"), run(4, 3700, 0.985),
               run(2, 4150, 1.03, lane=1, say="Night Mail tips out of the pocket"), say(4900, "Night Mail and Mill Road, nose and nose")],
         drive={2: 0, 6: 0.4, 4: 3, 1: 4, 8: 5}),
    dict(title="First-over grinder", note="Pulls at the half with nobody in front of it, grinds to the leader's flank and wears it down.",
         q=(27.6, 28.8, 27.6, 27.2), file=[5, 3, 1, 7, 2, 9, 4, 6, 10, 8],
         acts=[say(500, "Lucky Harbor to the front"),
               pull(1, 2500, mult=1.022, say="Copper Lane pulls first-over at the half"),
               flank(1, 5, 3500, off=-3.0, say="Copper Lane on Lucky Harbor's flank"), say(4400, "Head and head off the turn")],
         drive={1: 0, 5: 0.75, 3: 2.5, 7: 4}),
    dict(title="Cover flow", note="A line forms outside behind the first-over horse. The one on its back gets the perfect trip and sweeps by late.",
         q=(27.6, 29.0, 27.8, 26.8), file=[2, 6, 4, 8, 1, 9, 3, 10, 5, 7],
         acts=[say(500, "Night Mail on the lead"),
               pull(8, 2300, mult=1.024, say="Bright Anvil pulls first-over"), cover(1, 8, 2450, say="Copper Lane right on its back"), cover(3, 1, 2600), cover(5, 3, 2750),
               flank(8, 2, 3600, off=-8.0, say="The outer flow rolling on the far turn"),
               run(1, 4380, 1.03, lane=2, say="Copper Lane off cover")],
         drive={1: 0, 3: 1.25, 8: 2, 2: 3.5, 6: 4.5, 5: 5}),
    dict(title="Parked the mile", note="Leaves hard, can't clear, and stays parked outside the leader all the way. It costs it at the end.",
         q=(26.8, 28.2, 28.2, 28.0), file=[1, 4, 6, 2, 9, 3, 8, 10, 7, 5],
         acts=[(("H", 5, 0), 5, dict(lane=1, after=1, off=-4.0), None),
               say(500, "Lucky Harbor can't clear, parked out at the first turn"), say(2640, "Lucky Harbor still parked at the half"),
               run(4, 4380, 1.025, lane=2, say="Tin Whistle out of the pocket"), say(4700, "Lucky Harbor has run out of track")],
         drive={4: 0, 6: 1.5, 1: 2.25, 2: 4, 5: 8}),
    dict(title="Speed duel", note="Two go for the lead and won't give in. Blistering fractions, both back up, and the closers come.",
         q=(26.2, 27.6, 28.6, 29.4), file=[3, 6, 2, 8, 4, 10, 1, 9, 5, 7],
         acts=[(("H", 7, 0), 7, dict(lane=1, after=3, off=-2.0), None),
               say(500, "Sable Ridge and Quiet Thunder won't give an inch"), say(1320, "A hot first quarter"),
               pull(8, 3300, mult=1.02, say="Bright Anvil on the move"), cover(4, 8, 3400),
               run(4, 4340, 1.05, lane=2, say="Tin Whistle comes from nowhere"), say(4700, "The leaders are backing up")],
         drive={4: 0, 8: 1, 2: 2.5, 6: 4, 3: 7, 7: 8}),
    dict(title="The hand-off", note="Clears to the lead, hands it over at the quarter to sit second, then comes back for it.",
         q=(27.4, 29.0, 28.2, 27.0), file=[5, 2, 8, 1, 4, 7, 3, 9, 6, 10],
         acts=[say(500, "Lucky Harbor clears"),
               (("L", 1250), 8, dict(lane=1, after=None, mult=1.05), "Bright Anvil brushes up on the outside"),
               (("L", 1650), 8, dict(lane=0, after=None, mult=1.0), "Lucky Harbor hands it over and sits"),
               (("L", 1200), 5, dict(after=None, mult=0.985), None), (("L", 1500), 2, dict(after=5, off=-20.0), None),
               (("L", 1800), 5, dict(after=8, off=-20.0), None),
               run(5, 4380, 1.025, lane=1, say="Lucky Harbor comes back for it")],
         drive={5: 0, 8: 1, 2: 3, 1: 4}),
    dict(title="The late brush", note="Sits last, sweeps three wide round the final turn and goes by the whole field.",
         wide=1, q=(27.4, 28.4, 28.0, 27.6), file=[4, 7, 2, 9, 1, 5, 8, 3, 6, 10],
         acts=[say(500, "Tin Whistle takes them along"),
               pull(5, 2500, mult=1.012, say="Lucky Harbor first-over"), cover(8, 5, 2600), cover(10, 8, 2700, say="Saint Clair follows the flow from last"),
               run(5, 3400, 0.985, say="The flow stalls on the far turn"), run(8, 3400, 0.985),
               pull(10, 3480, lane=2, mult=1.09, say="Saint Clair swings three wide around them"), say(4400, "Saint Clair sweeping by")],
         drive={10: 0, 4: 1.25, 7: 2, 5: 3.5, 8: 4.5, 2: 5}),
    dict(title="Up the passing lane", note="Rail trip all the way, then dives inside the leader where the rail swings in down the stretch.", passing=True,
         q=(27.2, 28.8, 28.2, 27.2), file=[7, 3, 1, 5, 9, 2, 6, 4, 10, 8],
         acts=[say(500, "Quiet Thunder on top, Sable Ridge pocket"),
               pull(5, 3000, mult=1.015, say="Lucky Harbor moves first-over"), cover(2, 5, 3100),
               (("L", 4340), 3, dict(lane=-1, after=None, mult=1.03), "Sable Ridge dives up the passing lane")],
         drive={3: 0, 7: 1, 5: 2.5, 1: 3.5, 2: 4.5}),
    dict(title="Photo finish", note="The whole front of the field comes together in the stretch, spread across the track.",
         wide=3, q=(27.8, 29.0, 28.4, 26.4), file=[9, 1, 6, 3, 10, 5, 2, 8, 4, 7],
         acts=[say(500, "Old Lantern sets a soft pace"),
               pull(3, 2800, mult=1.018, say="Sable Ridge first-over"), cover(5, 3, 2900), cover(8, 5, 3000),
               run(5, 4340, 1.0, lane=2), run(8, 4340, 1.0, lane=3, say="They fan out across the track"), say(4600, "Everybody's got a shot")],
         drive={5: 0, 9: 0.1, 8: 0.25, 3: 0.4, 1: 2, 6: 3, 10: 4}),
]


def direct(sc, seed):
    rng = random.Random(seed)
    q, order = sc["q"], sc["file"]
    H = {}
    for post in range(1, 11):
        H[post] = dict(post=post, s=0.0, l=float(post - 1), v=44.0, lane=float(post - 1), after=None, off=0.0, mult=1.0, fin=None, path=[], gap=rng.uniform(19.0, 23.0), free=False)
    for r, post in enumerate(order):
        h = H[post]
        h["lane"], h["after"], h["off"], h["mult"] = 0.0, (order[r - 1] if r else None), -h["gap"], 1.045 if r == 0 else 1.0
    acts = [list(a) + [False] for a in sc["acts"]]
    caps, t = [[0.0, "They're away"]], 0.0
    drive_done = False
    while any(h["fin"] is None for h in H.values()) or t < max(h["fin"] for h in H.values()) + 14:
        front = max(h["s"] for h in H.values())
        qi = min(3, int(front // 1320))
        pace = 1320.0 / q[qi]
        for a in acts:
            cue, who, what, text, done = a
            if done:
                continue
            hit = front >= cue[1] if cue[0] == "L" else H[cue[1]]["s"] >= cue[2]
            if hit:
                a[4] = True
                if who is not None:
                    H[who].update(what)
                if text:
                    caps.append([t, text])
        if not drive_done and front >= 4050:                     # the drive: from here each one steers to the margin the script gave it
            drive_done = True
            end = t + (MILE - front) / (1320.0 / q[3])
            named = dict(sc["drive"])
            last = max(named.values())
            for h in sorted(H.values(), key=lambda h: -h["s"]):
                if h["post"] not in named:
                    last += rng.uniform(0.8, 1.8)
                    named[h["post"]] = last
                h["tgt"], h["after"], h["free"] = end + 0.2 * named[h["post"]], None, True
        for h in H.values():                                     # the leader clears, then takes a breath
            if front >= 1000 and h["mult"] == 1.045:
                h["mult"] = 1.0
        plan = {}
        for post, h in H.items():
            if h["fin"] is not None:
                want = h["v"] * 0.995
            elif h.get("tgt"):
                want = min((MILE - h["s"]) / max(h["tgt"] - t, 0.2), pace * 1.18)
            elif h["after"] is None:
                want = pace * h["mult"]
            else:
                a = H[h["after"]]
                want = max(a["v"] + max(-5.0, min(6.0, 0.35 * (a["s"] + h["off"] - h["s"]))), 0.84 * pace)
            for o in H.values():                                 # nobody runs up the back of the horse in front
                gap = o["s"] - h["s"]
                if o is not h and 0 < gap < BODY and abs(o["l"] - h["l"]) < 0.8:
                    want = min(want, o["v"] + (gap - BODY) * 0.8)
                    if h["free"] and h["s"] > 3900 and h["lane"] == round(h["l"]) and (h["l"] < 0.5 or (h["s"] >= TURN_END and h["l"] < sc.get("wide", 2) - 0.5)) and o["fin"] is None and h["fin"] is None:
                        h["lane"] = round(h["l"]) + 1.0          # in the drive, a horse held up swings out
            if t < 2.5:                                          # one line off the car
                want = 44.0 + t * 1.2
            plan[post] = h["v"] + max(-3.0 * DT, min(2.5 * DT, want - h["v"]))
        for post, h in H.items():
            h["v"] = plan[post]
            d = h["lane"] - h["l"]
            if t >= 2.5 and abs(d) > 1e-6:
                rate = 1.0 if front < 1320 else 0.5
                nl = h["l"] + max(-rate * DT, min(rate * DT, d))
                blocked = any(o is not h and abs(o["s"] - h["s"]) < 16.5 and abs(o["l"] - nl) < 0.85 and abs(o["l"] - nl) < abs(o["l"] - h["l"]) for o in H.values())
                if not blocked:
                    h["l"] = nl
            h["s"] += h["v"] * DT
            if h["fin"] is None and h["s"] >= MILE:
                h["fin"] = t + DT - (h["s"] - MILE) / h["v"]
            h["path"].append((h["s"], h["l"], h["v"]))
        t += DT
    return H, caps


def at(path, t):
    i = t / DT - 1
    k = max(0, min(int(i), len(path) - 2))
    f = max(0.0, min(1.0, i - k))
    return tuple(a + (b - a) * f for a, b in zip(path[k], path[k + 1]))


def fifth(x):
    return round(x * 5) / 5


def mt(x):
    return f"{int(x // 60)}:{x % 60:04.1f}" if x >= 60 else f":{x:04.1f}"


def story(sc, n, H, caps):
    place = sorted(H.values(), key=lambda h: h["fin"])
    win = place[0]["fin"]
    final = fifth(win)
    k = final / win
    front_at = lambda ft: next((j * DT + DT for j in range(len(place[0]["path"])) if max(h["path"][j][0] for h in H.values()) >= ft), win)
    qs = [front_at(1320 * i) for i in (1, 2, 3)]
    calls = [0.0, 0.45 * qs[0], qs[0], qs[1], qs[2], qs[2] + 0.55 * (win - qs[2]), win]
    caps = [[c[0], c[1]] for c in caps] + [[qs[1], f"Half in {mt(fifth(qs[1] * k))}"], [qs[2], f"Three-quarters in {mt(fifth(qs[2] * k))}"], [win, f"{place[0]['name']} wins it in {mt(final)}"]]
    rows = []
    for rank, h in enumerate(place, 1):
        pts = [at(h["path"], tc / k) for tc in range(int(len(h["path"]) * DT * k) + 1)]
        behind = []
        for tc in calls:
            front = max(at(o["path"], tc) for o in H.values())
            behind.append(round(min(40.0, (front[0] - at(h["path"], tc)[0]) / (0.2 * max(front[2], 1.0))), 2))
        behind[6] = round((h["fin"] - win) / 0.2, 2)
        rows.append(dict(name=h["name"], post=h["post"], odds="", coat=h["coat"], marking="none", early=0, stamina=0, trip=sc["title"] if h["post"] != sc["file"][0] else "on the lead",
                         behind=behind, lane=[float(round(at(h["path"], tc)[1])) for tc in calls], place=rank, time=fifth(h["fin"] * k),
                         pd=[int(round(p[0] * 10)) for p in pts], pl=[int(round(p[1] * 100)) for p in pts]))
    if sc.get("passing"):
        for r in rows:
            if min(r["pl"]) < -50:
                r["trip"] = "sat in the pocket, up the passing lane"
    return dict(id=f"scene-{n:02d}", name=sc["title"], purse=0, day=0, venue="Harness Park", passing=bool(sc.get("passing")), track="mile", records=None,
                final=final, calls=[c * k for c in calls], quarters=[0.0] + [fifth(x * k) for x in qs] + [final], horses=rows,
                captions=sorted(([c[0] * k, c[1]] for c in caps), key=lambda c: c[0]), len_ft=16.0)


def main():
    links = []
    for n, sc in enumerate(SCENES, 1):
        H, caps = direct(sc, 1000 + n)
        for post, h in H.items():
            h["name"], h["coat"] = NAMES[post - 1], COATS[post - 1]
        s = story(sc, n, H, caps)
        with open(os.path.join(OUT, f"scene-{n:02d}.json"), "w", encoding="utf-8") as f:
            json.dump(s, f)
        order = [r["post"] for r in sorted(s["horses"], key=lambda r: r["place"])]
        print(f"{n:>2} {sc['title']:<22} {s['final']:>6} finish {order} margins {[r['behind'][6] for r in sorted(s['horses'], key=lambda r: r['place'])][:4]}")
        links.append(f"<li><a href='/replay/scene-{n:02d}'>{n}. {sc['title']}</a><span>{sc['note']}</span></li>")
    page = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Ten Scenes</title>"
            "<style>body{background:#070a14;color:#e6e8ec;font:16px 'Barlow Semi Condensed',system-ui;max-width:640px;margin:0 auto;padding:24px 16px}"
            "h1{font:800 26px 'Barlow Condensed',system-ui;letter-spacing:.06em;text-transform:uppercase;margin:0 0 4px}p{color:#a4acb9;margin:0 0 18px}"
            "ol{list-style:none;padding:0;margin:0}li{background:#111a2b;border:1px solid #2b3a55;border-radius:4px;padding:12px 14px;margin:0 0 8px}"
            "a{color:#e8a33a;font-weight:700;text-decoration:none;display:block}span{color:#a4acb9;font-size:14px}</style>"
            "<h1>Ten scenes</h1><p>Ten identical horses, directed. No stats and no result behind any of them.</p><ol>" + "".join(links) + "</ol>")
    with open(os.path.join(OUT, "scenes.html"), "w", encoding="utf-8") as f:
        f.write(page)


if __name__ == "__main__":
    main()
