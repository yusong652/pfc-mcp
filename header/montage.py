"""Diagonal-seam banner montage (v2).

Anti-symmetric seams: the middle seam is vertical (symmetry axis), the left
seam leans "/", the right seam mirrors it "\". Each source panel is auto-
trimmed of its paper margin (kills internal whitespace), cover-cropped to its
strip aspect, and optionally inset (scale<1) to sit smaller within its slot.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.colors import to_rgb

HERE = os.path.dirname(os.path.abspath(__file__))
SEAM = "#8a98a6"                         # soft slate seams on the light-blue wash
GRAD_LIGHT = "#f6fafd"                    # bottom-left: near-white blue
GRAD_DEEP  = "#d8e6f1"                    # top-right: slightly deeper blue

W, H = 15.0, 4.5
S = 1.8                                  # seam slant magnitude

# (engine, width fraction, in-slot scale, x-offset) — EQUAL widths, parallel seams
STRIPS = [("pfc", 0.25, 0.9, 0.0), ("flac", 0.25, 0.78, 0.0),
          ("3dec", 0.25, 0.9, +0.8), ("mpoint", 0.25, 0.9, 0.0)]
SLANTS = {1: +S, 2: +S, 3: +S}           # same-direction parallel: / / /
IMG = {"pfc": "pfc/pfc.png", "flac": "flac/flac.png",
       "3dec": "3dec/3dec.png", "mpoint": "mpoint/mpoint.png"}

fr = np.cumsum([0] + [w for _, w, *_ in STRIPS]) / sum(w for _, w, *_ in STRIPS)
P = fr * W

def seam_x(j):
    if j == 0:            return 0.0, 0.0
    if j == len(STRIPS):  return W, W
    s = SLANTS[j]
    return P[j] + s / 2, P[j] - s / 2     # (top, bottom)

def trim(img, pad=2):
    # transparent panels: trim by the alpha channel
    mask = img[:, :, 3] > 0.04
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return img
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, img.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, img.shape[1])
    return img[y0:y1, x0:x1]

fig, ax = plt.subplots(figsize=(10, 10 * H / W), dpi=200)
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("auto"); ax.axis("off")

# diagonal wash: very-light blue at bottom-left -> slightly deeper at top-right
ny, nx = 400, 1200
yy, xx = np.mgrid[0:ny, 0:nx]
t = ((xx / (nx - 1)) + (yy / (ny - 1))) / 2
lo = np.array(to_rgb(GRAD_LIGHT)); hi = np.array(to_rgb(GRAD_DEEP))
grad = lo[None, None, :] * (1 - t[..., None]) + hi[None, None, :] * t[..., None]
ax.imshow(grad, extent=[0, W, 0, H], origin="lower", aspect="auto", zorder=0,
          interpolation="bilinear")

for i, (name, _, scale, dx) in enumerate(STRIPS):
    lt, lb = seam_x(i); rt, rb = seam_x(i + 1)
    xmin, xmax = min(lt, lb), max(rt, rb)
    poly = [(lb, 0), (rb, 0), (rt, H), (lt, H)]
    img = trim(plt.imread(os.path.join(HERE, IMG[name])))
    img_ar = img.shape[1] / img.shape[0]
    # contain: fit the whole panel inside the (scaled) slot box, no cropping
    box_w, box_h = (xmax - xmin) * scale, H * scale
    if img_ar > box_w / box_h:
        draw_w, draw_h = box_w, box_w / img_ar
    else:
        draw_w, draw_h = box_h * img_ar, box_h
    cx, cy = (xmin + xmax) / 2 + dx, H / 2
    im = ax.imshow(img, extent=[cx - draw_w / 2, cx + draw_w / 2, cy - draw_h / 2, cy + draw_h / 2],
                   aspect="auto", zorder=2, interpolation="lanczos")
    im.set_clip_path(Polygon(poly, closed=True, transform=ax.transData))

for j in range(1, len(STRIPS)):
    t, b = seam_x(j)
    ax.plot([b, t], [0, H], color=SEAM, lw=2.0, alpha=0.9, zorder=5, solid_capstyle="butt")

plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
out = os.path.join(HERE, "banner.png")
fig.savefig(out, dpi=200); plt.close(fig)
print("saved", out)
