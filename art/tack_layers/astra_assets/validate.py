from pathlib import Path
from PIL import Image
import numpy as np
import json
root=Path(__file__).resolve().parent
meta=json.loads((root/'animation.json').read_text())
w,h=meta['frameSize']['width'],meta['frameSize']['height']
count=meta['frameCount'];tested=0
for layer in ['base','wraps','hood','wraps-mask','hood-mask']:
 sheet=Image.open(root/f'{layer}-sheet.png')
 assert sheet.size==(w*count,h)
 for i in range(count):
  frame=Image.open(root/layer/f'{i:02d}.png')
  assert frame.size==(w,h)
  assert np.array_equal(np.asarray(frame),np.asarray(sheet.crop((i*w,0,(i+1)*w,h))))
for i in range(count):
 base=Image.open(root/'base'/f'{i:02d}.png').convert('RGBA');original=np.asarray(base).copy()
 layers=[];support=np.zeros((h,w),bool)
 for gear in ['wraps','hood']:
  overlay=Image.open(root/gear/f'{i:02d}.png').convert('RGBA');a=np.asarray(overlay)
  mask=np.asarray(Image.open(root/(gear+'-mask')/f'{i:02d}.png'))
  assert np.array_equal(a[:,:,3],mask)
  assert np.array_equal(a[:,:,0],a[:,:,1]) and np.array_equal(a[:,:,1],a[:,:,2])
  assert not np.any((a[:,:,3]>0)&(original[:,:,3]==0))
  support|=mask>0;layers.append(overlay)
 for color in [(255,255,255),(30,90,240),(235,40,55),(25,210,110)]:
  comp=base.copy()
  for overlay in layers:
   a=np.array(overlay);a[:,:,:3]=(a[:,:,:3].astype(np.uint16)*np.array(color,dtype=np.uint16)//255).astype(np.uint8)
   comp=Image.alpha_composite(comp,Image.fromarray(a))
  changed=np.any(np.asarray(comp)!=original,axis=2)
  assert not np.any(changed&~support)
  tested+=1
 assert meta['frames'][i]['wheelAxle']==meta['rig']['wheelAxle']
print(f'PASS: {count} frames, all five sheets equal their PNG frames, grayscale gear, alpha masks, {tested} tinted composites unchanged outside gear.')
print('This validates asset/compositing integrity, not anatomical gait or rigid-body motion.')
