# Experiments for the SwarmPlan prototype. Results are written to results/ as each block
# finishes.   usage: julia --project=.. run_experiments.jl [static] [spacing] [regime] [regime_summary] [tariff] [compat] [compat_summary]
include("SwarmPlan.jl"); using .SwarmPlan
include("village.jl")
using CSV, DataFrames, Printf

out(name) = joinpath(@__DIR__, "results", name)
mkpath(joinpath(@__DIR__, "results"))
todo = isempty(ARGS) ? ["static", "spacing", "regime", "regime_summary", "tariff", "compat", "compat_summary"] : ARGS
r2(x) = round(x, digits = 3)

# ---------------------------------------------------------------- 1. static comparison
if "static" in todo
    v = build_village()
    df = DataFrame()
    for st in (:isolated, :swarm, :minigrid)
        t = @elapsed r = plan(v, static_tree(); strategy = st, gap = 0.002, time_limit = 200.0)
        push!(df, (strategy = String(st), welfare = r2(r.welfare), consumer_value = r2(r.consumer_value),
                   cost = r2(r.cost), network_cost = r2(r.network_cost), served_share = r2(r.served_share),
                   pv_kWp = r2(r.pv[1]), battery_kWh = r2(r.battery[1]), lines = r.lines[1],
                   line_metres = r2(r.line_metres[1]), feeders = r.feeders[1],
                   status = string(r.status), mip_gap = r2(r.gap), seconds = r2(t)))
        CSV.write(out("static_strategies.csv"), df)
    end
    println(df)
end

# ---------------------------------------------------------------- 2. spacing sweep
if "spacing" in todo
    v = build_village(single_day = true)
    df = DataFrame()
    for budgets in (true, false), sp in (0.5, 1.0, 2.0, 4.0, 8.0)
        iso = plan(v, static_tree(); strategy = :isolated, ignore_budgets = !budgets, spread = sp)
        t = @elapsed sw = plan(v, static_tree(); strategy = :swarm, ignore_budgets = !budgets,
                                spread = sp, gap = 0.002, time_limit = 120.0)
        push!(df, (budget_limits = budgets, spacing_factor = sp, mean_line_length_m = r2(sw.mean_candidate_length),
                   welfare_isolated = r2(iso.welfare), welfare_swarm = r2(sw.welfare),
                   gain_eur_week = r2(sw.welfare - iso.welfare), served_isolated = r2(iso.served_share),
                   served_swarm = r2(sw.served_share), lines = sw.lines[1], line_metres = r2(sw.line_metres[1]),
                   status = string(sw.status), mip_gap = r2(sw.gap), seconds = r2(t)))
        CSV.write(out("spacing_sweep.csv"), df)
    end
    println(df)
end

# ---------------------------------------------------------------- 3. staged growth: regime map
# Two stages (now, later). Later demand is either unchanged or multiplied by `hi`
# (probability one half each). The hub decision is a pattern over the three tree nodes
# (now, later-low, later-high). For a fixed pattern the hub's fixed cost F only shifts
# welfare by F x (expected share of time the hub exists), so each pattern is solved once
# with F = 0 and the map over F follows analytically (block "regime_summary").
patterns = [("swarm_only",        (strategy = :swarm,),                              0.00),
            ("upgrade_if_high",   (strategy = :ladder, hub_pattern = [0, 0, 1]),     0.25),
            ("upgrade_later",     (strategy = :ladder, hub_pattern = [0, 1, 1]),     0.50),
            ("hybrid_upfront",    (strategy = :ladder, hub_pattern = [1, 1, 1]),     1.00),
            ("minigrid_upfront",  (strategy = :minigrid,),                           1.00)]
if "regime" in todo
    v = build_village(single_day = true)
    his = haskey(ENV, "HI") ? parse.(Float64, split(ENV["HI"], ",")) : [1.5, 2.5, 4.0]
    for hi in his
        df = DataFrame()
        tr = two_stage_tree(1.0, hi)
        tech = Tech(hub_fixed = 0.0, k_neigh = 2)
        for (name, kw, wgt) in patterns
            # pathway differences are small relative to total welfare, so the gap is tight
            t = @elapsed r = plan(v, tr; tech = tech, gap = 0.001, time_limit = 200.0, kw...)
            push!(df, (growth_high = hi, pathway = name, hub_weight = wgt, welfare_F0 = r2(r.welfare),
                       cost_F0 = r2(r.cost), served_share = r2(r.served_share),
                       served_high = r2(r.served_by_node[3]), lines_now = r.lines[1], lines_high = r.lines[3],
                       feeders_high = r.feeders[3], pv_hub_high = r2(r.pv_hub[3]), pv_total_high = r2(r.pv[3]),
                       status = string(r.status), mip_gap = round(r.gap, digits = 5), seconds = r2(t)))
            CSV.write(out("regime_patterns_hi$(hi).csv"), df)
        end
        println(df)
    end
end

