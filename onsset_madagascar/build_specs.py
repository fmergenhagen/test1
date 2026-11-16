"""
Build a GEP-OnSSET specs file for Madagascar from the calibrated settlement file.

Everything that can be derived from the input file is derived from it. Values marked
SOURCE come from the GEP Madagascar scenario description (mg-1, August 2019).
Values marked ASSUMED are copied from the Sierra Leone template shipped with gep-onsset
because no Madagascar value was available; replace them when the official specs file
is at hand.

usage: python build_specs.py <MG-inputs.csv> <out_dir>
Writes <out_dir>/mg-inputs-clean.csv, mg-specs-low.xlsx (urban tier 3 / rural tier 1)
and mg-specs-high.xlsx (urban tier 4 / rural tier 3).
"""
import sys
import pandas as pd

src, out = sys.argv[1], sys.argv[2]
d = pd.read_csv(src)
d = d.drop(columns=[c for c in d.columns if c.startswith("Unnamed")])
d["GridPenalty"] = d["GridPenalty"].fillna(d["GridPenalty"].mean())      # 6 missing values
d.to_csv(f"{out}/mg-inputs-clean.csv", index=False)

urban = d["IsUrban"] == 2
pop0, pop1 = d["Pop2020"].sum(), d["Pop2030"].sum()
elec = d["ElecPopCalib"].sum() / pop0
elec_u = d.loc[urban, "ElecPopCalib"].sum() / d.loc[urban, "Pop2020"].sum()
elec_r = d.loc[~urban, "ElecPopCalib"].sum() / d.loc[~urban, "Pop2020"].sum()
ur0 = d.loc[urban, "Pop2020"].sum() / pop0
ur1 = d.loc[urban, "Pop2030"].sum() / pop1

specs = pd.DataFrame([{
    "Country": "Madagascar", "CountryCode": "mg",
    "StartYear": 2020, "EndYEar": 2030,
    "PopStartYear": pop0, "UrbanRatioStartYear": ur0, "UrbanCutOff": None,
    "UrbanRatioModelled": ur0, "PopEndYear": pop1, "UrbanRatioEndYear": ur1,
    "NumPeoplePerHHRural": 4.4, "NumPeoplePerHHUrban": 3.7,         # SOURCE
    "GridCapacityInvestmentCost": 2238,                               # ASSUMED (USD/kW)
    "GridLosses": 0.167,                                              # ASSUMED
    "BaseToPeak": 0.8,                                                # ASSUMED
    "ExistingGridCostRatio": 0.1,                                     # ASSUMED
    "MaxGridExtensionDist": 50,                                       # ASSUMED (km)
    "NewGridGenerationCapacityAnnualLimitMW": 96,                     # SOURCE
    "ElecActual": elec, "Rural_elec_ratio": elec_r, "Urban_elec_ratio": elec_u,
    "ElecModelled": elec, "urban_elec_ratio_modelled": elec_u,
    "rural_elec_ratio_modelled": elec_r,
    "Diesel_Cost": 1, "GridCostLow": 0.1355, "GridCostHigh": 0.1355,  # SOURCE (grid cost)
    "GridConnectionsLimitThousands": 0.025 * pop0 / 4.1 / 1000,       # SOURCE: 2.5 % of pop/yr
    "UrbanTierLow": 3, "UrbanTierHigh": 4,
}])

params = pd.DataFrame({
    "PopEndYear": [0, 1],
    "UrbanTargetTier": [3, 4],            # SOURCE: low = U3-R1, high = U4-R3
    "RuralTargetTier": [1, 3],
    "5YearTarget": [0.65, 0.65],          # ASSUMED intermediate target for 2025
    "10YearTarget": [1.0, 1.0],           # universal access by 2030
    "GridConnectionsLimitThousands": [9999, specs.loc[0, "GridConnectionsLimitThousands"]],
    "GridGenerationCost": [0.1355, 0.1355],
    "PV_Cost_adjust": [1.0, 0.5],
    "DieselPrice": [1.08, 1.08],          # ASSUMED
    "ProductiveDemand": [1, 0],
    "PrioritizationAlgorithm": [5, 5],
    "AutoIntensificationKM": [0, 2],
})

for name, tier in [("low", 0), ("high", 1)]:
    info = pd.DataFrame([{
        "Scenario": 0, "Productive_uses_demand": 0,
        "Target_electricity_consumption_level": tier,
        "Grid_connection_cap": 0,                  # no annual connection cap, as in the GEP sample
        "Grid_electricity_generation_cost": 0, "PV_cost_adjust": 0,
        "Prioritization_algorithm": 1, "10YearTarget": 0,
    }])
    with pd.ExcelWriter(f"{out}/mg-specs-{name}.xlsx") as w:
        info.to_excel(w, sheet_name="ScenarioInfo", index=False)
        params.to_excel(w, sheet_name="ScenarioParameters", index=False)
        specs.to_excel(w, sheet_name="SpecsData", index=False)
        specs.to_excel(w, sheet_name="SpecsDataCalib", index=False)

print(f"population 2020 {pop0/1e6:.2f} M -> 2030 {pop1/1e6:.2f} M; urban {ur0:.1%} -> {ur1:.1%}")
print(f"electrified 2020: national {elec:.1%}, urban {elec_u:.1%}, rural {elec_r:.1%}")
