"""Run the circuit forward from a save and write a searchable archive of every horse.
    python archive.py <save.pkl> <years> <out.html>

Runs on a copy of the save (the original is never written). Keeps every horse that ever
existed, with pedigree, season-by-season results, recent charts and offspring, in one
self-contained HTML page: search, sort, click through.
"""
import json
import os
import shutil
import sys
import tempfile

import app
import circuit as c
import economy as e


def collect(years):
    seen = {}        # id -> horse
    seasons = {}     # id -> {year: [starts, wins, earnings]}
    charts = {}      # id -> last 30 chart lines
    prev = {}        # id -> (starts, wins, earnings) at the last tick
    for _ in range(years * c.YEAR):
        app.tick()
        year = app.G["day"] // c.YEAR + 1
        for h in app.G["horses"]:
            seen[h.id] = h
            st_, w, ea = h.starts, h.wins, h.earnings
            p = prev.get(h.id, (st_, w, ea) if h.id not in seen or h.id not in prev else prev[h.id])
            if h.id not in prev:
                prev[h.id] = (st_, w, ea)
                continue
            d = (st_ - p[0], w - p[1], ea - p[2])
            if d[0]:
                s = seasons.setdefault(h.id, {}).setdefault(year, [0, 0, 0.0])
                s[0] += d[0]; s[1] += d[1]; s[2] += d[2]
                last = h.form[-1] if getattr(h, "form", None) else None
                if last:
                    ch = charts.setdefault(h.id, [])
                    ch.append(f"Y{year} W{app.G['day'] % c.YEAR + 1}: {last}")
                    del ch[:-30]
            prev[h.id] = (st_, w, ea)
    return seen, seasons, charts


def best_of(h):
    b = getattr(h, "best", 999)
    return c.mile_time(b) if b < 999 else ""


def record(h, seasons, charts, alive):
    return {
        "id": h.id, "name": h.name, "sex": h.sex, "coat": getattr(h, "coat", "") or "",
        "age": h.age, "alive": h.id in alive, "retired": bool(h.retired),
        "sire": h.sire.name if h.sire else "", "dam": h.dam.name if h.dam else "",
        "starts": h.starts, "wins": h.wins, "earnings": round(h.earnings),
        "best": best_of(h), "bestsec": round(getattr(h, "best", 999), 2),
        "tier": h.tier, "peak": getattr(h, "peak_tier", h.tier), "owner": h.owner,
        "grade": getattr(h, "rarity", "") or "",
        "seasons": {y: [s[0], s[1], round(s[2])] for y, s in sorted(seasons.get(h.id, {}).items())},
        "charts": charts.get(h.id, []),
    }


