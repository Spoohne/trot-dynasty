"""The encyclopedia: a private page over the 100-season world (sim100.py's SQLite file), on this PC only.

  python research/encyclopedia/serve.py [db]      -> http://127.0.0.1:8114/

Search, filter and sort every horse by its card at an age and by its career; a card gallery; the two surprise lists
(plain cards with big careers, elite cards that flopped); looks-vs-results charts; each horse's cards season by season,
family, trophies and kept replays (played in the game's own replay viewer); notes saved to notes.json beside this file.
Read-only on the world file; the run can still be writing it.
"""
import json
import os
import sqlite3
import sys
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MOCK = os.path.join(ROOT, "mockups")
DB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "world100.db")
NOTES = os.path.join(HERE, "notes.json")
BUILDS = os.path.join(HERE, "builds.json")
sys.path.insert(0, os.path.join(ROOT, "art"))
import recolor                                                    # noqa: E402  the game's portraits, by coat and marking

GRADES = ["D", "C", "B", "A", "S", "S+", "Galaxy"]
GN = "CASE {c} WHEN 'D' THEN 0 WHEN 'C' THEN 1 WHEN 'B' THEN 2 WHEN 'A' THEN 3 WHEN 'S' THEN 4 WHEN 'S+' THEN 5 WHEN 'Galaxy' THEN 6 ELSE -1 END"
BARS = ("speed", "stamina", "grit", "manners")
SORTS = {"earnings": "h.earnings", "wins": "h.wins", "starts": "h.starts", "winpct": "CAST(h.wins AS REAL) / MAX(h.starts, 1)",
         "peak": "pk.rating", "stakes": "json_array_length(h.trophies)", "titles": "json_array_length(h.titles)", "foaled": "h.foaled",
         "name": "h.name", "card": "(c.speed + c.stamina + c.grit + c.manners)", "best": "COALESCE(h.best, 999)"}


def con():
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db


def meta(db):
    return {r["k"]: r["v"] for r in db.execute("SELECT k, v FROM meta")}


def card_join(age):
    """The card a filter looks at: the season the horse was that age, or its peak (best rating) season."""
    if age == "peak":
        return "JOIN seasons c ON c.id = h.id AND c.season = (SELECT season FROM seasons WHERE id = h.id ORDER BY rating DESC LIMIT 1)"
    return f"JOIN seasons c ON c.id = h.id AND c.age = {int(age)}"


PEAK = "LEFT JOIN (SELECT id, MAX(rating) rating FROM seasons GROUP BY id) pk ON pk.id = h.id"


def horses(db, q):
    g = lambda k, d="": q.get(k, [d])[0]
    age = g("age", "3")
    where, args = ["1=1"], []
    if g("name"):
        where.append("h.name LIKE ?"); args.append(f"%{g('name')}%")
    if g("sex") in ("m", "f"):
        where.append("h.sex = ?"); args.append(g("sex"))
    if g("style"):
        where.append("h.style = ?"); args.append(g("style"))
    for k in ("from", "to"):
        if g(k).lstrip("-").isdigit():
            where.append(f"h.foaled {'>=' if k == 'from' else '<='} ?"); args.append(int(g(k)))
    for b in BARS:
        if g("g_" + b) in GRADES:
            where.append(f"({GN.format(c='c.g_' + b)}) >= ?"); args.append(GRADES.index(g("g_" + b)))
    look = g("look")
    gsum = " + ".join(f"(({GN.format(c='c.g_' + b)}) >= 4)" for b in BARS)
    if look == "elite":
        where.append(f"({gsum}) >= 2")
    elif look == "plain":
        where.append(" AND ".join(f"({GN.format(c='c.g_' + b)}) <= 2" for b in BARS))
    for k, col in (("min_earn", "h.earnings"), ("min_wins", "h.wins"), ("min_starts", "h.starts")):
        if g(k).isdigit():
            where.append(f"{col} >= ?"); args.append(int(g(k)))
    if g("stake") == "1":
        where.append("json_array_length(h.trophies) > 0")
    if g("title") == "1":
        where.append("json_array_length(h.titles) > 0")
    if g("done") == "1":                                        # complete careers only: retired, or gone before the last season
        where.append("(h.retired = 1 OR h.last_season < ?)"); args.append(int(meta(db).get("season_done", 0)) - 1)
    if g("tier") in GRADES:
        where.append(f"(SELECT tier FROM seasons WHERE id = h.id ORDER BY rating DESC LIMIT 1) = ?"); args.append(g("tier"))
    order = SORTS.get(g("sort"), "h.earnings") + (" ASC" if g("dir") == "asc" else " DESC")
    page = max(0, int(g("page", "0") or 0)); per = min(200, int(g("per", "60") or 60))
    base = f"FROM horses h {card_join(age)} {PEAK} WHERE {' AND '.join(where)}"
    total = db.execute(f"SELECT COUNT(*) {base}", args).fetchone()[0]
    rows = db.execute(f"""SELECT h.id, h.name, h.sex, h.coat, h.marking, h.foaled, h.style, h.starts, h.wins, h.earnings, h.best,
        json_array_length(h.trophies) stakes, json_array_length(h.titles) titles, c.age, c.speed, c.stamina, c.grit, c.manners,
        c.g_speed, c.g_stamina, c.g_grit, c.g_manners, c.rating card_rating, c.tier card_tier, pk.rating peak,
        (SELECT tier FROM seasons WHERE id = h.id ORDER BY rating DESC LIMIT 1) peak_tier
        {base} ORDER BY {order} LIMIT ? OFFSET ?""", args + [per, page * per]).fetchall()
    return {"total": total, "rows": [dict(r) for r in rows]}


