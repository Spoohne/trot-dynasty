"""The independent reviewer: send Astra (OpenAI Responses API) a message and files, keep the thread, log the spend.
    python research/engine_lab/astra_review.py "message" [file ...]      continue the review thread
    python research/engine_lab/astra_review.py --new "message" [file ...] start a fresh thread
Key from OPENAI_API_KEY (environment or the Windows user registry); never printed. Each reply is saved under
reviews/ and every call's tokens go to spend.json; a call that would pass the budget is refused."""
import json, os, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SPEND, THREAD, OUT = os.path.join(HERE, "spend.json"), os.path.join(HERE, "thread.json"), os.path.join(HERE, "reviews")
MODEL = "gpt-6-astra"
BUDGET_CALLS = 25            # shortcut: a call count, not dollars (prices aren't in the response); raise only with Patrick's OK


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


def review(message, files=(), new=False):
    spend = json.load(open(SPEND)) if os.path.exists(SPEND) else []
    if len(spend) >= BUDGET_CALLS:
        sys.exit(f"review budget reached ({BUDGET_CALLS} calls): ask Patrick before spending more")
    text = message + "".join(f"\n\n===== FILE: {os.path.basename(f)} =====\n" + open(f, encoding="utf-8").read() for f in files)
    body = {"model": MODEL, "input": [{"role": "user", "content": [{"type": "input_text", "text": text}]}]}
    prev = None if new or not os.path.exists(THREAD) else json.load(open(THREAD)).get("last")
    if prev:
        body["previous_response_id"] = prev
    req = urllib.request.Request("https://api.openai.com/v1/responses", json.dumps(body).encode(),
                                 {"Authorization": "Bearer " + key(), "Content-Type": "application/json"})
    t = time.time()
    for attempt in range(4):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=900))
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(20 * (attempt + 1)); continue
            sys.exit(f"API error {e.code}: {e.read().decode()[:600]}")
    reply = "\n".join(c.get("text", "") for o in r.get("output", []) if o.get("type") == "message" for c in o.get("content", []))
    json.dump({"last": r.get("id")}, open(THREAD, "w"))
    spend.append({"t": int(t), "secs": round(time.time() - t), "usage": r.get("usage"), "chars_sent": len(text)})
    json.dump(spend, open(SPEND, "w"), indent=1)
    os.makedirs(OUT, exist_ok=True)
    n = len(spend)
    path = os.path.join(OUT, f"{n:02d}_{time.strftime('%Y%m%d_%H%M')}.md")
    open(path, "w", encoding="utf-8").write(f"# Review {n}\n\n## Sent\n\n{message}\n\nFiles: {', '.join(os.path.basename(f) for f in files) or 'none'}\n\n## Astra\n\n{reply}\n")
    return path, reply


if __name__ == "__main__":
    a = sys.argv[1:]
    new = a[:1] == ["--new"]
    if new:
        a = a[1:]
    p, rep = review(a[0], a[1:], new)
    sys.stdout.reconfigure(encoding="utf-8"); print(p); print(rep)
