"""Maps of the framework's decision per settlement at low demand, with budget limits,
for two line-cost assumptions.   usage: python plot_case_study.py"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
r = pd.read_csv(os.path.join(HERE, "results", "case_study_settlements.csv"))
r = r[(r.budgets == "with budget limits") & r.scenario.str.startswith("low")]
SURF, INK, INK2 = "#fcfcfb", "#0b0b0b", "#52514e"
COL = {"Approve": "#2a78d6", "Support or pilot": "#eb6834", "Defer": "#b9b8b2"}
r["cls"] = r.decision.replace({"Approve with support": "Support or pilot", "Pilot with subsidy": "Support or pilot"})
lines = [("cheap cable (1 per m)", "Cheap cable, 1 per metre"), ("GEP LV line (4.25 per m)", "Standard line, 4.25 per metre")]
regions = ["Antongil Bay", "Ambanja"]

fig, axes = plt.subplots(2, 2, figsize=(8.6, 9.6), dpi=150)
fig.patch.set_facecolor(SURF)
for i, (lc, lc_label) in enumerate(lines):
    for j, reg in enumerate(regions):
        ax = axes[i, j]; ax.set_facecolor(SURF)
        g = r[(r.line_cost == lc) & (r.region == reg)]
        for cls, z in (("Defer", 1), ("Support or pilot", 2), ("Approve", 3)):
            h = g[g.cls == cls]
            ax.scatter(h.X_deg, h.Y_deg, s=np.clip(np.sqrt(h.Pop2030) * 0.9, 5, 90), c=COL[cls], alpha=0.85,
                       linewidths=0.4, edgecolors=SURF, zorder=z)
        share = g.groupby("cls").Pop2030.sum() / g.Pop2030.sum()
        n = g.groupby("cls").size()
        txt = f"Approved: {share.get('Approve', 0):.0%} of people, {n.get('Approve', 0):,} of {len(g):,} settlements"
        ax.set_title(f"{reg}: {lc_label.lower()}", fontsize=9.3, color=INK, loc="left", pad=15)
        ax.text(0, 1.012, txt, transform=ax.transAxes, fontsize=7.8, color=INK2, va="bottom")
        ax.set_aspect(1 / np.cos(np.deg2rad(abs(g.Y_deg.mean()))))
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color("#e3e2dd")
handles = [plt.Line2D([], [], marker="o", ls="", ms=8, mfc=COL[c], mec=SURF, label=c) for c in COL]
fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.04, 0.912), ncol=3, frameon=False, fontsize=9,
           labelcolor=INK2, handletextpad=0.3, columnspacing=1.6)
fig.text(0.05, 0.972, "At low demand, the lines decide", fontsize=13, weight="bold", color=INK)
fig.text(0.05, 0.95, "Decision of the Ouanes et al. benefit ratio per settlement: rural Tier 1 demand, with budget limits,\n"
         "once the cost of the interconnecting lines is included.", fontsize=8.6, color=INK2, va="top")
fig.text(0.05, 0.012, "Off-grid settlements with at least 15 households; marker size follows population.\n"
         "Without line costs every settlement is approved; without budget limits every settlement is deferred.",
         fontsize=7.6, color=INK2, va="bottom")
fig.subplots_adjust(left=0.05, right=0.97, top=0.845, bottom=0.06, hspace=0.22, wspace=0.08)
fig.savefig(os.path.join(HERE, "..", "docs", "fig_case_study_decisions.png"), facecolor=SURF)
