"""Expected annual cost of two planning rules against the probability that demand rises.
usage: python plot_cost_vs_p.py"""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
r = pd.read_csv(os.path.join(HERE, "results", "two_stage_summary.csv"))
r = r[r.menu == "without swarm"].sort_values("p_high")
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e3e2dd"
BLUE, ORANGE = "#2a78d6", "#eb6834"
fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=160)
fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
ax.fill_between(r.p_high, r.plan_for_low_musd, r.plan_for_high_musd, color=ORANGE, alpha=0.08, linewidth=0)
ax.plot(r.p_high, r.plan_for_high_musd, color=ORANGE, lw=2, marker="o", ms=5, label="Build for the high target from day one")
ax.plot(r.p_high, r.plan_for_low_musd, color=BLUE, lw=2, marker="o", ms=5, label="Build for current demand, adapt later")
ax.annotate("Build for the high target from day one", (0.75, r.plan_for_high_musd.iloc[-2]), xytext=(0, 9),
            textcoords="offset points", ha="center", fontsize=8.5, color=INK2)
ax.annotate("Build for current demand, adapt later", (0.5, r.plan_for_low_musd.iloc[3]), xytext=(14, -24),
            textcoords="offset points", ha="left", fontsize=8.5, color=INK2)
row = r[r.p_high == 0.25].iloc[0]
ax.annotate("", (0.25, row.plan_for_high_musd - 12), (0.25, row.plan_for_low_musd + 12),
            arrowprops=dict(arrowstyle="<->", color=INK2, lw=0.9))
ax.annotate(f"USD {row.plan_for_high_musd - row.plan_for_low_musd:,.0f} M a year",
            (0.25, (row.plan_for_high_musd + row.plan_for_low_musd) / 2), xytext=(7, 0), textcoords="offset points",
            fontsize=8.5, color=INK2, va="center")
ax.set_ylim(0, 1150); ax.set_xlim(-0.02, 1.02)
ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0]); ax.set_xticklabels(["0 %", "25 %", "50 %", "75 %", "100 %"])
ax.set_xlabel("Probability that demand rises to the high level after five years", fontsize=8.5, color=INK2)
ax.set_ylabel("Expected cost, USD million per year", fontsize=8.5, color=INK2)
ax.tick_params(colors=INK2, labelsize=8.5, length=0)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
for s in ax.spines.values():
    s.set_visible(False)
fig.legend(loc="upper left", bbox_to_anchor=(0.015, 0.925), ncol=2, frameon=False, fontsize=8.5, labelcolor=INK2, handlelength=1.6, columnspacing=1.4)
fig.suptitle("Committing early costs far more than guessing wrong", x=0.02, y=0.98, ha="left", fontsize=11.5, weight="bold", color=INK)
fig.tight_layout(rect=(0, 0, 1, 0.88))
fig.savefig(os.path.join(HERE, "..", "paper", "fig_cost_vs_p.png"), facecolor=SURF)
