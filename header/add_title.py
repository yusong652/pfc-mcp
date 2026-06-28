"""Overlay the wordmark on the finished banner — two placements to compare.

Monospace (brand/terminal voice), dark slate fill + thin white stroke so it
lifts off the panels where it overlaps and stays clean over the wash.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

HERE = os.path.dirname(os.path.abspath(__file__))
img = plt.imread(os.path.join(HERE, "banner.png"))
h, w = img.shape[:2]
INK = "#27313a"
STROKE = [pe.withStroke(linewidth=4.5, foreground="white")]
STROKE_S = [pe.withStroke(linewidth=3, foreground="white")]

# white text, near-black outline (thinner)
WFILL = "white"
DARK = "#11161d"
WSTROKE = [pe.withStroke(linewidth=3.3, foreground=DARK)]
WSTROKE_S = [pe.withStroke(linewidth=2.2, foreground=DARK)]
GREY = "#5f6b76"
GSTROKE = [pe.withStroke(linewidth=1.8, foreground="white")]


def base_ax():
    fig, ax = plt.subplots(figsize=(w / 200, h / 200), dpi=200)
    ax.imshow(img); ax.set_xlim(0, w); ax.set_ylim(h, 0); ax.axis("off")
    plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
    return fig, ax


# ---- variant A: centred wordmark over the panels (white text, dark outline) ----
fig, ax = base_ax()
ax.text(0.5, 0.60, "itasca-mcp", transform=ax.transAxes, ha="center", va="center",
        fontsize=48, family="monospace", weight="bold", color=WFILL, path_effects=WSTROKE, zorder=20)
ax.text(0.5, 0.43, "MCP for ITASCA software", transform=ax.transAxes,
        ha="center", va="center", fontsize=15, family="monospace", weight="bold", color=WFILL,
        path_effects=WSTROKE_S, zorder=20)
ax.text(0.5, 0.12, "itasca> model new ;now, with LLM.", transform=ax.transAxes,
        ha="center", va="center", fontsize=12.5, family="monospace", color=GREY,
        path_effects=GSTROKE, zorder=20)
fig.savefig(os.path.join(HERE, "banner_title_center.png"), dpi=200); plt.close(fig)
print("saved banner_title_center.png")

# ---- variant B: wordmark upper-left, out of the panels' way ----
fig, ax = base_ax()
ax.text(0.035, 0.86, "itasca-mcp", transform=ax.transAxes, ha="left", va="center",
        fontsize=40, family="monospace", weight="bold", color=INK, path_effects=STROKE, zorder=20)
ax.text(0.04, 0.72, "MCP for PFC · FLAC · 3DEC · MPoint · MassFlow", transform=ax.transAxes,
        ha="left", va="center", fontsize=13.5, family="monospace", color="#3a4650",
        path_effects=STROKE_S, zorder=20)
fig.savefig(os.path.join(HERE, "banner_title_corner.png"), dpi=200); plt.close(fig)
print("saved banner_title_corner.png")
