"""
SwarmPlan.jl — a planning model for bottom-up electrification pathways.

What it adds to the equilibrium model of Ouanes et al. (2026):

  1. Space.       Nanogrids have coordinates. Lines are investment decisions with a cost
                  per metre, a capacity and distance-dependent losses (network design).
  2. Demand.      Demand is price-responsive: each nanogrid's load is split into blocks
                  with decreasing willingness to pay (WTP). Unserved energy has an
                  explicit welfare cost, so "welfare" is consumer value minus cost, in EUR.
  3. Time.        Investment is staged on a scenario tree of demand growth
                  (multi-stage stochastic program). Capacity and lines are irreversible.
  4. The ladder.  Besides nanogrid-level assets and peer-to-peer (swarm) lines, the village
                  can upgrade to a mini-grid: a central hub with a fixed cost, cheaper unit
                  costs (economies of scale) and stronger lines.
  5. Regulation.  A single operator who sets a uniform tariff, with or without a price cap
                  (solved by enumerating the tariff over the WTP levels).
  6. Compatibility. `Tech.strand` is the share of nanogrid-level assets that becomes
                  unusable once the hub exists (e.g. DC hardware on an AC mini-grid).

Strategies (all evaluated on the same tree, so they are directly comparable):
  :isolated   nanogrid-level assets only, no lines
  :swarm      nanogrid-level assets + swarm lines
  :minigrid   central hub from the first stage, no nanogrid-level assets
  :ladder     everything allowed; the hub can be added at any stage

Units: energy in kWh per hour, costs in EUR per week (levelised), distances in metres.
Operation is modelled on representative days with weights that add up to one week.
"""
module SwarmPlan

using JuMP, HiGHS

export Site, Village, Tech, Tree, plan, operator_tariff, two_stage_tree, three_stage_tree,
       static_tree

struct Site
    name::String
    x::Float64
    y::Float64
    demand::Matrix{Float64}      # [rep day, hour], kWh per hour at reference growth 1.0
    budget::Float64              # EUR per week for own PV + battery (Inf = none)
end

struct Village
    sites::Vector{Site}
    solar::Matrix{Float64}       # [rep day, hour], kWh per kWp
    day_weight::Vector{Float64}  # days per week represented by each rep day (sums to 7)
    wtp::Vector{Float64}         # EUR/kWh of each demand block, decreasing
    share::Vector{Float64}       # share of demand in each block (sums to 1)
end

Base.@kwdef struct Tech
    # nanogrid-level assets (paper, Tables 3-4)
    c_sol::Float64 = 0.518       # EUR per kWp per week
    c_bat::Float64 = 0.384       # EUR per kWh per week
    c_cyc::Float64 = 0.0005      # EUR per kWh charged or discharged
    eta::Float64 = 0.90          # one-way battery efficiency
    self_dis::Float64 = 0.004    # self-discharge per hour (0.1 % per 15 min in the paper)
    c_rate::Float64 = 1.0        # max (dis)charge per hour as share of capacity
    # swarm lines (low-voltage DC, nanogrid to nanogrid)          -- ASSUMED values
    c_line::Float64 = 0.006      # EUR per metre per week
    cap_line::Float64 = 1.0      # kWh per hour
    loss_line::Float64 = 0.0003  # loss share per metre (3 % per 100 m)
    c_wheel::Float64 = 0.0001    # EUR per kWh transferred (paper: c_ie)
    k_neigh::Int = 3             # candidate lines: each site to its k nearest neighbours
    # mini-grid hub (central PV + battery, AC star network)       -- ASSUMED values
    hub_fixed::Float64 = 8.0     # EUR per week (power house, inverter, licensing)
    hub_scale::Float64 = 0.70    # unit cost of central PV/battery relative to nanogrid level
    c_feeder::Float64 = 0.009    # EUR per metre per week
    cap_feeder::Float64 = 10.0   # kWh per hour
    loss_feeder::Float64 = 0.00005
    budget_scales::Bool = true   # household budgets grow with the demand growth factor
    strand::Float64 = 0.0        # share of nanogrid-level PV/battery made unusable once the hub exists
end

"Scenario tree: parent[n] = 0 for the root; growth[n] multiplies demand; prob[n] sums to 1 per stage."
struct Tree
    parent::Vector{Int}
    growth::Vector{Float64}
    prob::Vector{Float64}
    stage::Vector{Int}
end

