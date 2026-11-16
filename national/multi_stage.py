"""
Multi-stage technology choice under demand uncertainty, settlement by settlement.

Generalises two_stage.py: several stages, several demand states that follow a Markov
chain, and two adaptation frictions. Every settlement is an independent small dynamic
program; all of them are solved at once with array operations.

Demand states (OnSSET targets, rural / urban tier):
    1 = R1 / U3 (the platform's low target)     2 = R2 / U3
    3 = R3 / U4 (the platform's high target)    4 = R4 / U4

Asset: a technology k and a size s (sized for demand state s). At every stage the planner
sees current demand d and picks an asset with size >= d. Costs, all as annual flows:

    operating     max( A[k, d],  cap_k * A[k, s] + (1 - cap_k) * A[k, s] * E[d] / E[s] )
                  (capital of the installed size plus running cost of the energy served; an
                  oversized system never costs less than the right-sized one)
    switch k->j   the old capital that cannot be reused stays on the books:
                  (1 - chi[k, j]) * cap_k * A[k, s]            for the rest of the horizon
    expand k      added capacity costs (1 + eps_k) times its greenfield cost:
                  eps_k * cap_k * (A[k, s'] - A[k, s])          for the rest of the horizon
    upgrade lag   if demand exceeds the installed size, the extra energy is not served for
                  `lag` years and valued at `voll` USD per kWh

A[k, s] is OnSSET's levelised cost at demand state s times annual energy at that state.
With eps = 0, lag = 0, floor=False, two stages and two states this is exactly two_stage.py.

Planning rules compared:
    target      build the technology that is cheapest at the target state, sized for it,
                from day one (what a least-cost plan for the target year prescribes)
    myopic      at every stage choose the cheapest way to serve current demand, taking the
                installed system as given and assuming demand stays where it is
    stochastic  the optimum of the dynamic program
    perfect     the optimum for each demand path, known in advance

usage: python multi_stage.py <folder with the OnSSET output folders>
"""
import itertools
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
R, HORIZON = 0.08, 15
RUNS = {1: ("out_low", "mg-2-0_0_0.csv"), 2: ("out_t2", "mg-2-2_0_0.csv"),
        3: ("out_high", "mg-2-1_0_0.csv"), 4: ("out_t4", "mg-2-3_0_0.csv")}
F_MG, F_RUN = 10000.0, 2500.0          # mini-grid fixed cost in OnSSET; value in the proxy run
LV_MG, LV_RUN = 4250.0, 2000.0         # low-voltage line cost per km in OnSSET; value in the proxy run
SWARM = dict(premium=0.30, fixed=2500.0, lv=2000.0)      # ASSUMED central case for the swarm option
CAP_SHARE = {"SA": 0.85, "MG": 0.75, "SW": 0.75}         # ASSUMED capital share of levelised cost
CHI = {("SA", "SW"): 1.0, ("SW", "MG"): 1.0, ("SA", "MG"): 0.0,   # ASSUMED share of capital reusable
       ("MG", "SW"): 1.0, ("SW", "SA"): 0.0, ("MG", "SA"): 0.0}   # after a change of technology
VOLL = 0.50                            # ASSUMED value of energy not served during an upgrade, USD/kWh
COLS = ["Pop2025", "ElecStart", "FinalElecCode2030", "IsUrban", "EnergyPerSettlement2025", "NumPeoplePerHH",
        "SA_PV2025", "MG_PV_Hybrid2025", "MG_Hydro2025", "MG_Wind_Hybrid2025", "X_deg", "Y_deg"]


