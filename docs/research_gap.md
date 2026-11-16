# Swarm electrification: where the research gap is, and a way in

*First pass, 16 November 2026. Based on about 20 targeted searches, the Ouanes et al. (2026)
paper, a Madagascar OnSSET baseline and a prototype model built the same day. This is a
scoping note, not a systematic review. Paywalled full texts were not read; abstracts and
open versions were.*

## 1. The pitch in four sentences

Least-cost electrification plans must choose between stand-alone solar and mini-grids
before anyone knows how much electricity people will use. In Madagascar that choice flips
for about 11 million people depending on the assumed demand level. Swarm grids (nanogrids
that are interconnected step by step and can later be upgraded) are promoted as the
flexible middle path, but that flexibility has been asserted, not measured. The
contribution would be an operations-research model that values it: a multi-stage stochastic
network-design model of the path nanogrid → swarm → mini-grid, with regulation of the
operator on top and a link to national planning.

## 2. Why Madagascar makes the case (own OnSSET runs)

Two standard GEP-OnSSET scenarios for 2030, same inputs, different demand target
(details and caveats in `onsset_madagascar/README.md`):

| 2030, million people | Low demand (rural Tier 1) | High demand (rural Tier 3) |
|---|---|---|
| Grid | 14.7 | 16.3 |
| Mini-grids | 6.3 | 17.2 |
| Stand-alone solar | 14.6 | 2.0 |
| Investment 2020–2030 | USD 3.8 bn | USD 12.2 bn |

- **11.25 million people (32 %)** get stand-alone solar in one scenario and a mini-grid in
  the other. For them the plan is decided by an assumption.
- For that group the implied household bill rises from about **USD 24 to about USD 300–350
  a year**, and the upfront cost from about USD 290 to about USD 2,200.
- **12.3 of the 14.6 million** people assigned stand-alone solar live in settlements with at
  least 15 households and nanogrids on average at most 150 m apart (median: 33 households,
  65 m). Geometrically, these are places where interconnection is possible.

Several parameters of this run are assumed (no official specs file), so read the numbers
as orders of magnitude.

## 3. What already exists

| Strand | Representative work | What it does | What it leaves open |
|---|---|---|---|
| Concept, technology | Groh et al. 2014; Kirchhoff & Strunz 2019 (TU Berlin); Richard et al. 2022 (Nanoé, Madagascar) | Defines swarm electrification, control and stability, field deployment | No planning or investment model |
| Reviews | Sheridan et al. 2023 (RSER); Fuchs et al. 2024 | State of the art | Name modelling, scalability and business models as open problems |
| Simulation | Hoffmann & Ansari 2019 (TU Berlin, DIW Berlin), Yemen; Bowes 2021 (Strathclyde); Soltowski et al. 2018 | Simulate interconnected solar home systems | No optimisation; staged growth is discussed, not valued |
| Static optimisation | Mwakijale 2026 (Paderborn thesis): MILP, ten houses, Tanzania | Optimal swarm grid planning | One design year; no demand growth, upgrade path, market or budgets in the parts I could read |
| Market design | Dumitrescu, Lüth, Weibezahn & Groh 2022 (EEEP); Bertram et al. 2024 (JCLP) | Community PPAs; local market, central vs bilateral clearing, Madagascar | Capacities given; no investment under uncertainty |
| Equilibrium | Ouanes et al. 2026 (Energy Economics) | MCP with endogenous investment and tariffs | Fixed demand, three nanogrids, one week, free interconnection |
| Market power | Bou Gebrael et al. 2026 (arXiv) | Bilevel model, diesel microgrid monopolist, price caps | Diesel incumbent; not PV swarms, no network growth |
| Multi-year mini-grids | Fioriti, Poli, Dueñas-Martínez & Pérez-Arriaga 2021 (Pisa, MIT Energy Initiative); Sayani et al. 2023; Petrelli (PoliMi thesis) | Stochastic or multi-stage sizing under load growth; Fioriti et al. report savings beyond 16–20 % of net present cost against single-year sizing | Mini-grids only; no interconnection or technology ladder |
| Grid arrival | Hoffmann 2019 (RLI); González Grandón, de Cuadra & Pérez-Arriaga 2021 | Mini-grids facing or under the main grid | Not the bottom-up side |
| National planning | OnSSET (KTH); REM (MIT/Comillas); Rwanda multi-stage stochastic plan (2022) | Grid vs mini-grid vs stand-alone at country scale | No swarm or mesh option in the tools I checked |
| Practitioner evidence | Okra Network Planner; CrossBoundary 2025 (Nigeria); GEAPP (Haiti) | Site-level mesh vs mini-grid costs; CrossBoundary reports full mesh deployment 41 % cheaper than mini-grids | Proprietary or case-specific; not in the academic planning literature |
| Implementation | Díaz-Pastor, de Abajo, Stoner & Pérez-Arriaga 2026 (MIT CEEPR WP 2026-04) | Regulatory and financial framework: plans are least-cost on paper but not financeable | Framework, not an optimisation with household-level constraints |

