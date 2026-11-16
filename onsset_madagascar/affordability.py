"""
Affordability layer on top of GEP-OnSSET results (prototype).

OnSSET picks the cheapest technology per settlement for an exogenous demand tier and
implicitly assumes every household can pay for it. This script turns the result file
into what a household would actually have to pay:

  annual bill      = LCOE of the chosen technology x household consumption at the tier
  upfront cost     = investment per newly connected household

and, if a household budget is supplied, the share of people for whom the bill exceeds
a given fraction of that budget.

usage:
  python affordability.py <onsset_result.csv> [--budget-col COL] [--share 0.05]

`--budget-col` names a column with annual household expenditure (USD) per settlement.
No such column exists in GEP output; it has to be merged in from survey data
(e.g. DHS wealth index mapped to a consumption distribution). Without it, the script
reports bills and the expenditure a household would need for the bill to be affordable.
"""
import argparse
import numpy as np
import pandas as pd

# ESMAP multi-tier framework, kWh per household per year, as used by GEP
TIER_KWH_HH = {1: 38.7, 2: 219.0, 3: 803.0, 4: 2117.0, 5: 2993.0}
TECH = {1: "Grid (existing)", 2: "Grid (new)", 3: "Stand-alone PV", 5: "Mini-grid PV hybrid",
        6: "Mini-grid wind hybrid", 7: "Mini-grid hydro"}


def wquantile(x, w, q):
    o = np.argsort(x)
    x, w = np.asarray(x)[o], np.asarray(w)[o]
    return np.interp(q, np.cumsum(w) / w.sum(), x)


def household_table(df, year=2030):
    out = pd.DataFrame({
        "pop": df[f"Pop{year}"],
        "urban": df["IsUrban"] > 1,           # GEP: 0 rural, 1 peri-urban, 2 urban
        "tier": df["Tier"].astype(int),
        "tech": df[f"FinalElecCode{year}"].astype(int).map(TECH),
        "lcoe": df[f"MinimumOverallLCOE{year}"],
        "hh_size": df["NumPeoplePerHH"],
    })
    out["kwh_hh"] = out["tier"].map(TIER_KWH_HH)
    out["bill"] = out["lcoe"] * out["kwh_hh"]                       # USD per household-year
    new_hh = df[f"NewConnections{year}"] / df["NumPeoplePerHH"]
    out["upfront"] = np.where(new_hh > 0, df[f"InvestmentCost{year}"] / new_hh, np.nan)
    return out


def summarise(t, share=0.05, budget=None):
    rows = []
    for (urban, tech), g in t.groupby(["urban", "tech"]):
        w = g["pop"]
        u = g.dropna(subset=["upfront"])
        r = {"area": "urban" if urban else "rural", "technology": tech,
             "people_million": w.sum() / 1e6,
             "tier": int(g["tier"].mode().iloc[0]),
             "lcoe_median": wquantile(g["lcoe"], w, 0.5),
             "bill_median": wquantile(g["bill"], w, 0.5),
             "bill_p90": wquantile(g["bill"], w, 0.9),
             "needed_budget_median": wquantile(g["bill"], w, 0.5) / share,
             "upfront_median": wquantile(u["upfront"], u["pop"], 0.5) if len(u) else np.nan}
        if budget is not None:
            b = budget.loc[g.index]
            r["share_unaffordable"] = (w * (g["bill"] > share * b)).sum() / w.sum()
        rows.append(r)
    return pd.DataFrame(rows).sort_values(["area", "people_million"], ascending=[True, False])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("result_csv")
    ap.add_argument("--budget-col")
    ap.add_argument("--share", type=float, default=0.05)
    ap.add_argument("--out")
    a = ap.parse_args()
    df = pd.read_csv(a.result_csv)
    t = household_table(df)
    s = summarise(t, a.share, df[a.budget_col] if a.budget_col else None)
    pd.set_option("display.width", 200, "display.float_format", lambda v: f"{v:,.2f}")
    print(s.to_string(index=False))
    if a.out:
        s.to_csv(a.out, index=False)
