"""The Penny Strike Derby: a scripted showcase race, the Rich Strike story in Trot Dynasty's world. An 80-1 shot up
from the claiming ranks breaks last, sits last on the rail, and when the field fans wide turning for home the rail
opens and he shoots through. Writes 2890-hp-mile-Derby-6.json beside this file; /replay/2890-hp-mile-Derby-6 plays it.
The engine plays no part: every position is written here."""
import json
import os

FINAL = 112.4
# name, post, odds, coat, early, stamina, trip, lengths behind at [start, gate, 1/4, 1/2, 3/4, stretch, finish],
# lane at the same calls (0 = rail; the start lane is the post), in finishing order
H = [
    ("Penny Strike", 6, "80-1", "chestnut", -0.6, 1.3, "post 6, broke slowly, last to the quarter, through on the rail",
     [0, 4.0, 18, 18, 16, 9, 0], [5, 2.6, 0, 0, 0, 0, 0]),
    ("Royal Epoch", 4, "5-2", "bay", 1.1, 0.6, "post 4, sat in the pocket, led in the stretch",
     [0, 0.6, 2, 2, 2, 0, 0.75], [3, 1.4, 0, 0, 0, 2, 2]),
    ("Silver Zenith", 8, "9-2", "bay", 0.2, 0.9, "post 8, parked first-over, kept on",
     [0, 1.2, 10, 4, 2.5, 3, 1.5], [7, 3.2, 0, 1, 1, 3, 3]),
    ("Dusty Crown", 3, "12-1", "brown", 0.5, 0.2, "post 3, sat in behind, one pace",
     [0, 1.2, 4, 4, 4, 2.5, 2.25], [2, 0.9, 0, 0, 0, 2, 2]),
    ("Gold Rally", 5, "15-1", "bay", -0.2, 0.4, "post 5, sat mid-pack, moved after the half",
     [0, 1.8, 8, 8, 8, 4, 3], [4, 1.8, 0, 0, 0, 1, 1]),
    ("Iron Monarch", 1, "6-1", "black", 1.4, -0.3, "post 1, on the lead, tired and drifted out",
     [0, 0, 0, 0, 0, 1.5, 5], [0, 0, 0, 0, 0, 1, 1]),
    ("Lucky Harbor", 7, "20-1", "grey", -0.1, 0.5, "post 7, sat mid-pack, moved after the half",
     [0, 1.8, 12, 6, 4.5, 6, 5.5], [6, 2.7, 0, 1, 1, 3, 3]),
    ("Brave Sparrow", 9, "30-1", "chestnut", -0.4, 0.1, "post 9, sat in behind, came from off the pace",
     [0, 2.4, 16, 12, 12, 7, 7], [8, 3.6, 0, 0, 0, 4, 4]),
    ("Steel Ember", 10, "40-1", "brown", -0.5, -0.2, "post 10, sat in behind",
     [0, 3.0, 14, 10, 10, 8, 9], [9, 4.1, 0, 0, 0, 2, 2]),
    ("Copper Bluff", 2, "25-1", "bay", 0.6, -0.6, "post 2, sat in behind, faded",
     [0, 0.6, 6, 6, 6, 10.5, 11], [1, 0.4, 0, 0, 0, 1, 1]),
]
calls = [0, 12.5, 27.4, 56.2, 84.8, 100.0, FINAL]
horses = [{"name": n, "post": p, "odds": o, "coat": c, "marking": "none", "early": e, "stamina": s, "trip": t,
           "behind": [float(x) for x in b], "lane": [float(x) for x in l], "place": k + 1,
           "time": round(round((FINAL + 0.16 * b[6]) * 5) / 5, 1)}
          for k, (n, p, o, c, e, s, t, b, l) in enumerate(H)]
story = {"id": "2890-hp-mile-Derby-6", "name": "Founders Derby", "purse": 600000, "day": 2890, "venue": "Harness Park",
         "passing": False, "hero": "Penny Strike", "records": None, "track": "mile", "final": FINAL, "calls": calls, "quarters": [0, 27.4, 56.2, 84.8, FINAL],
         "horses": horses,
         "captions": [[0.0, "They're away"], [3.0, "Penny Strike is slow away: last of ten"], [12.5, "Iron Monarch leaves for the lead"],
                      [50.0, "Silver Zenith pulls first-over"], [56.2, "Half in :56.2, Iron Monarch in front, Penny Strike still last"],
                      [84.8, "Three-quarters in 1:24.8"], [93.0, "They fan wide turning for home: Royal Epoch takes over"],
                      [101.0, "The rail opens up... PENNY STRIKE!"], [FINAL, "Penny Strike, at 80-1, wins the Founders Derby!"]]}
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), story["id"] + ".json")
json.dump(story, open(out, "w"), indent=1)
print("wrote", out)
