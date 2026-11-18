import json, numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi
import cv2
out = {}
for k in ['full_cut','front','front34','sideL','back','sideR','back34','helmet']:
    im = np.array(Image.open(f'assets/{k}.png').convert('RGBA')).astype(np.float32)
    rgb, a = im[..., :3], im[..., 3] / 255
    if k != 'helmet':
        solid = ndi.binary_fill_holes(a > 0.35)
        lab, n = ndi.label(solid)
        if n > 1:  # keep biggest blob
            sizes = ndi.sum(solid, lab, range(1, n + 1)); solid = lab == (np.argmax(sizes) + 1)
        soft = cv2.GaussianBlur(solid.astype(np.float32), (0, 0), 1.2)
        a = np.where(solid, np.maximum(soft, np.clip(a * 1.6, 0, 1)), np.minimum(a, soft))
        a = np.where(ndi.binary_erosion(solid, iterations=3), 1.0, a)
    # eyes: saturated cyan
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    eye = (b > 150) & (g > 140) & (r < 170) & (b - r > 60)
    eye = ndi.binary_opening(eye, iterations=1)
    lab, n = ndi.label(eye)
    eyes = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(xs) < 40: continue
        eyes.append(dict(cx=float(xs.mean()), cy=float(ys.mean()), w=float(xs.max() - xs.min() + 1), h=float(ys.max() - ys.min() + 1), n=len(xs)))
    eyes = sorted(eyes, key=lambda e: -e['n'])[:2]
    eyes = sorted(eyes, key=lambda e: e['cx'])
    keep = {'back': [], 'back34': [], 'sideL': [1], 'sideR': [0]}
    if k in keep: eyes = [eyes[i] for i in keep[k]]
    # paint the eyes out with visor black (dilate to kill glow halo)
    m = np.zeros(eye.shape, bool)
    for e in eyes:
        yy, xx = np.ogrid[:eye.shape[0], :eye.shape[1]]
        m |= ((xx - e['cx']) / (e['w'] * 0.85)) ** 2 + ((yy - e['cy']) / (e['h'] * 0.8)) ** 2 < 1
    if m.any():
        img8 = np.clip(rgb, 0, 255).astype(np.uint8)
        fill = cv2.inpaint(img8, m.astype(np.uint8) * 255, 9, cv2.INPAINT_TELEA).astype(np.float32)
        # pull the inpainted area toward the dark visor tone
        vis = np.median(rgb[ndi.binary_dilation(m, iterations=12) & ~ndi.binary_dilation(m, iterations=6)], axis=0)
        fill[m] = fill[m] * 0.35 + vis * 0.65
        rgb = np.where(m[..., None], fill, rgb)
    res = np.dstack([rgb, a * 255]).clip(0, 255).astype(np.uint8)
    Image.fromarray(res).save(f'assets/c_{k}.png')
    out[k] = dict(size=list(res.shape[1::-1]), eyes=eyes)
    print(k, res.shape[1::-1], [(round(e['cx']), round(e['cy']), round(e['w']), round(e['h'])) for e in eyes])
json.dump(out, open('assets/astro.json', 'w'), indent=1)
