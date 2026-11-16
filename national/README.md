# National two-stage analysis: technology choice under demand uncertainty

Settlement-level decision model on top of the OnSSET Madagascar runs. It asks what a
least-cost plan should build now when rural demand may stay at Tier 1 or rise to Tier 3.
The write-up is in [`../paper/main.pdf`](../paper/main.pdf).

## Files

| File | What it does |
|---|---|
| `two_stage.py` | Loads six OnSSET result files, splits mini-grid cost into generation, lines and fixed cost, builds the swarm-grid proxy, solves the two-stage problem for every settlement, writes `results/` |
| `plot_cost_vs_p.py` | Figure 2 of the paper |
| `onsset_env_overrides.patch` | Two-line change to `gep_onsset` so the mini-grid fixed cost and the low-voltage line cost can be set from the environment |
| `results/` | Summary tables. The per-settlement file (12 MB) is not committed; `two_stage.py` regenerates it |

## Reproduce

1. Run the two baseline scenarios as described in `../onsset_madagascar/README.md`
   (outputs `out_low/mg-2-0_0_0.csv`, `out_high/mg-2-1_0_0.csv`).
2. Apply `onsset_env_overrides.patch` to `gep_onsset` and repeat both scenarios twice:

       MG_FIXED_COST=2500                    -> out_low_F2500, out_high_F2500
       MG_FIXED_COST=2500 LV_LINE_COST=2000  -> out_low_F2500_LV2000, out_high_F2500_LV2000

   `LV_LINE_COST` changes the default for every technology in that run. Only the
   `MG_PV_Hybrid2025` column of these runs is used, and settlements that the grid reaches in
   either baseline are outside the analysis.
3. Run

       python3 two_stage.py out_low/mg-2-0_0_0.csv out_high/mg-2-1_0_0.csv \
           out_low_F2500/mg-2-0_0_0.csv out_high_F2500/mg-2-1_0_0.csv \
           out_low_F2500_LV2000/mg-2-0_0_0.csv out_high_F2500_LV2000/mg-2-1_0_0.csv
       python3 plot_cost_vs_p.py

Each OnSSET run takes about seven minutes; the two-stage model takes under a minute.

## What is assumed

- Stage lengths (5 and 10 years) and the 8 % discount rate.
- Capital shares of levelised cost: 0.85 stand-alone solar, 0.75 mini-grid and swarm grid.
- Swarm grid: 30 % generation premium, USD 2,500 fixed cost, USD 2,000 per km of line.
  None of these comes from field data.
- Compatibility: stand-alone systems are stranded by a mini-grid but reusable in a swarm;
  swarm hardware is reusable in a mini-grid.
- Adaptation is immediate and costs nothing beyond stranded capital.

`results/robustness.csv` and `results/swarm_sensitivity.csv` vary the first four.
