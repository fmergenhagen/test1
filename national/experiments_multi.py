"""
Experiments with the multi-stage model (multi_stage.py). Writes results/multi_*.csv.

usage: python multi_stage.py <folder with the OnSSET output folders> [block ...]
blocks: costs central frictions breakeven swarm compat paths robust check   (default: all)
"""
import os
import sys
import time

import numpy as np
import pandas as pd

import multi_stage as ms

OUT = os.path.join(ms.HERE, "results")
MENUS = {"without swarm": ["SA", "MG"], "with swarm": ["SA", "MG", "SW"]}
FRICTIONS = {"none": dict(eps=0.0, lag=0),              # the frictionless benchmark of two_stage.py
             "moderate": dict(eps=0.25, lag=1),         # ASSUMED: added capacity 25 % dearer, one year to upgrade
             "strong": dict(eps=0.50, lag=2)}           # ASSUMED: 50 % dearer, two years
GS = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]                   # probability per five-year stage that demand rises


def main(root, blocks=None):
    blocks = blocks or ["costs", "central", "frictions", "breakeven", "swarm", "compat", "paths", "robust", "check"]
    data = ms.load(root)
    pop, E, urban = data["pop"], data["E"], data["urban"]
    A = ms.technology_costs(data)
    nD = E.shape[0]
    pd.set_option("display.width", 250, "display.max_columns", 40, "display.float_format", lambda x: f"{x:,.3f}")
    print(f"domain: {len(pop):,} settlements, {pop.sum()/1e6:.2f} M people; states {list(data['states'])}")

    def run(menu, g, jump=0.3, costs=A, **kw):
        res, paths, extra = ms.evaluate(costs, E, pop, MENUS[menu], ms.growth_matrix(nD, g, jump), **kw)
        return res, paths, extra

    def save(rows, name, show=None):
        df = pd.DataFrame(rows)
        df.round(4).to_csv(os.path.join(OUT, name), index=False)
        print(f"\n== {name}")
        print((df[show] if show else df).to_string(index=False))
        return df

    t0 = time.time()
    if "costs" in blocks:
        rows = []
        for i, d in enumerate(data["states"]):
            cheapest = np.argmin(np.vstack([A[k][i] for k in ("SA", "MG", "SW")]), axis=0)
            cheapest2 = np.argmin(np.vstack([A[k][i] for k in ("SA", "MG")]), axis=0)
            parts = np.array([data["gen"][i].sum(), (data["line_unit"][i] * ms.LV_MG).sum(), (data["fixed_unit"][i] * ms.F_MG).sum()])
            rows.append(dict(state=int(d), kwh_per_household_rural=E[i][~urban].sum() / data["hh"][~urban].sum(),
                             kwh_per_household_urban=E[i][urban].sum() / data["hh"][urban].sum(),
                             **{f"usd_per_person_{k}": A[k][i].sum() / pop.sum() for k in ("SA", "MG", "SW")},
                             **{f"cheapest_{k}_mpeople": pop[cheapest == j].sum() / 1e6 for j, k in enumerate(("SA", "MG", "SW"))},
                             cheapest_SA_no_swarm_mpeople=pop[cheapest2 == 0].sum() / 1e6,
                             **dict(zip(("mg_share_generation", "mg_share_lines", "mg_share_fixed"), parts / parts.sum())),
                             negative_generation_residual_share=float((data["gen"][i] < 0).mean()),
                             mg_is_pv_share_people=pop[data["mg_is_pv"][i]].sum() / pop.sum()))
        rows[-1]["note"] = f"grid would reach {pop[data['grid_at_top']].sum()/1e6:.2f} M of these people in the state-4 run"
        save(rows, "multi_costs.csv")

    if "central" in blocks:
        rows, firsts = [], {}
        for fr, fk in FRICTIONS.items():
            for g in GS:
                for menu in MENUS:
                    res, _, (pr, first, c) = run(menu, g, **fk)
                    rows.append(dict(frictions=fr, g=g, menu=menu, **res))
                    if g == 0.25 and menu == "with swarm":
                        firsts[fr] = (pr, first)
        df = save(rows, "multi_central.csv", ["frictions", "g", "menu", "target_musd", "myopic_musd", "stochastic_musd",
                                              "perfect_musd", "target_over_myopic", "myopic_gap_pct", "evpi_pct",
                                              "start_SA", "start_MG", "start_SW", "start_oversized"])
        m = pd.DataFrame({"x": data["x"], "y": data["y"], "pop": pop})
        for fr, (pr, first) in firsts.items():
            m[f"first_stage_{fr}"] = [f"{pr.menu[pr.assets[a][0]]}{pr.assets[a][1] + 1}" for a in first]
        m.round(4).to_csv(os.path.join(OUT, "multi_first_stage_g25.csv"), index=False)      # large, not committed
        print(f"   [{time.time()-t0:.0f} s]")

    if "frictions" in blocks:
        rows = []
        for g in (0.25, 0.5):
            for eps in (0.0, 0.25, 0.5, 1.0):
                for lag in (0, 1, 2, 3):
                    res, _, _ = run("without swarm", g, eps=eps, lag=lag, perfect=False)
                    rows.append(dict(g=g, eps=eps, lag=lag, **res))
        df = save(rows, "multi_frictions.csv", ["g", "eps", "lag", "target_musd", "myopic_musd", "stochastic_musd",
                                                "target_over_myopic", "target_over_stochastic", "myopic_gap_pct",
                                                "start_MG", "start_oversized"])
        print(f"   [{time.time()-t0:.0f} s]")

    if "breakeven" in blocks:
        # The two simple rules do not depend on the value of unserved energy, so their costs are
        # linear in it: two evaluations give the value at which building for a target breaks even
        # with myopic re-planning. The optimum does depend on it; its oversizing share is reported.
        rows = []
        for tgt in (1, 2):
            for g in (0.1, 0.25, 0.5, 0.75):
                for lag in (1, 2):
                    r0, _, _ = run("without swarm", g, eps=0.25, lag=lag, voll=0.0, target=tgt, perfect=False)
                    r1, _, _ = run("without swarm", g, eps=0.25, lag=lag, voll=1.0, target=tgt, perfect=False)
                    gap0 = r0["target_musd"] - r0["myopic_musd"]
                    slope = (r1["myopic_musd"] - r0["myopic_musd"]) - (r1["target_musd"] - r0["target_musd"])
                    rows.append(dict(target_state=tgt + 1, g=g, lag_years=lag, target_at_zero=r0["target_musd"],
                                     myopic_at_zero=r0["myopic_musd"], breakeven_usd_per_kwh=gap0 / slope if slope > 0 else np.nan))
        save(rows, "multi_breakeven.csv")
        rows = []
        for g in (0.25, 0.5):
            for lag in (1, 2):
                for voll in (0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0):
                    r, _, _ = run("without swarm", g, eps=0.25, lag=lag, voll=voll, perfect=False)
                    r2, _, _ = run("without swarm", g, eps=0.25, lag=lag, voll=voll, target=1, perfect=False)
                    rows.append(dict(g=g, lag_years=lag, voll=voll, stochastic_musd=r["stochastic_musd"],
                                     myopic_over_stochastic=r["myopic_musd"] / r["stochastic_musd"],
                                     target2_over_stochastic=r2["target_musd"] / r["stochastic_musd"],
                                     target3_over_stochastic=r["target_musd"] / r["stochastic_musd"],
                                     start_MG=r["start_MG"], start_oversized=r["start_oversized"],
                                     **{k: v for k, v in r.items() if k.startswith("start_size")}))
        save(rows, "multi_voll.csv")
        print(f"   [{time.time()-t0:.0f} s]")

    if "swarm" in blocks:
        rows = []
        for fr in ("none", "moderate"):
            fk = FRICTIONS[fr]
            for g in (0.25, 0.5):
                base, _, _ = run("without swarm", g, perfect=False, **fk)
                for prem in (0.0, 0.15, 0.30, 0.50, 0.75):
                    for fixed in (0.0, 2500.0, 5000.0):
                        c = ms.technology_costs(data, dict(premium=prem, fixed=fixed, lv=ms.SWARM["lv"]))
                        res, _, _ = run("with swarm", g, costs=c, perfect=False, **fk)
                        rows.append(dict(frictions=fr, g=g, premium=prem, fixed=fixed, modular_swarm=False,
                                         saving_pct=100 * (1 - res["stochastic_musd"] / base["stochastic_musd"]),
                                         saving_musd=base["stochastic_musd"] - res["stochastic_musd"],
                                         start_SW=res["start_SW"], without_musd=base["stochastic_musd"]))
        # a swarm that can grow without the expansion premium while the other technologies cannot
        for fr in ("moderate", "strong"):
            fk = FRICTIONS[fr]
            for g in (0.25, 0.5):
                base, _, _ = run("without swarm", g, perfect=False, **fk)
                for prem in (0.0, 0.15, 0.30, 0.50):
                    c = ms.technology_costs(data, dict(premium=prem, fixed=ms.SWARM["fixed"], lv=ms.SWARM["lv"]))
                    for modular in (False, True):
                        eps = {"SA": fk["eps"], "MG": fk["eps"], "SW": 0.0 if modular else fk["eps"]}
                        res, _, _ = run("with swarm", g, costs=c, perfect=False, eps=eps, lag=fk["lag"])
                        rows.append(dict(frictions=fr, g=g, premium=prem, fixed=ms.SWARM["fixed"], modular_swarm=modular,
                                         saving_pct=100 * (1 - res["stochastic_musd"] / base["stochastic_musd"]),
                                         saving_musd=base["stochastic_musd"] - res["stochastic_musd"],
                                         start_SW=res["start_SW"], without_musd=base["stochastic_musd"]))
        df = save(rows, "multi_swarm.csv")
        print(f"   [{time.time()-t0:.0f} s]")

    if "compat" in blocks:
        chi, rows = ms.CHI, []
        cases = (("central", chi), ("swarm hardware stranded by a mini-grid", {**chi, ("SW", "MG"): 0.0}),
                 ("stand-alone systems not reusable in a swarm", {**chi, ("SA", "SW"): 0.0}),
                 ("stand-alone systems reusable in a mini-grid", {**chi, ("SA", "MG"): 1.0}),
                 ("stand-alone systems half reusable in a mini-grid", {**chi, ("SA", "MG"): 0.5}))
        for fr in ("none", "moderate"):
            for g in (0.25, 0.5):
                for name, c in cases:
                    for menu in MENUS:
                        res, _, _ = run(menu, g, chi=c, perfect=False, **FRICTIONS[fr])
                        rows.append(dict(frictions=fr, g=g, compatibility=name, menu=menu, **res))
        save(rows, "multi_compat.csv", ["frictions", "g", "compatibility", "menu", "stochastic_musd", "myopic_musd",
                                        "start_SA", "start_MG", "start_oversized"])
        print(f"   [{time.time()-t0:.0f} s]")

    if "paths" in blocks:
        tabs = []
        for fr in FRICTIONS:
            for g in (0.25, 0.5):
                for menu in MENUS:
                    _, paths, _ = run(menu, g, **FRICTIONS[fr])
                    paths.insert(0, "menu", menu); paths.insert(0, "g", g); paths.insert(0, "frictions", fr)
                    tabs.append(paths)
        df = pd.concat(tabs, ignore_index=True)
        df.round(4).to_csv(os.path.join(OUT, "multi_paths.csv"), index=False)
        print("\n== multi_paths.csv (moderate frictions, g = 0.25, without swarm)")
        print(df[(df.frictions == "moderate") & (df.g == 0.25) & (df.menu == "without swarm")].to_string(index=False))

    if "robust" in blocks:
        rows = []

        def add(label, fr="moderate", costs=A, E_=E, pop_=pop, g_adj=None, jump=0.3, **kw):
            for g in (0.25, 0.5):
                P = ms.growth_matrix(nD, g_adj(g) if g_adj else g, jump)
                r = {m: ms.evaluate(costs, E_, pop_, MENUS[m], P, **{**FRICTIONS[fr], **kw})[0] for m in MENUS}
                wo, w = r["without swarm"], r["with swarm"]
                rows.append(dict(variant=label, frictions=fr, g=g, target_musd=wo["target_musd"], myopic_musd=wo["myopic_musd"],
                                 stochastic_musd=wo["stochastic_musd"], target_over_myopic=wo["target_over_myopic"],
                                 target_over_stochastic=wo["target_over_stochastic"], myopic_gap_pct=wo["myopic_gap_pct"],
                                 evpi_pct=wo.get("evpi_pct", np.nan), start_oversized=wo["start_oversized"],
                                 swarm_saving_pct=100 * (1 - w["stochastic_musd"] / wo["stochastic_musd"])))

        add("central: three 5-year stages, 8 %, jump share 0.3")
        add("no frictions", fr="none")
        add("strong frictions", fr="strong")
        add("demand rises one state at a time (jump share 0)", jump=0.0)
        add("jump share 0.6", jump=0.6)
        add("discount rate 5 %", rate=0.05)
        add("discount rate 12 %", rate=0.12)
        add("capital shares 0.70 / 0.60", cap={"SA": 0.70, "MG": 0.60, "SW": 0.60})
        add("capital shares 0.95 / 0.90", cap={"SA": 0.95, "MG": 0.90, "SW": 0.90})
        add("unserved energy valued at USD 0.25 per kWh", voll=0.25)
        add("unserved energy valued at USD 1.00 per kWh", voll=1.00)
        add("no cost floor for oversized systems", floor=False)
        add("no expansion premium, one-year lag", eps=0.0)
        add("planning target is state 2", target=1)
        rur = ~urban
        add("rural settlements only", costs={k: v[:, rur] for k, v in A.items()}, E_=E[:, rur], pop_=pop[rur])
        add("five 3-year stages, same hazard", stages=(3, 3, 3, 3, 3), g_adj=lambda g: 1 - (1 - g) ** 0.6, perfect=False)
        save(rows, "multi_robustness.csv")
        print(f"   [{time.time()-t0:.0f} s]")

    if "check" in blocks:
        # two stages and two states: the published two-stage numbers, with and without the cost floor
        st = list(data["states"]); use = [st.index(1), st.index(3)]
        rows = []
        for p in (0.25, 0.5, 1.0):
            for floor in (False, True):
                res, _, _ = ms.evaluate(A, E, pop, MENUS["without swarm"], np.array([[1 - p, p], [0, 1]]), target=1,
                                        stages=(5, 10), use=use, floor=floor)
                rows.append(dict(p_high=p, cost_floor=floor, **res))
        save(rows, "multi_two_stage_check.csv", ["p_high", "cost_floor", "target_musd", "myopic_musd", "stochastic_musd",
                                                 "perfect_musd", "target_over_myopic", "myopic_gap_pct"])
    print(f"\ndone in {time.time()-t0:.0f} s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