Two side observations:

- Dumitrescu et al. (2022) describe "complementarity and a linear model" for a swarm grid
  in Bangladesh. Ouanes et al. present theirs as the first MCP application to swarm
  electrification. Worth reading the earlier paper before repeating that claim.
- The concept comes from Berlin (TU Berlin MicroEnergy Systems, MicroEnergy International),
  and one of the simulation papers has a DIW Berlin affiliation. There is local history to
  build on.

## 4. The gaps, ranked

**Gap 1: the option value of modularity is unmeasured.** Swarm papers argue that staged,
bottom-up growth is the main advantage over mini-grids (Hoffmann & Ansari say so
explicitly). The models that study swarms are static. The models that value staging under
uncertain demand exist only for mini-grids (including one co-authored at MIT) and for
national plans. I found no model that
optimises *which lines to build and when*, and *when to centralise*, on a scenario tree.
Confidence that this is open: fairly high.

**Gap 2: swarm grids are missing from national planning.** OnSSET and REM choose among
grid, mini-grid and stand-alone. The Madagascar runs show why that matters: the binary
choice is unstable for a third of the population. Confidence: high for OnSSET (checked
documentation and recent extensions), medium for REM (not open, only papers checked).

**Gap 3: regulation of a swarm operator with real quantity effects.** Existing equilibrium
work has fixed demand, so market power only moves money. With price-responsive demand an
unregulated operator serves less and builds less. In practice one firm (Nanoé) owns the
nanogrids, so the relevant game is regulator versus operator, a bilevel problem.
Confidence: medium; Bou Gebrael et al. (2026) are close in method.

**Gap 4: interconnection versus credit.** In Ouanes et al. and in the prototype here,
interconnection pays almost only because poorer nanogrids cannot finance their own assets.
That ties the location of an asset to who pays for it. If the true friction is household
credit, then sharing energy is a substitute for lending, and the right comparison is with
pay-as-you-go finance. Conceptual, but it connects directly to the MIT group's
financeability agenda.

## 5. What the prototype shows (`swarmplan/`)

Illustrative village: eight sites (five household clusters, streetlights, school, mill),
50–120 m apart, the paper's cost parameters, assumed willingness-to-pay blocks. All values
EUR per week.

**(a) Why interconnect at all.** `results/spacing_sweep.csv`

| | Gain from swarm lines | Lines built |
|---|---|---|
| With household budget limits, sites ~80 m apart | 45.8 (demand served 64 % → 100 %) | 5 |
| Same, sites ~330 m apart | 38.0 | 5 |
| Same, sites ~660 m apart | 27.6 (served 87 %) | 4 |
| Without budget limits, any spacing from 40 m | 0.0 | 0 |

In this model interconnection is a response to financing constraints, not to load
diversity. (Average-day profiles understate diversity; the 15-minute replication found a
5.6 % cost saving, enough for roughly 30 m of line in total.)

**(b) Static comparison.** `results/static_strategies.csv`

| Pathway | Welfare | Cost | Demand served |
|---|---|---|---|
| Isolated nanogrids | 180.1 | 8.1 | 64 % |
| Swarm | 226.2 | 18.0 | 100 % |
| Mini-grid | 219.8 | 24.4 | 100 % |

