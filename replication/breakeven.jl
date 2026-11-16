# Break-even interconnection cost: how much may the lines cost per week before
# stand-alone nanogrids are cheaper? (No budget limits, so both cases are feasible.)
include("SwarmGrid.jl"); using .SwarmGrid, CSV, DataFrames, Printf
prof = CSV.read(joinpath(@__DIR__, "data", "profiles.csv"), DataFrame)
solar = Vector{Float64}(prof.solar_cf); p = Params()
mk(cols) = [Nanogrid(String(c), Vector{Float64}(prof[!, c]), Inf) for c in cols]
# levelised cost of 1 m of low-voltage line per week (ASSUMPTION: 5000 EUR/km, 20 years, 10 %)
crf = 0.10 / (1 - 1.10^-20); eur_per_m_week = 5.0 * crf / 52
for (label, cols) in [("homogeneous demand (3 household groups)", [:hh_a, :hh_b, :hh_c]),
                      ("heterogeneous demand (households, streetlights, school)", [:hh_a, :streetlights, :school])]
    ngs = mk(cols)
    sw = solve_swarm(ngs, solar, p); al = solve_swarm(ngs, solar, p; interconnected = false)
    saving = al.total_cost - sw.total_cost
    @printf("%s\n  stand-alone %.3f  swarm %.3f  saving %.3f EUR/week (%.1f %%)  -> break-even line length %.0f m in total\n",
            label, al.total_cost, sw.total_cost, saving, 100 * saving / al.total_cost, saving / eur_per_m_week)
end
