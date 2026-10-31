"""Round 2 with Astra: a 13th leg frame (the real stride is 13 video frames), then head/neck/mane/tail motion from the
video on all 13, then white wraps + hood on all 13. Sequential, waiting out the API's per-minute limit."""
import os, sys, time
import cv2
from PIL import Image
sys.path.insert(0, r"C:\Users\spooh\HarnessSim\art"); import astra_api
R = r"C:\Users\spooh\HarnessSim\art\astra_run"; V = r"C:\Users\spooh\HarnessSim\art\reference\pacer_video"
N = 13


def ask(prompt, imgs, out):
    for attempt in range(6):
        if os.path.exists(out):
            return
        try:
            astra_api.ask(prompt, imgs, out, background="opaque"); print("done", os.path.basename(out), flush=True); return
        except SystemExit as e:
            print("wait", os.path.basename(out), str(e)[:60], flush=True); time.sleep(65)


def green(src, out):
    f = Image.open(src).convert("RGBA").resize((1536, 973), Image.LANCZOS)
    g = Image.new("RGBA", (1536, 1024), (0, 255, 0, 255)); g.alpha_composite(f, (0, 25)); g.convert("RGB").save(out)


# the 13th pose: video frame 16 (poses 0-11 are frames 4-15)
v = cv2.VideoCapture(V + r"\clip.mov"); v.set(cv2.CAP_PROP_POS_FRAMES, 16); ok, f = v.read()
Image.fromarray(cv2.cvtColor(f[130:440, 330:900], cv2.COLOR_BGR2RGB)).save(V + r"\poses\12.png")
os.makedirs(f"{R}\\r2_legs", exist_ok=True); os.makedirs(f"{R}\\r2_head", exist_ok=True); os.makedirs(f"{R}\\r2_gear", exist_ok=True)

# 1. legs for frame 13 (the body is identical in every frame, so any base frame is the input)
ask(open(f"{R}\\p4.txt").read(), [f"{R}\\pf\\in_11.png", f"{V}\\poses\\12.png"], f"{R}\\r2_legs\\out_12.png")

# 2. head/neck/mane/tail from the video, on every leg-corrected frame
P_HEAD = open(f"{R}\\p6.txt").read()
for i in range(N):
    src = f"{R}\\vid\\out_{i:02d}.png" if i < 12 else f"{R}\\r2_legs\\out_12.png"
    green_in = f"{R}\\r2_head\\in_{i:02d}.png"
    if not os.path.exists(green_in):
        Image.open(src).convert("RGB").save(green_in)                      # already a green-screen frame at 1536x1024
    ask(P_HEAD, [green_in, f"{V}\\poses\\{i:02d}.png"], f"{R}\\r2_head\\out_{i:02d}.png")

# 3. gear on the final frames
P_GEAR = open(f"{R}\\p5.txt").read()
for i in range(N):
    ask(P_GEAR, [f"{R}\\r2_head\\out_{i:02d}.png"], f"{R}\\r2_gear\\out_{i:02d}.png")
print("round 2 complete", flush=True)
