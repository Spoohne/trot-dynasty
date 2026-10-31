"""Ask gpt-6-astra (OpenAI Responses API, image_generation tool) for an image, with input images. Key from OPENAI_API_KEY.
    python art/astra_api.py out.png "prompt" in1.png [in2.png ...]
Logs every call's usage to art/astra_spend.json so a run can stop at its budget."""
import base64, json, os, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "astra_spend.json")
MODEL = "gpt-6-astra"


def key():
    k = os.environ.get("OPENAI_API_KEY")
    if not k and sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as h:
                k = winreg.QueryValueEx(h, "OPENAI_API_KEY")[0]
        except OSError:
            pass
    if not k:
        sys.exit("OPENAI_API_KEY isn't set")
    return k


def uri(p):
    return "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()


def ask(prompt, images, out, size="1536x1024", quality="high", background="transparent"):
    body = {"model": MODEL,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}] +
                       [{"type": "input_image", "image_url": uri(p)} for p in images]}],
            "tools": [{"type": "image_generation", "size": size, "quality": quality, "background": background}],
            "tool_choice": {"type": "image_generation"}}
    req = urllib.request.Request("https://api.openai.com/v1/responses", json.dumps(body).encode(),
                                 {"Authorization": "Bearer " + key(), "Content-Type": "application/json"})
    t = time.time()
    try:
        r = json.load(urllib.request.urlopen(req, timeout=900))
    except urllib.error.HTTPError as e:
        sys.exit(f"API error {e.code}: {e.read().decode()[:600]}")
    imgs = [o["result"] for o in r.get("output", []) if o.get("type") == "image_generation_call" and o.get("result")]
    text = " ".join(c.get("text", "") for o in r.get("output", []) if o.get("type") == "message" for c in o.get("content", []))
    log = json.load(open(LOG)) if os.path.exists(LOG) else []
    log.append({"t": int(t), "secs": round(time.time() - t), "out": out, "usage": r.get("usage"), "images": len(imgs)})
    json.dump(log, open(LOG, "w"), indent=1)
    if not imgs:
        sys.exit("no image returned: " + text[:600])
    open(out, "wb").write(base64.b64decode(imgs[0]))
    return out, text


if __name__ == "__main__":
    o, t = ask(sys.argv[2], sys.argv[3:], sys.argv[1]); print(o, "|", t[:300])
