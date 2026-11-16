"""
Technology choice under demand uncertainty, settlement by settlement.

Inputs: GEP-OnSSET result files for Madagascar at a low and a high demand target, and the
same two runs with a lower mini-grid fixed cost (the swarm / mesh-grid proxy).

For every settlement that is unelectrified at the start and never reached by the grid in
either baseline run, OnSSET's first-step levelised costs give the annual cost A[k, d] of
serving it with technology k at demand level d:

    A[k, d] = LCOE_k,d  x  annual energy demand at level d            (USD per year)

Two-stage model (stage 1 = years 1-5, stage 2 = years 6-15, 8 % discount rate):
  stage 1: demand is low. Build technology k, sized for low demand (k, L) or already for
           high demand (k, H).
  stage 2: demand stays low with probability 1 - p, or rises to the high level with p.
           After (k, L) and high demand one may expand k in place (cost A[k, H]) or switch
           to j (cost A[j, H] plus the stranded part of k's capital, share (1 - chi[k->j])).
           After (k, H) nothing changes; the system is oversized while demand is low and
           then costs its capital share plus the running cost of the energy actually used.

Technologies: SA = stand-alone PV, MG = conventional mini-grid (cheapest of PV-hybrid,
hydro, wind-hybrid), SW = swarm / mesh grid. The swarm is built from OnSSET's PV-hybrid
mini-grid cost, split into three parts with the help of two extra OnSSET runs:

    mini-grid cost = G (generation, storage, connections) + lines x c_LV + fixed x F

    swarm cost     = (1 + premium) x G + lines x c_swarm + fixed x F_swarm

so a swarm is a mini-grid with a smaller fixed cost per system and cheaper low-voltage
lines, but more expensive generation because it is built in small distributed units.

usage: python two_stage.py <low.csv> <high.csv> <low_F2500.csv> <high_F2500.csv> <low_F2500_LV2000.csv> <high_F2500_LV2000.csv>
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
R, T1, T = 0.08, 5, 15
pv = lambda a, b: sum((1 + R) ** -t for t in range(a, b + 1))
W1, W2 = pv(1, T1) / pv(1, T), pv(T1 + 1, T) / pv(1, T)

F_MG, F_RUN = 10000.0, 2500.0          # mini-grid fixed cost in OnSSET; value used in the proxy run
LV_MG, LV_RUN = 4250.0, 2000.0         # low-voltage line cost per km in OnSSET; value used in the proxy run
SWARM = dict(premium=0.30, fixed=2500.0, lv=2000.0)   # ASSUMED central case for the swarm option
CAP_SHARE = {"SA": 0.85, "MG": 0.75, "SW": 0.75}    # ASSUMED capital share of levelised cost
COLS = ["Pop2025", "Pop2030", "ElecStart", "FinalElecCode2030", "EnergyPerSettlement2025", "NumPeoplePerHH",
        "SA_PV2025", "MG_PV_Hybrid2025", "MG_Hydro2025", "MG_Wind_Hybrid2025", "X_deg", "Y_deg", "GridCellArea"]


def load(paths):
    lo, hi = pd.read_csv(paths[0], usecols=COLS), pd.read_csv(paths[1], usecols=COLS)
    col = lambda f: pd.read_csv(f, usecols=["MG_PV_Hybrid2025"]).MG_PV_Hybrid2025
    runs = {"L": (col(paths[2]), col(paths[4])), "H": (col(paths[3]), col(paths[5]))}
    dom = (lo.ElecStart == 0) & ~lo.FinalElecCode2030.isin([1, 2]) & ~hi.FinalElecCode2030.isin([1, 2])
    d = {}
    for name, df in (("L", lo), ("H", hi)):
        g = df[dom]
        e = g.EnergyPerSettlement2025.values
        mg = g[["MG_PV_Hybrid2025", "MG_Hydro2025", "MG_Wind_Hybrid2025"]].min(axis=1).values
        base = g.MG_PV_Hybrid2025.values * e                       # F = 10,000, LV = 4,250
        f_run = runs[name][0][dom].values * e                      # F = 2,500,  LV = 4,250
        lv_run = runs[name][1][dom].values * e                     # F = 2,500,  LV = 2,000
        fixed_unit = (base - f_run) / (F_MG - F_RUN)               # USD per year per USD of fixed cost
        line_unit = (f_run - lv_run) / (LV_MG - LV_RUN)            # USD per year per USD/km of line cost
        gen = base - fixed_unit * F_MG - line_unit * LV_MG         # generation, storage, connections
        d[name] = dict(E=e, SA=g.SA_PV2025.values * e, MG=mg * e, mgpv=base,
                       gen=gen, fixed_unit=fixed_unit, line_unit=line_unit)
    meta = lo.loc[dom, ["Pop2025", "Pop2030", "NumPeoplePerHH", "X_deg", "Y_deg", "GridCellArea"]].reset_index(drop=True)
    return d, meta


def swarm_cost(d, premium, fixed, lv):
    """Annual cost of the swarm option per settlement and demand level (see module docstring)."""
    return {s: (1 + premium) * d[s]["gen"] + d[s]["line_unit"] * lv + d[s]["fixed_unit"] * fixed for s in ("L", "H")}


def solve(A, menu, p, chi, e_ratio):
    """Expected annual cost per settlement for every first-stage action, and the best one.
    A[k][s] are arrays of annual cost. Returns (table of actions, expected cost array)."""
    acts, ec = [], []
    for k in menu:
        # sized for low demand, adapt later
        best_high = A[k]["H"].copy()                                     # expand in place
        for j in menu:
            if j == k:
                continue
            switch = A[j]["H"] + (1 - chi.get((k, j), 0.0)) * CAP_SHARE[k] * A[k]["L"]
            best_high = np.minimum(best_high, switch)
        ec.append(W1 * A[k]["L"] + W2 * ((1 - p) * A[k]["L"] + p * best_high)); acts.append(f"{k}, sized for low demand")
        # sized for high demand from the start: while demand is low only the capital share and
        # the energy-proportional part of the running cost are paid
        idle = CAP_SHARE[k] * A[k]["H"] + (1 - CAP_SHARE[k]) * A[k]["H"] * e_ratio
        ec.append(W1 * idle + W2 * ((1 - p) * idle + p * A[k]["H"])); acts.append(f"{k}, sized for high demand")
    ec = np.vstack(ec)
    return acts, ec


def evaluate(d, meta, sw_par, chi, probs):
    sw = swarm_cost(d, **sw_par)
    A = {"SA": {s: d[s]["SA"] for s in "LH"}, "MG": {s: d[s]["MG"] for s in "LH"}, "SW": sw}
    pop = meta.Pop2025.values
    e_ratio = d["L"]["E"] / d["H"]["E"]                       # low over high energy demand
    rows, choice = [], {}
    for p in probs:
        res = {}
        for label, menu in (("without swarm", ["SA", "MG"]), ("with swarm", ["SA", "MG", "SW"])):
            acts, ec = solve(A, menu, p, chi, e_ratio)
            best = ec.argmin(axis=0)
            res[label] = ec.min(axis=0)
            choice[(p, label)] = (acts, best)
            # myopic plans, both restricted to the same menu
            k_low = np.argmin(np.vstack([A[k]["L"] for k in menu]), axis=0)          # least cost at low demand
            k_high = np.argmin(np.vstack([A[k]["H"] for k in menu]), axis=0)         # least cost at high demand
            plan_low = np.choose(k_low, [ec[2 * i] for i in range(len(menu))])       # build for low, adapt
            plan_high = np.choose(k_high, [ec[2 * i + 1] for i in range(len(menu))]) # build for high, commit
            # perfect information: know in advance whether demand will rise
            c_low = np.min(np.vstack([A[k]["L"] for k in menu]), axis=0)
            _, ec_hi = solve(A, menu, 1.0, chi, e_ratio)
            perfect = (1 - p) * c_low + p * ec_hi.min(axis=0)
            rows.append(dict(p_high=p, menu=label, **{"swarm_" + k: v for k, v in sw_par.items()},
                             plan_for_low_musd=plan_low.sum() / 1e6, plan_for_high_musd=plan_high.sum() / 1e6,
                             stochastic_musd=res[label].sum() / 1e6, perfect_info_musd=perfect.sum() / 1e6,
                             usd_per_person_stochastic=res[label].sum() / pop.sum()))
            share = pd.Series(pop).groupby(np.array(acts)[best]).sum() / pop.sum()
            for a, v in share.items():
                rows[-1][f"share_people: {a}"] = v
    return pd.DataFrame(rows).fillna(0.0), choice, A


if __name__ == "__main__":
    d, meta = load(sys.argv[1:7])
    pop = meta.Pop2025.values
    out = os.path.join(HERE, "results")
    pd.set_option("display.width", 250, "display.max_columns", 40, "display.float_format", lambda x: f"{x:,.3f}")
    print(f"domain: {len(meta):,} settlements, {pop.sum()/1e6:.2f} M people (2025), stage weights {W1:.3f} / {W2:.3f}")
    probs = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
    chi = {("SA", "SW"): 1.0, ("SW", "MG"): 1.0, ("SA", "MG"): 0.0, ("MG", "SW"): 1.0, ("SW", "SA"): 0.0, ("MG", "SA"): 0.0}

    # 1. central case
    res, choice, A = evaluate(d, meta, SWARM, chi, probs)
    res.round(4).to_csv(os.path.join(out, "two_stage_summary.csv"), index=False)
    print(res.to_string(index=False))

    # 2. cost levels behind the result, and the split of the mini-grid cost
    names = list(A)
    cheapest = lambda s: np.argmin(np.vstack([A[j][s] for j in names]), axis=0)
    desc = pd.DataFrame({
        "USD/person/yr, low demand": {k: A[k]["L"].sum() / pop.sum() for k in names},
        "USD/person/yr, high demand": {k: A[k]["H"].sum() / pop.sum() for k in names},
        "cheapest at low demand (M people)": {k: pop[cheapest("L") == i].sum() / 1e6 for i, k in enumerate(names)},
        "cheapest at high demand (M people)": {k: pop[cheapest("H") == i].sum() / 1e6 for i, k in enumerate(names)}})
    desc.round(3).to_csv(os.path.join(out, "two_stage_costs.csv"))
    print(desc.to_string())
    split = pd.DataFrame({s: {"generation etc.": d[s]["gen"].sum(), "lines": (d[s]["line_unit"] * LV_MG).sum(),
                              "fixed cost": (d[s]["fixed_unit"] * F_MG).sum()} for s in ("L", "H")})
    split = split / split.sum()
    split.columns = ["share at low demand", "share at high demand"]
    split.round(3).to_csv(os.path.join(out, "minigrid_cost_split.csv"))
    print(split.to_string())
    neg = {s: float((d[s]["gen"] < 0).mean()) for s in "LH"}
    print("share of settlements with negative residual generation cost:", neg)

    # 3. when does the swarm option matter? generation premium x fixed cost, at p = 0.25 and 0.5
    grid = []
    for prem in (0.0, 0.15, 0.30, 0.50, 0.75):
        for fixed in (0.0, 2500.0, 5000.0):
            r, _, _ = evaluate(d, meta, dict(premium=prem, fixed=fixed, lv=SWARM["lv"]), chi, [0.25, 0.5])
            w, wo = r[r.menu == "with swarm"], r[r.menu == "without swarm"]
            for p in (0.25, 0.5):
                a, b = w[w.p_high == p].iloc[0], wo[wo.p_high == p].iloc[0]
                sw_share = sum(v for k, v in a.items() if str(k).startswith("share_people: SW"))
                grid.append(dict(premium=prem, fixed=fixed, p_high=p, saving_pct=100 * (1 - a.stochastic_musd / b.stochastic_musd),
                                 saving_musd=b.stochastic_musd - a.stochastic_musd, share_people_starting_with_swarm=sw_share))
    grid = pd.DataFrame(grid)
    grid.round(4).to_csv(os.path.join(out, "swarm_sensitivity.csv"), index=False)
    print(grid.pivot_table(index="premium", columns=["p_high", "fixed"], values="saving_pct").round(2).to_string())
    print(grid.pivot_table(index="premium", columns=["p_high", "fixed"], values="share_people_starting_with_swarm").round(3).to_string())

    # 4. compatibility
    comp = []
    for name, c in (("all reusable", chi),
                    ("swarm hardware stranded by a mini-grid", {**chi, ("SW", "MG"): 0.0}),
                    ("stand-alone systems not reusable in a swarm", {**chi, ("SA", "SW"): 0.0}),
                    ("stand-alone systems reusable in a mini-grid", {**chi, ("SA", "MG"): 1.0})):
        r, _, _ = evaluate(d, meta, SWARM, c, [0.25, 0.5])
        r.insert(0, "compatibility", name)
        comp.append(r)
    comp = pd.concat(comp, ignore_index=True)
    comp.round(4).to_csv(os.path.join(out, "two_stage_compatibility.csv"), index=False)
    print(comp[["compatibility", "p_high", "menu", "stochastic_musd", "plan_for_low_musd"]].to_string(index=False))

    # 5. per-settlement first-stage choice at p = 0.25 (for the map)
    acts, best = choice[(0.25, "with swarm")]
    m = meta.copy()
    m["first_stage"] = np.array(acts)[best]
    m["first_stage_without_swarm"] = np.array(choice[(0.25, "without swarm")][0])[choice[(0.25, "without swarm")][1]]
    m.round(4).to_csv(os.path.join(out, "first_stage_choice_p25.csv"), index=False)

    # 6. robustness of the headline numbers to timing, discounting and the capital share
    def headline(label):
        r, _, _ = evaluate(d, meta, SWARM, chi, [0.25, 0.5])
        rows = []
        for p in (0.25, 0.5):
            wo = r[(r.menu == "without swarm") & (r.p_high == p)].iloc[0]
            w = r[(r.menu == "with swarm") & (r.p_high == p)].iloc[0]
            rows.append(dict(variant=label, p_high=p, build_for_high_musd=wo.plan_for_high_musd,
                             adaptive_musd=wo.plan_for_low_musd, stochastic_musd=wo.stochastic_musd,
                             early_commitment_factor=wo.plan_for_high_musd / wo.plan_for_low_musd,
                             adaptive_gap_pct=100 * (wo.plan_for_low_musd / wo.stochastic_musd - 1),
                             swarm_saving_pct=100 * (1 - w.stochastic_musd / wo.stochastic_musd)))
        return rows

    rob = headline("central (5-year first stage, 8 %, capital shares 0.85 / 0.75)")
    base = (R, T1, W1, W2, dict(CAP_SHARE))
    for label, r_, t1, cs in (("first stage 3 years", 0.08, 3, None), ("first stage 8 years", 0.08, 8, None),
                              ("discount rate 5 %", 0.05, 5, None), ("discount rate 12 %", 0.12, 5, None),
                              ("capital shares 0.70 / 0.60", 0.08, 5, {"SA": 0.70, "MG": 0.60, "SW": 0.60}),
                              ("capital shares 0.95 / 0.90", 0.08, 5, {"SA": 0.95, "MG": 0.90, "SW": 0.90})):
        f = lambda a, b: sum((1 + r_) ** -t for t in range(a, b + 1))
        W1, W2 = f(1, t1) / f(1, T), f(t1 + 1, T) / f(1, T)
        CAP_SHARE.update(cs or base[4])
        rob += headline(label)
        CAP_SHARE.update(base[4])
    R, T1, W1, W2 = base[:4]
    rob = pd.DataFrame(rob)
    rob.round(3).to_csv(os.path.join(out, "robustness.csv"), index=False)
    print(rob.to_string(index=False))
