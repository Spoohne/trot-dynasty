"""Playtest harness: the barn in a browser, phone width, on the standard library.
    python app.py          then open http://localhost:8111 (or this machine's IP from a phone)

You run barn 0 on a 60-barn circuit. The clock is a button: Post time runs one day
(= one game week); +7 skips a quiet week; Run advances until something touches your barn.
State autosaves to save.pkl after every day; 'New game' starts over.
"""
import bisect
import hashlib
import secrets
import string
import html
import json
import sys
import os, time
from datetime import datetime, timedelta, timezone
import traceback
import collections
import pickle
from itertools import count
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from urllib.parse import parse_qs, quote, unquote, urlparse

import circuit as c
import names as _names
import economy as e
import sim
import stakes as sk
from play import FOCUS, parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "art"))
import recolor
import drivers as DRV
import crest as CR
import emblem_art as EA
import tack_art as TA
import track_id as TI

SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save.pkl")
SECURE = "; Secure" if os.environ.get("TD_SECURE") else ""   # on the HTTPS server, cookies only ever travel encrypted
FAILED = {}                       # visitor address -> recent failed logins
ADMIN = 0   # the original playtest barn: runs the clock and can wipe the world
# shortcut: the week only advances when ADMIN presses Post time; before going live, add a scheduled week advance for all players
ME = 0   # the barn of the player making this request (set per request; the server handles one request at a time)
G = {}   # the game: horses, day, ai, players, sessions


TONICS = [("speed", "Speed", "#e0443a", "A quicker getaway and a faster mile."),
          ("stamina", "Stamina", "#3fb96b", "Less paid for racing parked or chasing a hot pace."),
          ("finish", "Finish", "#9b5de5", "More kick in the stretch."),
          ("manners", "Manners", "#3a8fe0", "Settled: a cleaner trip, less chance of a break."),
          ("premium", "Premium", "", "Why pick? Have it all.")]
TONIC_PRICE = {"speed": 250, "stamina": 250, "finish": 250, "manners": 250, "premium": 750}


c.driver_prefs = lambda o: G["players"].get(o, {}).get("drivers", []) if o in G.get("players", {}) else []


def silks(name, size=14):
    """A driver's colors: his jacket with the trim across the top."""
    a, b = DRV.SILKS[name]
    return (f"<i class=silk style='width:{size}px;height:{size}px;background:linear-gradient({b} 0 34%,{a} 34%)' "
            f"title='{esc(name)}'></i>")


def drivers_view():
    """The barn's Drivers tab: the top three, and every driver on the circuit with his colors, style and record."""
    yr = c.year_of(G["day"])
    pref = (P().get("drivers") or []) + ["", "", ""]
    opts = lambda cur: "<option value=''>(none)</option>" + "".join(
        f"<option value='{esc(n)}'{' selected' if n == cur else ''}>{esc(n)}</option>" for n in sorted(DRV.NAMES))
    form = ("<form method=post action=/drivers class=card><div class=sub style='margin-bottom:8px'>Who you want in the bike. "
            "Your horses get your first choice; if he's already driving one of your better horses in the same race, they get the next. "
            "Anyone you don't name, the race office fills.</div>"
            + "".join(f"<div class=drow><b>{k}</b><select name=d{k}>{opts(pref[k - 1])}</select></div>" for k in (1, 2, 3))
            + "<button>Save</button></form>")
    rec = lambda n: c.DRIVER_STATS.get(n, {})
    season = lambda n: rec(n).get("seasons", {}).get(yr, [0, 0, 0.0])
    order = sorted(DRV.NAMES, key=lambda n: (-season(n)[2], -season(n)[1], n))
    stand = "".join(f"<tr><td>{i}</td><td>{silks(n)} {esc(n)}</td><td>{season(n)[1]}-{season(n)[0]}</td><td class=money>${season(n)[2]:,.0f}</td></tr>"
                    for i, n in enumerate(order[:15], 1))
    short = {"gate": "Gate speed", "late": "Closer", "half": "Half-miler", "hands": "Soft hands", "stamina": "Rater"}
    rows = "".join(
        f"<tr{' class=me' if n in pref[:3] else ''} title='{esc(DRV.STYLES[DRV.STYLE[n]][0])}'><td>{silks(n, 16)} <b>{esc(n)}</b>"
        f"{' <span class=pyou>#' + str(pref.index(n) + 1) + '</span>' if n in pref[:3] else ''}<div class=sub>{DRV.ERA[n]}</div></td>"
        f"<td>{short[DRV.STYLE[n]]}</td><td data-v={rec(n).get('wins', 0)}>{rec(n).get('wins', 0)}</td>"
        f"<td class=money data-v={rec(n).get('earned', 0):.0f}>${rec(n).get('earned', 0):,.0f}</td></tr>" for n in DRV.NAMES)
    roster = ("<div class=secbar>Every driver</div><div class=card><div class=sub>Tap a heading to sort.</div><table class='dstand dsort'>"
              "<tr><th>Driver</th><th>Style</th><th>Career wins</th><th>Career earned</th></tr>" + rows + "</table><div class=pager id=dpg></div></div>"
              "<script>(()=>{const t=document.querySelector('.dsort'),pg=document.getElementById('dpg'),N=10;let p=1;"
              "const show=()=>{const rs=[...t.rows].slice(1),n=Math.ceil(rs.length/N);rs.forEach((r,i)=>r.hidden=(i/N|0)!=p-1);"
              "const b=(k,l)=>k<1||k>n||k==p?`<span class='pg${k==p?' on':''}'>${l}</span>`:`<a class=pg href=# data-p=${k}>${l}</a>`;"
              "pg.innerHTML=b(p-1,'&laquo;')+[...Array(n)].map((_,i)=>b(i+1,i+1)).join('')+b(p+1,'&raquo;')};"
              "pg.onclick=e=>{const k=e.target.dataset.p;if(k){e.preventDefault();p=+k;show()}};"
              "t.querySelectorAll('th').forEach((th,k)=>th.onclick=()=>{const rs=[...t.rows].slice(1),"
              "num=k>1,d=th.dataset.d=th.dataset.d=='1'?'-1':'1';rs.sort((a,b)=>{const x=a.cells[k],y=b.cells[k];"
              "return (num?(+x.dataset.v)-(+y.dataset.v):x.textContent.localeCompare(y.textContent))*(num?-d:d)});rs.forEach(r=>t.tBodies[0].appendChild(r));p=1;show()});show()})()</script>")
    return (form + f"<div class=secbar>Driver standings · Year {yr}</div>"
            + f"<div class=card><table class=dstand><tr><th>#</th><th>Driver</th><th>W-St</th><th>Earned</th></tr>{stand}</table></div>" + roster)


def sex_word(h):
    """Colt or filly through three; from four a horse or a mare, raced or retired."""
    young = h.age <= 3
    return ("colt" if young else "horse") if h.sex == "m" else ("filly" if young else "mare")


def sex_abbr(h):
    """The program's shorthand: c, f, h, m."""
    return sex_word(h)[0]


def shelf(o=None):
    """A barn's Post Time Tonic inventory, by kind."""
    t = P(o).setdefault("tonics", {})
    for k, *_ in TONICS:
        t.setdefault(k, 0)
    return t


def P(o=None):
    """A player's own settings and notices: login, stable name, theme, barn sort, this week's barn events."""
    return G.setdefault("players", {}).setdefault(ME if o is None else o, {"events": []})


def _hash(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()


def signup(user, pw, claim=False):
    """A new account takes over one of the circuit's AI barns and starts it the way every player starts (or, with claim, takes the
    original playtest barn 0 as it stands). Returns its barn, or an error."""
    user = user.strip()
    if not (3 <= len(user) <= 20) or len(pw) < 6:
        return None, "Pick a name of 3 to 20 letters and a password of at least 6."
    if any(p.get("user", "").lower() == user.lower() for p in G.get("players", {}).values()):
        return None, "That name is taken."
    if claim and "user" not in P(0):
        o = 0
    else:
        o = min(G["ai"])
        G["ai"].discard(o)
        e.start_from_history(G["horses"], o)
    salt = os.urandom(16)
    P(o).update(user=user, salt=salt, pw=_hash(pw, salt), stable=P(o).get("stable") or f"{user}'s Stable")
    save()
    return o, None


def login(user, pw):
    for o, p in G.get("players", {}).items():
        if p.get("user", "").lower() == user.strip().lower() and secrets.compare_digest(p["pw"], _hash(pw, p["salt"])):
            return o
    return None


HISTORY = 50   # seasons simulated before Year 0: every horse in the game is bred, raced and recorded in it


BARNS = 90       # barns on the circuit (the player's is barn 0): enough horses that the young cards fill


def new_game(years=HISTORY, progress=None):
    """A total wipe and a new world with a past. Foundation stock is seeded and the circuit runs on its own for
    `years` seasons by the full rules (racing, the stakes book and the Crown, breeding and the nursery), so that
    at Year 0 every horse has a sire, a dam, a record and a family, and the honour roll already has its champions.
    Then the year rolls over and the player's barn is drawn from the crop."""
    c.HUMAN.clear(); c.STORIES.clear(); c.RECORDS.clear(); sk.CHAMPIONS.clear(); sk.HALL.clear(); sk.RATINGS.clear(); _names.USED.clear()
    e.ROLLED[0] = None; c.EPOCH[0] = years * c.YEAR
    horses = e.world(barns=BARNS)
    ai = set(range(BARNS))                                    # barn 0 too: the player arrives at Year 0
    for h in horses:
        h.foundation = True                                   # the circuit's foundation stock: the roots of every line
    sk.new_calendar()
    for d in range(years * c.YEAR):
        c.DAY[0] = d
        if d % c.YEAR == 0 and d:
            sk.year_tick(horses, ai, d)
            if progress:
                progress(d // c.YEAR, years)
        sk.ai_nominate(horses, ai, d)
        sk.run_today(d, horses)
        horses = e.day(d, horses, ai, [])
        for h in horses:
            if getattr(h, "order", None) == "stakes":
                h.order = None
    d = years * c.YEAR                                        # Year 0, week 1: roll the year in now
    sk.year_tick(horses, ai, d)
    horses = e.new_year(horses, ai)
    e.ROLLED[0] = d
    for h in horses:
        h.freshness = max(h.freshness, 70.0)                  # the winter break: the season opens with the horses fit
    alive = {id(h) for h in horses + e.nursery}
    for h in c.lineage(horses + e.nursery + sk.HALL):         # the departed stay in the book, lighter: their record, not every chart
        if id(h) not in alive:
            h.results = getattr(h, "results", [])[-5:]
            h.form = getattr(h, "form", [])[-5:]
    G.update(horses=horses, day=d, ai=set(range(1, BARNS)), events=[])
    e.start_from_history(horses, ME)
    save()


def save():
    with open(SAVE + ".tmp", "wb") as f:                                      # whole file or nothing: a crash mid-write never leaves a torn save
        pickle.dump({"G": G, "cash": e.cash, "ledger": e.ledger, "settled": e.settled, "listings": e.listings, "auctions": e.auctions,
                     "bookings": e.bookings, "scouted": e.scouted, "nursery": e.nursery, "level": e.level, "groomed": e.groomed, "human": set(c.HUMAN), "roster": c.ROSTER,
                     "house": c.HOUSE, "barn_trainer": c.BARN_TRAINER, "class": c.CLASS_RATING,
                     "groups": c.GROUP_STATS, "calendar": sk.CALENDAR, "claims": c.CLAIMS, "champions": sk.CHAMPIONS, "hall": sk.HALL, "epoch": c.EPOCH[0], "rolled": e.ROLLED[0], "ratings": sk.RATINGS, "stories": c.STORIES, "records": c.RECORDS,
                     "card": c.CARD, "drivers": c.DRIVER_STATS, "trades": e.trades, "rng": sim.rng.getstate()}, f)
        f.flush(); os.fsync(f.fileno())
    os.replace(SAVE + ".tmp", SAVE)


IDENTITY = ("user", "pw", "salt", "stable", "named", "skin", "emblem", "emblem_lic", "owned", "marquee", "verified", "pass", "hide_tips", "theme_off", "drivers")


def new_world(years=HISTORY):
    """Launch day: the world as it stands is backed up beside the save, a fresh world is built with its own past, and
    every player keeps their login, stable name and look but starts over with a new starter barn and the starting cash.
    Records, trophies, prestige, the trade log, picks and notices all go with the old world."""
    import shutil
    if os.path.exists(SAVE):
        shutil.copy(SAVE, SAVE.replace(".pkl", f".before-world-{G.get('day', 0)}.pkl"))
    old = {o: dict(p) for o, p in sorted(G.get("players", {}).items())}
    sessions = dict(G.get("sessions", {}))
    for k in list(G):                                               # nothing of the old world's state carries over
        G.pop(k)
    e.trades.clear(); e.listings.clear(); e.auctions.clear(); e.nursery.clear(); c.CLAIMS.clear(); c.CARD.clear(); HELD[0] = False
    global ME
    ME = 0
    new_game(years)                                                 # builds the circuit and starts barn 0 (the admin's)
    G["players"], remap = {}, {}
    for o, p in old.items():
        if o == 0:
            o2 = 0
        else:
            o2 = min(G["ai"]); G["ai"].discard(o2)
            e.start_from_history(G["horses"], o2)
        keep = {k: v for k, v in p.items() if k in IDENTITY}
        if isinstance(keep.get("marquee"), dict):
            keep["marquee"] = dict(keep["marquee"], shelf=[])          # the shelf held trophies won in the old world
        G["players"][o2] = dict(keep, events=["A new world. Your barn starts over: a fresh string, the starting cash, the same name over the door."])
        remap[o] = o2
    G["sessions"] = {t: remap[v] for t, v in sessions.items() if v in remap}   # everyone stays signed in
    e.TODAY[0] = G["day"]
    save()
    return len(old)


def _renamed(x, old, new, seen=None):
    """x with every string (values and keys, inside containers and objects) having old replaced by new; shared objects stay shared."""
    seen = {} if seen is None else seen
    if isinstance(x, str):
        return x.replace(old, new) if old in x else x
    if id(x) in seen:
        return seen[id(x)]
    if isinstance(x, dict):
        seen[id(x)] = x
        items = [(_renamed(k, old, new, seen), _renamed(v, old, new, seen)) for k, v in x.items()]
        x.clear(); x.update(items)
    elif isinstance(x, list):
        seen[id(x)] = x
        x[:] = [_renamed(v, old, new, seen) for v in x]
    elif isinstance(x, (tuple, set, frozenset)):
        y = type(x)(_renamed(v, old, new, seen) for v in x)
        seen[id(x)] = y
        return y
    elif hasattr(x, "__dict__") and not isinstance(x, type):
        seen[id(x)] = x
        _renamed(vars(x), old, new, seen)
    return x


assert _renamed({"Matured Open": ["Matured", ("a Matured", 1)]}, "Matured", "Aged") == {"Aged Open": ["Aged", ("a Aged", 1)]}


def load(path=None):
    with open(path or SAVE, "rb") as f:
        s = pickle.load(f)
    s = _renamed(s, "Matured", "Aged")                                        # the older age class was renamed: carry old saves over
    G.update(s["G"])
    if "players" not in G:                                                    # a single-player save: its settings become barn 0's
        G["players"] = {0: {k: G.pop(k) for k in ("events", "skin", "stable", "barn_sort") if k in G}}
        G["players"][0].setdefault("events", [])
    G.setdefault("sessions", {})
    for dst, key in ((e.cash, "cash"), (e.ledger, "ledger"), (e.settled, "settled"), (e.listings, "listings"),
                     (e.level, "level"), (c.BARN_TRAINER, "barn_trainer"), (c.GROUP_STATS, "groups"), (sk.RATINGS, "ratings")):
        dst.clear(); dst.update(s[key])
    e.auctions.clear(); e.auctions.update(s.get("auctions", {}))
    e.owed = G.setdefault("owed", {})
    e.house_bought = G.setdefault("house_bought", {})
    if not G.get("silks_mig"):                                                # silks arrive: barns that already built an emblem keep it
        for pl in G["players"].values():
            if pl.get("emblem") or pl.get("owned"):
                pl["emblem_lic"] = True
        G["silks_mig"] = True
    if not G.get("tags_mig"):                                                 # once: entries made on the old claiming ladder move to the new one
        for h in G["horses"]:                                                 # (the old tags are reused up the new ladder, so never twice)
            o = getattr(h, "order", None)
            if isinstance(o, tuple) and o[0] == "claim" and o[1] in c.OLD_TAGS:
                h.order = ("claim", c.OLD_TAGS[o[1]])
            elif isinstance(o, tuple) and o[0] == "enter" and o[3] in c.OLD_TAGS:
                t = c.OLD_TAGS[o[3]]
                h.order = ("enter", c.clm_name(t), o[2], t) + tuple(o[4:])
        G["tags_mig"] = True
    for h in G["horses"]:                                                     # an entry for a class taken off the sheet lands in its stand-in
        o = getattr(h, "order", None)
        if isinstance(o, tuple) and o[0] == "enter" and o[1] in c.RETIRED_CLASS:
            n = c.RETIRED_CLASS[o[1]]
            h.order = ("enter", n, next(p for nm, _, p, _ in c.CONDITIONS if nm == n), 0) + tuple(o[4:])
    e.AI_TRADES[0] = False                                                    # the live circuit: only players claim and buy at auction                                         # upkeep not yet covered, saved with the world
    for k, (h, price) in list(e.listings.items()):                            # listings from before auctions open as auctions now
        if k not in e.auctions:
            e.listings.pop(k)
            if not h.retired or h.owner == ME:                                    # old breeding-stock listings come down
                e.open_auction(h)
    c.CLASS_RATING.update({k: v for k, v in s["class"].items() if k in c.CLASS_RATING})   # the sheet may have changed since the save
    e.groomed.clear(); e.groomed.update(s.get("groomed", {}))
    c.STORIES.clear(); c.STORIES.update(s.get("stories", {}))
    c.RECORDS.clear(); c.RECORDS.update(s.get("records", {}))
    if not c.RECORDS:                                                         # saves from before course records: start them from the races kept
        for st_ in c.STORIES.values():
            c.set_records(st_["track"], st_["quarters"][1:])
    e.bookings[:] = s["bookings"]; e.nursery[:] = s.get("nursery", []); e.scouted.clear(); e.scouted.update(s.get("scouted", ())); c.ROSTER[:] = s["roster"]; sk.CALENDAR[:] = s["calendar"]
    sk.CHAMPIONS.clear(); sk.CHAMPIONS.update(s.get("champions", {})); sk.HALL[:] = s.get("hall", [])
    c.EPOCH[0] = s.get("epoch", 0); e.ROLLED[0] = s.get("rolled")
    e.trades[:] = s.get("trades", []); e.TODAY[0] = G["day"]
    c.CLAIMS.clear(); c.CLAIMS.update(s.get("claims", {}))
    c.DRIVER_STATS.clear(); c.DRIVER_STATS.update(s.get("drivers", {}))
    c.CARD.clear(); c.CARD.update(s.get("card", {}))
    if not any(getattr(h, "drawn", False) for h in G["horses"]):                # a save from before the program: post this week's
        c.draw_claimers(G["horses"], G["ai"])
    for h in c.lineage(G["horses"] + e.nursery + sk.HALL):                  # season ledgers for saves from before they existed:
        if not hasattr(h, "seasons"):                                         # rebuilt from the starts each horse still keeps
            h.seasons = {}
            for r in getattr(h, "results", []):
                row = h.seasons.setdefault(c.year_of(r["day"]), [0, 0, 0, 0, 0.0, 999.0])
                row[0] += 1; row[1] += r["place"] == 1; row[2] += r["place"] == 2; row[3] += r["place"] == 3; row[4] += r["won"]
                row[5] = min(row[5], r["time"])
    _names.reserve(h.name for h in c.lineage(G["horses"] + e.nursery + sk.HALL))       # new foals can't take a name already in the book
    if not any(getattr(x, "title", None) for x in sk.CALENDAR):                  # a save from before the stakes book: this year's
        for x in sk.CALENDAR:                                                     # unrun stakes give nominations back, and the
            if not x.result:                                                      # named book takes over from tonight
                for h in x.noms:
                    e.book(h.owner, "stakes", x.purse * (0.03 if x.week - G["day"] % c.YEAR < sk.EARLY else 0.01))
        sk._ids = iter(range(max(int(x.id[1:]) for x in sk.CALENDAR) + 1, 10 ** 6))
        sk.new_calendar()
        for x in sk.CALENDAR:
            if x.week < G["day"] % c.YEAR:
                x.result = []                                                     # already past this season
    if ADMIN in G.get("players", {}) and not any(getattr(h, "ageless", False) for h in G["horses"]):
        giga_horse()                                                          # the owner's barn: one ageless S+ 3-year-old
    for h in G["horses"]:                                                     # claimed away by mistake: it comes home, the tag goes back
        if getattr(h, "ageless", False) and h.owner != ADMIN:
            tag = int(str(getattr(h, "gone", "")).split("$")[-1].replace(",", "") or 0) if "$" in str(getattr(h, "gone", "")) else 0
            if tag:
                e.book(ADMIN, "claims", -tag); e.book(h.owner, "claims", tag)
            e.barn_size[h.owner] = e.barn_size.get(h.owner, 1) - 1
            e.barn_size[ADMIN] = e.barn_size.get(ADMIN, 0) + 1
            if getattr(h, "trainer", None):
                h.trainer.horses -= 1
            h.owner, h.gone, h.order, h.ship, h.drawn = ADMIN, None, None, None, False
            c.assign(h, c.BARN_TRAINER.get(ADMIN, c.HOUSE)) or c.assign(h, c.HOUSE)
    have = {(x.week, x.group, x.sex, x.title) for x in sk.CALENDAR}           # stakes added to the book since this season began:
    for week, group, sex, title, purse, kind in sk.SCHEDULE:                  # the ones still ahead join it now
        if (week, group, sex, title) not in have and week > G["day"] % c.YEAR + sk.CLOSE:
            sk.CALENDAR.append(sk.Stake(week, group, sex, title, purse, kind))
    for st_ in sk.CALENDAR:                                                    # names follow the current naming, saved or not
        st_.name = sk.stake_name(st_)
    c.HUMAN.clear(); c.HUMAN.update(s["human"])
    c.HOUSE.__dict__.update(s["house"].__dict__)
    for h in c.lineage(G["horses"] + e.nursery):                              # horses saved with the house trainer point at
        if getattr(h, "trainer", None) is s["house"]:                         # the loaded copy: send them to the real one
            h.trainer = c.HOUSE
    for o, t in list(c.BARN_TRAINER.items()):                                 # (barns too)
        if t is s["house"] or getattr(t, "name", None) == "house":
            c.BARN_TRAINER[o] = c.HOUSE
    sim.rng.setstate(s["rng"])
    # id counters live in the modules, not the save: move them past everything that exists
    sim._ids = count(max(h.id for h in G["horses"] + e.nursery) + 1)
    for m, st_ in e.bookings:                                                 # bookings made before the nursery existed get their foal now
        if not any(f.dam is m for f in e.nursery):
            f = c.foal(st_, m); f.age = 0; e.grow(f, G["day"]); e.nursery.append(f)
    sk._ids = iter(range(max(int(x.id[1:]) for x in sk.CALENDAR) + 1, 10 ** 6))
    c._tnames = count(10 * len(c.NAMES))
    e.settle(G["horses"])                                      # rebuilds the stall counts; books nothing new
    c.public_stats(G["horses"])
    if not any(h.retired for h in G["horses"]):                # a save from before retirement existed
        c.ai_retire(G["horses"], G["ai"])
        e.settle(G["horses"])
    if not any(h.retired and h.sex == "m" for h in G["horses"]):   # a circuit started before stallions were seeded
        c.seed_studs(G["horses"], G["ai"])
        e.settle(G["horses"])


DEV = os.environ.get("HARNESS_DEV") == "1"   # developer view: every horse's bars visible. Off unless the server is started with HARNESS_DEV=1


def find_horse(name):
    """Any horse in the stud book by name: living, in the nursery, or long gone but still in someone's pedigree."""
    return next((x for x in G["horses"] + e.nursery if x.name == name), None) or         next((x for x in c.lineage(G["horses"] + e.nursery + sk.HALL) if x.name == name), None)


def kids_of(h):
    """Every foal a horse ever had, living or gone."""
    return [k for k in c.lineage(G["horses"] + e.nursery + sk.HALL) if k.sire is h or k.dam is h]


def mine():
    return [h for h in G["horses"] if h.owner == ME]


SNAPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")


def snapshot():
    """The world as it stood before tonight's races, for the admin's undo. The last three nights are kept."""
    save()
    os.makedirs(SNAPS, exist_ok=True)
    with open(SAVE, "rb") as f, open(os.path.join(SNAPS, f"night-{G['day']:06d}.pkl"), "wb") as g:
        g.write(f.read())
    for old in sorted(os.listdir(SNAPS))[:-3]:
        os.remove(os.path.join(SNAPS, old))


def undo_night():
    """Back to before the last race night run. The clock (when the scheduled night last ran) and everyone's
    sign-ins stay as they are now, so the undone night doesn't simply run again or log anyone out."""
    snaps = sorted(os.listdir(SNAPS)) if os.path.isdir(SNAPS) else []
    if not snaps:
        return False
    keep = {k: G[k] for k in ("last_night", "sessions") if k in G}
    path = os.path.join(SNAPS, snaps[-1])
    load(path)
    G.update(keep)
    os.remove(path)
    save()
    return True


def tick():
    """One game week for everyone: stakes, the cards, the books. Each player's barn gets its own notices."""
    snapshot()
    for o in list(G.get("players", {})):                      # Season Pass grace: a holder who didn't check in today is set up, three nights at most
        if has_pass(o):
            if P(o).get("seen_day") == G["day"]:
                P(o)["pass_missed"] = 0
            elif P(o).get("pass_missed", 0) < PASS_GRACE:
                P(o)["pass_missed"] = P(o).get("pass_missed", 0) + 1
                setup_tonight(o, auto=True)
    day, before = G["day"], {h.id: (h.earnings, h.owner) for h in G["horses"] if h.owner in c.HUMAN}
    for o in G.get("players", {}):                            # the books going into tonight: the Earnings graphs, week by week
        hist = P(o).setdefault("hist", [])
        hist.append({"d": day, "cash": round(e.cash.get(o, 0)), "led": {k: round(v) for k, v in e.ledger.get(o, {}).items()}})
        del hist[:-156]                                       # three seasons
    world_before = {h.id: (h.owner, h.retired) for h in G["horses"]}          # for the wire: who changed hands or retired tonight
    for o in c.HUMAN:
        P(o).setdefault("seen", day - 1)                      # nights before this one count as seen; tonight waits for Results
    c.DAY[0] = day                                            # stakes run before the cards: stamp their results with tonight's date
    names = {h.id: h.name for h in G["horses"] if h.id in before}
    if day % c.YEAR == 0 and not G.get("ai_trimmed"):            # once: the computer barns' decades of untaxed purses come down
        ai_ = [o for o in e.cash if o not in c.HUMAN]               # to a $2M median, each barn keeping its place in the order
        med = sorted(e.cash[o] for o in ai_)[len(ai_) // 2] if ai_ else 0
        if med > 2_000_000:
            for o in ai_:
                e.cash[o] = round(e.cash[o] * 2_000_000 / med)
        G["ai_trimmed"] = True
    if day % c.YEAR == 0 and day and e.ROLLED[0] != day:
        sk.year_tick(G["horses"], G["ai"], day)               # new book, and every horse's season tally starts again
    sk.ai_nominate(G["horses"], G["ai"], day)
    sk.run_today(day, G["horses"])
    settle_picks(day)
    G["horses"] = e.day(day, G["horses"], G["ai"], [])
    c.CLAIMS.clear()                                          # tonight's claims are settled (or the horse didn't run)
    for h in G["horses"]:                                     # a tonic that wasn't given (didn't race, or no cash for the vet) goes back on the shelf
        if getattr(h, "tonic", None) and not getattr(h, "tonic_used", False) and h.owner in G["players"]:
            shelf(h.owner)[h.tonic] += 1
        h.tonic = h.tonic_used = None
    for h in G["horses"]:
        if getattr(h, "drawn", False):                        # drawn into tonight's claimer: done with it
            h.order = h.ship = None; h.drawn = False
        if getattr(h, "order", None) == "stakes":
            h.order = None
    G["day"] += 1; e.TODAY[0] = G["day"]
    if G["day"] % c.YEAR == 0:                                # the season's last night is run: roll the year in now, so week 1
        name_handicapper(c.year_of(G["day"] - 1))             # the season's best handicapper takes the title
        sk.year_tick(G["horses"], G["ai"], G["day"])          # opens with everyone a year older and the 2-year-olds in the barn
        if SPONSORING:
            open_sponsor_auction()                            # and the season's stakes go up for sponsorship
        G["horses"] = e.new_year(G["horses"], G["ai"])
        e.ROLLED[0] = G["day"]                                # (the week-1 night itself won't roll it a second time)
    if G["day"] % c.YEAR == SPONSOR_WEEKS and G.get("sponsor_auction"):
        settle_sponsors()
    c.draw_claimers(G["horses"], G["ai"])                     # next week's claiming program goes up now
    draw_program()                                            # and tomorrow's card is drawn and posted: a whole day to read it
    events = {o: [] for o in c.HUMAN}
    alive = {h.id for h in G["horses"]}
    for hid, (_, o) in before.items():
        if hid not in alive:
            events[o].append(f"{names.get(hid, 'A horse')} reached {c.BREEDING_UNTIL} and is gone; the line lives on in the foals")
    for h in G["horses"]:
        if h.id not in before:
            continue
        o = before[h.id][1]
        if h.owner != o:
            events[o].append(f"{h.name} {getattr(h, 'gone', 'left the barn')}")
        elif h.earnings > before[h.id][0] and (h.last[2] == 1 or h.last[4] >= 10_000):
            events[o].append(f"{h.name} {'won' if h.last[2] == 1 else 'ran ' + str(h.last[2])} for ${h.last[4]:,.0f} in the {h.last[0]}")
    for o, ev in events.items():
        if G["day"] % c.YEAR == 0:
            ev.append("New year: the yearlings are on the board")
        ev.extend(G.get("pick_news", {}).pop(o, []))              # how the night's picks went
        P(o)["events"] = ev
    events = P()["events"]
    wire_tick(day, world_before)
    save()
    return events


# ---------------------------------------------------------------- pages
CSS = """
:root{color-scheme:dark;--paper:#11141a;--ink:#e6e8ec;--ink2:#a4acb9;--ink3:#6f7886;--rule:#2c3340;--rule2:#222833;--panel:#1a1f28;
--tote:#e8a33a;--tote-ink:#2a1a03;--win:#3fb96b;--loss:#e0704f;--mk:#7fd66a;
--p1:#d8322f;--p2:#1f4fbf;--p3:#f3f3f3;--p4:#1f8f3f;--p5:#1a1a1a;--p6:#f2d233;--p7:#e88fb0;--p8:#9a9a9a;--p9:#6b3fa0;--p10:#7fc4e8;--p11:#9acd32;--p12:#7a4a26}
body{font-family:'Barlow Semi Condensed',system-ui,sans-serif;margin:0;padding:env(safe-area-inset-top) env(safe-area-inset-right) 0 env(safe-area-inset-left);background:var(--paper);color:var(--ink);font-size:16px;line-height:1.35}
.w{max-width:420px;margin:0 auto;padding:12px 14px calc(104px + env(safe-area-inset-bottom,0px))}   /* clear of the tab bar and the phone's home indicator */
a{color:var(--ink);text-decoration:none} h1{font-size:26px;margin:8px 0 6px;letter-spacing:-.01em} h2{font-size:17px;margin:14px 0 6px}
.top{display:flex;justify-content:space-between;align-items:center;font-size:14px;color:var(--ink2);gap:10px;border-bottom:1px solid var(--rule);padding-bottom:8px}
.tabs{position:fixed;bottom:0;left:0;right:0;display:flex;justify-content:center;background:#0d1015;border-top:1px solid var(--rule);padding:4px 0 calc(4px + env(safe-area-inset-bottom))}
.tabs a{flex:0 1 105px;display:flex;flex-direction:column;align-items:center;gap:2px;padding:6px 0;font-size:12px;color:var(--ink3);font-weight:600}
.tabs a.on{color:var(--tote)} .tabs a.on svg{stroke-width:2.4} .tabs a:focus-visible{outline:2px solid var(--ink);outline-offset:-2px}
.mi{display:flex;flex-direction:column;padding:10px 0;border-bottom:1px solid var(--rule2)} .mi b{font-size:16px} .mi.off{opacity:.5}
.card{background:var(--panel);border:1px solid var(--rule);border-radius:4px;padding:10px 12px;margin:8px 0}
.row{display:flex;align-items:center;gap:10px}
.tier{font-size:34px;font-weight:700;width:40px;text-align:center;border-radius:4px;color:#fff;font-family:'Barlow Semi Condensed',sans-serif}
.S{background:#b45309}.A{background:#1f4fbf}.B{background:#1f7a3f}.C{background:#6b7280}.D{background:#a1a1aa}
.sub{font-size:13px;color:var(--ink2)} .pips{font-family:monospace;font-size:12px;white-space:nowrap}
.stat{height:9px;background:var(--rule2);border-radius:2px;position:relative;overflow:hidden;background-image:repeating-linear-gradient(90deg,transparent 0 calc(10% - 1px),var(--panel) calc(10% - 1px) 10%)} .stat i{display:block;height:9px;border-radius:2px}
.bar{height:6px;background:var(--rule2);border-radius:3px;margin:4px 0} .bar i{display:block;height:6px;background:var(--win);border-radius:3px}
.chart{font-size:13px;color:var(--ink2);margin-top:4px} .money{font-weight:600;font-variant-numeric:tabular-nums}
button,.btn{background:var(--tote);color:var(--tote-ink);border:0;border-radius:4px;padding:8px 12px;font-size:14px;font-family:inherit;font-weight:600}
button.armed{outline:2px solid var(--win);outline-offset:1px;background:var(--win);color:#06170c} button.sec.armed{color:var(--win);border-color:var(--win);background:none}
button.sec{background:transparent;color:var(--ink);border:1px solid var(--rule)} button.sec:hover{border-color:var(--ink3)} button.warn{background:var(--loss);color:#fff}
form.inline{display:inline} select,input{font-size:16px;padding:6px;border-radius:4px;border:1px solid var(--rule);font-family:inherit;background:var(--rule2);color:var(--ink)}
.ev{background:#2a2213;border-left:3px solid var(--tote);padding:8px 10px;font-size:14px;margin:8px 0}
table{width:100%;border-collapse:collapse;font-size:13px} td,th{text-align:left;padding:5px 2px;border-bottom:1px solid var(--rule2)} th{color:var(--ink2);font-weight:600}
.hdr{display:flex;gap:12px;padding:0;overflow:hidden} .port{position:relative;flex:0 0 124px;background:#1c2430;display:flex;align-items:center;justify-content:center}
.port svg{display:block} .badge{position:absolute;top:6px;right:6px;width:28px;height:28px;font-size:18px;line-height:28px;border-radius:4px}
.ribbon{position:absolute;left:0;right:0;bottom:0;background:#000b;color:var(--ink);text-align:center;font-weight:600;font-size:13px;padding:2px}
.hr{flex:1;padding:10px 12px 10px 0;display:flex;flex-direction:column;gap:5px;min-width:0} .hname{font-size:24px;font-weight:700;line-height:1.05}
.hline{font-size:14px;color:var(--ink2)} .chips{display:flex;font-size:13px;gap:6px;align-items:baseline} .chip{color:var(--ink3)} .chipv{color:var(--ink);font-weight:600}
.gchip{color:#fff;font-size:11px;padding:2px 6px;border-radius:3px;vertical-align:middle}
.act{margin-top:4px} .btn.big,button.big{display:block;width:100%;background:var(--tote);color:var(--tote-ink);text-align:center;padding:10px;border-radius:4px;font-weight:700;font-size:15px;box-sizing:border-box;border:0}
.btn.big.off{background:var(--rule2);color:var(--ink3)}
.secbar{font-size:13px;color:var(--ink3);margin:14px 0 2px;padding-bottom:2px;border-bottom:1px solid var(--rule)}
.tiles{display:grid;grid-template-columns:1fr 1fr 1.1fr;gap:10px} .tile{padding:6px 0}
.tl{font-size:13px;color:var(--ink2)} .tv{font-size:22px;font-weight:700;margin-top:2px;font-variant-numeric:tabular-nums;letter-spacing:-.01em}
.kv{display:flex;flex-direction:column} .kv div{display:flex;justify-content:space-between;border-bottom:1px solid var(--rule2);padding:3px 0;font-size:13px;font-variant-numeric:tabular-nums} .kv span{color:var(--ink2)}
details{margin:10px 0 0} summary{padding:9px 0;border-top:1px solid var(--rule);font-size:17px;font-weight:600;cursor:pointer;list-style:none;display:flex;justify-content:space-between}
summary::after{content:'+';color:var(--ink3);font-weight:400} details[open] summary::after{content:'–'} details .card{margin-top:2px}
.pedt{display:grid;grid-template-columns:1.2fr 1.1fr 1fr;grid-auto-rows:minmax(44px,auto)} .pc{border-bottom:1px solid var(--rule2);border-right:1px solid var(--rule2);padding:8px 10px;display:flex;flex-direction:column;justify-content:center;gap:2px;font-size:14px}
.pc:nth-child(3n){border-right:0} .pc small{color:var(--ink2);font-size:12px;font-variant-numeric:tabular-nums} .pc.me{font-size:16px;font-weight:700} .pc .unk{color:var(--ink3);font-style:italic;font-size:13px}
.pedt .pc.ps{background:#1f4fbf;border-color:#05070d}.pedt .pc.pd{background:#b8336a;border-color:#05070d}.pedt .pc.ps.g{background:#1f4fbf99}.pedt .pc.pd.g{background:#b8336a99}.pedt .pc.ps a,.pedt .pc.pd a{color:#fff}.pedt .pc.ps small,.pedt .pc.pd small{color:#ffffffbb}
.tcase .ticon{width:44px;height:44px;display:block;margin:0 auto 4px;filter:drop-shadow(0 2px 3px #0009)}
.mqe{display:inline-block;position:relative;border-radius:50%;padding:2px;background:conic-gradient(from var(--ang),var(--mqs));animation:holo 5s linear infinite;vertical-align:middle}.mqe .crest{display:block}.mqrow td{text-shadow:0 1px 0 #000,1px 0 0 #000,0 -1px 0 #000,-1px 0 0 #000,0 2px 4px #000}.mqrow td{border-top:1px solid #ffd36b55!important;border-bottom:1px solid #ffd36b55!important}.mqrow td:first-child{box-shadow:-4px 0 0 #ffd36b}.dsort th{cursor:pointer;user-select:none}.dsort td{vertical-align:middle;font-size:13px}.dsort td .sub{font-size:11px}.mqbar{margin:8px 0 0}h1+.mqbar{margin:0 0 10px}.mqsticky{position:sticky;top:env(safe-area-inset-top);z-index:5;margin:-4px -4px 12px}.mqsticky{background:#0b0e16;padding:4px 4px 0}.mqbar2{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:8px 0}.mqbar2 button{width:auto;padding:6px 14px;margin:0}.mqbar2 button:disabled{opacity:.4;cursor:default}.mqtabs{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;border-bottom:1px solid var(--rule2)}.mqtabs button{flex:none;width:auto;margin:0;padding:8px 14px;background:none;border:0;border-bottom:3px solid transparent;color:var(--ink2);font-weight:700;box-shadow:none}.mqtabs button.on{color:var(--tote);border-bottom-color:var(--tote)}.mqpane{display:none;padding-top:10px}.mqpane.on{display:block}.mqgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(92px,1fr));gap:6px}@media(max-width:520px){.mqgrid{grid-template-columns:repeat(3,1fr)}}.mqtile{position:relative;display:flex;flex-direction:column;gap:2px;padding:4px;border:1px solid var(--rule2);cursor:pointer;font-size:12px;text-align:center}.mqtile input{position:absolute;opacity:0;pointer-events:none}.mqtile:has(input:checked){outline:2px solid var(--tote);background:#e8a33a22}.mqtile.locked .mqth{filter:grayscale(1) brightness(.55)}.mqlock{font-size:10px;color:var(--ink2);line-height:1.2}.mqnew{position:absolute;top:4px;right:4px;font:800 9px sans-serif;background:#e23d3d;color:#fff;padding:1px 4px;border-radius:6px}.mqth{display:flex;align-items:center;justify-content:center;height:52px;overflow:hidden}.mqsc{width:100%;height:100%;background:center/cover}.mqx.mqmini{min-height:0;width:100%;height:100%;padding:0;background:#1a1f2e}.pxhd{font:800 18px 'Barlow Condensed',sans-serif;letter-spacing:.06em;text-transform:uppercase;color:var(--led)}.pbar{height:8px;background:var(--well);margin:6px 0 2px}.pbar i{display:block;height:100%;background:linear-gradient(90deg,#b45309,#ffd36b)}.thnum{position:absolute;top:2px;left:4px;font:800 12px 'Cinzel',serif;color:#ffe9a8;text-shadow:0 1px 2px #000}.mqth{position:relative}.bgrp{border:1px solid #3a4866;background:#ffffff05;border-radius:4px;padding:6px 10px 10px;margin:0 0 12px;min-width:0}.bgrp legend{padding:0 6px;font:800 13px 'Barlow Condensed',sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--led)}.mqtabs.slide{position:relative;scroll-snap-type:x proximity;scroll-behavior:smooth}.mqtabs.slide button{scroll-snap-align:center;padding:8px 11px;border-bottom-color:transparent!important}.mqink{position:absolute;left:0;bottom:0;height:3px;width:0;background:var(--tote);transition:transform .25s ease,width .25s ease}.mqpane.on.fromR{animation:pslideR .25s ease}.mqpane.on.fromL{animation:pslideL .25s ease}@keyframes pslideR{from{transform:translateX(24px);opacity:0}}@keyframes pslideL{from{transform:translateX(-24px);opacity:0}}@media (prefers-reduced-motion:reduce){.mqink,.mqpane.on{transition:none;animation:none!important}}.card.hc{background:linear-gradient(100deg,color-mix(in srgb,var(--tc) 34%,#1e2b46),#22304c 55%);border:2px solid #0a0f1c;border-left:5px solid var(--tc);box-shadow:inset 2px 2px 0 #4a5f8c,inset -2px -2px 0 #121a2b,0 3px 0 #05070d}.hc .bname{font-family:'Barlow Condensed',sans-serif;font-weight:800;letter-spacing:.02em;text-shadow:2px 2px 0 #000}.hc .sub{color:#c6cede}.hc .sv{color:#fff;text-shadow:1px 1px 0 #000}.hc .cond svg{filter:drop-shadow(1px 0 0 #04140a) drop-shadow(-1px 0 0 #04140a) drop-shadow(0 1px 0 #04140a) drop-shadow(0 -1px 0 #04140a) drop-shadow(0 0 4px #3fb96b88)}.hc .cond b{text-shadow:1px 1px 0 #000;font-size:15px}.hc .cond+.sub{display:block;width:100%;margin-top:4px;padding:4px 8px;background:#0b1120cc;border-left:3px solid var(--tote);color:#e6e8ec;font-weight:600}.hc .chart.starts{display:flex;flex-direction:column;gap:3px;margin-top:4px}.hc .chart.starts span{padding:4px 8px;background:#0b1120cc;border-left:3px solid #5ab7e6;color:#e6e8ec;font-weight:600}.hc .chart.starts b{color:#ffb347;text-transform:uppercase;font-size:11px;letter-spacing:.08em;margin-right:4px}body.themed .card.hc{background:linear-gradient(100deg,color-mix(in srgb,var(--tc) 34%,#1e2b46),#22304ce8 55%)}.vstrip{display:flex;overflow-x:auto;scrollbar-width:none;flex-wrap:nowrap;scroll-snap-type:x proximity}.vstrip{overflow-x:auto!important}.vstrip button{flex:none;scroll-snap-align:center}.vdot{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--win);vertical-align:2px}.vpane{border:2px solid var(--rule);background:var(--well);padding:4px 8px;margin-top:6px}.vmeta2{font-size:13px;color:var(--ink2);padding:4px 0 6px;border-bottom:1px solid var(--rule2);display:flex;gap:8px;flex-wrap:wrap}.vmeta2 .vname{display:none}.sbarn .btag{font-size:13px}.skwk{margin:8px 0}.skwh{display:flex;justify-content:space-between;align-items:baseline;font:800 14px 'Barlow Condensed',sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--led);border-bottom:1px solid var(--rule);padding:4px 2px}.skwh span{font-size:12px;color:var(--ink2);letter-spacing:.04em}.skrow{display:flex;justify-content:space-between;gap:10px;align-items:center;background:var(--panel);border:1px solid var(--rule);border-left:4px solid #5ab7e6;padding:6px 10px;margin-top:4px}.skrow.kfinal{border-left-color:var(--led)}.skrow.kclassic{border-left-color:#a78bfa}.skrow.kleg{border-left-color:#3fb96b}.skrow.ksignature{border-left-color:#e8a33a}.skrow.kinvitational{border-left-color:#f472b6}.skrow.kopener{border-left-color:#93c5fd}.skrow.mine{background:#e8a33a1a}.skl{display:flex;flex-direction:column;min-width:0}.skl b{font-size:15px}.skdiv{font-size:12px;color:var(--ink2)}.skyou{font-size:12px;color:var(--tote);font-weight:700}.skr{display:flex;flex-direction:column;align-items:flex-end;gap:2px;white-space:nowrap}.sk{font-size:12px;color:var(--ink2)}.sk.nom{color:var(--win);font-weight:700}.sk.inv{color:var(--led)}.sk.won a{color:var(--ink);font-weight:700}.skpast summary{font-size:14px}.gpart{border:2px solid var(--rule);border-radius:4px;background:var(--panel);margin:6px 0}.gpart>summary{padding:10px 12px!important;border:0;display:flex;justify-content:space-between;align-items:center}.gpart[open]>summary{border-bottom:2px solid var(--rule)}.gcount{font-size:12px;color:var(--ink2);background:var(--well);padding:1px 7px;border-radius:9px;letter-spacing:0}.gbody{padding:0 12px 4px}.gbody .gtopic summary{font-family:'Barlow Semi Condensed',sans-serif;text-transform:none;letter-spacing:0;color:var(--ink);font-size:15px;padding:8px 2px}.upl{display:flex;flex-direction:column;gap:10px}.upc{display:flex;gap:10px;align-items:center;padding:10px;background:var(--panel);border:2px solid var(--um);box-shadow:inset 2px 2px 0 #ffffff10,inset -2px -2px 0 #0006,0 3px 0 #05070d}.upc img{flex:none;image-rendering:pixelated;filter:drop-shadow(0 3px 2px #000a)}.upm{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px}.upm b{font:800 19px 'Barlow Condensed',sans-serif;letter-spacing:.04em;text-transform:uppercase;color:var(--um2);text-shadow:2px 2px 0 #000}.upk{display:flex;flex-wrap:wrap;gap:4px}.upk span{font-size:12px;padding:1px 6px;background:var(--well);border:1px solid var(--rule)}.upa{flex:none}.upa button{width:auto}.upst{font-weight:800;color:var(--um2);white-space:nowrap}.up0{--um:#5b4a38;--um2:#c8b89f}.up1{--um:#7a3b2a;--um2:#f2a28a}.up2{--um:#8a4a6a;--um2:#f6a8c8}.up3{--um:#8793a3;--um2:#e6ecf3}.up4{--um:#c9922e;--um2:#ffd36b}.up4.built,.up4.next{background:linear-gradient(100deg,#ffd36b22,var(--panel) 60%)}.upc.ahead{opacity:.55}.upc.ahead img{filter:grayscale(.8) brightness(.7)}.upc.next{outline:2px solid var(--tote);outline-offset:2px}.etiles{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:6px 0 4px}.etile{background:var(--panel);border:1px solid var(--rule);border-top:3px solid var(--led);padding:8px 10px;display:flex;flex-direction:column;gap:1px;min-width:0}.etl{font:800 12px 'Barlow Condensed',sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--ink2)}.etile b{font-size:21px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.etile .up{color:var(--win);font-size:12px;font-weight:700}.etile .dn{color:var(--loss);font-size:12px;font-weight:700}.echart{width:100%;height:120px;display:block;margin-top:6px;background:var(--well)}.chartax{display:flex;justify-content:space-between;font-size:11px;color:var(--ink3)}.ebook td.money,.etable td.money{text-align:right}.ebook th{text-align:left;color:var(--led);padding-top:8px}.ebook .esub td{font-weight:700;border-top:1px solid var(--rule)}.ebook .enet td{font-weight:800;font-size:16px;border-top:2px solid var(--led)}.hmenu{display:flex;gap:3px;margin:6px 0 12px;padding:3px;background:#05070d;border:2px solid #0a0f1c;box-shadow:inset 2px 2px 0 #00000080,inset -1px -1px 0 #ffffff12,0 2px 0 #ffffff08;overflow-x:auto;scrollbar-width:none}.hmenu a,.hmenu button{flex:1 0 auto;text-align:center;white-space:nowrap;padding:8px 6px;margin:0;width:auto;border:0;border-radius:2px;font:800 13px 'Barlow Condensed',sans-serif;letter-spacing:.02em;text-transform:uppercase;color:#a4acb9;background:linear-gradient(#1a2338,#121a2b);box-shadow:inset 1px 1px 0 #ffffff14,inset -1px -1px 0 #0008;transition:color .15s,background .15s}.hmenu a:hover,.hmenu button:hover{color:#e6e8ec}.hmenu a.on,.hmenu button.on{color:#2a1a03;background:linear-gradient(#ffd36b,#e8a33a 55%,#c27c1c);text-shadow:0 1px 0 #ffe9a8;box-shadow:inset 1px 1px 0 #fff3b0,inset -1px -2px 0 #8a5a12,0 2px 4px #000a}.bidf{display:flex;flex-direction:column;gap:3px;margin-top:4px;text-align:left}.bidf input[type=number]{width:100%;font-size:15px;padding:5px 6px}.bidok{font-size:11px;display:flex;gap:4px;align-items:center;color:var(--ink2)}.bidf button{width:100%}.sortrow{display:flex;align-items:center;gap:6px;margin:-4px 0 10px}.sortrow a{font-size:13px;font-weight:700;padding:3px 9px;border:1px solid var(--rule);color:var(--ink2)}.sortrow a.on{background:var(--tote);color:var(--tote-ink);border-color:var(--tote)}.pgh.tk{background:linear-gradient(100deg,var(--tp),color-mix(in srgb,var(--tp) 55%,#05070d));border-bottom:4px solid var(--ta)}.tkb{flex:none;align-self:center;image-rendering:pixelated;filter:drop-shadow(0 2px 2px #000a)}.tkn{font-size:20px;line-height:1.1;letter-spacing:.02em;text-shadow:2px 2px 0 #000}.vstrip button img{vertical-align:-4px;margin-right:4px}.vstrip button{border-bottom:3px solid var(--tp)!important}.vband{display:flex;gap:10px;align-items:center;margin:-4px -8px 4px;padding:8px 10px;background:linear-gradient(100deg,var(--tp),color-mix(in srgb,var(--tp) 55%,#05070d));border-bottom:3px solid var(--ta);color:#fff}.vband b{display:block;font-size:22px;line-height:1;text-shadow:2px 2px 0 #000}.vband span{font-size:12px;opacity:.85}/* the stud book: nearly every stallion there is S+, so the holo stays but holds still */.calm .tSp:before,.calm .tSp:after,.calm .tier.Sp,.calm .sqt.tSp,.calm .badge.tSp,.calm .troph{animation:none!important}.mi{position:relative;margin:6px 0;padding:10px 34px 10px 12px;border:2px solid #0a0f1c!important;border-left:4px solid var(--tote)!important;background:linear-gradient(#1a2338,#121a2b);box-shadow:inset 1px 1px 0 #ffffff14,inset -1px -1px 0 #0008,0 2px 0 #05070d;color:var(--ink);text-decoration:none}.mi:after{content:'›';position:absolute;right:12px;top:50%;transform:translateY(-50%);font:800 26px 'Barlow Condensed',sans-serif;color:var(--tote)}.mi:hover,.mi:active{background:linear-gradient(#22304c,#18223a);border-color:#e8a33a!important}.mi:active{transform:translateY(1px)}.mi .sub{font-size:13px}.mi.off:after{content:none}.r10{flex-wrap:wrap}.r10v{flex-basis:100%;font-size:13px;font-weight:700;color:var(--tote);text-decoration:none;padding:2px 0 0 46px}.billrow{display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:13px;color:var(--ink2);padding:6px 10px;margin:4px 0 8px;background:var(--well);border:1px solid var(--rule);border-left:3px solid var(--loss)}.billrow b{color:var(--ink)}.billrow a{margin-left:auto;color:var(--tote);font-weight:700}.billrow.wayup{border-left-color:var(--tote)}.ts .bname{display:flex;justify-content:space-between;align-items:baseline;gap:8px}.ts .bname .age{font-family:'Barlow Semi Condensed',sans-serif;font-size:13px;font-weight:400;color:var(--ink2)}.sheet{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:8px}.sheet button{width:100%;margin:0;padding:8px 2px;font-size:13px;letter-spacing:.04em}.sheet button[disabled]{opacity:.35;box-shadow:none;transform:none}.sheet .foc{grid-column:1/-1;display:flex;gap:6px;align-items:center;font-size:13px;color:var(--ink2);flex-wrap:wrap}.sheet .foc label{color:var(--ink);background:var(--well);border:2px solid var(--rule);padding:1px 8px;cursor:pointer}.sheet .foc label:has(input:checked){border-color:var(--tote);color:var(--tote)}.sheet .foc input{position:absolute;opacity:0;width:0;height:0}.sheet .pick{display:block;margin:0;cursor:pointer}.sheet .pick input{position:absolute;opacity:0;width:0;height:0}.sheet .pick span{display:grid;place-items:center;height:100%;box-sizing:border-box;padding:8px 2px;font-weight:700;font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:var(--ink);background:var(--panel);border:2px solid var(--edge);box-shadow:3px 3px 0 var(--edge)}.sheet .pick:has(input:checked) span{border-color:var(--tote);color:var(--tote);box-shadow:3px 3px 0 var(--edge),inset 0 0 0 1px var(--tote)}.sheet .pick:has(input:focus-visible) span{outline:2px solid var(--tote);outline-offset:2px}.sheet .pick:has(input[disabled]) span,.sheet .pick.lock span{opacity:.35;box-shadow:none;cursor:default}.didnote{font-size:13px;color:var(--ink2);margin-top:6px}.stageln{font-size:12.5px;color:var(--ink2);margin-top:6px}.stageln b{color:var(--ink)}.didnote b{color:var(--win)}.echart.tall{height:auto}.ct{font:600 10.5px 'Barlow Semi Condensed',sans-serif;fill:var(--ink2);font-variant-numeric:tabular-nums;text-transform:none;letter-spacing:0}.ct.now{fill:var(--led);font-weight:700;font-size:12px}.ct.ctw{fill:#3fb96b}.ct.ctl{fill:#e0704f}.chartax b.won{color:#3fb96b}.chartax b.lost{color:#e0704f}.tabs a{position:relative}.tabs a .tbadge{position:absolute;top:3px;right:8px;background:var(--tote);color:var(--tote-ink);font-size:10px;font-weight:800;line-height:1;padding:2px 4px;border-radius:8px;border:2px solid var(--edge);min-width:8px;text-align:center}.tabs a.on .tbadge{display:none}.tabs{gap:5px;padding:6px 8px calc(6px + env(safe-area-inset-bottom));background:#05070d!important;box-shadow:0 -2px 0 var(--rule),0 -4px 0 var(--edge)}.tabs a{flex:0 1 100px;border:2px solid #0a0f1c;border-radius:3px;color:#a4acb9;background:linear-gradient(#1a2338,#121a2b);box-shadow:inset 1px 1px 0 #ffffff14,inset -1px -1px 0 #0008,0 2px 0 #000;transition:background .15s,color .15s}.tabs a:active{transform:translateY(1px);box-shadow:inset 1px 1px 0 #0008}.tabs a.on{color:#2a1a03!important;background:linear-gradient(#ffd36b,#e8a33a 55%,#c27c1c);text-shadow:0 1px 0 #ffe9a8;box-shadow:inset 1px 1px 0 #fff3b0,inset -1px -2px 0 #8a5a12,0 2px 4px #000a}.stallct{font-family:'Barlow Semi Condensed',sans-serif;font-weight:700;font-size:1.05em;margin-left:4px;letter-spacing:0}.st-grn{color:#4ade80;text-shadow:0 0 6px #4ade8066}.st-yel{color:#facc15;text-shadow:0 0 6px #facc1566}.st-red{color:#f87171;text-shadow:0 0 6px #f8717166}.vseal{vertical-align:-3px;margin-left:4px;flex:none}.mqnl{display:flex;align-items:center;gap:4px;max-width:100%;min-width:0}.mqnl .mqn{min-width:0}.lgrid{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin-top:6px}.lpick{width:auto;margin:0;padding:4px 0;display:flex;flex-direction:column;align-items:center;gap:2px;background:var(--btn2);box-shadow:none;font-size:12px}.lpick.on{outline:2px solid var(--tote)}.pxchip{font:800 10px 'Cinzel',serif;padding:0 4px;border:1px solid var(--led);border-radius:3px;color:var(--led);vertical-align:1px}.mqdot{width:18px;height:18px;border-radius:50%}.mqaa{font-size:26px}.mqtile[hidden]{display:none}.mqpg .pg{cursor:pointer}.mqshim{font-size:28px;color:#fff;text-shadow:0 0 6px #fff,0 0 14px #ffd36b}.pager{display:flex;flex-wrap:wrap;justify-content:center;gap:2px;margin:14px 0}.pager .pg,.card .pager a.pg{flex:0 0 auto;display:inline-block;padding:4px 6px;width:auto;min-width:22px;margin:0}.pg{min-width:30px;padding:6px 8px;text-align:center;border:1px solid var(--rule2);text-decoration:none;color:inherit}.pg.on{background:var(--tote);color:#2a1a03;font-weight:800}span.pg:not(.on){opacity:.35}.crest{vertical-align:middle;flex:none}.btag{color:inherit;text-decoration:none;white-space:nowrap}.btitle{font-size:11px;color:var(--tote);letter-spacing:.04em}.pchip{font-size:10px;padding:1px 5px;border:1px solid var(--tote);border-radius:3px;color:var(--tote)}td.own{font-size:13px;max-width:140px;overflow:hidden;text-overflow:ellipsis}.cgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:8px;margin-bottom:8px}.cpick{display:flex;flex-direction:column;align-items:center;gap:4px;padding:8px;background:var(--card,#0002);border:1px solid var(--rule2);text-align:center;font-size:13px}.swr{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 10px}.sw{width:26px;height:26px;border:2px solid #05070d;display:inline-block}.sw input{opacity:0;width:100%;height:100%;margin:0}.sw:has(input:checked){outline:3px solid var(--tote)}.silk{display:inline-block;vertical-align:-2px;border:1px solid #05070d;border-radius:2px}.drow{display:flex;align-items:center;gap:10px;margin:6px 0}.drow b{width:18px}.drow select{flex:1}.drv{display:flex;align-items:center;gap:10px;padding:8px 2px;border-bottom:1px solid var(--rule2)}.drvm{flex:1;min-width:0}.drvr{display:flex;flex-direction:column;align-items:flex-end;font-size:13px}.dstand{width:100%}.dstand td,.dstand th{padding:3px 4px;text-align:left}
.clr summary{padding:0;border:0;font-size:inherit;font-weight:400;display:block}.clr summary::after{content:none}.clrow{display:flex;gap:10px;align-items:center}.cltag{flex:none;min-width:48px;text-align:center;font:800 15px 'Barlow Condensed',sans-serif;color:var(--led);text-shadow:0 0 6px var(--ledglow)}.clid{flex:1;min-width:0;display:flex;flex-direction:column;gap:1px}.clid .sub{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.clact{flex:none}.clact button{width:auto;margin:0;padding:6px 10px}.clr.mine{background:#e8a33a14;border-left:3px solid var(--tote)}.clr .pglines{margin-top:8px;background:#f4f1e8;color:#111;border-radius:4px;padding:4px 6px;font-family:'Barlow Semi Condensed',Arial Narrow,sans-serif}.tier.sm{font-size:12px;width:auto;padding:0 5px;display:inline-block;line-height:16px}
.spon{color:var(--mk)}.skr .mk{font-size:14px}
.mk{display:inline-flex;align-items:center;gap:5px;font-weight:700;color:var(--mk,#7fd66a);text-shadow:0 0 8px #7fd66a55;font-variant-numeric:tabular-nums}.mkic{image-rendering:pixelated;vertical-align:middle}.mkbar{margin-left:10px;text-decoration:none}
.packs{display:flex;gap:8px;margin-top:8px}.packs .pack{flex:1;text-align:center;margin:0;padding:8px 6px;display:flex;flex-direction:column;align-items:center;gap:2px}.packs .pack .mk{font-size:18px}
.mgr{padding:10px 12px 12px}.mgr .mhead{display:flex;justify-content:space-between;align-items:center;gap:8px}.mgr .mhead b{font:800 17px 'Barlow Condensed',sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--led);text-shadow:2px 2px 0 #000}
.mgr .pchip{font:800 11px 'Barlow Condensed',sans-serif;letter-spacing:.06em;text-transform:uppercase;padding:2px 8px;border:1px solid var(--rule);border-radius:3px;color:var(--ink2)}.mgr .pchip.lit{color:var(--tote-ink);background:var(--tote);border-color:var(--tote)}
.mgr .mgrid{margin-top:8px}.mgr .mrow{display:grid;grid-template-columns:30px minmax(0,1fr) auto;gap:6px;align-items:center;padding:6px 0;border-top:1px solid var(--rule2)}
.mgr .mpic{display:block;width:30px;height:30px;border:2px solid var(--rule);border-radius:3px;image-rendering:pixelated;background:#1c2430}
.mgr .mrow.mh{border-top:0;padding:0 0 2px;font:800 11px 'Barlow Condensed',sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--ink3)}
.mgr .mname{display:flex;flex-direction:column;min-width:0}.mgr .mname b{font-size:14px;line-height:1.1;overflow-wrap:anywhere}.mgr .mname small{font-size:11px;color:var(--ink3);white-space:nowrap}.mgr .mname small i{font-style:normal;color:var(--win);font-weight:700}
.mgr select{width:100%;font-size:13px;font-weight:600;padding:5px 4px;background:#0b1120;color:var(--ink);border:1px solid var(--rule);border-radius:3px;box-shadow:inset 1px 1px 0 #0008}.mgr select:focus{outline:none;border-color:var(--tote);box-shadow:0 0 0 1px var(--tote)}
.mgr .mrow.done select{opacity:.6}
.mgr .erow2{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:6px 0;border-top:1px solid var(--rule2)}.mgr .erow2 .sub{font-size:12px}
.mgr .mact{display:flex;gap:8px;margin-top:10px}.mgr .mact button,.mgr .mact .btn{width:auto;margin:0;flex:1;text-align:center;position:static}
.pk .pkrow{display:flex;gap:8px;align-items:center;padding:6px 0;border-top:1px solid var(--rule2);cursor:pointer}.pk .pkrow.on b{color:var(--tote)}.pk .pkrow .sub{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.pk input{accent-color:var(--tote);margin:0}
.fullorder{position:fixed;inset:0;z-index:50;display:none;align-items:center;justify-content:center;padding:16px;background:#05070dcc}.fobox{width:min(440px,100%);max-height:90vh;overflow:auto;background:var(--panel);border:2px solid var(--rule);border-top:3px solid var(--tote);padding:10px 12px}.foh{display:flex;justify-content:space-between;gap:8px;margin-bottom:8px}.foh span{color:var(--ink2);font-size:13px}.forow{display:flex;align-items:center;gap:8px;padding:5px 0;border-top:1px solid var(--rule2)}.forow.fome{background:#e8a33a22}.fopl{width:34px;flex:none}.fon{flex:1;min-width:0;display:flex;flex-direction:column}.fon small{color:var(--ink2);font-size:12px}.foo{width:44px;text-align:right;color:var(--ink2)}.fom{width:46px;text-align:right}.fohead{font-size:11px;color:var(--ink3);text-transform:uppercase;border-top:0}.mut{margin-top:10px;padding-top:8px;border-top:2px solid var(--rule)}.muh{display:flex;gap:6px;font-size:11px;color:var(--ink3);text-transform:uppercase;padding-bottom:4px}.muh span:first-child{flex:1;color:var(--tote);font-weight:700;letter-spacing:.1em}.murow{display:flex;align-items:center;gap:6px;padding:4px 0}.mun{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.muv{width:58px;text-align:right;font-variant-numeric:tabular-nums}.muex{display:flex;justify-content:space-between;padding:4px 0;border-top:1px solid var(--rule2);font-size:14px}
.fotap{text-align:center;color:var(--ink3);font-size:12px;margin-top:10px}.fullbtn{margin-left:6px}
.stat.otc{box-shadow:0 0 0 1px #fde68a,0 0 8px #f0abfcaa}.sv.otc{color:#fde68a;white-space:nowrap}
.hown{font-size:13px;color:var(--ink2);margin:4px 0 8px}.parents{display:grid;grid-template-columns:1fr 1fr;gap:6px}.pbox{display:flex;flex-direction:column;justify-content:center;min-height:52px;padding:6px 8px;border-radius:4px;border:2px solid #05070d;text-decoration:none;min-width:0;box-shadow:inset 0 -3px 0 #0003}.pbox small{font-size:10px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;opacity:.85}.pbox b{font-size:14px;line-height:1.15;color:#fff;overflow-wrap:anywhere}.pbox.sire{background:#1f4fbf;color:#cfe0ff}.pbox.dam{background:#b8336a;color:#ffd6e6}.pbox.none{opacity:.55}
.gtopic{border-bottom:1px solid var(--rule2);padding:2px 0}.gtopic summary{cursor:pointer;font-weight:700;padding:9px 2px;font-size:16px}.gtext{color:var(--ink2);line-height:1.5;padding:0 2px 12px;font-size:15px}.gtext b{color:var(--ink)}.tierrow{display:flex;align-items:center;gap:5px;margin:10px 0}.tierrow b{width:30px;height:30px;display:grid;place-items:center;color:#fff;font-weight:800;border:2px solid #05070d;border-radius:3px}.tierrow .tsp{width:36px;color:#111;background:linear-gradient(135deg,#f0abfc,#67e8f9,#fde68a)}.tierrow .tl{font-size:12px;color:var(--ink3);text-transform:uppercase}
.enterplus.tonic{color:#14170f;position:absolute}.enterplus.tonic.on{background:#14170f!important;color:#e8eef4;box-shadow:0 0 0 2px var(--tc2),0 0 10px var(--tc2)!important}.tbadge{position:absolute;right:-5px;bottom:-5px;width:14px;height:14px;border-radius:50%;font:800 10px/14px system-ui;font-style:normal;text-align:center;background:#14170f;color:#fff;border:1px solid #fff6}.enterplus.tonic.on .tbadge{background:var(--tc2);color:#111;border-color:#111}.tline{display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:700;color:var(--tc2);border:1px solid var(--tc2);border-radius:10px;padding:0 7px 0 4px}.tb{display:block}.tbp{filter:drop-shadow(0 0 4px #c084fc99)}.invrow{display:flex;justify-content:space-between;gap:6px}.inv{display:flex;flex-direction:column;align-items:center;gap:2px;min-width:0}.inv b{font-size:16px}.inv .sub{font-size:11px}.titem{display:flex;align-items:center;gap:12px}.tmid{flex:1;min-width:0}.tbig{flex:none}.tprem{border-image:linear-gradient(#f0abfc,#67e8f9,#fde68a) 1;background-image:linear-gradient(90deg,#c084fc2a,#38bdf812 40%,transparent 70%)}.tgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}.tpick button{width:100%;display:flex;flex-direction:column;align-items:center;gap:4px;padding:10px}.tpick button:disabled{opacity:.4}
.prograce{border:1px solid var(--rule);border-radius:6px;margin:6px 0;padding:6px 10px;background:var(--panel)}.prograce summary{cursor:pointer;padding:4px 0}.pform{font-size:12px;color:var(--ink2)}.pml{font-size:16px}.pyou,.pplay{font-size:11px;padding:1px 5px;border-radius:3px;background:var(--tote);color:#111}.pplay{background:#5ab7e6}.pmine{background:#e8a33a1a}.hpick{font-size:13px;margin:4px 0 6px;color:var(--ink2)}.pvs{font-size:13px;color:#5ab7e6;margin:2px 0}.plane{font-size:11px;padding:1px 6px;border-radius:3px;background:#5ab7e6;color:#111;margin-left:6px}.prograce .prow{display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-top:1px solid var(--rule2)}.prograce .pmid{flex:1;min-width:0}.prograce .pright{flex:0 0 auto;display:flex;flex-direction:column;align-items:flex-end;gap:6px}
.proghead{display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-top:2px solid var(--tote);border-bottom:1px solid var(--rule);font-size:14px;font-variant-numeric:tabular-nums}
.progcard{font-size:13px;font-weight:700;color:var(--ink2);padding:14px 0 4px;border-bottom:1px solid var(--rule2)}
.prow{display:grid;grid-template-columns:28px 28px 1fr auto;gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid var(--rule2)}
.prow:hover{background:#ffffff08} .watch{display:inline-block;margin:-4px 0 8px 66px;font-size:13px;color:var(--tote);font-weight:600} .pfin{font-size:22px;font-weight:700;text-align:center;color:var(--ink3);font-variant-numeric:tabular-nums}
.pwin .pfin{color:var(--ink)} .pmid{min-width:0} .ptrip{display:block;font-size:12px;color:var(--ink2)} .pright{text-align:right;display:flex;flex-direction:column}
.rlist{padding:0 12px} .ryear{font-size:13px;color:var(--ink3);padding:10px 0 4px}
.rrow{display:grid;grid-template-columns:30px 1fr auto;gap:10px;align-items:center;padding:8px 0;border-top:1px solid var(--rule2)}
.pad{width:28px;height:28px;border-radius:3px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:15px;border:1px solid #0002}
.rname{font-size:14px;font-weight:600} .rname b{font-weight:700} .rtrip{font-size:12px;color:var(--ink2)} .rright{text-align:right} .rtime{font-variant-numeric:tabular-nums;font-size:14px} .won{font-size:12px;color:var(--win);font-weight:600}
.brow{display:flex;gap:12px;align-items:flex-start} .bname{font-size:16px;font-weight:700} .bname .sub{font-weight:400}
.bbars{margin:6px 0 4px} .bbars .row{gap:8px;margin:2px 0} .bbars .sub{width:52px;font-size:12px}
.sq{position:relative;flex:0 0 auto;border:3px solid;border-radius:6px;background:#1c2430;overflow:hidden;display:flex;align-items:center;justify-content:center}
.sq img{display:block;width:100%;height:100%;object-fit:cover} .pimg{display:block;border:3px solid;border-radius:50%;background:#1c2430;object-fit:cover} .sqt{position:absolute;right:0;bottom:0;color:#fff;font-size:12px;font-weight:700;padding:1px 5px;border-radius:4px 0 0 0}
.cond{display:inline-flex;align-items:center;gap:5px;font-size:13px} .cond svg{display:block}
@media (max-width:420px){.tiles{grid-template-columns:1fr 1fr} .kv{grid-column:1/3}}
"""


# The HD-2D skin: the replay's look carried into every menu. Pixel type for headings, amber LED digits (the
# tote and odds boards) for money and times, hard-edged pixel panels on a night sky, the venue's own
# panorama behind the top bar. Layered over CSS, so each page keeps its layout; only the dress changes.
SKIN = """
:root{--paper:#070a14;--panel:#111a2b;--rule:#2b3a55;--rule2:#1b2539;--edge:#05070d;--led:#ffb347;--ledglow:rgba(255,179,71,.55);--sky:#0b1430;--well:#0b1120;--btn2:#18223a}
body{background:var(--paper);background-image:
  radial-gradient(1px 1px at 12% 8%,#fff8 50%,transparent 51%),radial-gradient(1px 1px at 37% 22%,#fff6 50%,transparent 51%),
  radial-gradient(1px 1px at 68% 12%,#fff7 50%,transparent 51%),radial-gradient(1px 1px at 83% 31%,#fff5 50%,transparent 51%),
  radial-gradient(1px 1px at 22% 47%,#fff4 50%,transparent 51%),radial-gradient(1px 1px at 91% 58%,#fff4 50%,transparent 51%),
  linear-gradient(var(--sky),var(--paper) 420px);background-attachment:fixed}
h1,.pixh{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:26px;line-height:1.1;letter-spacing:.04em;text-transform:uppercase;text-shadow:2px 2px 0 #000;margin:14px 0 10px}
h2{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:17px;text-transform:uppercase;letter-spacing:.05em;line-height:1.3}
.top{position:relative;margin:0 -14px;padding:10px 14px 12px;border-bottom:0;color:#d7dceb;
  background:var(--sky) url(/mock/pixel/panorama.png) 30% bottom/auto 100% repeat-x;image-rendering:pixelated;box-shadow:0 2px 0 var(--edge),0 4px 0 var(--rule)}
.top:before{content:'';position:absolute;inset:0;background:linear-gradient(rgba(7,10,20,.25),rgba(7,10,20,.82))}
.top>*{position:relative}
.top{display:grid;grid-template-columns:1fr auto 1fr}.top .tleft{display:flex;flex-direction:column;gap:4px}.top .tright{justify-self:end}.top .when{font-size:14px;line-height:1.2}.top .brand{display:block;line-height:0}.top .brand img{height:52px;width:auto;image-rendering:auto}
.top .money,.money,.tv,.pfin,.rtime,.ml,.led{font-family:'Barlow Semi Condensed',sans-serif;font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:0}
.top .money{font-size:24px;color:var(--led);text-shadow:0 0 6px var(--ledglow),2px 2px 0 #000;line-height:1}
.money{font-size:1.05em;color:var(--led);text-shadow:0 0 5px rgba(255,179,71,.35)}
.tv{font-size:24px;line-height:1;color:var(--ink);text-shadow:2px 2px 0 #000}
.pfin{font-size:24px}.rtime{font-size:15px}
.card,.prow,.ev,details .card{border-radius:0}
.card{background:var(--panel);background-image:linear-gradient(45deg,#ffffff05 25%,transparent 25%,transparent 75%,#ffffff05 75%),linear-gradient(45deg,#ffffff05 25%,transparent 25%,transparent 75%,#ffffff05 75%);
  background-size:4px 4px;background-position:0 0,2px 2px;border:2px solid var(--rule);box-shadow:0 0 0 2px var(--edge),inset 0 2px 0 #ffffff12;margin:12px 2px}
.hdr.card{padding:0}
button,.btn,.btn.big,button.big{border-radius:0;text-transform:uppercase;letter-spacing:.06em;font-weight:700;box-shadow:3px 3px 0 var(--edge),inset 0 2px 0 #fff5,inset 0 -2px 0 #0003;border:2px solid var(--edge);transition:transform .05s}
button:active,.btn:active{transform:translate(2px,2px);box-shadow:1px 1px 0 var(--edge)}
button.sec,a.btn.sec{background:var(--btn2);color:var(--ink);border:2px solid var(--rule);box-shadow:3px 3px 0 var(--edge)}
.btn.big.off{box-shadow:none;border-color:var(--rule)}
select,input{border-radius:0;border:2px solid var(--rule);background:var(--well)}
.ev{background:#0a0702;border:2px solid #3a2a10;border-left:4px solid var(--led);color:#ffd9a0;font-family:'Barlow Semi Condensed',sans-serif;font-weight:600;font-size:15px;line-height:1.3;
  background-image:radial-gradient(rgba(255,179,71,.07) 1px,transparent 1.5px);background-size:4px 4px;box-shadow:0 0 0 2px var(--edge)}
.stat,.bar{border-radius:0;background-color:var(--well);box-shadow:inset 0 0 0 1px #000}
.stat i,.bar i{border-radius:0;box-shadow:inset 0 -2px 0 #0004,inset 0 1px 0 #fff4}
.stat{height:10px;background-image:repeating-linear-gradient(90deg,transparent 0 calc(10% - 2px),#000 calc(10% - 2px) 10%)}
.stat:after{content:'';position:absolute;inset:0;pointer-events:none;z-index:1;background:repeating-linear-gradient(90deg,transparent 0 calc(10% - 2px),#000 calc(10% - 2px) 10%)}   /* the nibs sit over the fill: it fills the squares, not over them */
.stat i{position:relative;z-index:0}.stat u{z-index:2}
.pad{border-radius:0;font-family:'Barlow Semi Condensed',sans-serif;font-weight:700;font-variant-numeric:tabular-nums;font-size:16px;border:0;box-shadow:inset 0 -2px 0 #0005,inset 2px 0 0 #0003,inset -2px 0 0 #0003,inset 0 2px 0 #fff4,0 0 0 1px var(--edge)}
.tier{border-radius:0;font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:28px;line-height:44px;box-shadow:3px 3px 0 var(--edge),inset 0 2px 0 #fff4}
.sq,.pimg,.port{border-radius:0!important;image-rendering:pixelated;box-shadow:0 0 0 2px var(--edge)}
.badge{border-radius:0;font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:15px;box-shadow:2px 2px 0 var(--edge)}
.secbar,summary{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:16px;text-transform:uppercase;letter-spacing:.08em;color:var(--led);border-color:var(--rule);padding-top:12px}
summary::after{font-size:20px}
.proghead{border-top:4px solid var(--led);font-family:'Barlow Semi Condensed',sans-serif;font-weight:700;font-variant-numeric:tabular-nums;font-size:16px}
.progcard{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:15px;color:var(--led);letter-spacing:.06em;text-transform:uppercase}
.watch{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:14px;letter-spacing:.06em;text-transform:uppercase;color:var(--led)}
.watch:before{content:'\\25B6  '}
.tabs{background:var(--paper);border-top:0;box-shadow:0 -2px 0 var(--rule),0 -4px 0 var(--edge)}
.tabs a{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:13px;letter-spacing:.08em;text-transform:uppercase;gap:4px}
.tabs{z-index:20}
.tabs a.on{color:var(--led);text-shadow:0 0 6px var(--ledglow)}
.tabs a svg{shape-rendering:crispEdges}
table th{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:12px;text-transform:uppercase;color:var(--ink3);letter-spacing:.04em}
.mi{border-color:var(--rule)}.mi b{font-family:'Barlow Condensed',sans-serif;font-size:18px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;line-height:1.3}
.won{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:#58d36a}
.hname{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:28px;line-height:1.05;letter-spacing:.02em;text-shadow:2px 2px 0 #000}
.bname{font-family:'Barlow Condensed',sans-serif;font-size:19px;font-weight:700;line-height:1.2;letter-spacing:.02em}
.outl{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:8px;padding-top:8px;border-top:2px solid var(--rule2)}
.tband{display:inline-flex;gap:2px}.tband i{font-style:normal;font-weight:700;font-size:12px;width:20px;text-align:center;padding:2px 0;background:var(--well);color:var(--ink3);box-shadow:inset 0 0 0 1px #000}
.tband i.on{background:var(--rule);color:var(--ink)}.tband i.mid{background:var(--led);color:#1a1000}
.nick{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;padding:2px 6px;border:2px solid var(--rule)}
.nick.gold{color:#1a1000;background:linear-gradient(#ffe27a,#e8a33a);border-color:#7a5210;box-shadow:0 0 8px rgba(255,200,80,.6)}.nick.poor{color:#ff8a7a}
form.inl{display:inline;margin:0}form.inl button{padding:4px 8px;font-size:12px}
.bname .sub{font-family:'Barlow Semi Condensed',sans-serif;font-size:13px}
.facts{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:5px 0 2px}
.stat{position:relative}.stat u{position:absolute;top:-2px;bottom:-2px;width:2px;margin-left:-1px;background:#fff;opacity:.8;box-shadow:0 0 4px #fff}
.starts{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 12px}
/* barn rows: each horse in its own lit stall, framed in its tier color */
.hc{border-left:5px solid var(--tc);background-image:linear-gradient(90deg,color-mix(in srgb,var(--tc) 14%,transparent),transparent 45%)}
.hc .sq{border:0;border-radius:0;padding:0;box-shadow:0 0 0 2px #05070d,0 0 0 5px var(--tc),0 0 0 7px #05070d,0 6px 14px #000a,0 0 18px color-mix(in srgb,var(--tc) 45%,transparent);margin:5px 4px 0 5px;
  background:radial-gradient(circle at 50% 30%,#fff6dc 0,#e8c88a 38%,#9a6a32 72%,#4a2f14 100%)}
.hc .sq:after{content:'';position:absolute;inset:0;background:repeating-linear-gradient(90deg,#0000 0 10px,#3a24101a 10px 11px);pointer-events:none}
.hc .sq img{position:relative;z-index:1;filter:drop-shadow(0 2px 2px #0007)}
.hc .sqt{z-index:2;right:-1px;bottom:-1px;font-family:'Barlow Condensed',sans-serif;font-size:15px;line-height:1;padding:3px 6px 2px;border-radius:0;box-shadow:-2px -2px 0 #05070d,inset 0 2px 0 #fff5}
.hc .bname a{font-family:'Barlow Condensed',sans-serif;font-size:22px;letter-spacing:.04em;color:#fff;text-shadow:2px 2px 0 #000;text-decoration:none;border-bottom:2px solid var(--tc);padding-bottom:1px}
/* portrait corners, everywhere: tier bottom-right, trophy top-right */
.badge,.hdr .badge{top:auto;bottom:6px;right:6px}
.troph{position:absolute;top:0;right:0;width:20px;height:19px;padding:2px 3px;box-sizing:border-box;z-index:3;background:linear-gradient(#ffe27a,#e8a33a 55%,#b9771a);
  box-shadow:0 0 0 2px #05070d,0 0 0 3px #e8a33a,0 0 10px rgba(255,200,80,.7);animation:shine 2.6s ease-in-out infinite}
.troph b{position:absolute;right:-6px;bottom:-6px;font:700 11px/1 'Barlow Condensed',sans-serif;background:#e8a33a;color:#1a1000;padding:1px 3px;box-shadow:0 0 0 1px #05070d}
.hdr .troph{width:30px;height:30px;padding:4px;top:6px;right:6px}
@keyframes shine{50%{box-shadow:0 0 0 2px #05070d,0 0 0 3px #ffe27a,0 0 16px rgba(255,220,120,.95)}}
/* S+ : the holo frame */
@property --ang{syntax:'<angle>';inherits:false;initial-value:0deg}
@keyframes holo{to{--ang:360deg}}
@keyframes twinkle{0%,100%{opacity:.15;transform:scale(.6)}50%{opacity:1;transform:scale(1)}}
.hc.sp{--tc:#c084fc;background-image:linear-gradient(90deg,#c084fc2a,#38bdf812 40%,transparent 70%)}
.hc.sp{border-image:linear-gradient(#f0abfc,#67e8f9,#fde68a) 1}
/* the grandstand (or stall lamp) stays; the holo swirl washes over it like a filter */
.sq.tSp,.hdr .port.tSp{--tc:#c084fc;border-color:#c084fc!important;box-shadow:0 0 0 2px #05070d,0 0 18px #c084fc99,0 0 34px #38bdf844!important}
.hc .sq.tSp{position:relative;box-shadow:0 0 0 2px #05070d,0 0 0 5px #c084fc,0 0 0 7px #05070d,0 0 20px #c084fcaa!important}
.sq.tSp:before,.hdr .port.tSp:before{content:'';position:absolute;inset:0;z-index:2;pointer-events:none;
  background:conic-gradient(from var(--ang) at 50% 45%,#f0abfc,#818cf8,#38bdf8,#67e8f9,#fde68a,#f9a8d4,#f0abfc);
  mix-blend-mode:color;opacity:.38;animation:holo 6s linear infinite}
.sq.tSp:after{background:radial-gradient(1.5px 1.5px at 18% 22%,#fff 50%,transparent 51%),radial-gradient(1.5px 1.5px at 78% 30%,#fff 50%,transparent 51%),
  radial-gradient(1px 1px at 60% 70%,#fff 50%,transparent 51%),radial-gradient(1.5px 1.5px at 30% 80%,#fff 50%,transparent 51%),
  repeating-linear-gradient(90deg,#0000 0 10px,#3a24101a 10px 11px)!important;z-index:3;animation:twinkle 2.4s ease-in-out infinite}
.sqt.tSp,.badge.tSp,.tier.Sp{background:conic-gradient(from var(--ang),#f0abfc,#818cf8,#38bdf8,#67e8f9,#fde68a,#f0abfc)!important;color:#1a0b2e!important;
  animation:holo 4s linear infinite;text-shadow:0 1px 0 #fff8;letter-spacing:-.02em}
.hdr .badge.tSp{width:38px}
.book tr.past{opacity:.55}.book tr.kfinal td:first-child{color:var(--led)}.book tr.kfinal b,.book tr.kclassic b{color:var(--led)}
.crown table{margin-top:6px}.crown tr.me td{color:var(--led);font-weight:700}
.sv{display:none}
.mkt .row{align-items:flex-start}.mkt .sbars{grid-template-columns:1fr;max-width:none}.mkt .sbars .stat{min-width:0}   /* sale board: one column, so the grade and price keep their place */
/* compact bars (sale board, stud book): too small for ten ticks, so a plain solid bar with its value as a number */
.sbars .sv{display:block;min-width:14px;text-align:right;font-size:13px;font-variant-numeric:tabular-nums;color:var(--ink)}
.sbars .stat{height:8px;background-image:none}.sbars .stat:after{display:none}
.sbars{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:2px 12px;margin:6px 0 2px;width:100%;max-width:420px}.sbars .row{gap:6px;width:100%}.sbars .stat{flex:1;min-width:0}.sbars .sub{width:52px!important;font-size:12px}
.sbrow td{border-top:0;padding-top:0}
.kin{margin-top:6px;font-size:13px;color:#ffb38a}.kin b{color:#ff8a7a}.kin.ok{color:#7fd69a}.kin.bad{color:#ff8a7a;font-weight:700}
.hc{position:relative}
.enterplus{position:absolute;top:8px;right:8px;z-index:4;width:30px;height:30px;display:grid;place-items:center;text-decoration:none;
  font:700 22px/1 'Barlow Condensed',sans-serif;color:#1a1000;background:linear-gradient(#ffd27a,#e8a33a);border:2px solid #05070d;box-shadow:2px 2px 0 #05070d,inset 0 2px 0 #fff6}
.enterplus:active{transform:translate(2px,2px);box-shadow:none}
.enterplus.pause{color:#e8eefc;background:linear-gradient(#5b6b8c,#3a4762)}
.hc .bname{padding-right:36px}
.entercell{white-space:nowrap}.mates{display:inline-block;vertical-align:middle;margin-left:6px}.mates svg{width:24px!important;height:24px!important;min-width:24px;display:block;box-shadow:2px 2px 0 #05070d}
.pcol{flex:0 0 auto;display:flex;flex-direction:column;align-items:center}
.besttime{margin-top:10px;text-align:center;line-height:1.1}.besttime span{display:block;font-size:11px;color:var(--ink2);text-transform:uppercase;letter-spacing:.06em}
.besttime.rate{margin-top:8px}.besttime.rate b{color:var(--ink);text-shadow:none}
.mrate{display:flex;align-items:baseline;gap:8px}.mrate span{font-size:11px;color:var(--ink2);text-transform:uppercase;letter-spacing:.06em}.mrate b{font-size:20px;font-variant-numeric:tabular-nums}
.besttime b{font-size:17px;color:var(--led);font-variant-numeric:tabular-nums;text-shadow:0 0 5px rgba(255,179,71,.35)}
.filt{display:flex;flex-wrap:wrap;gap:6px;align-items:center}.filt input,.filt select{font:inherit;font-size:16px;padding:4px 6px;color:var(--ink)}
.filt input[name=q]{flex:1 1 140px}.filt .ages input{width:52px}.filt label{display:flex;gap:8px;align-items:center}
.arch td{vertical-align:top}.arch tr.me td,table tr.me td{color:var(--led)}
.stablehead{display:flex;justify-content:space-between;align-items:center;gap:8px}
.themes{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:8px 0}.themes a{display:flex;align-items:center;gap:8px;padding:8px;border:2px solid var(--rule);font-weight:700}
.themes a.on{border-color:var(--led)}.themes i{width:26px;height:26px;background:var(--sw);box-shadow:inset -8px -8px 0 var(--sl),0 0 0 1px #000}
.vfold{border:2px solid var(--rule);margin:4px 0;background:var(--well)}.vfold>summary{padding:4px 10px!important;min-height:0;font-size:15px;align-items:center}.vfold summary{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;padding:9px 10px;cursor:pointer;
  font-family:'Barlow Condensed',sans-serif;text-transform:none;letter-spacing:0;color:var(--ink);font-size:17px;border:0}
.vfold[open] summary{border-bottom:2px solid var(--rule)}.vname{font-weight:700}.vmeta{font-size:13px;color:var(--ink2);font-family:'Barlow Semi Condensed',sans-serif}
.vin{margin-left:auto;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--win)}
.erow{display:flex;align-items:center;gap:10px;padding:7px 10px;border-bottom:1px solid var(--rule2)}.erow:last-child{border-bottom:0}
.ename{flex:1;min-width:0}.erow .money{min-width:64px;text-align:right}.erow .entercell{min-width:76px;display:flex;justify-content:flex-end;align-items:center;gap:4px}
.entered{color:var(--win);font-size:13px;text-transform:uppercase;letter-spacing:.06em}
.phase b{font-family:'Barlow Condensed',sans-serif;font-size:20px;text-transform:uppercase;letter-spacing:.04em;margin-right:6px}
.r10{display:flex;align-items:baseline;gap:8px;padding:5px 0;border-bottom:1px solid var(--rule2);font-size:14px}.r10:last-of-type{border-bottom:0}
.rp{min-width:34px;font-weight:700;color:var(--ink2)}.rp.rp3{color:var(--ink)}.rp.rp1{color:var(--win)}
.r10n{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.r10t{font-variant-numeric:tabular-nums;color:var(--ink2)}.r10w{min-width:62px;text-align:right;font-variant-numeric:tabular-nums;color:var(--win)}
.tgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px}
.tcase{border:2px solid var(--rule);background:var(--well);padding:8px;display:flex;flex-direction:column;align-items:center;text-align:center;gap:3px}
.tcase i{font-style:normal;font-size:24px;color:var(--led);width:28px;height:28px;display:flex;align-items:center;justify-content:center}.tcase.tcup{border-color:#b8900a}
.tcase i svg{width:22px;height:22px}.tcase.tcup i{background:#e8b84a;border:2px solid #05070d;padding:2px}
.tcase b{font-size:13px;line-height:1.2}.tcase span{font-size:11px;color:var(--ink2)}
.retband{background:#b3261e;color:#fff;font-weight:700;font-size:12px;letter-spacing:.12em;text-transform:uppercase;padding:3px 8px;align-self:flex-start;border:2px solid #05070d}
.ribbon.retired{background:#b3261e;color:#fff;letter-spacing:.12em;font-weight:700}
.mkt.ret{border-color:#b3261e}.retchip{display:inline-block;background:#b3261e;color:#fff;font-size:10px;font-weight:700;letter-spacing:.1em;padding:1px 6px;margin-left:4px;vertical-align:middle}
.fchips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.fchips a{padding:4px 9px;border:2px solid var(--rule);font-size:13px;font-weight:700;color:var(--ink2);background:var(--well)}
.fchips a.on{background:var(--led);color:var(--tote-ink);border-color:var(--led)}
.race .rhead{display:flex;justify-content:space-between;align-items:baseline}.fhs{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.fh button{padding:4px 8px;font-size:12px}span.fh{font-size:12px;color:var(--win)}span.fh.here{border:2px solid var(--win);padding:3px 8px;font-weight:700}.elsewhere{display:block;font-size:11px;color:var(--ink3);margin-top:2px}.fairnow{color:var(--led)}


 
.news{background:var(--panel);border:1px solid var(--rule);border-radius:4px;padding:8px 10px;margin:6px 0;font-size:15px}
.nmeta{display:flex;align-items:center;gap:8px;margin-bottom:3px} .ntag{color:#fff;font-size:10px;font-weight:700;letter-spacing:.08em;padding:1px 6px;border-radius:3px}
.nwatch{margin-left:auto;font-size:12px;font-weight:700;color:var(--tote)}
.sortby{display:flex;align-items:center;gap:0;font-size:13px}.sortby span{color:var(--ink2);margin-right:8px;text-transform:uppercase;letter-spacing:.06em;font-size:11px}
.sortby a{padding:4px 10px;border:2px solid var(--rule);color:var(--ink2);text-decoration:none;font-weight:700;background:var(--well)}
.sortby a+a{border-left:0}.sortby a.on{color:#1a1000;background:linear-gradient(#ffd27a,#e8a33a);border-color:#05070d}
.groombtn button{padding:2px 8px;font-size:12px;line-height:1.4}
.prog{padding:0;overflow:hidden}.proghd{display:flex;justify-content:space-between;flex-wrap:wrap;gap:4px 10px;padding:8px 12px;
  background:linear-gradient(90deg,#e8a33a,#c47a17);color:#140c00;font-size:14px}.proghd b{letter-spacing:.06em;text-transform:uppercase}
.pg{display:grid;grid-template-columns:34px 1fr auto;gap:10px;align-items:start;padding:9px 12px;border-top:1px solid var(--rule2)}
.pg:nth-child(odd){background:#ffffff05}.pg.mine{background:#e8a33a14;box-shadow:inset 3px 0 0 var(--led)}
.pgnum{width:30px;height:30px;display:grid;place-items:center;font:800 17px/1 'Barlow Condensed',sans-serif;box-shadow:0 0 0 2px #05070d,inset 0 -3px 0 #0004}
.pgname{font-size:17px;font-weight:700}.pgname a{color:#fff;text-decoration:none}.ml{color:var(--led);font-weight:800;margin-left:6px;font-variant-numeric:tabular-nums}
.pgline{font-size:13px;color:var(--ink2);line-height:1.35}.lp{display:inline-block;min-width:16px;text-align:center;background:var(--well);border:1px solid var(--rule);color:var(--ink);font-weight:700;font-size:12px;margin-right:2px}
.lp.lpwin{background:var(--led);color:#140c00;border-color:#05070d}.pgact{text-align:right}.pgact button{padding:4px 9px;font-size:13px}.claimed{color:var(--led);font-weight:700;font-size:12px;margin-top:4px}
.gkey{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12px;color:var(--ink2);margin-top:4px}.gkey i{display:inline-block;width:12px;height:4px;margin-right:5px;vertical-align:middle}
.gkey i.dash{background:repeating-linear-gradient(90deg,#c9d1e3 0 4px,transparent 4px 7px);height:2px}
.rrow{display:grid;grid-template-columns:30px 1fr auto;gap:12px;align-items:center}.rrow .pmid a{color:inherit;text-decoration:none}
.rrow .pright{display:flex;flex-direction:row;align-items:center;justify-content:flex-end;gap:12px}
.rrow .rbtns{order:2}.rrow .rres{order:1;min-width:70px}
.spoil{display:none}.rrow.shown .spoil,.spoil.on{display:inline}.rrow.shown .ptrip.spoil{display:block}
.rbtns{display:flex;gap:6px}.rbtn{padding:4px 10px;font-size:13px}.rres{text-align:right}.rrow.shown .rres{display:flex;flex-direction:column;align-items:flex-end;line-height:1.15}
.rfin{font:800 22px/1 'Barlow Condensed',sans-serif;color:var(--ink)}.rfin.rwin{color:var(--led)}.revall{padding:3px 9px;font-size:12px;margin-left:8px}
.crownline{margin-bottom:10px;padding:8px 10px;border:2px solid var(--rule);background:var(--well);font-size:13px;color:var(--ink2);line-height:1.45}
.crownline b{color:var(--ink)}.crownline.in{border-color:#e8a33a;background:linear-gradient(90deg,#e8a33a22,transparent);color:#f3e6c8}.crownline.in b{color:var(--led)}
.rnav{display:flex;gap:8px;align-items:center;justify-content:space-between;margin:6px 0 10px}.rnav select{font:inherit;font-size:16px;padding:4px 6px;color:var(--ink);flex:1;min-width:0}
.rnav .off{opacity:.35;pointer-events:none}.rnav form{flex:1;min-width:0;display:flex}.rnav .btn{white-space:nowrap;flex:0 0 auto;padding-left:10px;padding-right:10px}
.chip{font-size:14px;font-weight:600;color:var(--ink);background:var(--well);border:2px solid var(--rule);padding:1px 7px;line-height:1.35}
.chip b{font-size:15px;font-weight:700;font-variant-numeric:tabular-nums;color:#fff}
.chip.cash{color:var(--led);font-weight:700;font-variant-numeric:tabular-nums;text-shadow:0 0 5px rgba(255,179,71,.35)}
/* the profile portrait as a showcase: the horse at the track at night, spotlit, in a frame of its tier color */
.hdr .port{flex:0 0 156px;width:156px;height:168px;margin:10px 0 10px 10px;align-self:center;overflow:hidden;
  background:var(--sky) url(/mock/pixel/backdrop_raw.png) 22% 46%/auto 260% no-repeat;image-rendering:pixelated;
  border:3px solid var(--tc,#6b7280);box-shadow:0 0 0 2px var(--edge),inset 0 0 0 2px #ffffff22,inset 0 -40px 30px -10px #000a}
.hdr .port.tS{--tc:#e8a33a}.hdr .port.tA{--tc:#3d6fe0}.hdr .port.tB{--tc:#2f9e57}.hdr .port.tC{--tc:#8a93a3}.hdr .port.tD{--tc:#c7ccd4}
.stagelight{position:absolute;inset:0;background:radial-gradient(ellipse 60% 55% at 50% 48%,rgba(255,226,170,.38),rgba(255,210,140,.1) 55%,transparent 72%),
  radial-gradient(ellipse 42% 7% at 50% 92%,rgba(0,0,0,.55),transparent 70%)}
.hdr .pimg{position:relative;border:0!important;background:transparent;box-shadow:none!important;border-radius:0;width:150px;height:150px;margin-top:8px;filter:drop-shadow(0 3px 0 #0008)}
.hdr .badge{width:30px;height:30px;line-height:30px;font-size:17px;top:auto;bottom:6px;right:6px;z-index:1}
.hdr .ribbon{z-index:1}
.hdr .hr{padding:12px 12px 12px 4px}
.hdr{flex-direction:column}.htop{display:flex;gap:12px}
.hbars{padding:4px 12px 12px;border-top:2px solid var(--rule2);margin-top:2px}.hbars .row{margin:3px 0}
/* Prime: four bevelled arrow tiles on a dark inset strip; the horse's own lit orange */
.prime{display:flex;align-items:center;gap:10px;margin-top:10px}
.pstrip{display:inline-flex;gap:3px;padding:3px;background:#05070d;border:1px solid #000;box-shadow:inset 0 2px 3px #000,0 1px 0 #ffffff14}
.pa{position:relative;display:block;width:30px;height:24px;background:linear-gradient(#3a414d,#22272f 55%,#1a1e25);
  box-shadow:inset 0 1px 0 #ffffff2a,inset 0 -1px 0 #0009,inset 1px 0 0 #ffffff12}
.pa:after{content:'';position:absolute;left:8px;top:4px;width:15px;height:16px;clip-path:polygon(0 0,100% 50%,0 100%);
  background:linear-gradient(135deg,#f3f5f8,#aab1bc 45%,#6b7380);filter:drop-shadow(1px 1px 0 #000)}
.pa.on{background:linear-gradient(#4a3416,#2a1c08)}
.pa.on:after{background:linear-gradient(135deg,#ffe2a8,#ff9a1f 45%,#d35400)}
.pa.on:before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at 45% 50%,rgba(255,150,40,.45),transparent 70%)}
.pnote{font-size:14px;color:var(--ink);font-weight:600}
.rfin{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:17px;letter-spacing:.03em;color:var(--ink2);margin-top:1px}
.rfin.rwin{color:var(--led);text-shadow:0 0 6px var(--ledglow)}
"""
FONTS = ("<link rel=preconnect href=https://fonts.googleapis.com><link href='https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@400;600;700"
         "&family=Barlow+Condensed:wght@600;700;800&display=swap' rel=stylesheet>")


# the in-app browser drops confirm() dialogs, so a confirm is a second tap on the same button
ASK_JS = """<script>/* two-tap confirm: the button keeps its size (no reflow) and reads Confirm until it times out */
function ask(b,m){if(b.dataset.armed)return true;b.dataset.armed=1;b.dataset.t=b.textContent;b.style.width=b.offsetWidth+'px';b.style.whiteSpace='nowrap';b.style.overflow='hidden';
b.textContent='Confirm';b.title=m;b.setAttribute('aria-label',m+' Tap again to confirm.');b.classList.add('armed');
setTimeout(()=>{delete b.dataset.armed;b.textContent=b.dataset.t;b.style.width='';b.classList.remove('armed');b.removeAttribute('aria-label')},4000);return false}
/* a button posts and the page comes back: keep the reader where they were (same page only; a new page opens at its top) */
document.addEventListener('submit',e=>{if(e.defaultPrevented)return;try{sessionStorage.setItem('keepY',JSON.stringify({p:location.pathname+location.search,y:scrollY}))}catch(x){}},true);
addEventListener('DOMContentLoaded',()=>{try{const k=JSON.parse(sessionStorage.getItem('keepY')||'null');sessionStorage.removeItem('keepY');
if(k&&k.p===location.pathname+location.search&&!location.hash){history.scrollRestoration='manual';scrollTo(0,k.y)}}catch(x){}});</script>"""


def urlname(name):
    return quote(name, safe='')                                         # a horse's name in a URL: spaces and all


def esc(x):
    return html.escape(str(x))


TABS = (("barn", "/", "Barn", "<path d='M3 11 12 4l9 7v9H3z'/><path d='M9 20v-6h6v6'/>"),
        ("train", "/training", "Training", "<circle cx='12' cy='13' r='8'/><path d='M12 9v4l3 2M9 2h6'/>"),
        ("market", "/market", "Market", "<path d='M4 7h16l-1.5 11h-13z'/><path d='M9 7a3 3 0 0 1 6 0'/>"),
        ("breed", "/studs", "Breeding", "<path d='M12 20s-7-4.3-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.7-7 10-7 10z'/>"),
        ("more", "/more", "Manage", "<circle cx='5' cy='12' r='1.5'/><circle cx='12' cy='12' r='1.5'/><circle cx='19' cy='12' r='1.5'/>"))
TAB_OF = {"Training": "train", "Compendium": "more", "Shop": "market", "Claimers": "market", "Sponsor a stake": "market", "Stable Manager": "barn", "Tonic": "barn", "Stakes & Crown": "more", "Breeding": "breed", "Breed": "breed", "Entries": "more", "Sale board": "market", "Stud book": "breed", "Results": "more", "Trainers": "more", "Stakes": "more",
          "Barn upgrades": "market", "Tack Room": "market", "Barn identity": "more", "More": "more", "Manage": "more", "Earnings": "more", "Leaderboards": "more", "Archive": "more"}


# color themes: each one re-points the skin's palette (the base skin is "night", the original deep blue;
# "clubhouse" is the default)
THEMES = {
    "night":     None,
    "clubhouse": "--paper:#0a0f0c;--panel:#14201a;--rule:#2f4a3a;--rule2:#1c2a22;--sky:#10201a;--well:#0c1510;--btn2:#1a2a21;--led:#e8b84a;--ledglow:rgba(232,184,74,.5)",
    "charcoal":  "--paper:#0c0c0e;--panel:#18181c;--rule:#36363e;--rule2:#232328;--sky:#16161a;--well:#101013;--btn2:#232329",
    "oxblood":   "--paper:#110a0b;--panel:#1e1315;--rule:#4a2b30;--rule2:#2c1a1d;--sky:#1e0f13;--well:#150c0e;--btn2:#2a181c;--led:#f0c27a;--ledglow:rgba(240,194,122,.5)",
}


def theme_css():
    v = THEMES.get(P().get("skin", "clubhouse"))
    return f":root{{{v}}}" if v else ""


# home-screen install: name, icon and colors a phone uses when the game is added to it
HEAD = ("<link rel=manifest href=/manifest.webmanifest><link rel=icon href=/mock/brand/app_32.png><link rel=apple-touch-icon href=/mock/brand/app_180.png>"
        "<meta name=theme-color content='#070a14'><meta name=apple-mobile-web-app-capable content=yes><meta name=mobile-web-app-capable content=yes>"
        "<meta name=apple-mobile-web-app-status-bar-style content=black-translucent><meta name=apple-mobile-web-app-title content='Trot Dynasty'>"
        "<script>if('serviceWorker' in navigator)addEventListener('load',()=>navigator.serviceWorker.register('/sw.js').catch(()=>{}));addEventListener('beforeinstallprompt',e=>{e.preventDefault();window.tdInstall=e;document.documentElement.classList.add('caninstall')})</script>")
OFFLINE_PAGE = ("<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Offline · Trot Dynasty</title>"
                "<meta name=theme-color content='#070a14'><style>body{margin:0;min-height:100vh;display:flex;flex-direction:column;align-items:center;"
                "justify-content:center;gap:14px;background:#070a14;color:#e6e8ec;font:16px system-ui,sans-serif;text-align:center;padding:24px}"
                "img{width:220px;max-width:70%}b{color:#ffb347;font-size:20px;letter-spacing:.06em;text-transform:uppercase}p{color:#a4acb9;margin:0;max-width:300px}"
                "button{margin-top:6px;padding:10px 20px;border:0;border-radius:3px;background:#e8a33a;color:#2a1a03;font-weight:800;font-size:15px}</style></head>"
                "<body><img src=/mock/brand/logo_text.png alt='Trot Dynasty'><b>You're offline</b><p>The track's still running. Reconnect and you'll pick up "
                "right where you left off.</p><button onclick='location.reload()'>Try again</button>"
                "<script>addEventListener('online',()=>location.reload())</script></body></html>")
MANIFEST = json.dumps({"id": "/", "name": "Trot Dynasty", "short_name": "Trot Dynasty",
                       "description": "A harness racing management sim: build a barn, breed champions, race for the Crown. Race night every night at 8 PM ET.",
                       "start_url": "/welcome", "scope": "/", "display": "standalone", "orientation": "any",   # any: replays turn sideways
                       "background_color": "#070a14", "theme_color": "#070a14", "categories": ["games", "sports"],
                       "icons": [{"src": f"/mock/brand/app_{n}.png", "sizes": f"{n}x{n}", "type": "image/png", "purpose": "any"} for n in (192, 512)]
                       + [{"src": f"/mock/brand/app_maskable_{n}.png", "sizes": f"{n}x{n}", "type": "image/png", "purpose": "maskable"} for n in (192, 512)]})


# ---------------------------------------------------------------- race night: daily at 8 PM New York time
def _ny_offset(u):
    """New York's offset from a naive UTC time: EDT from the second Sunday of March 2 AM to the first Sunday of November 2 AM."""
    mar = datetime(u.year, 3, 8 + (6 - datetime(u.year, 3, 8).weekday()) % 7, 7)      # 2 AM EST is 07:00 UTC
    nov = datetime(u.year, 11, 1 + (6 - datetime(u.year, 11, 1).weekday()) % 7, 6)    # 2 AM EDT is 06:00 UTC
    return timedelta(hours=-4 if mar <= u < nov else -5)


assert _ny_offset(datetime(2026, 7, 1)) == timedelta(hours=-4) and _ny_offset(datetime(2026, 1, 1)) == timedelta(hours=-5)
assert _ny_offset(datetime(2026, 3, 8, 7)) == timedelta(hours=-4) and _ny_offset(datetime(2026, 3, 8, 6)) == timedelta(hours=-5)
assert _ny_offset(datetime(2026, 11, 1, 5)) == timedelta(hours=-4) and _ny_offset(datetime(2026, 11, 1, 6)) == timedelta(hours=-5)


def ny_now():
    """New York time; or, while the admin has the clock frozen for a look (G["frozen"] = "HH:MM"), today at that time."""
    u = datetime.now(timezone.utc).replace(tzinfo=None)
    n = u + _ny_offset(u)
    if G.get("frozen"):
        hh, mm = map(int, G["frozen"].split(":"))
        n = n.replace(hour=hh, minute=mm, second=0, microsecond=0)
    return n


def last_slot():
    """The most recent 8 PM in New York (naive, New York time)."""
    n = ny_now()
    s = n.replace(hour=20, minute=0, second=0, microsecond=0)
    return s if n >= s else s - timedelta(days=1)


def entries_closed():
    """Entries never close now: an entry made today is drawn into tomorrow's card at 8 PM, when tonight's has run."""
    return False


def draw_program():
    """The draw, right after a card runs: tomorrow's fields, posts and morning lines, up all day. Its stakes horses stay out."""
    day = G["day"]
    skip = {h.id for s in sk.CALENDAR if s.week == day % c.YEAR and not s.result for h in s.noms}
    c.draw_card(day, G["horses"], skip)
    save()


def on_card(h):
    """The race on the posted program this horse is in, or None."""
    if c.CARD.get("day") != G["day"]:
        return None
    return next((r for r in c.CARD.get("races", []) if h in r["field"]), None)


def night_checks(day0):
    """Tonight's world has to add up before it's posted: why it doesn't, or '' when it does."""
    if G["day"] != day0 + 1:
        return f"the clock went from {day0} to {G['day']}"
    if (bad := [o for o, v in e.cash.items() if v < -1e-6]):
        return f"barn {bad[0]} has negative cash"
    owners = set(G["ai"]) | set(G["players"])
    if (lost := [h for h in G["horses"] if h.owner not in owners]):
        return f"{lost[0].name} is owned by nobody ({lost[0].owner})"
    if (dup := [n for n in collections.Counter(h.id for h in G["horses"]).items() if n[1] > 1]):
        return f"horse id {dup[0][0]} appears twice"
    for h in G["horses"]:
        for r in getattr(h, "results", []):
            if r["day"] == day0 and r.get("race_id") not in c.STORIES:
                return f"{h.name}'s result tonight has no story to replay ({r.get('race_id')})"
    return ""


HELD = [False]   # tonight's card was rolled back; it isn't tried again until the server restarts (a deploy with the fix)


def checked_tick():
    """Race night with a safety catch: run it, check the world adds up, and only then leave it posted. If the night
    crashes or fails a check, the world goes back to before it, the night is held, and the admin gets a notice."""
    day0, slot0 = G["day"], G.get("last_night")
    try:
        tick()
        why = night_checks(day0)
    except Exception:
        traceback.print_exc()
        why = traceback.format_exc().strip().splitlines()[-1]
    if not why:
        G.pop("held", None)
        return True
    print(f"race night {day0} held: {why}", flush=True)
    snaps = sorted(os.listdir(SNAPS)) if os.path.isdir(SNAPS) else []
    if snaps and snaps[-1] == f"night-{day0:06d}.pkl":                         # tonight's snapshot: put the world back
        undo_night()
    G["last_night"] = slot0                                                   # so the night runs again once the server restarts
    G["held"] = {"day": day0, "why": why}
    P(ADMIN).setdefault("events", []).append(f"Race night held and rolled back: {why}. Fix, deploy, and it runs again.")
    HELD[0] = True
    save()
    return False


def race_nights():
    """The circuit's clock, on its own thread: once its 8 PM has passed, tonight's card runs. A server that was down
    runs one night when it comes back; the other missed nights are skipped."""
    while True:
        try:
            with LOCK:
                slot = last_slot().isoformat()
                if G.setdefault("last_night", slot) < slot and not HELD[0]:
                    G["last_night"] = slot
                    checked_tick()
        except Exception:
            traceback.print_exc()
        time.sleep(30)


def countdown():
    """Top bar: time to post time, when tonight's card runs and tomorrow's is drawn. The page's script keeps it ticking."""
    n = ny_now()
    at = n.replace(hour=20, minute=0, second=0, microsecond=0)
    if n >= at:
        at += timedelta(days=1)
    label = "Race night"
    left = int((at - n).total_seconds())
    ms = int((datetime.now(timezone.utc).timestamp() + left) * 1000)
    return (f"<small class=cd data-t={ms} data-l='{label}'>{label} in {left // 3600}h {left % 3600 // 60}m</small>"
            "<script>(()=>{const e=document.currentScript.previousElementSibling,f=()=>{const s=Math.max(0,(e.dataset.t-Date.now())/1e3|0);"
            "if(!s)return location.reload();e.textContent=`${e.dataset.l} in ${s/3600|0}h ${(s%3600/60|0)}m`};setInterval(f,30000)})()</script>")


def page(title, body, foot=True, theme=None):
    """theme: the barn whose Prestige look dresses the page (your own barn tab, a barn's public page), unless you've
    switched the theme off in Barn identity."""
    day = G["day"]
    th = ME if theme is None and title == "Your barn" else theme
    tmq = marquee_of(th) if th is not None and not P(ME).get("theme_off") else None
    bodytag = "<body>"
    if tmq:
        tm = "gold" if tmq["tier"] >= 7 else "silver" if tmq["tier"] >= 4 else "iron"
        bodytag = (f"<body class='themed tm-{tm}' style='--tbg:url(/mock/brand/marquee/v2/{tmq['scene'] or 'plate'}.png)'>"
                   + (MQ_SPARKS.replace("class=sparks", "class='sparks tsparks'") if tmq["tier"] >= 7 else ""))
    mq, plaque = marquee_of(ME), ""
    if mq:
        won = won_last_night(ME)
        boom = won is not None and P().get("mq_boom") != won
        if boom:
            P()["mq_boom"] = won                                              # once per winning night (kept at the next save)
        plaque = f"<div class=mqbar>{marquee_html(ME, mq, href=f'/barn/{ME}', boom=boom, big=title == 'Your barn')}</div>"
    top = (f"<div class=top><div class=tleft><span class=money>${e.cash[ME]:,.0f}</span>" + (f"<a href=/shop#markers class=mkbar>{mk_tag(markers())}</a>" if markers() else "") +
           f"<span class=when>Year {c.year_of(day)}, wk {day % c.YEAR + 1}{' <b style=color:#ff6f7d>DEV</b>' if DEV else ''}<br>{countdown()}</span></div>"
           f"<a href=/welcome class=brand><img src=/mock/brand/logo_text.png alt='Trot Dynasty'></a><div class=tright>"
           + ("<form method=post action=/advance class=inline><button name=days value=1>Post time</button></form>" if ME == ADMIN else "") + "</div></div>" + ("" if title == "Your barn" else plaque))
    under = plaque if title == "Your barn" else ""              # on the barn screen the Marquee sits under the heading
    if G.get("held"):
        under += "<div class=ev>Tonight's card is delayed. The results will post once the track sorts it out.</div>"
    cur = TAB_OF.get(title, "barn")
    todo = len(unworked()) if foot and cur != "train" and ME in G.get("players", {}) else 0   # youngsters still to work today
    tabs = ("<nav class=tabs>" + "".join(
        f"<a href={href}{' class=on aria-current=page' if key == cur else ''}><svg viewBox='0 0 24 24' width=22 height=22 fill=none "
        f"stroke=currentColor stroke-width=1.8 stroke-linejoin=round aria-hidden=true>{icon}</svg>{label}"
        f"{f'<span class=tbadge>{todo}</span>' if key == 'train' and todo else ''}</a>"
        for key, href, label, icon in TABS) + "</nav>") if foot else ""
    return (f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            f"<title>{esc(title)} · Trot Dynasty</title>{HEAD}{FONTS}{MQ_CSS}<style>{CSS}{SKIN}{theme_css()}</style>{ASK_JS}</head>{bodytag}<div class=w>{top}<h1>{esc(title)}</h1>{under}{body}</div>{tabs}</body></html>")


def youngsters(o=None):
    """The day sheet's horses: your yearlings in the nursery and your 2- and 3-year-olds, youngest first."""
    o = ME if o is None else o
    ys = [f for f in e.nursery if f.owner == o and f.age == 1] + [h for h in G["horses"] if h.owner == o and not h.retired and h.age <= c.YOUNG]
    return sorted(ys, key=lambda h: (h.age, h.name))


def worked(h):
    return (getattr(h, "job", None) or (None,))[0] == G["day"]


def unworked(o=None):
    return [h for h in youngsters(o) if not worked(h) and not (h not in e.nursery and getattr(h, "order", None))]


def set_of(x):
    """A youngster's saved set: (job, focus), from the manager's sheet or the last job it was given; None if neither.
    A yearling whose set isn't open yet at its stage works its stage instead: break work, then jogging."""
    st = getattr(x, "tset", None) or (getattr(x, "job", None) or (None, None, None))[1:]
    if not (st and st[0] in JOB_WORD and st[1] in FOCUS_NAME):
        return None
    return tuple(st) if st[0] in e.open_jobs(x) else (STAGE_JOB[e.stage(x)], st[1])


STAGE_JOB = {"break": "school", "jog": "jog", "train": "train"}


def stage_line(x):
    """A yearling's progress through breaking and jogging, for its card; empty once it's ready to train."""
    s = e.stage(x)
    if s == "break":
        return f"<div class=stageln><b>Breaking</b> · week {x.broke} of {e.BREAK_WEEKS} done. Jogging comes next.</div>"
    if s == "jog":
        return f"<div class=stageln><b>Jogging</b> · week {x.jogged} of {e.JOG_WEEKS} done. Training comes next.</div>"
    return "<div class=stageln><b>Ready to train</b> · broke and jogged.</div>" if x in e.nursery else ""


def apply_job(x, o, job, focus):
    """One job on one youngster's day sheet for barn o; 'repeat' deploys its saved set. False if nothing was set."""
    rep = job == "repeat"
    if rep:
        st = set_of(x)
        if not st:
            return False
        job, focus = st
    if focus not in FOCUS_NAME or job not in e.open_jobs(x) or x.owner != o:
        return False
    if not rep:
        x.tset = (job, focus)                                   # whatever you last chose is the set the manager deploys
    if x in e.nursery:
        return e.handle(x, o, G["day"], job, focus)
    if not x.retired and x.age <= c.YOUNG and not getattr(x, "order", None) and not (job == "train" and x.freshness < 35):
        x.job = (G["day"], job, focus)
        return True
    return False


def has_pass(o):
    return bool(P(o).get("pass"))


def setup_plan(o):
    """What the Stable Manager would do for barn o right now, without doing it: [(horse, race title, track)] it would
    enter, and the youngsters whose sets it would deploy."""
    entries = []
    for h in G["horses"]:
        if h.owner == o and not h.retired and not getattr(h, "order", None) and h.freshness >= 50 and not on_card(h):
            c.trainer_of(h).plan(h)
            group, sex, name, purse, tag = c.entry(h)
            if not tag:
                entries.append((h, c.race_title(group, name), getattr(h, "ship", None) or ("mile", "half")[h.id % 2]))
    sets = [x for x in unworked(o) if set_of(x)]
    return entries, sets


def setup_page():
    """The Stable Manager's preview: exactly what one tap would enter and deploy, then Confirm or Cancel."""
    entries, sets = setup_plan(ME)
    rows = "".join(f"<div class=row style='justify-content:space-between;gap:8px;padding:5px 0;border-top:1px solid var(--rule2)'><b>{esc(h.name)}</b><span class=sub>{esc(title)} · {'mile' if track == 'mile' else 'half-mile'}</span></div>" for h, title, track in entries)
    srows = "".join(f"<div class=row style='justify-content:space-between;gap:8px;padding:5px 0;border-top:1px solid var(--rule2)'><b>{esc(x.name)}</b><span class=sub>{JOB_WORD[set_of(x)[0]]}{' · ' + FOCUS_NAME[set_of(x)[1]] if set_of(x)[0] == 'train' else ''}</span></div>" for x in sets)
    body = ("<p class=sub>Nothing is entered until you confirm. Everything below stays editable afterward from the horse cards and the Training tab.</p>"
            f"<div class=card><b>Enter for tomorrow night · {len(entries)}</b><div class=sub>The trainer's picks, never a claimer.</div>{rows or '<div class=sub>Every fit horse is already entered.</div>'}</div>"
            f"<div class=card><b>Sets to work · {len(sets)}</b><div class=sub>Each youngster's saved job and focus, today.</div>{srows or '<div class=sub>No sets to work today.</div>'}</div>"
            "<a class='btn sec' href=/entries style='display:block;text-align:center;margin-bottom:8px'>Check or change tomorrow's entries</a>"
            "<div class=row style='gap:8px'><form method=post action=/setup style='flex:1'><button class=big style='width:100%;background:var(--win);color:#06170c;box-shadow:3px 3px 0 var(--edge)'" + ("" if entries or sets else " disabled") + ">Confirm</button></form>"
            "<a class='btn sec big' href=/ style='flex:1;text-align:center'>Cancel</a></div>")
    return page("Stable Manager", body)


def setup_tonight(o, auto=False):
    """The Stable Manager (what the Season Pass buys): the trainer's entries for every fit, unentered horse (never a
    claimer), every youngster's saved set deployed, and a note of what it did. auto: run by the night tick for a
    holder who didn't check in."""
    n_e = trainers_entries(G["horses"], o)
    n_s = sum(apply_job(x, o, "repeat", "") for x in unworked(o))
    P(o)["pass_log"] = (G["day"], n_e, n_s, auto)
    return n_e, n_s


def train_banner():
    n = len(unworked())
    if not n or entries_closed():
        return ""
    return (f"<a href=/training style='display:block;margin:8px 0;padding:10px 12px;border-radius:6px;background:#e8a33a;color:#111;"
            f"font-weight:700;text-decoration:none'>{n} youngster{'s' if n != 1 else ''} not worked today ›</a>")


JOB_NOTE = {"jog": "<b>Jogged today.</b> Ticking over.", "train": "<b>Trained today</b>, focus on {focus}.",
            "school": "<b>Break work today</b>: harness and gait.", "out": "<b>Turned out.</b> A day off; freshness comes back."}
FOCUS_NAME = {"early_speed": "Speed", "stamina": "Stam", "late_speed": "Finish", "gait": "Manners"}   # same words and order as the stat bars
JOB_WORD = {"jog": "Jog", "train": "Train", "school": "Break", "out": "Turn out"}
JS_WORDS = ["{" + ",".join(f"{k}:'{v}'" for k, v in d.items()) + "}" for d in (JOB_WORD, FOCUS_NAME)]   # the Work button's label, as the picks change


def day_sheet(h, back="/training"):
    """The four jobs for one youngster, or what it did today. A racer entered tonight races instead."""
    foal = h in e.nursery
    if not foal and getattr(h, "order", None):
        return "<div class=didnote>Racing tonight. It jogs itself in the morning.</div>"
    job = getattr(h, "job", None)
    if worked(h):
        return f"<div class=didnote>{JOB_NOTE[job[1]].format(focus=FOCUS_NAME.get(job[2], '').lower())}</div>" + stage_line(h)
    tired = not foal and h.freshness < 35
    can = e.open_jobs(h)
    past = e.stage(h) == "train"                                         # broke and jogged: Break and Jog stay on the sheet, locked
    st = set_of(h)
    ok = [k for k in ("jog", "train", "school", "out") if k in can and not (k == "train" and tired)]
    pick = st[0] if st and st[0] in ok else ok[0]                         # the saved set comes up picked; otherwise the stage's job
    last = st[1] if st else job[2] if job and job[2] in FOCUS_NAME else "gait"   # the focus stays what it was last set to
    # Tap a job to pick it (and a focus for training miles), then the Work button does it.
    opt = lambda key, label: (f"<label class=pick><input type=radio name=j value={key}{' checked' if key == pick else ''}"
                              f"{' disabled' if key not in ok else ''}><span>{label}</span></label>" if key in can
                              else f"<label class='pick lock' title='Done: past this stage'><span>&#128274; {label}</span></label>" if past
                              else "")                                  # a yearling still in a stage sees only that stage's job
    foc = "".join(f"<label><input type=radio name=f value={k}{' checked' if k == last else ''}>{t}</label>" for k, t in FOCUS_NAME.items())
    word = lambda j, f: JOB_WORD[j] + (" · " + FOCUS_NAME[f] if j == "train" else "")
    return (stage_line(h) + f"<form method=post action=/job class=sheet style='grid-template-columns:repeat({4 if past else len(can)},1fr)' "
            f"onchange=\"var j=this.j.value,f=this.f.value;this.querySelector('.go b').textContent={JS_WORDS[0]}[j]+(j=='train'?' · '+{JS_WORDS[1]}[f]:'')\">"
            f"<input type=hidden name=h value='{esc(h.name)}'><input type=hidden name=back value='{back}'>"
            f"<button class=go style='grid-column:1/-1'>Work: <b>{word(pick, last)}</b></button>"
            f"{opt('jog', 'Jog')}{opt('train', 'Train')}{opt('school', 'Break')}{opt('out', 'Turn out')}"
            + (f"<div class=foc><span>Training focus</span>{foc}</div>" if "train" in can else "<input type=hidden name=f value=stamina>")
            + ("<div class=foc><span class=sub>Too tired for training miles this week.</span></div>" if tired else "") + "</form>")


def training_page():
    ys = youngsters()
    done = sum(worked(h) for h in ys)
    rows = ""
    for h in ys:
        foal = h in e.nursery
        what = ("yearling " if foal else f"{h.age}yo ") + sex_word(h)
        bars = "".join(stat_bar(h.developed[t], h, k.capitalize(), trait=t, goal=h.ceiling(t, 2) - 2.0 if foal else None) for k, t in FOCUS.items())
        rows += (f"<div class='card brow hc ts' style='--tc:{TIER_RGB[tier_base(h)]}'><div class=pcol>{square_portrait(h)}</div><div style='flex:1;min-width:0'>"
                 f"<div class=bname><a href='/horse/{urlname(h.name)}'>{esc(h.name)}</a><span class=age>{what}</span></div>"
                 f"<div class=bbars>{bars}</div>"
                 + ("" if foal else f"<div class=row style='gap:4px 10px;margin-top:4px;flex-wrap:wrap'>{condition(h)}</div>")
                 + day_sheet(h) + "</div></div>")
    again = [h for h in unworked() if set_of(h)]
    # Standing orders: one card either way. With the pass it works every saved set in a tap and covers nights away;
    # without it, the same list with the manual button, so a free barn sees what the pass does where the chore is.
    word = lambda st: JOB_WORD[st[0]] + (" · " + FOCUS_NAME[st[1]] if st[0] == "train" else "")
    srows = "".join(f"<div class='mrow{' done' if worked(h) else ''}'><img class=mpic src='/portrait/{urlname(h.name)}.png' width=30 height=30 loading=lazy alt='' style='border-color:{TIER_RGB[tier_base(h)]}'>"
                    f"<span class=mname><b>{esc(h.name)}</b><small>{'yearling' if h in e.nursery else f'{h.age}yo'}{' · <i>&#10003; done today</i>' if worked(h) else ''}</small></span>"
                    f"<span class=sub>{word(set_of(h)) if set_of(h) else 'no set yet'}</span></div>" for h in ys)
    if has_pass(ME):
        line = "Each horse's last set, saved from its day sheet below. Your manager works them all in a tap, and runs them for you on nights you're away."
        act = f"<form method=post action=/sets class=inline style='flex:1'><button name=do value=deploy{'' if again else ' disabled'}>Work the sets ({len(again)})</button></form>"
    else:
        line = (f"Each horse's last set, saved from its day sheet below. Repeat them by hand here, or let a manager run them "
                f"every night, away or not, with the Season Pass.")
        act = (f"<form method=post action=/job class=inline style='flex:1'><input type=hidden name=h value='*'><input type=hidden name=j value=repeat>"
               f"<button class=sec{'' if again else ' disabled'}>Repeat yesterday for all ({len(again)})</button></form><a class='btn sec' href=/guide>Season Pass</a>")
    repeat_all = (f"<div class='card hc mgr' style='--tc:#c9922e'><div class=mhead><b>Standing orders</b>"
                  f"<span class='pchip{' lit' if again else ''}'>{len(again)} to work</span></div><div class=sub>{line}</div>"
                  f"<div class=mgrid><div class='mrow mh'><span></span><span>Horse</span><span>Set</span></div>{srows}</div><div class=mact>{act}</div></div>") if ys else ""
    body = (train_banner() + f"<div class=stablehead><h2>Day sheet <span class='stallct st-grn'>{done}/{len(ys)}</span></h2></div>" + repeat_all +
            "<div class=sub style='margin:-4px 0 8px'>Yearlings, 2 and 3-year-olds: one job a day, your call. The stable jogs any you don't get to.</div>"
            + (rows or "<div class=card><div class=sub>No youngsters in the barn. Yearlings come from your broodmares; 2 and 3-year-olds race here.</div></div>")
            + f"<div class=card><div class=sub>A yearling comes up in stages: {e.BREAK_WEEKS} weeks of <b>Break</b> to get it used to the harness, then "
              f"{e.JOG_WEEKS} weeks of <b>Jog</b>. Then <b>Train</b> opens. Pick a focus and it improves that stat. "
              "Training tires a horse, so give it a <b>Turn out</b> day to rest. "
              "Matured horses are trained automatically.</div></div>")
    return page("Training", body)


PASS_GRACE = 3       # the Season Pass covers this many nights in a row without a check-in, then waits
MK_CHECKIN, MK_SEVENTH, MK_TITLE = 1, 5, 25   # Markers: a day's check-in, the seventh in a row, a season title (Handicapper of the Year, a Crown champion)
MK_ICON = lambda size=16: f"<img class=mkic src=/mock/brand/markers/marker_{size}.png width={size} height={round(size * .72)} alt='Markers'>"


SPONSORING = False      # held back until the game is further along (around season 5); True brings the whole feature back
SPONSOR_WEEKS = 2       # the season-start auction: bidding closes at the tick of week 3
SPONSOR_BUMP = 0.10     # a sponsored stake's purse rises by this share at the opening bid, up to half the purse for a big one


def sponsor_open(s):
    """The opening bid on a stake, in Markers: scaled to its purse."""
    return max(10, int(round(s.purse / 50_000)) * 10)


def sponsor_step(price):
    return max(5, int(-(-price * 0.1 // 5) * 5))


def open_sponsor_auction():
    """At the year roll: every stake but the Crown finals goes up for sponsorship. Last season's sponsors are gone with it."""
    G["sponsors"] = {}
    G["sponsor_auction"] = {s.id: {"price": sponsor_open(s), "leader": None, "bids": 0} for s in sk.CALENDAR if s.kind != "final"}


def sponsor_bid(o, sid):
    """A bid at the next step, in Markers: the previous leader gets theirs back. Returns the new price, or None."""
    a = G.get("sponsor_auction", {}).get(sid)
    if not a or a["leader"] == o or P(o).get("frozen"):
        return None
    price = a["price"] if a["leader"] is None else a["price"] + sponsor_step(a["price"])
    if markers(o) < price:
        return None
    s = next((x for x in sk.CALENDAR if x.id == sid), None)
    if a["leader"] is not None:
        mk_book(a["leader"], a["price"], f"outbid on the {s.name if s else 'stake'}")
    mk_book(o, -price, f"bid on the {s.name if s else 'stake'}")
    a.update(price=price, leader=o, bids=a["bids"] + 1)
    return price


def settle_sponsors():
    """Bidding closes: the leader sponsors the stake for the season, its purse rises with the bid, the Markers are gone."""
    for sid, a in list(G.get("sponsor_auction", {}).items()):
        s = next((x for x in sk.CALENDAR if x.id == sid), None)
        if s and a["leader"] is not None and not s.result:
            bump = min(0.5, SPONSOR_BUMP * a["price"] / sponsor_open(s))
            s.sponsor, s.purse = a["leader"], round(s.purse * (1 + bump), -3)
            G.setdefault("sponsors", {})[sid] = {"o": a["leader"], "paid": a["price"]}
            pick_news(a["leader"], f"Your barn presents the {s.name} this season. Purse ${s.purse:,.0f}.")
    G["sponsor_auction"] = {}


def sponsor_of(s):
    """The barn presenting a stake this season, or None."""
    return getattr(s, "sponsor", None) if getattr(s, "sponsor", None) in G.get("players", {}) else None


def markers(o=None):
    return P(o).get("markers", 0)


def mk_book(o, n, why):
    """Markers in or out of a barn, with a line in its Markers log. They never become cash."""
    P(o)["markers"] = max(0, markers(o) + n)
    P(o).setdefault("mk_log", []).append((G["day"], n, why))
    del P(o)["mk_log"][:-50]


def mk_tag(n, size=16):
    return f"<span class=mk>{MK_ICON(size)}{n:,}</span>"


def check_in(o):
    """The day's first visit: a Marker for showing up, five on the seventh day in a row. Once a day."""
    if P(o).get("mk_day") == G["day"]:
        return
    streak = P(o).get("streak", 0) + 1 if P(o).get("mk_day") == G["day"] - 1 else 1
    P(o)["mk_day"], P(o)["streak"] = G["day"], streak
    if streak % 7 == 0:
        mk_book(o, MK_SEVENTH, "seventh day in a row")
    else:
        mk_book(o, MK_CHECKIN, "daily check-in")
PICK_PRIZE = 1_000   # the handicapper's game: a correct stake pick earns this flat prize, small next to any purse. Measured 2026-10-29:
                     # 89 stakes a season; always-the-favorite hits 16-30%, so chalk banks about $20-27k a season at this prize


def stakes_tonight():
    """Stakes on tonight's card that haven't run: the pick'em's slate."""
    return [s for s in sk.CALENDAR if s.week == G["day"] % c.YEAR and s.result is None]


def nominees(s):
    """Who can be picked in a stake: its live nominees, or for the Crown the ten in line for an invitation."""
    if s.kind == "final":
        pool = [h for h in G["horses"] if s.eligible(h) and sk.season_earnings(h, G["day"]) > 0]
        return sorted(pool, key=lambda h: -sk.season_earnings(h, G["day"]))[:sk.FIELD]
    return [h for h in s.noms if s.eligible(h)]


def pick_news(o, msg):
    """A pick's outcome, queued for the night's notices (the tick writes those after the stakes run)."""
    G.setdefault("pick_news", {}).setdefault(o, []).append(msg)


def settle_picks(day):
    """After the stakes run: a correct pick pays the prize and counts for the season; every pick is told how it went."""
    yr = c.year_of(day)
    for s in sk.CALENDAR:
        if s.week != day % c.YEAR or s.result is None:
            continue
        if s.kind == "final" and s.result and s.result[0].owner in c.HUMAN:        # a Crown champion's barn
            mk_book(s.result[0].owner, MK_TITLE, f"Crown champion: {s.result[0].name}")
        for o, picks in G.get("picks", {}).items():
            hid = picks.pop(s.id, None)
            if hid is None or o not in c.HUMAN or not s.result:         # no pick, or a walkover: nothing to settle
                continue
            tally = G.setdefault("pickers", {}).setdefault(yr, {}).setdefault(o, [0, 0])
            tally[1] += 1
            h = next((x for x in s.result if x.id == hid), None)
            if h is not None and s.result[0] is h:
                tally[0] += 1; e.book(o, "picks", PICK_PRIZE)
                pick_news(o, f"Handicapper: your pick {h.name} won the {s.name}. Prize ${PICK_PRIZE:,}")
            else:
                ran = f"ran {s.result.index(h) + 1}{'th' if s.result.index(h) + 1 > 3 else ('st', 'nd', 'rd')[s.result.index(h)]}" if h else "didn't start"
                name = h.name if h else next((x.name for x in G["horses"] if x.id == hid), "your pick")
                pick_news(o, f"Handicapper: {name} {ran} in the {s.name}; {s.result[0].name} won it")


def name_handicapper(year):
    """At the Crown: the season's best handicapper by winners picked, with at least five picks made."""
    tally = G.get("pickers", {}).get(year, {})
    best = max((o for o in tally if tally[o][1] >= 5), key=lambda o: (tally[o][0], -tally[o][1]), default=None)
    if best is not None:
        P(best).setdefault("hcap", []).append(year)
        mk_book(best, MK_TITLE, f"Handicapper of the Year, Year {year}")
        pick_news(best, f"Handicapper of the Year: {tally[best][0]} winners from {tally[best][1]} picks. The title is yours.")


KIND_WORD = {"classic": "Classic", "memorial": "Memorial", "trophy": "Trophy", "final": "The Crown", "leg": "Sire Stakes leg",
             "opener": "Season opener", "invitational": "Invitational", "signature": "Signature stake"}


def sponsor_section():
    """On the Stakes page: a line to the Sponsor a stake page while the auction is open, with your standing."""
    auc = G.get("sponsor_auction", {})
    if not auc:
        return ""
    lead = sum(1 for a in auc.values() if a["leader"] == ME)
    return (f"<a class='btn big' href=/sponsor>Sponsor a stake · {len(auc)} open</a>"
            f"<div class=sub style='margin:4px 0 12px'>The season's stakes are up for sponsorship in Markers.{f' You lead {lead}.' if lead else ''}</div>")


def sponsor_page(qs=None):
    """Sponsor a stake, its own page: the season-start auction in Markers, filtered by division and kind, sorted
    by purse, week or current bid, twelve to a page, with a view of your own bids."""
    qs = qs or {}
    auc = G.get("sponsor_auction", {})
    div, kind, mine_, sort = qs.get("d", "all"), qs.get("k", "all"), qs.get("m") == "1", qs.get("s", "purse")
    link = lambda **kw: "/sponsor?" + "&".join(f"{k}={v}" for k, v in {"d": div, "k": kind, "m": int(mine_), "s": sort, **kw}.items())
    chips = lambda items, cur, key: "<div class=fchips>" + "".join(
        f"<a href='{link(**{key: k, 'p': 1})}' class='{'on' if str(cur) == str(k) else ''}'>{label}</a>" for k, label in items) + "</div>"
    day = G["day"]; left = SPONSOR_WEEKS - day % c.YEAR
    rows = [x for x in sk.CALENDAR if x.id in auc]
    if div != "all":
        rows = [x for x in rows if sk.DIVISION[(x.group, x.sex)] == div]
    if kind != "all":
        rows = [x for x in rows if getattr(x, "kind", "trophy") == kind]
    if mine_:
        rows = [x for x in rows if auc[x.id]["leader"] == ME]
    keyf = {"purse": lambda x: -x.purse, "week": lambda x: x.week, "bid": lambda x: -auc[x.id]["price"], "name": lambda x: x.name}[sort if sort in ("purse", "week", "bid", "name") else "purse"]
    rows.sort(key=keyf)
    PER = 12; n = max(1, -(-len(rows) // PER)); pg = max(1, min(n, int(qs.get("p", 1)) if str(qs.get("p", "")).isdigit() else 1))
    lead = [x for x in sk.CALENDAR if x.id in auc and auc[x.id]["leader"] == ME]
    head = (f"<p class=sub>Your barn's name and colors on a stake for the season, in Markers, to the highest bid when the auction closes"
            f"{f' in {left} night' + ('s' if left != 1 else '') if left > 0 else ' tonight'}. An outbid is refunded on the spot. A sponsored stake runs richer for every barn in it; "
            "the sponsor's horse races it on the same terms as any. The Crown is never for sale.</p>"
            f"<div class='card' style='display:flex;justify-content:space-between;align-items:center;gap:8px'><span>You hold {mk_tag(markers())}</span>"
            f"<span class=sub>Leading {len(lead)} · {sum(auc[x.id]['price'] for x in lead):,} Markers in bids</span></div>"
            + chips([("purse", "By purse"), ("week", "By week"), ("bid", "By current bid"), ("name", "By name")], sort, "s")
            + chips([("all", "All divisions")] + [(d, d) for d in sk.DIVISION.values()], div, "d")
            + chips([("all", "All kinds")] + [(k, w) for k, w in KIND_WORD.items() if k != "final"], kind, "k")
            + chips([(0, "Every stake"), (1, "My bids")], int(mine_), "m"))
    out = ""
    for x in rows[(pg - 1) * PER: pg * PER]:
        a = auc[x.id]; nxt = a["price"] if a["leader"] is None else a["price"] + sponsor_step(a["price"])
        who = "no bids yet" if a["leader"] is None else ("you lead" if a["leader"] == ME else f"{esc(barn_name(a['leader']))} leads")
        can = a["leader"] != ME and markers() >= nxt and not P().get("frozen")
        out += (f"<div class='skrow k{getattr(x, 'kind', 'trophy')}{' mine' if a['leader'] == ME else ''}'><div class=skl><b>{esc(x.name)}</b>"
                f"<span class=skdiv>{KIND_WORD.get(getattr(x, 'kind', 'trophy'), 'Stakes')} · {sk.DIVISION[(x.group, x.sex)]} · Harness Park · week {x.week + 1} · ${x.purse:,.0f}</span></div>"
                f"<div class=skr><b class=mk>{MK_ICON(16)}{a['price']:,}</b><span class=sub>{who}</span>"
                f"<form method=post action=/sponsor class=inline><input type=hidden name=s value={x.id}><input type=hidden name=back value='{esc(link(p=pg))}'>"
                f"<button class=sec style='padding:4px 10px'{'' if can else ' disabled'}>Bid {nxt:,}</button></form></div></div>")
    pager = ""
    if n > 1:
        lnk = lambda k, t: f"<a class=pg href='{link(p=k)}#list'>{t}</a>" if 1 <= k <= n and k != pg else f"<span class='pg{' on' if k == pg else ''}'>{t}</span>"
        pager = f"<div class=pager>{lnk(pg - 1, '&laquo;')}{''.join(lnk(k, k) for k in range(1, n + 1))}{lnk(pg + 1, '&raquo;')}</div>"
    body = (market_tabs("sponsor") + head + f"<p class=sub id=list style='scroll-margin-top:8px'>{len(rows)} stake{'s' if len(rows) != 1 else ''}{f' · page {pg} of {n}' if n > 1 else ''}</p>"
            + (out or ("<p class=sub>No stakes match.</p>" if auc else "<p class=sub>The auction opens at the start of each season and runs for its first weeks.</p>")) + pager)
    return page("Sponsor a stake", body)


def picks_section():
    """The handicapper's game on the Stakes page: tonight's stakes with a pick per stake, and the season's table."""
    day, wk = G["day"], G["day"] % c.YEAR
    mine = G.setdefault("picks", {}).setdefault(ME, {})
    cards = ""
    for s in stakes_tonight():
        noms = nominees(s)
        if len(noms) < 2:
            continue
        line = c.tote_odds(noms)
        rows = "".join(f"<label class='pkrow{' on' if mine.get(s.id) == h.id else ''}'><input type=radio name=h value={h.id}{' checked' if mine.get(s.id) == h.id else ''} onchange='this.form.submit()'>"
                       f"<b>{esc(h.name)}</b><span class=sub>{barn_tag(h.owner, 14)}</span><span class=money>{'%d-%d' % line[h.id]}</span></label>"
                       for h in sorted(noms, key=lambda h: line[h.id][0] / line[h.id][1]))
        cards += (f"<form method=post action=/pick class='card pk'><input type=hidden name=s value={s.id}><div class=row style='justify-content:space-between'>"
                  f"<b>{esc(s.name)}</b><span class=sub>${s.purse:,.0f} · tonight</span></div>{rows}</form>")
    yr = c.year_of(day); tally = G.get("pickers", {}).get(yr, {})
    table = "".join(f"<tr{brow(o)}><td>{k + 1}</td><td class=sbarn>{barn_tag(o)}{' &#127942;' * len(P(o).get('hcap', []))}</td><td>{t[0]}</td><td>{t[1]}</td><td>{100 * t[0] // t[1] if t[1] else 0}%</td></tr>"
                    for k, (o, t) in enumerate(sorted(tally.items(), key=lambda x: (-x[1][0], x[1][1]))))
    return ("<h2 id=picks>The handicapper's game</h2>"
            f"<p class=sub>Pick the winner of each stake before it runs; a winner pays a ${PICK_PRIZE:,} prize, and the season's best handicapper is named at the Crown. Free to play; picks lock at post time.</p>"
            + (cards or "<p class=sub>No stakes tonight. The next ones are below.</p>")
            + (f"<div class=card><b>Year {yr} handicappers</b><table><tr><th>#</th><th>Barn</th><th>Winners</th><th>Picks</th><th>Rate</th></tr>{table}</table></div>" if table else ""))


def race_banner():
    """At a glance: your races on tonight's posted program, and fit horses not yet entered for tomorrow."""
    bar = lambda msg, href: (f"<a href={href} style='display:block;margin:8px 0;padding:10px 12px;border-radius:6px;background:#e8a33a;color:#111;"
                             f"font-weight:700;text-decoration:none'>{esc(msg)} ›</a>")
    out = ""
    if c.CARD.get("day") == G["day"]:
        n = sum(1 for r in c.CARD["races"] if any(h.owner == ME for h in r["field"]))
        if n:
            out += bar(f"Tonight's program is up. Your races: {n}", "/program")
    idle = [h for h in mine() if not h.retired and h.freshness >= 50 and not getattr(h, "order", None) and not on_card(h)]
    if idle:
        left = int((ny_now().replace(hour=20, minute=0, second=0, microsecond=0) - ny_now()).total_seconds()) % 86400
        out += bar(f"{len(idle)} fit horse{'s' if len(idle) != 1 else ''} not entered for tomorrow. Entries drawn in {left // 3600}h {left % 3600 // 60}m", "/entries")
    open_picks = [s for s in stakes_tonight() if s.id not in G.get("picks", {}).get(ME, {}) and len(nominees(s)) >= 2]
    if open_picks:
        out += bar(f"{len(open_picks)} stake{'s' if len(open_picks) != 1 else ''} tonight: make your picks", "/stakes#picks")
    if has_pass(ME):                                                           # the Season Pass: one tap does the chores
        log = P().get("pass_log")
        if log and log[0] == G["day"]:
            out += f"<div class=ev>Stable Manager{' (you were away)' if log[3] else ''}: {log[1]} entered by the trainer, {log[2]} set{'s' if log[2] != 1 else ''} worked.</div>"
    return out


def welcome_page():
    """The launch screen: one stable per player, so no menu: who you are, and in. No race news here: results are
    revealed on Results, never on the way in."""
    day = G["day"]
    name = P().get("stable") or "Your Stable"
    rename = ("<form method=post action=/stablename class=rename><input name=n maxlength=28 placeholder='Name your stable' aria-label='Stable name'>"
              "<button>Save</button></form>") if not P().get("stable") else ""
    body = (f"<div class=launch><div class=sky><div class=in><img class=lg src=/mock/brand/logo_text.png alt='Trot Dynasty'>"
            f"<img class=tr src=/mock/brand/title_trotter.png alt=''></div></div><div class=tag>Breed · Race · Win</div>"
            f"<div class=away><small>Welcome back</small><b>{esc(name)}</b>{rename}"
            f"<em>Year {c.year_of(day)}, week {day % c.YEAR + 1} · ${e.cash[ME]:,.0f}</em></div>"
            f"{race_banner()}<a class=enter href=/>Enter the barn</a></div>")
    return (f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            f"<title>Trot Dynasty</title>{HEAD}{FONTS}<style>{CSS}{SKIN}{theme_css()}{LAUNCH_CSS}</style></head><body>{body}</body></html>")


def login_page(signup_, error="", local=False):
    """Log in, or make an account: every account is its own barn on the shared circuit."""
    claim = ("<label class=claim><input type=checkbox name=claim value=1 checked> Take over the existing playtest stable</label>"
             if signup_ and local and "user" not in P(0) else "")
    other = ("<p class=alt>Have an account? <a href=/login>Log in</a></p>" if signup_ else "<p class=alt>New here? <a href=/signup>Make an account</a></p>")
    body = (f"<div class=launch><div class=sky><div class=in><img class=lg src=/mock/brand/logo_text.png alt='Trot Dynasty'>"
            f"<img class=tr src=/mock/brand/title_trotter.png alt=''></div></div><div class=tag>Breed · Race · Win</div>"
            f"<form method=post action={'/signup' if signup_ else '/login'} class='away auth'><small>{'Make your stable' if signup_ else 'Welcome back'}</small>"
            + (f"<p class=err>{esc(error)}</p>" if error else "")
            + "<input name=user placeholder='Name' autocomplete=username autocapitalize=off required>"
            f"<input name=pw type=password placeholder='Password' autocomplete={'new-password' if signup_ else 'current-password'} required>"
            f"{claim}<button class=enter>{'Start my stable' if signup_ else 'Log in'}</button></form>{other}</div>")
    return (f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            f"<title>Trot Dynasty</title>{HEAD}{FONTS}<style>{CSS}{SKIN}{theme_css()}{LAUNCH_CSS}</style></head><body>{body}</body></html>")


LAUNCH_CSS = """
.auth{display:grid;gap:10px}.auth input[name]{width:100%;box-sizing:border-box;padding:12px}.auth .enter{width:100%;cursor:pointer}
.err{margin:0;color:#ff8a6b;font-weight:600}.claim{font-size:14px;color:var(--ink2);display:flex;gap:8px;align-items:center}
.alt{color:var(--ink2);margin-top:16px}.alt a{color:var(--led);text-decoration:underline}
.launch{position:relative;max-width:none;margin:0;padding:0 0 32px;text-align:center}
/* the title on the track: the top bar's night panorama as a wide strip, the night fading into the page below */
.sky{position:relative;min-height:240px;background:var(--sky) url(/mock/pixel/panorama.png) 38% bottom/auto 100% repeat-x;image-rendering:pixelated}   /* sized by the title and trotter: nothing clips */
.sky:after{content:'';position:absolute;inset:0;background:linear-gradient(180deg,#070a1480 0,#070a1420 35%,#070a14 100%)}
.sky .in{position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;padding:max(28px,env(safe-area-inset-top)) 16px 0}
.launch .lg{width:min(72%,340px);filter:drop-shadow(0 6px 0 #000)}.launch .tr{display:block;width:min(66%,300px);margin:4px auto 0;filter:drop-shadow(0 10px 8px #000c)}
@media (min-width:700px){.launch .lg{width:min(88%,380px)}.launch .tr{width:min(78%,320px)}}
.launch .tag{font:700 14px 'Barlow Condensed',sans-serif;letter-spacing:.42em;text-transform:uppercase;color:var(--led);margin:14px 0 18px}
.auth,.alt{max-width:430px;margin-left:auto;margin-right:auto}.auth{margin:0 max(16px,calc(50% - 215px))}
.away{text-align:left;background:var(--well,#0b1120);border:2px solid var(--rule);box-shadow:3px 3px 0 var(--edge);padding:14px 16px}
.away small{font:700 12px 'Barlow Condensed',sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3)}
.away b{display:block;font:800 26px/1.1 'Barlow Condensed',sans-serif;text-transform:uppercase;letter-spacing:.04em;margin:2px 0}
.away em{font:600 14px 'Barlow Semi Condensed',sans-serif;color:var(--led);font-style:normal}
.away ul{list-style:none;margin:12px 0 0;padding:10px 0 0;border-top:2px solid var(--rule2);display:grid;gap:9px;font:600 15px/1.3 'Barlow Semi Condensed',sans-serif}
.away li i{display:inline-block;min-width:62px;font:700 12px 'Barlow Condensed',sans-serif;letter-spacing:.06em;font-style:normal;color:var(--ink2)}
.away li i.won{color:#7dffa2}.away li i.trophy{color:#ffd27a}.away li i.rec{color:#ff8a6b}
.rename{display:flex;gap:6px;margin:6px 0 8px}.rename input{flex:1;min-width:0}
.enter{display:block;margin-top:14px;background:var(--tote);color:#2a1a03;border:2px solid #ffd27a;box-shadow:3px 3px 0 var(--edge),inset 0 2px 0 #fff4;
  padding:14px;font:800 22px 'Barlow Condensed',sans-serif;letter-spacing:.1em;text-transform:uppercase;text-decoration:none}
"""


def more_page():
    """Everything past the three everyday tabs, grouped by what it's for."""
    def item(href, name, note, live=True):
        return (f"<a class=mi href={href}><b>{name}</b><span class=sub>{note}</span></a>" if live
                else f"<div class='mi off'><b>{name}</b><span class=sub>{note}</span></div>")
    groups = (("Racing", [item("/results", "Results", "last night's starts for your horses"),
                          item("/stakes", "Stakes & Crown", "stakes, memorials, the Crown and its champions"),
                          item("/program", "Tonight's program", "every race on the card: fields, form, morning lines, claims"),
                          item("/guide", "Compendium", "how the circuit works, what a horse's card means, and the craft of winning")]),
              ("The circuit", [item("/leaders", "Leaderboards", "top horses and barns"),
                               item("/archive", "History and search", "every horse and season on record")]),
              ("Your operation", [item("/earnings", "Earnings", "where your money came from and went"),
                                  item("/crest", "Barn identity", "build your emblem, Marquee, name and title")]))
    body = "".join(f"<div class=secbar>{g}</div>" + "".join(items) for g, items in groups)
    cur = P().get("skin", "clubhouse")
    body += ("<div class=secbar>Theme</div><div class=themes>" + "".join(
        f"<a href='/skin?s={k}' class='{'on' if k == cur else ''}' style='--sw:{THEMES[k].split(';')[1].split(':')[1] if THEMES[k] else '#111a2b'};"
        f"--sl:{(THEMES[k] or '').split('--led:')[1].split(';')[0] if THEMES[k] and '--led:' in THEMES[k] else '#ffb347'}'><i></i>{k.title()}</a>"
        for k in THEMES) + "</div>")
    body += ("<div class=secbar>Tips</div><div class=row style='padding:8px 0;justify-content:space-between'>"
             f"<span class=sub>Tip cards {'are hidden' if P().get('hide_tips') else 'show while replays load and after race night'}</span>"
             f"<form method=post action=/tips class=inline><button class=sec name=hide value={0 if P().get('hide_tips') else 1}>{'Show tips' if P().get('hide_tips') else 'Hide tips'}</button></form></div>")
    # install: Chrome/Android hand us a prompt; iPhone needs Share → Add to Home Screen; hidden once installed
    body += ("<div id=appsec><div class=secbar>Get the app</div><div class=row style='padding:8px 0;justify-content:space-between;flex-wrap:wrap;gap:8px'>"
             "<span class=sub id=appnote>Put Trot Dynasty on your home screen: it opens full screen like any app.</span>"
             "<button class=sec id=appbtn hidden onclick='tdInstall.prompt();tdInstall.userChoice.then(()=>appsec.remove())'>Install</button></div></div>"
             "<script>if(matchMedia('(display-mode: standalone)').matches||navigator.standalone)appsec.remove();"
             "else if(/iPhone|iPad|iPod/.test(navigator.userAgent))appnote.innerHTML='On iPhone: tap <b>Share</b> in Safari, then <b>Add to Home Screen</b>.';"
             "else{const s=()=>{if(window.tdInstall)appbtn.hidden=false};s();addEventListener('beforeinstallprompt',s)}</script>")
    body += (f"<div class=secbar>Account</div><div class=row style='padding:8px 0'><span class=sub>Signed in as {esc(P().get('user', '?'))}</span>"
             "<form method=post action=/logout class=inline><button class=sec>Log out</button></form></div>")
    if ME == ADMIN:
        body += ("<div class=secbar>Playtest</div><div class=row style='padding:8px 0'><a class='btn sec' href=/admin>Admin desk</a>"
                 "<form method=post action=/advance class=inline><button class=sec name=days value=7>+7 weeks</button></form>"
                 "<form method=post action=/advance class=inline><button class=sec name=days value=run>Run until something happens</button></form></div>")
    return page("Manage", body)


def review_flags():
    """Pairs of player barns the stewards should look at, with why. One barn per person is the rule; a second barn feeding
    the first, or a real-money deal outside the game, both show up the same way: shared sign-ins, or sales between the
    same two barns at prices far from the horse's worth. Signals only: the admin decides."""
    pl, flags = G.get("players", {}), {}
    def add(a, b, why):
        k = tuple(sorted((a, b)))
        if k not in G.get("cleared", []):
            flags.setdefault(k, []).append(why)
    ids = sorted(pl)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if a == ADMIN or b == ADMIN:
                continue
            shared = set(pl[a].get("ips", [])) & set(pl[b].get("ips", [])) - {"127.0.0.1"}
            if shared:
                add(a, b, f"signed in from the same address ({len(shared)} shared)")
            if shared and set(pl[a].get("uas", [])) & set(pl[b].get("uas", [])):
                add(a, b, "same address and the same device")
    pair = collections.defaultdict(list)
    for d, s, b, hid, price, worth in e.trades:
        if s in pl and b in pl:
            pair[tuple(sorted((s, b)))].append((d, s, b, hid, price, worth))
    for (a, b), ts in pair.items():
        if len(ts) >= 3:
            add(a, b, f"{len(ts)} sales between them")
        cheap = [t for t in ts if t[5] > e.MIN_PRICE and t[4] < t[5] / 3]
        if cheap:
            add(a, b, f"{len(cheap)} sold for under a third of worth")
        flow = sum(t[4] if t[2] == a else -t[4] for t in ts)
        if len(ts) >= 2 and abs(flow) == sum(t[4] for t in ts):
            add(a, b, f"cash only ever goes one way (${abs(flow):,.0f})")
    return flags


def admin_page(msg=""):
    """The admin's desk: cash for any barn, undo the last race night, run a night now, and who's playing."""
    snaps = sorted(os.listdir(SNAPS)) if os.path.isdir(SNAPS) else []
    ago = lambda t: "never" if not t else f"{int((time.time() - t) // 60)}m ago" if time.time() - t < 3600 else \
        f"{int((time.time() - t) // 3600)}h ago" if time.time() - t < 86400 else f"{int((time.time() - t) // 86400)}d ago"
    rows = "".join(f"<tr><td><b>{esc(p.get('user', '?'))}</b><div class=sub>{esc(barn_name(o))}</div></td>"
                   f"<td style='text-align:right'>${e.cash.get(o, 0):,.0f}</td>"
                   f"<td style='text-align:right'>{sum(1 for h in G['horses'] if h.owner == o and not h.retired)}</td>"
                   f"<td style='text-align:right' class=sub>{ago(p.get('last_seen'))}</td>"
                   f"<td><form method=post action=/admin/pass class=inline><input type=hidden name=o value={o}><button class=sec style='padding:3px 8px'>{'Pass: on' if p.get('pass') else 'Pass: off'}</button></form></td></tr>"
                   for o, p in sorted(G["players"].items()))
    opts = "".join(f"<option value={o}>{esc(p.get('user', '?'))} · {esc(full_name(o))}</option>" for o, p in sorted(G["players"].items()))
    last = f"Year {c.year_of(int(snaps[-1][6:12]))}, week {int(snaps[-1][6:12]) % c.YEAR + 1}" if snaps else ""
    body = ((f"<div class=card><b>{esc(msg)}</b></div>" if msg else "")
            + "<div class=secbar>Players</div><table><tr><th>Player</th><th style='text-align:right'>Cash</th>"
              "<th style='text-align:right'>Racers</th><th style='text-align:right'>Seen</th><th></th></tr>" + rows + "</table>"
            + "<div class=secbar>Cash</div><form method=post action=/admin/cash class=card style='display:flex;gap:8px;flex-wrap:wrap;align-items:center'>"
              f"<select name=o>{opts}</select><input name=amt type=number step=1000 placeholder='+/- amount' style='width:140px'>"
              "<button>Apply</button><div class=sub style='width:100%'>A negative amount takes cash away.</div></form>"
            + "<div class=secbar>Markers</div><form method=post action=/admin/markers class=card style='display:flex;gap:8px;flex-wrap:wrap;align-items:center'>"
              f"<select name=o>{opts}</select><input name=n type=number step=1 placeholder='+/- Markers' style='width:140px'><button>Apply</button>"
              "<div class=sub style='width:100%'>Until there's a store. Markers buy sponsorships and looks, never horses.</div></form>"
            + "<div class=secbar>Sponsorship auction</div><form method=post action=/admin/sponsor class=card style='display:flex;gap:8px;flex-wrap:wrap;align-items:center'>"
              f"<button class=sec name=do value=open>Open for this season</button><button class=sec name=do value=close>Close and settle</button><div class=sub style='width:100%'>{len(G.get('sponsor_auction', {}))} stakes up for bids · {len(G.get('sponsors', {}))} sponsored this season. Opens itself at every year roll and settles after week {SPONSOR_WEEKS}.</div></form>"
            + "<div class=secbar>Gift a horse</div><form method=post action=/admin/gift class=card style='display:flex;gap:8px;flex-wrap:wrap;align-items:center'>"
              f"<select name=o>{opts}</select><input name=h placeholder='Horse name' style='width:160px'><select name=mode><option value=exact>this horse</option><option value=like>one like it</option><option value=clone>an identical copy (dev)</option></select>"
              "<button>Give</button><div class=sub style='width:100%'>Exact: a computer barn's racer by name. Like: the nearest computer-owned racer of the same age by rating.</div></form>"
            + "<div class=secbar>Message from the barn</div><form method=post action=/admin/msg class=card style='display:flex;flex-direction:column;gap:8px'>"
              "<textarea name=text maxlength=280 rows=3 placeholder='New tonight: ...' style='font:inherit;font-size:16px;padding:8px;background:var(--panel);color:var(--ink);border:1px solid var(--rule)'></textarea>"
              f"<div class=row style='justify-content:space-between'><span class=sub>Each player sees it once, on their next card. {len(G.get('team_msgs', []))} posted so far.</span><button>Post</button></div></form>"
            + "<div class=secbar>Clock</div><div class=card style='display:flex;gap:8px;flex-wrap:wrap;align-items:center'>"
            + (f"<b>Frozen at {G['frozen']}</b><form method=post action=/admin/clock class=inline><button name=at value=''>Unfreeze</button></form>"
               "<div class=sub style='width:100%'>Race night won't run while the clock is frozen. Unfreezing throws away an early draw and reopens entries.</div>"
               if G.get("frozen") else
               "<form method=post action=/admin/clock class=inline><button class=sec name=at value='19:45'>Freeze at 7:45 PM</button></form>"
               "<form method=post action=/admin/clock class=inline><button class=sec name=at value='19:00'>Freeze at 7:00 PM</button></form>"
               "<div class=sub style='width:100%'>For a look at the program and claims as players will see them. Unfreeze before race night.</div>")
            + "</div>"
            + "<div class=secbar>Race night</div><div class=card style='display:flex;gap:8px;flex-wrap:wrap'>"
              "<form method=post action=/advance class=inline><button name=days value=1>Run a race night now</button></form>"
            + (f"<form method=post action=/admin/undo class=inline><button class=sec onclick=\"return ask(this,'Undo the race night of {last}? "
               f"Everything since it ran goes back.')\">Undo last race night ({last})</button></form>" if snaps else "<span class=sub>No race night to undo yet.</span>")
            + f"<div class=sub style='width:100%'>{len(snaps)} night{'s' if len(snaps) != 1 else ''} can be undone, newest first.</div></div>")
    body += ("<div class=secbar>New world</div><form method=post action=/newgame class=card style='display:flex;gap:8px;flex-wrap:wrap;align-items:center'>"
             "<input name=confirm placeholder='Type NEW WORLD' style='width:170px' autocomplete=off><button class=warn onclick=\"return ask(this,'Start a new world? Every barn starts over. The old world is backed up first.')\">Start a new world</button>"
             "<div class=sub style='width:100%'>Builds a fresh circuit with its own fifty-year past (a few minutes, the game pauses), backs the old world up beside the save, and gives every player a new starter barn under the same login and name. Records, trophies and cash do not carry over.</div></form>")
    flags, frozen = review_flags(), [o for o, p in G["players"].items() if p.get("frozen")]
    who = lambda o: esc(G["players"].get(o, {}).get("user", "?"))
    body += "<div class=secbar>Stewards' review</div>"
    for (a, b), whys in sorted(flags.items()):
        body += (f"<div class=card><b>{who(a)}</b> and <b>{who(b)}</b><div class=sub>{'; '.join(esc(w) for w in whys)}</div>"
                 f"<form method=post action=/admin/review class='row' style='gap:8px;margin-top:6px'><input type=hidden name=a value={a}><input type=hidden name=b value={b}>"
                 "<button class=sec name=do value=clear>Clear</button><button class=sec name=do value=warn>Warn both</button>"
                 "<button class=warn name=do value=freeze>Freeze both</button></form></div>")
    if not flags:
        body += "<div class=sub>Nothing flagged: no shared sign-ins and no odd sales between barns.</div>"
    for o in frozen:
        body += (f"<div class=card><b>{who(o)}</b> is frozen: can race, can't buy or sell.<form method=post action=/admin/review class=inline>"
                 f"<input type=hidden name=a value={o}><input type=hidden name=b value={o}><button class=sec name=do value=unfreeze>Unfreeze</button></form></div>")
    return page("Admin", body)


GUIDE = [
    ("The circuit", [
        ("Your stable", "You run one barn on a circuit of harness tracks, alongside the other players and the circuit's long-established "
         "barns. Every horse in the book has a sire, a dam, a record and a family: the history of this circuit runs back long before "
         "you arrived. Build a string, win races, breed the next generation, and leave a dynasty behind."),
        ("The training bill", "Your trainer charges a day rate for every horse in work: stall, feed, shoeing, jogging and training. "
         "Your retired stock boards at the farm for less. Both bills come out of your cash each race night. A good horse pays its own "
         "way many times over; a slow one costs you to keep, so sell, retire or drop down the ones that aren't earning. If the bills "
         "ever run past your cash, they come out of your next purses."),
        ("Race night", "The circuit races once a day, at 8:00 PM Eastern. Each race night is a week of the season, and the season "
         "builds to the Crown, which closes it. On this circuit you enter a day ahead: the moment tonight's card has "
         "run, tomorrow's program is drawn from the entries and posted, so you have all day to read the form, make your claims and "
         "scratch if you need to. The countdown at the top of the screen tells you where you are in the day."),
        ("The tracks", "The circuit's tracks come in two sizes. Mile tracks have long, sweeping turns and reward a horse that can sustain "
         "its speed. Half-mile tracks have four tight turns: gate speed and a good post count for more there, and every mile is slower. "
         "Each track has its own character, its own slate of races and its own purse level; you'll see them when you enter a horse. "
         "Bayview Fair doubles its purses during fair week."),
        ("The passing lane", "Some tracks have a passing lane: down the homestretch the inside rail swings into the infield and opens an "
         "extra lane inside the leader. Only the horse sitting directly behind the leader may use it, so at these tracks the pocket "
         "trip rarely gets shut in. Front-runners like these tracks a little less. They're marked on Entries and the program."),
    ]),
    ("Your horses", [
        ("The four stats", "<b>Speed</b> is raw pace: how fast a horse can go and how quickly it gets into position off the gate. "
         "<b>Stamina</b> is how well it carries that speed: through a hard pace, a trip parked on the outside, a long tough mile. "
         "<b>Finish</b> is the kick in the stretch. <b>Manners</b> is how a horse behaves on the track: a well-mannered horse goes "
         "where its driver asks and gets the trip it wants; a rank one gets shuffled into bad spots, and is more likely to break stride. "
         "The bars on each horse's card show where it stands; color moves from grey through yellow and green, and the very best "
         "shimmer."),
        ("Mile time and tier", "<b>Mile time</b> is how fast your horse is expected to trot a mile, worked out from its "
         "races. It updates after every start. A horse that hasn't raced yet gets an estimate from its parents.<br><br>"
         "<b>Tier</b> is a letter grade that comes from the mile time:" 
         "<div class=tierrow><span class=tl>worst</span><b style='background:#a1a1aa'>D</b><b style='background:#6b7280'>C</b><b style='background:#1f7a3f'>B</b><b style='background:#1f4fbf'>A</b><b style='background:#b45309'>S</b><b class=tsp>S+</b><span class=tl>best</span></div>"
         "Young horses usually start low and move up as they get faster."),
        ("Preferred position", "Every horse has a place it likes to race: out on the lead, sitting just off the pace, settled mid-pack, "
         "or dropped out to close. The arrows on its card show it. A horse that gets where it wants runs its race; one that doesn't "
         "wastes some of what it has. Manners decides how often it gets its way."),
        ("Development", "Horses race from two. Most improve through three and four, peak somewhere in their middle years and then slowly "
         "decline; some are early bloomers, some late. A horse's Development chart is the trainer's read of that arc, showing where it is "
         "now: developing, in its prime, just past its peak, or declining."),
        ("Training the youngsters", "Yearlings, 2-year-olds and 3-year-olds are yours to make, and the Training tab is their day sheet. "
         "Each gets one job a day. A yearling comes up in stages, one at a time: <b>break</b> work to get it used to the harness, then "
         "<b>jogging</b>. Once it's broke and jogged, its days are <b>training miles</b> on the focus you choose, or a <b>turn out</b> "
         "for a day off. Training miles are the big step and take something out of a horse, so a tired one "
         "can't go. A youngster you don't get to is jogged by the stable, which keeps it coming along but leaves it the horse its blood "
         "made; only your hands decide what kind of horse it becomes. A yearling worked through its year comes to the races further "
         "along than one left in the field. Older horses are past making: they're kept fit and sound, not trained."),
        ("Freshness and grooming", "Racing takes it out of a horse. Freshness drops with each start and comes back with rest; a horse "
         "isn't fit to race until it has recovered enough, and some horses bounce back faster than others. Grooming speeds the recovery: "
         "your barn has a few grooming slots each week, and bigger barns have more. Pick your spots: a fresh horse runs its best."),
        ("Retirement", "Racers retire as they age, or whenever you choose. A retired filly or mare can join your broodmare band and a "
         "colt with a good record can stand at stud; their racing record and their best rating stay in the book for good."),
    ]),
    ("Entering a race", [
        ("Entries", "Tap the + on a horse's card in your barn to see every race it qualifies for, track by track, and enter it. "
         "Nothing in your barn races unless you enter it."),
        ("Race classes", "<b>Opens</b> are for the best of each age; an older horse climbs from the Aged Open through the Open and the "
         "Preferred to the Invitational at the top of the ladder, "
         "and above them the <b>Winners Over</b> races, where the best horses meet others who have earned as much as they have. "
         "When too few are entered, a Winners Over race isn't carded and its horses race the Invitational. "
         "<b>Conditioned races</b> keep horses with like records together: NW1 is for non-winners of a race, NW2L6 for horses that "
         "haven't won two of their last six, NW$20k for horses that haven't earned a set amount, and so on. "
         "<b>Claiming races</b> (CLM) carry a price tag: every horse in one is for sale at that price. The ladder runs from cheap "
         "claimers up to tags that only a top horse carries, and the purse at each rung sits beside the condition class for horses of "
         "that level: a little richer, since the owner is risking the horse."),
        ("Claiming", "In a claiming race any other barn can put in a claim on your horse before post time, and you can claim theirs. "
         "A claim is binding: if the horse races, it changes hands at the tag whatever the result, and the purse goes to the old owner. "
         "Drop a horse into a cheap claimer and it may win easily, but you may lose it."),
        ("The program", "Tonight's program is drawn and posted at 8 PM the night before: fields filled out, race numbers, post "
         "positions by random draw, the morning line, each horse's recent form and the handicapper's pick. Those exact fields go "
         "to the gate at 8:00, less any scratches. Your races are shown first. A horse on the program can still be entered "
         "for the next night."),
        ("Drivers", "Every horse goes to the gate with a driver, and every driver wears his own colors. Pick your barn's top three "
         "on the Drivers tab. Your horses get your first choice; when he's already driving one of your better horses in the same race, "
         "they get your next. Each driver has his own way of getting a horse around: some get away from the gate, some wait and "
         "come late, some know the half-mile tracks, some settle a rank horse. The standings show who's winning this season."),
        ("Post Time Tonic", "Sold in the Market's Shop. Once a horse is entered, tap the bottle on its card to give it a tonic for the "
         "night: Speed, Stamina, Finish or Manners each lift that side of its game, and the Premium lifts all four. The vet charges a "
         "small share of the race's purse to give it. On this circuit it's allowed as part of race prep, and nobody else knows who's on what. A tonic "
         "helps; it doesn't make a slow horse fast."),
    ]),
    ("On the track", [
        ("Trips", "How a race unfolds matters as much as how fast a horse is. The <b>leader</b> sets the pace and runs the shortest way "
         "round. The <b>pocket</b>, sitting right behind the leader, is the classic trip: sheltered, saving ground, waiting for the "
         "stretch, though it can get boxed in. <b>First-over</b> means pulling out to race on the outside and take the field to the "
         "leader with no cover: honest, hard work. Horses tucked in behind it get cover. <b>Closers</b> sit back and come late, and a "
         "fast early pace sets it up for them. A horse can also <b>break stride</b> and lose its chance."),
        ("Pace", "When two quick horses fight for the lead, the pace gets hot, the speed horses pay for it late, and the closers come "
         "into it. When one horse gets the lead to itself, it can slow things down and is hard to run down. Read the program for "
         "who has speed."),
        ("Post position", "Posts are drawn at random. An inside post saves ground; an outside post costs a little, more so on a "
         "half-mile track's tight turns."),
        ("Upsets", "The best horse doesn't always win. A bad trip, a hot pace, a break, a horse that's sharper tonight than its "
         "record says: harness racing has its surprises, and every so often something remarkable happens."),
    ]),
    ("After the races", [
        ("Results and replays", "Results are spoiler-free: your starters are listed in post order, and you choose when to reveal each "
         "result or watch the replay. The barn sends you to Results first after a race night, so nothing gets spoiled. The replay is "
         "the race as it was run: watch from the grandstand, from the blimp, or the TV coverage."),
        ("Money", "Purses pay down the order of finish, with the lion's share to the winner. The trainer and driver take their cut of "
         "what each horse wins. Your Earnings page shows where every dollar came from and went."),
        ("The Market", "The <b>Auction</b> is the sale board, and the only place a horse changes hands between barns: every horse "
         "runs a full day in the open, bid in steps, with a late bid putting time back on the clock, and the highest bid at the close "
         "takes it. There are no private deals, so the price of a horse is whatever the circuit's barns will pay. Bidding never opens "
         "under what the house would pay for the horse, the house takes its commission on every sale, and a horse you buy stays in "
         "your barn a few weeks before it can be sold on. You can also buy an unraced 3-year-old from the house, sight unseen: most are "
         "ordinary, a few are something special. The <b>Shop</b> sells Post Time Tonic, with more to come. Sell your own horses on "
         "the board, or to the house, which pays on the record: more for a proven earner, a floor for the rest."),
        ("The claimers board", "Under Market, the Claimers board lists every horse in a claiming race on tonight's program, "
         "the tag it can be taken for, its record and its last starts, sorted and filtered however you scout. A claim is the "
         "same from here as from the program: binding if the horse races, whatever the result, and settled when the card runs. "
         "Your own claimers show on the board too, so you know who's exposed tonight."),
        ("The handicapper's game", "Every stake on the calendar is also a contest for the barns: pick its winner from the nominees "
         "before it runs, one pick a stake, free. A winner earns a small prize from the track, the same for every stake, and the "
         "season's best handicapper is named at the Crown. It's a prize for reading the form, not a wager: nothing is staked and "
         "nothing can be lost."),
        ("The Stable Manager", "What the Season Pass buys: a manager who does your chores in one tap. The trainer's entries for "
         "every fit horse, and every youngster's standing orders from the Training tab: the last set you gave each one, "
         "saved from its day sheet, which you change any time by working it by hand. Miss a night and the manager covers you, for a few nights in a row, then waits for you. It never "
         "enters a claimer, never nominates for a stake, and never does anything you couldn't do yourself with a few taps."),
    ] + ([
        ("Sponsoring a stake", "At the start of every season the stakes go up for sponsorship, in Markers, to the highest bid. "
         "The sponsor's barn presents that stake for the season: its name and colors on the calendar, the program and the track, "
         "and the purse runs richer for every barn in it. Sponsoring buys the name, nothing on the track: the sponsor's horse "
         "races the stake on the same terms as any other. The Crown is never for sale."),
    ] if SPONSORING else []) + [
        ("Markers", "The track's own chits, shown beside your cash when you hold any. Markers buy the look of "
         "your barn; they never buy a horse, a cover, a claim or an entry, and they never turn into cash. A few come free for "
         "showing up each day, with a bonus for a week straight, and the season's titles pay them too."),
        ("Fair play", "Nothing you can buy for real money wins a race, buys a horse, or makes one grow faster: horses are earned on the "
         "track, in the ring and in the breeding shed, at the same price for everyone. Each person runs one barn. The stewards review "
         "sales that look wrong, such as horses passed between the same two barns for far under their worth, and a barn under review "
         "can race but not buy or sell until it's cleared."),
        ("Barn upgrades", "A bigger barn means more stalls, more grooming slots each week, and the Breeder's License and broodmare space "
         "you need to breed your own."),
    ]),
    ("Stakes and the Crown", [
        ("Stakes", "The big races of the season, on the Stakes & Crown page. Most must be nominated in advance, with a fee to keep a horse "
         "eligible; nominate early and it costs less. Stakes are run at Harness Park and carry the richest purses on the circuit. "
         "Each stake is for colts, for fillies and mares, or for both, and when a division has a fillies' race that week the open "
         "one is the colts'. A horse starts in one stake a night."),
        ("The Crown", "The season closes with the Crown: the top earners in each division are invited to its championship, and the "
         "winner is that year's champion. One title per division per year, and it stays in the book forever."),
        ("Trophies and records", "Stakes wins, championships and course records go in a horse's trophy case. Every track keeps its own "
         "course record; break it and the whole circuit hears about it."),
    ]),
    ("Breeding", [
        ("Stallions and mares", "Book a mare to a stallion standing at stud from her own page; the fee is the price of the cover. "
         "Your own stallions cover your own mares free. Foals take after both parents, sometimes better than either, sometimes not."),
        ("Lines and nicks", "Every horse belongs to a family line, and some lines cross better than others. A pedigree scout can rate "
         "how a stallion's line crosses with a mare's, from a poor nick up to a golden cross."),
        ("Foals", "A foal is born into your nursery and grows up through its weanling and yearling years. As a yearling it goes on "
         "your Training day sheet, and a yearling worked through its year comes to the races further along. At two it can be registered "
         "to race, for a flat fee, and moves into your racing barn. Until then it keeps its place in the shed, and the house will take "
         "an unregistered horse off your hands for a token price. Its early rating is a guess from its pedigree until it gets to the races."),
    ]),
    ("Your barn's name", [
        ("Silks and emblems", "Every barn races in its silks: a jacket in two colors and a pattern, shown beside its name everywhere "
         "on the circuit and free to change. A barn that wants more can buy an emblem license and build an emblem of its own: a frame, "
         "an icon and its colors. Frames and icons are bought; the trophy icons and the titles that come with them can only be won."),
        ("The Marquee and Prestige", "The elite barns can buy a Marquee: their top bar on every screen becomes a lit banner that every "
         "player sees, and it hangs over the winner's circle when their horse wins. It starts as a plain gilded nameplate and grows "
         "through ten tiers of Prestige as the barn wins: big races, Crown finals, championships, course records and a long career "
         "all move it up the ladder. A tier is awarded while the barn holds the Stable Manager's pass; the record keeps counting "
         "in between, and the next season with the pass collects whatever was earned. Each tier is kept for good once reached, "
         "and the barn's tier shows beside its name. The owner chooses which tier to show and which trophies sit on its shelf."),
        ("The Tack Room", "Where a barn keeps its gear. A design is bought once for the barn, in Markers, and worn in the barn's two "
         "colors: the harness, the face mask, the leg wraps and the bike, with the bike and its hub colored apart. Fitting a "
         "horse is a small charge each time; the gear stays with the barn when a horse leaves. Gear is looks, nothing more: a "
         "horse races the same in it or out of it. The most prestigious barns fit their horses for free."),
    ]),
]


def guide_page():
    """The Compendium: the world the player is in, how to read it and why it matters, in plain words. No formulas,
    no numbers behind the curtain: what a horseman would know, not what the engine does."""
    roman = "I II III IV V VI VII VIII IX X XI XII".split()
    body = (BOOK_CSS + "<div class=book><div class=bkhead><span>The Compendium</span><span>Trot Dynasty</span></div>"
            "<div class=bktitle><b>The Compendium</b><span>being a horseman's manual of the circuit</span></div><div class=bkrule></div>"
            "<p class=bkintro>How the circuit works, what the numbers on a horse's card mean, and the craft of getting a horse to the "
            "winner's circle. Open a chapter, then a topic.</p>")
    for i, (part, topics) in enumerate(GUIDE):                    # chapters fold open to their topics, topics to their text
        body += (f"<details class=bkch><summary><i>{roman[i]}.</i><span class=bkchn>{esc(part)}</span><span class=bkdots></span></summary>" + "".join(
            f"<details class=bktp><summary>{esc(t)}</summary><div class=bktxt>{txt}</div></details>" for t, txt in topics) + "</details>")
    return page("Compendium", body + "<div class=bkfoot>&#10086;</div></div>")


# The Compendium as an old horseman's manual: an aged page under the track lamps, the one light surface in the game.
BOOK_CSS = ("<link href='https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=IM+Fell+English+SC&display=swap' rel=stylesheet><style>"
    ".book{position:relative;margin:4px 6px 16px;background:#e9dcbd;color:#2b2016;border-radius:2px 6px 6px 2px;padding:18px 16px 12px 18px;"
    "font-family:'IM Fell English',Georgia,serif;"
    "background-image:radial-gradient(90% 60% at 50% 12%,rgba(255,236,190,.55),transparent 70%),radial-gradient(160% 100% at 50% 50%,transparent 60%,rgba(110,74,30,.35));"
    "box-shadow:-3px 0 0 #cdbd98,-6px 0 0 #b9a77f,0 10px 26px #000,0 0 60px rgba(232,163,58,.12)}"
    ".bkhead{display:flex;justify-content:space-between;font:12px 'IM Fell English SC',Georgia,serif;color:#7a6446;letter-spacing:.08em;border-bottom:1px solid #b9a27a;padding-bottom:4px;margin-bottom:12px}"
    ".bktitle{text-align:center;margin:4px 0 12px}.bktitle b{display:block;font:italic 900 28px 'Playfair Display',Georgia,serif;color:#3a2412}"
    ".bktitle span{font:15px 'IM Fell English SC',Georgia,serif;color:#6b5236}"
    ".bkrule{height:5px;border-top:1px solid #7a5a36;border-bottom:1px solid #7a5a36;margin:0 30px 10px}"
    ".bkintro{font-style:italic;font-size:15px;line-height:1.45;color:#4a3826;text-align:center;margin:0 6px 8px}"
    ".book details{border-bottom:1px dotted #b39b72}.book summary{list-style:none;cursor:pointer;display:flex;align-items:baseline;gap:10px;"
    "padding:9px 0;margin:0;border:0;background:none;text-transform:none;letter-spacing:0;text-shadow:none}"
    ".book summary::-webkit-details-marker{display:none}.book details>summary::after,.book details[open]>summary::after{content:none!important}"
    ".book summary{font-family:'IM Fell English',Georgia,serif!important;font-weight:400!important;text-transform:none!important;letter-spacing:0!important}"
    ".bkch>summary{font:19px 'IM Fell English SC',Georgia,serif!important;color:#2b2016}.bkch>summary i{font:italic 15px 'IM Fell English',Georgia,serif;color:#8a2a1c;min-width:34px}"
    ".bkchn{flex:0 1 auto}.bkdots{flex:1;border-bottom:1px dotted #9c8462;transform:translateY(-4px)}"
    ".bktp>summary{font-size:16px;color:#4a3826;padding-left:44px}.bktp[open]>summary{color:#8a2a1c}.bkch .bktp:last-child{border-bottom:0}"
    ".bktxt{padding:0 0 14px 44px;font-size:16.5px;line-height:1.48;text-align:justify;hyphens:auto;color:#2b2016}"
    ".bktxt b{font-weight:normal;font-style:italic}.bktxt::first-letter{float:left;font-size:46px;line-height:.82;color:#8a2a1c;padding:6px 6px 0 0}"
    ".bktxt .tierrow{margin:8px 0}.bktxt .tierrow b{font:normal 800 15px 'Barlow Semi Condensed',sans-serif}.bktxt .tierrow .tl{color:#7a6446}.bkfoot{text-align:center;color:#8a6a46;padding-top:10px;font-size:16px}"
    "@media(max-width:400px){.bktp>summary,.bktxt{padding-left:26px}.bkch>summary i{min-width:18px}}</style>")


# ---------------------------------------------------------------- tip cards: the replay load and the pause after race night
# A new player's first tips teach the game in order; after that they come at random. A message from the team is shown
# once to each player and then retired; a reminder that applies tonight comes before a tip.
TIP_SEQUENCE = [
    "Race night is every night at 8:00 PM Eastern. Enter today and your horse races tomorrow night; the program is posted at 8 PM for the next day.",
    "Nothing in your barn races unless you enter it. Tap the + on a horse's card to enter it.",
    "A horse needs to be fresh to run its best. Rest it, or use a grooming slot to get it back sooner.",
    "Mile time is how fast a horse is expected to trot. Tier is the letter grade that comes with it: D up to S+.",
    "Two yearlings came with your barn, papers paid. Find them on the Training tab; they join your racers at two.",
    "Youngsters are yours to make. The Training tab is their day sheet: jog, train, school or turn out, one job a day.",
    "Your mare is your way up. Buy the Breeder's License on the Breeding tab, and her foals can race for you.",
    "Every horse has a place it likes to race: on the lead, just off it, mid-pack, or coming from behind.",
    "Results are spoiler-free. Watch the replay first, or reveal each result when you're ready.",
    "Claiming races carry a price tag. Any barn can claim a horse in one, so be careful how cheap you go.",
    "The program is up all day. Read the form, check the posts, and see who the handicapper likes.",
    "Post Time Tonic is sold in the Shop. Once a horse is entered, tap its bottle to give it one for the night.",
    "Stakes are the big races of the season. Nominate early: it costs less, and the purses are the richest on the circuit.",
]
TIP_POOL = [
    "A hot pace sets it up for the closers. When two speed horses go at it, the late runners come into it.",
    "The pocket, right behind the leader, is the classic trip. Just don't get boxed in.",
    "First-over is honest, hard work: racing outside with no cover. The horse that follows it gets a free ride.",
    "At tracks with a passing lane, the horse in the pocket can come up the inside of the leader in the stretch.",
    "Half-mile tracks have tight turns. Gate speed and an inside post count for more there.",
    "Manners decide how often a horse gets the trip it wants. A rank horse wastes what it has.",
    "Young horses usually start in the low tiers and climb as they get faster.",
    "A horse that's been claimed from you is gone for good. Its purse still comes to you, though.",
    "The Crown closes the season. The top earners in each division are invited to race for the title.",
    "Some family lines cross better than others. A pedigree scout can tell you how a pairing rates.",
    "Retired mares can join your broodmare band. A colt with a good record can stand at stud.",
    "Foals grow up in your nursery. At two, register one to race and it joins your racing barn.",
    "Every track keeps its own course record. Break one and the whole circuit hears about it.",
    "Bayview Fair doubles its purses during fair week.",
    "The best horse doesn't always win. That's harness racing.",
    "Your Earnings page shows where every dollar came from, and where it went.",
    "A bigger barn means more stalls, more grooming slots and room to breed your own.",
    "The house sells unraced 3-year-olds, sight unseen. Most are ordinary. A few are something special.",
    "Tonics are private. Nobody else knows who's on what.",
    "Check the Compendium under Manage for how the circuit works.",
]


def next_card():
    """The card to show this player now: an unseen team message, else a reminder that applies, else a tip (unless
    hidden). Marks it as seen. (badge, text) or None."""
    p = P()
    seen = p.setdefault("msgs_seen", [])
    msg = next((m for m in G.get("team_msgs", []) if m["id"] not in seen), None)
    if msg:
        seen.append(msg["id"])
        return ("From the barn", msg["text"])
    idle = [h for h in mine() if not h.retired and h.freshness >= 50 and not getattr(h, "order", None) and not on_card(h)]
    if idle:
        return ("Reminder", f"You have {len(idle)} fit horse{'s' if len(idle) != 1 else ''} not entered for tomorrow night. Entries are drawn at 8 PM.")
    if p.get("hide_tips"):
        return None
    i = p.get("tip_i", 0)
    p["tip_i"] = i + 1
    return ("Tip", TIP_SEQUENCE[i] if i < len(TIP_SEQUENCE) else sim.rng.choice(TIP_POOL))


def card_overlay(card, href=None):
    """The full-screen card. Tap anywhere (or wait) to carry on: to href, or just off the screen."""
    badge, text = card
    go = f"location.href='{href}'" if href else "document.getElementById('tipcard').remove();window.CARD_UP=false"
    return ("<div id=tipcard style='position:fixed;inset:0;z-index:10000;display:flex;flex-direction:column;align-items:center;justify-content:center;"
            "gap:18px;padding:24px;background:radial-gradient(ellipse at 50% 30%,#1b2b55 0,#070b18 70%);color:#e8eef4;text-align:center;cursor:pointer;"
            f"font-family:\"Barlow Semi Condensed\",system-ui,sans-serif' onclick=\"{go}\">"
            "<img src=/mock/brand/logo_text.png alt='Trot Dynasty' style='height:min(18vh,110px);width:auto;filter:drop-shadow(0 4px 10px #000a)'>"
            f"<span style='font-weight:800;letter-spacing:.2em;font-size:13px;padding:4px 12px;border:2px solid #e8a33a;color:#e8a33a;text-transform:uppercase'>{esc(badge)}</span>"
            f"<div style='max-width:520px;font-size:clamp(18px,4.6vw,26px);line-height:1.35;font-weight:600'>{esc(text)}</div>"
            "<div style='font-size:13px;color:#8a93a3;letter-spacing:.1em;text-transform:uppercase'>Tap to continue</div></div>"
            f"<script>window.CARD_UP=true;setTimeout(()=>{{if(document.getElementById('tipcard')){{{go}}}}},7000)</script>")


def card_page(nxt):
    """The pause after race night, before Results: a card, then on to where the player was going."""
    nxt = nxt if nxt.startswith("/") and not nxt.startswith("//") else "/results"
    card = next_card()
    if not card:
        return None
    return page("Tip", card_overlay(card, nxt))


LEDGER_NAMES = {"purses": "Purses", "sales": "Horse sales", "stud": "Stud fees", "claims": "Claims", "costs": "Upkeep and fees",
                "barn": "Barn upgrades", "cosmetics": "Emblem and Marquee", "registry": "Foal registration", "shop": "Shop and tonic",
                "stakes": "Stakes nominations", "vet": "Vet", "gifts": "Gifts", "upkeep": "Upkeep", "training": "Training bill", "board": "Farm board"}


def money_k(v):
    """$1.2M, $340k, $900: the short money for chart labels, with a sign when asked for."""
    a = abs(v)
    s = f"${a / 1e6:.1f}M" if a >= 1e6 else f"${a / 1e3:,.0f}k" if a >= 1e3 else f"${a:,.0f}"
    return s


def spark_line(pts, days, w=380, h=150):
    """Cash over time as an SVG line with the figures on it: three gridlines labeled on the left, the low and the high
    marked, and tonight's cash at the end of the line."""
    if len(pts) < 2:
        return "<div class=sub>The graph fills in as race nights go by.</div>"
    L, R, T, B = 48, 14, 16, 20
    lo, hi = min(pts), max(pts)
    span = (hi - lo) or 1
    x = lambda i: L + i * (w - L - R) / (len(pts) - 1)
    y = lambda v: T + (hi - v) * (h - T - B) / span
    xy = [(round(x(i), 1), round(y(v), 1)) for i, v in enumerate(pts)]
    line = " ".join(f"{px},{py}" for px, py in xy)
    grid = "".join(f"<line x1={L} x2={w - R} y1={y(v):.1f} y2={y(v):.1f} stroke='#ffffff22'/>"
                   f"<text x={L - 6} y={y(v) + 4:.1f} text-anchor=end class=ct>{money_k(v)}</text>" for v in (lo, (lo + hi) / 2, hi))
    marks = ""                                                                  # the axis already carries the low and the high
    end = (f"<circle cx={xy[-1][0]} cy={xy[-1][1]} r=4 fill='#ffb347' stroke='#05070d' stroke-width='1.5'/>"
           f"<text x={w - 2} y={xy[-1][1] + 17 if xy[-1][1] < T + 30 else xy[-1][1] - 9:.1f} text-anchor=end class='ct now'>${pts[-1]:,.0f}</text>")
    first = f"wk {days[0] % c.YEAR + 1}" if days[0] // c.YEAR == days[-1] // c.YEAR else f"Y{c.year_of(days[0])} wk {days[0] % c.YEAR + 1}"
    return (f"<svg class='echart tall' viewBox='0 0 {w} {h}'>{grid}<polygon points='{xy[0][0]},{h - B} {line} {xy[-1][0]},{h - B}' fill='#ffb34722'/>"
            f"<polyline points='{line}' fill=none stroke='#ffb347' stroke-width='2.5'/>{marks}{end}"
            f"<text x={L} y={h - 4} class=ct>{first}</text><text x={w - R} y={h - 4} text-anchor=end class=ct>tonight</text></svg>")


def week_bars(weeks, w=380, h=170):
    """Each race night's income (green, up) and costs (red, down) as bars around a zero line, the night's net printed on
    each, the week number under it, and the figures in a tooltip. The last ten nights, so the numbers have room."""
    weeks = weeks[-10:]
    if not weeks:
        return "<div class=sub>The graph fills in as race nights go by.</div>"
    top = max(max(i for i, _, _ in weeks), max(-c_ for _, c_, _ in weeks), 1)
    T, B = 16, 18
    bw, mid, room = w / len(weeks), T + (h - T - B) / 2, (h - T - B) / 2 - 2
    bars = ""
    for k, (i, c_, d) in enumerate(weeks):
        net = i + c_
        x0, bx = k * bw + 2, max(bw - 4, 1)
        up, dn = i * room / top, -c_ * room / top
        bars += (f"<g><title>Week {d % c.YEAR + 1}: income ${i:,.0f}, costs ${-c_:,.0f}, net {'+' if net >= 0 else '−'}${abs(net):,.0f}</title>"
                 f"<rect x={x0:.1f} y={mid - up:.1f} width={bx:.1f} height={up:.1f} fill='#3fb96b'/>"
                 f"<rect x={x0:.1f} y={mid:.1f} width={bx:.1f} height={dn:.1f} fill='#e0704f'/>"
                 f"<text x={x0 + bx / 2:.1f} y={(mid - up - 4) if net >= 0 else (mid + dn + 11):.1f} text-anchor=middle class='ct {'ctw' if net >= 0 else 'ctl'}'>"
                 f"{'+' if net >= 0 else '−'}{money_k(net)}</text>"
                 f"<text x={x0 + bx / 2:.1f} y={h - 4} text-anchor=middle class=ct>{d % c.YEAR + 1}</text></g>")
    tot = lambda n: sum(i + c_ for i, c_, _ in weeks[-n:])
    return (f"<svg class='echart tall' viewBox='0 0 {w} {h}'>{bars}<line x1=0 x2={w} y1={mid:.1f} y2={mid:.1f} stroke='#ffffff40'/></svg>"
            f"<div class=chartax><span>week of the season</span><span>last 7 nights <b class={'won' if tot(7) >= 0 else 'lost'}>{'+' if tot(7) >= 0 else '−'}${abs(tot(7)):,.0f}</b>"
            f" · last 10 <b class={'won' if tot(10) >= 0 else 'lost'}>{'+' if tot(10) >= 0 else '−'}${abs(tot(10)):,.0f}</b></span></div>")


def earnings_page():
    """Earnings as a dashboard: the headline numbers, cash over time, each night's income against its costs, the books
    grouped into income and costs, and what every horse has earned."""
    led = e.ledger.get(ME, {})
    now = {"d": G["day"], "cash": round(e.cash.get(ME, 0)), "led": {k: round(v) for k, v in led.items()}}
    hist = (P().get("hist") or [])[-30:] + [now]
    net = lambda pt: sum(pt["led"].values())
    yr0 = next((pt for pt in reversed(hist) if pt["d"] <= G["day"] - G["day"] % c.YEAR), None)
    prev = hist[-2] if len(hist) > 1 else None
    mine_ = sorted((h for h in G["horses"] if h.owner == ME), key=lambda h: -h.earnings)
    best = mine_[0] if mine_ else None

    def tile(label, val, delta=None, sub=""):
        arrow = ("" if delta is None or not round(delta) else
                 f"<span class={'up' if delta > 0 else 'dn'}>{'&#9650;' if delta > 0 else '&#9660;'} ${abs(delta):,.0f}</span>")
        return f"<div class=etile><span class=etl>{label}</span><b class=money>{val}</b>{arrow}<span class=sub>{sub}</span></div>"
    tiles = ("<div class=etiles>"
             + tile("Cash on hand", f"${now['cash']:,.0f}", now["cash"] - prev["cash"] if prev else None, "vs last week")
             + tile("This season", f"${net(now) - net(yr0):,.0f}" if yr0 else "—", sub="net, since week 1")
             + tile("Career net", f"${net(now):,.0f}", net(now) - net(prev) if prev else None, "vs last week")
             + tile("Best earner", esc(best.name) if best else "—", sub=f"${best.earnings:,.0f} career" if best else "")
             + tile("Weekly bills", f"${sum(e.bills(ME, G['horses'])):,}", sub="training bill + farm board, each race night")
             + "</div>")
    weeks = []
    for a, b in zip(hist, hist[1:]):
        d = {k: b["led"].get(k, 0) - a["led"].get(k, 0) for k in set(a["led"]) | set(b["led"])}
        weeks.append((sum(v for v in d.values() if v > 0), sum(v for v in d.values() if v < 0), b["d"]))
    charts = (f"<div class=card><div class=etl>Cash over time · {min(len(hist), 30)} nights</div>{spark_line([pt['cash'] for pt in hist], [pt['d'] for pt in hist])}</div>"
              "<div class=card><div class=etl>Each night: income <b style=color:#3fb96b>&#9632;</b> and costs <b style=color:#e0704f>&#9632;</b>, net on each bar</div>"
              f"{week_bars(weeks)}</div>")
    line = lambda k, v: (f"<tr><td>{esc(LEDGER_NAMES.get(k, k.title()))}</td>"
                         f"<td class='money {'won' if v > 0 else 'sub'}'>{'+' if v > 0 else '−'}${abs(v):,.0f}</td></tr>")
    inc = sorted(((k, v) for k, v in led.items() if v > 0 and round(v)), key=lambda kv: -kv[1])
    cost = sorted(((k, v) for k, v in led.items() if v < 0 and round(v)), key=lambda kv: kv[1])
    books = ("<div class=card><table class=ebook><tr><th colspan=2>Income</th></tr>" + "".join(line(k, v) for k, v in inc)
             + f"<tr class=esub><td>Total income</td><td class=money>+${sum(v for _, v in inc):,.0f}</td></tr>"
             + "<tr><th colspan=2>Costs</th></tr>" + "".join(line(k, v) for k, v in cost)
             + f"<tr class=esub><td>Total costs</td><td class=money>−${-sum(v for _, v in cost):,.0f}</td></tr>"
             + f"<tr class=enet><td>Net</td><td class=money>${sum(led.values()):,.0f}</td></tr></table></div>") if led else "<p>Nothing booked yet.</p>"
    horses = ("<div class=card><table class=etable><tr><th>Horse</th><th>Starts</th><th>Wins</th><th>Season</th><th>Career</th></tr>"
              + "".join(f"<tr><td><a href='/horse/{urlname(h.name)}'>{esc(h.name)}</a>{' <span class=sub>retired</span>' if h.retired else ''}</td>"
                        f"<td>{h.starts}</td><td>{h.wins}</td><td class=money>${sk.season_earnings(h, G['day']):,.0f}</td>"
                        f"<td class=money>${h.earnings:,.0f}</td></tr>" for h in mine_) + "</table></div>")
    return page("Earnings", tiles + charts + "<div class=secbar>The books</div>" + books + "<div class=secbar>By horse</div>" + horses)


def status_of(h):
    if h in e.nursery:
        return "foal"
    if h not in G["horses"]:
        return "departed"
    return "retired" if h.retired else "racing"


def archive_page(qs):
    """History and search, live: every horse in the stud book (racing, retired, the foals, and the departed still in
    a pedigree or the hall of winners), filtered by name, age, sex, status, owner and tier, sorted any way."""
    name, sex, status, who, tier, barn = (qs.get(k, "") for k in ("q", "sex", "status", "who", "tier", "barn"))
    bname = lambda o: (f"{G['players'][o].get('user', '')} {G['players'][o].get('stable', '')} " if o in G.get("players", {}) else "") + full_name(o)
    amin, amax = int(qs.get("amin") or 0), int(qs.get("amax") or 30)
    sort = qs.get("sort", "earnings")
    pool = c.lineage(G["horses"] + e.nursery + sk.HALL)
    rows = [h for h in pool
            if (not name or name.lower() in h.name.lower()) and (not sex or h.sex == sex)
            and (not status or status_of(h) == status) and (not who or (h.owner == ME) == (who == "mine"))
            and (not tier or tier_label(h) == tier) and amin <= h.age <= amax
            and (not barn or (status_of(h) != "departed" and barn.lower() in bname(h.owner).lower()))]
    barns = sorted({h.owner for h in rows if status_of(h) != "departed"}, key=lambda o: -sum(x.earnings for x in rows if x.owner == o))[:12] if barn else []
    key = {"earnings": lambda h: -h.earnings, "wins": lambda h: -h.wins, "starts": lambda h: -h.starts,
           "best": lambda h: getattr(h, "best", 999), "trophies": lambda h: -len(getattr(h, "trophies", [])),
           "age": lambda h: h.age, "name": lambda h: h.name}[sort if sort in ("earnings", "wins", "starts", "best", "trophies", "age", "name") else "earnings"]
    rows.sort(key=key)
    opt = lambda k, v, label: f"<option value='{v}'{' selected' if qs.get(k, '') == v else ''}>{label}</option>"
    form = ("<form class='card filt' method=get action=/archive>"
            f"<input name=q placeholder='Horse name' value='{esc(name)}'><input name=barn placeholder='Barn or player' value='{esc(barn)}'>"
            f"<select name=sex>{opt('sex', '', 'Any sex')}{opt('sex', 'm', 'Colts & horses')}{opt('sex', 'f', 'Fillies & mares')}</select>"
            f"<select name=status>{opt('status', '', 'Any status')}{opt('status', 'racing', 'Racing')}{opt('status', 'retired', 'Retired')}"
            f"{opt('status', 'foal', 'Foals')}{opt('status', 'departed', 'Departed')}</select>"
            f"<select name=who>{opt('who', '', 'Every barn')}{opt('who', 'mine', 'My horses')}{opt('who', 'others', 'Other barns')}</select>"
            f"<select name=tier>{opt('tier', '', 'Any tier')}" + "".join(opt('tier', t, t) for t in ("S+", "S", "A", "B", "C", "D")) + "</select>"
            f"<span class=ages>Age <input name=amin type=number min=0 max=30 value='{qs.get('amin', '')}' placeholder=0> to "
            f"<input name=amax type=number min=0 max=30 value='{qs.get('amax', '')}' placeholder=30></span>"
            f"<select name=sort>{opt('sort', 'earnings', 'Sort: earnings')}{opt('sort', 'wins', 'Sort: wins')}{opt('sort', 'starts', 'Sort: starts')}"
            f"{opt('sort', 'best', 'Sort: best time')}{opt('sort', 'trophies', 'Sort: trophies')}{opt('sort', 'age', 'Sort: age')}{opt('sort', 'name', 'Sort: name')}</select>"
            "<button>Search</button></form>")
    shown = rows[:200]
    table = "".join(
        f"<tr{brow(h.owner)}><td><a href='/horse/{urlname(h.name)}'>{esc(h.name)}</a>"
        f"<div class=sub>{h.age}yo {sex_word(h)} · {status_of(h)} · {f'<a href=/barn/{h.owner}>' + esc(barn_name(h.owner)) + '</a>' if status_of(h) != 'departed' else 'gone'}</div></td>"
        f"<td>{tier_label(h)}</td><td>{h.starts}-{h.wins}</td><td>{best_time(h)}</td><td>{len(getattr(h, 'trophies', [])) or ''}</td>"
        f"<td class=money>${h.earnings:,.0f}</td></tr>" for h in shown)
    found = ("<div class=card><b>Barns</b><div class=sub>Tap a barn for its live stable.</div><div class=fchips>"
             + "".join(f"<a href=/barn/{o}>{esc(full_name(o))} · {sum(1 for x in rows if x.owner == o)}</a>" for o in barns) + "</div></div>") if barns else ""
    body = (form + found + f"<p class=sub>{len(rows):,} horses match{f' · showing the first 200' if len(rows) > 200 else ''}.</p>"
            "<div class=card><table class=arch><tr><th>Horse</th><th>Tier</th><th>Record</th><th>Best</th><th>🏆</th><th>Earned</th></tr>"
            + (table or "<tr><td colspan=6 class=sub>No horses match.</td></tr>") + "</table></div>")
    return page("History and search", body)


def leaders_page(qs=None):
    """Leaderboards by season: the top horses (and barns, from their horses' purses) for any year on record,
    with your own horses and barn picked out. The current season is the default."""
    qs = qs or {}
    now = c.year_of(G["day"])
    pool = c.lineage(G["horses"] + e.nursery + sk.HALL)
    years = sorted({y for h in pool for y in getattr(h, "seasons", {})} | {now}, reverse=True)
    raced = lambda y: any(getattr(h, "seasons", {}).get(y, [0])[0] for h in G["horses"])
    default = now if raced(now) else now - 1                                  # week 1: show the season just finished
    try:
        yr = int(qs.get("year", default))
    except ValueError:
        yr = default
    row = lambda h: getattr(h, "seasons", {}).get(yr)
    ranked = sorted((h for h in pool if row(h) and row(h)[0]), key=lambda h: -row(h)[4])
    pick = ("<form class='card filt' method=get action=/leaders><label>Season <select name=year onchange='this.form.submit()'>"
            + "".join(f"<option value={y}{' selected' if y == yr else ''}>Year {y}{' (this season)' if y == now else ''}</option>" for y in years)
            + "</select></label><noscript><button>Show</button></noscript></form>")
    top = "".join(
        f"<tr{brow(h.owner)}><td>{i}</td><td><a href='/horse/{urlname(h.name)}'><b>{esc(h.name)}</b></a>"
        f"</td><td class=own>{barn_tag(h.owner, 16)}</td><td>{row(h)[0]}-{row(h)[1]}</td>"
        f"<td>{c.mile_time(row(h)[5]) if row(h)[5] < 999 else '—'}</td><td class=money>${row(h)[4]:,.0f}</td></tr>"
        for i, h in enumerate(ranked[:15], 1))
    mine_ = [(i, h) for i, h in enumerate(ranked, 1) if h.owner == ME]
    yours = "".join(f"<tr{brow(ME)}><td>{i}</td><td><a href='/horse/{urlname(h.name)}'><b>{esc(h.name)}</b></a></td><td>{row(h)[0]}-{row(h)[1]}</td>"
                    f"<td>{c.mile_time(row(h)[5]) if row(h)[5] < 999 else '—'}</td><td class=money>${row(h)[4]:,.0f}</td></tr>" for i, h in mine_)
    barns = {}
    for h in ranked:
        barns[h.owner] = barns.get(h.owner, 0) + row(h)[4]
    border = sorted(barns, key=lambda o: -barns[o])
    best = {}
    for h in ranked:                                                          # ranked by purses: the first seen is the barn's best
        best.setdefault(h.owner, h)
    btab = "".join(f"<tr{brow(o)}><td>{i}</td><td>{barn_tag(o, 22)}{' <span class=pchip>player</span>' if o in G.get('players', {}) else ''}"
                   f"<div class=sub>best: <a href='/horse/{urlname(best[o].name)}'>{esc(best[o].name)}</a></div></td>"
                   f"<td class=money>${barns[o]:,.0f}</td></tr>" for i, o in enumerate(border[:10], 1))
    me_rank = border.index(ME) + 1 if ME in border else None
    oldest = min(years)
    body = (pick + f"<div class=secbar>Top earners · Year {yr}</div><div class=card><table><tr><th>#</th><th>Horse</th><th>Barn</th><th>Record</th><th>Best</th><th>Purses</th></tr>"
            + (top or "<tr><td colspan=6 class=sub>No starts on record for this season.</td></tr>") + "</table></div>"
            + (f"<div class=secbar>Your horses · Year {yr}</div><div class=card><table><tr><th>#</th><th>Horse</th><th>Record</th><th>Best</th><th>Purses</th></tr>{yours}</table></div>" if yours else "")
            + f"<div class=secbar>Top barns by purses · Year {yr}</div><div class=card><table>{btab}</table>"
            + (f"<div class=sub>You're {me_rank} of {len(border)}.</div>" if me_rank and me_rank > 10 else "") + "</div>"
            + f"<p class=sub>Season records are complete from Year {now} on; Year {oldest} to {now - 1} come from the starts each horse still keeps, so older seasons are partial.</p>")
    return page("Leaderboards", body)


def pips(v, h, trait=None):
    """A stat as 1-10 pips on one fixed scale for every horse at every age, so a horse visibly
    fills in as it trains and matures and fades as it ages. A green 2YO lights two or three;
    an average aged horse six. The top is stretched: a 9 is about one bar in a hundred, and a
    full 10 one in a couple of thousand, so a maxed bar is a once-a-generation horse.
    A vague trainer is a pip off."""
    if c.trainer_of(h).quirk == "vague":
        v += (h.id % 3 - 1) * 0.8
    n = 1 + bisect.bisect_right(PIP_STEPS, v)
    return "●" * n + "○" * (10 - n)


# stat value needed for pips 2..10: even steps up to 8, then a long climb to 9 and a cliff to 10
PIP_STEPS = (-3.33, -2.5, -1.67, -0.83, 0.0, 0.83, 1.67, 3.7, 6.0)


def fill(v, h):
    """Bar fill in percent: the pip scale made continuous, so a week of growth or training moves the bar a little
    instead of waiting for the next whole pip."""
    if c.trainer_of(h).quirk == "vague":
        v += (h.id % 3 - 1) * 0.8
    xs, ys = (-4.17,) + PIP_STEPS, range(10, 101, 10)
    if v <= xs[0]:
        raw = max(4.0, 10 + 6 * (v - xs[0]))
    elif v >= xs[-1]:
        raw = 100.0
    else:
        i = bisect.bisect_right(xs, v) - 1
        raw = ys[i] + 10 * (v - xs[i]) / (xs[i + 1] - xs[i])
    return BAR_FLOOR + (100 - BAR_FLOOR) * raw / 100         # lifted: the weakest bar is still a quarter full, so a card never looks empty


BAR_FLOOR = 25   # chosen 2026-10-29 off a side-by-side of real cards: tiers still read, a green 2-year-old no longer looks like another species


def on_bar(trait, v):
    """Where a stat sits on its bar. Speed, Finish and stamina pay all the way up, so they keep the shared scale.
    Manners only buys the trip, and at sim.GAIT_CAP the trip is perfect: that is a full bar, and nothing past it shows."""
    if trait != "gait":
        return v
    lo, top = PIP_STEPS[5], PIP_STEPS[-1]                   # the scale is unchanged up to an ordinary 7 pips...
    if v <= lo:
        return v
    return min(top, lo + (v - lo) * (top - lo) / (sim.GAIT_CAP - lo))   # ...then stretched so the cap lands on the top


def stat_bar(v, h, label=None, width=None, goal=None, trait=None):
    """The same 0-10 scale as pips, as a bar: a track with ten ticks and a fill. Color steps
    from grey (low) through yellow (medium) to green (high); a 9 or 10 is elite and gets an
    iridescent violet-to-cyan fill, a color nothing else in the UI uses. Past the top of the breed it's off the charts:
    a glowing bar and a star."""
    otc = trait is not None and v > sim.SOFT_AT
    v = on_bar(trait, v)
    goal = None if goal is None else on_bar(trait, goal)
    n = pips(v, h).count("●")
    color = ("#5b6270" if n <= 3 else "#d4c13a" if n <= 6 else "#3fb96b" if n <= 8
              else "linear-gradient(90deg,#8b5cf6,#38bdf8 70%,#67e8f9)")
    lab = f"<span class=sub style='width:62px'>{label}</span>" if label else ""
    w = f"width:{width}px;" if width else "flex:1;"
    return (f"<div class=row style='gap:8px'>{lab}<div class='stat{' otc' if otc else ''}' style='{w}' title='{'Off the charts' if otc else f'{n} of 10'}'>"
            f"<i style='width:{fill(v, h):.1f}%;background:{color}'></i>"
            + (f"<u style='left:{fill(goal, h):.1f}%' title='at 2'></u>" if goal is not None else "") + f"</div><b class='sv{' otc' if otc else ''}'>{n}{'★' if otc else ''}</b></div>")



def looks(h):
    """Coat and marking; horses from before this existed get a stable one from their id."""
    coat = getattr(h, "coat", None) or sim.COATS[h.id % len(sim.COATS)]
    marking = getattr(h, "marking", None) or sim.MARKINGS[h.id % len(sim.MARKINGS)]
    return coat, marking


GRADE_COLOR = {"common": "#9d9d9d", "uncommon": "#1eff00", "rare": "#0070dd", "epic": "#a335ee", "legendary": "#ff8000"}
GRADE_LINE = {"common": "An ordinary horse", "uncommon": "A useful horse", "rare": "A good one",
              "epic": "A serious racehorse", "legendary": "One for the big nights"}
TIER_GRADE = {"D": "common", "C": "uncommon", "B": "rare", "A": "epic", "S": "legendary"}


def grade(h):
    """The grade as its owner knows it: a house horse carries the roll the house certified at
    sale; any other horse shows the public tier in the same five colors."""
    return getattr(h, "rarity", None) or TIER_GRADE[h.tier]


def pattern(h):
    """The horse's pattern number: lays out its dapples. Fixed by its id, so it never changes."""
    return getattr(h, "pattern", None) or h.id * 7919 % 1000


def portrait(h, size=96):
    """The painted portrait in the horse's coat, marking and pattern, framed in its grade color.
    The PNG is built once per look by art/recolor.py and served from /portrait."""
    coat, marking = looks(h)
    return (f"<img class=pimg src='/portrait/{urlname(h.name)}.png' width={size} height={size} loading=lazy "
            f"style='border-color:{GRADE_COLOR[grade(h)]}' alt='{coat} {h.sex}, {marking if marking != 'none' else 'no'} marking'>")


def best_time(h):
    best = getattr(h, "best", 999)
    for x in getattr(h, "form", []):                           # older saves: read it off the charts
        t = x.rsplit(" in ", 1)[-1]
        secs = float(t) if ":" not in t else int(t.split(":")[0]) * 60 + float(t.split(":")[1])
        best = min(best, secs)
    return c.mile_time(best) if best < 999 else "—"


def barn_name(o):
    if o == ME:
        return "You"
    return (G.get("players", {}).get(o, {}).get("stable") or f"Barn {o}") if o in G.get("players", {}) else CR.ai_name(o)


def full_name(o):
    """A barn's name as others see it, even your own."""
    return (P(o).get("stable") or f"Barn {o}") if o in G.get("players", {}) else CR.ai_name(o)


def emblem_of(o):
    """The barn's emblem, its rim metal set by its Marquee's Prestige: iron, silver from IV, gold from VII."""
    if o not in G.get("players", {}):
        return {**CR.ai_silks(o), "rim": "iron"}                         # computer barns race in their silks, always
    if not P(o).get("emblem_lic"):
        return {**silks_of(o), "rim": "iron"}
    top = prestige_of(o) if P(o).get("marquee") else 0
    return {**CR.DEFAULT, **(P(o).get("emblem") or {}), "rim": "gold" if top >= 7 else "silver" if top >= 4 else "iron"}


def silks_of(o):
    """A player barn's silks: the ones it picked, or a pattern from its number in its emblem's colors until it picks."""
    em = {**CR.DEFAULT, **(P(o).get("emblem") or {})}
    return P(o).get("silks") or {"pat": EA.PATTERNS[o % len(EA.PATTERNS)], "c1": em["c1"], "c2": em["c2"]}


def barn_earned(o):
    """The trophy devices and titles a player barn has won: kept for good once earned, even after the horse is sold."""
    if o not in G.get("players", {}):
        return set()
    champs = {n for ch in sk.CHAMPIONS.values() for n in ch.values()}
    recs = {st_["horses"][0]["name"] for _, st_ in _record_breakers() if st_["horses"]}
    got = set(P(o).get("earned", ())) | CR.earned([h for h in G["horses"] if h.owner == o], champs, recs, sk.KIND_OF)
    P(o)["earned"] = sorted(got)
    return got


def verified(o):
    """A harness-racing professional, verified by hand by the game's owner: (True, note) or (False, "")."""
    v = P(o).get("verified") if o in G.get("players", {}) else None
    return (v is not None), (v or "")


def seal(o, size=16):
    """The verified seal beside a barn's name, with what it means on hover or tap."""
    ok, note = verified(o)
    tip = "Verified: harness racing professional" + (f" · {note}" if note else "")
    return (f"<img class=vseal src=/mock/brand/emblem/verified.png width={size} height={size} alt='Verified' title='{esc(tip)}'>" if ok else "")


def barn_tag(o, size=18, link=True):
    """Emblem and name (and the verified seal, the Prestige numeral), linked to the barn's page. No title: lists stay short."""
    name = esc(full_name(o)) if o != ME else "<b>You</b>"
    mq = marquee_of(o)
    em = CR.svg(emblem_of(o), 32)                                       # pixel art: 32px, never squeezed
    em = f"<span class=mqe style='{CR.marquee_style(mq)}'>{em}</span>" if mq else em
    inner = (f"{em} {name}{seal(o)}" + (f" <span class=pxchip title='Prestige {CR.NUMERAL[mq['top'] - 1]}'>{CR.NUMERAL[mq['top'] - 1]}</span>" if mq else ""))
    return f"<a class=btag href=/barn/{o}>{inner}</a>" if link else f"<span class=btag>{inner}</span>"


def brow(o):
    """A table row's attributes for a barn's horse: a player barn's row wears its emblem colors across the whole row,
    a Marquee barn's its finish and pattern, moving; yours keeps its highlight class."""
    cls = " class=me" if o == ME else ""
    if o not in G.get("players", {}):
        return cls
    mq, em = marquee_of(o), emblem_of(o)
    if mq:
        bg = f"url(/mock/brand/marquee/v2/{mq['scene'] or 'plate'}.png) center/cover"
        return f" class='mqrow{' me' if o == ME else ''}' style='background:linear-gradient(#05070dc4,#05070dc4),{bg}'"
    return f"{cls} style='background:linear-gradient(90deg,{em['c1']}66,{em['c2']}26 70%,transparent)'"


def barn_public(o):
    """A barn's public page: its emblem and colors, this season's purses, its racing string and its trophy horses."""
    if not any(h.owner == o for h in G["horses"]) and o not in G.get("players", {}):
        return page("Barn", "<p>No such barn.</p>")
    em = {**CR.DEFAULT, **(emblem_of(o) or {})}
    yr = c.year_of(G["day"])
    mine = sorted((h for h in G["horses"] if h.owner == o), key=lambda h: -h.earnings)
    racing = [h for h in mine if not h.retired]
    season = sum(getattr(h, "seasons", {}).get(yr, [0, 0, 0, 0, 0.0])[4] for h in mine)
    rows = "".join(f"<tr><td><a href='/horse/{urlname(h.name)}'><b>{esc(h.name)}</b></a></td><td>{h.age}yo {sex_word(h)}</td><td>{h.tier}</td>"
                   f"<td>{h.starts}-{h.wins}</td><td class=money>${h.earnings:,.0f}</td></tr>" for h in racing[:20])
    stars = [h for h in mine if getattr(h, "trophies", None)]
    t = P(o).get("title") if o in G.get("players", {}) else None
    head = (f"<div class=card style='border-left:6px solid {em['c1']}'><div class=row style='gap:12px;align-items:center'>{CR.svg(em, 64)}"
            f"<div><div class=bname>{esc(full_name(o))}{seal(o, 20)}</div>" + (f"<div class=btitle>{esc(t)}</div>" if t else "")
            + f"<div class=sub>{'Player barn' if o in G.get('players', {}) else 'Computer barn'} · {len(racing)} racing · "
            f"{len(mine) - len(racing)} retired · ${season:,.0f} in purses, Year {yr}</div></div></div>"
            + "</div>")
    body = head + "<div class=secbar>Racing string</div><div class=card><table><tr><th>Horse</th><th></th><th>Tier</th><th>Record</th><th>Earned</th></tr>"         + (rows or "<tr><td colspan=5 class=sub>No horses racing.</td></tr>") + "</table></div>"
    if stars:
        body += "<div class=secbar>Trophy horses</div><div class=card>" + "".join(
            f"<div><a href='/horse/{urlname(h.name)}'><b>{esc(h.name)}</b></a> <span class=sub>{len(h.trophies)} trophies</span></div>" for h in stars[:12]) + "</div>"
    if ME == ADMIN and o in G.get("players", {}):           # the owner's hand-verification control
        ok, note = verified(o)
        body += ("<div class=secbar>Verification (admin)</div><form method=post action=/verify class=card>"
                 f"<input type=hidden name=o value={o}><input name=note maxlength=60 placeholder='Note, e.g. Trainer, Meadowlands' value='{esc(note)}'> "
                 f"<button name=act value=on>{'Update' if ok else 'Verify this barn'}</button>"
                 + (" <button name=act value=off class=sec>Remove</button>" if ok else "") + "</form>")
    return page(full_name(o), body, theme=o)


def crest_page(msg=""):
    """Barn identity: one builder for everything a barn shows the circuit. The Marquee (or the plain bar before it's bought)
    stays pinned at the top and redraws with every pick; tabs below for the emblem, colors, Prestige tier, trophy shelf and
    the name and title. Whatever costs money is listed on the Save button and bought when you save."""
    got = barn_earned(ME)
    owned = set(P().get("owned", ())) | {k for k, (p, _) in CR.SHAPES.items() if p == 0} | {k for k, (p, _) in CR.DEVICES.items() if p == 0}
    em = {**CR.DEFAULT, **(P().get("emblem") or {})}
    mq = marquee_of(ME)
    top = mq["top"] if mq else 1
    metal = lambda t: "gold" if t >= 7 else "silver" if t >= 4 else "iron"
    rim = metal(mq["tier"]) if mq else "iron"

    def tile(name, value, label, thumb, cur, price=0, lock=""):
        return (f"<label class='mqtile{' locked' if lock else ''}'><input type=radio name={name} value={value}{' checked' if cur else ''}"
                f"{f' data-price={price}' if price else ''}{' data-lock=1' if lock else ''} data-label='{esc(label)}'>"
                f"<span class=mqth>{thumb}</span><b>{esc(label)}</b>"
                + (f"<span class=mqlock>&#128274; {esc(lock)}</span>" if lock else f"<span class=sub>${price:,}</span>" if price else "")
                + "</label>")
    img = lambda e_: f"<img class=bthumb src={EA.render({**CR.DEFAULT, **e_}, rim)} width=48 height=48 alt=''>"
    shapes = "".join(tile("shape", k, k.title(), img({**em, "shape": k}), em["shape"] == k, 0 if k in owned else p) for k, (p, _) in CR.SHAPES.items())
    devs = "".join(tile("dev", k, k.title(), img({**em, "dev": k}), em["dev"] == k, 0 if k in owned else p)
                   for k, (p, _) in CR.DEVICES.items() if p is not None)
    trophies = "".join(tile("dev", k, CR.EARNED[k], img({**em, "dev": k}), em["dev"] == k, lock="" if k in got else CR.EARN_HOW[k]) for k in CR.EARNED)
    letters = "".join(f"<label class=lpick><input type=radio name=letter value={L}{' checked' if em.get('letter', 'A') == L else ''}><b>{L}</b></label>"
                      for L in string.ascii_uppercase)
    swatch = lambda n: "".join(f"<label class=sw style='background:{col}'><input type=radio name={n} value='{col}'{' checked' if em[n] == col else ''}></label>"
                               for col in CR.PALETTE)
    lic, sk_ = P().get("emblem_lic"), silks_of(ME)
    pats = "".join(tile("pat", k, k.title(), f"<img class=bthumb src={EA.render_silks({**sk_, 'pat': k})} width=48 height=48 alt=''>", sk_["pat"] == k)
                   for k in EA.PATTERNS)
    sksw = lambda n: "".join(f"<label class=sw style='background:{col}'><input type=radio name=s{n} value='{col}'{' checked' if sk_[n] == col else ''}></label>"
                             for col in CR.PALETTE)
    titles = "<option value=''>(none)</option>" + "".join(f"<option{' selected' if P().get('title') == CR.EARNED[k] else ''}>{CR.EARNED[k]}</option>"
                                                          for k in CR.EARNED if k in got)
    fee = CR.RENAME_FEE if P().get("named") else 0
    # the preview: every tier's Marquee drawn once (only the chosen one shows), or the plain bar before the Marquee is bought
    if mq:
        previews = "".join(marquee_html(ME, tier_look(t, mq["shelf"]), el_id=f"mqt{t}", hidden=t != mq["tier"]) for t in range(1, len(CR.PRESTIGE) + 1))
        rec = barn_record(ME)
        if top < len(CR.PRESTIGE):
            nname, key, n = CR.PRESTIGE[top][:3]
            nxt = (f"Next: <b>{CR.NUMERAL[top]} · {esc(nname)}</b>, {esc(CR.milestone(key, n))}"
                   f"<div class=pbar><i style='width:{min(1, rec.get(key, 0) / n) * 100:.0f}%'></i></div>")
        else:
            nxt = "The top of the ladder. Your barn is a Dynasty."
        tiers = ""
        for t, (name, key, n, scene, *_r) in enumerate(CR.PRESTIGE, 1):
            th = f"<span class=mqsc style='background-image:url(/mock/brand/marquee/v2/{scene or 'plate'}.png)'></span><b class=thnum>{CR.NUMERAL[t - 1]}</b>"
            tiers += tile("tier", t, name, th, t == mq["tier"], lock="" if t <= top else CR.milestone(key, n))
        shelf = "".join(f"<label class='mqtile{'' if k in got else ' locked'}'><input type=checkbox name=shelf value={k}"
                        f" data-src=/mock/brand/trophies/{TROPHY_ART[k]}.png{' checked' if k in mq['shelf'] else ''}{'' if k in got else ' disabled'}>"
                        f"<span class=mqth><img src=/mock/brand/trophies/{TROPHY_ART[k]}.png width=36 height=36 alt=''></span><b>{esc(CR.EARNED[k])}</b>"
                        + ("" if k in got else f"<span class=mqlock>&#128274; {esc(CR.EARN_HOW[k])}</span>") + "</label>" for k in CR.EARNED)
        prestige_pane = (f"<div class=card><div class=pxhd>Prestige {CR.NUMERAL[top - 1]} · {esc(CR.PRESTIGE[top - 1][0])}</div><div class=sub>{nxt}</div></div>"
                         f"<div class=sub>Show any tier you've reached.</div><div class=mqgrid>{tiers}</div>")
        shelf_pane = f"<div class=sub id=mqslots></div><div class=mqgrid>{shelf}</div>"
    else:
        previews = (f"<div class='mqx v2 sc-plain mqpre' id=mqt1 data-slots=0 style='--bg:url(/mock/brand/marquee/v2/plate.png)'>"
                    f"<div class=mqmid><span class='mqped ld-iron'>{CR.svg(emblem_of(ME), 64)}</span>"
                    f"<span class=mqname><span class='mqn np np-iron'>{esc(full_name(ME))}</span></span></div></div>")
        prestige_pane = (f"<div class=card>{marquee_html(ME, tier_look(1))}<div class=sub style='margin-top:8px'>For the elite barns. Your top bar on every "
                         "screen becomes your Marquee, every player sees it beside your name, and your barn page takes on its look. It starts as a "
                         "gilded nameplate and grows through ten tiers of Prestige, each one won on the track. Bought once, yours for good.</div>"
                         f"<button form=mqbuy onclick=\"return ask(this,'Buy the Marquee for ${CR.MARQUEE_FEE:,}?')\" style='margin-top:8px'>"
                         f"Buy the Marquee · ${CR.MARQUEE_FEE:,}</button></div>")
        shelf_pane = "<div class=sub>The trophy shelf comes with the Marquee.</div>"
    grp = lambda title, inner, note="": (f"<fieldset class=bgrp><legend>{title}</legend>"
                                         + (f"<div class=sub>{note}</div>" if note else "") + inner + "</fieldset>")
    silks_pane = (grp("Pattern", f"<div class=mqgrid>{pats}</div>", "Your racing colors, free to change any time.")
                  + grp("Jacket", f"<div class=swr>{sksw('c1')}</div>") + grp("Trim", f"<div class=swr>{sksw('c2')}</div>"))
    license_pane = (f"<div class=card><div class=pxhd>Emblem license</div><div class=sub>Trade your silks for a barn emblem of your own: a frame, "
                    "an icon and your colors, drawn in pixel art and shown everywhere your barn appears. The license opens the builder; "
                    "frames and icons are bought one at a time, and the trophy icons are only ever won.</div>"
                    f"<button form=licbuy onclick=\"return ask(this,'Buy the emblem license for ${CR.EMBLEM_LICENSE:,}?')\" style='margin-top:8px'>"
                    f"Buy the license · ${CR.EMBLEM_LICENSE:,}</button></div>")
    tabs = ([] if lic else [("silks", "Silks", silks_pane)]) + [("emb", "Emblem", license_pane if not lic else grp("Frame", f"<div class=mqgrid>{shapes}</div>")
                              + grp("Icon", f"<div class=mqgrid>{devs}{trophies}</div>"
                                    f"<div id=letters><div class=sub>Your letter: switch any time, free</div><div class=lgrid>{letters}</div></div>",
                                    "Trophy icons (the last six) are earned, never sold."))]
    tabs += ([("col", "Colors", grp("Field", f"<div class=swr>{swatch('c1')}</div>") + grp("Icon", f"<div class=swr>{swatch('c2')}</div>"))] if lic else [])
    tabs += [("pre", "Prestige", prestige_pane), ("shelf", "Shelf", shelf_pane),
            ("name", "Name", f"<div class=sub>Stable name</div><div class=rename><input name=n form=namef maxlength=28 value='{esc(full_name(ME))}'>"
                                     f"<button form=namef{'' if not fee else f' onclick=\"return ask(this,\'Rename for ${fee:,}?\')\"'}>"
                                     f"{'Rename · $' + format(fee, ',') if fee else 'Set name'}</button></div>"
                                     f"<div class=sub style='margin-top:10px'>Title</div><select name=title>{titles}</select>"
                                     "<div class=sub>Titles come with the trophy devices: win your way to them.</div>"
                                     f"<label class=sub style='display:block;margin-top:10px'><input type=checkbox name=theme value=1"
                                     f"{'' if P().get('theme_off') else ' checked'}> Theme my barn page in my Prestige look</label>")]
    live = ("<script>(()=>{const f=document.getElementById('bld'),sv=f.querySelector('[value=save]'),st=document.getElementById('mqstate'),"
            "q=()=>new URLSearchParams(new FormData(f)).toString(),init=q(),"
            "up=e=>{const d=new FormData(f),t=d.get('tier')||1,v=document.getElementById('mqt'+t),k=+v.dataset.slots,"
            "sh=[...f.querySelectorAll('input[name=shelf]:checked')];"
            "if(e&&e.target.name==='shelf'&&sh.length>k){e.target.checked=false;sh.pop()}"
            "f.querySelectorAll('.mqpre').forEach(x=>x.hidden=x!==v);"
            "const s=v.querySelectorAll('.mqshelf'),im=sh.slice(0,k).map(x=>`<img src=${x.dataset.src} alt=''>`);"
            "if(s.length){s[0].innerHTML=im.slice(0,1).join('');s[1].innerHTML=im.slice(1,2).join('');v.querySelector('.mqunder').innerHTML=im.slice(2).join('')}"
            "const sl=document.getElementById('mqslots');if(sl)sl.textContent=k?`This tier shows up to ${k} on its shelf.`:'Shelf slots open at Prestige IV.';"
            "const rim=t>=7?'gold':t>=4?'silver':'iron',p=d.get('pat')?new URLSearchParams({pat:d.get('pat'),c1:d.get('sc1'),c2:d.get('sc2')})"
            ":new URLSearchParams({shape:d.get('shape'),c1:d.get('c1'),c2:d.get('c2'),dev:d.get('dev'),letter:d.get('letter')||'A',rim});"
            "v.querySelector('.mqped .crest').src='/emblem?'+p;"
            "const lt=document.getElementById('letters');if(lt)lt.hidden=d.get('dev')!=='letter';"
            "const buy=[...f.querySelectorAll('input[data-price]:checked')],cost=buy.reduce((a,x)=>a+ +x.dataset.price,0),"
            "lock=f.querySelector('input[data-lock]:checked'),dirty=q()!==init;"
            "sv.disabled=!!lock||!dirty;sv.textContent=cost?'Save · $'+cost.toLocaleString():'Save';"
            "st.textContent=lock?'Preview only: not yours yet':cost?'Buys: '+buy.map(x=>x.dataset.label).join(', '):dirty?'Unsaved changes':'Saved';"
            "window.mqfit&&mqfit()};"
            "f.addEventListener('change',up);f.querySelector('[data-rev]').onclick=()=>{f.reset();up()};"
            "sv.onclick=()=>sv.textContent.includes('$')?ask(sv,'Save and pay '+sv.textContent.split('· ')[1]+'?'):true;"
            "const tb=[...f.querySelectorAll('.mqtabs button')],ink=f.querySelector('.mqink'),"
            "mv=b=>{ink.style.width=b.offsetWidth+'px';ink.style.transform=`translateX(${b.offsetLeft}px)`};"
            "tb.forEach((b,i)=>b.onclick=()=>{const o=tb.findIndex(x=>x.classList.contains('on'));"
            "f.querySelectorAll('.mqtabs button,.mqpane').forEach(x=>x.classList.remove('on','fromL','fromR'));"
            "b.classList.add('on');const p=document.getElementById('mqp-'+b.dataset.t);p.classList.add('on',i<o?'fromL':'fromR');"
            "mv(b);b.scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'})});"
            "requestAnimationFrame(()=>mv(tb[0]));up()})()</script>")
    body = ((f"<div class=card>{msg}</div>" if msg else "")
            + "<form id=namef method=post action=/stablename><input type=hidden name=back value=/crest></form>"
            + "<form id=mqbuy method=post action=/crest><input type=hidden name=marquee value=buy></form>"
            + "<form id=licbuy method=post action=/crest><input type=hidden name=license value=buy></form>"
            + "<form method=post action=/crest class=card id=bld><input type=hidden name=build value=1>"
            + (f"<input type=hidden name=tier value=1>" if not mq else "")
            + f"<div class=mqsticky>{previews}"
            "<div class=mqbar2><span id=mqstate class=sub></span><span><button type=button class=sec data-rev>Revert</button> "
            "<button name=marquee value=save>Save</button></span></div>"
            "<div class='mqtabs slide'>" + "".join(f"<button type=button data-t={k}{' class=on' if i == 0 else ''}>{t}</button>" for i, (k, t, _) in enumerate(tabs))
            + "<i class=mqink></i></div></div>"
            + "".join(f"<div class='mqpane{' on' if i == 0 else ''}' id=mqp-{k}>{b}</div>" for i, (k, _, b) in enumerate(tabs))
            + "</form>" + live)
    return page("Barn identity", body)


def build_save(q):
    """The builder's Save: check every pick, charge for anything new in one go, then apply the emblem, title, theme and Marquee."""
    got = barn_earned(ME)
    owned = set(P().get("owned", ()))
    buys, cost = [], 0
    if not P().get("emblem_lic"):                                       # silks: free, any time
        if q.get("pat") not in EA.PATTERNS or q.get("sc1") not in CR.PALETTE or q.get("sc2") not in CR.PALETTE:
            return "Something in those silks isn't available."
        P()["silks"] = {"pat": q["pat"], "c1": q["sc1"], "c2": q["sc2"]}
    else:
        sh, dv = q.get("shape"), q.get("dev")
        if sh not in CR.SHAPES or dv not in CR.DEVICES or q.get("c1") not in CR.PALETTE or q.get("c2") not in CR.PALETTE:
            return "Something in that emblem isn't available."
        if CR.DEVICES[dv][0] is None and dv not in got:
            return "That trophy device is earned, not bought."
        letter = q.get("letter") if q.get("letter") in list(string.ascii_uppercase) else "A"
        buys = [(k, (CR.SHAPES if kind == "shape" else CR.DEVICES)[k][0]) for kind, k in (("shape", sh), ("dev", dv))
                if (CR.SHAPES if kind == "shape" else CR.DEVICES)[k][0] and k not in owned]
        cost = sum(p for _, p in buys)
        if e.cash.get(ME, 0) < cost:
            return f"Not enough cash: that comes to ${cost:,}."
        if cost:
            e.book(ME, "cosmetics", -cost)
            P()["owned"] = sorted(owned | {k for k, _ in buys})
        P()["emblem"] = {**(P().get("emblem") or {}), "shape": sh, "dev": dv, "c1": q["c1"], "c2": q["c2"], "letter": letter}
    t_ = q.get("title", "")
    if t_ == "" or t_ in {CR.EARNED[k] for k in got}:
        P()["title"] = t_ or None
    P()["theme_off"] = not q.get("theme")
    if P().get("marquee"):
        top = prestige_of(ME)
        t = int(q["tier"]) if str(q.get("tier", "")).isdigit() and 1 <= int(q["tier"]) <= top else P()["marquee"].get("tier", top)
        P()["marquee"] = {"tier": t, "shelf": [k for k in q.get("shelf_all", []) if k in got][:CR.PRESTIGE[t - 1][6]]}
    return "Saved." + (f" Bought: {', '.join(k.title() for k, _ in buys)} (${cost:,})." if buys else "")


MQ_CSS = ("<link rel=stylesheet href=/mock/brand/marquee/marquee.css?v=14>"
          # shrink a long barn name until the whole of it fits its nameplate
          "<script>window.mqfit=()=>document.querySelectorAll('.mqn').forEach(n=>{n.style.fontSize='';let z=parseFloat(getComputedStyle(n).fontSize);while(n.scrollWidth>n.clientWidth&&z>11)n.style.fontSize=(z-=1)+'px'});addEventListener('load',mqfit);addEventListener('resize',mqfit);document.fonts&&document.fonts.ready.then(mqfit)</script>")
TROPHY_ART = {"cup": "cup", "laurel": "horseshoe", "crown": "crown", "clock": "clock", "money": "money", "medal": "medal",
              "plaque": "plaque", "star": "star", "ribbon": "ribbon"}


def prestige_of(o):
    """The highest Prestige tier the barn has reached; kept for good once reached (a sold horse doesn't take it away)."""
    p = P(o)
    if has_pass(o) or o == ADMIN:                                         # tiers are awarded while the pass is held; the record counts regardless
        p["prestige"] = max(p.get("prestige", 1), CR.prestige(barn_record(o)), 10 if o == ADMIN else 0)   # the owner's barn: every tier open
    return p.get("prestige", 1)


def marquee_of(o):
    """A barn's Marquee as shown, or None: the tier it displays (any it has reached) dressed in that tier's look, and its shelf."""
    raw = P(o).get("marquee") if o in G.get("players", {}) else None
    if o == ADMIN and not raw:                                  # the owner's barn has the Marquee without buying it
        raw = P(o)["marquee"] = {"tier": 10, "shelf": []}
    if not raw:
        return None
    top = prestige_of(o)
    t = raw.get("tier") if isinstance(raw.get("tier"), int) and 1 <= raw.get("tier") <= top else top
    name, _, _, scene, frame, shim, slots, fx = CR.PRESTIGE[t - 1]
    return {"tier": t, "top": top, "name": name, "scene": scene, "frame": frame, "shim": shim, "slots": slots, "fx": fx,
            "shelf": [k for k in raw.get("shelf", []) if k in TROPHY_ART][:slots]}


def barn_record(o):
    """What a barn's horses have won: Crown finals, stakes, division titles, course records, career purses."""
    mine_ = [h for h in G["horses"] if h.owner == o]
    names = {h.name for h in mine_}
    t = [x for h in mine_ for x in getattr(h, "trophies", [])]
    recs = {st_["horses"][0]["name"] for _, st_ in _record_breakers() if st_["horses"]}
    return {"crowns": sum("Crown" in x for x in t), "stakes": sum("Crown" not in x for x in t),
            "titles": sum(n in names for ch in sk.CHAMPIONS.values() for n in ch.values()),
            "records": len(names & recs), "career": sum(h.earnings for h in mine_)}


def won_last_night(o):
    """The barn won a race on the most recent race night."""
    days = [st_["day"] for st_ in c.STORIES.values()]
    if not days:
        return None
    last = max(days)
    for st_ in c.STORIES.values():
        if st_["day"] == last and st_["horses"] and (h := find_horse(st_["horses"][0]["name"])) and h.owner == o:
            return last
    return None


MQ_SPARKS = "<i class=sparks><i class=mqsp style='left:14%;top:22%;animation-delay:0s'></i><i class=mqsp style='left:31%;top:70%;animation-delay:1.1s'></i><i class=mqsp style='left:47%;top:18%;animation-delay:2.3s'></i><i class=mqsp style='left:63%;top:62%;animation-delay:0.6s'></i><i class=mqsp style='left:78%;top:28%;animation-delay:1.7s'></i><i class=mqsp style='left:91%;top:68%;animation-delay:2.9s'></i><i class=mqsp style='left:56%;top:40%;animation-delay:3.4s'></i></i>"
MQ_CORNERS = "<i class=corners><b></b><b></b><b></b><b></b></i>"


def marquee_html(o, mq, href=None, boom=False, el_id="", big=False, hidden=False):
    """The Marquee in its Prestige tier's look: the scene (the walnut plate below III), frame, the emblem on a metal ledge at the
    left, the pixel nameplate, one trophy either side and the rest in a shadow-box tray under the name, the tier's numeral.
    The ledge, the name's fill and the emblem's rim are iron, then silver from IV, gold from VII. Stats live on the barn page."""
    t, fx, tag = mq["tier"], mq["fx"], "a" if href else "div"
    metal = "gold" if t >= 7 else "silver" if t >= 4 else "iron"
    em = {**CR.DEFAULT, **(emblem_of(o) or {}), "rim": metal}
    name = esc(full_name(o))
    imgs = [f"<img src=/mock/brand/trophies/{TROPHY_ART[k]}.png alt='' title='{esc(CR.EARNED[k])}'>" for k in mq["shelf"]]
    return (f"<{tag} class='mqx v2 sc-{mq['scene'] or 'plain'} fr-{mq['frame']} {fx}{' mqpre' if el_id else ''}{' mqbig' if big else ''}'"
            f"{f' id={el_id}' if el_id else ''}{f' href={href}' if href else ''}{' hidden' if hidden else ''} data-slots={mq['slots']}"
            f" style='--bg:url(/mock/brand/marquee/v2/{mq['scene'] or 'plate'}.png);--bulb:{CR.BULBS['gold']}'>"
            f"<i class=mqfx></i>{'<i class=mqboom></i>' if boom or 'pt-dynasty' in fx else ''}"
            f"{MQ_SPARKS if 'pt-embers' in fx else ''}{MQ_CORNERS if 'pt-corners' in fx else ''}{'<i class=gems></i>' if 'pt-dynasty' in fx else ''}"
            f"<span class='mqshelf l'>{''.join(imgs[:1])}</span>"
            f"<div class=mqmid><span class='mqped ld-{metal}'>{CR.svg(em, 64)}"
            f"{'<img class=pcrown src=/mock/brand/trophies/crown.png alt=>' if 'pt-crown' in fx else ''}</span>"
            f"<span class=mqname><span class=mqnl><span class='mqn np np-{metal}' data-t='{name}'>{name}</span>{seal(o, 22)}</span><span class=mqunder>{''.join(imgs[2:])}</span></span></div>"
            f"<span class='mqshelf r'>{''.join(imgs[1:2])}</span><b class=pxbadge>{CR.NUMERAL[t - 1]}</b></{tag}>")


def tier_look(t, shelf=()):
    """A Marquee dressed as tier t, for previews."""
    name, _, _, scene, frame, shim, slots, fx = CR.PRESTIGE[t - 1]
    return {"tier": t, "name": name, "scene": scene, "frame": frame, "shim": shim, "slots": slots, "fx": fx, "shelf": list(shelf)[:slots]}


def buy_crest(q):
    """The /crest form: buy a part, use a part, set colors or a title."""
    got = barn_earned(ME)
    owned = set(P().get("owned", ()))
    free = lambda kind, k: (CR.SHAPES if kind == "shape" else CR.DEVICES).get(k, (None,))[0] == 0
    em = P().setdefault("emblem", dict(CR.DEFAULT))
    if q.get("license") == "buy":
        if P().get("emblem_lic"):
            return ""
        if e.cash.get(ME, 0) < CR.EMBLEM_LICENSE:
            return "Not enough cash for the emblem license."
        e.book(ME, "cosmetics", -CR.EMBLEM_LICENSE)
        sk_ = silks_of(ME)
        P()["emblem_lic"] = True
        P()["emblem"] = {**CR.DEFAULT, "c1": sk_["c1"], "c2": sk_["c2"]}           # the new emblem starts in the barn's racing colors
        return "The emblem license is yours: build your emblem below."
    if not P().get("emblem_lic") and q.get("marquee") != "buy" and q.get("marquee") != "save":
        return "Emblems need the emblem license."
    if q.get("marquee") == "buy":
        if P().get("marquee"):
            return ""
        if e.cash.get(ME, 0) < CR.MARQUEE_FEE:
            return "Not enough cash for the Marquee."
        e.book(ME, "cosmetics", -CR.MARQUEE_FEE)
        P()["marquee"] = {"tier": 1, "shelf": []}
        return "The Marquee is yours: Prestige I."
    if q.get("marquee") == "save" and P().get("marquee"):
        top = prestige_of(ME)
        t = int(q["tier"]) if str(q.get("tier", "")).isdigit() and 1 <= int(q["tier"]) <= top else P()["marquee"].get("tier", top)
        P()["marquee"] = {"tier": t, "shelf": [k for k in q.get("shelf_all", []) if k in got][:CR.PRESTIGE[t - 1][6]]}
        return "Marquee saved."
    if q.get("buy"):
        kind, _, k = q["buy"].partition(":")
        price = (CR.SHAPES if kind == "shape" else CR.DEVICES).get(k, (None,))[0]
        if not price or k in owned:
            return "Not for sale."
        if e.cash.get(ME, 0) < price:
            return "Not enough cash."
        e.book(ME, "cosmetics", -price)
        P()["owned"] = sorted(owned | {k})
        em["shape" if kind == "shape" else "dev"] = k
        return f"Bought the {k}."
    if q.get("letter") in string.ascii_uppercase and len(q["letter"]) == 1 and "letter" in owned:
        em["dev"], em["letter"] = "letter", q["letter"]
        return f"Your emblem now carries the {q['letter']}."
    for kind in ("shape", "dev"):
        k = q.get(kind)
        if k and (k in owned or free(kind, k) or (kind == "dev" and k in got)):
            em[kind] = k
    if q.get("colors"):
        for n in ("c1", "c2"):
            if q.get(n) in CR.PALETTE:
                em[n] = q[n]
    if q.get("settitle"):
        t = q.get("title", "")
        if t == "" or t in {CR.EARNED[k] for k in got}:
            P()["title"] = t or None
    return ""


def parent_box(p, role):
    """Sire (blue) or dam (rose): a colored square with the parent's name, a link to it."""
    name = esc(p.name) if p else "Foundation"
    inner = f"<small>{role}</small><b>{name}</b>"
    cls = "pbox sire" if role == "Sire" else "pbox dam"
    return f"<a class='{cls}' href='/horse/{urlname(p.name)}'>{inner}</a>" if p else f"<span class='{cls} none'>{inner}</span>"


def card_header(h, own, price=None):
    """The reference layout: portrait with the tier over it and a retired ribbon; name, one
    line of identity, owned-by / bred-by chips, one primary action."""
    coat, marking = looks(h)
    sexname = sex_word(h)
    ribbon = "<div class='ribbon retired'>RETIRED</div>" if h.retired else ""
    grade_chip = f"<span class=gchip style='background:{GRADE_COLOR[h.rarity]}'>{h.rarity}</span>" if getattr(h, "rarity", None) else ""
    bred = barn_name(h.breeder) if getattr(h, "breeder", None) is not None else "foundation stock"
    if own and not h.retired:
        action = ""                                                        # the entry form is right below; no button needed to scroll to it
    elif own:
        action = "<a class='btn big' href=#breeding>Breeding</a>"
    elif price is not None:
        action = (f"<form method=post action=/buy><input type=hidden name=h value='{esc(h.name)}'>"
                  f"<button class=big onclick=\"return ask(this,'Buy {h.name} for ${price:,.0f}?')\">Buy for ${price:,.0f}</button></form>")
    else:
        action = "<span class='btn big off'>Not for sale</span>"
    return (f"<div class='card hdr'><div class=htop><div class='port t{tier_cls(h)}'><div class=stagelight></div>{portrait(h, 150)}<div class='tier {tier_cls(h)} badge'>{tier_label(h)}</div>{trophy(h)}{ribbon}</div>"
            f"<div class=hr><div class=hname>{esc(h.name)} {grade_chip}</div>"
            f"<div class=hline>{h.age}-year-old {coat} {sexname}, {h.starts} starts, {h.wins} wins</div>"
            f"<div class=hown>{'Owned and bred by ' + esc(bred) if bred == barn_name(h.owner) else f'Owned by {esc(barn_name(h.owner))} · bred by {esc(bred)}'}</div>"
            + (f"<div class=act>{action}</div>" if action else "") + "</div></div>"
            + (f"<div class=hbars>{''.join(stat_bar(h.developed[t], h, k.capitalize(), trait=t, goal=h.ceiling(t, 2) - 2.0 if h in e.nursery else None) for k, t in FOCUS.items())}"
               + ("<div class=sub>White line: where each stat will be at 2</div>" if h in e.nursery else "") + f"{prime_row(h)}</div>")   # every horse's bars are public
            + "</div>")


def stats_block(h, own):
    l5 = sum(getattr(h, "last5", []) or [])
    itm = (h.wins + getattr(h, "places", 0) + getattr(h, "shows", 0)) / h.starts if h.starts else 0
    mark = best_time(h) + (f" ({'half' if getattr(h, 'best_track', 'mile') == 'half' else 'mile'})" if best_time(h) != "—" else "")
    tiles = (f"<div class=tiles><div class=tile><div class=tl>Purses</div><div class=tv>${h.earnings:,.0f}</div><div class=sub>(${l5:,.0f} L5)</div></div>"
             f"<div class=tile><div class=tl>Lifetime mark</div><div class=tv>{mark}</div></div>"
             f"<div class=kv><div><span>Starts</span><b>{h.starts}</b></div><div><span>Wins</span><b>{h.wins}</b></div>"
             f"<div><span>Places</span><b>{getattr(h, 'places', 0)}</b></div><div><span>Shows</span><b>{getattr(h, 'shows', 0)}</b></div>"
             f"<div><span>In the money</span><b>{itm:.3f}</b></div></div></div>")
    if own:
        if h.retired:
            left = c.BREEDING_UNTIL - h.age
            extra = (f"<div class=sub style='margin:8px 0 4px'>Retired · {'standing at stud' if h.sex == 'm' else 'broodmare'}"
                     + (f" · fee ${e.stud_fee(h):,.0f}" if h.sex == "m" else "") + f" · {left} season{'s' if left != 1 else ''} left · at their best:</div>")
        else:
            extra = (f"<div class=row style='margin-top:10px;gap:10px'>{condition(h)}</div>"
                     f"<div class=sub>{tonight(h)}</div>")
        tiles += extra                                                     # the bars and Prime sit in the header box now
    return f"<div class=secbar>Record</div><div class=card>{tiles}</div>"


def prime_row(h):
    """Where the horse likes to sit, as four arrows pointing the way the field runs: the leading arrow
    (right) is the front, the trailing one (left) closes from the back. Its own arrow is lit."""
    st = sim.style_of(h)
    cells = "".join(f"<i class='pa{' on' if k == st else ''}' title='{t}'></i>" for k, t in
                    (("late", "closes late"), ("mid", "mid-pack"), ("stalk", "stalks the pace"), ("front", "wants the lead")))
    return (f"<div class=prime><span class=sub>Preferred Position</span><span class=pstrip>{cells}</span>"
            f"<span class=pnote>{ {'front': 'wants the lead', 'stalk': 'sits just off the pace', 'mid': 'mid-pack, moves after the half', 'late': 'drops out, closes late'}[st] }</span></div>")


def identity_card(h, context="owned", price=None):
    return card_header(h, context == "owned", price) + stats_block(h, context == "owned")


def section(title, inner, open_=False, sid=""):
    return f"<details{' open' if open_ else ''}{' id=' + sid if sid else ''}><summary>{title}</summary>{inner}</details>"


TIER_RGB = {"S": "#b45309", "A": "#1f4fbf", "B": "#1f7a3f", "C": "#6b7280", "D": "#a1a1aa"}


CUP = ("<svg viewBox='0 0 12 12' width=100% height=100% shape-rendering=crispEdges aria-hidden=true>"   # a bold cup, readable at 14px
       "<path fill='#2a1600' d='M2 1h8v1h2v3h-1v1h-1v1H8v2h1v1h1v2H2v-2h1V9h1V7H2V6H1V5H0V2h2zM1 3v1h1V3zm9 0v1h1V3z'/>"
       "<path fill='#fff3c4' d='M3 2h2v3H3z'/></svg>")




# Displayed tiers are absolute, cut from the mile rating, so a tier means the same horse at any age: a promising
# 2-year-old shows C or B until it is fast. (Classes, prices and breeding still use h.tier, the age-relative one.)
MILE_TIERS = tuple((sim.retime(x), t) for x, t in ((107.5, "S+"), (109.5, "S"), (112.0, "A"), (115.0, "B"), (119.0, "C")))
# seconds for a mile, slower is D: the original cuts, moved exactly onto the 2026-10-27 clock (S+ ~1:50.9 ... C ~2:00.1)


def tier_label(h):
    if h.age < 2 or c.age_group(h) not in c.GROUP_STATS:                       # a foal hasn't raced: no rating yet
        return h.tier
    secs = c.mile_secs(c.peak_est(h) if h.retired else h.est)                 # a retired horse keeps the rating of its prime
    return next((t for cut, t in MILE_TIERS if secs <= cut), "D")


def tier_base(h):
    t = tier_label(h)
    return "S" if t == "S+" else t


def tier_cls(h):
    return "Sp" if tier_label(h) == "S+" else tier_base(h)


STABLEMATE = ("<svg class=mate viewBox='0 0 28 28' width=24 height=24 aria-hidden=true>"   # a plain square tile, two black heads
              "<rect x='.5' y='.5' width='27' height='27' fill='#8b95a8' stroke='#05070d'/>"
              "<path transform='translate(4.5 1.5) scale(.95)' fill='#05070d' d='M21 23H8c0-3 .8-5.2 3-6.8L9 14.5l-3.2 1.2L3.5 13.5 6.8 8C8 5.8 10 4 13 3.6l1-2.4 2.2 2.2C19.6 4.6 22 8 22 13z'/>"
              "<path transform='translate(-.5 2.5) scale(.95)' fill='#05070d' stroke='#8b95a8' stroke-width='1.4' d='M21 23H8c0-3 .8-5.2 3-6.8L9 14.5l-3.2 1.2L3.5 13.5 6.8 8C8 5.8 10 4 13 3.6l1-2.4 2.2 2.2C19.6 4.6 22 8 22 13z'/>"
              "</svg>")


def stablemates(h, rname, track, vid=None):
    """Your other horses already entered tonight in the very race this horse would run in (same card: name, track,
    age class and sex), so you can see you'd be racing against yourself."""
    group = "all" if rname in c.ALL_AGES else c.age_group(h)
    sex = "F&M" if h.sex == "f" else "open"
    out = []
    for x in mine():
        o = getattr(x, "order", None)
        if x is h or not (isinstance(o, tuple) and o[0] == "enter" and o[1] == rname and o[4] == track)                 or (vid and len(o) > 5 and o[5] != vid):                  # at another track: a different race
            continue
        if ("all" if rname in c.ALL_AGES else c.age_group(x)) == group and (rname in c.MIXED or ("F&M" if x.sex == "f" else "open") == sex):
            out.append(x)
    return out


def trophy(h, count=True):
    """Top-right corner of any portrait: a gold cup for a horse that has won a trophy race (a stake), with the
    count when it's more than one. The tier always sits bottom-right."""
    won = getattr(h, "trophies", [])
    if not won:
        return ""
    tip = esc("Trophy winner: " + ", ".join(won))
    return f"<span class=troph title='{tip}'>{CUP}{f'<b>{len(won)}</b>' if count and len(won) > 1 else ''}</span>"


def square_portrait(h, size=88):
    """The barn-row portrait: square, in the coat, with the tier as a colored edge."""
    return (f"<div class='sq t{tier_cls(h)}' style='width:{size}px;height:{size}px;border-color:{TIER_RGB[tier_base(h)]}'>"
            f"<img src='/portrait/{urlname(h.name)}.png' width={size} height={size} loading=lazy alt=''><span class='sqt t{tier_cls(h)}' style='background:{TIER_RGB[tier_base(h)]}'>{tier_label(h)}</span>{trophy(h, count=False)}</div>")   # the barn row: just the cup


def weeks_to_stake(h):
    """Weeks until the stake this horse is nominated to, or None."""
    st_ = next((x for x in sk.CALENDAR if h in x.noms and not x.result), None)
    return None if st_ is None else st_.week - G["day"] % c.YEAR


def corner_action(h):
    """The stable card's top-right button. + goes to the race sheet; it stays even with a stake booked weeks ahead.
    A week out from a booked stake it becomes a pause: rest or groom this week so the horse goes in fresh. Entered
    tonight, there's nothing to add."""
    o = getattr(h, "order", None)
    if not h.retired and h.owner == ME and isinstance(o, tuple) and o[0] == "enter":     # entered: the bottle, for a tonic tonight
        on = getattr(h, "tonic", None)
        tip = f"{h.name} is on tonic tonight" if on else f"Give {h.name} a Post Time Tonic"
        ring = dict((k, c_) for k, _, c_, _ in TONICS).get(on) or "#c084fc"
        return (f"<a class='enterplus tonic{' on' if on else ''}' style='--tc2:{ring}' href='/tonic/{urlname(h.name)}' title='{esc(tip)}' aria-label='{esc(tip)}'>"
                f"{bottle(on, 18, empty='#2fae5a')}<i class=tbadge>{'✓' if on else '+'}</i></a>")
    if h.retired or h.owner != ME or o:
        return ""
    href = f"/horse/{urlname(h.name)}?enter=1#enter"
    cr = crown_invite(h)
    if cr and cr[2] == 0:
        return ""
    if weeks_to_stake(h) == 1 or (cr and cr[2] == 1):
        tip = f"{h.name} has a stake next week: rest or groom this week"
        return (f"<a class='enterplus pause' href='{href}' title='{esc(tip)}' aria-label='{esc(tip)}'>"
                "<svg viewBox='0 0 12 12' width=12 height=12 aria-hidden=true><rect x='2' y='1.5' width='3' height='9' fill='currentColor'/>"
                "<rect x='7' y='1.5' width='3' height='9' fill='currentColor'/></svg></a>")
    return f"<a class=enterplus href='{href}' title='Enter {esc(h.name)} in a race' aria-label='Enter {esc(h.name)} in a race'>+</a>"


def horse_card(h, link=True):
    """A barn row: square tier-edged portrait, the name line, four stacked stat bars, status."""
    name = f"<a href='/horse/{urlname(h.name)}'>{esc(h.name)}</a>" if link else esc(h.name)
    bars = "".join(stat_bar(h.developed[t], h, k.capitalize(), trait=t) for k, t in FOCUS.items())
    last = h.form[-1] if getattr(h, "form", None) and isinstance(getattr(h, "last", None), tuple) else (getattr(h, "last", None) or "")
    if h.retired:
        status = f"<div class=sub>Retired, {'at stud' if h.sex == 'm' else 'broodmare'}</div>"
    else:
        groom = ""
        if h.owner == ME and h.freshness < e.GROOMED_TO and e.groom_left(ME, G["day"]) > 0:   # next to the condition it fixes
            groom = (f"<form method=post action=/groom class='inline groombtn'><input type=hidden name=h value='{esc(h.name)}'>"
                     f"<button class=sec title='Uses 1 of {e.groom_left(ME, G['day'])} grooming slots left this week'>Groom</button></form>")
        tn = getattr(h, "tonic", None)
        ton = f"<span class=tline style='--tc2:{dict((k, c_) for k, _, c_, _ in TONICS)[tn] or "#c084fc"}'>{bottle(tn, 13)} {dict((k, l_) for k, l_, *_ in TONICS)[tn]} Tonic</span>" if tn and h.owner == ME else ""
        status = f"<div class=row style='gap:4px 10px;margin-top:4px;flex-wrap:wrap'>{condition(h)}{groom}<span class=sub>{tonight(h)}</span>{ton}</div>"
    enter = corner_action(h)
    return (f"<div class='card brow hc{' sp' if tier_label(h) == 'S+' else ''}' style='--tc:{'#c084fc' if tier_label(h) == 'S+' else TIER_RGB[tier_base(h)]}'>{enter}<div class=pcol>{square_portrait(h)}<div class=besttime><span>Best Time</span><b>{best_time(h)}</b></div></div><div style='flex:1;min-width:0'>"
            f"<div class=bname>{name}</div>"
            f"<div class=facts><span class=chip>{h.age}yo {sex_word(h)}</span>"
            f"<span class=chip title='starts-wins'><b>S{h.starts}-W{h.wins}</b></span><span class='chip cash'>${h.earnings:,.0f}</span>"
            "</div>"
            f"<div class=bbars>{bars}</div>{status}{"" if h.retired else f"<div class='chart starts'><span><b>Last Start:</b> {esc(last.rsplit('; ', 1)[-1]) if last else '—'}</span><span><b>Next Start:</b> {next_start(h)}</span></div>"}</div></div>")


def order_text(h):
    o = h.order
    if isinstance(o, tuple) and o[0] == "enter":
        at = c.VENUE_BY[o[5]]["name"] if len(o) > 5 and o[5] in c.VENUE_BY else f"the {o[4]}"
        return f"{o[1]} at {at}" + (f" (${o[3]:,} tag)" if o[3] else "")
    return o if isinstance(o, str) else " ".join(str(x) for x in o)


def condition(h):
    """Fitness at a glance: a heart that fills with freshness, green when fit to race, amber
    when it would run a little flat, red when it needs the week off. With the word."""
    f = max(0, min(100, h.freshness))
    color, word = ("#3fb96b", "Fit") if f >= 65 else ("#e8a33a", "Fair") if f >= 50 else ("#e0704f", "Tired")
    hid = f"hc{h.id}"
    return (f"<span class=cond title='freshness {f:.0f}'><svg viewBox='0 0 24 24' width='20' height='20' aria-label='{word}'>"
            f"<defs><clipPath id='{hid}'><rect x='0' y='{24 - 24 * f / 100:.1f}' width='24' height='24'/></clipPath></defs>"
            f"<path d='M12 21s-7-4.6-9.3-9A5.3 5.3 0 0 1 12 6.4a5.3 5.3 0 0 1 9.3 5.6C19 16.4 12 21 12 21z' fill='none' stroke='{color}' stroke-width='1.8'/>"
            f"<path d='M12 21s-7-4.6-9.3-9A5.3 5.3 0 0 1 12 6.4a5.3 5.3 0 0 1 9.3 5.6C19 16.4 12 21 12 21z' fill='{color}' clip-path='url(#{hid})'/>"
            f"</svg><b style='color:{color}'>{word}</b></span>")



def groom_form(h):
    """Under fit: offer a grooming slot, or say when they're back. Resting stays free."""
    left, cap = e.groom_left(ME, G["day"]), e.GROOM[e.level[ME]]
    why = "it would race flat tonight" if h.freshness < 50 else "it can race, a little short of its best"
    if left > 0:
        return (f"<div class=row style='gap:10px;margin-top:6px'><form method=post action=/groom class=inline>"
                f"<input type=hidden name=h value='{esc(h.name)}'><button class=sec>Groom to fit</button></form>"
                f"<span class=sub>{why[0].upper() + why[1:]}. Grooming uses 1 of {left} slot{'s' if left != 1 else ''} left this week ({cap} a week at your barn).</span></div>")
    return f"<div class=sub>{why[0].upper() + why[1:]}. No grooming slots left this week; a week off brings it back, and a bigger barn has more slots.</div>"

def crown_line(h):
    """This horse's place in the running for its division's Crown: (stake, rank by season earnings, weeks out), or
    None if its Crown has run or it has no season earnings. The top sk.FIELD are invited on the night."""
    st_ = next((x for x in sk.CALENDAR if x.kind == "final" and not x.result and x.eligible(h)), None)
    if not st_ or sk.season_earnings(h, G["day"]) <= 0:
        return None
    pool = sorted((x for x in G["horses"] if st_.eligible(x) and sk.season_earnings(x, G["day"]) > 0),
                  key=lambda x: -sk.season_earnings(x, G["day"]))
    return st_, pool.index(h) + 1, st_.week - G["day"] % c.YEAR


def crown_invite(h):
    """(stake, rank, weeks) when this horse is currently in line for a Crown invitation."""
    cl = crown_line(h)
    return cl if cl and cl[1] <= sk.FIELD else None


def next_start(h):
    """The horse's next race, short: tonight's entry, else the stake it's nominated to, else nothing yet."""
    if getattr(h, "order", None):
        return f"tonight, {esc(order_text(h))}"
    cr = crown_invite(h)
    stake = next((s for s in sk.CALENDAR if h in s.noms and not s.result), None)
    if cr and (not stake or cr[2] <= stake.week - G["day"] % c.YEAR):
        return f"{esc(cr[0].name)} (invited, #{cr[1]}), " + ("tonight" if cr[2] == 0 else f"in {cr[2]} wk{'s' if cr[2] != 1 else ''}")
    if stake:
        wk = stake.week - G["day"] % c.YEAR
        return f"{esc(stake.name)}, " + ("tonight" if wk == 0 else f"in {wk} wk{'s' if wk != 1 else ''}")
    return "—"


def tonight(h):
    """What this horse is doing at post time, for the barn sheet."""
    o = getattr(h, "order", None)
    if h.retired:
        return "retired"
    if (r := on_card(h)):                                     # on the posted program; maybe entered again for the night after
        return (f"<b>Tonight: {esc(c.race_title(r['key'][0], r['key'][2]))} at {esc(r['v']['name'])}, post {h.post}</b>"
                + (f"<br>Tomorrow: {esc(order_text(h))}" if o else ""))
    if o:
        return f"<b>Tomorrow: {esc(order_text(h))}</b>"
    cr = crown_invite(h)
    if cr and cr[2] == 0:
        return f"<b>Tonight: the {esc(cr[0].name)}</b> <span class=sub>(invited)</span>"
    stake = next((s for s in sk.CALENDAR if h in s.noms and not s.result), None)
    if stake:
        return (f"<b>Tonight: the {esc(stake.name)}</b>" if stake.week == G["day"] % c.YEAR
                else f"nominated: {esc(stake.name)} in {stake.week - G['day'] % c.YEAR} wks" + ("; " if h.freshness >= 50 else "") +
                ("<span style='color:var(--tote)'>not entered tonight</span>" if h.freshness >= 50 else ""))
    if h.freshness < 50:
        return f"not fit to race (fresh {h.freshness:.0f}); trainer's week"
    return "<span style='color:var(--tote)'>not entered</span>"


def trainers_entries(horses, o=None):
    """Fill the sheet with the trainer's picks for every fit, unentered horse. Each stays editable. Never a claimer:
    putting a horse up for a tag is the owner's call alone."""
    o = ME if o is None else o
    n = 0
    for h in horses:
        if h.owner == o and not h.retired and not getattr(h, "order", None) and h.freshness >= 50 and not on_card(h):
            tr = c.trainer_of(h)
            tr.plan(h)                                         # sets h.ship by style
            group, sex, name, purse, tag = c.entry(h)
            if tag:
                continue
            track = getattr(h, "ship", None) or ("mile", "half")[h.id % 2]
            h.order = ("enter", name, purse, tag, track)
            n += 1
    return n


TIER_RANK = {"S+": 0, "S": 1, "A": 2, "B": 3, "C": 4, "D": 5}


# ---------------------------------------------------------------- the news: two running feeds read straight from the
# record (results, race stories, records, the stakes book), so they need nothing saved of their own
def _wk(day):
    return f"Yr {c.year_of(day)} · Wk {day % c.YEAR + 1}"


def _record_breakers():
    """Every race that beat the course record it went in against: (day, story)."""
    return [(st_["day"], st_) for st_ in c.STORIES.values()
            if st_.get("records") and st_["quarters"][-1] < st_["records"][3]]


def notable(h):
    """Worth a line on the wire: a proven earner or a stakes winner."""
    return h.earnings >= 250_000 or bool(getattr(h, "trophies", None))


def wire_tick(day, world_before):
    """Log the night's notable sales, claims and retirements: the moves the record doesn't keep with a date."""
    wire = G.setdefault("wire", [])
    for h in G["horses"]:
        was = world_before.get(h.id)
        if not was or not notable(h):
            continue
        owner, retired = was
        tag = f"{h.name} ({h.age}yo {sex_word(h)}, ${h.earnings:,.0f} earned)"
        if h.retired and not retired:
            wire.append((day, "retire", f"{tag} retires from racing" + (" to stand at stud" if h.sex == "m" else " to the broodmare band"), None))
        elif h.owner != owner and h.owner != -1:
            how = getattr(h, "gone", "") or "changes hands"
            wire.append((day, "sale", f"{tag} {how.lower() if how.startswith('CLAIMED') else how}, from {barn_name(owner)} to {barn_name(h.owner)}", None))
    del wire[:-300]


def win_streaks():
    """Horses on a run of 3+ wins, and runs of 3+ that just ended (with who beat them)."""
    items = []
    for h in G["horses"]:
        rs = getattr(h, "results", [])
        if not rs:
            continue
        n = 0
        for r in reversed(rs):
            if r["place"] != 1:
                break
            n += 1
        if n >= 3:
            items.append((rs[-1]["day"], "streak", f"{h.name} makes it {n} wins in a row, the latest in the {rs[-1]['race']}", rs[-1].get("race_id")))
        elif n == 0 and len(rs) >= 4:
            m = 0
            for r in reversed(rs[:-1]):
                if r["place"] != 1:
                    break
                m += 1
            if m >= 3:
                st_ = c.STORIES.get(rs[-1].get("race_id"), {})
                by = f", beaten by {st_['horses'][0]['name']}" if st_.get("horses") else ""
                items.append((rs[-1]["day"], "streak", f"{h.name}{"'" if h.name.endswith("s") else "'s"} {m}-race win streak ends in the {rs[-1]['race']}{by}", rs[-1].get("race_id")))
    return items


def rivalries():
    """Pairs that have run 1-2 against each other three times or more in the races on record."""
    meets = {}
    for st_ in c.STORIES.values():
        if len(st_["horses"]) > 1:
            a, b = st_["horses"][0]["name"], st_["horses"][1]["name"]
            meets.setdefault(tuple(sorted((a, b))), []).append((st_["day"], a, st_["id"]))
    items = []
    for (a, b), ms in meets.items():
        if len(ms) >= 3:
            ms.sort()
            wa = sum(1 for m in ms if m[1] == a); lead, trail = (a, b) if wa >= len(ms) - wa else (b, a)
            score = f"{max(wa, len(ms) - wa)}-{min(wa, len(ms) - wa)}"
            items.append((ms[-1][0], "rival", f"Rivalry: {a} and {b} have run one-two {len(ms)} times; "
                          + (f"{lead} leads {score}" if score[0] != score[-1] else f"all square at {score}"), ms[-1][2]))
    return items


def earnings_milestones():
    """Career earnings crossing each million (or $500k for the first), dated by the start that crossed it."""
    items = []
    for h in G["horses"]:
        total = h.earnings
        for r in reversed(getattr(h, "results", [])):
            prev = total - r["won"]
            marks = [500_000] + [m * 1_000_000 for m in range(1, 50)]
            crossed = [m for m in marks if prev < m <= total]
            if crossed:
                items.append((r["day"], "earner", f"{h.name} passes ${crossed[-1]:,.0f} in career earnings with the {r['race']}", r.get("race_id")))
                break
            total = prev
    return items


def barn_news(limit=30):
    """Your barn's week by week: wins and placings (with the replay), purses, trophies and records."""
    items = []
    names = {h.name for h in mine()}
    for h in mine():
        for r in getattr(h, "results", []):
            rid = r.get("race_id")
            watch = rid if rid in c.STORIES else None
            if r["place"] == 1:
                items.append((r["day"], "win", f"{h.name} won the {r['race']} in {c.mile_time(r['time'])}, earning ${r['won']:,.0f}", watch))
            elif r["place"] <= 3:
                items.append((r["day"], "place", f"{h.name} ran {['', '', '2nd', '3rd'][r['place']]} in the {r['race']} (${r['won']:,.0f})", watch))
        for t in getattr(h, "trophies", [])[-3:]:
            items.append((None, "trophy", f"{h.name} holds the {t} trophy", None))
    for day, st_ in _record_breakers():
        w = st_["horses"][0]["name"]
        if w in names:
            items.append((day, "record", f"Course record! {w} set a new {st_['track']}-track mark of {c.mile_time(st_['quarters'][-1])}", st_["id"]))
    items = [i for i in items if i[0] is None or i[0] <= P().get("seen", G["day"])]   # no spoilers: a night shows once its Results page was opened
    for f in e.nursery:                                                       # a yearling's stage opening: yours already, nothing to spoil
        for d, s in (getattr(f, "stage_days", []) if f.owner == ME else []):
            items.append((d, "note", f"{f.name} is broke to harness. Jogging is open." if s == "jog"
                          else f"{f.name} has its jogging in. Training miles and a focus are open.", None))
    items += [(G["day"] - 1, "note", x, None) for x in P()["events"] if " for $" not in x]
    items.sort(key=lambda i: -(i[0] if i[0] is not None else -1))
    return items[:limit]


def world_news(limit=50):
    """Around the circuit: stakes winners, the night's richest races, upsets, course records and the year's champions."""
    items, by_day = [], {}
    for st_ in c.STORIES.values():
        by_day.setdefault(st_["day"], []).append(st_)
    for day, races in by_day.items():
        for st_ in races:
            w = st_["horses"][0]
            if "-stake-" in st_["id"]:
                items.append((day, "stake", f"{w['name']} wins the {st_['name']}{' at ' + st_['venue'] if st_.get('venue') else ''} (${st_['purse']:,}) in {c.mile_time(w['time'])}", st_["id"]))
            else:
                odds = w.get("odds", "")
                if odds and int(odds.split("-")[0]) >= 15 * int(odds.split("-")[1]):
                    items.append((day, "upset", f"Upset! {w['name']} wins the {st_['name']} at {odds}", st_["id"]))
        top = max((r for r in races if "-stake-" not in r["id"]), key=lambda r: r["purse"], default=None)
        if top:
            at = f" at {top['venue']}" if top.get("venue") else ""
            items.append((day, "feature", f"Feature: {top['horses'][0]['name']} takes the {top['name']}{at} (${top['purse']:,}) by "
                                          f"{top['horses'][1]['behind'][6]:.1f} lengths" if len(top["horses"]) > 1 else f"Feature: {top['horses'][0]['name']} takes the {top['name']}", top["id"]))
    for day, st_ in _record_breakers():
        old = c.mile_time(st_["records"][3])
        items.append((day, "record", f"Course record! {st_['horses'][0]['name']} stops the clock in {c.mile_time(st_['quarters'][-1])} at {st_.get('venue') or 'the ' + st_['track'] + ' track'} (old mark {old})", st_["id"]))
    items += win_streaks() + rivalries() + earnings_milestones() + list(G.get("wire", []))
    for yr, champs in sk.CHAMPIONS.items():
        if yr >= c.year_of(G["day"]) - 1:
            day = c.EPOCH[0] + (yr + 1) * c.YEAR - 1
            for div, name in champs.items():
                items.append((day, "champ", f"{name} is crowned Year {yr} {div} champion", None))
    items.sort(key=lambda i: -i[0])
    return items[:limit]


NEWS_TAG = {"win": ("WIN", "var(--win)"), "place": ("PLACED", "#5b8def"), "trophy": ("TROPHY", "#d4af37"), "record": ("RECORD", "#e8574a"),
            "note": ("BARN", "var(--ink3)"), "stake": ("STAKES", "#d4af37"), "upset": ("UPSET", "#c05ce0"), "feature": ("FEATURE", "var(--tote)"),
            "champ": ("CHAMPION", "#d4af37"), "streak": ("STREAK", "#2fb5a0"), "rival": ("RIVALRY", "#e0704f"),
            "earner": ("MILESTONE", "#3fb96b"), "retire": ("RETIRES", "#8a94a6"), "sale": ("SALE", "#5b8def")}


def news_list(items, empty):
    if not items:
        return f"<p class=sub>{empty}</p>"
    rows = []
    for day, kind, text, rid in items:
        tag, col = NEWS_TAG[kind]
        watch = f"<a class=nwatch href='/replay/{rid}'>Watch</a>" if rid else ""
        rows.append(f"<div class=news><div class=nmeta><span class=ntag style='background:{col}'>{tag}</span>"
                    f"<span class=sub>{_wk(day) if day is not None else ''}</span>{watch}</div><div>{esc(text)}</div></div>")
    return "".join(rows)


def stall_tone(n, cap):
    """Plenty of room (green), running out (yellow, past 3/4), almost full (red, past 7/8): 30 and 35 of 40 stalls."""
    return "st-red" if n > cap * 7 / 8 else "st-yel" if n > cap * 3 / 4 else "st-grn"


assert stall_tone(7, 40) == "st-grn" and stall_tone(31, 40) == "st-yel" and stall_tone(36, 40) == "st-red"


def barn_page(qs=None):
    # race results live on Results; the barn keeps only notices about the barn itself (retirements, the new year)
    qs = qs or {}
    if qs.get("sort") in ("age", "class"):
        P()["barn_sort"] = qs["sort"]                                            # remembered: the barn opens the way you last sorted it
    by = P().get("barn_sort", "class")
    ev = "".join(f"<div class=ev>{esc(x)}</div>" for x in P()["events"] if " for $" not in x)
    racers = [h for h in mine() if not h.retired]
    rated = lambda h: c.mile_secs(h.est)                                     # fastest first
    racers.sort(key=(lambda h: (h.age, TIER_RANK[tier_label(h)], rated(h))) if by == "age" else (lambda h: (TIER_RANK[tier_label(h)], rated(h))))
    toggle = ("<div class=sortby><span>Sort by</span>"
              + "".join(f"<a href='/?sort={k}' class='{'on' if by == k else ''}'>{label}</a>" for k, label in (("age", "Age"), ("class", "Class"))) + "</div>")
    tb, fb = e.bills(ME, G["horses"])
    cards = (f"<div class=billrow><span>Training bill <b>${tb:,}</b>/wk</span><span>Farm board <b>${fb:,}</b>/wk</span>"
             f"<a href=/earnings>Books ›</a></div>")
    if not e.can_breed(ME) and any(h.retired and h.sex == "f" for h in mine()):   # the way up, until the barn can breed
        lv = e.level.get(ME, 0)
        shed = next(i for i, L in enumerate(e.LEVELS) if L[2])
        cost = sum(e.LEVELS[i][3] for i in range(lv + 1, shed + 1))
        cards += (f"<div class='billrow wayup'><span>Your mare is your way up: the <b>Breeder's License</b> lets her foals race for you.</span>"
                  f"<a href=/studs>${cost:,} to get it ›</a></div>")
    cards += (
             f"<div class=stablehead><h2>Stable <span class='stallct {stall_tone(len(racers), e.stalls(ME))}'>{len(racers)}/{e.stalls(ME)}</span></h2>{toggle}</div>"
             + ("".join(horse_card(h) for h in racers) or "<p class=sub>No racers. Try the market.</p>"))
    view = qs.get("view", "stable")
    menu = ("<div class=hmenu>" + "".join(f"<a href='/?view={k}' class='{'on' if view == k else ''}'>{label}</a>"
                                          for k, label in (("stable", "Stable"), ("barn", "Barn news"), ("world", "Around the track"), ("drivers", "Drivers"))) + "</div>")
    if view == "drivers":
        return page("Your barn", menu + drivers_view())
    if view == "barn":
        return page("Your barn", menu + news_list(barn_news(), "Nothing yet: your horses' wins, placings and trophies will show here."))
    if view == "world":
        return page("Your barn", menu + news_list(world_news(), "The racing world is quiet."))
    wipe = ("<p class=sub><form method=post action=/newgame class=inline>"
            "<button class=warn onclick=\"return ask(this,'Start over? This wipes the world for every player.')\">New game</button></form></p>") if ME == ADMIN else ""
    owe = e.owed.get(ME, 0)
    owe = (f"<div class='card ev' style='border-color:var(--loss)'><b>Training bill overdue: ${owe:,.0f}</b><div class=sub>Your trainer's "
           "day rate and the farm's board ran past your cash. It comes out of your next purses. Selling or retiring a horse that isn't "
           "earning brings the bill down.</div></div>" if owe else "")
    return page("Your barn", menu + owe + race_banner() + train_banner() + ev + cards + wipe)   # the entry box is off the barn page for now; entries are on /entries


def entries_page(qs=None):
    """The race finder: every track's slate, filtered by track, kind of race and purse, with your horses that can
    run in each and an Enter for each. The trainer's picks are one tap at the top; tonight's plan is at the bottom."""
    qs = qs or {}
    vid, kind, floor = qs.get("v", "all"), qs.get("k", "all"), int(qs.get("min", "0") or 0)
    racers = [h for h in mine() if not h.retired]
    open_ = sum(1 for h in racers if not getattr(h, "order", None) and h.freshness >= 50)
    head = (f"<div class=card><b>{open_} fit horse{'s' if open_ != 1 else ''} not entered for tomorrow night.</b> Find a race below, "
            "or let the trainer enter them and change any you like. Entries are drawn into tomorrow's card at 8 PM."
            "<form method=post action=/entries style='margin-top:10px'><button class=big>Take the trainer's entries</button></form></div>"
            if open_ else "<div class=card>Every fit horse is entered for tomorrow night.</div>")
    link = lambda **kw: "/entries?" + "&".join(f"{k}={v}" for k, v in {"v": vid, "k": kind, "min": floor, **kw}.items())
    chips = lambda items, cur, key: "<div class=fchips>" + "".join(
        f"<a href='{link(**{key: k})}' class='{'on' if str(cur) == str(k) else ''}'>{label}</a>" for k, label in items) + "</div>"
    head += chips([("all", "All tracks")] + [(v["id"], v["name"]) for v in c.VENUES], vid, "v")
    head += chips([("all", "All races"), ("cond", "Conditions"), ("clm", "Claimers"), ("young", "2 & 3-year-olds"), ("top", "Open & up")], kind, "k")
    head += chips([(0, "Any purse"), (15000, "$15k+"), (30000, "$30k+"), (45000, "$45k+")], floor, "min")
    if vid in c.VENUE_BY:
        v = c.VENUE_BY[vid]
        wk = G["day"] % c.YEAR + 1
        fair = (f" <b class=fairnow>Fair week: purses doubled</b>" if v.get("fair") and v["fair"][0] <= wk < v["fair"][1]
                else f" <span class=sub>Fair week: weeks {v['fair'][0]}-{v['fair'][1] - 1}</span>" if v.get("fair") else "")
        head += (f"<div class='card venue'><b>{esc(v['name'])}</b> <span class=sub>{'mile' if v['track'] == 'mile' else 'half-mile'} · purses "
                 f"{'+' if v['purse'] >= 1 else ''}{(v['purse'] - 1) * 100:.0f}%</span>{' <b class=plane>Passing lane</b>' if v.get('passing') else ''}{fair}<div class=sub>{esc(v['about'])}</div></div>")
    purses = {n: p for n, _, p, _ in c.CONDITIONS} | {c.clm_name(t): p for t, _, p in c.CLAIMERS}
    tags = {c.clm_name(t): t for t, _, _ in c.CLAIMERS}
    can = {}                                                    # (track id, class) -> your horses that can go
    for h in racers:
        for v, rname, purse, vpurse, tag, track in c.offerings(h):
            can.setdefault((v["id"], rname), []).append((h, purse, tag, track))
    def keep(name):
        clm, young, top = name.startswith("CLM"), name[:3] in ("2YO", "3YO"), name in ("Open", "Aged Open", "Preferred", "Invitational") + c.WINNERS_OVER
        return {"all": True, "cond": not clm and not top, "clm": clm, "young": young, "top": top}.get(kind, True)
    claim_ask = lambda h, tag: (f"onclick=\"return ask(this,'Enter {esc(h.name)} for a ${tag:,} tag? Any barn can take it for the tag.')\""
                                if tag else "")
    rows, folds = [], []
    for v in c.VENUES:
        if vid != "all" and v["id"] != vid:
            continue
        mark = len(rows)
        for name in v["slate"]:
            pay = c.venue_purse(v, purses[name])
            if not keep(name) or pay < floor:
                continue
            who = can.get((v["id"], name), [])
            title = f"Claiming ${name[3:]} · by age" if name.startswith("CLM") else name   # your horses race in their own age's card
            def chip(h, purse, tag, track):
                """Each of your horses that can run here: entered HERE (green), entered elsewhere (says where; the
                button moves it), or free (the button enters it)."""
                o = getattr(h, "order", None)
                o = o if isinstance(o, tuple) and o[0] == "enter" else None
                if o and o[1] == name and len(o) > 5 and o[5] == v["id"]:
                    return f"<span class='fh here'>✓ <b>{esc(h.name)}</b> entered here</span>"
                where = (c.VENUE_BY[o[5]]["name"] if o and len(o) > 5 and o[5] in c.VENUE_BY else "another race") if o else ""
                return (f"<form method=post action=/enter class='inline fh'><input type=hidden name=h value='{esc(h.name)}'>"
                        f"<input type=hidden name=r value='{name}|{purse}|{tag}|{track}|{v['id']}'>"
                        f"<button class=sec {claim_ask(h, tag)}>{'Move' if o else 'Enter'} <b>{esc(h.name)}</b></button>"
                        + (f"<span class=elsewhere>entered at {esc(where)}</span>" if o else "") + "</form>")
            horses = "".join(chip(*x) for x in who)
            rows.append(f"<div class='card race'><div class=rhead><b>{esc(title)}</b><span class=money>${pay:,}</span></div>"
                        f"<div class=sub>{esc(v['name'])} · {'mile' if v['track'] == 'mile' else 'half-mile'}"
                        + (f" · claiming ${tags[name]:,}" if name in tags else "") + "</div>"
                        + (f"<div class=fhs>{horses}</div>" if who else "<div class=sub>None of yours qualifies.</div>") + "</div>")
        mine_here = sum(1 for r in rows[mark:] if "fhs" in r)
        if len(rows) > mark:                                    # all tracks: one fold per track, its races inside
            folds.append(f"<details class=vfold><summary><span class=vname>{esc(v['name'])}</span><span class=vmeta>"
                         f"{'mile' if v['track'] == 'mile' else 'half-mile'}{' · passing lane' if v.get('passing') else ''} · {len(rows) - mark} races · {mine_here} for your horses</span></summary>"
                         f"<div style='padding:0 8px'>{''.join(rows[mark:])}</div></details>")
    body = "".join(folds) if vid == "all" else "".join(rows)
    finder = (f"<div class=secbar>Races · {len(rows)}</div>" + (body or "<p class=sub>No races match.</p>"))
    return page("Find a race", head + finder)


def entry_rows(racers):
    """One line a racer: what it's doing tomorrow night, Enter or Change (the horse page picks the race), and Scratch."""
    return "".join(f"<div class='erow2'><div style='flex:1;min-width:0'><a href='/horse/{urlname(h.name)}'><b>{esc(h.name)}</b></a> <span class=sub>{h.age}yo {sex_word(h)} · {tier_label(h)}</span><div class=sub>{tonight(h)}</div></div>"
                   f"<span class=row style='gap:6px'><a class='btn sec' href='/horse/{urlname(h.name)}'>{'Change' if getattr(h, 'order', None) else 'Enter'}</a>"
                   + (f"<form method=post action=/scratch class=inline><input type=hidden name=h value='{esc(h.name)}'><button class=sec>Scratch</button></form>" if getattr(h, "order", None) and not on_card(h) else "") + "</span></div>" for h in racers)


def entry_box():
    """The Barn tab's entry box: every racer's entry for tomorrow night, the trainer's picks in one tap, and the race finder."""
    racers = [h for h in mine() if not h.retired]
    if not racers or entries_closed():
        return ""
    open_ = sum(1 for h in racers if not getattr(h, "order", None) and h.freshness >= 50 and not on_card(h))
    acts = ("<div class=mact>" + (f"<form method=post action=/entries class=inline style='flex:1'><input type=hidden name=back value=/><button class=sec style='width:100%'>Trainer's picks</button></form>" if open_ else "")
            + ("<a class='btn sec' href=/setup>Set up tonight</a>" if has_pass(ME) else "") + "<a class='btn sec' href=/entries>Find a race</a></div>"
            + ("<div class=sub>Your manager enters the trainer's picks every night, and works the standing orders, on nights you're away.</div>" if has_pass(ME) else ""))
    return (f"<div class='card hc mgr' id=entrybox style='--tc:#c9922e'><div class=mhead><b>Entry box</b><span class='pchip{' lit' if open_ else ''}'>{open_} to enter</span></div>"
            "<div class=sub>Tomorrow night's entries, drawn into the card at 8 PM. Change or scratch any until then.</div>"
            f"<div class=mgrid>{entry_rows(racers)}</div>{acts}</div>")


def unseen_night():
    """A race night of yours you haven't opened on Results yet."""
    return any(r["day"] > P().get("seen", G["day"]) for h in mine() for r in getattr(h, "results", []))


def mutuels(st_):
    """$2 payouts from the final odds, the way a results chart prints them: win, place and show for the first three,
    and the exacta and trifecta. Place and show pools pay a share of the win price; the exotics multiply the
    prices of the horses in them, with the takeout. Rounded down to the dime, never under $2.10."""
    top = sorted(st_["horses"], key=lambda r: r["place"])[:3]
    def price(r):
        a, _, b = (r.get("odds") or "").partition("-")
        return int(a) / int(b) if a.isdigit() and b.isdigit() and int(b) else None
    p = [price(r) for r in top]
    if len(top) < 3 or None in p:
        return ""
    pay = lambda x: f"${max(2.10, int(x * 10) / 10):,.2f}"
    win = 2 * (p[0] + 1)
    plc = [2 + p[0] * .9, 2 + p[1] * .9]                            # a place ticket shares its pool between two horses
    shw = [2 + p[0] * .55, 2 + p[1] * .55, 2 + p[2] * .55]          # and a show ticket among three
    ex, tri = 2 * (p[0] + 1) * (p[1] + 1) * .8, 2 * (p[0] + 1) * (p[1] + 1) * (p[2] + 1) * .75
    row = lambda r, cells: (f"<div class=murow><span class=pad style='background:var(--p{r['post']});color:{'#111' if r['post'] in (3, 6, 8, 10, 11) else '#fff'}'>{r['post']}</span>"
                            f"<b class=mun>{esc(r['name'])}</b>" + "".join(f"<span class=muv>{x}</span>" for x in cells) + "</div>")
    return ("<div class=mut><div class=muh><span>$2 Mutuels</span><span class=muv>Win</span><span class=muv>Place</span><span class=muv>Show</span></div>"
            + row(top[0], [pay(win), pay(plc[0]), pay(shw[0])]) + row(top[1], ["", pay(plc[1]), pay(shw[1])]) + row(top[2], ["", "", pay(shw[2])])
            + f"<div class=muex><span>$2 Exacta {top[0]['post']}-{top[1]['post']}</span><b>{pay(ex)}</b></div>"
            + f"<div class=muex><span>$2 Trifecta {top[0]['post']}-{top[1]['post']}-{top[2]['post']}</span><b>{pay(tri)}</b></div></div>")


def full_order(rid, mine_name=""):
    """The whole field in finishing order, as a hidden pop-up for Results (shown by fullOrder, closed with a tap)."""
    st_ = c.STORIES[rid]
    nth = lambda p: f"{p}{'th' if 10 <= p % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(p % 10, 'th')}"
    def margin(r):
        b = r["behind"][6]
        if r["place"] == 1:
            return "won"
        w, f = int(b), b - int(b)
        frac = min((("", 0), ("¼", .25), ("½", .5), ("¾", .75), ("", 1)), key=lambda x: abs(x[1] - f))
        w += 1 if frac[1] == 1 else 0
        return f"{w or ''}{frac[0]}" if (w or frac[0]) else "nose"
    rows = "".join(
        f"<div class='forow{' fome' if r['name'] == mine_name else ''}'><b class=fopl>{nth(r['place'])}</b>"
        f"<span class=pad style='background:var(--p{r['post']});color:{'#111' if r['post'] in (3, 6, 8, 10, 11) else '#fff'}'>{r['post']}</span>"
        f"<span class=fon><b>{esc(r['name'])}</b>{('<small>' + esc(r['driver']) + '</small>') if r.get('driver') else ''}</span>"
        f"<span class=foo>{esc(r.get('odds', ''))}</span><span class=fom>{margin(r)}</span></div>"
        for r in sorted(st_["horses"], key=lambda r: r["place"]))
    return (f"<div class=fullorder id='fo-{esc(rid)}' onclick=\"this.style.display='none'\"><div class=fobox>"
            f"<div class=foh><b>{esc(st_['name'])}</b><span>{esc(st_.get('venue', ''))} · {c.mile_time(st_['final'])}</span></div>"
            f"<div class='forow fohead'><b class=fopl></b><span class=pad style='visibility:hidden'>0</span><span class=fon>Horse · driver</span><span class=foo>Odds</span><span class=fom>Margin</span></div>"
            f"{rows}{mutuels(st_)}<div class=fotap>Tap anywhere to close</div></div></div>")


def results_page(qs=None):
    """A night's results, spoiler-free: your starters in post order with nothing given away. Each has Watch (the
    replay) and Result (reveal the finish, time, purse and trip); Reveal all opens the lot. Step back through earlier
    nights with the arrows or the picker. What's revealed stays revealed in this browser."""
    qs = qs or {}
    nights = sorted({r["day"] for h in mine() for r in getattr(h, "results", [])}, reverse=True)
    if not nights:
        return page("Results", "<p>None of yours has raced yet.</p>")
    try:
        day = int(qs.get("day", nights[0]))
    except ValueError:
        day = nights[0]
    if day not in nights:
        day = nights[0]
    k = nights.index(day)
    lbl = lambda d: f"Year {c.year_of(d)}, week {d % c.YEAR + 1}"
    nav = ("<div class=rnav>"
           + (f"<a class='btn sec' href='/results?day={nights[k + 1]}'>‹ Earlier</a>" if k + 1 < len(nights) else "<span class='btn sec off'>‹ Earlier</span>")
           + "<form method=get action=/results class=inline><select name=day onchange='this.form.submit()'>"
           + "".join(f"<option value={d}{' selected' if d == day else ''}>{lbl(d)}{' (last night)' if d == nights[0] else ''}</option>" for d in nights)
           + "</select></form>"
           + (f"<a class='btn sec' href='/results?day={nights[k - 1]}'>Later ›</a>" if k > 0 else "<span class='btn sec off'>Later ›</span>")
           + "</div>")
    rs = [(h, r) for h in mine() for r in getattr(h, "results", []) if r["day"] == day]
    P()["seen"] = max(P().get("seen", -1), day)
    wins, paid = sum(r["place"] == 1 for _, r in rs), sum(r["won"] for _, r in rs)
    body = (f"<div class=proghead><span>Year {c.year_of(day)}, week {day % c.YEAR + 1}</span>"
            f"<span>{len(rs)} start{'s' if len(rs) != 1 else ''}<span class=spoil data-all> · {wins} win{'s' if wins != 1 else ''}, "
            f"<b class=won>${paid:,.0f}</b></span> <button class='sec revall' onclick='revealAll()'>Reveal all</button></span></div>")
    for track, title in (("mile", "Mile track"), ("half", "Half-mile track")):
        post_of = lambda r: int(r["trip"].split(",")[0].split()[-1]) if r["trip"].startswith("post") else 0
        rows = sorted((x for x in rs if x[1]["track"] == track), key=lambda x: post_of(x[1]))     # post order: no hint
        if not rows:
            continue
        body += f"<div class=progcard>{title}</div>"
        for h, r in rows:
            p, post = r["place"], post_of(r)
            trip = r["trip"].split(", ", 1)[1] if ", " in r["trip"] else r["trip"]
            rid = r.get("race_id") or f"{day}-{h.name}"
            nth = f"{p}{'th' if 10 <= p % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(p % 10, 'th')}"
            body += (f"<div class='prow rrow' data-rid='{esc(rid)}'>"
                     f"<span class=pad style='background:var(--p{post});color:{'#111' if post in (3, 6, 8, 10, 11) else '#fff'}'>{post}</span>"
                     f"<span class=pmid><a href='/horse/{urlname(h.name)}'><b>{esc(h.name)}</b></a> <span class=sub>{esc(r['race'])}, ${r['purse']:,}</span>"
                     f"<span class='ptrip spoil'>{esc(trip)}, {esc(r['finish'])}</span></span>"
                     f"<span class=pright><span class=rbtns>"
                     + (f"<a class='btn sec rbtn' href='/replay/{r['race_id']}'>Watch</a>" if r.get("race_id") in c.STORIES else "")
                     + f"<button class='rbtn' onclick='reveal(this)'>Result</button></span>"
                     f"<span class='spoil rres'><span class='rfin{' rwin' if p == 1 else ''}'>{nth}</span> <span class=rtime>{c.mile_time(r['time'])}</span>"
                     + (f"<span class=won>${r['won']:,.0f}</span>" if r["won"] else "")
                     + (f"<button class='sec rbtn fullbtn' onclick=\"fullOrder('{esc(r['race_id'])}')\">Full order</button>" if r.get("race_id") in c.STORIES else "")
                     + "</span></span></div>"
                     + (full_order(r["race_id"], h.name) if r.get("race_id") in c.STORIES else ""))
    idle = [h.name for h in mine() if h not in {x for x, _ in rs} and not h.retired] if day == nights[0] else []
    if idle:
        body += f"<p class=sub style='margin-top:14px'>Didn't race: {esc(', '.join(idle))}</p>"
    body = nav + body
    body += "<script>function fullOrder(id){const e=document.getElementById('fo-'+id);if(e)e.style.display='flex'}</script>"
    body += ("<script>const K='revealed';let seen=[];try{seen=JSON.parse(localStorage.getItem(K)||'[]')}catch(e){}"
             "function show(row){row.classList.add('shown');const b=row.querySelector('button.rbtn');if(b)b.remove();"
             "if(!seen.includes(row.dataset.rid)){seen.push(row.dataset.rid);try{localStorage.setItem(K,JSON.stringify(seen.slice(-300)))}catch(e){}}"
             "if(!document.querySelector('.rrow:not(.shown)')){document.querySelectorAll('[data-all]').forEach(x=>x.classList.add('on'));const a=document.querySelector('.revall');if(a)a.remove();}}"
             "function reveal(b){show(b.closest('.rrow'))}function revealAll(){document.querySelectorAll('.rrow').forEach(show)}"
             "document.querySelectorAll('.rrow').forEach(r=>{if(seen.includes(r.dataset.rid))show(r)});</script>")
    return page("Results", body)


def pedigree(h, gen=3):
    """The classic pedigree table: the horse, then sire over dam, then their parents.
    Each cell is a name and its best mile; unknown ancestors are the foundation stock."""
    def cell(p, rows, cls=""):
        inner = (f"<a href='/horse/{urlname(p.name)}'>{esc(p.name)}</a><small>{best_time(p)}</small>" if p
                 else "<span class=unk>foundation stock</span>")
        return f"<div class='pc {cls}' style='grid-row:span {rows}'>{inner}</div>"
    s, d = getattr(h, "sire", None), getattr(h, "dam", None)
    gp = [getattr(s, "sire", None), getattr(s, "dam", None), getattr(d, "sire", None), getattr(d, "dam", None)]
    return ("<div class=pedt>" + cell(h, 4, "me") + cell(s, 2, "ps") + cell(gp[0], 1, "ps g") + cell(gp[1], 1, "pd g")   # sires blue, dams rose
            + cell(d, 2, "pd") + cell(gp[2], 1, "ps g") + cell(gp[3], 1, "pd g") + "</div>")


def results_list(h, n=10):
    """The last ten starts, newest first, one line each: finish, race and track, time, and what it paid."""
    res = getattr(h, "results", None)
    if not res:
        lines = list(reversed(getattr(h, "form", [])))[:n]
        return ("<div class=card>" + ("<br>".join(esc(x) for x in lines) or "<span class=sub>unraced</span>") + "</div>")
    rows = ""
    for r in list(reversed(res))[:n]:
        p = r["place"]
        ordn = {1: "1st", 2: "2nd", 3: "3rd"}.get(p, f"{p}th")
        rows += (f"<div class=r10><span class='rp{' rp1' if p == 1 else ' rp3' if p <= 3 else ''}'>{ordn}</span>"
                 f"<span class=r10n>{esc(r['race'])}<span class=sub> · {esc(r.get('venue') or ('half-mile' if r['track'] == 'half' else 'mile'))}</span></span>"
                 f"<span class=r10t>{c.mile_time(r['time'])}</span><span class=r10w>{'$' + format(round(r['won']), ',') if r['won'] else ''}</span>"
                 + (f"<a class=r10v href='/replay/{r['race_id']}'>▶ Watch replay</a>" if r.get("race_id") in c.STORIES else "") + "</div>")
    more = len(res) - n
    return "<div class='card rlist10'>" + rows + (f"<div class=sub style='margin-top:6px'>Last {n} of {h.starts} starts</div>" if more > 0 else "") + "</div>"


def trophy_case(h):
    """What the horse has won that lasts: stakes trophies, championships, course records, and career milestones."""
    items = []
    for t in getattr(h, "trophies", []):                               # "Year N Stake name"
        name = t.split(" ", 2)[2] if t.startswith("Year ") else t
        items.append(("laurel" if name.startswith("Crown") else "cup", name, t.split(" ", 2)[0] + " " + t.split(" ", 2)[1] if t.startswith("Year ") else ""))
    for yr, champs in sk.CHAMPIONS.items():
        for div, name in champs.items():
            if name == h.name:
                items.append(("crown", f"{div} Champion", f"Year {yr}"))
    for day, st_ in _record_breakers():
        if st_["horses"] and st_["horses"][0]["name"] == h.name:
            items.append(("clock", f"Course record {c.mile_time(st_['quarters'][-1])}", st_.get("venue") or st_["track"]))
    mark = max((m for m in (1_000_000, 5_000_000, 10_000_000) if h.earnings >= m), default=0)   # the highest milestone only
    if mark:
        items.append(("money", f"${mark // 1_000_000}M earner", f"${h.earnings:,.0f} career"))
    w = max((x for x in (25, 50, 100) if h.wins >= x), default=0)
    if w:
        items.append(("medal", f"{w} wins", f"{h.wins} career"))
    if not items:
        return "<div class=card><span class=sub>No trophies yet. Stakes wins, championships and course records go here.</span></div>"
    art = {"cup": "cup", "crown": "crown", "clock": "clock", "medal": "medal", "money": "money", "laurel": "horseshoe"}   # SpriteCook trophy icons
    tiles = "".join(f"<div class='tcase t{k}'><img class=ticon src=/mock/brand/trophies/{art[k]}.png alt=''><b>{esc(t)}</b><span>{esc(sub)}</span></div>" for k, t, sub in items)
    return f"<div class=card><div class=tgrid>{tiles}</div></div>"


def career_phase(h):
    """Where a horse is in its career, from the trainer's read of its arc: (phase, one-line verdict, peak age).
    Phases: developing, prime, past peak, declining."""
    curve = {a: h.race_score(a) for a in range(2, 13)}
    peak_age = max(curve, key=curve.get)
    top, low = curve[peak_age], min(curve.values())
    now = curve.get(h.age, low)
    share = (now - low) / ((top - low) or 1)                    # 1 at the peak, 0 at the arc's lowest
    if h.age < peak_age and share < .97:
        return "developing", f"Still improving. Expect its best around age {peak_age}.", peak_age
    if share >= .95:
        left = sum(1 for a in range(h.age + 1, 13) if (curve[a] - low) / ((top - low) or 1) >= .9)
        return "prime", (f"In its prime{', with about ' + str(left) + ' more top season' + ('s' if left != 1 else '') if left else ', and this is likely the last top season'}."), peak_age
    if share >= .8:
        return "past", "Just past its peak. Still competitive; the slide is gentle for now.", peak_age
    return "declining", "Declining. Each season from here will be a step slower.", peak_age


def growth_chart(h):
    """Development: one question, where is this horse in its career? The trainer's read of the arc from 2 to 12,
    shaded by phase, with the horse marked on it, and the answer in a line. No scale to decode."""
    if h.starts < 10 and h.age <= 2:
        return (f"<div class=card><div class=phase><b>Developing</b> <span class=sub>The trainer needs 10 starts to read "
                f"this horse's career ({h.starts} so far).</span></div></div>")
    W, H, L, R, T, B = 340, 120, 10, 10, 18, 26
    curve = {a: h.race_score(a) for a in range(2, 13)}
    peak_age = max(curve, key=curve.get)
    top, low = curve[peak_age], min(curve.values())
    x = lambda a: L + (a - 2) * (W - L - R) / 10
    y = lambda r: T + (top - r) * (H - T - B) / ((top - low) or 1)
    def phase_at(a):
        sh = (curve[a] - low) / ((top - low) or 1)
        return "developing" if a < peak_age and sh < .97 else "prime" if sh >= .95 else "past" if sh >= .8 else "declining"
    COL = {"developing": "#3fb96b", "prime": "#e8a33a", "past": "#89cff0", "declining": "#8a93a3"}
    bands = "".join(f"<rect x='{x(a) - (W - L - R) / 20:.1f}' y='{H - B + 4}' width='{(W - L - R) / 10 + .5:.1f}' height='6' fill='{COL[phase_at(a)]}'/>"
                    for a in range(2, 13))
    area = (f"<path d='M{x(2):.1f},{H - B} " + " ".join(f"L{x(a):.1f},{y(curve[a]):.1f}" for a in range(2, 13))
            + f" L{x(12):.1f},{H - B} Z' fill='#ffffff10'/>"
            + "<polyline fill='none' stroke='#c9d1e3' stroke-width='2' points='" + " ".join(f"{x(a):.1f},{y(curve[a]):.1f}" for a in range(2, 13)) + "'/>")
    ages = "".join(f"<text x='{x(a):.1f}' y='{H - 4}' font-size='10' text-anchor='middle' fill='#8a93a3'>{a}</text>" for a in range(2, 13, 2))
    peak = f"<text x='{x(peak_age):.1f}' y='{y(top) - 6:.1f}' font-size='10' text-anchor='middle' fill='#c9d1e3'>peak</text>"
    mark = ""
    if not h.retired and 2 <= h.age <= 12:
        a = h.age
        mark = (f"<circle cx='{x(a):.1f}' cy='{y(curve[a]):.1f}' r='6' fill='{COL[phase_at(a)]}' stroke='#05070d' stroke-width='2'/>"
                f"<text x='{x(a):.1f}' y='{y(curve[a]) + 18:.1f}' font-size='11' font-weight='700' text-anchor='middle' fill='var(--ink)'>now</text>")
    ph, line, _ = career_phase(h)
    title = {"developing": "Developing", "prime": "In its prime", "past": "Past its peak", "declining": "Declining"}[ph]
    key = "".join(f"<span><i style='background:{COL[k]}'></i>{t}</span>" for k, t in
                  (("developing", "developing"), ("prime", "prime"), ("past", "past peak"), ("declining", "declining")))
    return (f"<div class=card><div class=phase><b style='color:{COL[ph]}'>{title}</b> <span class=sub>{line if not h.retired else 'Retired.'}</span></div>"
            f"<svg viewBox='0 0 {W} {H}' width='100%' style='display:block;margin-top:6px'>{area}{bands}{ages}{peak}{mark}</svg>"
            f"<div class=gkey>{key}</div></div>")


def sell_box(h):
    """Two ways out of the barn: the sale board, where the price is the market's (a proven earner's record, never under
    $50k) and a buyer has to come; or the house, which pays 40% of that same record tonight, never under $20k."""
    house = e.house_offer(h)
    if (w := e.held(h)):
        return f"<div class=card><div class=sub>Bought on the board: {h.name} can be sold again in {w} week{'s' if w != 1 else ''}.</div></div>"
    if P().get("frozen"):
        return "<div class=card><div class=sub>Your barn's buying and selling is paused while the stewards look at a sale. You can still race.</div></div>"
    if on_card(h):
        return f"<div class=card><div class=sub>{h.name} is on tonight's program. It races first; list it tomorrow.</div></div>"
    return (f"<div class=card><div class=row style='gap:10px;flex-wrap:wrap'>"
            f"<form method=post action=/order class=inline><input type=hidden name=h value='{esc(h.name)}'><input type=hidden name=o value=sell>"
            f"<button class=sec>List on the market</button></form>"
            f"<form method=post action=/scrap class=inline><input type=hidden name=h value='{esc(h.name)}'>"
            f"<button class=sec onclick=\"return ask(this,'Sell {h.name} to the house for ${house:,.0f}? Gone for good.')\">Sell to the house · ${house:,.0f}</button></form></div>"
            f"<div class=sub>Market: worth about ${max(e.MIN_PRICE, e.value(h)):,.0f}; bidding opens under that tonight and it sells when a barn buys. "
            f"House: ${house:,.0f}, paid now, no buyer needed. The house pays on the record, so a proven earner brings "
            f"more and an unraced or losing horse brings ${e.SCRAP:,}.</div></div>")


def horse_page(name, entering=False):
    h = find_horse(name)
    if not h:
        return page("Horse", "<p>Gone.</p>")
    own = h.owner == ME
    listed = e.listings.get(h.id)
    sim = ""
    if h in e.nursery and own and ME == ADMIN:                                # watch a youngster grow, a month at a time (moves the world: admin only)
        wk = (2 - h.age) * c.YEAR - G["day"] % c.YEAR
        sim = ("<div class=card><div class=row style='justify-content:space-between;gap:10px'>"
               f"<span>{'Weanling' if h.age == 0 else 'Yearling'} · races in {wk} weeks</span>"
               f"<form method=post action=/advance class=inline><input type=hidden name=days value=4><input type=hidden name=back value=/horse/{urlname(h.name)}>"
               "<button>Sim 1 month</button></form></div>"
               "<div class=sub>Runs four weeks of the whole circuit: your racers' entries race too.</div></div>")
    if h.retired:                                                             # life after racing gets its own card
        body = retired_header(h, own)
    else:
        body = card_header(h, own, listed[1] if listed and not own else None) + sim + stats_block(h, own)
    if own and (h in e.nursery and h.age == 1 or h not in e.nursery and not h.retired and h.age <= c.YOUNG):   # the day sheet, for a youngster
        body += section("Training", f"<div class=card>{day_sheet(h, '/horse/' + urlname(h.name))}</div>", True)
    if not h.retired and (own or h.starts >= 10 or h.age > 2):                # anyone's horse once it has a 10-start record to read
        body += section("Development", growth_chart(h), True)
    foal = h in e.nursery                                                     # still growing up: nothing to race or show yet
    if not foal:
        body += section("Results", results_list(h))
        body += section("Trophy Case", trophy_case(h), bool(getattr(h, "trophies", None)))
    body += section("Pedigree", "<div class=card style='padding:0;overflow:hidden'>" + pedigree(h) + "</div>")
    kids = sorted(kids_of(h), key=lambda k: -k.earnings)
    if kids:
        rows = "".join(f"<tr><td><a href='/horse/{urlname(k.name)}'>{esc(k.name)}</a></td><td>{k.age}yo {sex_word(k)}</td><td>{k.tier}</td>"
                       f"<td>{k.starts}-{k.wins}</td><td>{best_time(k)}</td><td>${k.earnings:,.0f}</td></tr>" for k in kids)
        body += section(f"Foal Stats · {len(kids)}", f"<div class=card><div class=sub>{sum(k.wins for k in kids)} wins, ${sum(k.earnings for k in kids):,.0f} earned, "
                        f"{sum(1 for k in kids if k.tier in 'SA')} rated A or better</div>"
                        "<table><tr><th>Name</th><th></th><th>Tier</th><th>Record</th><th>Best</th><th>Earnings</th></tr>" + rows + "</table></div>")
    if not own or foal:
        return page(h.name, body)
    if h.retired:
        if h.sex == "m":
            inner = (f"<div class=card><div>{e.covers_sold(h)} of {e.BOOK} covers sold this season · house price ${e.house_price(h):,.0f}"
                     f" · expected foal earnings ${e.expected_foal_net(h):,.0f}</div>"
                     f"<form method=post action=/fee style='margin-top:6px'><input type=hidden name=h value='{esc(h.name)}'>"
                     f"$<input name=fee type=number min=0 step=1000 value={int(e.stud_fee(h))} style='width:110px'> <button class=sec>Set fee</button></form>"
                     f"<div class=sub>Players book all season at your fee. From week {e.AI_BREED_WEEK} computer barns book too, at or under ${e.AI_RATE * e.house_price(h):,.0f}. "
                     f"Registry takes {e.REGISTRY:.0%}.</div></div>")
        else:
            inner = None                                                      # mares book from the Breed button in their card
        if inner:
            body += section("Stud fee", inner, True, "breeding")
        body += section("Sell", sell_box(h), True, "sell")
        return page(h.name, body)
    cur = getattr(h, "order", None)
    cl = crown_line(h)
    crown = ""
    if cl:
        st_, rank, wk = cl
        when = "tonight" if wk == 0 else f"in {wk} week{'s' if wk != 1 else ''} (week {st_.week + 1})"
        crown = (f"<div class='crownline{' in' if rank <= sk.FIELD else ''}'><b>{esc(st_.name)}</b> · ${st_.purse:,} · {when}<br>"
                 + (f"Invited: #{rank} in this season's earnings. The Crown takes the top {sk.FIELD}; {esc(h.name)} goes in automatically, no entry needed."
                    if rank <= sk.FIELD else
                    f"#{rank} in this season's earnings: the top {sk.FIELD} are invited. "
                    f"{'Still time to earn a place.' if wk > 0 else 'Not in this year.'}") + "</div>")
    inner = f"<div class=card>{crown}<div class=row style='gap:4px 10px;margin-bottom:6px;flex-wrap:wrap'>{condition(h)}<span>{tonight(h)}</span>"
    if cur:
        inner += f" <form method=post action=/scratch class=inline><input type=hidden name=h value='{esc(h.name)}'><button class=sec>Scratch</button></form>"
    inner += "</div>"
    if h.freshness < e.GROOMED_TO:
        inner += groom_form(h)
    # a sliding strip of tracks (like the barn's menu); the chosen track's races open underneath, best-paying first.
    # The track it's entered at is picked by itself.
    by_track, vtabs, vpanes = {}, [], []
    for o in c.offerings(h):
        by_track.setdefault(o[0]["id"], []).append(o)
    for v in c.VENUES:
        rows = sorted(by_track.get(v["id"], []), key=lambda o: -o[3])
        if not rows:
            continue
        here = cur and cur[0] == "enter" and len(cur) > 5 and cur[5] == v["id"]
        fold = ""
        for _, rname, purse, vpurse, tag, track in rows:
            picked = here and cur[1] == rname and cur[4] == track
            warn = f"onclick=\"return ask(this,'Enter {h.name} in a ${tag:,} claimer at {v['name']}? Any barn can take him for the tag.')\"" if tag else ""
            mates = stablemates(h, rname, track, v["id"])
            tip = "You already have " + " and ".join(x.name for x in mates) + " in this race"
            fold += (f"<div class=erow><span class=ename>{esc(c.race_title(c.age_group(h), rname))}</span><span class=money>${vpurse:,}</span><span class=entercell>"
                     + ("<b class=entered>Entered</b>" if picked else
                        f"<form method=post action=/enter class=inline><input type=hidden name=h value='{esc(h.name)}'>"
                        f"<input type=hidden name=r value='{rname}|{purse}|{tag}|{track}|{v['id']}'><button class=sec {warn}>Enter</button></form>")
                     + (f"<span class=mates title='{esc(tip)}' aria-label='{esc(tip)}'>{STABLEMATE}</span>" if mates else "") + "</span></div>")
        wk = G["day"] % c.YEAR + 1
        fair = " · <b class=fairnow>fair week</b>" if v.get("fair") and v["fair"][0] <= wk < v["fair"][1] else ""
        head = (f"<span class=vname>{esc(v['name'])}</span><span class=vmeta>{'mile' if v['track'] == 'mile' else 'half-mile'} · "
                f"{len(rows)} race{'s' if len(rows) != 1 else ''} · up to ${rows[0][3]:,}{fair}</span>"
                + ("<span class=vin>entered</span>" if here else ""))
        vtabs.append((v["id"], v["name"], here, bool(fair)))
        p_, a_, f_, m_, b_ = TI.look(v["id"])
        vpanes.append((v["id"], f"<div class=vband style='--tp:{p_};--ta:{a_}'><img src={b_} width=40 height=40 alt=''><div><b style=\"font-family:{f_}\">"
                                f"{esc(v['name'])}</b><span>{esc(m_)}</span></div></div><div class=vmeta2>{head}</div>{fold}"))
    if vtabs:
        pick = next((i for i, (_, _, here_, _) in enumerate(vtabs) if here_), 0)
        inner += ("<div class='hmenu vstrip'>" + "".join(
            f"<button type=button data-v={vid}{' class=on' if i == pick else ''} style='--tp:{TI.look(vid)[0]};--ta:{TI.look(vid)[1]}'>"
            f"<img src={TI.look(vid)[4]} width=18 height=18 alt=''>{esc(nm)}{' <i class=vdot></i>' if here_ else ''}"
            f"{' <b class=fairnow>fair</b>' if fair_ else ''}</button>" for i, (vid, nm, here_, fair_) in enumerate(vtabs)) + "</div>"
            + "".join(f"<div class=vpane id=vp-{vid}{'' if i == pick else ' hidden'}>{p}</div>" for i, (vid, p) in enumerate(vpanes))
            + "<script>document.currentScript.previousElementSibling&&0;(()=>{const s=document.querySelector('.vstrip');s.querySelectorAll('button').forEach(b=>b.onclick=()=>{"
              "s.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));document.querySelectorAll('.vpane').forEach(p=>p.hidden=p.id!=='vp-'+b.dataset.v);"
              "b.scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'})});s.querySelector('.on').scrollIntoView({inline:'center',block:'nearest'})})()</script>")
    inner += "<div class=sub style='margin-top:6px'>Every race this horse qualifies for, by track. Higher class, bigger purse, tougher field.</div>"
    best = sk.best_for(h, G["day"])
    inner += "<div style='margin-top:10px'><b>Stakes</b> <span class=sub>by nomination, weeks ahead</span></div>"
    if best:
        inner += "<table><tr><th>Stake</th><th>Week</th><th>Fee now</th><th>Expected net</th><th></th></tr>"
        for ev, s, fee in best[:5]:
            act = ("<b>nominated</b>" if h in s.noms else
                   f"<form method=post action=/nominate class=inline><input type=hidden name=h value='{esc(h.name)}'><input type=hidden name=s value={s.id}>"
                   f"<button class=sec onclick=\"return ask(this,'Pay ${fee:,.0f} to nominate {h.name} for the {s.name}?')\">Nominate</button></form>")
            inner += f"<tr><td>{esc(s.name)}</td><td>{s.week} ({s.week - G['day'] % c.YEAR:+})</td><td>${fee:,.0f}</td><td>${ev:,.0f}</td><td>{act}</td></tr>"
        inner += "</table>"
    else:
        inner += "<div class=sub>None open that this horse can enter.</div>"
    opts = "".join(f"<option>{o}</option>" for o in ["rest", "sell"])
    inner += (f"<div style='margin-top:10px'><b>Or instead this week</b></div><form method=post action=/order><input type=hidden name=h value='{esc(h.name)}'>"
              f"<select name=o>{opts}</select> <button class=sec>Set</button></form><div class=sub>Not entered means the trainer's week: school or rest.</div></div>")
    if entering:                                                          # the race sheet: only when you came to enter the horse
        body += section("Enter tonight", inner, True, "enter")
    body += section("Sell", sell_box(h), False, "sell")
    role = "stand at stud" if h.sex == "m" else "join the broodmare band"
    room = e.barn_head(ME) - sum(x.retired for x in mine())
    if room <= 0:
        body += section("Retire", "<div class=card><div class=sub>No place in the breeding barn" + (" (it comes with the Breeder's License)" if not e.barn_head(ME) else ": sell or cull a retired horse, or upgrade") + ".</div></div>")
    else:
        body += section("Retire", f"<div class=card><form method=post action=/order><input type=hidden name=h value='{esc(h.name)}'><input type=hidden name=o value=retire>"
                        f"<button class=warn onclick=\"return ask(this,'Retire {h.name} from racing to {role}? This cannot be undone.')\">Retire to {role}</button></form>"
                        "<div class=sub>A horse breeds only after its racing days are over.</div></div>")
    return page(h.name, body)


def bottle(kind, size=22, empty=None):
    """A Post Time Tonic bottle in its color; the premium in the S+ shimmer. kind None: an empty outline."""
    col = dict((k, c_) for k, _, c_, _ in TONICS).get(kind)
    gid = f"pg{size}"
    fill = (f"url(#{gid})" if kind == "premium" else col) if kind else (empty or "none")
    grad = (f"<defs><linearGradient id={gid} x1=0 y1=0 x2=1 y2=1><stop offset=0 stop-color='#f0abfc'/><stop offset=.5 stop-color='#67e8f9'/>"
            f"<stop offset=1 stop-color='#fde68a'/></linearGradient></defs>") if kind == "premium" else ""
    return (f"<svg class='tb{' tbp' if kind == 'premium' else ''}' viewBox='0 0 24 24' width={size} height={size} aria-hidden=true>{grad}"
            f"<path d='M9 2h6v2h-1v4l5 8a3 3 0 0 1-2.6 4.5H7.6A3 3 0 0 1 5 16l5-8V4H9z' fill='{fill}' stroke='currentColor' stroke-width='1.4' stroke-linejoin='round'/>"
            f"<path d='M8 13h8' stroke='#fff8' stroke-width='1.2'/></svg>")


def market_tabs(on):
    return ("<div class=hmenu>" + "".join(f"<a href='{h_}' class='{'on' if on == k else ''}'>{l_}</a>"
                                          for k, h_, l_ in (("auction", "/market", "Auction"), ("claimers", "/claimers", "Claimers"), ("sponsor", "/sponsor", "Sponsor"), ("shop", "/shop", "Shop"), ("tack", "/tack", "Tack Room"), ("upgrade", "/upgrade", "Upgrades"))
                                          if k != "sponsor" or SPONSORING) + "</div>")


def claimers_page(qs=None):
    """The claimers board: every horse in a claiming race on tonight's posted program, one row each, sortable by tag,
    rating, purses or age and filtered by tag band, age, sex, track and what you can afford. A claim from here is the
    same binding claim as one from the program; your own horses show tinted, with no button."""
    qs = qs or {}
    sort, band, grp, sex, vid, afford = qs.get("s", "tag"), qs.get("b", "all"), qs.get("g", "all"), qs.get("x", "all"), qs.get("v", "all"), qs.get("m") == "1"
    link = lambda **kw: "/claimers?" + "&".join(f"{k}={v}" for k, v in {"s": sort, "b": band, "g": grp, "x": sex, "v": vid, "m": int(afford), **kw}.items())
    chips = lambda items, cur, key: "<div class=fchips>" + "".join(
        f"<a href='{link(**{key: k})}' class='{'on' if str(cur) == str(k) else ''}'>{label}</a>" for k, label in items) + "</div>"
    head = (chips([("tag", "By tag"), ("est", "By rating"), ("earn", "By purses"), ("age", "By age")], sort, "s")
            + chips([("all", "Any tag"), ("lo", "$25,000–$60,000"), ("mid", "$90,000–$200,000"), ("hi", "$300,000+")], band, "b")
            + chips([("all", "All ages"), ("2", "2yo"), ("3", "3yo"), ("aged", "Aged")], grp, "g")
            + chips([("all", "Colts & fillies"), ("m", "Colts"), ("f", "Fillies")], sex, "x")
            + chips([("all", "All tracks")] + [(v["id"], v["name"]) for v in c.VENUES], vid, "v")
            + chips([(0, "Any price"), (1, f"Within my cash (${e.cash.get(ME, 0):,.0f})")], int(afford), "m"))
    rows = []
    if c.CARD.get("day") == G["day"]:
        for r in c.CARD["races"]:
            group, sx, name, purse, tag, track = r["key"]
            if not tag:
                continue
            for h in r["field"]:
                rows.append((h, tag, r))
    bands = {"lo": (0, 60_000), "mid": (90_000, 200_000), "hi": (300_000, 10 ** 9)}
    if band in bands:
        rows = [x for x in rows if bands[band][0] <= x[1] <= bands[band][1]]
    if grp != "all":
        rows = [x for x in rows if c.age_group(x[0]) == grp]
    if sex != "all":
        rows = [x for x in rows if x[0].sex == sex]
    if vid != "all":
        rows = [x for x in rows if x[2]["v"]["id"] == vid]
    if afford:
        rows = [x for x in rows if x[1] <= e.cash.get(ME, 0)]
    keyf = {"tag": lambda x: (x[1], -x[0].est), "est": lambda x: -x[0].est, "earn": lambda x: -x[0].earnings, "age": lambda x: (x[0].age, x[1])}[sort if sort in ("tag", "est", "earn", "age") else "tag"]
    rows.sort(key=keyf)
    room = e.stalls(ME) - e.barn_size.get(ME, 0) - sum(1 for b in c.CLAIMS.values() if b == ME)
    PER = 10; n = max(1, -(-len(rows) // PER))
    pg = max(1, min(n, int(qs.get("p", 1)) if str(qs.get("p", "")).isdigit() else 1))
    nums = {(key, vn): num for num, key, vn, f, o in program_races()[1]}       # each race's number on its track's card
    out = ""
    for h, tag, r in rows[(pg - 1) * PER: pg * PER]:                            # each claimer as its program entry, under a strip in the track's colors
        lk = vlook(r["v"]["name"]); num = nums.get((r["key"], r["v"]["name"]), "·")
        tkname = f"<span class=tkn style='font-family:{lk[2]}'>{esc(r['v']['name'])}</span><br>" if lk else ""
        strip = (f"<div class='pgh{' tk' if lk else ''}'" + (f" style='--tp:{lk[0]};--ta:{lk[1]}'" if lk else "") + f"><div class=pgn style='font-size:{20 if tag >= 1_000_000 else 24}px'>${tag:,}</div>"
                 + (f"<img class=tkb src={lk[4]} width=40 height=40 alt=''>" if lk else "")
                 + f"<div class=pgt>{tkname}RACE {num} · {esc(c.race_title(r['key'][0], r['key'][2]).split(' $')[0])}"   # the tag shows once, big, on the left
                   f"<br>Purse ${c.venue_purse(r['v'], r['key'][3]):,} · {'Mile' if r['key'][5] == 'mile' else 'Half-mile'} track</div>"
                 f"<div class=pgp>POST<br><b>{getattr(h, 'post', 0)}</b></div></div>")
        entry = program_entry(h, tag, r["odds"], True, room).replace("class='inline pgclaim'>", "class='inline pgclaim'><input type=hidden name=back value=/claimers>")
        out += f"<div class=pgm>{strip}{entry}</div>"
    pager = ""
    if n > 1:
        lnk = lambda k, t: f"<a class=pg href='{link(p=k)}#list'>{t}</a>" if 1 <= k <= n and k != pg else f"<span class='pg{' on' if k == pg else ''}'>{t}</span>"   # lands on the entries, not the page top
        pager = f"<div class=pager>{lnk(pg - 1, '&laquo;')}{''.join(lnk(k, k) for k in range(1, n + 1))}{lnk(pg + 1, '&raquo;')}</div>"
    note = (f"<p class=sub>Every horse in a claiming race tonight, each as its program entry. A claim is binding if the horse races, whatever the result; claims stay open until post time. "
            f"You can claim {max(0, room)} more tonight.</p>")
    body = (f"<style>{PP_CSS}</style><style>.pgm{{margin:10px 0}}.pgm .pgh{{cursor:default}}</style>" + market_tabs("claimers") + note + head
            + f"<p class=sub id=list style='scroll-margin-top:8px'>{len(rows)} claimer{'s' if len(rows) != 1 else ''}{f' · page {pg} of {n}' if n > 1 else ''}</p>"
            + (out or "<p class=sub>No claimers on tonight's program" + ("" if c.CARD.get("day") == G["day"] else "; the card is drawn at 8 PM") + ".</p>") + pager)
    return page("Claimers", body)


TACK = {"harness": ("Harness", 0, 0), "mask": ("Face mask", 40, 5), "wraps": ("Leg wraps", 30, 5), "bike": ("Bike", 50, 5)}   # name, unlock, fitting
TACK_FREE_FIT = 7      # Prestige tier from which fittings cost nothing


def tack_of(o):
    """The barn's Tack Room: designs unlocked, and which of its two colors each piece takes (the hub apart from the bike)."""
    return P(o).setdefault("tack", {"own": ["harness"], "col": {"harness": "p", "mask": "p", "wraps": "s", "bike": "p", "hub": "s"}})


def tack_colors(o):
    sk_ = silks_of(o)
    return sk_["c1"], sk_["c2"]


def fitted(h):
    """The pieces a horse wears: only while it's with the barn that fitted it."""
    f = getattr(h, "fit", None)
    return f[1] if f and f[0] == h.owner else []


def fit_cost(o, pieces):
    return 0 if prestige_of(o) >= TACK_FREE_FIT else sum(TACK[k][2] for k in pieces)


def tack_model(o, pieces=None):
    t = tack_of(o); c1, c2 = tack_colors(o)
    return TA.render(t["own"] if pieces is None else pieces, t["col"], c1, c2)


def tack_page(msg=""):
    """The Tack Room: the barn's horse model pinned at the top in its gear, the designs to unlock and color, and the
    string below to fit, all in Markers."""
    t = tack_of(ME); own = t["own"]; c1, c2 = tack_colors(ME); free = prestige_of(ME) >= TACK_FREE_FIT
    sw = lambda hx: f"<span style='display:inline-block;width:12px;height:12px;background:{hx};border:1px solid #000;vertical-align:-1px'></span>"
    pick = lambda k: "".join(f"<label style='margin-right:8px'><input type=radio name=c_{k} value={v}{' checked' if t['col'].get(k, 'p') == v else ''}> {sw(c1 if v == 'p' else c2)}</label>" for v in ("p", "s"))
    rows = ""
    for k, (name, unlock, fee) in TACK.items():
        have = k in own
        rows += (f"<div class='erow2'><div style='flex:1'><b>{name}</b><div class=sub>{'in the barn' if have else f'unlock {unlock} Markers'} · fitting {'free' if free else f'{fee} each'}</div>"
                 + (f"<div class=sub style='margin-top:4px'>{'Bike ' if k == 'bike' else ''}{pick(k)}{' Hub ' + pick('hub') if k == 'bike' else ''}</div>" if have else "") + "</div>"
                 + ("" if have else f"<form method=post action=/tack class=inline><input type=hidden name=do value=unlock><input type=hidden name=k value={k}><button class=sec{'' if markers() >= unlock else ' disabled'}>Unlock {unlock}</button></form>") + "</div>")
    horses = ""
    for h in sorted((x for x in mine() if not x.retired), key=lambda x: x.name):
        on = fitted(h); cost = fit_cost(ME, [k for k in own if k not in on])
        horses += (f"<div class='erow2'><div style='flex:1;min-width:0'><b>{esc(h.name)}</b> <span class=sub>{h.age}yo {sex_word(h)}</span>"
                   f"<div class=sub>{'wearing ' + ', '.join(TACK[k][0].lower() for k in on) if on else 'bare'}</div></div><span class=row style='gap:6px'>"
                   + (f"<form method=post action=/tack class=inline><input type=hidden name=do value=fit><input type=hidden name=h value='{esc(h.name)}'><button class=sec{'' if markers() >= cost else ' disabled'}>Fit{f' · {cost}' if cost else ''}</button></form>" if len(on) < len(own) else "")
                   + (f"<form method=post action=/tack class=inline><input type=hidden name=do value=strip><input type=hidden name=h value='{esc(h.name)}'><button class=sec>Strip</button></form>" if on else "") + "</span></div>")
    body = (market_tabs("tack") + (f"<div class=card><b>{esc(msg)}</b></div>" if msg else "")
            + f"<div class='card hc mgr' style='--tc:{c1}'><div class=mhead><b>Tack Room</b><span>{mk_tag(markers())}</span></div>"
            f"<div style='text-align:center;background:#0b1120;border:1px solid var(--rule);padding:8px'><img src='{tack_model(ME)}' alt='your horse in its gear' style='max-width:100%;image-rendering:pixelated'></div>"
            f"<div class=sub style='margin-top:6px'>Your colors {sw(c1)} primary {sw(c2)} secondary, set in Barn identity. A design is bought once for the barn; fitting a horse is a small charge each time, and the gear stays home when a horse leaves. Looks only: a horse races the same in it or out of it.</div></div>"
            f"<form method=post action=/tack><input type=hidden name=do value=colors><div class='card hc mgr' style='--tc:{c2}'><div class=mhead><b>Designs</b></div><div class=mgrid>{rows}</div><div class=mact><button class=sec>Save colors</button></div></div></form>"
            f"<div class='card hc mgr' style='--tc:{c1}'><div class=mhead><b>Your string</b><span class=pchip>{'fittings free' if free else 'fit per horse'}</span></div><div class=mgrid>{horses or '<p class=sub>No racers.</p>'}</div></div>")
    return page("Tack Room", body)


def tack_post(q):
    """Unlock a design, save the colors, fit or strip a horse. Returns the message for the page."""
    t = tack_of(ME); do = q.get("do")
    if do == "unlock" and q.get("k") in TACK and q["k"] not in t["own"]:
        price = TACK[q["k"]][1]
        if markers() < price:
            return "Not enough Markers."
        mk_book(ME, -price, f"{TACK[q['k']][0]} design"); t["own"].append(q["k"])
        return f"{TACK[q['k']][0]}: in the barn."
    if do == "colors":
        for k in list(TACK) + ["hub"]:
            if q.get(f"c_{k}") in ("p", "s"):
                t["col"][k] = q[f"c_{k}"]
        return "Colors saved."
    h = next((x for x in mine() if x.name == q.get("h")), None)
    if not h:
        return ""
    if do == "fit":
        on = fitted(h); new = [k for k in t["own"] if k not in on]; cost = fit_cost(ME, new)
        if markers() < cost:
            return "Not enough Markers."
        if cost:
            mk_book(ME, -cost, f"fitting {h.name}")
        h.fit = (ME, list(t["own"]))
        return f"{h.name} fitted."
    if do == "strip":
        h.fit = None
        return f"{h.name} stripped."
    return ""


def shop_page(msg=""):
    """The Shop: Post Time Tonic by the bottle, and the barn's shelf. More items and cosmetics come here later."""
    t = shelf()
    inv = "".join(f"<div class=inv>{bottle(k, 26)}<b>{t[k]}</b><span class=sub>{l_}</span></div>" for k, l_, *_ in TONICS)
    items = "".join(
        f"<div class='card titem{' tprem' if k == 'premium' else ''}'><div class=tbig>{bottle(k, 44)}</div><div class=tmid><b>{l_} Tonic</b>"
        f"<div class=sub>{esc(what)}</div></div>"
        f"<form method=post action=/buytonic class=inline><input type=hidden name=k value={k}>"
        f"<button{' disabled' if e.cash.get(ME, 0) < TONIC_PRICE[k] else ''}>${TONIC_PRICE[k]:,}</button></form></div>"
        for k, l_, _, what in TONICS)
    streak, log = P().get("streak", 0), P().get("mk_log", [])[-6:][::-1]
    packs = "".join(f"<div class='card pack'><b>{mk_tag(n, 20)}</b><span class=sub>${usd:.2f}</span><span class=sub>coming soon</span></div>" for n, usd in ((20, 4.99), (50, 9.99), (120, 19.99)))
    loglines = "".join(f"<div class=row style='justify-content:space-between;font-size:13px'><span class=sub>Yr {c.year_of(d)} wk {d % c.YEAR + 1} · {esc(why)}</span><b style='color:{'var(--mk)' if n > 0 else 'var(--loss)'}'>{n:+,}</b></div>" for d, n, why in log)
    mk = (f"<div class='card' id=markers><div class=row style='gap:12px'>{MK_ICON(40)}<div style='flex:1'><b>Markers</b> <span class=mk style='margin-left:6px'>{markers():,}</span>"
          "<div class=sub>The track's own chits. Spent on the barn's look, never on a horse, and never turned into cash. A few come free for showing up.</div></div></div>"
          + (f"<a class='btn sec' href=/sponsor style='display:block;text-align:center;margin-top:8px'>Sponsor a stake · {len(G.get('sponsor_auction', {}))} open</a>" if G.get("sponsor_auction") else "")
          + f"<div class=packs>{packs}</div>"
          f"<div class=row style='gap:10px;margin-top:8px'>{MK_ICON(28)}<div style='flex:1'><b>Daily check-in</b><div class=sub>Day {streak % 7 or 7} of 7 · {MK_CHECKIN} Marker a day, {MK_SEVENTH} on the seventh</div></div></div>"
          + (f"<div style='margin-top:8px'>{loglines}</div>" if loglines else "") + "</div>")
    body = (market_tabs("shop") + (f"<div class=card><b>{esc(msg)}</b></div>" if msg else "")
            + "<div class=secbar>Markers</div>" + mk
            + f"<div class=secbar>Your shelf</div><div class='card invrow'>{inv}</div>"
            + "<div class=secbar>Post Time Tonic</div>"
            + "<p class=sub>Give a tonic to a horse once it's entered: tap the bottle on its card. One per start; it lifts that stat for the night. "
              "The vet charges 2% of that race's purse to give it, paid at post time. Your tonics are your business: nobody else sees them.</p>"
            + items)
    return page("Shop", body)


def tonic_page(name, msg=""):
    """Give an entered horse a tonic for tonight: tap one from the shelf. Shows the vet's fee for this race."""
    h = find_horse(name)
    o = getattr(h, "order", None) if h else None
    if not h or h.owner != ME or not (isinstance(o, tuple) and o[0] == "enter"):
        return page("Tonic", "<p>Enter the horse first; then its bottle gives it a tonic for the night.</p>")
    t, on = shelf(), getattr(h, "tonic", None)
    v = c.VENUE_BY.get(o[5]) if len(o) > 5 else None
    fee = round(c.TONIC_FEE * (c.venue_purse(v, o[2]) if v else o[2]))
    head = (f"<div class=card><b>{esc(h.name)}</b> <span class=sub>tonight: {esc(order_text(h))}</span>"
            f"<div class=sub>Vet's fee for this race: <b class=money>${fee:,}</b>, paid at post time.</div></div>")
    if on:
        head += (f"<div class='card titem'><div class=tbig>{bottle(on, 40)}</div><div class=tmid><b>On {dict((k, l_) for k, l_, *_ in TONICS)[on]} Tonic tonight</b></div>"
                 f"<form method=post action=/tonic class=inline><input type=hidden name=h value='{esc(h.name)}'><input type=hidden name=k value=none>"
                 f"<button class=sec>Take it off</button></form></div>")
    if not any(t.values()) and not on:
        return page("Tonic", head + "<div class=card><b>Out of tonic.</b> <a class=btn href=/shop>Buy more in the Shop?</a></div>")
    picks = "".join(
        f"<form method=post action=/tonic class='inline tpick'><input type=hidden name=h value='{esc(h.name)}'><input type=hidden name=k value={k}>"
        f"<button class='sec' {'disabled' if not t[k] or k == on else ''}>{bottle(k, 34)}<b>{l_}</b><span class=sub>{t[k]} on the shelf</span></button></form>"
        for k, l_, *_ in TONICS)
    return page("Tonic", head + (f"<div class=card><b>{esc(msg)}</b></div>" if msg else "")
                + f"<div class=secbar>{'Switch to' if on else 'Give'} a tonic</div><div class=tgrid>{picks}</div>"
                + "<p class=sub><a href=/shop>Shop for more</a></p>")


TIER_ORDER = {t: k for k, t in enumerate(("S+", "S", "A", "B", "C", "D"))}


def market_page(qs=None):
    """The sale board, as an auction: each horse runs a real day; type a bid (all bids are final); a bid in the last ten
    minutes puts an hour back on the clock; the high bid at the close takes the horse. Ten to a page, sorted by when the
    auction ends, by age or by tier."""
    qs = qs or {}
    now = time.time()
    rows = [(h, e.auctions[h.id]) for h, _ in e.listings.values() if h.id in e.auctions]
    def left(s):
        s = max(0, int(s)); h_, m = s // 3600, s % 3600 // 60
        return f"{h_}h {m:02d}m" if h_ else f"{m}m {s % 60:02d}s"
    body = ("<div class=card><b>Auction</b><div class=sub>Every horse runs a full day. Type your bid: at least the minimum shown, as much more as you like. All bids are final. A bid with ten "
            "minutes or less left puts an hour back on the clock. The high bid at the close takes the horse. Other barns bid too.</div></div>")
    sort = qs.get("s") if qs.get("s") in ("age", "tier") else "ends"
    rows.sort(key={"ends": lambda r: r[1]["ends"], "age": lambda r: (r[0].age, r[1]["ends"]),
                   "tier": lambda r: (TIER_ORDER.get(tier_label(r[0]), 9), r[1]["ends"])}[sort])
    per, n = 10, max(1, -(-len(rows) // 10))
    pg = min(n, max(1, int(qs["p"]) if str(qs.get("p", "")).isdigit() else 1))
    url = lambda k, s_=sort: f"/market?s={s_}&p={k}"
    body += ("<div class=hmenu>" + "".join(f"<a href='{url(1, k)}' class='{'on' if k == sort else ''}'>{t}</a>"
                                           for k, t in (("ends", "Ending soon"), ("age", "Age"), ("tier", "Tier"))) + "</div>")
    for h, a in rows[(pg - 1) * per:pg * per]:
        coat, _ = looks(h)
        sire = f"by {h.sire.name}" if h.sire else "foundation stock"
        own_h, lead = h.owner == ME, a["leader"] == ME
        nb = e.next_bid(h.id)
        who = ("<b class=win>You lead</b>" if lead else f"high bid: {esc(barn_name(a['leader']))}" if a["leader"] is not None else "no bids yet")
        if own_h:
            act = "<span class=sub>your horse</span>"
        elif lead:
            act = "<span class=sub>you're the high bid</span>"
        elif e.cash.get(ME, 0) < nb:
            act = "<span class=sub>not enough cash</span>"
        else:
            act = (f"<form method=post action=/bid class=bidf><input type=hidden name=h value='{esc(h.name)}'>"
                   f"<label class=sub>Your bid (min ${nb:,.0f})</label><input type=number name=amt min={nb:.0f} max={e.cash.get(ME, 0):.0f} step=1000 value={nb:.0f} required>"
                   "<label class=bidok><input type=checkbox required> All bids are final</label>"
                   f"<button onclick=\"return this.form.reportValidity()&&ask(this,'Place this bid on {esc(h.name)}? All bids are final.')\">Place bid</button></form>")
        hot = a["ends"] - now <= 3600
        body += (f"<div class='card mkt{' ret' if h.retired else ''}' id=a{h.id}><div class=row>{portrait(h, 56)}<div style='flex:1;min-width:0'>"
                 f"<b><a href='/horse/{urlname(h.name)}'>{esc(h.name)}</a></b>{'<span class=retchip>RETIRED</span>' if h.retired else ''} <span class=sub>{h.age}yo {coat} {sex_word(h)} · {h.starts}-{h.wins} ${h.earnings:,.0f} · {sire}</span>"
                 + ("" if getattr(h, "form", None) else "<div class=chart>unraced</div>")
                 + f"<div class=sub style='margin-top:3px'>Best time <b class=money>{best_time(h)}</b></div>{stud_bars(h)}</div>"
                 f"<div style='text-align:center;min-width:96px'><div class='tier {tier_cls(h)}' style='margin:0 auto 4px'>{tier_label(h)}</div>"
                 f"<div class=money style='font-size:17px'>${a['price']:,.0f}</div><div class=sub style='font-size:11px'>{who}</div>"
                 f"<div class=sub style='font-size:11px;{'color:var(--loss)' if hot else ''}'>⏱ {left(a['ends'] - now)}</div>{act}</div></div></div>")
    link = lambda k, t: f"<a class=pg href='{url(k)}'>{t}</a>" if 1 <= k <= n and k != pg else f"<span class='pg{' on' if k == pg else ''}'>{t}</span>"
    if n > 1:
        body += f"<div class=pager>{link(pg - 1, '&laquo;')}{''.join(link(k, k) for k in range(1, n + 1))}{link(pg + 1, '&raquo;')}</div>"
    free = e.stalls(ME) - sum(not h.retired for h in mine())
    hp, nth = e.house_horse_price(ME), e.house_bought.get(ME, 0)
    cant = ("no stall free: sell, scrap or upgrade the barn first" if free <= 0
            else f"not enough cash (${hp:,} needed)" if e.cash[ME] < hp else "")
    house = (f"<div class=card><b>From the house</b><div class=sub>An unraced 3-year-old, sight unseen: breeding unknown, "
             f"the card is what you get. About half earn back their price over a career, and now and then one turns into a star.</div>"
             f"<div class=sub>{free} stall{'s' if free != 1 else ''} free</div>"
             + (f"<div class=sub style='color:var(--win);font-weight:700'>Welcome price: your {'first' if nth == 0 else 'second'} house horse is ${hp:,}"
                + (f" (then ${e.HOUSE_INTRO[1]:,}, then ${e.HOUSE_HORSE:,})" if nth == 0 else f" (then ${e.HOUSE_HORSE:,})") + "</div>" if hp < e.HOUSE_HORSE else "")
             + (f"<div class=ev>{cant}</div>" if cant else
                f"<form method=post action=/house style='margin-top:6px'>"
                f"<button onclick=\"return ask(this,'Buy an unraced 3-year-old from the house for ${hp:,}?')\">"
                f"Buy a horse · ${hp:,}</button></form>") + "</div>")
    return page("Sale board", market_tabs("auction") + house + (body or "<p>Nothing else on the board tonight. Yearlings come up at the year tick.</p>"))


def license_cost(o):
    """What the Breeder's License costs barn o from where it stands: the license plus any barn below it not yet built."""
    shed = next(i for i, L in enumerate(e.LEVELS) if L[2])
    return sum(e.LEVELS[i][3] for i in range(e.level.get(o, 0) + 1, shed + 1))


def license_offer():
    """The Breeder's License for sale right on the Breeding tab, with the barn it needs first folded into one price."""
    cost, short = license_cost(ME), e.LEVELS[e.level.get(ME, 0) + 1][0] != "breeder's license"
    what = "Build the working barn and buy the Breeder's License" if short else "Buy the Breeder's License"
    return (f"<div class=sub style='margin:6px 0'>The Breeder's License lets your mares be covered and your stallions stand at stud."
            + (" It needs the working barn first, so both come together." if short else "") + "</div>"
            + (f"<form method=post action=/license><button onclick=\"return ask(this,'{what} for ${cost:,}?')\">{what} · ${cost:,}</button></form>"
               if e.cash.get(ME, 0) >= cost else f"<button disabled>{what} · ${cost:,}</button><div class=sub>Not enough cash yet.</div>"))


def breeding_page(qs=None):
    """The Breeding tab: where your retired horses live. Stallions, broodmares and foals each on their own tab, ten to a
    page, sorted by age, tier or foals; each with seasons left, foals, and what it's doing this season."""
    qs = qs or {}
    mine_ = [h for h in mine() if h.retired]
    stallions, mares = [h for h in mine_ if h.sex == "m"], [h for h in mine_ if h.sex == "f"]
    def kids(h):
        return [k for k in G["horses"] if k.sire is h or k.dam is h]
    def row(h):
        ks, left = kids(h), c.BREEDING_UNTIL - h.age
        if h.sex == "m":
            now = f"{e.covers_sold(h)}/{e.BOOK} covers · fee ${e.stud_fee(h):,.0f}"
            act = f"<a class='btn sec' href='/horse/{urlname(h.name)}'>Set fee</a>"
        else:
            b = e.booked_to(h)
            now = f"foal by <b>{esc(b.name)}</b> at her side" if b else "open this season"
            act = "" if b else f"<a class=btn href='/breed/{urlname(h.name)}'>Breed</a>"
        return (f"<div class=card><div class=brow><a href='/horse/{urlname(h.name)}'>{portrait(h, 64)}</a><div style='flex:1;min-width:0'>"
                f"<a href='/horse/{urlname(h.name)}' class=bname>{esc(h.name)}</a> <span class=sub>{h.age}yo {sex_word(h)} · {left} season{'s' if left != 1 else ''} left</span>"
                f"<div class=sub>{len(ks)} foal{'s' if len(ks) != 1 else ''} · {sum(k.wins for k in ks)} wins · ${sum(k.earnings for k in ks):,.0f}</div>"
                f"<div>{now}</div>{stud_bars(h)}</div><div>{act}</div></div></div>")
    body = (BREED_MENU("mine") + f"<div class=card><div class=row style='justify-content:space-between'><span>{len(stallions)} stallion{"s" if len(stallions) != 1 else ""} · {len(mares)} broodmare{"s" if len(mares) != 1 else ""}</span>"
            f"</div>"
            + ("" if e.can_breed(ME) else license_offer()) + "</div>")
    def foal_row(f):
        if getattr(f, "unreg", False) and f.age >= 2:                            # old enough to race: register it or let it go
            nm = esc(f.name)
            return (f"<div class=card><div class=brow><a href='/horse/{urlname(f.name)}'>{portrait(f, 64)}</a><div style='flex:1;min-width:0'>"
                    f"<a href='/horse/{urlname(f.name)}' class=bname>{nm}</a> <span class=sub>{f.age}yo {sex_word(f)} · {f.tier} · unregistered</span>"
                    f"<div class=sub>by {esc(f.sire.name)} out of {esc(f.dam.name)}</div>"
                    f"<div class=row style='gap:8px;flex-wrap:wrap;margin-top:6px'>"
                    f"<form method=post action=/register class=inline><input type=hidden name=h value='{nm}'>"
                    f"<button onclick=\"return ask(this,'Register {nm} to race for ${e.REG_FEE:,}?')\">Register to race · ${e.REG_FEE:,}</button></form>"
                    f"<form method=post action=/dump class=inline><input type=hidden name=h value='{nm}'>"
                    f"<button class=sec onclick=\"return ask(this,'Sell {nm} to the house for ${e.UNREG_SALE:,}? Gone for good.')\">Sell to the house · ${e.UNREG_SALE:,}</button></form></div>"
                    f"<div class=sub>Stays in your shed, taking a stall, until you register or sell.</div></div></div></div>")
        wk = (2 - f.age) * c.YEAR - G["day"] % c.YEAR
        return (f"<div class=card><div class=brow><a href='/horse/{urlname(f.name)}'>{portrait(f, 64)}</a><div style='flex:1;min-width:0'>"
                f"<a href='/horse/{urlname(f.name)}' class=bname>{esc(f.name)}</a> <span class=sub>{'weanling' if f.age == 0 else 'yearling'} {'colt' if f.sex == 'm' else 'filly'} · {f.tier}</span>"
                f"<div class=sub>by {esc(f.sire.name)} out of {esc(f.dam.name)}</div>"
                f"<div>{''.join(stat_bar(f.developed[t], f, k.capitalize(), 90, trait=t, goal=f.ceiling(t, 2) - 2.0) for k, t in FOCUS.items())}</div>"
                f"<div class=sub>{'ready to register' if getattr(f, 'unreg', False) else 'joins the barn to race'} in {wk} weeks</div></div></div></div>")
    young = [f for f in e.nursery if f.owner == ME]
    view = qs.get("v") if qs.get("v") in ("mares", "foals") else "stud"
    sort = qs.get("s") if qs.get("s") in ("tier", "foals") else "age"
    pool = {"stud": stallions, "mares": mares, "foals": young}[view]
    pool = sorted(pool, key={"age": lambda h: (h.age, h.name), "tier": lambda h: (TIER_ORDER.get(tier_label(h), 9), h.name),
                             "foals": lambda h: (-len(kids(h)), h.name)}[sort])
    per, n = 10, max(1, -(-len(pool) // 10))
    pg = min(n, max(1, int(qs["p"]) if str(qs.get("p", "")).isdigit() else 1))
    url = lambda v=view, s_=sort, k=1: f"/studs?v={v}&s={s_}&p={k}"
    body += ("<div class=hmenu>" + "".join(f"<a href='{url(v=k)}' class='{'on' if k == view else ''}'>{t} ({len(x)})</a>"
                                           for k, t, x in (("stud", "Stallions", stallions), ("mares", "Broodmares", mares), ("foals", "Foals", young))) + "</div>")
    body += ("<div class=sortrow><span class=sub>Sort by</span>" + "".join(f"<a href='{url(s_=k)}' class='{'on' if k == sort else ''}'>{t}</a>"
             for k, t in (("age", "Age"), ("tier", "Tier"), ("foals", "Foals"))) + "</div>")
    one = foal_row if view == "foals" else row
    empty = {"stud": "No stallions. Retire a colt with a good record to stand him.", "mares": "No broodmares. Retire a mare from racing to breed her.",
             "foals": "No foals yet. Book a broodmare and her foal is born here."}[view]
    body += "".join(one(h) for h in pool[(pg - 1) * per:pg * per]) or f"<p class=sub>{empty}</p>"
    link = lambda k, t: f"<a class=pg href='{url(k=k)}'>{t}</a>" if 1 <= k <= n and k != pg else f"<span class='pg{' on' if k == pg else ''}'>{t}</span>"
    if n > 1:
        body += f"<div class=pager>{link(pg - 1, '&laquo;')}{''.join(link(k, k) for k in range(1, n + 1))}{link(pg + 1, '&raquo;')}</div>"
    return page("Breeding", body)


def breed_page(name):
    """Pick a stallion for one of your mares: your own first (no fee), then every public stud with room in his book."""
    m = next((x for x in G["horses"] if x.name == name and x.owner == ME and x.sex == "f" and x.retired), None)
    if not m:
        return page("Breed", "<p>Not one of your broodmares.</p>")
    why = e.why_not_breed(m, ME, G["horses"])
    def outlook(s):
        (lo, mid, hi), width = e.foal_outlook(s, m, G["horses"])
        tiers = "DCBAS"
        bar = "".join(f"<i class='{'on' if tiers.index(lo) <= k <= tiers.index(hi) else ''}{' mid' if t == mid else ''}'>{t}</i>" for k, t in enumerate(tiers))
        word = "tight" if width < 30 else "moderate" if width < 40 else "wide"
        nk = e.nick(s, m)
        tag = ({"golden": "<span class='nick gold'>&#9733; Golden cross</span>", "good": "<span class=nick>Good nick</span>",
                "neutral": "<span class=nick>Neutral nick</span>", "poor": "<span class='nick poor'>Poor nick</span>"}[nk] if nk else
               f"<form method=post action=/scout class=inl><input type=hidden name=h value='{esc(m.name)}'><input type=hidden name=s value='{esc(s.name)}'>"
               f"<button class=sec onclick=\"return ask(this,'Pay a pedigree scout ${e.SCOUT_FEE:,} to rate this cross?')\">Scout nick ${e.SCOUT_FEE:,}</button></form>")
        return f"<div class=outl><span class=sub>Foals</span><span class=tband>{bar}</span><span class=sub>{word} spread</span>{tag}</div>"
    def row(s, own):
        ks = [k for k in G["horses"] if k.sire is s]
        full = e.covers_sold(s) >= e.BOOK
        fee = 0 if own else e.stud_fee(s)
        close = e.too_close(s, m)
        btn = (f"<span class='btn big off'>{close}</span>" if close else "<span class='btn big off'>book full</span>" if full else "" if why else
               f"<form method=post action=/breed><input type=hidden name=h value='{esc(m.name)}'><input type=hidden name=s value='{esc(s.name)}'>"
               f"<input name=n placeholder='Name the foal' maxlength={_names.MAXLEN} pattern='[A-Za-z ]+' title='Letters and spaces, up to {_names.MAXLEN}' style='width:100%;margin:0 0 4px'>"
               f"<button onclick=\"return ask(this,'Book {m.name} to {s.name}{'' if own else f' for ${fee:,.0f}'}?')\">Book{'' if own else f' ${fee:,.0f}'}</button></form>")
        return (f"<div class=card><div class=brow><a href='/horse/{urlname(s.name)}'>{portrait(s, 64)}</a><div style='flex:1;min-width:0'>"
                f"<a href='/horse/{urlname(s.name)}' class=bname>{esc(s.name)}</a> <span class=sub>{s.tier} · {s.starts}-{s.wins} · ${s.earnings:,.0f}</span>"
                f"<div class=sub>{len(ks)} foals · {sum(k.wins for k in ks)} wins · book {e.covers_sold(s)}/{e.BOOK}</div>"
                f"<div class=money>{'your stallion · no fee' if own else f'${fee:,.0f}'}</div>{stud_bars(s)}</div><div>{btn}</div></div>{outlook(s)}"
                + (f"<div class='kin bad'>He is {close}: the registry won't take this mating.</div>" if close else "")   # inbreeding itself is for the breeder to find out
                + "</div>")
    own = [h for h in mine() if h.retired and h.sex == "m"]
    public = [s for s in e.studs(G["horses"]) if s.owner != ME]
    head = (f"<div class=card><div class=brow>{portrait(m, 64)}<div><span class=bname>{esc(m.name)}</span>"
            f"<div class=sub>{m.age}-year-old broodmare · {c.BREEDING_UNTIL - m.age} seasons left</div></div></div>"
            + (f"<div class=ev>Can't book her: {esc(why)}</div>" if why else "<div class=sub style='margin-top:6px'>Fee paid now; the foal arrives at the year tick.</div>")
            + "</div>")
    body = head + "<h2>Your stallions</h2>" + ("".join(row(s, True) for s in own) or "<p class=sub>None standing.</p>")
    body += "<h2>Public stud book</h2>" + "".join(row(s, False) for s in public)
    return page("Breed", body)


def retired_header(h, own):
    """A retired horse's card, built around life after racing: status, seasons left, foals and the best of them,
    with the race career kept to one line of record, earnings and best time."""
    ks = kids_of(h)
    best = max(ks, key=lambda k: k.earnings, default=None)
    left = c.BREEDING_UNTIL - h.age
    gone = h not in G["horses"]
    if gone:                                                                  # long gone: a name in the stud book, not a stallion for hire
        last = max((r["day"] for r in getattr(h, "results", [])), default=None)
        role = f"In the stud book · raced to Year {c.year_of(last)}" if last is not None else "In the stud book"
        act = ""
    elif h.sex == "m":
        role = f"Standing at stud · fee ${e.stud_fee(h):,.0f} · {e.covers_sold(h)}/{e.BOOK} covers this season"
        act = ""
    else:
        b = e.booked_to(h)
        role = f"Broodmare · in foal to {esc(b.name)}" if b else "Broodmare · open this season"
        act = f"<a class='btn big' href='/breed/{urlname(h.name)}'>Breed</a>" if own and not b else ""
    bars = (f"<div class=hbars><div class=sub>At their best</div>{''.join(stat_bar(h.developed[t], h, k.capitalize(), trait=t) for k, t in FOCUS.items())}{prime_row(h)}</div>")
    return (f"<div class='card hdr'><div class=htop><div class='port t{tier_cls(h)}'><div class=stagelight></div>{portrait(h, 150)}"
            f"<div class='tier {tier_cls(h)} badge'>{tier_label(h)}</div>{trophy(h)}</div>"
            f"<div class=hr><div class=retband>Retired · no longer racing</div><div class=hname>{esc(h.name)}</div><div class=hline>{esc(role)}</div>"
            + ("" if gone else f"<div class=hline>{left} breeding season{'s' if left != 1 else ''} left · owned by {esc(barn_name(h.owner))}</div>")
            + (f"<div class=act>{act}</div>" if act else "") + "</div></div>"
            f"<div class=hbars><div class=tiles><div class=tile><div class=tl>Foals</div><div class=tv>{len(ks)}</div><div class=sub>{sum(k.wins for k in ks)} wins</div></div>"
            f"<div class=tile><div class=tl>Foal earnings</div><div class=tv>${sum(k.earnings for k in ks):,.0f}</div>"
            f"<div class=sub>{"best: <a href='/horse/" + urlname(best.name) + "'>" + esc(best.name) + '</a>' if best else 'none yet'}</div></div>"
            f"<div class=kv><div><span>Raced</span><b>{h.starts}-{h.wins}</b></div><div><span>Earned</span><b>${h.earnings:,.0f}</b></div>"
            f"<div><span>Best time</span><b>{best_time(h)}</b></div></div></div></div>{bars}</div>")


def stud_bars(h):
    """A stallion's four bars at his best, compact: what a mare's owner is paying for. Shown for every stud."""
    return "<div class=sbars>" + "".join(stat_bar(h.developed[t], h, k.capitalize(), trait=t) for k, t in FOCUS.items()) + "</div>"


BREED_MENU = lambda on: ("<div class=hmenu>" + "".join(f"<a href={href} class='{'on' if on == k else ''}'>{label}</a>"
                                                       for k, href, label in (("mine", "/studs", "Your breeding barn"), ("book", "/studbook", "Public stud book"))) + "</div>")


def studs_page(qs=None):
    """The public stud book: every standing stallion as a barn card with his book and fee, ten to a page."""
    all_ = e.studs(G["horses"])
    per, n = 10, max(1, -(-len(all_) // 10))
    try:
        pg = min(n, max(1, int((qs or {}).get("p", 1))))
    except ValueError:
        pg = 1
    body = ""
    for s in all_[(pg - 1) * per:pg * per]:
        kids = [k for k in G["horses"] if k.sire is s]
        body += (horse_card(s) + f"<div class=sub style='margin:-6px 0 12px 4px'>{'<b>Yours</b> · ' if s.owner == ME else ''}{barn_tag(s.owner, 14)} · "
                 f"{len(kids)} foals, {sum(k.wins for k in kids)} wins · book {e.covers_sold(s)}/{e.BOOK} · fee <b>${e.stud_fee(s):,.0f}</b></div>")
    link = lambda k, t: f"<a class=pg href=/studbook?p={k}>{t}</a>" if 1 <= k <= n and k != pg else f"<span class='pg{' on' if k == pg else ''}'>{t}</span>"
    nav = f"<div class=pager>{link(pg - 1, '&laquo;')}{''.join(link(k, k) for k in range(1, n + 1))}{link(pg + 1, '&raquo;')}</div>"
    return page("Stud book", BREED_MENU("book") + f"<div class=calm>{body}</div>" + nav + f"<p class=sub>Book a mare from her own page. A fee is the price of a cover.</p>")


def trainers_page():
    body = ""
    for t in sorted(c.ROSTER, key=lambda t: -t.earnings / max(1, t.starts)):
        perk = f"+ {t.perk}" if t.perk != "none" else ""
        quirk = f"− {t.quirk}" if t.quirk != "none" else ""
        yours = " · <b>your barn</b>" if c.BARN_TRAINER.get(ME) is t else ""
        body += (f"<div class=card><b>{esc(t.name)}</b> <span class=sub>{t.style} · {t.years}y · takes {t.cut:.0%} · {t.stalls - t.horses}/{t.stalls} stalls free{yours}</span>"
                 f"<div class=sub>{esc(c.STYLES[t.style][0])}</div><div class=sub>{esc(perk)} {esc(quirk)}</div>"
                 f"<div>record {t.record()}</div>"
                 f"<form method=post action=/hire class=inline><input type=hidden name=t value='{esc(t.name)}'>"
                 f"<button class=sec>Hire for the barn</button></form></div>")
    return page("Trainers", body)


def stakes_page(qs=None):
    """Stakes & Crown: the Crown standings (who's in line for an invitation), the season's stakes in order, and the
    honour roll of champions. Nominating happens on a horse's page."""
    day = G["day"]
    wk = day % c.YEAR
    tag = {"classic": "Classic", "memorial": "Memorial", "trophy": "Trophy", "final": "The Crown", "leg": "Sire Stakes leg",
           "opener": "Season opener", "invitational": "Invitational", "signature": "Signature stake"}
    # Crown standings: the ten top earners of the season are invited to each division's championship
    stand = ""
    for (g, sx), div in sk.DIVISION.items():
        final = next((x for x in sk.CALENDAR if x.kind == "final" and x.group == g and x.sex == sx), None)
        if not final:
            continue
        pool = sorted((h for h in G["horses"] if final.eligible(h) and sk.season_earnings(h, day) > 0),
                      key=lambda h: -sk.season_earnings(h, day))
        top = "".join(f"<tr{brow(h.owner)}><td>{k + 1}</td><td><a href='/horse/{urlname(h.name)}'>{esc(h.name)}</a></td>"
                      f"<td class=sbarn>{barn_tag(h.owner)}</td><td class=money>${sk.season_earnings(h, day):,.0f}</td></tr>"
                      for k, h in enumerate(pool[:5]))
        champ = "winner " + esc(final.result[0].name) if final.result else f"week {final.week + 1} · ${final.purse:,.0f}"
        stand += (f"<div class='card crown'><div class=row style='justify-content:space-between'><b>{div}</b><span class=sub>{champ}</span></div>"
                  f"<table><tr><th>#</th><th>Horse</th><th>Barn</th><th>Season</th></tr>{top or '<tr><td colspan=4 class=sub>No earners yet</td></tr>'}</table></div>")
    # the season's stakes, week by week: what's coming in cards, what's been run folded away underneath
    weeks = {}
    for x in sorted(sk.CALENDAR, key=lambda x: (x.week, -x.purse)):
        weeks.setdefault(x.week, []).append(x)
    def stake(x):
        fee = x.fee(day)
        yours = ", ".join(h.name for h in x.noms if h.owner == ME)
        kind = getattr(x, "kind", "trophy")
        status = (f"<span class='sk won'>&#127942; <a href=/horse/{urlname(x.result[0].name)}>{esc(x.result[0].name)}</a></span>" if x.result
                  else "<span class=sk>not run</span>" if x.result == [] else "<span class='sk inv'>by invitation</span>" if x.kind == "final"
                  else "<span class=sk>closed</span>" if fee is None else f"<span class='sk nom'>nominate ${fee:,.0f}</span>")
        sp = sponsor_of(x)
        return (f"<div class='skrow k{kind}{' mine' if yours else ''}'><div class=skl><b>{esc(getattr(x, 'title', None) or x.name)}</b>"
                f"<span class=skdiv>{tag.get(kind, 'Stakes')} · {sk.DIVISION[(x.group, x.sex)]}{f' · <span class=spon>presented by {barn_tag(sp, 14)}</span>' if sp is not None else ''}</span>"
                + (f"<span class=skyou>Yours: {esc(yours)}</span>" if yours else "") + f"</div><div class=skr><b class=money>${x.purse:,.0f}</b>{status}</div></div>")
    ahead = "".join(f"<div class=skwk><div class=skwh>Week {w + 1}<span>{'this week' if w == wk else f'in {w - wk} wk' + ('s' if w - wk != 1 else '')}</span></div>"
                    + "".join(stake(x) for x in xs) + "</div>" for w, xs in weeks.items() if w >= wk)
    past = "".join(f"<div class=skwk><div class=skwh>Week {w + 1}</div>" + "".join(stake(x) for x in xs) + "</div>" for w, xs in weeks.items() if w < wk)
    rows = (ahead or "<p class=sub>The season's stakes are all run.</p>") + (
        f"<details class=skpast><summary>Run so far ({sum(len(xs) for w, xs in weeks.items() if w < wk)})</summary>{past}</details>" if past else "")
    years = sorted(sk.CHAMPIONS, reverse=True)                    # one year at a time, newest first; or all of them
    pick = (qs or {}).get("year", str(years[0]) if years else "")
    shown = years if pick == "all" else [y for y in years if str(y) == pick] or years[:1]
    k = years.index(shown[0]) if shown and pick != "all" else -1
    nav = ("<div class=rnav>"
           + (f"<a class='btn sec' href='/stakes?year={years[k + 1]}#champs'>‹ Earlier</a>" if 0 <= k < len(years) - 1 else "<span class='btn sec off'>‹ Earlier</span>")
           + "<form method=get action=/stakes class=inline><select name=year onchange='this.form.submit()'>"
           + f"<option value=all{' selected' if pick == 'all' else ''}>All years</option>"
           + "".join(f"<option value={y}{' selected' if pick != 'all' and y == shown[0] else ''}>Year {y}</option>" for y in years)
           + "</select></form>"
           + (f"<a class='btn sec' href='/stakes?year={years[k - 1]}#champs'>Later ›</a>" if k > 0 else "<span class='btn sec off'>Later ›</span>")
           + "</div>") if years else ""
    honour = nav + "".join(f"<div class=card><b>Year {y} champions</b><table>" + "".join(
        f"<tr><td>{div}</td><td><a href=/horse/{n}>{esc(n)}</a></td></tr>" for div, n in sk.CHAMPIONS[y].items()) + "</table></div>"
        for y in shown)
    body = ("<p class=sub>The Crown closes the season: the ten top earners in each division are invited to its championship, "
            "and the winner is that year's champion. One title per division per year.</p>"
            + sponsor_section() + picks_section() +
            "<h2>Crown standings</h2>" + stand +
            "<h2>This season's stakes</h2>" + rows + "<h2 id=champs>Champions</h2>" + (honour or "<p class=sub>The first Crowns are run in weeks 50 to 52.</p>"))
    return page("Stakes & Crown", body)


PP_CSS = """
.pgm{background:#f4f1e8;color:#111;border-radius:4px;margin:8px 0;font-family:'Barlow Semi Condensed',Arial Narrow,sans-serif;overflow:hidden}
.pgm summary{list-style:none;cursor:pointer}.pgm summary::-webkit-details-marker{display:none}
.pgh{display:flex;gap:8px;align-items:stretch;background:#111;color:#fff;padding:6px 8px}
.pgn{font-size:34px;font-weight:800;line-height:1;min-width:30px;text-align:center;align-self:center}
.pgt{flex:1;min-width:0;font-size:13px;font-weight:600;line-height:1.25}.pgt b{font-size:16px;letter-spacing:.3px}
.pgp{text-align:right;font-size:12px;line-height:1.25;white-space:nowrap}.pgp b{font-size:16px}
.pgpick{font-size:12px;padding:5px 8px;border-bottom:2px solid #111;background:#e9e4d6}
.pgr{border-bottom:2px solid #111;padding:6px 8px 4px}.pgr.mine{background:#fbe9c6}
.pgtop{display:flex;gap:8px;align-items:flex-start}
.pgpp{display:flex;flex-direction:column;align-items:center;gap:2px;min-width:38px}
.pgml{font-size:13px;font-weight:700}.pgcl{font-size:24px;font-weight:800;width:36px;height:36px;display:flex;align-items:center;justify-content:center;border:1px solid #111}
.pgid{flex:1;min-width:0}.pgname{font-size:19px;font-weight:800;text-transform:uppercase;line-height:1.05}.pgname a{color:#111;text-decoration:none}
.pgped,.pgown{font-size:13px;line-height:1.35;color:#222;font-weight:500}.pgtag{font-size:10px;font-weight:700;padding:0 4px;border-radius:2px;background:#111;color:#fff;margin-left:4px;vertical-align:2px}.pgtag.pl{background:#1e4fb5}
.pgcar{width:auto!important;font-size:13px;font-weight:500;border-collapse:collapse;margin-top:4px;font-variant-numeric:tabular-nums}.pgcar td{padding:0 10px 0 0!important;border:0!important;white-space:nowrap}.pgcar td:first-child{font-weight:700}
.pglines{margin-top:6px}.pglines table{border-collapse:collapse;font-size:13px;font-weight:500;font-variant-numeric:tabular-nums;white-space:nowrap;width:100%;table-layout:fixed}.pglines td{overflow:hidden;text-overflow:ellipsis}
.pglines td{padding:3px 6px 1px 0;border-top:1px solid #0002}.pglines .w{font-weight:800}.pglines sup{font-size:9px}.pglines .pph td{font-weight:700;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#555;border-top:0}.pglines .ppc{max-width:130px;overflow:hidden;text-overflow:ellipsis}.pglines .ppt td{border-top:0;padding:0 0 4px;font-size:12px;font-style:italic;color:#555;white-space:normal}.pglines .pptk{font-style:normal;font-weight:700;color:#333}
.pgclaim{margin-top:4px}.pgfoot{font-size:13px;padding:6px 8px;background:#111;color:#e9e4d6;line-height:1.4}
.pgsec{font-family:'Barlow Semi Condensed',sans-serif;font-weight:700;letter-spacing:.5px;text-transform:uppercase;margin:14px 0 4px;color:var(--ink2)}
"""

COAT_ABBR = {"bay": "b", "brown": "br", "black": "blk", "chestnut": "ch", "grey": "gr", "gray": "gr"}


def _lengths(b):
    """Lengths behind as a program prints them: whole lengths and a quarter fraction."""
    q = round(b * 4) / 4
    w, f = int(q), q - int(q)
    return (str(w) if w else "") + {0.25: "¼", 0.5: "½", 0.75: "¾"}.get(f, "") or "ns"


def _calls(r):
    """Positions at the quarter, half, three-quarters, stretch and finish, from the replay where it's still kept."""
    st_ = c.STORIES.get(r.get("race_id"))
    me = next((x for x in st_["horses"] if x["name"] == r.get("name_")), None) if st_ else None
    if not me:
        return None
    out = []
    for k in (2, 3, 4, 5, 6):
        pos = 1 + sum(1 for x in st_["horses"] if x["behind"][k] < me["behind"][k] or (x["behind"][k] == me["behind"][k] and x["place"] < me["place"]))
        out.append((pos, me["behind"][k]))
    return out


TRACK_WORD = {"mile": "Mile track", "half": "Half-mile track"}


def pp_lines(h, n=3):
    """A horse's last few starts for the program, kept short: week, class, purse, post, stretch call, finish, time and the
    trip in a word or two."""
    nth = lambda p: f"{p}{'th' if 10 <= p % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(p % 10, 'th')}"
    rows = ""
    for r in getattr(h, "results", [])[-n:][::-1]:                     # a first-time starter has no history yet
        calls = _calls(dict(r, name_=h.name))
        st_ = (f"{calls[3][0]}{f'<sup>{_lengths(calls[3][1])}</sup>' if calls[3][0] > 1 and calls[3][1] > 0 else ''}") if calls else "—"
        fin = calls[4] if calls else (r["place"], 0)
        trip = r["trip"].split(", ", 1)[1] if ", " in r["trip"] else ""
        cls = "Clm " + r["race"].split("$", 1)[1] if " Claiming $" in r["race"] else r["race"]   # the program's short form: Clm 25,000
        rows += (f"<tr><td>W{r['day'] % c.YEAR + 1}</td><td class=ppc title='{esc(r['race'])}'>{esc(cls)}</td><td>{r['purse']:,}</td>"
                 f"<td>{r['trip'].split(',')[0].replace('post ', '') if r['trip'].startswith('post') else ''}</td><td>{st_}</td>"
                 f"<td class={'w' if r['place'] == 1 else ''}>{nth(r['place'])}{f'<sup>{_lengths(fin[1])}</sup>' if r['place'] > 1 and fin[1] > 0 else ''}</td>"
                 f"<td>{c.mile_time(r['time'])}</td></tr>"
                 + f"<tr class=ppt><td></td><td colspan=6><b class=pptk>{TRACK_WORD.get(r.get('track'), '')}</b>"   # times on a half are slower: say which
                 f"{' · ' if trip and r.get('track') in TRACK_WORD else ''}{esc(trip)}</td></tr>")
    if not rows:
        return "<div class=pgped>Unraced.</div>"
    return ("<div class=pglines><table><colgroup><col style='width:2.2em'><col><col style='width:4.6em'><col style='width:1.8em'>"
            "<col style='width:2.6em'><col style='width:3.4em'><col style='width:3.6em'></colgroup><tr class=pph><td>Wk</td><td>Class</td><td>Purse</td><td>PP</td><td>Str</td><td>Fin</td><td>Time</td></tr>"
            + rows + "</table></div>")


def career_box(h):
    yrs = getattr(h, "seasons", {}) or {}
    now = c.year_of(G["day"])
    life = [sum(r[i] for r in yrs.values()) for i in range(5)] + [min((r[5] for r in yrs.values()), default=999)]
    line = lambda lbl, r: (f"<tr><td>{lbl}</td><td>{r[0]}</td><td>{r[1]}-{r[2]}-{r[3]}</td><td>${r[4]:,.0f}</td>"
                           f"<td>{c.mile_time(r[5]) if r[5] < 999 else ''}</td></tr>")
    rows = line("Life", life) + "".join(line(f"Y{y}", yrs[y]) for y in (now, now - 1) if y in yrs)
    return f"<table class=pgcar><tr style='color:#555'><td></td><td>St</td><td>W-P-S</td><td>Earned</td><td>Best</td></tr>{rows}</table>"


def claim_tag(h):
    """The price a horse can be claimed for tonight, or 0: drawn into a claiming card (the posted program), or entered
    in a claimer before the draw. Claims stay open until post time."""
    for r_ in (c.CARD.get("races", []) if c.CARD.get("day") == G["day"] else []):
        if h in r_["field"]:
            return r_["key"][4]
    o = getattr(h, "order", None)
    return o[1] if isinstance(o, tuple) and o[0] == "claim" else 0


def program_entry(h, tag, odds, drawn, room):
    post = getattr(h, "post", 0) if drawn else 0
    coat, _ = looks(h)
    sire, dam = getattr(h, "sire", None), getattr(h, "dam", None)
    damsire = getattr(dam, "sire", None) if dam else None
    ped = (f"{esc(sire.name)} – {esc(dam.name)}{' – ' + esc(damsire.name) if damsire else ''}" if sire and dam else "foundation stock")
    breeder = getattr(h, "breeder", None)
    tagl = "<span class=pgtag>YOU</span>" if h.owner == ME else "<span class='pgtag pl'>PLAYER</span>" if h.owner in c.HUMAN else ""
    act = ""
    if tag and h.owner != ME and claim_tag(h):                           # claims stay open until post time
        if c.CLAIMS.get(h.id) == ME:
            act = (f"<form method=post action=/claim class='inline pgclaim'><input type=hidden name=h value='{esc(h.name)}'><input type=hidden name=undo value=1>"
                   f"<button class=sec>Withdraw claim</button></form>")
        elif e.cash.get(ME, 0) >= tag and room > 0 and h.id not in c.CLAIMS:
            act = (f"<form method=post action=/claim class='inline pgclaim'><input type=hidden name=h value='{esc(h.name)}'>"
                   f"<button class=sec onclick=\"return ask(this,'Claim {esc(h.name)} for ${tag:,}? Binding if it races.')\">Claim ${tag:,}</button></form>")
    cloth = (f"<div class=pgcl style='background:var(--p{post});color:{'#111' if post in (3, 6, 8, 10, 11) else '#fff'}'>{post}</div>" if post else "")
    ml = f"<div class=pgml>{'%d/%d' % odds[h.id]}</div>" if h.id in odds else ""
    return (f"<div class='pgr{' mine' if h.owner == ME else ''}'><div class=pgtop><div class=pgpp>{ml}{cloth}</div><div class=pgid>"
            f"<div class=pgname><a href='/horse/{urlname(h.name)}'>{esc(h.name)}</a>{tagl}</div>"
            f"<div class=pgped>{COAT_ABBR.get(coat, coat)} {sex_abbr(h)} {h.age} · {ped}</div>"
            + (f"<div class=pgown>Driver – {silks(drv)} <b>{esc(drv)}</b></div>" if (drv := next((r_["drivers"].get(h.id) for r_ in c.CARD.get("races", []) if h.id in r_.get("drivers", {})), None)) and drawn else "")
            + ("" if drawn else "<div class='pgown sub'>Post and driver drawn at 8 PM</div>")
            + f"<div class=pgown>Owner/Trainer – <b>{barn_tag(h.owner, 14)}</b>{' · Breeder – ' + esc(barn_name(breeder)) if isinstance(breeder, int) else ''}</div>"
            f"{career_box(h)}</div></div>{pp_lines(h)}{act}</div>")


def program_races():
    """Tonight's races as (number, key, venue, field, odds), numbered through each venue's card. Before the draw: what's
    entered so far, by class and track, unnumbered."""
    if c.CARD.get("day") == G["day"]:
        rs = sorted(c.CARD["races"], key=lambda r: (r["v"]["name"], r["key"][5], str(r["key"][0]), -r["key"][3]))
        out, n = [], {}
        for r in rs:
            n[r["v"]["name"]] = n.get(r["v"]["name"], 0) + 1
            out.append((n[r["v"]["name"]], r["key"], r["v"]["name"], r["field"], r["odds"]))
        return True, out
    by = {}
    for h in G["horses"]:
        o = getattr(h, "order", None)
        if not h.retired and isinstance(o, tuple) and o[0] in ("enter", "claim"):
            track = o[4] if o[0] == "enter" else getattr(h, "ship", None) or "mile"
            by.setdefault(c.entry(h) + (track,), []).append(h)
    out = []
    for k, f in sorted(by.items(), key=lambda kv: (kv[0][5], str(kv[0][0]), -kv[0][3])):
        n = -(-len(f) // c.FIELD[k[5]])                                   # more than the gate holds: divisions, as the draw will split them
        f = sorted(f, key=lambda h: -h.est)
        out += [(0, k, f"Division {d + 1} of {n}" if n > 1 else "", f[d::n], {}) for d in range(n)]   # dealt round, so each is a fair race
    return False, out


def program_race_body(drawn, key, field, odds):
    group, sex, name, purse, tag, track = key
    room = e.stalls(ME) - e.barn_size.get(ME, 0) - sum(1 for b in c.CLAIMS.values() if b == ME)
    body = ""
    if drawn and len(field) > 1:
        score = lambda h: h.est + 1.5 * sum(h.recent[-5:]) - 0.4 * getattr(h, "post", 5)   # public info only: often right, not always
        best = max(field, key=score)
        why = ("best recent form" if sum(best.recent[-5:]) and sum(best.recent[-5:]) >= max(sum(h.recent[-5:]) for h in field)
               else "tops the field on ratings" if best.est >= max(h.est for h in field) else "the pick of an open field")
        body += (f"<div class=pgpick>Handicapper's pick: <b>{esc(best.name)}</b>, {why}"
                 f"{', from an inside post' if getattr(best, 'post', 9) <= 2 else ''}.</div>")
    body += "".join(program_entry(h, tag, odds, drawn, room) for h in sorted(field, key=lambda h: getattr(h, "post", 0)))
    if drawn and len(field) > 1:
        winp = lambda h: h.wins / h.starts if h.starts else 0
        last = lambda h: h.results[-1]["time"] if getattr(h, "results", None) else 999
        yr = c.year_of(G["day"])
        earn = lambda h: (getattr(h, "seasons", {}) or {}).get(yr, [0] * 5)[4]
        hw, bl, te = max(field, key=winp), min(field, key=last), max(field, key=earn)
        body += (f"<div class=pgfoot>Highest win %: <b>{esc(hw.name)} {winp(hw):.0%}</b> · Best last-race time: <b>{esc(bl.name)}</b>"
                 f" · Top earner this year: <b>{esc(te.name)} ${earn(te):,.0f}</b></div>")
    return body


def giga_horse():
    """Barn 0's ageless horse: bred far above any foundation stock, an S+ 3-year-old that never ages (the owner's own)."""
    for shift in (1.2, 1.5, 2.0, 3.0):
        h = sim.founder({t: shift for t in c.RACE_TRAITS})
        h.age, h.owner, h.ageless = 3, ADMIN, True
        c.init_public(h)
        if tier_label(h) == "S+":
            break
    c.assign(h, c.BARN_TRAINER.get(ADMIN, c.HOUSE)) or c.assign(h, c.HOUSE)
    G["horses"].append(h)
    e.barn_size[ADMIN] = e.barn_size.get(ADMIN, 0) + 1
    e.settled[h.id] = (0, 0)
    return h


def vlook(name):
    """A track's identity by its name: (primary, accent, font, motto, badge), or None for a race with no track."""
    v = next((v for v in c.VENUES if v["name"] == name), None)
    return TI.look(v["id"]) if v else None


def program_race(num, key, venue, field, odds, drawn, open_):
    group, sex, name, purse, tag, track = key
    title = f"{c.race_title(group, name)}{' F&amp;M' if sex == 'F&M' else ''}"
    rival = sorted({barn_name(h.owner) for h in field if h.owner in c.HUMAN and h.owner != ME})
    vs = f" · vs {esc(', '.join(rival))}" if rival and any(h.owner == ME for h in field) else ""
    lane = any(v.get("passing") and v["name"] == venue for v in c.VENUES)
    vd = next((v for v in c.VENUES if v["name"] == venue), None)
    purse = c.venue_purse(vd, purse) if vd else purse                      # what this race pays at this track tonight
    lk = vlook(venue)
    tk_style = f' style="--tp:{lk[0]};--ta:{lk[1]}"' if lk else ""
    tk_name = f'<span class=tkn style="font-family:{lk[2]}">{esc(venue)}</span><br>' if lk else ""
    head = (f"<summary class='pgh{' tk' if lk else ''}'{tk_style}><div class=pgn>{num or '·'}</div>"
            + (f"<img class=tkb src={lk[4]} width=40 height=40 alt=''>" if lk else "")
            + f"<div class=pgt>{tk_name}"
            f"TROT – {'1 MILE' if track == 'mile' else '½ MILE TRACK, 1 MILE'}{' · PASSING LANE' if lane else ''}<br><b>{title}</b>{vs}</div>"
            f"<div class=pgp>PURSE<br><b>${purse:,}</b><br>{len(field)} {'starters' if drawn else 'in'}</div></summary>")
    inner = program_race_body(drawn, key, field, odds) if open_ else f"<div class=pgload data-k='{esc(repr((key, venue, num)))}'>Loading…</div>"
    return f"<details class=pgm{' open' if open_ else ''}>{head}{inner}</details>"


def program_page(qs=None):
    """Tonight's program, laid out like a real past-performance program (drawn at 8 PM the night before, so it's up all
    day; before the first draw, a preview of what's entered): race numbers, posts, morning lines, career boxes, five past performances with
    positions at each call, the handicapper's pick. Your races open first; the rest are folded and load when opened."""
    qs = qs or {}
    drawn, races = program_races()
    if "k" in qs:                                                      # one folded race's entries, fetched when it's opened
        r = next((r for r in races if repr((r[1], r[2], r[0])) == qs["k"]), None)
        return program_race_body(drawn, r[1], r[3], r[4]) if r else "<div class=pgpick>This race has changed. Reload the program.</div>"
    day = G["day"]
    head = (f"<style>{PP_CSS}</style><div class=proghead><span>Year {c.year_of(day)}, week {day % c.YEAR + 1}</span><span>"
            + ("Final program · post time 8:00 PM" if drawn else "Preview · the draw posts at 8:00 PM for tomorrow") + "</span></div>")
    note = "" if drawn else ("<p class=sub>Who's entered so far. At the 8 PM draw fields are filled out and split, and race numbers, posts and "
                             "morning lines go up for tomorrow night. A claim is binding if the horse races; claims stay open until post time.</p>")
    mine_ = [r for r in races if any(h.owner == ME for h in r[3])]
    tracks = sorted({r[2] for r in races if drawn and r[2]})               # the posted card, track by track, as a spectator buys it
    pick = qs.get("track", "")
    chips = ("<div class=fchips>" + f"<a href=/program class='{'' if pick in tracks else 'on'}'>Your races</a>"
             + "".join(f"<a href='/program?track={quote(t)}' class='{'on' if pick == t else ''}'>{esc(t)}</a>" for t in tracks) + "</div>") if tracks else ""
    body = head + note + chips
    if pick in tracks:                                                     # one track's whole card, race 1 onward
        card_ = sorted((r for r in races if r[2] == pick), key=lambda r: r[0])
        v = next(v for v in c.VENUES if v["name"] == pick)
        body += (f"<div class=pgsec>{esc(pick)} · {len(card_)} races · {'mile' if v['track'] == 'mile' else 'half-mile'}"
                 f"{' · passing lane' if v.get('passing') else ''}</div><p class=sub>{esc(v['about'])}</p>"
                 + "".join(program_race(*r, drawn, False) for r in card_))
        mine_, races = [], []                                              # nothing else on this page
    if mine_:
        body += "<div class=pgsec>Your races</div>" + "".join(program_race(*r, drawn, True) for r in mine_)
    for track, title in (("mile", "Mile track"), ("half", "Half-mile track")):
        rest_ = [r for r in races if r not in mine_ and r[1][5] == track]
        if rest_:
            body += f"<div class=pgsec>{title} · {len(rest_)} race{'s' if len(rest_) != 1 else ''}</div>" + "".join(program_race(*r, drawn, False) for r in rest_)
    if not races and pick not in tracks:
        body += "<p class=sub>Nothing entered yet tonight.</p>"
    body += ("<script>document.querySelectorAll('details.pgm').forEach(d=>d.addEventListener('toggle',()=>{const l=d.querySelector('.pgload');"
             "if(d.open&&l&&!l.dataset.go){l.dataset.go=1;fetch('/program?k='+encodeURIComponent(l.dataset.k)).then(r=>r.text()).then(t=>l.outerHTML=t)}}))</script>")
    return page("Tonight's program", body)


def claims_page(qs=None):
    """Tonight's claiming program, laid out like a race programme: each claiming race with its entries in program
    order, saddle cloth, the horse at a glance (age, sex, color, breeding, trainer, owner), the morning line, the last
    three starts, record and best time, and a Claim button good until post time."""
    cards = c.claiming_cards(G["horses"])
    room = e.stalls(ME) - e.barn_size.get(ME, 0) - sum(1 for b in c.CLAIMS.values() if b == ME)
    mine_in = sum(1 for b in c.CLAIMS.values() if b == ME)
    head = (f"<div class=card><div class=row style='justify-content:space-between;gap:8px'><span>Year {c.year_of(G['day'])}, week {G['day'] % c.YEAR + 1} · "
            f"{len(cards)} claiming race{'s' if len(cards) != 1 else ''} tonight</span><span class=sub>{mine_in} claim{'s' if mine_in != 1 else ''} in · "
            f"{max(0, room)} stall{'s' if room != 1 else ''} free</span></div>"
            "<div class=sub>A claim is binding: if the horse races, it's yours for the tag whatever the result, and its purse goes to the old owner. "
            "Claims can be made or withdrawn until post time. Fields may be filled out at post, and posts are drawn then.</div></div>")
    qs = qs or {}
    AGE = {"2": "2YO", "3": "3YO", "aged": "Aged"}
    age = qs.get("age", "all")
    order = sorted(cards, key=lambda k: (["2", "3", "aged"].index(k[0]) if k[0] in AGE else 9, k[4], k[5], k[1]))   # by race: age class, then tag
    shown = [k for k in order if age == "all" or k[0] == age]
    body = head + "<div class=fchips>" + "".join(
        f"<a href='/claims?age={a}' class='{'on' if age == a else ''}'>{l} ({sum(1 for k in order if a == 'all' or k[0] == a)})</a>"
        for a, l in (("all", "All"), ("2", "2YO"), ("3", "3YO"), ("aged", "Aged"))) + "</div>"
    body += "<div class=fchips>" + "".join(                    # jump straight to a race
        f"<a href='#r{n}'>{esc(c.race_title(k[0], k[2]))}{' F&amp;M' if k[1] == 'F&M' else ''} · {'mile' if k[5] == 'mile' else 'half'}</a>"
        for n, k in enumerate(shown)) + "</div>"
    order = shown
    pads = ["#d23b2a", "#1e4fb5", "#f3f3ef", "#2e7d32", "#111111", "#f2c230", "#e75480", "#8a8f99", "#7b3fa0", "#5ab7e6", "#2e8b8b", "#c05020"]
    dark = {3, 6, 10}
    for n, key in enumerate(order):
        group, sex, name, purse, tag, track = key
        field = sorted(cards[key], key=lambda h: -h.est)
        line = c.tote_odds(field) if len(field) > 1 else {}
        rows = ""
        for i, h in enumerate(field, 1):
            last3 = " ".join(f"<span class='lp{' lpwin' if r['place'] == 1 else ''}'>{r['place']}</span>" for r in h.results[-3:][::-1]) or "<span class=sub>unraced</span>"
            coat, marking = looks(h)
            mine_claim = c.CLAIMS.get(h.id) == ME
            if h.owner == ME:
                act = "<span class=sub>yours</span>"
            elif mine_claim:
                act = (f"<form method=post action=/claim class=inline><input type=hidden name=h value='{esc(h.name)}'><input type=hidden name=undo value=1>"
                       f"<button class=sec>Withdraw claim</button></form><div class=claimed>Claim in</div>")
            elif e.cash.get(ME, 0) < tag or room <= 0:
                act = f"<span class=sub>{'not enough cash' if e.cash.get(ME, 0) < tag else 'no stall free'}</span>"
            else:
                act = (f"<form method=post action=/claim class=inline><input type=hidden name=h value='{esc(h.name)}'>"
                       f"<button onclick=\"return ask(this,'Claim {esc(h.name)} for ${tag:,}? Binding if it races.')\">Claim {c.clm_name(tag)[3:]}</button></form>")
            ml = "%d-%d" % line[h.id] if h.id in line else "—"
            rows += (f"<div class='pg{' mine' if mine_claim else ''}'><div class=pgnum style='background:{pads[(i - 1) % 12]};color:{'#111' if i in dark else '#fff'}'>{i}</div>"
                     f"<div class=pgmain><div class=pgname><a href='/horse/{urlname(h.name)}'>{esc(h.name)}</a> <span class=ml>{ml}</span></div>"
                     f"<div class=pgline>{h.age}yo {coat} {sex_word(h)} · "
                     f"by {esc(h.sire.name) if h.sire else 'foundation stock'} out of {esc(h.dam.name) if h.dam else 'foundation stock'}</div>"
                     f"<div class=pgline>O: {esc(barn_name(h.owner))} · {tier_label(h)} · Prime {sim.style_of(h)}</div>"
                     f"<div class=pgline>Last 3: {last3} · {h.starts}-{h.wins}-{h.places}-{h.shows} · ${h.earnings:,.0f} · best {best_time(h)}</div></div>"
                     f"<div class=pgact>{act}</div></div>")
        body += (f"<div class='card prog' id=r{n}><div class=proghd><b>{esc(c.race_title(group, name))}{' · Fillies &amp; mares' if sex == 'F&M' else ''}</b>"
                 f"<span>{'mile' if track == 'mile' else 'half-mile'} · purse ${purse:,} · claiming ${tag:,}</span></div>{rows}</div>")
    if not cards:
        body += "<p class=sub>No claiming races drawn for tonight.</p>"
    return page("Claiming", body)


BARN_ART = ["starter", "working", "shed", "farm", "estate"]
BARN_BLURB = ["A humble start: a shed, a few stalls and a lot of hope.", "A proper working barn. Room to run a real string.",
              "The Breeder's License: your stock can stand at stud and raise foals of your own.", "An established farm. Barns, pasture, a name people know.",
              "The estate. You're the king now."]


def upgrade_page():
    """Barn upgrades as milestones: each building a step up the ladder, built ones lit in their metal, the next one for sale,
    the rest still ahead."""
    lvl = e.level[ME]
    body = "<div class=upl>"
    for i, (name, n, breed, price, head) in enumerate(e.LEVELS):
        st = "built" if i <= lvl else "next" if i == lvl + 1 else "ahead"
        perks = [f"{n} stalls", f"{e.GROOM[i]} groom{'s' if e.GROOM[i] != 1 else ''}/wk"] + ([f"breeding barn of {head}"] if breed else [])
        act = ("<span class=upst>&#10003; Built</span>" if st == "built" else
               f"<form method=post action=/upgrade><button onclick=\"return ask(this,'{'Buy' if 'license' in name else 'Build'} the {name} for ${price:,}?')\">{'Buy' if 'license' in name else 'Build'} · ${price:,}</button></form>"
               if st == "next" else f"<span class=upst>${price:,}</span>")
        body += (f"<div class='upc up{i} {st}'><img src=/mock/brand/barns/{BARN_ART[i]}.png width=96 height=96 alt=''>"
                 f"<div class=upm><b>{esc(' '.join(w[0].upper() + w[1:] for w in name.split()))}</b><span class=sub>{BARN_BLURB[i]}</span>"
                 f"<div class=upk>{''.join(f'<span>{p}</span>' for p in perks)}</div></div><div class=upa>{act}</div></div>")
    return page("Barn upgrades", market_tabs("upgrade") + body + "</div>")


REVEAL_CSS = """
body.reveal{background:#0f0e0c;color:#eee;overflow-x:clip}
.stage{position:relative;max-width:420px;margin:0 auto;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px}
.pack{position:relative;width:230px;height:300px;border-radius:16px;background:linear-gradient(160deg,#2a2622,#141210);box-shadow:0 20px 60px #000c;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:transform .3s}
.pack .sil img{filter:brightness(0);border-color:#1d1a17 !important;background:#1d1a17}
.pack .hint{position:absolute;bottom:14px;font-size:13px;color:#aaa;letter-spacing:.08em;text-transform:uppercase}
.pack.shake{animation:shake .7s ease-in-out}
@keyframes shake{0%,100%{transform:rotate(0)}20%{transform:rotate(-4deg) scale(1.02)}40%{transform:rotate(4deg) scale(1.04)}60%{transform:rotate(-5deg) scale(1.06)}80%{transform:rotate(5deg) scale(1.08)}}
.burst{position:absolute;inset:0;pointer-events:none;display:none}
.burst.on{display:block}
.burst .ring{position:absolute;left:50%;top:50%;width:40px;height:40px;margin:-20px;border-radius:50%;border:6px solid var(--c);animation:ring 1s ease-out forwards}
@keyframes ring{to{transform:scale(14);opacity:0}}
.burst .glow{position:absolute;inset:0;background:radial-gradient(circle at 50% 50%,var(--c) 0,transparent 60%);opacity:0;animation:glow 1.4s ease-out forwards}
@keyframes glow{20%{opacity:.75}100%{opacity:0}}
.burst i{position:absolute;left:50%;top:50%;width:8px;height:8px;border-radius:2px;background:var(--c);animation:fly 1.3s cubic-bezier(.2,.8,.3,1) forwards}
@keyframes fly{to{transform:translate(var(--x),var(--y)) rotate(540deg);opacity:0}}
.cardwrap{width:100%;opacity:0;transform:rotateY(90deg) scale(.9);transition:transform .6s cubic-bezier(.2,.8,.3,1),opacity .4s}
.cardwrap.in{opacity:1;transform:none}
.cardwrap .card{color:#222}
.grade{font-size:13px;letter-spacing:.2em;text-transform:uppercase;color:#bbb;margin:14px 0 6px;opacity:0;transition:opacity .4s .5s}
.cardwrap.in+.grade{opacity:1}
.take{margin-top:16px;opacity:0;transition:opacity .4s 1s} .take.in{opacity:1}
"""

SPARKS = {"common": 0, "uncommon": 12, "rare": 30, "epic": 55, "legendary": 100}   # the flourish follows the grade


def reveal_page(name):
    h = next((x for x in G["horses"] if x.name == name and x.owner == ME), None)
    if not h:
        return page("Reveal", "<p>Nothing to reveal.</p>")
    g = grade(h)
    color, sparks, line = GRADE_COLOR[g], SPARKS[g], GRADE_LINE[g]
    import math
    bits = "".join(f"<i style='--x:{math.cos(i / sparks * 6.283) * (120 + (i * 37) % 90):.0f}px;--y:{math.sin(i / sparks * 6.283) * (120 + (i * 53) % 90):.0f}px;"
                   f"animation-delay:{(i * 7) % 40 * 10}ms'></i>" for i in range(sparks))
    return (f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{esc(h.name)}</title>{FONTS}<style>{CSS}{SKIN}{REVEAL_CSS}</style>{ASK_JS}</head><body class='reveal'><div class=stage style='--c:{color}'>"
            f"<div class=pack id=pack onclick='go()'><div class=sil>{portrait(h, 150)}</div><div class=hint>tap to open</div></div>"
            f"<div class=burst id=burst><div class=glow></div><div class=ring></div>{bits}</div>"
            f"<div class=cardwrap id=card>{identity_card(h)}</div><div class=grade><b style='color:{color}'>{g}</b> · {line}</div>"
            f"<div class=take id=take><a class=btn href='/horse/{urlname(h.name)}'>Take to the barn</a>"
            f" <form method=post action=/scrap class=inline style='margin-left:10px'><input type=hidden name=h value='{esc(h.name)}'>"
            f"<button class=sec onclick=\"return ask(this,'Sell {h.name} to the house for ${e.SCRAP:,.0f}? Gone for good.')\">Sell to the house · ${e.SCRAP:,.0f}</button></form></div></div>"
            "<script>let done=false;function go(){if(done)return;done=true;const p=document.getElementById('pack');p.classList.add('shake');"
            "setTimeout(()=>{document.getElementById('burst').classList.add('on');p.style.transform='scale(0)';p.style.opacity='0';},650);"
            "setTimeout(()=>{p.style.display='none';document.getElementById('card').classList.add('in');},1050);"
            "setTimeout(()=>document.getElementById('take').classList.add('in'),1500);}"
            "setTimeout(go,2200);</script></body></html>")


# ---------------------------------------------------------------- server
LOCK = threading.Lock()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, code=200, loc=None, cookie=None):
        self.send_response(code)
        if loc:
            self.send_header("Location", loc)
        if cookie is not None:                                    # a year-long login, or "" to log out
            self.send_header("Set-Cookie", f"td={cookie}; Path=/; HttpOnly; SameSite=Lax; Max-Age={31536000 if cookie else 0}{SECURE}")
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")             # game pages are live: never show a stale one
        data = body.encode()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def player(self):
        """The barn behind this request's login cookie, or None."""
        for part in self.headers.get("Cookie", "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "td" and v in G["sessions"]:
                return G["sessions"][v]
        return None

    def ip(self):
        """The visitor's address: the proxy's forwarded one when the game sits behind the HTTPS front end."""
        return (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()

    def local(self):
        """A request from this machine itself, not forwarded from outside (claiming barn 0 needs it)."""
        return self.client_address[0] == "127.0.0.1" and not self.headers.get("X-Forwarded-For")

    def gate(self, p):
        """Sets ME for this request; False when a login is needed (static art and the login pages are open to all)."""
        global ME
        o = self.player()
        if o is None:
            return p.startswith(("/mock/", "/login", "/signup")) or p in ("/manifest.webmanifest", "/sw.js", "/offline")
        ME = o
        P()["last_seen"] = time.time(); P()["seen_day"] = G["day"]        # today's check-in: the pass's grace counts the days missed
        check_in(o)
        ips, ua = P().setdefault("ips", []), (self.headers.get("User-Agent") or "")[:80]   # where and what they sign in from: the anti-dupe review reads it
        if self.ip() not in ips:
            ips.append(self.ip()); del ips[:-8]
        if ua and ua not in P().setdefault("uas", []):
            P()["uas"].append(ua); del P()["uas"][:-4]
        return True

    def start_session(self, o):
        token = secrets.token_urlsafe(24)
        G["sessions"][token] = o; save()
        return self.send("", 303, "/welcome", cookie=token)

    # requests arrive on their own threads but are handled one at a time: ME (and the whole world) is shared
    def do_GET(self):
        with LOCK:
            self._get()

    def do_POST(self):
        with LOCK:
            self._post()

    def _get(self):
        p = urlparse(self.path).path
        if not self.gate(p):
            return self.send("", 303, "/login")
        if p in ("/login", "/signup"):
            return self.send(login_page(p == "/signup", local=self.local()))
        if e.auctions and min(a["ends"] for a in e.auctions.values()) <= time.time():   # auctions close in real time
            e.settle_auctions(G["horses"]); save()
        if p == "/skin":                                                  # pick the color theme (More > Theme)
            k = parse_qs(urlparse(self.path).query).get("s", ["night"])[0]
            if k in THEMES:
                P()["skin"] = k; save()
            return self.send("", 303, loc=parse_qs(urlparse(self.path).query).get("back", ["/more"])[0])
        if p in ("/", "/welcome") and unseen_night():
            if P().get("carded") != G["day"]:                       # once per night: a card before the results
                P()["carded"] = G["day"]
                cp = card_page("/results")
                if cp:
                    return self.send(cp)
            return self.send("", 303, "/results")                   # results first, so the barn can't spoil them
        if p == "/":
            return self.send(barn_page({k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}))
        if p == "/results":
            return self.send(results_page({k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}))
        if p == "/entries":
            return self.send(entries_page({k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}))
        if p.startswith("/race/") and p.endswith(".json"):               # a race's story, for the replay
            rid = unquote(p[len("/race/"):-5])
            showcase = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mockups", "races", os.path.basename(rid) + ".json")
            if rid in c.STORIES:
                st_ = c.STORIES[rid]
                if not all("odds" in r for r in st_["horses"]):                # raced before the tote: price it off today's ratings
                    field = [x for x in (next((h for h in G["horses"] if h.name == r["name"]), None) for r in st_["horses"]) if x]
                    line = c.tote_odds(field)
                    for r in st_["horses"]:
                        h = next((x for x in field if x.name == r["name"]), None)
                        r.setdefault("odds", "%d-%d" % line[h.id] if h else "")
                st_ = dict(st_, horses=[dict(r) for r in st_["horses"]])     # this viewer's copy: names are per viewer
                best = None
                for r in st_["horses"]:                                    # the winner's circle names the barn
                    h = find_horse(r["name"])
                    r["owner"] = barn_name(h.owner) if h else ""
                    r["stable"] = (G["players"][h.owner].get("stable") or G["players"][h.owner].get("user")) if h and h.owner in G["players"] else r["owner"]
                    r["player"] = bool(h and h.owner in c.HUMAN)
                    r["emblem"] = CR.svg(emblem_of(h.owner)).split("src=")[1].split()[0] if h else ""   # the PNG's path
                    r["marquee"] = marquee_html(h.owner, mq_) if h and (mq_ := marquee_of(h.owner)) else ""
                    if h:                                                  # the handicapper's pick, on what was known before the race
                        form = [x["place"] == 1 for x in getattr(h, "results", []) if x["day"] < st_["day"]][-5:]
                        score = h.est + 1.5 * sum(form) - 0.4 * r["post"]
                        if best is None or score > best[0]:
                            best = (score, r["name"])
                st_["pick"] = best[1] if best else ""
                if (lk := vlook(st_.get("venue", "Harness Park"))):
                    st_["tlook"] = dict(zip(("p", "a", "font", "motto", "badge"), lk))
                st_["matinee"] = bool(next((v.get("day") for v in c.VENUES if v["name"] == st_.get("venue")), False))   # a daytime track: the replay draws it in daylight
                data = json.dumps(st_).encode()
            elif os.path.isfile(showcase):                                 # showcase races built by showcase.py
                with open(showcase, "rb") as f:
                    data = f.read()
            else:
                return self.send("not found", 404)
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data))); self.end_headers()
            return self.wfile.write(data)
        if p.startswith("/replay/") or p.startswith("/replay2d/"):        # the replay page for one race: HD-2D, or the flat 2D one
            flat = p.startswith("/replay2d/")
            rid = unquote(p[len("/replay2d/" if flat else "/replay/"):])
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mockups", "replay_pixel.html" if flat else "replay_hd2d.html")
            with open(path, encoding="utf-8") as f:
                html_ = f.read().replace("<!--RACE_ID-->null", json.dumps(rid)).replace('"__RACE_ID__"', json.dumps(rid))
            mine_names = {h.name for h in mine()}                         # your horse in this race, for the replay to tag
            me = next((r["name"] for r in c.STORIES.get(rid, {}).get("horses", []) if r["name"] in mine_names), "")
            html_ = html_.replace('MY_NAME = "H2395"', f"MY_NAME = {json.dumps(me)}")
            back = ("<a href='/' onclick=\"if(history.length>1){history.back();return false}\" style='position:fixed;top:env(safe-area-inset-top,0);"
                    "right:env(safe-area-inset-right,0);z-index:9999;padding:8px 14px;border-radius:0 0 0 10px;background:#000c;color:#fff;font:600 15px system-ui;text-decoration:none'>&larr; Back</a>")
            card = next_card()
            return self.send(html_.replace("</body>", back + (card_overlay(card) if card else "") + "</body>", 1))
        if p.startswith("/horse/"):
            return self.send(horse_page(unquote(p.split("/")[2]), "enter" in parse_qs(urlparse(self.path).query)))
        if p.startswith("/mock/"):                          # design mockups: static files from mockups/
            root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mockups")
            path = os.path.normpath(os.path.join(root, p[len("/mock/"):]))
            name = path
            if not path.startswith(root + os.sep) or not os.path.isfile(path):   # nothing outside mockups/
                return self.send("not found", 404)
            kind = {".html": "text/html; charset=utf-8", ".png": "image/png", ".js": "text/javascript", ".css": "text/css", ".jpg": "image/jpeg", ".json": "application/json", ".wav": "audio/wav", ".mp3": "audio/mpeg"}.get(os.path.splitext(name)[1], "application/octet-stream")
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        if p.startswith("/portrait/"):
            h = find_horse(unquote(p.split("/")[2]).removesuffix(".png"))
            if not h:
                return self.send("not found", 404)
            coat, marking = looks(h)
            with open(recolor.portrait(coat, marking, pattern(h), 256), "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "max-age=86400")       # a horse's look never changes
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        if p.startswith("/reveal/"):
            return self.send(reveal_page(unquote(p.split("/")[2])))
        qs = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
        if p == "/archive":                                   # the live stud book: every horse, searchable and filtered
            return self.send(archive_page(qs))
        if p == "/leaders":
            return self.send(leaders_page(qs))
        if p == "/market":
            return self.send(market_page(qs))
        if p == "/claimers":
            return self.send(claimers_page(qs))
        if p == "/sponsor":
            return self.send(sponsor_page(qs)) if SPONSORING else self.send("", 303, "/market")
        if p == "/setup" and has_pass(ME):                                # the Stable Manager's preview
            return self.send(setup_page())
        if p == "/studs":
            return self.send(breeding_page(qs))
        if p == "/studbook":
            return self.send(studs_page(qs))
        if p.startswith("/barn/") and p[6:].lstrip("-").isdigit():
            return self.send(barn_public(int(p[6:])))
        if p == "/crest":
            return self.send(crest_page())
        if p == "/emblem":                                            # the builder's live preview of an emblem
            qe = parse_qs(urlparse(self.path).query)
            sk_ = {k: qe.get(k, [""])[0] for k in ("pat", "c1", "c2")}
            if sk_["pat"]:
                ok = sk_["pat"] in EA.PATTERNS and sk_["c1"] in CR.PALETTE and sk_["c2"] in CR.PALETTE
                return self.send("", 302, EA.render_silks(sk_)) if ok else self.send("", 404)
            em_ = {k: qe.get(k, [""])[0] for k in ("shape", "c1", "c2", "dev", "letter", "rim")}
            if (em_["shape"] in CR.SHAPES and em_["dev"] in CR.DEVICES and em_["c1"] in CR.PALETTE and em_["c2"] in CR.PALETTE
                    and em_["rim"] in ("iron", "silver", "gold") and em_["letter"] in list(string.ascii_uppercase)):
                return self.send("", 302, EA.render(em_, em_["rim"]))
            return self.send("", 404)
        if p.startswith("/breed/"):
            return self.send(breed_page(unquote(p[len("/breed/"):])))
        routes = {"/claims": claims_page, "/training": training_page, "/market": market_page, "/studs": breeding_page, "/trainers": trainers_page, "/stakes": stakes_page, "/upgrade": upgrade_page, "/more": more_page, "/earnings": earnings_page, "/guide": guide_page}
        if p == "/claims":
            return self.send("", 303, "/program")                       # the claiming races live on the program now
        if p == "/shop":
            return self.send(shop_page())
        if p == "/tack":
            return self.send(tack_page())
        if p.startswith("/tonic/"):
            return self.send(tonic_page(unquote(p.split("/")[2])))
        if p == "/stakes":
            return self.send(stakes_page({k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}))
        if p == "/program":
            return self.send(program_page({k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}))
        if p == "/admin":
            return self.send(admin_page() if ME == ADMIN else "not found", 200 if ME == ADMIN else 404)
        if p == "/welcome":
            return self.send(welcome_page())
        if p == "/sw.js":                                                 # the service worker, at the root so it covers the whole game
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sw.js"), "rb") as f:
                data = f.read()
            self.send_response(200); self.send_header("Content-Type", "application/javascript"); self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
            return
        if p == "/offline":                                               # what the installed game shows with no signal
            return self.send(OFFLINE_PAGE)
        if p == "/manifest.webmanifest":
            data = MANIFEST.encode()
            self.send_response(200); self.send_header("Content-Type", "application/manifest+json"); self.send_header("Content-Length", str(len(data))); self.end_headers()
            return self.wfile.write(data)
        if p in routes:
            return self.send(routes[p]())
        self.send("not found", 404)

    def _post(self):
        p = urlparse(self.path).path
        raw = parse_qs(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode())
        q = {k: v[0] for k, v in raw.items()}
        q["shelf_all"] = raw.get("shelf", [])                                 # the one multi-pick field: the Marquee's trophy shelf
        if p == "/login":
            now = time.time()
            keys = (self.ip(), "u:" + q.get("user", "").strip().lower())    # by address, and by the name under attack
            tries = {k: [t for t in FAILED.get(k, []) if now - t < 900] for k in keys}
            if any(len(v) >= 8 for v in tries.values()):           # eight misses in 15 minutes, from one address or at one name: wait it out
                return self.send(login_page(False, error="Too many tries. Wait a few minutes and try again."))
            o = login(q.get("user", ""), q.get("pw", ""))
            if o is None:
                for k in keys:
                    FAILED[k] = tries[k] + [now]
                if len(FAILED) > 5000:                             # forget stale addresses rather than grow forever
                    FAILED.clear()
            return self.start_session(o) if o is not None else self.send(login_page(False, error="Name or password doesn't match."))
        if p == "/signup":
            local = self.local()
            o, err = signup(q.get("user", ""), q.get("pw", ""), claim=local and q.get("claim") == "1")
            return self.start_session(o) if o is not None else self.send(login_page(True, error=err, local=local))
        if not self.gate(p):
            return self.send("", 303, "/login")
        if p == "/logout":
            for k in [k for k, v in G["sessions"].items() if v == ME]:
                G["sessions"].pop(k)
            save()
            return self.send("", 303, "/login", cookie="")
        by_name = {h.name: h for h in G["horses"]}
        back = self.headers.get("Referer", "/")
        if entries_closed() and ME != ADMIN and p in ("/entries", "/enter", "/scratch", "/order", "/tonic"):   # claims stay open until post time
            return self.send("", 303, back)                         # 7:55 to 8 PM: the program is final
        if p == "/advance" and ME == ADMIN:                       # the world clock: admin only
            if q.get("days") == "run":
                for _ in range(c.YEAR * 3):
                    if tick():
                        break
            else:
                for _ in range(int(q.get("days", 1))):
                    tick()
            back = q.get("back", "")
            return self.send("", 303, back if back.startswith("/horse/") else "/results")
        if p == "/admin/cash" and ME == ADMIN:
            try:
                o, amt = int(q.get("o", "")), int(float(q.get("amt", "")))
            except ValueError:
                return self.send(admin_page("Enter an amount."))
            if o not in G["players"] or not amt:
                return self.send(admin_page("Pick a player and an amount."))
            amt = max(amt, -int(e.cash.get(o, 0)))                     # never below zero
            e.book(o, "gifts", amt)
            save()
            return self.send(admin_page(f"{'Gave' if amt > 0 else 'Took'} ${abs(amt):,} {'to' if amt > 0 else 'from'} {G['players'][o].get('user')} ({full_name(o)}). Their cash is now ${e.cash[o]:,.0f}."))
        if p == "/admin/gift" and ME == ADMIN:                          # move a horse to a player's barn: by name, or one like a named horse
            o = int(q.get("o", "")) if str(q.get("o", "")).isdigit() else -1
            name, like = q.get("h", "").strip(), q.get("mode") == "like"
            if o not in G["players"] or not name:
                return self.send(admin_page("Pick a player and name a horse."))
            if q.get("mode") == "clone":                               # dev: an identical copy, fresh record, new name
                import copy
                ref = find_horse(name)
                if not ref or ref.retired:
                    return self.send(admin_page(f"No racer called {name}."))
                h = copy.copy(ref)
                for k, v in list(vars(ref).items()):                   # own copies of every dict/list so the two never share state
                    if isinstance(v, (dict, list, set)) and k not in ("sire", "dam"):
                        setattr(h, k, copy.deepcopy(v))
                h.id = max(x.id for x in G["horses"]) + 1
                base = ref.name + " II"; n = 2
                while find_horse(base):
                    n += 1; base = f"{ref.name} {'I' * n if n <= 3 else n}"
                h.name = base
                h.results, h.trophies, h.seasons, h.history = [], [], {}, []
                h.starts = h.wins = h.earnings = h.costs = 0; h.places = h.shows = 0; h.last5 = []; h.recent = []
                e.settled[h.id] = (0, 0)                                # a clean ledger: nothing of the original's purses or bills carries over
                h.last, h.best, h.order, h.ship, h.job, h.wk = None, 999, None, None, None, None
                h.owner, h.breeder, h.gone = o, None, "a gift from the circuit"
                h.freshness, h.ageless = 100, False                    # a copy ages like any horse; only the original is the owner's ageless one (load() reclaims those)
                G["horses"].append(h); e.barn_size[o] = e.barn_size.get(o, 0) + 1; c.trainer_of(h); save()
                return self.send(admin_page(f"{h.name} ({h.age}yo {sex_word(h)}, {tier_label(h)}), a copy of {ref.name}, now races for {G['players'][o].get('user')}."))
            if like:
                ref = find_horse(name)
                if not ref:
                    return self.send(admin_page(f"No horse called {name}."))
                pool = [x for x in G["horses"] if x.owner in G["ai"] and not x.retired and x.id not in e.listings and x.id not in c.CLAIMS and not on_card(x)]
                h = min(pool, key=lambda x: (round(abs(x.est - ref.est)), c.age_group(x) != c.age_group(ref), -x.starts), default=None)   # nearest rating, same age if it can
            else:
                h = find_horse(name)
                if h and h.owner in c.HUMAN and h.owner != ME:
                    return self.send(admin_page(f"{h.name} belongs to a player; the board is for that."))
            if not h or h.retired or h in e.nursery:
                return self.send(admin_page("No racer to give."))
            was = h.owner
            e.listings.pop(h.id, None); e.auctions.pop(h.id, None); c.CLAIMS.pop(h.id, None)
            h.owner, h.order, h.ship, h.gone, h.ageless = o, None, None, "a gift from the circuit", False
            e.barn_size[o] = e.barn_size.get(o, 0) + 1; e.barn_size[was] = max(0, e.barn_size.get(was, 1) - 1)
            c.trainer_of(h)
            save()
            over = "" if e.barn_size[o] <= e.stalls(o) else f" They are over their stalls ({e.barn_size[o]} of {e.stalls(o)})."
            return self.send(admin_page(f"{h.name} ({h.age}yo {sex_word(h)}, {tier_label(h)}, {h.starts}-{h.wins}, ${h.earnings:,.0f}) now races for {G['players'][o].get('user')}.{over}"))
        if p == "/drivers":
            P()["drivers"] = [n for n in (q.get(f"d{k}", "") for k in (1, 2, 3)) if n in DRV.STYLE][:3]
            P()["drivers"] = list(dict.fromkeys(P()["drivers"]))           # a driver named twice counts once
            save()
            return self.send("", 303, "/?view=drivers")
        if p == "/tips":
            P()["hide_tips"] = q.get("hide") == "1"; save()
            return self.send("", 303, "/more")
        if p == "/admin/msg" and ME == ADMIN:
            text = q.get("text", "").strip()[:280]
            if text:
                G.setdefault("team_msgs", []).append({"id": secrets.token_hex(4), "text": text, "at": time.time()}); save()
            return self.send(admin_page("Posted. Each player sees it once." if text else "Write a message first."))
        if p == "/admin/clock" and ME == ADMIN:
            at = q.get("at", "")
            if at:
                G["frozen"] = at
            else:
                G.pop("frozen", None)
            save()
            return self.send(admin_page(f"Clock frozen at {at}." if at else "Clock running again."))
        if p == "/admin/undo" and ME == ADMIN:
            return self.send(admin_page("Last race night undone." if undo_night() else "Nothing to undo."))
        if p == "/sponsor":                                               # a bid in the sponsorship auction
            if SPONSORING:
                sponsor_bid(ME, q.get("s", "")); save()
            back = q.get("back", "")
            return self.send("", 303, (back if back.startswith("/sponsor") else "/sponsor") + "#list")
        if p == "/admin/sponsor" and ME == ADMIN:                         # dev: open the auction now, or close it now
            if q.get("do") == "open":
                open_sponsor_auction()
            else:
                settle_sponsors()
            save()
            return self.send(admin_page("Sponsorship auction opened." if q.get("do") == "open" else "Sponsorship auction settled."))
        if p == "/sets" and has_pass(ME):                                # the Stable Manager's sheet: save every set, or deploy them all
            for x in youngsters():
                j, f_ = q.get(f"j{x.id}"), q.get(f"f{x.id}") or (getattr(x, "tset", None) or (None, "stamina"))[1]   # no focus field before training opens
                if j in JOB_WORD and f_ in FOCUS_NAME:
                    x.tset = (j, f_)
            if q.get("do") == "deploy":
                for x in unworked():
                    apply_job(x, ME, "repeat", "")
            save()
            return self.send("", 303, "/training")
        if p == "/setup" and has_pass(ME):                               # the Stable Manager's one button
            setup_tonight(ME); save()
            return self.send("", 303, "/")
        if p == "/admin/markers" and ME == ADMIN:                         # dev: Markers for a barn, until there's a store
            o = int(q.get("o", "")) if str(q.get("o", "")).isdigit() else -1
            n = int(q.get("n", "")) if str(q.get("n", "")).lstrip("-").isdigit() else 0
            if o in G["players"] and n:
                mk_book(o, n, "from the track"); save()
            return self.send(admin_page(f"{G['players'][o].get('user')} now holds {markers(o):,} Markers." if o in G["players"] and n else "Pick a player and a number."))
        if p == "/admin/pass" and ME == ADMIN:                            # dev: the pass on or off for a barn, until there's a store
            o = int(q.get("o", "")) if str(q.get("o", "")).isdigit() else -1
            if o in G["players"]:
                P(o)["pass"] = not P(o).get("pass"); save()
            return self.send(admin_page(f"Season Pass {'on' if P(o).get('pass') else 'off'} for {G['players'][o].get('user')}." if o in G["players"] else "Pick a player."))
        if p == "/pick":                                                  # the handicapper's game: one pick per stake, changeable until it runs
            s = next((s for s in stakes_tonight() if s.id == q.get("s")), None)
            hid = int(q["h"]) if str(q.get("h", "")).isdigit() else None
            if s and any(h.id == hid for h in nominees(s)):
                G.setdefault("picks", {}).setdefault(ME, {})[s.id] = hid; save()
            return self.send("", 303, "/stakes#picks")
        if p == "/admin/review" and ME == ADMIN:                        # the stewards' call on a flagged pair
            a, b, do = (int(q.get(k, -1)) if str(q.get(k, "")).isdigit() else -1 for k in ("a", "b")), q.get("do")
            a, b = a
            if a in G["players"] and b in G["players"]:
                if do == "clear":
                    G.setdefault("cleared", []).append(tuple(sorted((a, b))))
                elif do == "warn":
                    for o in {a, b}:
                        P(o).setdefault("events", []).append("A note from the stewards: a sale between barns has been looked at. Keep the market honest.")
                elif do in ("freeze", "unfreeze"):
                    for o in {a, b}:
                        P(o)["frozen"] = do == "freeze"
                save()
            return self.send(admin_page(f"{do}: done."))
        if p == "/newgame" and ME == ADMIN:                           # a world wipe: every player starts over in a new world
            if q.get("confirm", "").strip() != "NEW WORLD":
                return self.send(admin_page("Type NEW WORLD in the box to start a new world."))
            n = new_world()
            return self.send(admin_page(f"A new world. {n} player barn{'s' if n != 1 else ''} started over; the old world is saved beside the save file."))
        if p == "/crest":
            msg = build_save(q) if q.get("build") else buy_crest(q); save()
            return self.send(crest_page(msg))
        if p == "/tack":
            msg = tack_post(q); save()
            return self.send(tack_page(msg))
        if p == "/verify" and ME == ADMIN:
            o = int(q.get("o", -1)) if str(q.get("o", "")).lstrip("-").isdigit() else -1
            if o in G.get("players", {}):
                if q.get("act") == "on":
                    P(o)["verified"] = q.get("note", "").strip()[:60]
                else:
                    P(o).pop("verified", None)
                save()
            return self.send("", 303, f"/barn/{o}")
        if p == "/stablename":
            n, fee = q.get("n", "").strip()[:28], CR.RENAME_FEE if P().get("named") else 0   # the first name is free
            if n and n != P().get("stable") and e.cash.get(ME, 0) >= fee:
                if fee:
                    e.book(ME, "cosmetics", -fee)
                P()["stable"], P()["named"] = n, True; save()
            return self.send("", 303, q.get("back") if q.get("back") == "/crest" else "/welcome")
        if p == "/entries":
            trainers_entries(G["horses"])
            save()
            return self.send("", 303, "/entries")
        if p == "/buytonic":
            k = q.get("k")
            if k in TONIC_PRICE and e.cash.get(ME, 0) >= TONIC_PRICE[k]:
                e.book(ME, "shop", -TONIC_PRICE[k]); shelf()[k] += 1; save()
                return self.send(shop_page(f"Bought a {k.title()} Tonic."))
            return self.send(shop_page("Not enough cash for that one."))
        if p in ("/register", "/dump"):
            f = next((x for x in e.nursery if x.name == q.get("h", "")), None)
            if f and (e.register(f, ME, G["horses"]) if p == "/register" else e.dump(f, ME)):
                save()
            return self.send("", 303, "/breeding")
        h = by_name.get(q.get("h", ""))
        if p == "/tonic" and h and h.owner == ME:
            k, o = q.get("k"), getattr(h, "order", None)
            if isinstance(o, tuple) and o[0] == "enter":
                t = shelf()
                if getattr(h, "tonic", None):                     # whatever it was on goes back first
                    t[h.tonic] += 1; h.tonic = None
                if k in t and t[k] > 0:
                    t[k] -= 1; h.tonic = k
                save()
            return self.send("", 303, "/")
        if p == "/house":
            got = e.buy_house_horse(ME, G["horses"], P().get("rig"))
            if got:
                P().pop("rig", None)                                 # a rigged roll is one purchase only
            save()
            return self.send("", 303, f"/reveal/{urlname(got[0].name)}" if got else "/market")
        h = by_name.get(q.get("h", ""))
        if p == "/enter" and h and h.owner == ME:
            name, purse, tag, track, *vid = q["r"].split("|")
            if (name, int(purse), int(tag), track) in c.eligible_races(h) and (not vid or c.hosts(name, track) and vid[0] in [v["id"] for v in c.hosts(name, track)]):
                h.order = ("enter", name, int(purse), int(tag), track) + tuple(vid[:1])   # the track asked for rides along as o[5]
                save()
                return self.send("", 303, "/")                       # entered: back to the barn to set the next one
        elif p == "/groom" and h:
            e.groom(h, ME, G["day"])
        elif p == "/job":                                         # the day sheet: one job a day for a youngster
            if q.get("h") == "*":                                     # the whole string: every youngster not yet worked today
                for x in unworked():
                    apply_job(x, ME, "repeat", "")
            else:
                f = next((x for x in e.nursery if x.name == q.get("h", "")), None)
                x = f or (h if h and h.owner == ME else None)
                if x:
                    apply_job(x, ME, q.get("j", ""), q.get("f", "gait"))
            save()
            return self.send("", 303, q.get("back") if q.get("back", "").startswith("/") else "/training")
        elif p == "/scratch" and h and h.owner == ME:
            if getattr(h, "tonic", None):                       # scratched: the tonic goes back on the shelf
                shelf()[h.tonic] += 1; h.tonic = None
            if (r := on_card(h)):                                # off tonight's program: it rests, and any claim on it is void
                r["field"].remove(h); c.CLAIMS.pop(h.id, None); h.wk = "rest"; h.last = "scratched"
            else:
                h.order = h.ship = None
        if p == "/order" and h and h.owner == ME:
            if q["o"] == "retire":
                e.retire(h, ME)
            elif q["o"] == "sell" and (e.held(h) or P().get("frozen") or on_card(h)):
                pass                                                  # just bought, under review, or racing tonight: it stays
            else:
                try:
                    h.order = parse(q["o"], h)
                except ValueError:
                    pass
        elif p == "/hire":
            t = next((t for t in c.ROSTER if t.name == q.get("t")), None)
            if t and h and h.owner == ME:
                c.assign(h, t)
            elif t:
                c.BARN_TRAINER[ME] = t
                for x in mine():
                    if c.trainer_of(x) is not t:
                        c.assign(x, t)
        elif p == "/nominate" and h and h.owner == ME:
            s = next((s for s in sk.CALENDAR if s.id == q.get("s")), None)
            if s:
                sk.nominate(h, s, G["day"])
        elif p == "/scout" and h and h.owner == ME:
            s = by_name.get(q.get("s", ""))
            if s and e.scout(s, h, ME):
                save()
            return self.send("", 303, f"/breed/{urlname(h.name)}")
        elif p == "/breed" and h and h.owner == ME:
            s = by_name.get(q.get("s", ""))
            if s and e.book_mare(h, s, ME, G["horses"], day=G["day"]) is not None:
                n = " ".join(q.get("n", "").split())                       # the breeder names the foal; the registry's rules, else the house name stands
                if n and n.replace(" ", "").isalpha() and len(n) <= _names.MAXLEN and n not in _names.USED and not find_horse(n):
                    e.nursery[-1].name = n; _names.USED.add(n)
                save()
                return self.send("", 303, f"/horse/{urlname(e.nursery[-1].name)}")      # straight to the new foal
        elif p == "/bid" and h:
            amt = q.get("amt", "")
            if not P().get("frozen"):
                e.bid(h, ME, amount=int(amt) if amt.isdigit() else None)
            save()
            back = self.headers.get("Referer", "")                      # back to the same page and position: the scroll keeper needs no hash
            return self.send("", 303, back if "/market" in back else "/market#a" + str(h.id))
        elif p == "/claim" and h and h.owner != ME:
            o = getattr(h, "order", None)
            if q.get("undo"):
                if c.CLAIMS.get(h.id) == ME:
                    del c.CLAIMS[h.id]
            elif (tag := claim_tag(h)) and h.id not in c.CLAIMS and e.cash.get(ME, 0) >= tag \
                    and e.barn_size.get(ME, 0) + sum(1 for b in c.CLAIMS.values() if b == ME) < e.stalls(ME):
                c.CLAIMS[h.id] = ME                            # in before post time: settled when the race is run
            save()
            return self.send("", 303, "/claimers" if q.get("back") == "/claimers" else "/program")
        elif p == "/scrap" and h:
            if not P().get("frozen") and e.scrap(h, ME, G["horses"]):
                save()
                return self.send("", 303, "/market")
        elif p == "/fee" and h:
            try:
                e.set_fee(h, ME, float(q.get("fee", "")))
            except ValueError:
                pass
        elif p == "/upgrade":
            e.upgrade(ME)
        elif p == "/license" and not e.can_breed(ME) and e.cash.get(ME, 0) >= license_cost(ME):   # all of it or none of it
            while not e.can_breed(ME) and e.upgrade(ME):
                pass
        save()
        self.send("", 303, back)


if __name__ == "__main__":
    if os.path.exists(SAVE):
        load()
    else:
        new_game()
    print("Playtest barn at http://localhost:8111  (Ctrl+C to stop; progress is saved every day)")
    threading.Thread(target=race_nights, daemon=True).start()
    ThreadingHTTPServer((os.environ.get("TD_BIND", "0.0.0.0"), 8111), H).serve_forever()
