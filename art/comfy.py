"""Drive the local ComfyUI server (127.0.0.1:8188) from scripts: text-to-image with Qwen-Image,
and image edits with Qwen-Image-Edit, saving PNGs into the project. Stdlib only.

    python art/comfy.py gen  "prompt" out.png [--w 1024 --h 1024 --seed 7]
    python art/comfy.py edit "what to change" in.png out.png [--seed 7]
    python art/comfy.py cut  in.png out.png          transparent background (BiRefNet, built into ComfyUI)
Add --cut 1 to gen or edit to cut the result out as well.
"""
import json, os, sys, time, uuid, urllib.error, urllib.request, urllib.parse

HOST = "http://127.0.0.1:8188"
UNET = "qwen_image_2512_fp8_e4m3fn.safetensors"
EDIT = "qwen_image_edit_2511_fp8mixed.safetensors"
CLIP = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
VAE = "qwen_image_vae.safetensors"
NEG = "blurry, low quality, watermark, text, signature, extra limbs, deformed"


def _post(path, data, ctype="application/json"):
    req = urllib.request.Request(HOST + path, data=data, headers={"Content-Type": ctype})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:                     # ComfyUI says which node and input it rejected
        raise RuntimeError(e.read().decode()[:2000]) from None


def _get(path):
    with urllib.request.urlopen(HOST + path) as r:
        return r.read()


def upload(path):
    """Put a local image into ComfyUI's input folder; returns the name LoadImage wants."""
    b = uuid.uuid4().hex
    with open(path, "rb") as f:
        body = (f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{os.path.basename(path)}\"\r\n"
                f"Content-Type: image/png\r\n\r\n").encode() + f.read() + f"\r\n--{b}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{b}--\r\n".encode()
    return _post("/upload/image", body, f"multipart/form-data; boundary={b}")["name"]


def run(graph, out, timeout=900):
    """Queue a workflow, wait for it, save its first output image to `out`."""
    pid = _post("/prompt", json.dumps({"prompt": graph, "client_id": "harnesssim"}).encode())["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = json.loads(_get(f"/history/{pid}"))
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                raise RuntimeError(json.dumps(st.get("messages", [])[-1:], indent=1))
            for node in h[pid]["outputs"].values():
                for im in node.get("images", []):
                    q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im["subfolder"], "type": im["type"]})
                    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
                    with open(out, "wb") as f:
                        f.write(_get("/view?" + q))
                    return out, round(time.time() - t0, 1)
        time.sleep(1)
    raise TimeoutError(f"ComfyUI took over {timeout}s")


def _base(unet):
    return {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": unet, "weight_dtype": "default"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "qwen_image", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "shift": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["unet", 0], "shift": 3.1}},
        "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae", 0]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["decode", 0], "filename_prefix": "harnesssim"}},
    }


def gen(prompt, out, w=1024, h=1024, seed=7, steps=24, cfg=2.5):
    g = _base(UNET)
    g.update({
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["clip", 0]}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["clip", 0]}},
        "latent": {"class_type": "EmptySD3LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "sample": {"class_type": "KSampler", "inputs": {"model": ["shift", 0], "seed": seed, "steps": steps, "cfg": cfg,
                   "sampler_name": "euler", "scheduler": "simple", "positive": ["pos", 0], "negative": ["neg", 0],
                   "latent_image": ["latent", 0], "denoise": 1.0}},
    })
    return run(g, out)


