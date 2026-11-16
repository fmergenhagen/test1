"""
Specs files for the two extra demand states of the multi-stage model.

The baseline specs (onsset_madagascar/build_specs.py) hold two rows of scenario parameters:
row 0 = urban Tier 3 / rural Tier 1 (state 1), row 1 = urban Tier 4 / rural Tier 3 (state 3).
This adds row 2 = urban Tier 3 / rural Tier 2 (state 2) and row 3 = urban Tier 4 / rural Tier 4
(state 4) and writes one specs file per new state. Everything else is unchanged.

usage: python make_state_specs.py <mg-specs-low.xlsx> <out_dir>
Writes <out_dir>/mg-specs-t2.xlsx and mg-specs-t4.xlsx; OnSSET then names the outputs
mg-2-2_0_0.csv and mg-2-3_0_0.csv.
"""
import sys

import pandas as pd

src, out = sys.argv[1], sys.argv[2]
x = pd.read_excel(src, sheet_name=None)
p = pd.concat([x["ScenarioParameters"], x["ScenarioParameters"].iloc[[0, 1]]], ignore_index=True)
p.loc[2, ["UrbanTargetTier", "RuralTargetTier"]] = [3, 2]
p.loc[3, ["UrbanTargetTier", "RuralTargetTier"]] = [4, 4]
p["PopEndYear"] = [0, 1, 2, 3]
for name, tier in (("t2", 2), ("t4", 3)):
    info = x["ScenarioInfo"].copy()
    info["Target_electricity_consumption_level"] = tier
    with pd.ExcelWriter(f"{out}/mg-specs-{name}.xlsx") as w:
        info.to_excel(w, sheet_name="ScenarioInfo", index=False)
        p.to_excel(w, sheet_name="ScenarioParameters", index=False)
        x["SpecsData"].to_excel(w, sheet_name="SpecsData", index=False)
        x["SpecsDataCalib"].to_excel(w, sheet_name="SpecsDataCalib", index=False)
print("written", f"{out}/mg-specs-t2.xlsx", f"{out}/mg-specs-t4.xlsx")