def horse(db, hid):
    h = db.execute("SELECT * FROM horses WHERE id = ?", (hid,)).fetchone()
    if not h:
        return None
    d = dict(h)
    d["seasons"] = [dict(r) for r in db.execute("SELECT * FROM seasons WHERE id = ? ORDER BY season", (hid,))]
    d["races"] = [dict(r) for r in db.execute("""SELECT k.rid, k.place, s.name, s.purse, s.season FROM kept k JOIN stories s ON s.rid = k.rid
        WHERE k.id = ? ORDER BY k.score DESC""", (hid,))]
    name = d["name"]
    d["stakes_races"] = [dict(r) for r in db.execute("SELECT rid, name, purse, season FROM stories WHERE stake = 1 AND rid IN "
                                                       "(SELECT rid FROM kept WHERE id = ?) ORDER BY season", (hid,))]
    for k in ("sire", "dam"):
        p = db.execute("SELECT id, name FROM horses WHERE id = ?", (d[k],)).fetchone() if d[k] else None
        d[k + "_name"] = p["name"] if p else None
    d["foals"] = [dict(r) for r in db.execute(f"SELECT id, name, earnings, wins, json_array_length(titles) titles FROM horses WHERE {'sire' if d['sex'] == 'm' else 'dam'} = ? "
                                                "ORDER BY earnings DESC LIMIT 40", (hid,))]
    d["trophies"] = json.loads(d["trophies"] or "[]"); d["titles"] = json.loads(d["titles"] or "[]")
    d["name"] = name
    return d


def charts(db, age):
    """Looks vs results, for complete careers: per bar, each grade at that age against career earnings and stakes wins;
    and a sample of (card total, career earnings, peak tier) points."""
    done = int(meta(db).get("season_done", 0)) - 1
    out = {"bars": {}}
    for b in BARS:
        rows = db.execute(f"""SELECT c.g_{b} g, COUNT(*) n, AVG(h.earnings) avg, AVG(json_array_length(h.trophies) > 0) stake,
            AVG(json_array_length(h.titles) > 0) title FROM horses h {card_join(age)}
            WHERE (h.retired = 1 OR h.last_season < ?) AND c.g_{b} IS NOT NULL GROUP BY c.g_{b}""", (done,)).fetchall()
        out["bars"][b] = sorted((dict(r) for r in rows), key=lambda r: GRADES.index(r["g"]))
    out["points"] = [list(r) for r in db.execute(f"""SELECT (c.speed + c.stamina + c.grit + c.manners), h.earnings,
        (SELECT tier FROM seasons WHERE id = h.id ORDER BY rating DESC LIMIT 1), h.id FROM horses h {card_join(age)}
        WHERE (h.retired = 1 OR h.last_season < ?) AND h.starts > 0 ORDER BY RANDOM() LIMIT 5000""", (done,))]
    out["speed_time"] = [list(r) for r in db.execute("""SELECT p.speed, h.best, p.tier FROM horses h JOIN (SELECT id, MAX(speed) speed,
        (SELECT tier FROM seasons s2 WHERE s2.id = s.id ORDER BY rating DESC LIMIT 1) tier FROM seasons s GROUP BY id) p ON p.id = h.id
        WHERE h.starts >= 20 AND h.best < 900 AND (h.retired = 1 OR h.last_season < ?) ORDER BY RANDOM() LIMIT 5000""", (done,))]
    return out