**(c) Staged growth under uncertain demand.** `results/regime_map.csv`

Two stages; later demand either stays flat or is multiplied by the growth factor, each with
probability one half. Expected welfare, EUR per week, for two values of the hub's fixed cost F.
Best pathway per column in bold.

| Pathway | F=3, growth ×1.5 | F=3, growth ×2.5 | F=3, growth ×4 | F=8, growth ×1.5 | F=8, growth ×2.5 | F=8, growth ×4 |
|---|---|---|---|---|---|---|
| Swarm only | 254.9 | 311.7 | 396.4 | **254.9** | **311.7** | 396.4 |
| Swarm, hub if demand is high | 254.7 | 312.8 | 400.1 | 253.4 | 311.6 | **398.8** |
| Swarm, hub later in any case | 253.9 | 312.1 | 399.3 | 251.4 | 309.6 | 396.8 |
| Hub from day one, nanogrid assets kept | **256.5** | **314.4** | **401.6** | 251.5 | 309.4 | 396.6 |
| Classic mini-grid from day one | 254.0 | 312.4 | 399.9 | 249.0 | 307.4 | 394.9 |

Solver tolerance: values are optimal to within about 0.5 EUR per week, so differences
smaller than that are not meaningful.

What this shows:

- **Low hub cost (F=3):** the best design is a hub from day one that feeds only a few sites,
  with swarm lines distributing onward and nanogrid assets kept. It beats the classic
  mini-grid in every case.
- **High hub cost (F=8):** swarm only is best when growth is moderate. When demand may
  quadruple, starting as a swarm and adding the hub only if demand takes off is best, by
  about EUR 2.2 a week over any pathway that decides at the start (on a cost of about 28).
- **The classic mini-grid is never the best pathway** in this parameterisation.
- **Staging has value only when uncertainty is large and the hub is costly.** In 15 of the
  18 cases in `regime_map.csv` waiting gains nothing beyond solver tolerance. Capacity can
  be added later at the same unit cost and there are no lead times, which works against
  finding a value of waiting.

**Compatibility test.** `results/compatibility.csv` repeats the case where staging paid
(growth ×4, F=8) and strands part of the nanogrid hardware once the hub arrives:

| Share of nanogrid hardware stranded by the hub | Best pathway | Staged upgrade vs. best decide-now pathway |
|---|---|---|
| 0 % | Swarm, hub if demand is high | +2.2 |
| 50 % | Swarm, hub if demand is high | +0.6 (close to solver tolerance) |
| 100 % | Swarm only | −0.9 |

The value of the staged path is a statement about hardware compatibility. If swarm
equipment survives centralisation, starting small and upgrading is the best plan; if it
does not, the choice collapses back to swarm or mini-grid.

Practitioners describe hub-and-spoke mesh layouts (Okra); I have not checked how close
they are to the hybrid design the model picks.

**(d) Operator and price cap.** `results/tariff_regulation.csv`

| Case | Tariff | Demand served | PV built (kWp) | Operator profit | Welfare |
|---|---|---|---|---|---|
| Welfare-maximising planner | – | 100 % | 11.0 | – | 228.6 |
| Unregulated operator | 1.2 | 35 % | 3.9 | 117.4 | 152.4 |
| Cap at 0.7 | 0.7 | 60 % | 6.6 | 113.4 | 199.7 |
| Cap at 0.4 | 0.4 | 80 % | 8.8 | 81.1 | 220.0 |
| Cap at 0.2 | 0.2 | 100 % | 11.0 | 42.8 | 228.6 |

Unlike in the paper, market power now changes investment: the unregulated operator builds
65 % less solar and serves a third of potential demand. The size of the effect is not
credible yet, for the reason below.

**A calibration red flag.** With the paper's cost parameters the model produces energy at
about EUR 0.05–0.08 per kWh, while Nanoé's tariff was about EUR 2 per kWh. The cost data
probably cover hardware only (my inference), leaving out installation, staff, logistics and
non-payment. Any welfare or regulation result needs a fixed operating cost first.