def load(root, states=(1, 2, 3, 4)):
    """Annual cost components per settlement and demand state, cached in <root>/multi_stage_cache.npz."""
    cache = os.path.join(root, "multi_stage_cache.npz")
    if os.path.exists(cache):
        z = np.load(cache)
        if list(z["states"]) == list(states):
            return {k: z[k] for k in z.files}
    base = {d: pd.read_csv(os.path.join(root, RUNS[d][0], RUNS[d][1]), usecols=COLS) for d in states}
    var = lambda d, tag: pd.read_csv(os.path.join(root, RUNS[d][0] + tag, RUNS[d][1]),
                                     usecols=["MG_PV_Hybrid2025"]).MG_PV_Hybrid2025
    lo, hi = base[1], base[3]
    assert all(np.allclose(base[d].X_deg, lo.X_deg) for d in states), "runs are not row-aligned"
    dom = ((lo.ElecStart == 0) & ~lo.FinalElecCode2030.isin([1, 2]) & ~hi.FinalElecCode2030.isin([1, 2])).values
    out = {k: [] for k in ("E", "SA", "MG", "gen", "fixed_unit", "line_unit", "mg_is_pv")}
    for d in states:
        g = base[d][dom]
        e = g.EnergyPerSettlement2025.values
        mgs = g[["MG_PV_Hybrid2025", "MG_Hydro2025", "MG_Wind_Hybrid2025"]].values
        pvb = g.MG_PV_Hybrid2025.values * e                          # F = 10,000, LV = 4,250
        f_run = var(d, "_F2500")[dom].values * e                     # F = 2,500,  LV = 4,250
        lv_run = var(d, "_F2500_LV2000")[dom].values * e             # F = 2,500,  LV = 2,000
        fixed_unit = (pvb - f_run) / (F_MG - F_RUN)                  # USD per year per USD of fixed cost
        line_unit = (f_run - lv_run) / (LV_MG - LV_RUN)              # USD per year per USD/km of line cost
        out["E"].append(e); out["SA"].append(g.SA_PV2025.values * e); out["MG"].append(mgs.min(axis=1) * e)
        out["gen"].append(pvb - fixed_unit * F_MG - line_unit * LV_MG)
        out["fixed_unit"].append(fixed_unit); out["line_unit"].append(line_unit)
        out["mg_is_pv"].append(mgs.argmin(axis=1) == 0)
    out = {k: np.vstack(v) for k, v in out.items()}
    out.update(states=np.array(states), pop=lo.Pop2025.values[dom], urban=(lo.IsUrban.values[dom] == 2),
               hh=(lo.Pop2025 / lo.NumPeoplePerHH).values[dom],
               x=lo.X_deg.values[dom], y=lo.Y_deg.values[dom],
               grid_at_top=base[states[-1]].FinalElecCode2030.isin([1, 2]).values[dom])
    np.savez(cache, **out)
    return out


def technology_costs(data, swarm=SWARM):
    """A[k] with shape (states, settlements); the swarm is the mini-grid with a generation premium,
    a smaller fixed cost and cheaper lines."""
    sw = (1 + swarm["premium"]) * data["gen"] + data["line_unit"] * swarm["lv"] + data["fixed_unit"] * swarm["fixed"]
    return {"SA": data["SA"], "MG": data["MG"], "SW": sw}


def growth_matrix(n, g, jump=0.3):
    """Demand stays with probability 1 - g, rises one state with g (1 - jump), two states with g jump."""
    P = np.zeros((n, n))
    for i in range(n):
        P[i, i] += 1 - g
        P[i, min(i + 1, n - 1)] += g * (1 - jump)
        P[i, min(i + 2, n - 1)] += g * jump
    return P


