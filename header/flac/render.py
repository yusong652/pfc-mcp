import json, os, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.collections import PolyCollection

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "data", "flac_slope.json")))
gp = {g["id"]: g for g in D["gridpoints"]}

polys, gamma = [], []
for z in D["zones"]:
    v = [(gp[i]["x"], gp[i]["y"], gp[i]["vx"], gp[i]["vy"]) for i in z]
    cx = sum(p[0] for p in v) / 4.0
    cy = sum(p[1] for p in v) / 4.0
    v.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))   # CCW loop
    polys.append([(p[0], p[1]) for p in v])
    A = dudx = dudy = dvdx = dvdy = 0.0
    for k in range(4):
        x0, y0, u0, w0 = v[k]
        x1, y1, u1, w1 = v[(k + 1) % 4]
        A += 0.5 * (x0 * y1 - x1 * y0)
        um, wm = 0.5 * (u0 + u1), 0.5 * (w0 + w1)
        dudx += um * (y1 - y0); dudy -= um * (x1 - x0)
        dvdx += wm * (y1 - y0); dvdy -= wm * (x1 - x0)
    A = abs(A) or 1e-12
    dudx /= A; dudy /= A; dvdx /= A; dvdy /= A
    exy = 0.5 * (dudy + dvdx)
    gamma.append(math.sqrt(((dudx - dvdy) / 2.0) ** 2 + exy ** 2))

gamma = np.array(gamma)
clim = np.percentile(gamma, 99)

# bright slip band over a faint slope body (alpha ramped by shear strain rate)
rgba = cm.inferno(np.clip(gamma / clim, 0, 1))
rgba[:, 3] = np.clip(gamma / clim, 0, 1) ** 0.6

BG = "#0e1116"
fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=200)
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
ax.add_collection(PolyCollection(polys, facecolors="#272c37", edgecolors="none", zorder=1))
ax.add_collection(PolyCollection(polys, facecolors=rgba, edgecolors="none", zorder=2))

ax.set_xlim(-0.5, 34.0); ax.set_ylim(-0.5, 20.5)
ax.set_aspect("equal"); ax.axis("off")
plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
out = os.path.join(HERE, "flac_slope.png")
plt.savefig(out, facecolor=BG, dpi=200, bbox_inches="tight", pad_inches=0)
print("saved", out, "gamma_clim=%.3e FoS~%.2f" % (clim, D["fos_estimate"]))
