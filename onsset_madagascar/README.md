# Madagascar baseline with GEP-OnSSET

A conventional least-cost electrification run for Madagascar (2020-2030), used as the
benchmark for the swarm work, plus two small scripts on top of the results.

## Inputs (not in the repository)
- `MG-inputs` - calibrated GEP settlement file, 155,275 settlements (about 70 MB)
- `MG-pv.csv`, `MG-wind.csv` - renewables.ninja resource files
- No official specs file was available, so `build_specs.py` creates one. Population,
  urban shares and electrification rates are derived from the settlement file itself.
  Household sizes, grid generation cost (0.1355 USD/kWh), the 96 MW/year generation cap
  and the demand tiers come from the GEP Madagascar scenario description (mg-1, 2019).
  Grid investment cost, grid losses, base-to-peak ratio, maximum extension distance,
  diesel price and the 2025 intermediate target (65 %) are ASSUMED (Sierra Leone
  template values). Replace them when the official specs file is at hand.

## Run
    git clone https://github.com/global-electrification-platform/gep-onsset
    cp -r gep-onsset/gep_onsset code
    sed -i "s#os.path.join(r'..\\\\test_data', #os.path.join(os.environ.get('GEP_RESOURCE_DIR', '.'), #" code/runner.py
    conda create -n onsset -c conda-forge python=3.8 pandas=1.1 numpy=1.19 numba openpyxl xlrd=1.2 scipy

    python build_specs.py MG-inputs data/            # writes cleaned inputs + two specs files
    cp MG-pv.csv data/mg-2-pv.csv; cp MG-wind.csv data/mg-2-wind.csv
    python run_country.py data/mg-specs-low.xlsx  data/mg-inputs-clean.csv data out_low
    python run_country.py data/mg-specs-high.xlsx data/mg-inputs-clean.csv data out_high
    python screen_swarm.py out_low/mg-2-0_0_0.csv
    python affordability.py out_low/mg-2-0_0_0.csv

Each scenario takes about 7 minutes. The pipeline was first validated on the Sierra Leone
sample shipped with gep-onsset, whose published sample output it reproduces exactly.

## Results (see `results/`)

| 2030, million people | Low demand (urban Tier 3, rural Tier 1) | High demand (urban Tier 4, rural Tier 3) |
|---|---|---|
| Grid (existing + new) | 14.7 | 16.3 |
| Mini-grids | 6.3 | 17.2 |
| Stand-alone solar | 14.6 | 2.0 |
| Investment 2020-2030 | USD 3.8 bn | USD 12.2 bn |

- 11.25 million people (32 % of the 2030 population) are assigned stand-alone solar in the
  low scenario and a mini-grid in the high scenario. 39 % of the population change
  technology class between the two scenarios.
- Of the 14.6 million people on stand-alone solar in the low scenario, 12.3 million live
  in settlements with at least 15 households and a nanogrid spacing of at most 150 m
  (median settlement: 33 households, 65 m spacing).

These numbers depend on the assumed parameters above and on the 2019-vintage GEP inputs.
They are a benchmark, not a plan.

## Known limits
- `screen_swarm.py` is descriptive: it counts people in settlements where interconnecting
  nanogrids is geometrically plausible. It does not model the swarm option.
- `affordability.py`: grid rows are not interpretable yet (see comments in the file).
- Settlement area (`GridCellArea`) comes from 100 m population rasters, so spacing is
  approximate.