HTML = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>Circuit archive</title><style>
body{font-family:system-ui,sans-serif;margin:0;background:#f4f1ea;color:#222}.w{max-width:1000px;margin:0 auto;padding:14px}
h1{font-size:20px}input,select{font-size:14px;padding:6px;border:1px solid #ccc;border-radius:6px}
table{width:100%;border-collapse:collapse;font-size:13px;background:#fff}td,th{padding:5px 6px;border-bottom:1px solid #eee;text-align:left;white-space:nowrap}
th{cursor:pointer;background:#faf8f3;position:sticky;top:0}th.on{color:#1d4ed8}a{color:#1d4ed8;text-decoration:none;cursor:pointer}
.tier{display:inline-block;width:22px;text-align:center;border-radius:4px;color:#fff;font-weight:700}
.S{background:#b45309}.A{background:#1d4ed8}.B{background:#047857}.C{background:#6b7280}.D{background:#9ca3af}
.panel{position:fixed;inset:0;background:#0008;display:none;align-items:flex-start;justify-content:center;overflow:auto;padding:20px}
.panel.on{display:flex}.sheet{background:#fff;border-radius:10px;max-width:760px;width:100%;padding:16px}
.pkids{display:flex;flex-direction:column;gap:6px;justify-content:center}.pgen{display:flex;align-items:center;gap:6px}
.pbox{border:1px solid #d6d3cc;border-radius:6px;padding:3px 7px;background:#faf8f3;font-size:12px;white-space:nowrap;display:flex;gap:8px}
.pbox.unk{color:#999;border-style:dashed}.chart{font-size:12px;color:#333}.sub{color:#555;font-size:13px}.ped{overflow-x:auto}
.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0}
</style></head><body><div class=w>
<h1>Circuit archive · __YEARS__ seasons · __N__ horses</h1>
<div class=bar><input id=q placeholder='search name, sire, dam' size=28>
<select id=f><option value=''>everyone</option><option value='alive'>alive now</option><option value='racing'>racing now</option><option value='retired'>at stud / broodmare</option><option value='m'>males</option><option value='f'>females</option></select>
<span class=sub id=count></span></div>
<table><thead><tr>
<th data-k=name>Name</th><th data-k=sex>Sex</th><th data-k=age>Age</th><th data-k=tier>Tier</th><th data-k=peak>Peak</th><th data-k=sire>Sire</th><th data-k=dam>Dam</th>
<th data-k=starts>Starts</th><th data-k=wins>Wins</th><th data-k=earnings>Earnings</th><th data-k=bestsec>Best</th><th data-k=foals>Foals</th><th data-k=foalearn>Foals earned</th>
</tr></thead><tbody id=rows></tbody></table></div>
<div class=panel id=panel onclick="if(event.target===this)this.classList.remove('on')"><div class=sheet id=sheet></div></div>
<script>
const H=__DATA__;const byName={};H.forEach(h=>byName[h.name]=h);
H.forEach(h=>{h.foals=0;h.foalearn=0});H.forEach(h=>{for(const p of [h.sire,h.dam]){const q=byName[p];if(q){q.foals++;q.foalearn+=h.earnings}}});
const T={S:5,A:4,B:3,C:2,D:1};let key='earnings',dir=-1;
const money=n=>'$'+Math.round(n).toLocaleString();
function render(){const q=document.getElementById('q').value.toLowerCase(),f=document.getElementById('f').value;
let rows=H.filter(h=>(!q||h.name.toLowerCase().includes(q)||h.sire.toLowerCase().includes(q)||h.dam.toLowerCase().includes(q))&&
(f===''||(f==='alive'&&h.alive)||(f==='racing'&&h.alive&&!h.retired)||(f==='retired'&&h.alive&&h.retired)||(f==='m'&&h.sex==='m')||(f==='f'&&h.sex==='f')));
rows.sort((a,b)=>{let x=a[key],y=b[key];if(key==='tier'||key==='peak'){x=T[x];y=T[y]}if(typeof x==='string'){return dir*x.localeCompare(y)}return dir*((x>y)-(x<y))});
document.getElementById('count').textContent=rows.length+' horses';
document.getElementById('rows').innerHTML=rows.slice(0,400).map(h=>`<tr><td><a onclick="show('${h.name}')">${h.name}</a>${h.alive?'':' <span class=sub>†</span>'}</td><td>${h.sex}</td><td>${h.age}</td>
<td><span class="tier ${h.tier}">${h.tier}</span></td><td><span class="tier ${h.peak}">${h.peak}</span></td><td>${h.sire?`<a onclick="show('${h.sire}')">${h.sire}</a>`:'<span class=sub>imported</span>'}</td><td>${h.dam?`<a onclick="show('${h.dam}')">${h.dam}</a>`:'<span class=sub>imported</span>'}</td>
<td>${h.starts}</td><td>${h.wins}</td><td>${money(h.earnings)}</td><td>${h.best||'—'}</td><td>${h.foals||''}</td><td>${h.foals?money(h.foalearn):''}</td></tr>`).join('')+(rows.length>400?'<tr><td colspan=13 class=sub>first 400 shown; narrow the search</td></tr>':'');
document.querySelectorAll('th').forEach(t=>t.classList.toggle('on',t.dataset.k===key))}
function box(n){const h=byName[n];return h?`<div class=pbox><a onclick="show('${h.name}')">${h.name}</a><span>${h.best||'—'}</span></div>`:`<div class='pbox unk'>imported</div>`}
function branch(n,g){if(g===0)return box(n);const h=byName[n];return `<div class=pgen>${box(n)}<div class=pkids>${branch(h?h.sire:'',g-1)}${branch(h?h.dam:'',g-1)}</div></div>`}
function show(n){const h=byName[n];if(!h)return;const kids=H.filter(k=>k.sire===n||k.dam===n).sort((a,b)=>b.earnings-a.earnings);
const seasons=Object.entries(h.seasons).map(([y,s])=>`<tr><td>Y${y}</td><td>${s[0]}</td><td>${s[1]}</td><td>${money(s[2])}</td></tr>`).join('');
document.getElementById('sheet').innerHTML=`<h2 style='margin:0'>${h.name} <span class="tier ${h.tier}">${h.tier}</span> <span class=sub>peak</span> <span class="tier ${h.peak}">${h.peak}</span></h2>
<div class=sub>${h.age}-year-old ${h.coat} ${h.sex==='m'?'horse':'mare'} · ${h.alive?(h.retired?'retired':'racing'):'gone'} · ${h.starts} starts, ${h.wins} wins, ${money(h.earnings)}, best ${h.best||'—'}${h.grade?' · house roll: '+h.grade:''}</div>
<h3>Pedigree</h3><div class=ped><div class=pkids>${branch(h.sire,2)}${branch(h.dam,2)}</div></div>
<h3>Seasons</h3>${seasons?`<table><tr><th>Year</th><th>Starts</th><th>Wins</th><th>Earnings</th></tr>${seasons}</table>`:'<div class=sub>no starts recorded in the archive window</div>'}
<h3>Recent charts</h3>${h.charts.length?h.charts.slice().reverse().map(x=>`<div class=chart>${x}</div>`).join(''):'<div class=sub>none</div>'}
<h3>Offspring · ${kids.length}</h3>${kids.length?`<table><tr><th>Name</th><th>Sex</th><th>Tier</th><th>Record</th><th>Best</th><th>Earnings</th></tr>${kids.slice(0,60).map(k=>`<tr><td><a onclick="show('${k.name}')">${k.name}</a></td><td>${k.sex}</td><td><span class="tier ${k.tier}">${k.tier}</span></td><td>${k.starts}-${k.wins}</td><td>${k.best||'—'}</td><td>${money(k.earnings)}</td></tr>`).join('')}</table>`:'<div class=sub>none</div>'}
<p><a onclick="document.getElementById('panel').classList.remove('on')">close</a></p>`;
document.getElementById('panel').classList.add('on');document.getElementById('panel').scrollTop=0}
document.querySelectorAll('th').forEach(t=>t.onclick=()=>{if(key===t.dataset.k)dir=-dir;else{key=t.dataset.k;dir=(key==='name'||key==='sire'||key==='dam'||key==='bestsec')?1:-1}render()});
document.getElementById('q').oninput=render;document.getElementById('f').onchange=render;render();
</script></body></html>"""


if __name__ == "__main__":
    src, years, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    tmp = os.path.join(tempfile.gettempdir(), "archive_run.pkl")
    shutil.copy(src, tmp)
    app.SAVE = tmp
    app.load()
    app.save = lambda: None                                   # never write the copy back, let alone the original
    seen, seasons, charts = collect(years)
    alive = {h.id for h in app.G["horses"]}
    data = [record(h, seasons, charts, alive) for h in seen.values()]
    html = HTML.replace("__DATA__", json.dumps(data, separators=(",", ":"))).replace("__YEARS__", str(years)).replace("__N__", str(len(data)))
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{len(data)} horses over {years} seasons -> {out} ({os.path.getsize(out) / 1e6:.1f} MB)")