def edit(prompt, src, out, seed=7, steps=24, cfg=2.5):
    """Change what the prompt says and keep the rest: same pose, framing and light."""
    g = _base(EDIT)
    g.update({
        "load": {"class_type": "LoadImage", "inputs": {"image": upload(src)}},
        "scale": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["load", 0], "upscale_method": "lanczos", "megapixels": 1.0, "resolution_steps": 8}},
        "pos": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["clip", 0], "prompt": prompt, "vae": ["vae", 0], "image1": ["scale", 0]}},
        "neg": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["clip", 0], "prompt": "", "vae": ["vae", 0], "image1": ["scale", 0]}},
        "latent": {"class_type": "VAEEncode", "inputs": {"pixels": ["scale", 0], "vae": ["vae", 0]}},
        "norm": {"class_type": "CFGNorm", "inputs": {"model": ["shift", 0], "strength": 1.0}},
        "sample": {"class_type": "KSampler", "inputs": {"model": ["norm", 0], "seed": seed, "steps": steps, "cfg": cfg,
                   "sampler_name": "euler", "scheduler": "simple", "positive": ["pos", 0], "negative": ["neg", 0],
                   "latent_image": ["latent", 0], "denoise": 1.0}},
    })
    return run(g, out)


def inpaint(prompt, src, mask, out, seed=7, steps=24, cfg=2.5, denoise=.8):
    """Edit only where `mask` (same size as src, white = repaint) is white; the latent outside it is kept as is."""
    g = _base(EDIT)
    g.update({
        "load": {"class_type": "LoadImage", "inputs": {"image": upload(src)}},
        "scale": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["load", 0], "upscale_method": "lanczos", "megapixels": 1.0, "resolution_steps": 8}},
        "mload": {"class_type": "LoadImage", "inputs": {"image": upload(mask)}},
        "mscale": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["mload", 0], "upscale_method": "nearest-exact", "megapixels": 1.0, "resolution_steps": 8}},
        "m": {"class_type": "ImageToMask", "inputs": {"image": ["mscale", 0], "channel": "red"}},
        "pos": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["clip", 0], "prompt": prompt, "vae": ["vae", 0], "image1": ["scale", 0]}},
        "neg": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["clip", 0], "prompt": "", "vae": ["vae", 0], "image1": ["scale", 0]}},
        "enc": {"class_type": "VAEEncode", "inputs": {"pixels": ["scale", 0], "vae": ["vae", 0]}},
        "latent": {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["enc", 0], "mask": ["m", 0]}},
        "norm": {"class_type": "CFGNorm", "inputs": {"model": ["shift", 0], "strength": 1.0}},
        "sample": {"class_type": "KSampler", "inputs": {"model": ["norm", 0], "seed": seed, "steps": steps, "cfg": cfg,
                   "sampler_name": "euler", "scheduler": "simple", "positive": ["pos", 0], "negative": ["neg", 0],
                   "latent_image": ["latent", 0], "denoise": denoise}},
    })
    return run(g, out)


def cutout(src, out):
    """BiRefNet's foreground mask from ComfyUI, applied here as the PNG's alpha."""
    from PIL import Image
    g = {
        "load": {"class_type": "LoadImage", "inputs": {"image": upload(src)}},
        "bgm": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": "birefnet.safetensors"}},
        "mask": {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["bgm", 0], "image": ["load", 0]}},
        "asimg": {"class_type": "MaskToImage", "inputs": {"mask": ["mask", 0]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["asimg", 0], "filename_prefix": "harnesssim_mask"}},
    }
    tmp = out + ".mask.png"
    _, secs = run(g, tmp)
    im = Image.open(src).convert("RGBA")
    a = Image.open(tmp).convert("L").resize(im.size, Image.LANCZOS)
    im.putalpha(a)
    bb = a.point(lambda v: 255 if v > 8 else 0).getbbox()        # trim to the subject
    (im.crop(bb) if bb else im).save(out)
    os.remove(tmp)
    return out, secs


if __name__ == "__main__":
    a, kw = sys.argv[1:], {}
    while "--" in " ".join(a):
        i = next(i for i, v in enumerate(a) if v.startswith("--"))
        kw[a[i][2:]] = int(a[i + 1]); del a[i:i + 2]
    cut = kw.pop("cut", 0)
    if a[0] == "gen":
        print(gen(a[1], a[2], **kw)); cut and print(cutout(a[2], a[2]))
    elif a[0] == "edit":
        print(edit(a[1], a[2], a[3], **kw)); cut and print(cutout(a[3], a[3]))
    elif a[0] == "cut":
        print(cutout(a[1], a[2]))
