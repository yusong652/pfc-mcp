import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
d = np.loadtxt(os.path.join(HERE, "data", "mpoint_runout.txt"))
x, y, vx, vy = d[:, 0], d[:, 1], d[:, 2], d[:, 3]
speed = np.hypot(vx, vy)
print("n=%d  x[%.1f,%.1f] y[%.1f,%.1f]  vmax=%.4f vmean=%.4f"
      % (len(x), x.min(), x.max(), y.min(), y.max(), speed.max(), speed.mean()))

BG = "#0e1116"
fig, ax = plt.subplots(figsize=(7.2, 2.8), dpi=200)
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)

# mid-flow: colour by speed -> the runout tongue glows, the static source stays dark
clim = np.percentile(speed, 97)
ax.scatter(x, y, c=speed, cmap="inferno", vmin=0, vmax=clim, s=7, edgecolors="none")

ax.set_xlim(x.min() - 0.5, x.max() + 0.5)
ax.set_ylim(y.min() - 0.5, y.max() + 1.0)
ax.set_aspect("equal"); ax.axis("off")
plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
out = os.path.join(HERE, "mpoint_runout.png")
plt.savefig(out, facecolor=BG, dpi=200, bbox_inches="tight", pad_inches=0)
print("saved", out, "clim=%.4f" % clim)
