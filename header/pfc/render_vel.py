import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Circle

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "data", "pfc_biaxial_shear.json")))

BG = "#0e1116"
fig, ax = plt.subplots(figsize=(3.2, 6.0), dpi=200)
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)

vy = np.array([b["vy"] for b in D["balls"]])
lim = np.percentile(np.abs(vy), 98)  # robust symmetric limit
circ = [Circle((b["x"], b["y"]), b["r"]) for b in D["balls"]]
pc = PatchCollection(circ, cmap="coolwarm", edgecolor="none", zorder=2)
pc.set_array(vy); pc.set_clim(-lim, lim)
ax.add_collection(pc)

xs = [b["x"] for b in D["balls"]]; ys = [b["y"] for b in D["balls"]]
m = 0.4
ax.set_xlim(min(xs) - m, max(xs) + m); ax.set_ylim(min(ys) - m, max(ys) + m)
ax.set_aspect("equal"); ax.axis("off")
plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
out = os.path.join(HERE, "pfc_biaxial_vel.png")
plt.savefig(out, facecolor=BG, dpi=200)
print("saved", out, "vy-lim=%.4f" % lim)
