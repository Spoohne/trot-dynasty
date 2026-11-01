"""Listing-fee test (log item 37): fee $0/$100k/$250k x AI sire-quality weight 0.6/0.3/0.0, 8 paired histories x 80
seasons. Each fee is compared with the $0 fee at the same AI weight, paired by history (seasons 40-80).
    python research/engine_lab/listing_l5.py <l5 dir>"""
import glob, json, math, os, statistics as st, sys
D = sys.argv[1]
W = dict(es=1.15, ls=0.85, sta=0.66, g=0.7)
soft = lambda x: x if x <= 5 else 5 + 2.5 * (1 - math.exp(-(x - 5) / 2.5))
def frozen(p):
    s = {t: soft(p[t]) for t in ("early_speed", "late_speed", "stamina", "gait")}
    return 1.15*s["early_speed"]+0.85*s["late_speed"]+0.66*s["stamina"]+0.7*min(s["gait"],3.0)+min(s["gait"],s["stamina"],0)
def trend(xs, ys):
    mx, my = st.mean(xs), st.mean(ys); return 10*sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs)
def load(v): return {s: json.load(open(os.path.join(D, f"{v}_{s}.json"))) for s in range(1, 9) if os.path.exists(os.path.join(D, f"{v}_{s}.json"))}
def m(r):
    rows=[x for x in r["rows"] if x["season"]>=40]; B=[b for b in r["births"] if len(b)>7]
    by={}
    for b in B:
        if b[0]>=40: by.setdefault(b[0],[]).append(frozen(b[7]))
    ss=sorted(by)
    pol=lambda k:[frozen(b[7]) for b in B if b[1]==k]
    e=r["rows"][-1].get("econ",{})
    return dict(slope=trend([x["season"] for x in rows],[x["racer_est"] for x in rows]), s_end=r["rows"][-1]["s_share"],
                frozen=trend(ss,[st.mean(by[s]) for s in ss]), top5=r["rows"][-1]["top5"],
                nick_edge=st.mean(pol("nick"))-st.mean(pol("ordinary")), public_edge=st.mean(pol("public"))-st.mean(pol("ordinary")),
                listed=st.mean(x.get("econ",{}).get("listed",0) for x in rows),
                fees_per_season=st.mean(x.get("econ",{}).get("list_fees_paid",0) for x in rows),
                player_minus_ai=st.mean((x["econ"]["strat_racer_pot"] or 0)-(x["econ"]["ai_racer_pot"] or 0) for x in rows if x.get("econ")))
out={}
for q in ("06","03","00"):
    ref={s:m(r) for s,r in load(f"open_f0_q{q}").items()}
    out[f"q{q} fee0"]={k:round(st.mean(v[k] for v in ref.values()),3) for k in next(iter(ref.values()))}
    for f in ("100","250"):
        A={s:m(r) for s,r in load(f"open_f{f}_q{q}").items()}; seeds=sorted(set(A)&set(ref))
        row={k:round(st.mean(A[s][k] for s in seeds),3) for k in A[seeds[0]]}
        for k in ("slope","s_end","frozen","top5"):
            d=[A[s][k]-ref[s][k] for s in seeds]; row[k+"_vs_fee0"]=f"{st.mean(d):+.3f} (se {st.stdev(d)/len(d)**.5:.3f})"
        out[f"q{q} fee{f}"]=row
json.dump(out,open("listing_l5.json","w"),indent=1)
for k,v in out.items(): print(k, v)