**(e) The paper's framework on real settlements.** See `docs/case_study.md`. Applied to
2,075 settlements around Antongil Bay and Ambanja, the published framework approves all of
them with budget limits and defers all of them without. Adding line costs makes demand
level and settlement geometry decisive. This by itself could be a short paper or comment.

## 6. A possible paper sequence

1. **OR core.** "Bottom-up or top-down? Valuing modularity in rural electrification."
   Multi-stage stochastic network design (the ladder model), decomposition for larger
   villages, real village geometry. Natural co-authors: the Ouanes/González Grandón/Gabriel
   group. Target: EJOR, Energy Economics, or Computational Management Science.
2. **Regulation.** Regulator–operator bilevel model with continuous demand (MPEC), price
   caps versus connection subsidies, calibrated on Nanoé tariff and metering data.
3. **Scale-up.** Reduced form of (1) as a fourth technology in OnSSET for Madagascar,
   with household affordability. This is PhD Essay 4.

Paper 1 alone is a well-defined OR contribution and does not need proprietary data.

## 7. Why this is a route to the MIT lab

- The MIT/Comillas group's 2026 working paper says plans are least-cost on paper but not
  financeable. Putting staging and household budgets inside the optimisation answers the
  problem they have just posed.
- Their tool (REM, commercialised through Waya Energy) has the same three technology
  classes as OnSSET. A validated swarm module is something they do not have.
- There is a personal chain. Tatiana González Grandón, co-author of the Ouanes paper,
  has published with Ignacio Pérez-Arriaga (MIT) and Fernando de Cuadra (Comillas, Waya
  co-founder) on undergrid mini-grids. Steven Gabriel is on the same paper. The first
  author is at Humboldt University in Berlin.
- REM is a cost-minimising design tool. Strategic operators and a swarm option are not
  part of it as far as I could see. Pérez-Arriaga co-authored the multi-year stochastic
  mini-grid paper (Fioriti et al. 2021), so the group already cares about staging. The
  edge to bring is the swarm ladder with network design plus the equilibrium layer.

## 8. What could sink it

- **The option value may be small.** In the prototype, staging is worth nothing in most
  cases and at most about 8 % of cost. If that holds with realistic costs, the headline
  becomes "staging rarely matters; a hub feeding a swarm does", which is publishable but a
  different paper. Lumpy sizing and lead times need to go in before drawing that
  conclusion, and hardware compatibility needs real engineering input.
- **Parameters.** Line costs, hub costs, scale economies and willingness to pay are
  assumed. Okra, CrossBoundary and Nanoé have real numbers; getting them is step one.
- **Someone is already doing it.** The authors of the Ouanes paper list uncertainty and
  bilevel optimisation as their own future work. Talking to them early turns a competitor
  into a co-author.
- **Budget modelling.** Gap 4 means the main mechanism has to be modelled as a credit
  constraint, or a referee will say the benefit is assumed.

## 9. Next steps

**Update, 16 November 2026.** Gap 1 now has a first national-scale answer in
`paper/main.pdf` (code in `national/`). It narrows the claim: the large effect is the cost
of sizing for future demand, and a simple adaptive rule captures almost all of it. The
swarm option itself is worth 1 to 2 % unless its generation is as cheap as a mini-grid's,
and it is largely a substitute for making stand-alone hardware mini-grid-compatible. The
steps below still apply; the swarm cost parameters (step 3) are now the binding one.

1. Read Dumitrescu et al. (2022), the Paderborn thesis chapter 5, and Fioriti et al. (2021)
   in full; confirm Gap 1 with a Scopus search.
2. Write to the first author of the Ouanes paper: share the replication, the pricing
   observation (see `replication/`), and ask for the input files.
3. Replace assumed costs with field numbers; add fixed operating cost.
4. Solve the three-stage tree with Gurobi (HiGHS does not close the gap in reasonable time).
5. Get DHS 2021 Madagascar access for the affordability layer.

## Sources

