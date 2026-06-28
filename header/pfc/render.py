import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import Circle

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "data", "pfc_biaxial_relaxed.json")))

BG = "#0e1116"
fig, ax = plt.subplots(figsize=(3.2, 6.0), dpi=200)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

# balls: faint backdrop
circ = [Circle((b["x"], b["y"]), b["r"]) for b in D["balls"]]
pc = PatchCollection(circ, facecolor="#2a2f3a", edgecolor="none", alpha=0.55, zorder=1)
ax.add_collection(pc)

# force chains: segment between ball centroids, width & color by normal force
fn_max = D["fn_max"]
segs, lws, vals = [], [], []
for c in D["contacts"]:
    segs.append([(c["x1"], c["y1"]), (c["x2"], c["y2"])])
    r = c["fn"] / fn_max
    lws.append(0.15 + 3.6 * r)
    vals.append(c["fn"])
lc = LineCollection(segs, linewidths=lws, cmap="inferno", zorder=3)
lc.set_array(__import__("numpy").array(vals))
lc.set_clim(0, fn_max)
ax.add_collection(lc)

xs = [b["x"] for b in D["balls"]]; ys = [b["y"] for b in D["balls"]]
m = 0.4
ax.set_xlim(min(xs) - m, max(xs) + m)
ax.set_ylim(min(ys) - m, max(ys) + m)
ax.set_aspect("equal")
ax.axis("off")
plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
out = os.path.join(HERE, "pfc_biaxial.png")
plt.savefig(out, facecolor=BG, dpi=200)
print("saved", out)
