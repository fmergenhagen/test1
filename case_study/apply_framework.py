"""
Case study, step 2: apply the framework of Ouanes et al. (2026) to real settlements.

For every off-grid settlement with at least 15 households in two regions of Madagascar
(Antongil Bay and the Ambanja area), this script

  1. builds the representative swarm cluster used in lookup.jl (three household nanogrids
     plus an anchor load) from the settlement's OnSSET data,
  2. computes the paper's heterogeneity indexes (SDI, PDI, BHI, H_raw) and indicators
     (avoided investment, energy shared, OPEX saving, social welfare),
  3. combines them into the paper's benefit ratio BR (planning horizon N = 1 year, as
     implied by the paper's Table 9) and applies its decision rule, and
  4. repeats 3 with the cost of the interconnecting lines, which the paper leaves out,
     taken from the settlement's size and area.

usage: python apply_framework.py <low_result.csv> <high_result.csv>
"""
import glob
import os
import sys

import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator

HERE = os.path.dirname(os.path.abspath(__file__))
REGIONS = {  # lon_min, lon_max, lat_min, lat_max
    "Antongil Bay": (49.2, 50.3, -16.3, -15.0),
    "Ambanja": (48.1, 48.9, -14.1, -13.3),
}
TIER_KWH_HH = {1: 38.7, 2: 219.0, 3: 803.0, 4: 2117.0, 5: 2993.0}   # ESMAP tiers, kWh per household-year
HH_PER_NANOGRID = 5
CLUSTER_HH = 15                       # three household nanogrids

# --- parameters taken from the paper -------------------------------------------------
V_ENERGY = 0.3                        # EUR per kWh shared (Section 6.2)
LAMBDA_SW = 10.0                      # EUR per welfare unit and year (Section 6.2)
CAPEX_PAPER_YEAR = 6.99 * 52          # the paper's swarm CAPEX, used to keep SW in proportion
SWS = {(True, True): 1.00, (True, False): 0.79, (False, True): 0.82, (False, False): 0.65}
#      (budget limits, anchor load) -> normalised social welfare score, Table A.10
W_S, W_P, W_B = 0.25, 0.25, 0.50      # weights of H_raw (Section 6.2)

# --- what the paper leaves out: line cost ---------------------------------------------
# GEP Madagascar: low-voltage line 4,250 USD/km. Levelised at 8 % over 30 years plus 2 % O&M.
# USD and EUR are treated as equal here.
CRF = 0.08 / (1 - 1.08 ** -30)
LINE_COST = {"none": 0.0, "cheap cable (1 per m)": 1.0 * (CRF + 0.02), "GEP LV line (4.25 per m)": 4.25 * (CRF + 0.02)}


def load_lookup():
    files = glob.glob(os.path.join(HERE, "results", "lookup*.csv"))
    lk = pd.concat([pd.read_csv(f) for f in files]).drop_duplicates(["rho", "ghi"]).sort_values(["rho", "ghi"])
    rhos, ghis = np.sort(lk.rho.unique()), np.sort(lk.ghi.unique())
    cols = ["SDI", "PDI", "BHI", "capex_alone", "opex_alone", "capex_swarm", "opex_swarm", "shared_swarm",
            "capex_budget", "opex_budget", "shared_budget", "demand_res"]
    interp = {c: RegularGridInterpolator((rhos, ghis), lk.pivot(index="rho", columns="ghi", values=c).values)
              for c in cols}
    return interp, rhos, ghis


def decision(br, h):
    """The paper's decision structure (Section 2.2)."""
    out = np.full(br.shape, "Defer", dtype=object)
    out[(br >= 0.7) & (br < 0.8) & (h >= 0.3)] = "Pilot with subsidy"
    out[(br >= 0.8) & (br < 1.0) & (h >= 0.3)] = "Approve with support"
    out[br >= 1.0] = "Approve"
    return out


