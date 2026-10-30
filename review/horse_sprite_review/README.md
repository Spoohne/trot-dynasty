# Trot Dynasty: horse sprite pipeline, review package

Everything here was copied as it is, except for two kinds of file:
- The per-frame PNGs and GIFs in `2_animations/` were cut from the existing sheets.
- C's 24-frame sheet was put together from frames already in the pool.

Nothing was regenerated for this package.

## Engine and renderer
- **Game:** the server is Python's built-in `http.server` (`app.py`, not included because it's 5k lines of game logic). It is not a game engine.
- **Replay:** `4_code/mockups/replay_hd2d.html` uses three.js 0.160 (WebGL).
  - Each runner is a flat card (plane) facing the camera in a 3D scene, so it reads as 2.5D.
  - Sprite textures use NearestFilter with no mipmaps, so no smoothing is applied in the browser.
  - Colors are applied per horse on a 2D canvas, which then becomes a `CanvasTexture`.
- **Tack Room preview:** a static PNG drawn by `tack_art.py` with Pillow.

## Pipeline, in order

### A. Baseline runner (shipped, no wraps)
1. SpriteCook pixel still, 242 px (`race_b_still_242.png`), enlarged 3× to 750 px.
2. SpriteCook "frame-engine" image-to-animation of that still: `fe12_raw...webp`, 12 frames at 640×640 each.
3. `fe_prep.py`:
   - Trims all frames to one shared box.
   - Shrinks back to sprite scale, nearest-neighbor.
   - Calls `fix_pace.py --bob 0 --anchor pad`, which shifts each frame so the saddle pad sits at the same spot (no body bob).
   - Result: 12 × 208×101.

### B. Leg wraps (shipped)
1. A SpriteCook edit of the still that adds white wraps. The edit redraws the whole horse.
2. SpriteCook animation runs → `fe_prep` / `fix_pace` → `assemble_wraps.py`:
   - `steady()` lays today's wheel and driver over every frame, so they don't wobble.
   - It then fits the frames to today's frame size and wheel position.
   - `defringe` cleans the outline.
3. Run 3 was picked by eye and shipped as `wraps12.png`.
4. The wrap mask is found automatically (`wraps()`): white to light-grey, unsaturated pixels below the saddle pad and off the wheel.

### C. Newest attempt (not shipped)
1. Seedance 2.5 image-to-video on fal.ai: a 720p still on a green screen, with the last frame set to match the first. The prompt asks for slow motion.
   - Output: `slow1_seedance_720p.mp4`, 97 frames. One stride runs about 36 frames.
2. `seedance.py frames`: OpenCV writes each frame out as a lossless PNG.
3. `build_pool.py seedance` → `seedance_loop.key()`:
   - Chroma key from the edge color, then morphological open/close.
   - Keeps connected blobs over 400 px.
   - Erodes the alpha by one pixel and removes green spill.
4. Crops to the union box of all frames and shrinks ½ with a BOX filter.
5. Quantizes to today's runner palette with no dither, and thresholds alpha at 140 (fully on or off).
6. `fix_pace`, the same pad pin as A.
7. Scaled (nearest) to match today's horse area, but capped so the nose never crosses the frame edge. Placed so the wheel lands on today's wheel.
8. `finish()`:
   - `steady()` lays today's wheel and driver back on.
   - For Seedance, the area behind the driver (tail and seat) is now taken from today's runner, because the video version broke up into noise. This change was made today, just before packaging.
   - Wrap mask, then `defringe`.
9. Pose choice: optical flow (DIS) on the leg region finds the exact stride. The 24 poses are spaced evenly through it and are real frames only, with nothing blended between frames (`selection.json`).
10. The Sprite Lab (`spritelab/server.py`, a local page) lets a person swap, nudge and size any pose. **Send to game** writes `wraps12.png`, the mask and `wraps12.json`.

### In the game, each runner each frame
`coat()` recolors the coat, then `dye()` recolors silks and saddle pad. For wrapped horses, `wrapTint()` then recolors only the masked pixels, keeping their shading. `grit()` follows. The result goes to `CanvasTexture`, and UV offsets pick the frame.

## Sizes

| Item | Size |
|---|---|
| Baseline original animation | 640×640 per frame (3× art) |
| Seedance video | 1280×720 |
| Exported frames (all versions) | 208×101 RGBA |
| Long sheets | Wrap into rows at 4096 px wide (a phone texture limit) |
| Display | Card is 14.5 ft long in world units, so screen size depends on the camera, roughly 150–600 px wide; scaled nearest |

