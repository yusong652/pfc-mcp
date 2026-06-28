"""Render all four engine panels in the locked shared style (c2_teal family).

Paper background, ink linework, low-saturation wash. PFC uses the diverging
teal<->terracotta velocity field; the other three are single-sign scalar
fields (shear-strain rate / displacement / speed) on a single-sided warm
sequential ramp, alpha ramped so the static body stays paper and the active
feature (slip surface / toppling / runout tongue) glows.
"""
import json, os, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, to_rgba
from matplotlib.collections import LineCollection, PatchCollection, PolyCollection
from matplotlib.patches import Circle

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- shared style (porcelain: light + steel <-> terracotta) ----
BG   = "#eef1f4"
INK  = "#33291f"                                       # dark warm ink on porcelain
COOL, MID, WARM = "#6f8c9c", "#cfd2cf", "#bd7d5f"     # steel-blue -> pale -> terracotta
# PFC maps this diverging over signed vy; the scalar-field panels map it
# cool->warm over magnitude (static = teal, active feature = terracotta) so
# every panel carries both poles instead of a single warm ramp.
FIELD = LinearSegmentedColormap.from_list("field", [COOL, MID, WARM])


def finish(ax):
    ax.set_aspect("equal"); ax.axis("off")


# ---------- PFC (diverging velocity + ink force chains) ----------
def render_pfc():
    D = json.load(open(f"{HERE}/pfc/data/pfc_biaxial_shear.json"))
    B = D["balls"]
    vy = np.array([b["vy"] for b in B]); lim = np.percentile(np.abs(vy), 98)
    fn = np.array([c["fn"] for c in D["contacts"]]); fnmax = D["fn_max"]
    segs = [[(c["x1"], c["y1"]), (c["x2"], c["y2"])] for c in D["contacts"]]
    fig, ax = plt.subplots(figsize=(3.2, 6.0), dpi=200); fig.patch.set_alpha(0); ax.set_facecolor("none")
    t = np.clip((vy / lim + 1) / 2, 0, 1); cols = FIELD(t); cols[:, 3] = 0.74
    ax.add_collection(PatchCollection([Circle((b["x"], b["y"]), b["r"]) for b in B],
                                      facecolor=cols, edgecolor="none", zorder=1))
    r = np.clip(fn / fnmax, 0, 1); cc = np.tile(to_rgba(INK), (len(r), 1)); cc[:, 3] = 0.05 + 0.78 * r ** 0.78
    ax.add_collection(LineCollection(segs, colors=cc, linewidths=0.14 + 2.1 * r, zorder=2))
    xs = [b["x"] for b in B]; ys = [b["y"] for b in B]; m = 0.4
    ax.set_xlim(min(xs) - m, max(xs) + m); ax.set_ylim(min(ys) - m, max(ys) + m); finish(ax)
    _save(fig, "pfc/pfc.png")


# ---------- FLAC (shear-strain-rate slip surface) ----------
def render_flac():
    D = json.load(open(f"{HERE}/flac/data/flac_slope.json"))
    gp = {g["id"]: g for g in D["gridpoints"]}
    polys, gamma = [], []
    for z in D["zones"]:
        v = [(gp[i]["x"], gp[i]["y"], gp[i]["vx"], gp[i]["vy"]) for i in z]
        cx = sum(p[0] for p in v) / 4.0; cy = sum(p[1] for p in v) / 4.0
        v.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
        polys.append([(p[0], p[1]) for p in v])
        A = dudx = dudy = dvdx = dvdy = 0.0
        for k in range(4):
            x0, y0, u0, w0 = v[k]; x1, y1, u1, w1 = v[(k + 1) % 4]
            A += 0.5 * (x0 * y1 - x1 * y0)
            um, wm = 0.5 * (u0 + u1), 0.5 * (w0 + w1)
            dudx += um * (y1 - y0); dudy -= um * (x1 - x0)
            dvdx += wm * (y1 - y0); dvdy -= wm * (x1 - x0)
        A = abs(A) or 1e-12
        dudx /= A; dudy /= A; dvdx /= A; dvdy /= A
        exy = 0.5 * (dudy + dvdx)
        gamma.append(math.sqrt(((dudx - dvdy) / 2.0) ** 2 + exy ** 2))
    gamma = np.array(gamma); clim = np.percentile(gamma, 99)
    g = np.clip(gamma / clim, 0, 1)
    rgba = FIELD(g); rgba[:, 3] = 0.40 + 0.55 * g ** 0.5   # teal body wash -> terracotta slip
    fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=200); fig.patch.set_alpha(0); ax.set_facecolor("none")
    ax.add_collection(PolyCollection(polys, facecolors=rgba, edgecolors=to_rgba(INK, 0.32), linewidths=0.22, zorder=1))
    ax.set_xlim(-0.5, 34.0); ax.set_ylim(-0.5, 20.5); finish(ax)
    _save(fig, "flac/flac.png")