if "regime_summary" in todo
    files = filter(f -> startswith(f, "regime_patterns_hi"), readdir(joinpath(@__DIR__, "results")))
    pat = vcat([CSV.read(out(f), DataFrame) for f in files]...)
    CSV.write(out("regime_patterns.csv"), sort(pat, [:growth_high, :hub_weight]))
    df = DataFrame()
    for g in groupby(pat, :growth_high), F in (0.0, 2.0, 4.0, 6.0, 8.0, 12.0)
        val = g.welfare_F0 .- F .* g.hub_weight
        k = argmax(val)
        get(p) = val[findfirst(==(p), g.pathway)]
        sw, mg, hy = get("swarm_only"), get("minigrid_upfront"), get("hybrid_upfront")
        # "decide now" pathways fix the hub decision in the first stage; the staged ones wait
        push!(df, (growth_high = g.growth_high[1], hub_fixed = F, best_pathway = g.pathway[k],
                   welfare_best = r2(val[k]), swarm_only = r2(sw), minigrid_upfront = r2(mg),
                   hybrid_upfront = r2(hy), upgrade_if_high = r2(get("upgrade_if_high")),
                   upgrade_later = r2(get("upgrade_later")),
                   gain_from_staging = r2(val[k] - max(sw, mg, hy)),
                   solver_tolerance_abs = r2(maximum(g.mip_gap .* g.welfare_F0))))
    end
    CSV.write(out("regime_map.csv"), df)
    println(df)
end

# ---------------------------------------------------------------- 4. operator and tariff cap
# A single operator owns all assets (as Nanoe does) and sets one tariff.
if "tariff" in todo
    v = build_village(single_day = true)
    tech = Tech(k_neigh = 2)
    df = DataFrame()
    pl = plan(v, static_tree(); strategy = :swarm, tech = tech, ignore_budgets = true, gap = 0.002, time_limit = 120.0)
    push!(df, (case = "welfare-maximising planner", tariff = NaN, energy_sold = r2(pl.energy_sold),
               served_share = r2(pl.served_share), pv_kWp = r2(pl.pv[1]), cost = r2(pl.cost),
               operator_profit = NaN, welfare = r2(pl.welfare)))
    for p in sort(unique(v.wtp); rev = true)
        r = plan(v, static_tree(); strategy = :swarm, tech = tech, price = p, operator = true,
                 ignore_budgets = true, gap = 0.002, time_limit = 120.0)
        push!(df, (case = "operator at tariff", tariff = p, energy_sold = r2(r.energy_sold),
                   served_share = r2(r.served_share), pv_kWp = r2(r.pv[1]), cost = r2(r.cost),
                   operator_profit = r2(r.profit), welfare = r2(r.welfare)))
        CSV.write(out("tariff_regulation.csv"), df)
    end
    println(df)
end

# ---------------------------------------------------------------- 5. compatibility
# Does staging still pay if nanogrid hardware is (partly) stranded when the hub arrives?
# Growth factor 4, where staging mattered. Swarm-only and the classic mini-grid do not
# depend on `strand`; they are read from the regime results.
if "compat" in todo
    v = build_village(single_day = true)
    tr = two_stage_tree(1.0, 4.0)
    strands = haskey(ENV, "STRAND") ? parse.(Float64, split(ENV["STRAND"], ",")) : [0.5, 1.0]
    for sdr in strands
        df = DataFrame()
        tech = Tech(hub_fixed = 0.0, k_neigh = 2, strand = sdr)
        for (name, kw, wgt) in patterns[2:4]
            t = @elapsed r = plan(v, tr; tech = tech, gap = 0.001, time_limit = 240.0, kw...)
            push!(df, (strand = sdr, growth_high = 4.0, pathway = name, hub_weight = wgt, welfare_F0 = r2(r.welfare),
                       cost_F0 = r2(r.cost), served_share = r2(r.served_share), lines_now = r.lines[1],
                       lines_high = r.lines[3], feeders_high = r.feeders[3], pv_hub_high = r2(r.pv_hub[3]),
                       pv_total_high = r2(r.pv[3]), status = string(r.status),
                       mip_gap = round(r.gap, digits = 5), seconds = r2(t)))
            CSV.write(out("compat_patterns_strand$(sdr).csv"), df)
        end
        println(df)
    end
end

if "compat_summary" in todo
    base = CSV.read(out("regime_patterns_hi4.0.csv"), DataFrame)
    base.strand .= 0.0
    files = filter(f -> startswith(f, "compat_patterns_strand"), readdir(joinpath(@__DIR__, "results")))
    cp = vcat([CSV.read(out(f), DataFrame) for f in files]...)
    fixed = base[in.(base.pathway, Ref(["swarm_only", "minigrid_upfront"])), :]
    df = DataFrame()
    for sdr in sort(unique(vcat(0.0, cp.strand))), F in (3.0, 8.0)
        g = sdr == 0.0 ? base : vcat(cp[cp.strand .== sdr, names(cp)], fixed[:, names(cp)])
        val = g.welfare_F0 .- F .* g.hub_weight
        row = Dict(p => r2(val[findfirst(==(p), g.pathway)]) for p in g.pathway)
        k = argmax(val)
        push!(df, (strand = sdr, hub_fixed = F, best_pathway = g.pathway[k], swarm_only = row["swarm_only"],
                   upgrade_if_high = row["upgrade_if_high"], upgrade_later = row["upgrade_later"],
                   hybrid_upfront = row["hybrid_upfront"], minigrid_upfront = row["minigrid_upfront"]))
    end
    CSV.write(out("compatibility.csv"), df)
    println(df)
end
