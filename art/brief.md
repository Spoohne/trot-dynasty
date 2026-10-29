# Horse portrait brief (SpriteCook)

Goal: one approved hero base portrait, then coat/marking/pattern variants made by editing that
same image so pose, lighting and framing never drift. Code later composites cosmetics on top.

## Hero base (first call)
generate_game_art, pixel=false, 512x512, bg_mode=transparent, variations=4, resolution=2K,
model: check list_generation_models (start with gemini-3.1-flash-image; try gpt-image-2 high for the keeper)

prompt:
  Head-and-neck portrait of a Standardbred racehorse, three-quarter view facing left, ears pricked,
  alert intelligent eye, wearing a simple black leather racing bridle. Plain light grey coat so it
  can be recoloured. Polished digital painting for a premium mobile sports-management game:
  confident painterly brushwork, crisp readable silhouette, accurate equine anatomy (jaw, cheek
  muscle, veins on the face), soft studio key light from upper left with a cool rim light.
  Centered, neck cropped cleanly at the bottom edge. No text, no frame, no background scenery.
theme: modern harness racing, night racing under lights
style:  semi-realistic painted illustration, between a racing-print painting and a premium card game

## Variants (edit_asset_id = approved hero)
- coats: bay with black points, chestnut, black, dark grey dappled, palomino, buckskin
- markings: star, strip, blaze, bald face; blue eye
- patterns: tobiano patches, appaloosa leopard spots, roan
- legendary: metallic gold coat with a subtle iridescent sheen

## Acceptance
- reads at 64px (barn row) and 240px (horse card)
- same angle, crop and light across every variant
- no text, signatures or extra horses
