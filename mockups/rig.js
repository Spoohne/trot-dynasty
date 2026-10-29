// A cut-out ("paper doll") horse and sulky, animated in code. One set of parts, made locally;
// every runner gets its own coat tint and driver silks, and the gait comes from its ground speed.
const RIG = { ready: false, k: .5 };                                    // parts are pre-scaled to half size
RIG.COATS = { "#5a3420": [176, 98, 54], "#8a4a26": [204, 112, 58], "#241a16": [74, 64, 62], "#8c8f95": [236, 236, 238], "#3d2a1e": [124, 80, 52] };
RIG.LEGS = ["hind_far", "fore_far", "hind_near", "fore_near"];

RIG.load = async () => {
  const j = await (await fetch("/mock/rig/rig.json")).json();
  const img = src => new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = "/mock/rig/" + src; });
  const names = Object.keys(j.parts);
  const raw = Object.fromEntries(await Promise.all(names.map(async n => [n, await img(n + ".png")])));
  const sulky = await img("sulky.png"), wheel = await img("wheel.png");
  const half = (im, w = im.width * RIG.k, h = im.height * RIG.k) => { const c = document.createElement("canvas"); c.width = Math.ceil(w); c.height = Math.ceil(h); c.getContext("2d").drawImage(im, 0, 0, c.width, c.height); return c; };
  // a coat is the grey horse multiplied by a color; far legs a shade darker, they're in shadow
  const tint = (src, rgb, dark = 1) => {
    const c = half(src), g = c.getContext("2d");
    g.globalCompositeOperation = "multiply"; g.fillStyle = `rgb(${rgb.map(v => v * dark | 0)})`; g.fillRect(0, 0, c.width, c.height);
    g.globalCompositeOperation = "destination-in"; g.drawImage(src, 0, 0, c.width, c.height); return c;
  };
  RIG.coat = {};
  for (const [hex, rgb] of Object.entries(RIG.COATS)) {
    RIG.coat[hex] = Object.fromEntries(names.map(n => [n, tint(raw[n], rgb, n.includes("_far") ? .62 : 1)]));
  }
  // silks: the driver's blue jacket re-dyed to the saddle-pad color, shading kept
  const base = half(sulky), bd = base.getContext("2d").getImageData(0, 0, base.width, base.height);
  RIG.silks = RACE.PAD.map(hex => {
    const t = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)), c = document.createElement("canvas");
    c.width = base.width; c.height = base.height; const g = c.getContext("2d"), d = new ImageData(new Uint8ClampedArray(bd.data), bd.width, bd.height), p = d.data;
    for (let i = 0; i < p.length; i += 4) {
      const r = p[i], gg = p[i + 1], b = p[i + 2];
      if (p[i + 3] > 0 && b > r + 45 && b > gg + 15) { const l = Math.min(1.25, (r * .3 + gg * .59 + b * .11) / 95); p[i] = t[0] * l; p[i + 1] = t[1] * l; p[i + 2] = t[2] * l; }
    }
    g.putImageData(d, 0, 0); return c;
  });
  RIG.wheel = half(wheel);
  RIG.j = j; RIG.ready = true;
};

// Draw one runner. (x, ground) is where its forefeet meet the dirt, px per foot is s; phase from distance run.
RIG.draw = (ctx, h, x, ground, s, t) => {
  if (!RIG.ready) return ground - 6 * s;
  const j = RIG.j, PXFT = 141, sc = s / PXFT / RIG.k;                   // horse art: 141 px to the foot at full size
  const parts = RIG.coat[RACE.H[h.i][1]] || RIG.coat["#5a3420"];
  const p = h.d / 19 * Math.PI * 2 + h.i * 1.3;                        // one stride per 19 ft
  const bob = Math.abs(Math.sin(p)) * 2.2;
  ctx.save();
  ctx.translate(x - 700 * RIG.k * sc, ground - j.ground * RIG.k * sc - bob * sc);
  ctx.scale(sc, sc);
  const K = RIG.k, P = j.parts;
  const leg = name => {
    const near = name.includes("near"), fore = name.startsWith("fore");
    const ph = p + (near ? 0 : Math.PI);                                // pacing: both legs on a side move together
    const up = -(fore ? .42 : .34) * Math.sin(ph);                     // forward swing is negative (anticlockwise)
    const fold = (fore ? .9 : .55) * Math.max(0, Math.cos(ph)) ** 1.6;  // the knee folds while the leg comes forward
    const u = P[name + "_upper"], l = P[name + "_lower"];
    ctx.save();
    ctx.translate(u.pivot[0] * K, u.pivot[1] * K); ctx.rotate(up); ctx.translate(-u.pivot[0] * K, -u.pivot[1] * K);
    ctx.drawImage(parts[name + "_upper"], u.at[0] * K, u.at[1] * K);
    ctx.translate(l.pivot[0] * K, l.pivot[1] * K); ctx.rotate(fore ? fold : -fold * .6); ctx.translate(-l.pivot[0] * K, -l.pivot[1] * K);
    ctx.drawImage(parts[name + "_lower"], l.at[0] * K, l.at[1] * K);
    ctx.restore();
  };
  leg("hind_far"); leg("fore_far");
  ctx.drawImage(parts.body, 0, 0);
  leg("hind_near"); leg("fore_near");
  // harness and the number cloth, drawn over the coat
  ctx.fillStyle = "#15181d"; ctx.fillRect(545 * K, 330 * K, 26 * K, 225 * K);
  ctx.fillRect(250 * K, 268 * K, 330 * K, 14 * K);
  ctx.fillStyle = RACE.PAD[h.i]; ctx.fillRect(400 * K, 300 * K, 120 * K, 120 * K);
  ctx.strokeStyle = "rgba(0,0,0,.5)"; ctx.lineWidth = 6 * K; ctx.strokeRect(400 * K, 300 * K, 120 * K, 120 * K);
  ctx.fillStyle = RACE.DARK.includes(h.i + 1) ? "#111" : "#fff"; ctx.font = `700 ${90 * K}px system-ui`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.fillText(h.i + 1, 460 * K, 364 * K); ctx.textAlign = "start"; ctx.textBaseline = "alphabetic";
  // the sulky: hitched behind, tilted so the shafts run up to the girth; the wheel turns with the ground
  const SK = .82, hub = j.sulky.hub, ax = -120 * K, ay = (j.ground - j.sulky.r * SK) * K + bob;
  ctx.save();
  ctx.translate(ax, ay); ctx.rotate(-.2); ctx.scale(SK, SK);
  ctx.drawImage(RIG.silks[h.i], -hub[0] * K, -hub[1] * K);
  ctx.save(); ctx.rotate(h.d / (Math.PI * 2.3) * Math.PI * 2 % (Math.PI * 2)); ctx.drawImage(RIG.wheel, -RIG.wheel.width / 2, -RIG.wheel.height / 2); ctx.restore();
  ctx.restore();
  ctx.restore();
  return ground - 6.2 * s;                                             // where the top of the runner is, for a name tag
};
