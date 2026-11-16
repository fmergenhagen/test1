"""
Summarise a GEP-OnSSET result for Madagascar and screen for swarm-grid candidates.

The screen is descriptive. It asks: among the people the least-cost plan assigns to
stand-alone solar or to mini-grids, how many live in settlements that are big and dense
enough for nanogrids to be interconnected? It does not yet model the swarm option.

  households     = Pop2030 / household size
  nanogrids      = households / 5            (a nanogrid serves about 5 households)
  spacing        = sqrt(settlement area / nanogrids)   (lattice spacing between nanogrids)
  candidate      = at least `min_nanogrids` nanogrids and spacing <= `max_spacing` metres

usage: python screen_swarm.py <result.csv> [--max-spacing 150] [--min-nanogrids 3] [--out summary.csv]
"""
import argparse
import numpy as np
import pandas as pd

TECH = {1: "Grid (existing)", 2: "Grid (new)", 3: "Stand-alone PV", 5: "Mini-grid PV hybrid",
        6: "Mini-grid wind hybrid", 7: "Mini-grid hydro"}

ap = argparse.ArgumentParser()
ap.add_argument("result_csv")
ap.add_argument("--max-spacing", type=float, default=150.0)
ap.add_argument("--min-nanogrids", type=float, default=3.0)
ap.add_argument("--out")
a = ap.parse_args()

cols = ["Pop2030", "NumPeoplePerHH", "GridCellArea", "FinalElecCode2030", "IsUrban",
        "MinimumOverallLCOE2030", "InvestmentCost2025", "InvestmentCost2030", "Tier",
        "NewConnections2025", "NewConnections2030"]
d = pd.read_csv(a.result_csv, usecols=cols)
d["tech"] = d["FinalElecCode2030"].astype(int).map(TECH)
d["hh"] = d["Pop2030"] / d["NumPeoplePerHH"]
d["ng"] = d["hh"] / 5
d["spacing"] = np.sqrt(d["GridCellArea"] * 1e6 / d["ng"].clip(lower=1e-9))
d["invest"] = d["InvestmentCost2025"].fillna(0) + d["InvestmentCost2030"].fillna(0)
tot = d["Pop2030"].sum()

pd.set_option("display.width", 200, "display.float_format", lambda v: f"{v:,.2f}")
t = d.groupby("tech").agg(people_million=("Pop2030", lambda s: s.sum() / 1e6),
                          settlements=("Pop2030", "size"),
                          invest_bn=("invest", lambda s: s.sum() / 1e9)).sort_values("people_million", ascending=False)
t["share"] = t["people_million"] * 1e6 / tot
print("== Technology split in 2030 ==")
print(t.to_string())
print(f"total: {tot/1e6:.2f} million people, investment 2020-2030 USD {d['invest'].sum()/1e9:.2f} bn\n")

d["cand"] = (d["ng"] >= a.min_nanogrids) & (d["spacing"] <= a.max_spacing)
rows = []
for tech in ["Stand-alone PV", "Mini-grid PV hybrid"]:
    g = d[d["tech"] == tech]
    c = g[g["cand"]]
    rows.append({"assigned_to": tech, "people_million": g["Pop2030"].sum() / 1e6,
                 "candidate_people_million": c["Pop2030"].sum() / 1e6,
                 "candidate_share": c["Pop2030"].sum() / max(g["Pop2030"].sum(), 1),
                 "candidate_settlements": len(c),
                 "median_households": c["hh"].median(), "median_spacing_m": c["spacing"].median()})
s = pd.DataFrame(rows)
print(f"== Swarm screen: >= {a.min_nanogrids:g} nanogrids and spacing <= {a.max_spacing:g} m ==")
print(s.to_string(index=False))

sa = d[d["tech"] == "Stand-alone PV"]
bins = [0, 5, 15, 50, 150, 500, 1e9]
lab = ["<5", "5-15", "15-50", "50-150", "150-500", ">500"]
size = sa.groupby(pd.cut(sa["hh"], bins, labels=lab), observed=True).agg(
    people_million=("Pop2030", lambda x: x.sum() / 1e6), settlements=("hh", "size"),
    median_spacing_m=("spacing", "median"))
print("\n== Stand-alone PV settlements by size (households) ==")
print(size.to_string())
if a.out:
    t.to_csv(a.out.replace(".csv", "_split.csv"))
    s.to_csv(a.out, index=False)
    size.to_csv(a.out.replace(".csv", "_sa_size.csv"))