static_tree(g = 1.0) = Tree([0], [g], [1.0], [1])
two_stage_tree(lo, hi; p = 0.5) = Tree([0, 1, 1], [1.0, lo, hi], [1.0, 1 - p, p], [1, 2, 2])
function three_stage_tree(lo, hi; p = 0.5)
    Tree([0, 1, 1, 2, 2, 3, 3],
         [1.0, lo, hi, lo * lo, lo * hi, hi * lo, hi * hi],
         [1.0, 1 - p, p, (1 - p)^2, (1 - p) * p, p * (1 - p), p^2],
         [1, 2, 2, 3, 3, 3, 3])
end

dist(a, b) = hypot(a[1] - b[1], a[2] - b[2])

"Candidate swarm lines: undirected k-nearest-neighbour graph."
function candidate_lines(v::Village, k::Int)
    I = length(v.sites)
    pos = [(s.x, s.y) for s in v.sites]
    E = Set{Tuple{Int,Int}}()
    for i in 1:I
        order = sortperm([i == j ? Inf : dist(pos[i], pos[j]) for j in 1:I])
        for j in order[1:min(k, I - 1)]
            push!(E, (min(i, j), max(i, j)))
        end
    end
    sort(collect(E))
end

"""
    plan(v, tree; strategy=:ladder, tech=Tech(), price=nothing, operator=false, ...)

Welfare-maximising plan on the scenario tree. `hub_pattern` fixes the hub decision per
tree node (e.g. [0, 0, 1] = upgrade only if demand turns out high). If `price` is given, only demand blocks
with WTP >= price can be served and, with `operator=true`, the objective is the
operator's profit (price x energy sold - cost) instead of welfare.
"""
function plan(v::Village, tree::Tree; strategy::Symbol = :ladder, tech::Tech = Tech(),
              price::Union{Nothing,Float64} = nothing, operator::Bool = false,
              time_limit::Float64 = 240.0, gap::Float64 = 0.005, spread::Float64 = 1.0,
              ignore_budgets::Bool = false, hub_pattern::Union{Nothing,Vector{Int}} = nothing)
    I = length(v.sites); R, H = size(v.solar); K = length(v.wtp); N = length(tree.parent)
    pos = [(s.x * spread, s.y * spread) for s in v.sites]
    hub = (sum(first.(pos)) / I, sum(last.(pos)) / I)              # hub at the centroid
    E = candidate_lines(v, tech.k_neigh)
    len = [dist(pos[i], pos[j]) for (i, j) in E]
    flen = [dist(pos[i], hub) for i in 1:I]
    w = v.day_weight
    allow_lines = strategy in (:swarm, :ladder)
    allow_hub = strategy in (:minigrid, :ladder)
    allow_own = strategy != :minigrid
    blocks = price === nothing ? collect(1:K) : [k for k in 1:K if v.wtp[k] >= price - 1e-9]

    m = Model(HiGHS.Optimizer)
    set_silent(m)
    set_attribute(m, "time_limit", time_limit)
    set_attribute(m, "mip_rel_gap", gap)

    @variables(m, begin
        S[0:I, 1:N] >= 0                      # PV capacity; index 0 is the hub
        B[0:I, 1:N] >= 0
        g[0:I, 1:R, 1:H, 1:N] >= 0            # solar used
        ch[0:I, 1:R, 1:H, 1:N] >= 0
        dis[0:I, 1:R, 1:H, 1:N] >= 0
        soc[0:I, 1:R, 1:H, 1:N] >= 0
        d[1:I, blocks, 1:R, 1:H, 1:N] >= 0    # served demand per WTP block
        f[1:length(E), 1:2, 1:R, 1:H, 1:N] >= 0   # swarm flows, direction 1: i->j, 2: j->i
        ff[1:I, 1:2, 1:R, 1:H, 1:N] >= 0      # feeder flows, 1: hub->site, 2: site->hub
        y[1:length(E), 1:N], Bin              # swarm line built
        z[1:I, 1:N], Bin                      # feeder built
        u[1:N], Bin                           # hub built
        Su[1:I, 1:N] >= 0                     # usable nanogrid PV (differs from S only if strand > 0)
        Bu[1:I, 1:N] >= 0                     # usable nanogrid battery
    end)
    stranding = tech.strand > 0
    capS(i, n) = (stranding && i >= 1) ? Su[i, n] : S[i, n]
    capB(i, n) = (stranding && i >= 1) ? Bu[i, n] : B[i, n]

    for n in 1:N
        pa = tree.parent[n]; gr = tree.growth[n]
        if pa > 0                                   # irreversibility
            @constraint(m, [i in 0:I], S[i, n] >= S[i, pa])
            @constraint(m, [i in 0:I], B[i, n] >= B[i, pa])
            @constraint(m, [e in eachindex(E)], y[e, n] >= y[e, pa])
            @constraint(m, [i in 1:I], z[i, n] >= z[i, pa])
            @constraint(m, u[n] >= u[pa])
        end
        allow_lines || @constraint(m, [e in eachindex(E)], y[e, n] == 0)
        allow_hub || @constraint(m, u[n] == 0)
        strategy == :minigrid && @constraint(m, u[n] == 1)
        hub_pattern === nothing || @constraint(m, u[n] == hub_pattern[n])
        if !allow_own
            @constraint(m, [i in 1:I], S[i, n] == 0)
            @constraint(m, [i in 1:I], B[i, n] == 0)
        end
        # tight big-M: the hub never needs more than the village's peak-day energy
        peak = gr * maximum(sum(s.demand[r, h] for s in v.sites, h in 1:H) for r in 1:R)
        maxS = 3 * peak / minimum(sum(v.solar, dims = 2)); maxB = 3 * peak
        @constraint(m, S[0, n] <= maxS * u[n])
        @constraint(m, B[0, n] <= maxB * u[n])
        if stranding
            # compatibility: with the hub in place only a share (1 - strand) of nanogrid assets is usable
            @constraint(m, [i in 1:I], S[i, n] <= maxS)
            @constraint(m, [i in 1:I], B[i, n] <= maxB)
            @constraint(m, [i in 1:I], Su[i, n] <= S[i, n])
            @constraint(m, [i in 1:I], Bu[i, n] <= B[i, n])
            @constraint(m, [i in 1:I], Su[i, n] <= (1 - tech.strand) * S[i, n] + maxS * (1 - u[n]))
            @constraint(m, [i in 1:I], Bu[i, n] <= (1 - tech.strand) * B[i, n] + maxB * (1 - u[n]))
        end
        @constraint(m, [i in 1:I], z[i, n] <= u[n])
        if !ignore_budgets
            for i in 1:I
                b = v.sites[i].budget
                isfinite(b) || continue
                b *= tech.budget_scales ? gr : 1.0
                @constraint(m, tech.c_sol * S[i, n] + tech.c_bat * B[i, n] <= b)
            end
        end
        for r in 1:R, h in 1:H
            hp = h == 1 ? H : h - 1                 # cyclic representative day
            for i in 0:I
                @constraint(m, g[i, r, h, n] <= capS(i, n) * v.solar[r, h])
                @constraint(m, ch[i, r, h, n] <= tech.c_rate * capB(i, n))
                @constraint(m, dis[i, r, h, n] <= tech.c_rate * capB(i, n))
                @constraint(m, soc[i, r, h, n] <= capB(i, n))
                @constraint(m, soc[i, r, h, n] == (1 - tech.self_dis) * soc[i, r, hp, n] +
                                                   tech.eta * ch[i, r, h, n] - dis[i, r, h, n] / tech.eta)
            end
            for i in 1:I
                inflow = AffExpr(0.0); outflow = AffExpr(0.0)
                for (e, (a, b)) in enumerate(E)
                    eff = 1 - tech.loss_line * len[e]
                    if a == i
                        add_to_expression!(outflow, f[e, 1, r, h, n]); add_to_expression!(inflow, eff, f[e, 2, r, h, n])
                    elseif b == i
                        add_to_expression!(outflow, f[e, 2, r, h, n]); add_to_expression!(inflow, eff, f[e, 1, r, h, n])
                    end
                end
                feff = 1 - tech.loss_feeder * flen[i]
                @constraint(m, g[i, r, h, n] + dis[i, r, h, n] - ch[i, r, h, n] + inflow - outflow +
                               feff * ff[i, 1, r, h, n] - ff[i, 2, r, h, n] ==
                               sum(d[i, k, r, h, n] for k in blocks; init = 0.0))
                for k in blocks
                    @constraint(m, d[i, k, r, h, n] <= v.share[k] * gr * v.sites[i].demand[r, h])
                end
                # no feeder needs to carry more than the village's peak hourly demand
                fcap = min(tech.cap_feeder, gr * maximum(sum(s.demand[rr, hh] for s in v.sites) for rr in 1:R, hh in 1:H))
                @constraint(m, [dir in 1:2], ff[i, dir, r, h, n] <= fcap * z[i, n])
            end
            @constraint(m, g[0, r, h, n] + dis[0, r, h, n] - ch[0, r, h, n] +
                           sum((1 - tech.loss_feeder * flen[i]) * ff[i, 2, r, h, n] - ff[i, 1, r, h, n] for i in 1:I) == 0)
            for e in eachindex(E), dir in 1:2
                eff = 1 - tech.loss_line * len[e]
                if eff <= 0.5                       # line too long to be useful
                    @constraint(m, f[e, dir, r, h, n] == 0)
                else
                    @constraint(m, f[e, dir, r, h, n] <= tech.cap_line * y[e, n])
                end
            end
        end
    end

    value_n = [sum(w[r] * v.wtp[k] * d[i, k, r, h, n] for i in 1:I, k in blocks, r in 1:R, h in 1:H; init = 0.0) for n in 1:N]
    sold_n = [sum(w[r] * d[i, k, r, h, n] for i in 1:I, k in blocks, r in 1:R, h in 1:H; init = 0.0) for n in 1:N]
    capex_n = [sum(tech.c_sol * S[i, n] + tech.c_bat * B[i, n] for i in 1:I) +
               tech.hub_scale * (tech.c_sol * S[0, n] + tech.c_bat * B[0, n]) for n in 1:N]
    net_n = [sum(tech.c_line * len[e] * y[e, n] for e in eachindex(E); init = 0.0) +
             sum(tech.c_feeder * flen[i] * z[i, n] for i in 1:I) + tech.hub_fixed * u[n] for n in 1:N]
    opex_n = [sum(w[r] * tech.c_cyc * (ch[i, r, h, n] + dis[i, r, h, n]) for i in 0:I, r in 1:R, h in 1:H) +
              sum(w[r] * tech.c_wheel * f[e, dir, r, h, n] for e in eachindex(E), dir in 1:2, r in 1:R, h in 1:H; init = 0.0) +
              sum(w[r] * tech.c_wheel * ff[i, dir, r, h, n] for i in 1:I, dir in 1:2, r in 1:R, h in 1:H) for n in 1:N]
    cost_n = [capex_n[n] + net_n[n] + opex_n[n] for n in 1:N]
    # equal-length stages: each stage gets weight 1 / number of stages
    nst = maximum(tree.stage)
    pw = [tree.prob[n] / nst for n in 1:N]
    if operator
        price === nothing && error("operator=true needs a price")
        @objective(m, Max, sum(pw[n] * (price * sold_n[n] - cost_n[n]) for n in 1:N))
    else
        @objective(m, Max, sum(pw[n] * (value_n[n] - cost_n[n]) for n in 1:N))
    end
    optimize!(m)
    st = termination_status(m)
    has_values(m) || return (status = st,)

    potential = [sum(w[r] * tree.growth[n] * s.demand[r, h] for s in v.sites, r in 1:R, h in 1:H) for n in 1:N]
    ev(x) = sum(pw[n] * value(x[n]) for n in 1:N)
    return (status = st, strategy = strategy,
            welfare = ev(value_n) - ev(cost_n), consumer_value = ev(value_n), cost = ev(cost_n),
            capex = ev(capex_n), network_cost = ev(net_n),
            energy_sold = ev(sold_n), served_share = ev(sold_n) / sum(pw .* potential),
            revenue = price === nothing ? NaN : price * ev(sold_n),
            profit = price === nothing ? NaN : price * ev(sold_n) - ev(cost_n),
            pv = [sum(value(S[i, n]) for i in 0:I) for n in 1:N],
            pv_hub = [value(S[0, n]) for n in 1:N],
            battery = [sum(value(B[i, n]) for i in 0:I) for n in 1:N],
            lines = [round(Int, sum(value.(y[:, n]))) for n in 1:N],
            line_metres = [sum(len[e] * value(y[e, n]) for e in eachindex(E)) for n in 1:N],
            feeders = [round(Int, sum(value.(z[:, n]))) for n in 1:N],
            hub = [round(Int, value(u[n])) for n in 1:N],
            served_by_node = [value(sold_n[n]) / potential[n] for n in 1:N],
            gap = try relative_gap(m) catch; NaN end,
            n_candidate_lines = length(E), mean_candidate_length = sum(len) / length(len))
end

"""
    operator_tariff(v; cap=Inf, strategy=:ladder, ...)

A single operator owns all assets and sets one tariff. With step demand the profit-
maximising tariff is one of the WTP levels, so it is found by enumeration. Returns the
operator's choice among tariffs <= cap, together with the welfare it implies.
"""
function operator_tariff(v::Village; cap::Float64 = Inf, strategy::Symbol = :ladder,
                         tech::Tech = Tech(), tree::Tree = static_tree(), kwargs...)
    best = nothing
    for p in sort(unique(v.wtp); rev = true)
        p <= cap + 1e-9 || continue
        r = plan(v, tree; strategy = strategy, tech = tech, price = p, operator = true,
                 ignore_budgets = true, kwargs...)
        haskey(r, :profit) || continue
        if best === nothing || r.profit > best.profit + 1e-9
            best = merge(r, (tariff = p,))
        end
    end
    return best
end

end # module
