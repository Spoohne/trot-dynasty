"""One request per frame: Astra's frame i with its legs redrawn to copy our original runner's frame i leg pose."""
import sys, concurrent.futures as cf
import numpy as np
from PIL import Image
sys.path.insert(0, r"C:\Users\spooh\HarnessSim\art")
import astra_api
R = r"C:\Users\spooh\HarnessSim\art\astra_run\pf"
ORIG = Image.open(r"C:\Users\spooh\HarnessSim\mockups\pixel\fe12_cycle.png").convert("RGBA")
PROMPT = open(r"C:\Users\spooh\HarnessSim\art\astra_run\p3.txt").read()
K = 3.2

def prep(i):
    f = Image.open(rf"C:\Users\spooh\HarnessSim\art\tack_layers\astra_assets\base\{i:02d}.png").convert("RGBA").resize((1536, 973), Image.LANCZOS)
    g = Image.new("RGBA", (1536, 1024), (0, 255, 0, 255)); g.alpha_composite(f, (0, 25)); g.convert("RGB").save(rf"{R}\in_{i:02d}.png")
    o = ORIG.crop((i * 208, 0, (i + 1) * 208, 101)).resize((208 * 7, 101 * 7), Image.NEAREST)
    r = Image.new("RGBA", o.size, (255, 255, 255, 255)); r.alpha_composite(o); r.convert("RGB").save(rf"{R}\ref_{i:02d}.png")

def run(i):
    astra_api.ask(PROMPT, [rf"{R}\in_{i:02d}.png", rf"{R}\ref_{i:02d}.png"], rf"{R}\out_{i:02d}.png", background="opaque")
    return i

if __name__ == "__main__":
    for i in range(12): prep(i)
    with cf.ThreadPoolExecutor(4) as ex:
        for i in ex.map(run, range(12)): print("done", i + 1, flush=True)