class Problem:
    """All settlements at once. `use` selects the demand states (rows of the cost arrays) in play."""

    def __init__(self, A, E, menu, P, stages=(5, 5, 5), use=None, chi=CHI, cap=CAP_SHARE, eps=0.0, lag=0,
                 voll=VOLL, rate=R, floor=True):
        use = list(range(E.shape[0])) if use is None else list(use)
        self.menu, self.nD, self.N, self.T = list(menu), len(use), E.shape[1], len(stages)
        self.E = E[use]
        self.P = np.asarray(P, float)
        assert self.P.shape == (self.nD, self.nD) and np.allclose(self.P.sum(axis=1), 1)
        eps = eps if isinstance(eps, dict) else {k: eps for k in menu}
        pv = lambda a, b: sum((1 + rate) ** -t for t in range(a, b + 1))
        tot, starts = pv(1, sum(stages)), np.concatenate([[0], np.cumsum(stages)[:-1]])
        self.w = np.array([pv(s + 1, s + n) / tot for s, n in zip(starts, stages)])      # stage weights, sum to 1
        self.wplus = np.cumsum(self.w[::-1])[::-1]                                        # this and all later stages
        self.lagw = np.array([pv(s + 1, s + min(lag, n)) / tot if lag else 0.0 for s, n in zip(starts, stages)])
        self.voll, self.floor = voll, floor
        # assets: (technology index, size index)
        self.assets = [(k, s) for k in range(len(menu)) for s in range(self.nD)]
        self.nA = len(self.assets)
        full = np.stack([A[k][use] for k in menu])                                        # (K, D, N) annual cost at own size
        self.full = full
        self.cap = np.stack([cap[menu[k]] * full[k, s] for k, s in self.assets])          # capital part, (nA, N)
        self.run = np.stack([(1 - cap[menu[k]]) * full[k, s] / self.E[s] for k, s in self.assets])  # per kWh served
        self.chi = np.array([[1.0 if i == j else chi.get((a, b), 0.0) for j, b in enumerate(menu)]
                             for i, a in enumerate(menu)])
        self.eps = np.array([eps[k] for k in menu])

    # ---- cost pieces -------------------------------------------------------------------------
    def op(self, a, d):
        c = self.cap[a] + self.run[a] * self.E[d]
        return np.maximum(c, self.full[self.assets[a][0], d]) if self.floor else c

    def trans(self, a, b):
        """Annual flow, paid from now to the horizon, for moving from asset a to asset b."""
        if a is None or a == b:
            return 0.0
        (k, s), (j, s2) = self.assets[a], self.assets[b]
        if k == j:
            return self.eps[k] * np.maximum(self.cap[b] - self.cap[a], 0.0)
        return (1 - self.chi[k, j]) * self.cap[a]

    def lag_pen(self, t, a, d):
        if a is None or t == 0 or self.lagw[t] == 0.0 or self.assets[a][1] >= d:
            return 0.0
        return self.lagw[t] * self.voll * (self.E[d] - self.E[self.assets[a][1]])

    def feasible(self, a, d):
        out = []
        for b, (j, s2) in enumerate(self.assets):
            if s2 < d:
                continue
            if a is not None and self.assets[a][0] == j and s2 < self.assets[a][1]:
                continue                                    # no downsizing within a technology
            out.append(b)
        return out

    def step_costs(self, t, a, d, cont=None):
        """Cost of every feasible next asset b from (stage t, previous asset a, demand d):
        transition + this stage's operation (+ continuation value cont[b] if given)."""
        fb = self.feasible(a, d)
        c = np.empty((len(fb), self.N))
        for i, b in enumerate(fb):
            c[i] = self.wplus[t] * self.trans(a, b) + self.w[t] * self.op(b, d)
            if cont is not None:
                c[i] += cont[b]
        return fb, c + self.lag_pen(t, a, d)

    # ---- demand paths ------------------------------------------------------------------------
    def paths(self, d0=0):
        out = []
        for seq in itertools.product(range(self.nD), repeat=self.T - 1):
            path, pr = (d0,) + seq, 1.0
            for u, v in zip(path[:-1], path[1:]):
                pr *= self.P[u, v]
            if pr > 0:
                out.append((path, pr))
        return out

    # ---- stochastic optimum ------------------------------------------------------------------
    def solve(self, d0=0):
        """Backward recursion. Returns expected cost per settlement and the policy
        pol[t][(d, a)] = index of the chosen asset per settlement."""
        V_next, pol = None, [dict() for _ in range(self.T)]
        reach = [np.linalg.matrix_power(self.P, t)[d0] > 0 for t in range(self.T)]
        for t in range(self.T - 1, -1, -1):
            V = {}
            for d in np.flatnonzero(reach[t]):
                cont = None
                if V_next is not None:                      # expected value of ending the stage with asset b
                    cont = np.zeros((self.nA, self.N))
                    for d2 in np.flatnonzero(self.P[d] > 0):
                        cont += self.P[d, d2] * V_next[d2]
                Vd = np.full((self.nA, self.N), np.inf)
                for a in ([None] if t == 0 else range(self.nA)):
                    fb, c = self.step_costs(t, a, d, cont)
                    best = c.argmin(axis=0)
                    val = c[best, np.arange(self.N)]
                    pol[t][(d, a)] = np.asarray(fb, dtype=np.int8)[best]
                    if t == 0:
                        return val, pol
                    Vd[a] = val
                V[d] = Vd
            V_next = V
        raise RuntimeError

    # ---- rules -------------------------------------------------------------------------------
    def rule_stochastic(self, pol):
        return lambda t, d, a: pol[t][(d, a)]

    def rule_myopic(self):
        def f(t, d, a):
            # demand is assumed to stay at d, so compare annual flows over the rest of the horizon
            fb = self.feasible(a, d)
            flows = np.stack([self.trans(a, b) + self.op(b, d) for b in fb])
            return np.asarray(fb, dtype=np.int8)[flows.argmin(axis=0)]
        return f

    def rule_target(self, target):
        """Build the technology that is cheapest at the target state, sized for it; if demand ever
        exceeds the installed size, re-plan myopically."""
        k_star = self.full[:, target, :].argmin(axis=0)
        first = np.array([self.assets.index((k, target)) for k in range(len(self.menu))], dtype=np.int8)[k_star]
        myopic = self.rule_myopic()

        def f(t, d, a):
            if t == 0:
                return first
            if self.assets[a][1] >= d:
                return np.full(self.N, a, dtype=np.int8)
            return myopic(t, d, a)
        return f

    def simulate(self, rule, d0=0):
        """Follow a rule down the demand tree. Returns expected cost per settlement, national
        cost per demand path as (path, probability, cost), and the first-stage asset."""
        exp, by_path, first, idx = np.zeros(self.N), [], [], np.arange(self.N)

        def go(t, d, cur, cost, pr, path):
            if t == 0:
                nxt = rule(0, d, None)
                fb, c = self.step_costs(0, None, d)
                cost = cost + c[np.searchsorted(fb, nxt), idx]
                first.append(nxt)
            else:
                nxt, cost = np.empty(self.N, dtype=np.int8), cost.copy()
                for a in np.unique(cur):
                    m = cur == a
                    choice = rule(t, d, int(a))[m]
                    fb, c = self.step_costs(t, int(a), d)
                    nxt[m] = choice
                    cost[m] += c[np.searchsorted(fb, choice), idx[m]]
            if t == self.T - 1:
                exp[:] += pr * cost
                by_path.append((path, pr, cost.sum()))
                return
            for d2 in np.flatnonzero(self.P[d] > 0):
                go(t + 1, int(d2), nxt, cost, pr * self.P[d, d2], path + (int(d2),))

        go(0, d0, None, np.zeros(self.N), 1.0, (d0,))
        return exp, by_path, first[0]

    def perfect(self, d0=0):
        """Best plan for each demand path when the path is known in advance."""
        exp, by_path = np.zeros(self.N), []
        for path, pr in self.paths(d0):
            V_next = None
            for t in range(self.T - 1, -1, -1):
                d = path[t]
                if t == 0:
                    _, c = self.step_costs(0, None, d, V_next)
                    val = c.min(axis=0)
                else:
                    V = np.empty((self.nA, self.N))
                    for a in range(self.nA):
                        _, c = self.step_costs(t, a, d, V_next)
                        V[a] = c.min(axis=0)
                    V_next = V
            exp += pr * val
            by_path.append((path, pr, val.sum()))
        return exp, by_path

    def describe(self, first, pop):
        """Share of people by first-stage technology and by whether it is sized above current demand."""
        k = np.array([self.assets[a][0] for a in range(self.nA)])[first]
        s = np.array([self.assets[a][1] for a in range(self.nA)])[first]
        out = {f"start_{self.menu[i]}": pop[k == i].sum() / pop.sum() for i in range(len(self.menu))}
        out["start_oversized"] = pop[s > 0].sum() / pop.sum()
        out.update({f"start_size{j + 1}": pop[s == j].sum() / pop.sum() for j in range(self.nD)})
        return out


