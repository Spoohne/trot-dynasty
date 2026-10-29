// Record a replay page with its broadcast graphics to MP4: headless Chrome screencasts the page (the stage made
// full-window), then ffmpeg turns the timestamped frames into constant-rate video.
//   node art/record_replay.js <url> <out.mp4> [seconds=165] [width=1920] [height=1080]
const { spawn, execFileSync } = require("child_process");
const fs = require("fs"), path = require("path"), os = require("os");
const [url, out, secs = 165, W = 1920, H = 1080] = process.argv.slice(2);
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const FFMPEG = "C:/Users/spooh/AppData/Local/Programs/Python/Python314/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe";
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "rec-")), PORT = 9333;
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${PORT}`, `--window-size=${W},${H}`, `--user-data-dir=${dir}/prof`,
  "--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required", "--hide-scrollbars", "about:blank"]);
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  let tgt; for (let i = 0; i < 50 && !tgt; i++) { await sleep(200); try { tgt = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find(t => t.type === "page"); } catch {} }
  const ws = new WebSocket(tgt.webSocketDebuggerUrl); await new Promise(r => ws.onopen = r);
  let id = 0; const wait = {}, frames = [];
  const send = (method, params = {}) => new Promise(r => { wait[++id] = r; ws.send(JSON.stringify({ id, method, params })); });
  ws.onmessage = ({ data }) => { const m = JSON.parse(data);
    if (m.id && wait[m.id]) { wait[m.id](m.result); delete wait[m.id]; }
    if (m.method === "Page.screencastFrame") { const f = path.join(dir, `f${String(frames.length).padStart(6, "0")}.jpg`);
      fs.writeFileSync(f, Buffer.from(m.params.data, "base64")); frames.push([f, m.params.metadata.timestamp]);
      send("Page.screencastFrameAck", { sessionId: m.params.sessionId }); } };
  await send("Page.enable"); await send("Emulation.setDeviceMetricsOverride", { width: +W, height: +H, deviceScaleFactor: 1, mobile: false });
  // the stage alone, filling the window; the sound/camera buttons hidden
  await send("Page.addScriptToEvaluateOnNewDocument", { source: `addEventListener("DOMContentLoaded", () => { const s = document.createElement("style");
    s.textContent = ".stage{position:fixed!important;inset:0!important;width:100vw!important;height:100vh!important;max-width:none!important;aspect-ratio:auto!important;margin:0!important;border-radius:0!important;z-index:9999}.views,.skip{display:none!important}body{overflow:hidden}";
    document.head.appendChild(s); setTimeout(() => dispatchEvent(new Event("resize")), 50); });` });
  await send("Page.navigate", { url }); await sleep(1500);
  await send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: +W, maxHeight: +H, everyNthFrame: 1 });
  await sleep(secs * 1000); await send("Page.stopScreencast"); ws.close(); chrome.kill();
  // concat list: each frame held until the next one arrived
  const list = frames.map(([f, t], i) => `file '${f.replace(/\\/g, "/")}'\nduration ${((frames[i + 1]?.[1] ?? t + 1 / 30) - t).toFixed(4)}`).join("\n");
  fs.writeFileSync(path.join(dir, "list.txt"), list + `\nfile '${frames.at(-1)[0].replace(/\\/g, "/")}'\n`);
  execFileSync(FFMPEG, ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", path.join(dir, "list.txt"), "-vf", "fps=30,format=yuv420p",
    "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-movflags", "+faststart", out]);
  console.log(`${frames.length} frames over ${(frames.at(-1)[1] - frames[0][1]).toFixed(1)}s -> ${out}`);
  fs.rmSync(dir, { recursive: true, force: true });
})().catch(e => { console.error(e); chrome.kill(); process.exit(1); });
