"""A top-down lab viewer for a race3 record: the oval drawn to scale, every horse's body where the record puts it,
saddle-pad colors, a scrubber, and the auditor's findings. Lab only; the game's replay adapter comes later.
    from v3_view import write; write(rec, "out.html", title="...")"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import race3 as R

PADS = ["#d8322f", "#1f4fbf", "#f3f3f3", "#1f8f3f", "#1a1a1a", "#f2d233", "#e88fb0", "#9a9a9a", "#6b3fa0", "#7fc4e8"]


def write(rec, path, title="race3 lab", note=""):
    tr = R.TRACKS[rec["track"]]
    frames = [[[round(c, 1) for c in R.to_xy(tr, s, y)] + [round(v, 1), b] for (s, y, v, E, b) in fr] for fr in rec["frames"]]
    rail = [[round(c, 1) for c in R.to_xy(tr, u, 0.0)] for u in [i * tr.lap / 400 for i in range(401)]]
    outer = [[round(c, 1) for c in R.to_xy(tr, u, R.RAIL_Y + 4.5 * R.LANE)] for u in [i * tr.lap / 400 for i in range(401)]]
    wire = [list(R.to_xy(tr, R.FT_MILE, -3)), list(R.to_xy(tr, R.FT_MILE, R.RAIL_Y + 4.5 * R.LANE))]
    data = dict(frames=frames, rail=rail, outer=outer, wire=wire, names=rec["names"], dt=rec["dt"], pads=PADS,
                finish=rec["finish"], audit=R.audit(rec), events=rec["events"][:200], body=[R.BODY_L, R.BODY_W])
    html = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>body{margin:0;background:#070a14;color:#e6e8ec;font:14px 'Barlow Semi Condensed',system-ui,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:12px max(16px,env(safe-area-inset-left))}
h1{font:800 20px 'Barlow Condensed',system-ui;letter-spacing:.06em;text-transform:uppercase;margin:4px 0}
.note{color:#a4acb9;margin:0 0 8px}canvas{width:100%;background:#0b1430;border:1px solid #2b3a55;border-radius:4px}
.bar{display:flex;gap:10px;align-items:center;margin:8px 0}input[type=range]{flex:1}
button{background:#e8a33a;color:#2a1a03;border:0;border-radius:4px;padding:6px 14px;font-weight:700;cursor:pointer}
.panel{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:600px){.panel{grid-template-columns:1fr}}
.card{background:#111a2b;border:1px solid #2b3a55;border-radius:4px;padding:8px 10px;font-variant-numeric:tabular-nums}
.card b{color:#ffb347}</style>
<div class=wrap><h1>__TITLE__</h1><p class=note>__NOTE__</p><canvas id=c width=1100 height=620></canvas>
<div class=bar><button id=play>Pause</button><input id=t type=range min=0 value=0><span id=clock></span>
<select id=sp><option value=1>1x</option><option value=2 selected>2x</option><option value=4>4x</option></select>
<label><input id=zoom type=checkbox checked> follow the leader</label></div>
<div class=panel><div class=card id=fin></div><div class=card id=aud></div></div></div>
<script>const D=__DATA__;
const cv=document.getElementById('c'),g=cv.getContext('2d'),T=document.getElementById('t');T.max=D.frames.length-1;
let k=0,play=true,last=0;const all=D.outer.concat(D.rail);const X=all.map(p=>p[0]),Y=all.map(p=>p[1]);
const bx=[Math.min(...X)-20,Math.max(...X)+20,Math.min(...Y)-20,Math.max(...Y)+20];
function view(){if(!document.getElementById('zoom').checked)return {cx:(bx[0]+bx[1])/2,cy:(bx[2]+bx[3])/2,sc:Math.min(cv.width/(bx[1]-bx[0]),cv.height/(bx[3]-bx[2]))};
 const f=D.frames[k];let lx=0,ly=0;f.forEach(p=>{lx+=p[0];ly+=p[1]});return {cx:lx/f.length,cy:ly/f.length,sc:3.2}}
function draw(){const v=view(),P=(x,y)=>[cv.width/2+(x-v.cx)*v.sc,cv.height/2-(y-v.cy)*v.sc];
 g.fillStyle='#0b1430';g.fillRect(0,0,cv.width,cv.height);
 g.fillStyle='#3b2a1a';g.beginPath();D.outer.forEach((p,i)=>{const q=P(...p);i?g.lineTo(...q):g.moveTo(...q)});
 D.rail.slice().reverse().forEach(p=>g.lineTo(...P(...p)));g.fill();
 g.strokeStyle='#e6e8ec';g.lineWidth=2;g.beginPath();D.rail.forEach((p,i)=>{const q=P(...p);i?g.lineTo(...q):g.moveTo(...q)});g.stroke();
 g.strokeStyle='#e8a33a';g.lineWidth=3;g.beginPath();g.moveTo(...P(...D.wire[0]));g.lineTo(...P(...D.wire[1]));g.stroke();
 const f=D.frames[k],n=D.frames[Math.min(k+1,D.frames.length-1)];
 f.forEach((p,i)=>{const a=Math.atan2(n[i][1]-p[1],n[i][0]-p[0])||0;const q=P(p[0],p[1]);g.save();g.translate(...q);g.rotate(-a);
  const L=D.body[0]*v.sc,W=D.body[1]*v.sc;g.fillStyle=D.pads[i%10];g.strokeStyle=p[3]?'#e0704f':'#05070d';g.lineWidth=p[3]?3:1.5;
  g.fillRect(-L,-W/2,L,W);g.strokeRect(-L,-W/2,L,W);g.fillStyle=i==2||i==5?'#111':'#fff';g.font=`700 ${Math.max(9,W*0.9)}px sans-serif`;
  g.textAlign='center';g.textBaseline='middle';g.fillText(i+1,-L*0.35,0);g.restore()});
 document.getElementById('clock').textContent=(k*D.dt).toFixed(1)+' s';T.value=k}
function loop(ts){if(play&&ts-last>1000*D.dt/document.getElementById('sp').value){k=Math.min(k+1,D.frames.length-1);last=ts;if(k==D.frames.length-1)play=false}draw();requestAnimationFrame(loop)}
document.getElementById('play').onclick=e=>{play=!play;if(play&&k>=D.frames.length-1)k=0;e.target.textContent=play?'Pause':'Play'};
T.oninput=()=>{k=+T.value;play=false;document.getElementById('play').textContent='Play'};
document.getElementById('fin').innerHTML='<b>Finish</b><br>'+D.finish.map((x,i)=>`${i+1}. ${x[0]} &nbsp; ${x[1]?Math.floor(x[1]/60)+':'+(x[1]%60).toFixed(1).padStart(4,'0'):'—'}`).join('<br>');
document.getElementById('aud').innerHTML='<b>Part 0 audit</b><br>'+Object.entries(D.audit).map(([a,b])=>`${a.replaceAll('_',' ')}: ${b}`).join('<br>');
requestAnimationFrame(loop);</script>"""
    html = html.replace("__TITLE__", title).replace("__NOTE__", note).replace("__DATA__", json.dumps(data, separators=(",", ":")))
    open(path, "w", encoding="utf-8").write(html)
    return path