# ---------- 3DEC (block toppling, displacement) ----------
def render_3dec():
    from scipy.spatial import ConvexHull
    D = json.load(open(f"{HERE}/3dec/data/3dec_toppling.json"))
    clim = np.percentile([b["disp"] for b in D["blocks"]], 98) or max(b["disp"] for b in D["blocks"])
    tris, vals = [], []
    for b in D["blocks"]:
        pts = np.array(b["verts"])[:, [0, 2, 1]]
        try:
            hull = ConvexHull(pts)
        except Exception:
            continue
        for s in hull.simplices:
            tris.append(pts[s]); vals.append(b["disp"])
    vals = np.array(vals)
    v = np.clip(vals / clim, 0, 1)
    rgba = FIELD(v); rgba[:, 3] = 0.55 + 0.4 * v        # teal standing -> terracotta toppled
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(6.4, 4.2), dpi=200); fig.patch.set_alpha(0)
    ax = fig.add_subplot(111, projection="3d"); ax.set_facecolor("none")
    pc = Poly3DCollection(tris, facecolors=rgba, edgecolors=to_rgba(INK, 0.8), linewidths=0.22)
    ax.add_collection3d(pc)
    allv = np.array([[v[0], v[2], v[1]] for b in D["blocks"] for v in b["verts"]])
    ax.set_xlim(allv[:, 0].min(), allv[:, 0].max()); ax.set_ylim(allv[:, 1].min(), allv[:, 1].max())
    ax.set_zlim(allv[:, 2].min(), allv[:, 2].max())
    ax.set_box_aspect((np.ptp(allv[:, 0]), np.ptp(allv[:, 1]), np.ptp(allv[:, 2])))
    ax.view_init(elev=12, azim=-86)
    for pane in (ax.xaxis, ax.yaxis, ax.zaxis):
        pane.set_pane_color((0, 0, 0, 0)); pane.line.set_color((0, 0, 0, 0))
    ax.grid(False); ax.axis("off")
    _save(fig, "3dec/3dec.png")


# ---------- MPoint (runout, speed) ----------
def render_mpoint():
    d = np.loadtxt(f"{HERE}/mpoint/data/mpoint_runout.txt")
    x, y, vx, vy = d[:, 0], d[:, 1], d[:, 2], d[:, 3]
    speed = np.hypot(vx, vy); clim = np.percentile(speed, 97)
    fig, ax = plt.subplots(figsize=(7.2, 2.8), dpi=200); fig.patch.set_alpha(0); ax.set_facecolor("none")
    ax.scatter(x, y, c=speed, cmap=FIELD, vmin=0, vmax=clim, s=8, edgecolors="none", alpha=0.9)  # teal source -> terracotta tongue
    ax.set_xlim(x.min() - 0.5, x.max() + 0.5); ax.set_ylim(y.min() - 0.5, y.max() + 1.0); finish(ax)
    _save(fig, "mpoint/mpoint.png")


def _save(fig, rel):
    plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
    out = os.path.join(HERE, rel)
    fig.savefig(out, transparent=True, dpi=200, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig); print("saved", out)


render_pfc(); render_flac(); render_3dec(); render_mpoint()

# ---- family contact sheet ----
imgs = [("pfc", "pfc/pfc.png"), ("flac", "flac/flac.png"),
        ("3dec", "3dec/3dec.png"), ("mpoint", "mpoint/mpoint.png")]
fig, axes = plt.subplots(2, 2, figsize=(12, 9), dpi=110); fig.patch.set_facecolor("#cfcabb")
for ax, (name, rel) in zip(axes.ravel(), imgs):
    ax.imshow(plt.imread(os.path.join(HERE, rel))); ax.set_title(name, color="#333", fontsize=11)
    ax.axis("off")
plt.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.01, wspace=0.04, hspace=0.1)
fig.savefig(os.path.join(HERE, "family_compare.png"), facecolor="#cfcabb", dpi=110)
print("saved family_compare.png")