- Ouanes, González Grandón, Fagerli, Gabriel (2026), Energy Economics 163, 109598. https://doi.org/10.1016/j.eneco.2026.109598
- Sheridan, Sunderland, Courtney (2023), Swarm electrification: a comprehensive literature review, RSER 175. https://ideas.repec.org/a/eee/rensus/v175y2023ics1364032123000138.html
- Fuchs, Rajasekharan, Cali (2024), Decentralization, decarbonization and digitalization in swarm electrification. https://quarxiv.authorea.com/doi/full/10.36227/techrxiv.171332363.33333014/v1
- Kirchhoff & Strunz (2019), Applied Energy 244. https://econpapers.repec.org/RePEc:eee:appene:v:244:y:2019:i:c:p:46-62
- Hoffmann & Ansari (2018/2019), Simulating the potential of swarm grids, Yemen. https://mpra.ub.uni-muenchen.de/88166/1/MPRA_paper_88166.pdf
- Bowes (2021), Interconnection of Solar Home Systems as a Path to Bottom-Up Electrification, Strathclyde. https://stax.strath.ac.uk/downloads/79407x61s?locale=en
- Mwakijale (2026), Energy management and optimal grid planning for rural electrification in Africa, Paderborn. https://digital.ub.uni-paderborn.de/download/pdf/8281071.pdf
- Dumitrescu, Lüth, Weibezahn, Groh (2022), EEEP 11(1). https://research.cbs.dk/en/publications/prosumer-empowerment-through-community-power-purchase-agreements-/
- Bertram et al. (2024), J. Cleaner Production 449. https://ntnuopen.ntnu.no/ntnu-xmlui/handle/11250/3146079
- Richard et al. (2022), Energies 15(18), 6727. https://www.mdpi.com/1996-1073/15/18/6727
- Bou Gebrael, Olleik, Zwickl-Bernhard (2026), arXiv 2603.16893. https://arxiv.org/abs/2603.16893
- Fioriti, Poli, Dueñas-Martínez, Pérez-Arriaga (2021), Electric Power Systems Research 194, 107053. https://doi.org/10.1016/j.epsr.2021.107053
- Sayani et al. (2023), J. Phys. Energy 5. https://eprints.whiterose.ac.uk/194353/1/Sayani_2023_J._Phys._Energy_5_014004.pdf
- Multi-stage stochastic electrification planning, Rwanda (2022), IEEE PowerAfrica. https://iro.uiowa.edu/esploro/outputs/conferenceProceeding/Multi-Stage-Stochastic-Electrification-Planning-under-Demand/9984380451502771
- Hoffmann (2019), micro grids facing interconnection, RLI. https://reiner-lemoine-institut.de/?p=3253
- González Grandón, de Cuadra, Pérez-Arriaga (2021), Energies 14(23), 7881. https://dspace.mit.edu/handle/1721.1/138237
- Díaz-Pastor, de Abajo, Stoner, Pérez-Arriaga (2026), MIT CEEPR WP 2026-04. https://ceepr.mit.edu/wp-content/uploads/2026/03/MIT-CEEPR-WP-2026-04.pdf
- Waya Energy / REM. https://www.weforum.org/stories/energy-transition/mit-software-universal-access-electricity/
- CrossBoundary mesh-grid study (2025), via Duke Energy Access Project. https://energyaccess.duke.edu/publication/mesh-grids-for-rural-electrification-new-crossboundary-study-unveils-a-scalable-cost-effective-and-resilient-solution/
- Okra, mesh-grids vs mini-grids. https://www.okrasolar.com/blog/mesh-grids-vs-mini-grids-for-different-sized-communities
- Okra, hub and spoke. https://www.okrasolar.com/blog/the-road-to-productive-use-energy-at-sub-500-per-connection-okra-hub-spoke
- RMI, Interconnected Minigrids: From Pilots to Powerhouses (applies its framework to Madagascar, among others). https://rmi.org/insight/interconnected-minigrids-from-pilots-to-powerhouses
- GEAPP mesh-grids report, Haiti. https://energyalliance.org/wp-content/uploads/2025/03/GEAPP-Mesh-Grids-Report.pdf
- OnSSET documentation. https://onsset.readthedocs.io/
- GEP Madagascar scenario description (2019). https://gep-source-archive.s3.amazonaws.com/models-august-2019/mg-1/mg-1-scenario-description.pdf
