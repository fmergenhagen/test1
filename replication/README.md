# Swarm-grid replication (Ouanes et al. 2026, Energy Economics 163, 109598)

Julia/JuMP re-implementation of the paper's planner LP and the two equilibrium cases.

## Run
    julia --project=.. -e 'using Pkg; Pkg.instantiate()'
    python make_inputs.py            # writes data/profiles.csv (needs numpy, pandas)
    julia --project=.. run_scenarios.jl
    julia --project=.. breakeven.jl

Tested with Julia 1.13, JuMP + HiGHS.

## Files
- `SwarmGrid.jl`      model (eqs. 9-20), prices from duals, SDI / PDI / BHI indexes
- `run_scenarios.jl`  scenarios 1, 2, 3, 4a, 4b, 4c and comparison with Tables 5 and 6
- `breakeven.jl`      how much interconnection cost the savings can carry
- `make_inputs.py`    synthetic 15-minute load and solar profiles
- `results/`          output tables from the run in this session

## What is and is not replicated
- Inputs are synthetic stand-ins. The paper's RAMP load files and PVGIS solar profile are
  not published; profiles here are calibrated to Figs. 3-4 and to the weekly demand implied
  by Table 6 (43.2 / 29.2 / 21.5 kWh). Replace `data/profiles.csv` to use real data.
- 15-minute resolution is inferred (Table 5 matches the paper's "15-minute" sharing figure).
- Perfect competition and Cournot are solved as the LP plus duals, not with an MCP solver.
  With fixed demand the paper's MCPs are the LP's optimality conditions, and the Cournot
  price reduces to alpha - beta * D. Price-responsive demand will need PATHSolver.jl.
- `profit_paper_convention` prices internal trade at half the system marginal value
  (conditions 26-27 with p_micro = lambda_micro); `profit_consistent_price` uses the full value.
- The line cost in `breakeven.jl` (5000 EUR/km, 20 years, 10 %) is an assumption.

## Findings
- Scenario 4 totals: planner profit 182.0 (paper 180.9), Cournot profit 86.6 (85.8), energy
  shared 40.6 kWh/week (41.9). Capacities and cost are lower than in the paper (PV 3.9 vs
  5.8 kWp, cost 5.8 vs 7.1 EUR/week) because the inputs are stand-ins.
- Individual profits under perfect competition (+1.05, +0.62, -1.67; paper +1.23, +0.84,
  -2.07) appear only under the half-price convention. At the full marginal value each
  nanogrid earns zero. The paper's reported prices (0.214 vs 0.428 EUR/kWh) differ by the
  same factor of two. Worth raising with the authors.
- Cost saving from interconnection without budget limits: 0.4 % (similar households) and
  5.6 % (mixed loads), about EUR 0.35 per week for three nanogrids.
