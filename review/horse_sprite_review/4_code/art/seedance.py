"""Seedance 2.5 image-to-video through fal.ai, for sprite motion: send a still (and optionally an end frame, the same
still for a loop), get the MP4, and pull its frames. Needs the FAL_KEY environment variable (your fal.ai API key).
Stdlib + OpenCV only.

    python art/seedance.py clip  <still.png> "<motion prompt>" <out.mp4> [--end same|<end.png>] [--res 480p] [--dur 4]
    python art/seedance.py frames <clip.mp4> <out_dir>          every frame of the clip as PNGs
"""
import base64, json, os, sys, time, urllib.error, urllib.request

MODEL = "bytedance/seedance-2.5/image-to-video"
QUEUE = "https://queue.fal.run/"


def _key():
    k = os.environ.get("FAL_KEY")
    if not k:
        sys.exit("FAL_KEY isn't set: create a key at fal.ai and save it as the FAL_KEY environment variable.")
    return k


def _req(url, data=None, method=None):
    h = {"Authorization": "Key " + _key()}
    if data is not None:
        h["Content-Type"] = "application/json"; data = json.dumps(data).encode()
    r = urllib.request.Request(url, data=data, headers=h, method=method or ("POST" if data is not None else "GET"))
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:                            # fal says what it rejected
        raise RuntimeError(f"{e.code}: {e.read().decode()[:1500]}") from None


def data_uri(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def clip(still, prompt, out, end=None, res="480p", dur="4", timeout=900, bitrate="standard"):
    body = {"prompt": prompt, "image_url": data_uri(still), "resolution": res, "duration": str(dur), "generate_audio": False, "bitrate_mode": bitrate}
    if end:
        body["end_image_url"] = data_uri(still if end == "same" else end)
    job = _req(QUEUE + MODEL, body)
    status, result = job["status_url"], job["response_url"]
    print("request", job.get("request_id"), flush=True)                  # kept, so a finished clip can always be fetched again
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = _req(status)
        if s.get("status") == "COMPLETED":
            break
        if s.get("status") not in ("IN_QUEUE", "IN_PROGRESS"):
            raise RuntimeError(json.dumps(s)[:1500])
        time.sleep(5)
    else:
        raise TimeoutError(f"Seedance took over {timeout}s; request {job.get('request_id')}")
    r = _req(result)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    import subprocess                                                  # curl: Windows' own certificate store (Python's fails on fal's CDN)
    subprocess.run(["curl", "-s", "-f", "-o", out, r["video"]["url"]], check=True)
    return out, r.get("seed"), round(time.time() - t0)


def frames(mp4, out_dir):
    import cv2
    os.makedirs(out_dir, exist_ok=True)
    cap = cv2.VideoCapture(mp4); n = 0
    fps = cap.get(cv2.CAP_PROP_FPS)
    while True:
        ok, im = cap.read()
        if not ok:
            break
        cv2.imwrite(os.path.join(out_dir, f"{n:04d}.png"), im); n += 1
    return n, fps


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if a and a[0] == "clip":
        print(clip(a[1], a[2], a[3], end=opt("--end"), res=opt("--res", "480p"), dur=opt("--dur", "4"), bitrate=opt("--bitrate", "standard")))
    elif a and a[0] == "frames":
        print(frames(a[1], a[2]))
    else:
        print(__doc__)
