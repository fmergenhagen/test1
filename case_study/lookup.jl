# Case study, step 1: run the paper's model on a grid of settlement types.
#
# The framework of Ouanes et al. (2026) is scale-free: if every demand and every budget
# is multiplied by the same factor, all quantities scale and the indexes, AVIN and the
# benefit ratio do not change. A settlement therefore matters to the framework only through
#   rho  = productive and community demand / residential demand, and
#   GHI  = its solar resource.
# This script solves the model once per (rho, GHI) pair; apply_framework.py then scales the
# results to each real settlement and adds what does not scale: the lines.
#
# Representative cluster: three household nanogrids (five households each) plus, if rho > 0,
# one anchor nanogrid carrying the productive and community load.
#   julia --project=.. lookup.jl
include(joinpath(@__DIR__, "..", "replication", "SwarmGrid.jl"))
using .SwarmGrid
using CSV, DataFrames

prof = CSV.read(joinpath(@__DIR__, "..", "replication", "data", "profiles.csv"), DataFrame)
p = Params()
T = nrow(prof)
hh = [Vector{Float64}(prof.hh_a), Vector{Float64}(prof.hh_b), Vector{Float64}(prof.hh_c)]
D_res = sum(sum, hh)                                   # residential kWh per week in the cluster

# anchor load: daytime productive use, mostly on weekdays (quarter-hour steps)
clock = [((t - 1) % 96) / 4 for t in 1:T]; day = [(t - 1) ÷ 96 + 1 for t in 1:T]
anchor_shape = [(9 <= clock[t] < 16 ? (day[t] <= 5 ? 0.6 : 0.2) : 0.0) + 0.02 for t in 1:T]
anchor_shape ./= sum(anchor_shape)

GHI_REF = 2100.0      # ASSUMED: the reference solar profile (4.4 kWh/kWp/day) corresponds to this GHI
B_SHARE = (0.14, 0.14, 0.41)      # household budgets as a share of own stand-alone CAPEX
                                  # (paper: 0.4 and 1.2 EUR/week against about 2.9)
ANCHOR_MULT = 5.67                # paper: school budget 40 against a swarm CAPEX of 7.06

rhos = haskey(ENV, "RHO") ? parse.(Float64, split(ENV["RHO"], ",")) : [0.0, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0]
ghis = [1500.0, 1700.0, 1900.0, 2100.0, 2300.0]
tag = haskey(ENV, "RHO") ? "_" * replace(ENV["RHO"], "," => "-") : ""
df = DataFrame()
for rho in rhos, ghi in ghis
    solar = Vector{Float64}(prof.solar_cf) .* (ghi / GHI_REF)
    dem = copy(hh); names = ["HH1", "HH2", "HH3"]
    if rho > 0
        push!(dem, rho * D_res .* anchor_shape); push!(names, "Anchor")
    end
    K = length(dem)
    free = [Nanogrid(names[i], dem[i], Inf) for i in 1:K]
    alone = solve_swarm(free, solar, p; interconnected = false)       # isolated nanogrids
    nb = solve_swarm(free, solar, p)                                  # swarm, no budget limits
    # budgets in the paper's proportions
    bud = rho > 0 ? [B_SHARE[1] * alone.capex[1], B_SHARE[2] * alone.capex[2], B_SHARE[3] * alone.capex[3],
                     ANCHOR_MULT * sum(alone.capex)] :
                    [B_SHARE[1] * alone.capex[1], B_SHARE[3] * alone.capex[2], ANCHOR_MULT * sum(alone.capex)]
    wb = solve_swarm([Nanogrid(names[i], dem[i], bud[i]) for i in 1:K], solar, p)   # swarm with budgets
    ngs = [Nanogrid(names[i], dem[i], bud[i]) for i in 1:K]
    push!(df, (rho = rho, ghi = ghi, nanogrids = K, demand_res = D_res, demand_total = sum(sum, dem),
               SDI = sdi(ngs), PDI = pdi(ngs), BHI = bhi(bud),
               capex_alone = sum(alone.capex), opex_alone = sum(alone.opex),
               capex_swarm = sum(nb.capex), opex_swarm = sum(nb.opex), shared_swarm = nb.energy_shared,
               capex_budget = sum(wb.capex), opex_budget = sum(wb.opex), shared_budget = wb.energy_shared,
               status_budget = string(wb.status)))
    CSV.write(joinpath(@__DIR__, "results", "lookup$(tag).csv"), df)
end
println(df)
