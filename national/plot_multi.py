"""Figures for the multi-stage results. usage: python plot_multi.py"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RES, PAPER = os.path.join(HERE, "results"), os.path.join(HERE, "..", "paper")
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e3e2dd"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"


def style(ax):
    ax.set_facecolor(SURF)
    ax.tick_params(colors=INK2, labelsize=8.5, length=0)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)


def title(fig, text, sub=None):
    fig.suptitle(text, x=0.02, y=0.985, ha="left", fontsize=11.5, weight="bold", color=INK)
    if sub:
        fig.text(0.02, 0.915, sub, ha="left", va="top", fontsize=8.5, color=INK2)


# ---- 1. expected cost against the probability that demand rises -----------------------------
c = pd.read_csv(os.path.join(RES, "multi_central.csv"))
c = c[c.menu == "without swarm"]
m, lo, hi = (c[c.frictions == f].sort_values("g") for f in ("moderate", "none", "strong"))
fig, ax = plt.subplots(figsize=(6.4, 4.1), dpi=160)
fig.patch.set_facecolor(SURF); style(ax)
ax.fill_between(m.g, lo.myopic_musd.values, hi.myopic_musd.values, color=BLUE, alpha=0.13, linewidth=0)
ax.fill_between(m.g, lo.target_musd.values, hi.target_musd.values, color=ORANGE, alpha=0.13, linewidth=0)
ax.plot(m.g, m.target_musd, color=ORANGE, lw=2, marker="o", ms=5, label="Size every system for the Tier 3 target from day one")
ax.plot(m.g, m.myopic_musd, color=BLUE, lw=2, marker="o", ms=5, label="Re-plan for current demand at every stage")
row = m[m.g == 0.25].iloc[0]
ax.annotate("", (0.25, row.target_musd - 14), (0.25, row.myopic_musd + 14), arrowprops=dict(arrowstyle="<->", color=INK2, lw=0.9))
ax.annotate(f"USD {row.target_musd - row.myopic_musd:,.0f} M a year", (0.25, (row.target_musd + row.myopic_musd) / 2),
            xytext=(7, 0), textcoords="offset points", fontsize=8.5, color=INK2, va="center")
ax.annotate("Size for the target", (0.62, 1040), xytext=(0, 12), textcoords="offset points", ha="center", fontsize=8.5, color=INK2)
ax.annotate("Re-plan at every stage", (0.62, 660), xytext=(10, -34), textcoords="offset points", ha="left", fontsize=8.5, color=INK2)
ax.set_ylim(0, 1320); ax.set_xlim(-0.02, 1.02)
ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0]); ax.set_xticklabels(["0 %", "25 %", "50 %", "75 %", "100 %"])
ax.set_xlabel("Probability per five-year stage that demand rises", fontsize=8.5, color=INK2)
ax.set_ylabel("Expected cost, USD million per year", fontsize=8.5, color=INK2)
ax.grid(axis="y", color=GRID, lw=0.8)
fig.legend(loc="upper left", bbox_to_anchor=(0.015, 0.90), ncol=1, frameon=False, fontsize=8.5, labelcolor=INK2, handlelength=1.6)
title(fig, "Sizing for the target costs far more unless growth is near certain")
fig.text(0.02, 0.012, "Lines: moderate adaptation frictions. Bands: from no frictions to strong frictions.", fontsize=7.5, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 0.82))
fig.savefig(os.path.join(PAPER, "fig_cost_vs_g.png"), facecolor=SURF)
plt.close(fig)

# ---- 2. national cost along every demand path -----------------------------------------------
p = pd.read_csv(os.path.join(RES, "multi_paths.csv"))
p = p[(p.frictions == "moderate") & (p.g == 0.25) & (p.menu == "without swarm")].sort_values("myopic", ascending=False)
labels = [f"Tier {' → '.join(s.split('-'))}   ({q:.0%})" if q >= 0.095 else f"Tier {' → '.join(s.split('-'))}   ({q:.1%})"
          for s, q in zip(p.path, p.prob)]
fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=160)
fig.patch.set_facecolor(SURF); style(ax)
y = range(len(p))
ax.hlines(y, p.myopic, p.target, color=GRID, lw=3, zorder=1)
ax.scatter(p.target, y, s=46, color=ORANGE, zorder=3, edgecolor=SURF, linewidth=1.2, label="Size every system for the Tier 3 target from day one")
ax.scatter(p.myopic, y, s=46, color=BLUE, zorder=3, edgecolor=SURF, linewidth=1.2, label="Re-plan for current demand at every stage")
ax.set_yticks(list(y)); ax.set_yticklabels(labels, fontsize=8.5, color=INK2)
ax.set_xlim(0, 1560); ax.set_ylim(-0.6, len(p) - 0.4)
ax.set_xlabel("National cost on this demand path, USD million per year", fontsize=8.5, color=INK2)
ax.grid(axis="x", color=GRID, lw=0.8)
fig.legend(loc="upper left", bbox_to_anchor=(0.015, 0.90), ncol=1, frameon=False, fontsize=8.5, labelcolor=INK2, handletextpad=0.4)
title(fig, "Sizing for the target costs more on every demand path")
fig.text(0.02, 0.012, "Demand path over three five-year stages, with its probability (25 % chance of a rise per stage). Moderate frictions.",
         fontsize=7.5, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 0.82))
fig.savefig(os.path.join(PAPER, "fig_paths.png"), facecolor=SURF)
plt.close(fig)

# ---- 3. which simple rule, as the cost of being caught short rises ---------------------------
v = pd.read_csv(os.path.join(RES, "multi_voll.csv"))
v = v[v.lag_years == 1]
fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.9), dpi=160, sharey=True)
fig.patch.set_facecolor(SURF)
series = (("myopic_over_stochastic", BLUE, "Re-plan for current demand"),
          ("target2_over_stochastic", AQUA, "Size for Tier 2 from day one"),
          ("target3_over_stochastic", ORANGE, "Size for Tier 3 from day one"))
for ax, g in zip(axes, (0.25, 0.5)):
    style(ax)
    d = v[v.g == g].sort_values("voll")
    for col, color, name in series:
        ax.plot(d.voll, 100 * (d[col] - 1), color=color, lw=2, marker="o", ms=4, label=name if g == 0.25 else None)
    ax.set_xscale("log")
    ax.set_xticks([0.25, 0.5, 1, 2, 4, 8]); ax.set_xticklabels(["0.25", "0.5", "1", "2", "4", "8"])
    ax.minorticks_off()
    ax.set_ylim(0, 150)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_title(f"{g:.0%} chance of a rise per stage", fontsize=8.5, color=INK2, loc="left")
axes[0].set_ylabel("Cost above the stochastic optimum, %", fontsize=8.5, color=INK2)
fig.legend(loc="upper left", bbox_to_anchor=(0.015, 0.915), ncol=3, frameon=False, fontsize=8, labelcolor=INK2, handlelength=1.4, columnspacing=1.2)
title(fig, "The best simple rule depends on what a shortfall costs")
fig.supxlabel("Value of energy not served during an upgrade, USD per kWh (log scale)", fontsize=8.5, color=INK2, y=0.06)
fig.text(0.02, 0.012, "One-year upgrade lag, added capacity 25 % dearer than greenfield. Menu without swarm grids.", fontsize=7.5, color=INK2)
fig.tight_layout(rect=(0, 0.05, 1, 0.88))
fig.savefig(os.path.join(PAPER, "fig_rules_vs_voll.png"), facecolor=SURF)
plt.close(fig)
print("figures written to", os.path.abspath(PAPER))
