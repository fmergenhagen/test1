# Runs the six scenarios of Ouanes et al. (2026), Table 2, and prints a comparison
# with the paper's Tables 5 and 6.   Usage:  julia --project=. run_scenarios.jl
include("SwarmGrid.jl")
using .SwarmGrid
using CSV, DataFrames, Printf

prof = CSV.read(joinpath(@__DIR__, "data", "profiles.csv"), DataFrame)
solar = Vector{Float64}(prof.solar_cf)
p = Params()

hom_budget = [Inf, Inf, Inf]            # "no budget limitations"
het_budget = [0.4, 1.2, 40.0]           # EUR per week, Section 4.3
hom_demand = [("Households A", prof.hh_a), ("Households B", prof.hh_b), ("Households C", prof.hh_c)]
het_demand = [("Households", prof.hh_a), ("Streetlights", prof.streetlights), ("School", prof.school)]
grid(dem, bud) = [Nanogrid(dem[i][1], Vector{Float64}(dem[i][2]), bud[i]) for i in 1:3]

scenarios = [
    ("1",  grid(hom_demand, hom_budget), :competition),
    ("2",  grid(het_demand, hom_budget), :competition),
    ("3",  grid(hom_demand, het_budget), :competition),
    ("4a", grid(het_demand, het_budget), :planner),
    ("4b", grid(het_demand, het_budget), :competition),
    ("4c", grid(het_demand, het_budget), :cournot),
]

# Paper values: (PV kWp, battery kWh, cost EUR/week, energy shared kWh/week, total profit)
paper = Dict(
    "1"  => (7.215, 12.921, 8.78, 0.340, 0.00),
    "2"  => (5.778, 10.405, 7.06, 2.653, 0.00),
    "3"  => (7.215, 12.921, 8.78, 42.886, 0.00),
    "4a" => (5.778, 10.405, 7.06, 42.024, 180.87),
    "4b" => (5.778, 10.405, 7.06, 41.877, 0.00),
    "4c" => (5.778, 10.405, 7.06, 41.881, 85.76),
)

rows = DataFrame()
detail = DataFrame()
for (id, ngs, market) in scenarios
    r = solve_swarm(ngs, solar, p; market = market)
    # stand-alone benchmark without budget limits, for avoided investment (AVIN)
    free = [Nanogrid(n.name, n.demand, Inf) for n in ngs]
    alone = solve_swarm(free, solar, p; interconnected = false, market = market)
    avin = 100 * (sum(alone.capex) - sum(r.capex)) / sum(alone.capex)
    pp = paper[id]
    push!(rows, (scenario = id, market = String(market),
        SDI = sdi(ngs), PDI = pdi(ngs),
        BHI = all(isinf, [n.budget for n in ngs]) ? 0.0 : bhi([n.budget for n in ngs]),
        pv_kWp = sum(r.pv), pv_paper = pp[1],
        battery_kWh = sum(r.battery), battery_paper = pp[2],
        cost_EUR_week = sum(r.cost), cost_paper = pp[3],
        shared_kWh = r.energy_shared, shared_paper = pp[4],
        profit_total = sum(r.profit_paper), profit_paper = pp[5],
        AVIN_pct = avin))
    for i in 1:3
        push!(detail, (scenario = id, nanogrid = r.names[i], demand_kWh = r.demand[i],
            pv_kWp = r.pv[i], battery_kWh = r.battery[i], cost = r.cost[i],
            imports = r.imports[i], exports = r.exports[i],
            profit_paper_convention = r.profit_paper[i],
            profit_consistent_price = r.profit_full[i],
            mean_price = sum(r.p_nano[i, :] .* ngs[i].demand) / r.demand[i],
            max_price = maximum(r.p_nano[i, :])))
    end
end

mkpath(joinpath(@__DIR__, "results"))
CSV.write(joinpath(@__DIR__, "results", "summary.csv"), rows)
CSV.write(joinpath(@__DIR__, "results", "by_nanogrid.csv"), detail)

fmt(x) = x isa AbstractFloat ? @sprintf("%.3f", x) : string(x)
println("\n=== System totals: replication vs. paper ===")
show(stdout, mapcols(c -> fmt.(c), rows); allrows = true, allcols = true, summary = false)
println("\n\n=== By nanogrid ===")
show(stdout, mapcols(c -> fmt.(c), detail); allrows = true, allcols = true, summary = false)
println()