## Frames and timing
- A and B have 12 frames. C has 24 frames (from a 97-frame clip).
- **There is no fixed FPS.** The frame is taken from distance travelled: one cycle per 17 ft (`STRIDE_FT`).
  - At race speed, about 48 ft/s, that's about 2.8 cycles a second: about 34 fps for 12 frames, or 67 for 24.
- Each runner has a fixed phase offset so the field doesn't move in step.
- The included GIFs play 3 cycles a second.
- Frames are selected, never interpolated. Blended and flow-warped in-betweens were tried (`seedance_phases.py`) and dropped because they ghosted.

## Transparency
- SpriteCook output comes with alpha.
- Video output is keyed, as described in C above.
- Alpha is binary everywhere: thresholded, with no partial transparency.

## Resize, palette and compression
- **Resizing:** nearest for whole-number shrinks of SpriteCook art; BOX for the video shrink, then quantized to the stock palette with no dither. No smoothing at display.
- **Files:** PNG is lossless. The source videos are H.264 MP4, which is lossy; the slow clip was rendered at a high bitrate.

## Accessories
- **Leg wraps are not a separate layer.** They are painted into a separate full set of frames (sheet B or C), with a per-pixel mask. A wrapped horse swaps to that sheet, and its mask pixels are recolored per horse.
  - The tint keeps the source's lightness and darkens edge pixels ×0.8. It's the same formula in `wrap_tint.py`, `wrapTint()` in the replay, and `tack_art.paint`.
  - Because the wraps are baked into the horse frames, they follow the legs exactly, and they are hidden wherever the art hides them: the far legs behind the near legs, or behind the wheel. There's no layer ordering to manage.
- **Wheel and driver** are shared with today's runner and laid on per frame.
- **Head mask, harness and bike colors have no replay art.** They exist only as Tack Room data and the static preview in `tack_art.py`. Saddle pad and silks are recolored by color matching in `dye()`.
- **Earlier tries, abandoned and included as code only:** an overlay layer traced by code (`trace_wraps`, `overlay_wraps`), pasting wraps from a reference (`paste_wraps`), and local GPU inpainting (`inpaint_wraps`, ComfyUI + Qwen; frames 1 to 11 only, frame 12 was never made).

## Known problems
- **Body jitter between versions.** Every SpriteCook edit redraws the whole horse, so every wrapped run is a different horse. Workaround: shared wheel and driver, the pad pin, and fitting to today's size.
- **Leg drawing errors in B.** The owner flagged 11 of 12 frames: a back leg that turns shapeless, floppy hooves, a vanishing leg, a tail break. Some were patched (`hooves.py`, tail kept); most are in the source animation itself.
- **Video edges.** Earlier Seedance clips left fringe and jagged outlines from keying and dithering. The slow clip (green screen, 720p, high bitrate) is cleaner, but frames still need review at 4×.
- **C issues:**
  - The horse comes out about 18% smaller than A, because of the nose cap.
  - Its wraps run longer, knee to fetlock.
  - The video's tail and seat area broke into noise; that area is now taken from today's runner.
- **Gear timing.** Gear shows only on the side-view card, not on the other camera angles, and the replay uses the horse's current gear, not what it wore on race night.
- **The two runners don't match.** The wrapped sheet and the plain sheet are different drawings, so a wrapped horse doesn't look exactly like the same horse without wraps.

## Reproduce

Run these from the game folder; the scripts expect that layout.

```
pip install -r 4_code/requirements.txt
python mockups/pixel/fe_prep.py fe12_raw.webp 12 fe12_cycle.png
python art/seedance.py frames art/seedance_out/slow1.mp4 art/seedance_out/slow1_frames
python art/spritelab/build_pool.py seedance art/seedance_out/slow1_frames seedance_slow1 "Seedance slow"
python art/spritelab/server.py
```

The first command rebuilds A, the third rebuilds C, and the last opens the Sprite Lab at http://127.0.0.1:8120.

- Generating a new clip with `seedance.py clip` needs a fal.ai key in `FAL_KEY` (not included).
- SpriteCook runs were made through its hosted service and can't be reproduced offline. Their raw outputs are in `1_original_source`.

## Not available
- The SpriteCook prompts and settings exist only in that service's history.
- Today's runner has no original video. Its source is the SpriteCook animation (`fe12_raw.webp`).
