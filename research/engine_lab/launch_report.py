"""Reads the launch-scenario worlds (launch.py) and answers Patrick's questions, seeds averaged per player count:
does the player herd drift, does S+ stay rare, does pedigree matter, do a few sires take over, how far do players pull
away from the AI Filler Barns, can a late joiner compete, and does any kind of player break the world.

  python research/engine_lab/launch_report.py            every research/engine_lab/launch/p*_s*.db
"""
import glob
import json
import os
import sqlite3
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
SPANS = ((0, 9, "1-10"), (10, 24, "11-25"), (25, 49, "26-50"), (50, 74, "51-75"), (75, 99, "76-100"))


def worlds():
    out = {}
    for path in sorted(glob.glob(os.path.join(HERE, "launch", "p*_s*.db"))):
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        players = int(os.path.basename(path)[1:].split("_")[0])
        rows = [json.loads(j) for (j,) in db.execute("SELECT json FROM world ORDER BY season")]
        out.setdefault(players, []).append((path, db, rows))
    return out


def avg(vals):
    vals = [v for v in vals if v is not None]
    return st.mean(vals) if vals else None


def f(v, fmt):
    return "  -  " if v is None else format(v, fmt)


def span_mean(rows, lo, hi, get):
    return avg([get(m) for m in rows if lo <= m["season"] <= hi])


def main():
    W = worlds()
    for players, runs in sorted(W.items()):
        done = min(len(r) for _, _, r in runs)
        print(f"\n=== {players} players: {len(runs)} worlds, {done} seasons each ===")
        print(f"{'seasons':8}{'players':>8}{'S+ all':>8}{'S+ fill':>9}{'S+ bred':>8}{'fill pot':>9}{'bred pot':>9}{'foal pot':>9}"
              f"{'foals':>7}{'sires':>6}{'top5':>6}{'own sire':>9}{'listed':>7}{'ped r':>7}{'herd top':>9}{'herd mid':>9}{'bots $':>9}{'top barn':>9}")
        g = lambda m, grp, k: m["groups"].get(grp, {}).get(k)
        for lo, hi, lab in SPANS:
            if lo >= done:
                continue
            col = lambda get: avg([span_mean(r, lo, hi, get) for _, _, r in runs])
            print(f"{lab:8}{f(col(lambda m: m['players']), '8.0f')}{f(col(lambda m: m['s_plus_all']), '8.1%')}"
                  f"{f(col(lambda m: g(m, 'ai', 's_plus')), '9.1%')}{f(col(lambda m: g(m, 'bred', 's_plus')), '8.1%')}"
                  f"{f(col(lambda m: g(m, 'ai', 'pot')), '9.2f')}{f(col(lambda m: g(m, 'bred', 'pot')), '9.2f')}"
                  f"{f(col(lambda m: m.get('foal_pot')), '9.2f')}{f(col(lambda m: m['foals']), '7.0f')}{f(col(lambda m: m.get('sires_used')), '6.0f')}"
                  f"{f(col(lambda m: m.get('top5_share')), '6.0%')}{f(col(lambda m: m.get('own_sire')), '9.0%')}{f(col(lambda m: m['book']['listed']), '7.0f')}"
                  f"{f(col(lambda m: m.get('pedigree_r')), '7.2f')}{f(col(lambda m: m.get('herd_top')), '9.2f')}{f(col(lambda m: m.get('herd_median')), '9.2f')}{f(col(lambda m: m['player_purse_share']), '9.0%')}{f(col(lambda m: m['top_barn_share']), '9.1%')}")
        worst = max((m["top_barn_share"], m["season"], os.path.basename(p)) for p, _, r in runs for m in r)
        print(f"biggest single barn: {worst[0]:.1%} of all purses (season {worst[1] + 1}, {worst[2]})")
        # each kind of player: purses a season while active, and how long it stays
        print("kind        purses a season   seasons stayed   still there at the end")
        for strat in ("chaser", "studfarm", "flipper", "casual"):
            pur, stay, left = [], [], []
            for _, db, r in runs:
                pur += [p for (p,) in db.execute("SELECT purses FROM bots WHERE strat=? AND (quit IS NULL OR quit > season)", (strat,))]
                for a, q in db.execute("SELECT arrived, MAX(quit) FROM bots WHERE strat=? GROUP BY owner", (strat,)):
                    stay.append((q if q is not None else len(r)) - a)
                    left.append(q is None)
            print(f"{strat:10} {f(avg(pur), '>14,.0f')}   {f(avg(stay), '>12.1f')}   {sum(left):>10} of {len(left)}")
        # a late joiner: purses in each of its first three seasons, launch-day players vs ones arriving from season 11 on
        print("first three seasons' purses     launch-day players      joined in season 11+")
        for k in range(3):
            early, late = [], []
            for _, db, r in runs:
                for arrived, p in db.execute("SELECT arrived, purses FROM bots WHERE season = arrived + ? AND (quit IS NULL OR quit > season)", (k,)):
                    (early if arrived <= 1 else late if arrived >= 10 else []).append(p)
            print(f"  season {k + 1} as a player        {f(avg(early), '>12,.0f')}           {f(avg(late), '>12,.0f')}")


if __name__ == "__main__":
    main()
