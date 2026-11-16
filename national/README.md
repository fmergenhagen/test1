# National analysis: when to build ahead of demand

Settlement-level decision models on top of the OnSSET Madagascar runs. They ask what a
least-cost plan should build now, and how large, when rural demand may stay at Tier 1 or
rise. The write-up is [`../paper/main.pdf`](../paper/main.pdf).

## Files

| File | What it does |
|---|---|
| `multi_stage.py` | The model of the paper: several stages, four demand states on a Markov chain, technology and size, stranded capital, expansion premium, upgrade lag. One dynamic programme per settlement, all solved at once with arrays. Four planning rules |
| `experiments_multi.py` | All experiments of the paper; writes `results/multi_*.csv` |
| `test_multi_stage.py` | Checks: against an independent scalar recursion, ordering of the rules, and exact reproduction of `two_stage.py` as a special case |
| `plot_multi.py` | Figures 2 to 4 of the paper |
| `two_stage.py` | First version: two stages, two demand states, no frictions. Kept as the reference for the special case |
| `plot_cost_vs_p.py` | Figure of the two-stage version (`results/fig_two_stage_cost_vs_p.png`) |
| `make_state_specs.py` | Specs files for the two extra demand states |
| `onsset_env_overrides.patch` | Two-line change to `gep_onsset` so the mini-grid fixed cost and the low-voltage line cost can be set from the environment |
| `results/` | Result tables. Per-settlement files are not committed; the scripts regenerate them |

## Reproduce

1. Run the two baseline scenarios as described in `../onsset_madagascar/README.md`
   (folders `out_low`, `out_high`).
2. `python make_state_specs.py mg-specs-low.xlsx .` and run OnSSET with `mg-specs-t2.xlsx`
   and `mg-specs-t4.xlsx` (folders `out_t2`, `out_t4`).
3. Apply `onsset_env_overrides.patch` to `gep_onsset` and repeat all four scenarios twice:

       MG_FIXED_COST=2500                    -> out_low_F2500, out_t2_F2500, out_high_F2500, out_t4_F2500
       MG_FIXED_COST=2500 LV_LINE_COST=2000  -> the same names with _F2500_LV2000

   `LV_LINE_COST` changes the default for every technology in that run. Only the
   `MG_PV_Hybrid2025` column of these runs is used, and settlements that the grid reaches in
   either baseline are outside the analysis.
4. With `<data>` the folder that holds the twelve output folders:

       python test_multi_stage.py <data>        # four checks, a few seconds
       python multi_stage.py <data>             # all experiments, about 12 minutes
       python plot_multi.py

   Single blocks: `python multi_stage.py <data> central frictions` (see `experiments_multi.py`).
   The two-stage version runs as before with `python two_stage.py` and six file names.

Each OnSSET run takes five to seven minutes; one configuration of the multi-stage model takes
about two seconds.

## What is assumed

None of these comes from field data. All are varied in the experiments.

- Three stages of five years, 8 % discount rate; demand rises with probability g per stage,
  by two states in 30 % of those cases.
- Capital shares of levelised cost: 0.85 stand-alone solar, 0.75 mini-grid and swarm grid.
- Compatibility: stand-alone systems are stranded by a mini-grid but reusable in a swarm;
  swarm hardware is reusable in a mini-grid.
- Frictions: added capacity costs 25 % more than greenfield, an upgrade takes one year, and
  energy not served during that year is valued at USD 0.50 per kWh.
- Swarm grid: 30 % generation premium, USD 2,500 fixed cost, USD 2,000 per km of line.
- Demand states 2 and 4 keep the urban tier of states 1 and 3.
