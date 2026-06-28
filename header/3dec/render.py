import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.spatial import ConvexHull

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "data", "3dec_toppling.json")))

dmax = max(b["disp"] for b in D["blocks"])
clim = np.percentile([b["disp"] for b in D["blocks"]], 98) or dmax

tris, vals = [], []
for b in D["blocks"]:
    # swap y/z so the physical vertical (data y, gravity) maps to mpl's up-axis
    pts = np.array(b["verts"])[:, [0, 2, 1]]
    try:
        hull = ConvexHull(pts)
    except Exception:
        continue
    for s in hull.simplices:
        tris.append(pts[s])
        vals.append(b["disp"])
vals = np.array(vals)
rgba = cm.inferno(np.clip(vals / clim, 0, 1))

BG = "#0e1116"
fig = plt.figure(figsize=(6.4, 4.2), dpi=200)
ax = fig.add_subplot(111, projection="3d")
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)

pc = Poly3DCollection(tris, facecolors=rgba, edgecolors="#0a0c10", linewidths=0.12)
ax.add_collection3d(pc)

allv = np.array([[v[0], v[2], v[1]] for b in D["blocks"] for v in b["verts"]])
ax.set_xlim(allv[:, 0].min(), allv[:, 0].max())
ax.set_ylim(allv[:, 1].min(), allv[:, 1].max())
ax.set_zlim(allv[:, 2].min(), allv[:, 2].max())
ax.set_box_aspect((np.ptp(allv[:, 0]), np.ptp(allv[:, 1]), np.ptp(allv[:, 2])))
ax.view_init(elev=12, azim=-86)
ax.axis("off")
plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
out = os.path.join(HERE, "3dec_toppling.png")
plt.savefig(out, facecolor=BG, dpi=200, bbox_inches="tight", pad_inches=0)
print("saved", out, "disp_max=%.2f clim=%.2f" % (dmax, clim))
