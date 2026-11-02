"""Review page for casting (DECISIONS 229): fresh outcome-model races, each drawn by the caster, on the live replay page.
The Field panel shows each horse's big-four card and the trip the model gave it.
    python v5_cast_page.py [races] [seed]      writes v5/cast/index.html"""
import os, sys
import numpy as np
import v5_cast as K
from v5_library import page_race
from v3_replay import build_page

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "v5", "cast")
ROLE = ["lead", "pocket", "first-over", "follow", "line"]
TRAITS = ("gate", "cruise", "kick", "manners", "grit")

if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 24; seed = int(sys.argv[2]) if len(sys.argv) > 2 else 11
    races, made = {"half": [], "mile": []}, []
    for k, res in enumerate(K.model_races(N, 700 + seed)):
        if len(made) == 12:
            break
        c = K.cast(res, seed=k)
        print(k, K.story_of(res), "cast" if c else "-", c and c["tries"])
        if not c:
            continue
        v = dict(c, role={i: ROLE[r] for i, r in enumerate(res["role"])}, story=K.story_of(res), cast=True)
        n = len(made)
        r = page_race(v, f"Cast race {n + 1} · {K.story_of(res).replace('_', '-')}", 20 + n)
        for h in r["horses"]:
            i = h["post"] - 1
            h["traits"] = dict(zip(TRAITS, res["traits"][i])); h["trip"] = ROLE[res["role"][i]]
        r["note"] = "The outcome model decided this race; the caster drew it. Order and margins are the model's; trips are the model's."
        races["half" if n < 6 else "mile"].append(r); made.append(K.story_of(res))
    links = "".join(f'<a href="#{"half" if k < 6 else "mile"}{k % 6 + 1}" style="background:#111a2b;color:#e8a33a;border:1px solid #2b3a55;padding:6px 8px;border-radius:4px;text-decoration:none">{k + 1} {s.replace("_", "-")}</a>'
                    for k, s in enumerate(made))
    page = build_page(races, links, OUT).replace("<title>Engine Test Replay</title>", "<title>Cast Replays</title>")
    for old, new in (("Bars as the game would show them. Race-day form is how the horse is going today (added to Speed, Stam and Finish for this race). Grit is hidden in the game.", "${s.note || ''}"),
                     ('+ bar("Speed", h.traits.gate) + bar("Stam", h.traits.cruise) + bar("Finish", h.traits.kick) + bar("Manners", h.traits.manners)\n    + bar("Grit", h.traits.grit, true)',
                      '+ bar("Speed", (.242 * h.traits.gate + .391 * h.traits.kick) / .633) + bar("Stam", h.traits.cruise) + bar("Grit", h.traits.grit) + bar("Manners", h.traits.manners)'),
                     ("<div class=\"nt\">Race-day form ${f(h.form)}</div>", "<div class=\"nt\">Trip: ${h.trip}</div>")):
        assert old in page, old
        page = page.replace(old, new)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)
    print("page", len(made), "races", round(os.path.getsize(os.path.join(OUT, "index.html")) / 1e6, 2), "MB")