def evaluate(A, E, pop, menu, P, target=2, perfect=True, **kw):
    """One configuration: the four rules in USD million a year, first-stage shares, and the
    national cost of every rule along every demand path."""
    pr = Problem(A, E, menu, P, **kw)
    v_opt, pol = pr.solve()
    c_opt, path_opt, first = pr.simulate(pr.rule_stochastic(pol))
    assert np.allclose(c_opt, v_opt), "simulation of the optimal policy does not match the recursion"
    c_my, path_my, _ = pr.simulate(pr.rule_myopic())
    c_tg, path_tg, _ = pr.simulate(pr.rule_target(min(target, pr.nD - 1)))
    res = dict(target_musd=c_tg.sum() / 1e6, myopic_musd=c_my.sum() / 1e6, stochastic_musd=c_opt.sum() / 1e6)
    label = lambda p: "-".join(str(d + 1) for d in p)
    paths = pd.DataFrame({"path": [label(p) for p, _, _ in path_opt], "prob": [q for _, q, _ in path_opt]})
    for name, tab in (("target", path_tg), ("myopic", path_my), ("stochastic", path_opt)):
        paths[name] = paths.path.map({label(p): c / 1e6 for p, _, c in tab})
    if perfect:
        c_pi, path_pi = pr.perfect()
        res["perfect_musd"] = c_pi.sum() / 1e6
        res["evpi_pct"] = 100 * (1 - res["perfect_musd"] / res["stochastic_musd"])
        paths["perfect"] = paths.path.map({label(p): c / 1e6 for p, _, c in path_pi})
    res["target_over_myopic"] = res["target_musd"] / res["myopic_musd"]
    res["target_over_stochastic"] = res["target_musd"] / res["stochastic_musd"]
    res["myopic_gap_pct"] = 100 * (res["myopic_musd"] / res["stochastic_musd"] - 1)
    res.update(pr.describe(first, pop))
    return res, paths, (pr, first, c_opt)


if __name__ == "__main__":
    import experiments_multi
    experiments_multi.main(sys.argv[1], sys.argv[2:])
