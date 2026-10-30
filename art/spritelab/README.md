# Sprite Lab

Assemble the replay's 12-frame wrapped runner by eye, from any candidate frames.

## Start it

```
cd C:\Users\spooh\HarnessSim
python art/spritelab/server.py
```

Open http://127.0.0.1:8120 in a browser.

## Use it

1. **Frames to choose from:** pick a source tab (Seedance clips, SpriteCook runs, inpainted frames, today's runner).
2. **Fill all 12 from this source** loads that source's suggested stride, or click a pose box, then click any frame to
   put it there (the next pose is selected for you). Sources can be mixed.
3. Watch **Yours** beside **Today's runner** at race speed, at 4x and real size. Change the wrap color, slow it down,
   step pose by pose, or show today's runner faintly behind yours to line poses up.
4. Per pose: **nudge** with the arrows, **size** with the slider, **reset** or **clear**.
5. **Send to game** writes the sheet and wrap mask into `mockups/pixel/tack/` and bumps the replay's version. Every
   export is kept in `art/spritelab/exports/` and can be loaded back from **Load export**. Nothing goes live until the
   game is deployed.

## Add a new Seedance clip

```
python art/seedance.py clip art/seedance_in/wraps_still.png "<prompt>" art/seedance_out/clip2.mp4 --end same --res 480p --dur 4
python art/seedance.py frames art/seedance_out/clip2.mp4 art/seedance_out/clip2_frames
python art/spritelab/build_pool.py seedance art/seedance_out/clip2_frames seedance2 "Seedance clip 2"
```

Reload the Lab; the clip appears as a new tab.
