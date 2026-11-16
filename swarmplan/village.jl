# Builds the illustrative village used in the experiments.
#
# Load shapes come from ../replication/data/profiles.csv (synthetic stand-ins calibrated
# to Ouanes et al. 2026, Fig. 4 and Table 6), aggregated to hourly values and averaged
# into two representative days (weekday, weekend). Everything else here -- positions,
# budgets beyond the paper's three values, the productive user, the WTP blocks -- is an
# ASSUMPTION made to exercise the model, not data.
using CSV, DataFrames

function rep_days(x::AbstractVector)                 # 672 quarter-hours -> [2 rep days, 24 h]
    hourly = [sum(x[4(k-1)+1:4k]) for k in 1:168]
    daily = reshape(hourly, 24, 7)                   # column = day
    hcat(vec(sum(daily[:, 1:5], dims = 2)) ./ 5, vec(sum(daily[:, 6:7], dims = 2)) ./ 2)' |> Matrix
end

function build_village(; profiles = joinpath(@__DIR__, "..", "replication", "data", "profiles.csv"),
                       single_day::Bool = false)
    p = CSV.read(profiles, DataFrame)
    hh_a, hh_b, hh_c = rep_days(p.hh_a), rep_days(p.hh_b), rep_days(p.hh_c)
    lights, school = rep_days(p.streetlights), rep_days(p.school)
    # productive user (mill / workshop): daytime load, mostly on weekdays
    mill = zeros(2, 24); mill[1, 9:16] .= 0.6; mill[2, 9:13] .= 0.3
    sites = [
        #    name              x      y     demand        budget (EUR/week)
        Site("Households A",    0.0,   0.0, hh_a,          0.4),   # paper: 0.4
        Site("Households B",   60.0,  20.0, hh_b,          0.6),
        Site("Households C",   40.0,  90.0, hh_c,          1.5),
        Site("Households D",  150.0,  10.0, 1.1 .* hh_b,   0.5),
        Site("Households E",  120.0, 110.0, 0.9 .* hh_c,   6.0),   # better-off cluster
        Site("Streetlights",   90.0,  50.0, lights,        1.2),   # paper: 1.2
        Site("School",        200.0,  90.0, school,       40.0),   # paper: 40
        Site("Mill",          230.0,  20.0, mill,          8.0),
    ]
    solar = rep_days(p.solar_cf)
    # WTP blocks: the top level matches the roughly 2 EUR/kWh that Nanoe customers paid,
    # the bottom level is below typical mini-grid tariffs. Shares are assumed.
    wtp = [2.0, 1.2, 0.7, 0.4, 0.2]
    share = [0.15, 0.20, 0.25, 0.20, 0.20]
    if single_day                      # one average day: smaller model for the stochastic runs
        avg(x) = reshape((5 .* x[1, :] .+ 2 .* x[2, :]) ./ 7, 1, 24)
        sites = [Site(s.name, s.x, s.y, avg(s.demand), s.budget) for s in sites]
        return Village(sites, avg(solar), [7.0], wtp, share)
    end
    Village(sites, solar, [5.0, 2.0], wtp, share)
end