def surprises(db, age):
    """Plain cards with big careers (no bar above B at that age, career purses in the top 5%), and elite cards that flopped
    (two or more bars S or better at that age, career purses under the median), complete careers only."""
    done = int(meta(db).get("season_done", 0)) - 1
    earn = [r[0] for r in db.execute("SELECT earnings FROM horses WHERE starts > 0 AND (retired = 1 OR last_season < ?) ORDER BY earnings", (done,))]
    if not earn:
        return {"plain": [], "flops": [], "top5": 0, "median": 0}
    top5, med = earn[int(len(earn) * .95)], earn[len(earn) // 2]
    plain_w = " AND ".join(f"({GN.format(c='c.g_' + b)}) <= 2" for b in BARS)
    elite_w = " + ".join(f"(({GN.format(c='c.g_' + b)}) >= 4)" for b in BARS)
    cols = "h.id, h.name, h.sex, h.coat, h.marking, h.starts, h.wins, h.earnings, c.speed, c.stamina, c.grit, c.manners, c.g_speed, c.g_stamina, c.g_grit, c.g_manners"
    q = f"FROM horses h {card_join(age)} WHERE (h.retired = 1 OR h.last_season < ?) AND h.starts > 0"
    plain = db.execute(f"SELECT {cols} {q} AND {plain_w} AND h.earnings >= ? ORDER BY h.earnings DESC LIMIT 200", (done, top5)).fetchall()
    flops = db.execute(f"SELECT {cols} {q} AND ({elite_w}) >= 2 AND h.earnings < ? ORDER BY h.earnings LIMIT 200", (done, med)).fetchall()
    return {"plain": [dict(r) for r in plain], "flops": [dict(r) for r in flops], "top5": top5, "median": med}


def tiers(db):
    """Where the world's horses sit, per tier: the average card of every season raced at 3 and up (the builder's ghosts)."""
    rows = db.execute("""SELECT tier, COUNT(*) n, AVG(speed) speed, AVG(stamina) stamina, AVG(grit) grit, AVG(manners) manners
        FROM seasons WHERE age >= 3 AND retired = 0 GROUP BY tier""").fetchall()   # starts is career starts: a retired card is frozen
    total = sum(r["n"] for r in rows) or 1
    return {r["tier"]: dict(r, share=r["n"] / total) for r in rows}


def builds(new=None):
    """Patrick's hand-built horses, by tier, in builds.json beside this file. A post replaces the whole list."""
    if new is not None:
        json.dump(new, open(BUILDS + ".tmp", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        os.replace(BUILDS + ".tmp", BUILDS)
    return json.load(open(BUILDS, encoding="utf-8")) if os.path.exists(BUILDS) else {"settings": None, "horses": []}


def notes(new=None):
    n = json.load(open(NOTES, encoding="utf-8")) if os.path.exists(NOTES) else {"general": "", "horses": {}}
    if new:
        if new.get("id") == "general":
            n["general"] = new.get("text", "")
        else:
            n["horses"][str(new["id"])] = new.get("text", "")
            if not n["horses"][str(new["id"])]:
                del n["horses"][str(new["id"])]
        json.dump(n, open(NOTES + ".tmp", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        os.replace(NOTES + ".tmp", NOTES)
    return n


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, kind="application/json", code=200):
        body = body if isinstance(body, bytes) else (json.dumps(body, default=str) if kind == "application/json" else body).encode()
        self.send_response(code); self.send_header("Content-Type", kind); self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path); p, q = unquote(u.path), parse_qs(u.query)
        db = con()
        try:
            if p == "/":
                return self.send(open(os.path.join(HERE, "index.html"), "rb").read(), "text/html; charset=utf-8")
            if p == "/api/meta":
                m = meta(db); m["horses"] = db.execute("SELECT COUNT(*) FROM horses").fetchone()[0]
                m["stories"] = db.execute("SELECT COUNT(*) FROM stories").fetchone()[0]
                return self.send(m)
            if p == "/api/horses":
                return self.send(horses(db, q))
            if p.startswith("/api/horse/"):
                d = horse(db, int(p.rsplit("/", 1)[1]))
                return self.send(d) if d else self.send({"error": "no such horse"}, code=404)
            if p == "/api/charts":
                return self.send(charts(db, q.get("age", ["3"])[0]))
            if p == "/api/surprises":
                return self.send(surprises(db, q.get("age", ["3"])[0]))
            if p == "/api/notes":
                return self.send(notes())
            if p == "/gallop":                                       # gallop_report.py's page over the Gallop-model world
                return self.send(open(os.path.join(HERE, "gallop.html"), "rb").read(), "text/html; charset=utf-8")
            if p == "/builder":
                return self.send(open(os.path.join(HERE, "builder.html"), "rb").read(), "text/html; charset=utf-8")
            if p == "/api/tiers":
                return self.send(tiers(db))
            if p == "/api/builds":
                return self.send(builds())
            if p.startswith("/portrait/"):                          # /portrait/<coat>/<marking>.png
                _, _, coat, mk = p.split("/")
                path = recolor.portrait(coat, mk[:-4], 0, 128)
                return self.send(open(path, "rb").read(), "image/png")
            if p.startswith("/race/") and p.endswith(".json"):
                r = db.execute("SELECT json FROM stories WHERE rid = ?", (p[6:-5],)).fetchone()
                if r:
                    return self.send(zlib.decompress(r[0]), "application/json")
                f = os.path.join(HERE, "gallop_races", os.path.basename(p[6:]))         # gallop_replay.py's recorded races
                return self.send(open(f, "rb").read(), "application/json") if os.path.isfile(f) else self.send({"error": "not kept"}, code=404)
            if p.startswith("/replay/"):
                html = open(os.path.join(MOCK, "replay_hd2d.html"), encoding="utf-8").read()
                rid = p[len("/replay/"):]
                return self.send(html.replace("<!--RACE_ID-->null", json.dumps(rid)).replace('"__RACE_ID__"', json.dumps(rid)), "text/html; charset=utf-8")
            if p.startswith("/mock/"):
                path = os.path.normpath(os.path.join(MOCK, p[len("/mock/"):]))
                if path.startswith(MOCK + os.sep) and os.path.isfile(path):
                    kind = {".html": "text/html; charset=utf-8", ".png": "image/png", ".js": "text/javascript", ".css": "text/css", ".json": "application/json",
                            ".webp": "image/webp", ".jpg": "image/jpeg", ".mp3": "audio/mpeg", ".wav": "audio/wav"}.get(os.path.splitext(path)[1], "application/octet-stream")
                    return self.send(open(path, "rb").read(), kind)
            return self.send({"error": "not found"}, code=404)
        finally:
            db.close()

    def do_POST(self):
        if self.path == "/api/notes":
            n = int(self.headers.get("Content-Length", 0))
            return self.send(notes(json.loads(self.rfile.read(n) or b"{}")))
        if self.path == "/api/builds":
            n = int(self.headers.get("Content-Length", 0))
            return self.send(builds(json.loads(self.rfile.read(n) or b"{}")))
        return self.send({"error": "not found"}, code=404)


if __name__ == "__main__":
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8114
    print(f"encyclopedia on http://127.0.0.1:{port}/", flush=True)
    host = sys.argv[3] if len(sys.argv) > 3 else "127.0.0.1"                      # 0.0.0.0 to reach it from a phone on the same network
    ThreadingHTTPServer((host, port), H).serve_forever()
