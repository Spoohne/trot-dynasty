"""Does the card tell the story? Reads an encyclopedia world and answers Patrick's test (2026-11-02): Speed sets how fast a
horse can finish, Speed and Stamina tell most of the story, and the best horses look Speed >> Stamina >>> Grit >>>>> Manners.

  python research/encyclopedia/proof.py [db]
"""
import os
import sqlite3
import statistics as st
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "world100.db")
db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
done = int(db.execute("SELECT v FROM meta WHERE k='season_done'").fetchone()[0]) - 1
# each horse's peak season (best rating), complete careers, 20+ starts
rows = db.execute("""SELECT h.name, h.earnings, h.best, h.wins, h.starts, json_array_length(h.titles), s.speed, s.stamina, s.grit, s.manners,
    s.g_speed, s.g_stamina, s.g_grit, s.g_manners, s.gate FROM horses h JOIN seasons s ON s.id = h.id
    AND s.season = (SELECT season FROM seasons WHERE id = h.id ORDER BY rating DESC LIMIT 1)
    WHERE h.starts >= 20 AND (h.retired = 1 OR h.last_season < ?) AND h.best < 900""", (done,)).fetchall()
col = lambda i: [r[i] for r in rows]
print(f"{len(rows):,} complete careers (20+ starts), each horse's card at its peak season\n")
print("How fast it finishes: correlation with its best mile (negative = a bigger bar runs faster)")
for name, i in (("Speed", 6), ("Stamina", 7), ("Grit", 8), ("Manners", 9), ("gate (not on card)", 14)):
    print(f"  {name:20} r = {st.correlation(col(i), col(2)):+.2f}")
print("\nHow good a career: correlation with career purses")
for name, i in (("Speed", 6), ("Stamina", 7), ("Grit", 8), ("Manners", 9), ("gate (not on card)", 14)):
    print(f"  {name:20} r = {st.correlation(col(i), col(1)):+.2f}")
both = [a + b for a, b in zip(col(6), col(7))]
print(f"  {'Speed + Stamina':20} r = {st.correlation(both, col(1)):+.2f}")
top = sorted(rows, key=lambda r: -r[1])[:50]
mean = lambda rs, i: st.mean(r[i] for r in rs)
print("\nThe 50 richest horses vs everyone (average bar at peak)")
print(f"  {'':10} {'Speed':>7} {'Stamina':>8} {'Grit':>6} {'Manners':>8}")
for lab, rs in (("top 50", top), ("everyone", rows)):
    print(f"  {lab:10} {mean(rs, 6):7.1f} {mean(rs, 7):8.1f} {mean(rs, 8):6.1f} {mean(rs, 9):8.1f}")
order = sum(r[6] >= r[7] >= r[8] for r in top)
best_is = {k: sum(max(range(4), key=lambda j: r[6 + j]) == j0 for r in top) for j0, k in enumerate(("Speed", "Stamina", "Grit", "Manners"))}
print(f"  top 50 whose bars run Speed >= Stamina >= Grit: {order}; their single best bar: {best_is}")
print(f"  top 50 graded S or better on Speed: {sum(r[10] in ('S', 'S+', 'Galaxy') for r in top)}, on Stamina: {sum(r[11] in ('S', 'S+', 'Galaxy') for r in top)}")
fast = sorted(rows, key=lambda r: r[2])[:20]
print("\nThe 20 fastest best miles: their peak Speed bars")
print("  " + ", ".join(f"{r[0]} {int(r[2] // 60)}:{r[2] % 60:04.1f} Spd {r[6]:.1f}" for r in fast))
print("\nThe 10 richest: peak card (Speed / Stamina / Grit / Manners) and career")
for r in top[:10]:
    print(f"  {r[0]:18} {r[6]:4.1f} {r[10]:6} / {r[7]:4.1f} {r[11]:6} / {r[8]:4.1f} {r[12]:6} / {r[9]:4.1f} {r[13]:6}  ${r[1]:>12,.0f}  {r[3]}-{r[4]}  best {int(r[2] // 60)}:{r[2] % 60:04.1f}  titles {r[5]}")
