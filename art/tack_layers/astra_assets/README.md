# Pacer game assets — aligned base and tintable gear

Integration export of the approved retake artwork. No game code is included or modified.

## Files

- `base/00.png` through `base/11.png`: horse, sulky, rotating-wheel artwork and driver, without gear.
- `wraps/00.png` through `wraps/11.png`: white/gray wrap pixels only, transparent elsewhere.
- `hood/00.png` through `hood/11.png`: light-gray hood pixels only, transparent elsewhere. Eye, ears and muzzle remain uncovered.
- `wraps-mask/` and `hood-mask/`: matching 8-bit grayscale coverage masks.
- `base-sheet.png`, `wraps-sheet.png`, `hood-sheet.png`, `wraps-mask-sheet.png`, `hood-mask-sheet.png`: single-row 12-frame sheets.
- `animation.json`: dimensions, frame order, registration, visible attachment coordinates and compositing conventions.
- `validation.json`: export-time test results.
- `validate.py`: independent asset validation; requires Python, Pillow and NumPy.
- `preview.gif`: three variants side by side, approximately 35 frames/sec. GIF timing is quantized; this is not a playback specification.
- `preview-slow.gif`: the same comparison at 10 frames/sec.
- `equipped-preview.gif`: blue-hood example built from the delivered layers.

## Dimensions and coordinates

All frames: **480 × 304 px**. All sheets: **5760 × 304 px**, one row of 12 frames with no gutters. Frames run 00–11.

The canvas adds room for alignment without cropping the horse. Artwork is translated by whole pixels only; no scaling, blur, morphing or interpolation is used in the exported PNGs.

Coordinates use the top-left origin, x right, y down, in source pixels.

Wheel axle: **(84, 220)** in every frame. Registration uses the visible silver hub rather than the changing wheel-spoke pattern. Visible near-side hitch centers are measured per frame in `animation.json`. Far-side hitch coordinates are null because that attachment is occluded. Hitch coordinates describe the baked art; they are not a solved rigid-body rig.

At 208 px wide, preserve the aspect ratio: height is 131.733 px (132 px if rounding). Do not force the old 208 × 101 aspect ratio.

## Distance-driven playback

Keep the existing one-stride-per-17-feet system:

`frame = floor(((distanceFeet % 17) + 17) % 17 / 17 * 12)`

Use one frame index for base, wraps and hood. There is no required playback fps.

## Compositing and tinting

Layer order: base, wraps if enabled, hood if enabled.

PNG RGB is straight/unpremultiplied. Gear RGB channels are equal (grayscale shading). To tint, multiply those channels by the desired color channels divided by 255; preserve the overlay alpha. Then source-over composite onto the base. Every appearance is assembled from the exact same base.

Masks encode coverage: 0 means absent, 255 opaque, intermediate values are edge coverage. Each mask is byte-identical to its overlay's alpha. If you use the overlay alpha directly, **do not multiply it by the mask again**, which would thin the edges. If your recolor pipeline needs the mask, use it as the coverage once.

Freeze the base before equipment compositing. Any existing coat/silks/pad color matching should run on the base before adding gear, so it cannot accidentally recolor the white gear.

## Validation

All individual frames match their sheet cells exactly. All gear is grayscale. Masks equal alpha exactly. Four tint choices across all 12 frames (48 composites) leave every RGBA pixel outside gear support unchanged. Overlay coverage is confined to the base silhouette. Run `python validate.py` to repeat these checks.

## Scope and remaining visual work

This is an integration prototype of the approved artwork, not a newly corrected anatomical pacing cycle. It stabilizes the wheel axle and separates gear; it preserves the generated leg sequence, driver motion, baked shafts and baked wheel appearance. Residual gait, body or wheel-shape fluctuations can still be visible at race speed. A passing pixel test is not proof of convincing movement.

The optional separate rotating wheel and still sulky/driver layer are not included. The source art is flattened, and a clean separation would require drawing hidden tail, rig and wheel areas. No patched or blurred substitute is supplied.

Gear was isolated from the approved generated cosmetic variants, aligned to the base, converted to grayscale and clipped to its silhouette. It is supplied as independent overlays, not as alternate regenerated full horses.
