"""
Checks for multi_stage.py. No OnSSET data needed for the first three.

1. The array-based recursion equals an independent scalar recursion on the scenario tree
   (random costs, three technologies, four states, both frictions switched on).
2. Ordering: perfect information <= stochastic optimum <= myopic rule and target rule.
3. With no growth and no frictions the myopic rule, the optimum and perfect information all
   equal the cheapest way to serve current demand.
4. With the OnSSET data at hand (folder as first argument): two stages and two states
   reproduce results/two_stage_summary.csv.
"""
import os
import sys

import numpy as np
import pandas as pd

import multi_stage as ms


def reference(A, E, menu, P, stages, chi, cap, eps, lag, voll, rate, i, floor=True):
    """Scalar recursion for settlement i, written from the model description only."""
    K, D, T = len(menu), E.shape[0], len(stages)
    disc = [(1 + rate) ** -y for y in range(1, sum(stages) + 1)]
    b = np.concatenate([[0], np.cumsum(stages)])
    w = [sum(disc[b[t]:b[t + 1]]) / sum(disc) for t in range(T)]
    lagw = [sum(disc[b[t]:b[t] + min(lag, stages[t])]) / sum(disc) for t in range(T)]
    full = lambda k, s: A[menu[k]][s, i]

    def f(t, d, asset):
        best = np.inf
        for k in range(K):
            for s in range(d, D):
                if asset is not None and asset[0] == k and s < asset[1]:
                    continue
                run = cap[menu[k]] * full(k, s) + (1 - cap[menu[k]]) * full(k, s) * E[d, i] / E[s, i]
                c = w[t] * (max(run, full(k, d)) if floor else run)
                if asset is not None:
                    k0, s0 = asset
                    old = cap[menu[k0]] * full(k0, s0)
                    if k0 == k and s > s0:
                        c += sum(w[t:]) * eps * max(cap[menu[k]] * full(k, s) - old, 0.0)
                    if k0 != k:
                        c += sum(w[t:]) * (1 - chi.get((menu[k0], menu[k]), 0.0)) * old
                    if s0 < d:
                        c += lagw[t] * voll * (E[d, i] - E[s0, i])
                if t < T - 1:
                    c += sum(P[d, d2] * f(t + 1, d2, (k, s)) for d2 in range(D) if P[d, d2] > 0)
                best = min(best, c)
        return best

    return f(0, 0, None)


def random_instance(rng, n=30, D=4):
    E = np.cumsum(rng.uniform(50, 400, (D, n)), axis=0)
    A = {k: np.cumsum(rng.uniform(5, 60, (D, n)), axis=0) * rng.uniform(0.6, 1.6, (1, n)) for k in ("SA", "MG", "SW")}
    return A, E


def main():
    rng, ok = np.random.default_rng(7), True
    menu, cap = ["SA", "MG", "SW"], ms.CAP_SHARE

    # 1. vectorised recursion against the scalar reference
    worst = 0.0
    for trial, (eps, lag, g, stages, floor) in enumerate([(0.0, 0, 0.3, (5, 5, 5), True), (0.4, 2, 0.5, (5, 5, 5), False),
                                                          (1.0, 1, 0.7, (3, 5, 7), True), (0.25, 3, 0.2, (4, 4, 4, 3), True)]):
        A, E = random_instance(rng, n=12 if len(stages) > 3 else 30)
        chi = {(a, b): float(rng.uniform()) for a in menu for b in menu if a != b}
        P = ms.growth_matrix(4, g, jump=0.3)
        pr = ms.Problem(A, E, menu, P, stages=stages, chi=chi, eps=eps, lag=lag, floor=floor)
        v, pol = pr.solve()
        ref = np.array([reference(A, E, menu, P, stages, chi, cap, eps, lag, ms.VOLL, ms.R, i, floor)
                        for i in range(E.shape[1])])
        worst = max(worst, np.abs(v / ref - 1).max())
        sim, _, _ = pr.simulate(pr.rule_stochastic(pol))
        worst = max(worst, np.abs(sim / ref - 1).max())
    print(f"1. recursion vs scalar reference, 4 instances: max relative difference {worst:.2e}")
    ok &= worst < 1e-10

    # 2. ordering of the rules
    A, E = random_instance(rng, n=500)
    bad = 0
    for eps, lag, g in [(0.0, 0, 0.25), (0.5, 2, 0.5), (1.0, 3, 0.9)]:
        pr = ms.Problem(A, E, menu, ms.growth_matrix(4, g), eps=eps, lag=lag)
        v, pol = pr.solve()
        my, _, _ = pr.simulate(pr.rule_myopic())
        tg, _, _ = pr.simulate(pr.rule_target(2))
        pi, _ = pr.perfect()
        bad += int((pi > v * (1 + 1e-12)).sum() + (v > my * (1 + 1e-12)).sum() + (v > tg * (1 + 1e-12)).sum())
    print(f"2. perfect <= stochastic <= myopic, target: {bad} violations in 1,500 settlement-cases")
    ok &= bad == 0

    # 3. no growth, no frictions: myopic = stochastic = perfect
    pr = ms.Problem(A, E, menu, ms.growth_matrix(4, 0.0))
    v, pol = pr.solve()
    my, _, _ = pr.simulate(pr.rule_myopic())
    pi, _ = pr.perfect()
    cheapest = np.min([pr.op(a, 0) for a in range(pr.nA)], axis=0)       # any technology, any size
    same = np.allclose(v, my) and np.allclose(v, pi) and np.allclose(v, cheapest)
    print(f"3. no growth, no frictions: myopic = stochastic = perfect = cheapest way to serve current demand: {same}")
    ok &= same

    # 4. two stages, two states against two_stage.py
    if len(sys.argv) > 1:
        data = ms.load(sys.argv[1])
        states = list(data["states"])
        use = [states.index(1), states.index(3)]
        Ad, ref, worst = ms.technology_costs(data), pd.read_csv(os.path.join(ms.HERE, "results", "two_stage_summary.csv")), 0.0
        for p in (0.0, 0.1, 0.25, 0.5, 0.75, 1.0):
            for label, m in (("without swarm", ["SA", "MG"]), ("with swarm", ["SA", "MG", "SW"])):
                res, _, _ = ms.evaluate(Ad, data["E"], data["pop"], m, np.array([[1 - p, p], [0, 1]]), target=1,
                                        stages=(5, 10), use=use, floor=False)
                r = ref[(ref.p_high == p) & (ref.menu == label)].iloc[0]
                for a, b in (("target_musd", "plan_for_high_musd"), ("myopic_musd", "plan_for_low_musd"),
                             ("stochastic_musd", "stochastic_musd"), ("perfect_musd", "perfect_info_musd")):
                    worst = max(worst, abs(res[a] - r[b]))
        print(f"4. two-stage special case vs two_stage_summary.csv: max difference USD {worst:.4f} million")
        ok &= worst < 1e-3
    print("ALL CHECKS PASS" if ok else "CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
