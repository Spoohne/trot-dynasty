"""Meshy image-to-3D from a local image. Usage: meshy.py image.png out_prefix [polycount] [textured 1/0]
Reads MESHY_API_KEY from the environment or ~/.claude/settings.json, submits, polls, downloads glb+fbx."""
import base64, json, os, sys, time, urllib.request
img, out = sys.argv[1], sys.argv[2]
poly = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
tex = sys.argv[4] != "0" if len(sys.argv) > 4 else True
key = os.environ.get("MESHY_API_KEY") or json.load(open(os.path.expanduser("~/.claude/settings.json"), encoding="utf-8"))["env"]["MESHY_API_KEY"]
H = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
API = "https://api.meshy.ai/openapi/v1/image-to-3d"
ext = img.rsplit(".", 1)[-1].lower().replace("jpg", "jpeg")
data = f"data:image/{ext};base64," + base64.b64encode(open(img, "rb").read()).decode()
body = {"image_url": data, "ai_model": "latest", "topology": "triangle", "target_polycount": poly, "should_remesh": True,
        "should_texture": tex, "enable_pbr": False, "target_formats": ["glb", "fbx"]}
req = urllib.request.Request(API, json.dumps(body).encode(), H)
try:
    tid = json.load(urllib.request.urlopen(req))["result"]
except urllib.error.HTTPError as e:
    sys.exit("submit failed: " + e.read().decode()[:400])
print("task", tid, flush=True)
while True:
    t = json.load(urllib.request.urlopen(urllib.request.Request(f"{API}/{tid}", headers=H)))
    print(t["status"], t.get("progress"), flush=True)
    if t["status"] in ("SUCCEEDED", "FAILED", "CANCELED"): break
    time.sleep(10)
if t["status"] != "SUCCEEDED": sys.exit("task " + t["status"] + ": " + json.dumps(t.get("task_error"))[:400])
for fmt, url in t["model_urls"].items():
    if fmt in ("glb", "fbx"): urllib.request.urlretrieve(url, f"{out}.{fmt}"); print("saved", f"{out}.{fmt}")
if t.get("thumbnail_url"): urllib.request.urlretrieve(t["thumbnail_url"], f"{out}_thumb.png")
print("credits", t.get("consumed_credits"))
