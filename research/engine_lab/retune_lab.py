"""The retune lab (Patrick 2026-11-03: "I don't ever want to see a horse like Northern Star get beat by a marginally better
horse to the tune of 9+ lengths"). On a copy of the live world, with fresh randomness each race:
  1. Northern Star v Crimson Ivy, 1000 Invitational fields: who wins, by how much, and what trip each got.
  2. Single-bar interventions on 400 identical fields: the win chance one more bar of each stat buys.
  3. Pairs: two horses scored a length apart (0.1 unit) in a field of 8: how often the better one finishes ahead, and by how much.
    python research/engine_lab/retune_lab.py <save copy> base|new
new = the retune: closer's kick 1.10 -> 0.40, form 0.15 -> 0.08, the following trip open to a fast leaver."""
import copy, os, random, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import app                                                     # noqa: E402
c = app.c; O = c.outcome

RETUNES = {   # the trips worth little (Patrick: variety, not an advantage): lead, pocket, first-over, follow in units; the closer's kick; the line's depth; form
    "new": dict(k_close=0.40, s_form=0.08),
    "small": dict(A_lead=0.45, A_pocket=0.30, A_fo=0.15, A_fol=0.30, k_close=0.20, b_depth=0.10, s_form=0.08),
    "tiny": dict(A_lead=0.25, A_pocket=0.15, A_fo=0.05, A_fol=0.15, k_close=0.10, b_depth=0.06, s_form=0.06)}


def setup(path, mode):
    app.load(path); app.ME = 0
    if mode in RETUNES:
        O.P["mile"].update(RETUNES[mode]); O.P["half"]["s_form"] = RETUNES[mode]["s_form"]; O.FOLLOW_EARLY = True
    hs = [h for h in app.G["horses"] if not h.retired and h.age >= 3]
    for h in hs:
        h.freshness = 100.0
    return hs


def run(field, rng):
    O.rng = rng
    order = O.race(field, "mile")
    return order


def main(path, mode):
    hs = setup(path, mode)
    rng = random.Random(11)
    by = {h.name: h for h in hs}
    ns, ci = by["Northern Star"], by["Crimson Ivy"]
    pool = sorted((h for h in hs if h not in (ns, ci)), key=lambda h: O.pred_mile(O.bars(h, h.developed)))[:40]   # the top 40: Invitational company
    w = {"Northern Star": 0, "Crimson Ivy": 0}; margins = []; roles = {"Northern Star": {}, "Crimson Ivy": {}}
    for _ in range(1000):
        field = [ns, ci] + rng.sample(pool, 6); rng.shuffle(field)
        order = run(field, random.Random(rng.random()))
        w[order[0].name] = w.get(order[0].name, 0) + 1
        margins.append((ns.margin_l - ci.margin_l))
        for h in (ns, ci):
            roles[h.name][h.why["role"]] = roles[h.name].get(h.why["role"], 0) + 1
    print(f"[{mode}] Northern Star v Crimson Ivy, 1000 races: NS wins {w['Northern Star']/10:.0f}%, CI wins {w['Crimson Ivy']/10:.0f}%, others {(1000-w['Northern Star']-w['Crimson Ivy'])/10:.0f}%")
    print(f"        NS minus CI at the wire (lengths): median {st.median(margins):+.1f}, CI by 5+ L {sum(m >= 5 for m in margins)/10:.0f}%, NS by 5+ L {sum(m <= -5 for m in margins)/10:.0f}%, within 2 L {sum(abs(m) < 2 for m in margins)/10:.0f}%")
    print(f"        trips NS {dict(sorted(roles['Northern Star'].items(), key=lambda x:-x[1]))} | CI {dict(sorted(roles['Crimson Ivy'].items(), key=lambda x:-x[1]))}")
    # 2. interventions
    base_bars = O.bars
    out = {}
    fields = [rng.sample(hs, 8) for _ in range(400)]
    seeds = [rng.random() for _ in fields]
    for stat in (None, "kick", "cruise", "gate", "manners", "grit"):
        wins = 0
        for field, seed in zip(fields, seeds):
            subj = field[0]
            def bars(h, stats, _s=subj, _k=stat):
                b = base_bars(h, stats)
                if h is _s and _k:
                    b[_k] = min(13.0, b[_k] + 1.0)
                return b
            O.bars = bars
            order = run(list(field), random.Random(seed))
            wins += order[0] is subj
        O.bars = base_bars
        out[stat or "none"] = wins / 4
    print(f"        one more bar, win chance from {out['none']:.1f}%: " + ", ".join(f"{k} {out[k]-out['none']:+.1f}" for k in ("kick", "cruise", "gate", "manners", "grit")))
    # 3. pairs a length apart
    units = lambda h: O.class_units(O.bars(h, h.developed))
    ahead = 0; gaps = []; n = 0
    for _ in range(600):
        a = rng.choice(hs)
        bs = [h for h in hs if h is not a and 0.08 <= units(h) - units(a) <= 0.12]
        if not bs: continue
        b = rng.choice(bs); n += 1
        field = [a, b] + rng.sample([h for h in hs if h not in (a, b)], 6); rng.shuffle(field)
        run(field, random.Random(rng.random()))
        ahead += b.margin_l < a.margin_l; gaps.append(a.margin_l - b.margin_l)
    print(f"        pairs a length apart ({n}): the better horse ahead {ahead/n:.0%}; its margin median {st.median(gaps):+.1f} L, 90th {sorted(gaps)[int(.9*n)]:+.1f}, worst {max(gaps):+.1f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "base")