def evaluate(path, scenario, interp, rhos, ghis):
    cols = ["X_deg", "Y_deg", "Pop2030", "NumPeoplePerHH", "GridCellArea", "FinalElecCode2030", "GHI", "Tier",
            "CommercialDemand2030", "AgriDemand2030", "HealthDemand2030", "EducationDemand2030"]
    d = pd.read_csv(path, usecols=cols)
    d["region"] = None
    for name, (x0, x1, y0, y1) in REGIONS.items():
        d.loc[d.X_deg.between(x0, x1) & d.Y_deg.between(y0, y1), "region"] = name
    d = d[d.region.notna() & d.FinalElecCode2030.isin([3, 5, 6, 7])].copy()        # off-grid in the plan
    d["households"] = d.Pop2030 / d.NumPeoplePerHH
    d = d[d.households >= CLUSTER_HH].copy()
    d["scenario"] = scenario
    d["onsset_tech"] = d.FinalElecCode2030.map({3: "Stand-alone PV", 5: "Mini-grid", 6: "Mini-grid", 7: "Mini-grid"})
    d["kwh_hh"] = d.Tier.astype(int).map(TIER_KWH_HH)
    other = d[["CommercialDemand2030", "AgriDemand2030", "HealthDemand2030", "EducationDemand2030"]].sum(axis=1)
    d["rho"] = (other / (d.households * d.kwh_hh)).clip(0, rhos.max())
    pts = np.column_stack([d.rho.values, d.GHI.clip(ghis.min(), ghis.max()).values])
    v = {c: f(pts) for c, f in interp.items()}

    # scale the cluster from the lookup's reference demand to this settlement's demand level
    scale = CLUSTER_HH * d.kwh_hh.values / 52.0 / v["demand_res"]       # weekly residential demand ratio
    yr = 52.0 * scale
    anchor = d.rho.values >= 0.01
    k = np.where(anchor, 4, 3)                                           # nanogrids in the cluster
    d["nanogrid_spacing_m"] = np.sqrt(d.GridCellArea * 1e6 / (d.households / HH_PER_NANOGRID))
    d["line_m"] = (k - 1) * d.nanogrid_spacing_m                         # a tree connecting the cluster
    d["SDI"], d["PDI"] = v["SDI"], v["PDI"]
    d["AVIN_pct"] = 100 * (v["capex_alone"] - v["capex_swarm"]) / v["capex_alone"]

    rows = []
    for budgets in (False, True):
        tag = "with budget limits" if budgets else "no budget limits"
        capex = (v["capex_budget"] if budgets else v["capex_swarm"]) * yr
        opex = (v["opex_budget"] if budgets else v["opex_swarm"]) * yr
        shared = (v["shared_budget"] if budgets else v["shared_swarm"]) * yr
        d_capex = (v["capex_alone"] - v["capex_swarm"]) * yr              # paper: CAPEX x AVIN
        d_opex = v["opex_alone"] * yr - opex
        eb = shared * V_ENERGY
        sws = np.array([SWS[(budgets, a)] for a in anchor])
        sw = sws * LAMBDA_SW * capex / CAPEX_PAPER_YEAR                   # kept in the paper's proportion
        bhi = v["BHI"] if budgets else 0.0
        h_raw = W_S * v["SDI"] + W_P * v["PDI"] + W_B * bhi
        for line_name, c_line in LINE_COST.items():
            lc = d.line_m.values * c_line
            br = (d_capex - lc + eb + d_opex + sw) / (capex + lc)
            r = d[["region", "scenario", "onsset_tech", "X_deg", "Y_deg", "Pop2030", "households", "kwh_hh", "rho",
                   "GHI", "nanogrid_spacing_m", "line_m", "SDI", "PDI", "AVIN_pct"]].copy()
            r["budgets"], r["line_cost"] = tag, line_name
            r["BHI"], r["H_raw"] = bhi, h_raw
            r["capex_year"], r["energy_shared_year"], r["line_cost_year"] = capex, shared, lc
            r["BR"] = br
            r["decision"] = decision(br, h_raw)
            rows.append(r)
    return pd.concat(rows, ignore_index=True)


def wmedian(x, w):
    o = np.argsort(x.values)
    return float(np.interp(0.5, np.cumsum(w.values[o]) / w.sum(), x.values[o]))


if __name__ == "__main__":
    interp, rhos, ghis = load_lookup()
    res = pd.concat([evaluate(sys.argv[1], "low demand (rural Tier 1)", interp, rhos, ghis),
                     evaluate(sys.argv[2], "high demand (rural Tier 3)", interp, rhos, ghis)], ignore_index=True)
    out = os.path.join(HERE, "results")
    res.round(4).to_csv(os.path.join(out, "case_study_settlements.csv"), index=False)

    keys = ["region", "scenario", "budgets", "line_cost"]
    order = ["Approve", "Approve with support", "Pilot with subsidy", "Defer"]
    summ = []
    for key, g in res.groupby(keys, sort=False):
        row = dict(zip(keys, key))
        row.update(settlements=len(g), people_k=g.Pop2030.sum() / 1e3, BR_median=wmedian(g.BR, g.Pop2030),
                   H_raw_median=wmedian(g.H_raw, g.Pop2030))
        for o in order:
            row[f"share_people_{o}"] = g.loc[g.decision == o, "Pop2030"].sum() / g.Pop2030.sum()
        summ.append(row)
    summ = pd.DataFrame(summ)
    summ.round(3).to_csv(os.path.join(out, "case_study_summary.csv"), index=False)

    base = res[(res.budgets == "no budget limits") & (res.line_cost == "none")]
    desc = base.groupby(["region", "scenario"]).apply(lambda g: pd.Series({
        "settlements": len(g), "people_k": g.Pop2030.sum() / 1e3,
        "households_median": g.households.median(), "spacing_m_median": g.nanogrid_spacing_m.median(),
        "rho_median": g.rho.median(), "rho_p90": g.rho.quantile(0.9), "GHI_median": g.GHI.median(),
        "SDI_median": g.SDI.median(), "PDI_median": g.PDI.median(), "AVIN_pct_median": g.AVIN_pct.median(),
        "share_standalone_PV": (g.onsset_tech == "Stand-alone PV").mean()}))
    desc.round(3).to_csv(os.path.join(out, "case_study_description.csv"))
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.float_format", lambda x: f"{x:,.3f}")
    print(desc.T.to_string())
    print()
    print(summ.to_string(index=False))
