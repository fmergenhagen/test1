"""Map of settlements whose least-cost technology flips between the low and high demand runs.
usage: python plot_switch_map.py <low_result.csv> <high_result.csv> <out.png>"""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

lo = pd.read_csv(sys.argv[1], usecols=["Pop2030", "FinalElecCode2030", "X_deg", "Y_deg"])
hi = pd.read_csv(sys.argv[2], usecols=["FinalElecCode2030"])
T = {1: "Grid", 2: "Grid", 3: "SA", 5: "MG", 6: "MG", 7: "MG"}
a = lo.FinalElecCode2030.astype(int).map(T)
b = hi.FinalElecCode2030.astype(int).map(T)
switch = (a == "SA") & (b == "MG")
grid = (a == "Grid") & (b == "Grid")
other = ~(switch | grid)
M = lambda m: lo.Pop2030[m].sum() / 1e6

SURF, INK, INK2 = "#fcfcfb", "#0b0b0b", "#52514e"
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#b9b8b2"
fig, ax = plt.subplots(figsize=(6.2, 8.6), dpi=160)
fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
for m, col, lab, s, z in [
        (other, GRAY, f"Same off-grid choice or other change ({M(other):.1f} M)", 1.2, 1),
        (grid, BLUE, f"Grid in both scenarios ({M(grid):.1f} M)", 2.0, 2),
        (switch, ORANGE, f"Stand-alone solar or mini-grid,\ndepending on assumed demand ({M(switch):.1f} M)", 1.6, 3)]:
    ax.scatter(lo.X_deg[m], lo.Y_deg[m], s=s, c=col, linewidths=0, alpha=0.85, label=lab, zorder=z, rasterized=True)
ax.set_aspect(1 / np.cos(np.deg2rad(19))); ax.axis("off")
ax.legend(loc="upper left", bbox_to_anchor=(-0.02, 0.995), frameon=False, fontsize=8.5, markerscale=6,
          labelcolor=INK2, handletextpad=0.4, labelspacing=0.9)
fig.text(0.06, 0.965, "For a third of Madagascar, the plan is set by an assumption", fontsize=12.5, color=INK, weight="bold")
fig.text(0.06, 0.94, "Least-cost technology in 2030 under low vs. high demand targets, by settlement (people in 2030)", fontsize=8.5, color=INK2)
fig.text(0.06, 0.02, "Own GEP-OnSSET runs, 155,275 settlements. Several parameters assumed; see onsset_madagascar/README.md.", fontsize=7, color=INK2)
fig.subplots_adjust(left=0.04, right=0.98, top=0.92, bottom=0.04)
fig.savefig(sys.argv[3], facecolor=SURF)
