"""2x2 four-engine montage — square sibling of the 1x4 banner.

Same visual language as montage.py + add_title.py: light-blue diagonal wash,
soft slate seams, each transparent panel auto-trimmed and *contained* (no crop)
inside its cell, monospace wordmark centred over the seam crossing.

Grid (matches the 1x4 reading order):
    pfc  | flac
    3dec | mpoint
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle
from matplotlib.colors import to_rgb

HERE = os.path.dirname(os.path.abspath(__file__))
SEAM = "#8a98a6"
GRAD_LIGHT = "#f6fafd"          # bottom-left
GRAD_DEEP = "#d8e6f1"           # top-right

W, H = 12.0, 9.0                # 4:3 canvas
# (engine, in-cell scale, dx, dy) — col,row placement is by index below
CELLS = [("pfc", 0.82, 0.0, 0.0), ("flac", 0.92, 0.0, 0.0),
         ("3dec", 0.96, 0.0, -0.1), ("mpoint", 0.96, 0.0, 0.2)]
IMG = {"pfc": "pfc/pfc.png", "flac": "flac/flac.png",
       "3dec": "3dec/3dec.png", "mpoint": "mpoint/mpoint.png"}
# cell boxes (xmin, ymin, xmax, ymax) in data coords; row 0 is TOP
HALF_W, HALF_H = W / 2, H / 2
BOXES = {
    0: (0, HALF_H, HALF_W, H),       # top-left
    1: (HALF_W, HALF_H, W, H),       # top-right
    2: (0, 0, HALF_W, HALF_H),       # bottom-left
    3: (HALF_W, 0, W, HALF_H),       # bottom-right
}


def trim(img, pad=2):
    mask = img[:, :, 3] > 0.04
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return img
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, img.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, img.shape[1])
    return img[y0:y1, x0:x1]


fig, ax = plt.subplots(figsize=(10, 10 * H / W), dpi=200)
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("auto"); ax.axis("off")

# diagonal wash (same recipe as montage.py)
ny, nx = 400, 1200
yy, xx = np.mgrid[0:ny, 0:nx]
t = ((xx / (nx - 1)) + (yy / (ny - 1))) / 2
lo = np.array(to_rgb(GRAD_LIGHT)); hi = np.array(to_rgb(GRAD_DEEP))
grad = lo[None, None, :] * (1 - t[..., None]) + hi[None, None, :] * t[..., None]
ax.imshow(grad, extent=[0, W, 0, H], origin="lower", aspect="auto", zorder=0,
          interpolation="bilinear")

for i, (name, scale, dx, dy) in enumerate(CELLS):
    xmin, ymin, xmax, ymax = BOXES[i]
    img = trim(plt.imread(os.path.join(HERE, IMG[name])))
    img_ar = img.shape[1] / img.shape[0]
    box_w, box_h = (xmax - xmin) * scale, (ymax - ymin) * scale
    if img_ar > box_w / box_h:                 # contain inside the cell, no crop
        draw_w, draw_h = box_w, box_w / img_ar
    else:
        draw_w, draw_h = box_h * img_ar, box_h
    cx = (xmin + xmax) / 2 + dx
    cy = (ymin + ymax) / 2 + dy
    ax.imshow(img, extent=[cx - draw_w / 2, cx + draw_w / 2,
                           cy - draw_h / 2, cy + draw_h / 2],
              aspect="auto", zorder=2, interpolation="lanczos")

# cross seams (vertical + horizontal), soft slate
ax.plot([HALF_W, HALF_W], [0, H], color=SEAM, lw=2.0, alpha=0.9, zorder=5, solid_capstyle="butt")
ax.plot([0, W], [HALF_H, HALF_H], color=SEAM, lw=2.0, alpha=0.9, zorder=5, solid_capstyle="butt")

# ---- wordmark plaque over the seam crossing (white text, dark outline) ----
WFILL = "white"; DARK = "#11161d"; GREY = "#5f6b76"
WSTROKE = [pe.withStroke(linewidth=3.6, foreground=DARK)]
WSTROKE_S = [pe.withStroke(linewidth=2.4, foreground=DARK)]
GSTROKE = [pe.withStroke(linewidth=1.8, foreground="white")]

# soft scrim behind the wordmark so it lifts off the four corners
ax.add_patch(Rectangle((W * 0.5 - 5.2, H * 0.5 - 1.7), 10.4, 3.4,
                       facecolor="white", alpha=0.18, edgecolor="none", zorder=18))

ax.text(0.5, 0.59, "itasca-mcp", transform=ax.transAxes, ha="center", va="center",
        fontsize=82, family="monospace", weight="bold", color=WFILL,
        path_effects=WSTROKE, zorder=20)
ax.text(0.5, 0.465, "MCP for ITASCA software", transform=ax.transAxes,
        ha="center", va="center", fontsize=23, family="monospace", weight="bold",
        color=WFILL, path_effects=WSTROKE_S, zorder=20)
ax.text(0.5, 0.378, "itasca>model new ;now, with LLM.", transform=ax.transAxes,
        ha="center", va="center", fontsize=17, family="monospace",
        color=GREY, path_effects=GSTROKE, zorder=20)

plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
out = os.path.join(HERE, "banner_2x2.png")
fig.savefig(out, dpi=200); plt.close(fig)
print("saved", out)
