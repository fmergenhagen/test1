"""
SwarmGrid.jl

Replication of the swarm-grid models in
  Ouanes, González Grandón, Fagerli, Gabriel (2026), "Isolated or interconnected?
  An equilibrium framework for swarm electrification in rural energy planning",
  Energy Economics 163, 109598.

Equation numbers in the comments refer to that paper.

How the three market designs are solved
---------------------------------------
* Central planner (4a): the LP of Section 3.3, eqs. (9)-(20).
* Perfect competition (1, 2, 3, 4b): the MCP (23)-(42) is the KKT system of the
  same LP once the market-clearing dual is identified (see `price_convention`).
  Demand is fixed, so we solve the LP and read prices off the duals.
* Cournot (4c): in the MCP (44)-(63) the inverse-demand term enters every
  stationarity condition as the constant beta * D[i,t], because supply must equal
  the fixed demand D[i,t]. Quantities are therefore the LP quantities and the
  price is p_nano = alpha - beta * D[i,t], eq. (43).

A direct MCP solve (e.g. PATHSolver.jl) is not needed for these cases, but the LP
formulation below is written so that each constraint maps one-to-one to the
paper's complementarity conditions.
"""
module SwarmGrid

using JuMP, HiGHS

export Params, Nanogrid, solve_swarm, sdi, pdi, bhi

Base.@kwdef struct Params
    c_sol::Float64 = 0.518      # EUR per kWp per week        (Table 3)
    c_B::Float64 = 0.384        # EUR per kWh per week        (Table 3)
    c_ch::Float64 = 0.0005      # EUR per kWh charged         (Table 3)
    c_dis::Float64 = 0.0005     # EUR per kWh discharged      (Table 3)
    c_ie::Float64 = 0.0001      # EUR per kWh imported/exported (Table 3)
    s_b::Float64 = 0.001        # self-discharge per step     (Table 4: 0.1 %)
    u_b::Float64 = 0.90         # charge/discharge efficiency (Table 4)
    v_B::Float64 = 0.50         # max (dis)charge per step as share of capacity
    z_B::Float64 = 0.70         # initial state of charge as share of capacity
    g_max::Float64 = 100.0      # max transfer per step, kWh  (Table 4)
    alpha::Float64 = 1.0        # inverse demand intercept, EUR/kWh   (Section 4.3)
    beta::Float64 = 0.2         # inverse demand slope, EUR/kWh^2     (Section 4.3)
    line_cost::Float64 = 0.0    # EXTENSION: EUR per week per interconnected nanogrid
end

struct Nanogrid
    name::String
    demand::Vector{Float64}     # kWh per step
    budget::Float64             # EUR per week; Inf = no budget constraint
end

"""
    solve_swarm(ngs, solar_cf, p; interconnected=true, market=:competition, p_fixed=2.0)

`market` is one of `:planner`, `:competition`, `:cournot`.
Returns a NamedTuple with capacities, flows, prices and profits per nanogrid.
"""
function solve_swarm(ngs::Vector{Nanogrid}, solar_cf::Vector{Float64}, p::Params = Params();
                     interconnected::Bool = true, market::Symbol = :competition,
                     p_fixed::Float64 = 2.0)
    I, T = length(ngs), length(solar_cf)
    D = [ngs[i].demand[t] for i in 1:I, t in 1:T]

    m = Model(HiGHS.Optimizer)
    set_silent(m)
    @variables(m, begin
        S[1:I] >= 0                 # PV capacity, kWp
        B[1:I] >= 0                 # battery capacity, kWh
        Esol[1:I, 1:T] >= 0
        Ech[1:I, 1:T] >= 0
        Edis[1:I, 1:T] >= 0
        Eimp[1:I, 1:T] >= 0
        Eexp[1:I, 1:T] >= 0
        SoC[1:I, 1:T] >= 0
    end)

    # (10) nodal balance of each nanogrid; dual = lambda_nano
    @constraint(m, bal[i in 1:I, t in 1:T],
        Esol[i, t] + Edis[i, t] + Eimp[i, t] - Ech[i, t] - Eexp[i, t] == D[i, t])
    # (11) closed system: net exports sum to zero; dual = marginal value of energy
    @constraint(m, clear[t in 1:T], sum(Eexp[i, t] - Eimp[i, t] for i in 1:I) == 0)
    # (12)-(13) storage dynamics
    @constraint(m, soc1[i in 1:I],
        SoC[i, 1] - p.z_B * B[i] + Edis[i, 1] / p.u_b - p.u_b * Ech[i, 1] == 0)
    @constraint(m, soc[i in 1:I, t in 2:T],
        SoC[i, t] - (1 - p.s_b) * SoC[i, t-1] + Edis[i, t] / p.u_b - p.u_b * Ech[i, t] == 0)
    # (14)-(19) capacity limits
    @constraint(m, [i in 1:I, t in 1:T], Esol[i, t] <= S[i] * solar_cf[t])
    @constraint(m, [i in 1:I, t in 1:T], Ech[i, t] <= p.v_B * B[i])
    @constraint(m, [i in 1:I, t in 1:T], Edis[i, t] <= p.v_B * B[i])
    @constraint(m, [i in 1:I, t in 1:T], SoC[i, t] <= B[i])
    gmax = interconnected ? p.g_max : 0.0
    @constraint(m, [i in 1:I, t in 1:T], Eimp[i, t] <= gmax)
    @constraint(m, [i in 1:I, t in 1:T], Eexp[i, t] <= gmax)
    # (20) budget
    budget = Dict{Int,ConstraintRef}()
    for i in 1:I
        isfinite(ngs[i].budget) || continue
        budget[i] = @constraint(m, p.c_sol * S[i] + p.c_B * B[i] <= ngs[i].budget)
    end

    capex = [p.c_sol * S[i] + p.c_B * B[i] for i in 1:I]
    opex = [p.c_ch * sum(Ech[i, :]) + p.c_dis * sum(Edis[i, :]) +
            p.c_ie * sum(Eexp[i, :] .+ Eimp[i, :]) for i in 1:I]
    @objective(m, Min, sum(capex) + sum(opex))      # (9) without the constant revenue term
    optimize!(m)
    termination_status(m) == MOI.OPTIMAL ||
        return (status = termination_status(m),)

    lam_nano = [dual(bal[i, t]) for i in 1:I, t in 1:T]
    lam_sys = [dual(clear[t]) for t in 1:T]
    # The paper's stationarity conditions (26)-(27) contain p_micro + lambda_micro and
    # set p_micro = lambda_micro, so its reported microgrid price is half the
    # system marginal value of energy. `p_micro_paper` follows that convention.
    p_micro_paper = lam_sys ./ 2

    imp = [sum(value.(Eimp[i, :])) for i in 1:I]
    expo = [sum(value.(Eexp[i, :])) for i in 1:I]
    cost = [value(capex[i]) + value(opex[i]) for i in 1:I]
    net(i, t) = value(Eexp[i, t]) - value(Eimp[i, t])

    p_nano = if market == :planner
        fill(p_fixed, I, T)
    elseif market == :cournot
        [p.alpha - p.beta * D[i, t] for i in 1:I, t in 1:T]          # (43) with supply = D
    else
        lam_nano
    end
    revenue = [sum(p_nano[i, t] * D[i, t] for t in 1:T) for i in 1:I]
    # The planner drops the microgrid trade term (it nets out); see text below eq. (9).
    trade_paper = market == :planner ? zeros(I) :
                  [sum(p_micro_paper[t] * net(i, t) for t in 1:T) for i in 1:I]
    trade_full = [sum(lam_sys[t] * net(i, t) for t in 1:T) for i in 1:I]
    line = interconnected ? p.line_cost : 0.0

    return (status = MOI.OPTIMAL,
            names = [n.name for n in ngs],
            pv = value.(S), battery = value.(B),
            capex = value.(capex), opex = value.(opex), cost = cost .+ line,
            imports = imp, exports = expo, energy_shared = sum(expo),
            demand = vec(sum(D, dims = 2)),
            p_nano = p_nano, lam_nano = lam_nano, lam_sys = lam_sys,
            p_micro_paper = p_micro_paper,
            profit_paper = revenue .+ trade_paper .- cost .- line,
            profit_full = revenue .+ trade_full .- cost .- line,
            budget_dual = [haskey(budget, i) ? -dual(budget[i]) : 0.0 for i in 1:I],
            total_cost = objective_value(m) + I * line)
end

# ------------------------------------------------------------ heterogeneity indexes
"Shape Diversity Index, eq. (1): mean pairwise cosine dissimilarity of load profiles."
function sdi(ngs::Vector{Nanogrid})
    J = length(ngs)
    cosd(a, b) = 1 - sum(a .* b) / sqrt(sum(abs2, a) * sum(abs2, b))
    vals = [cosd(ngs[j].demand, ngs[k].demand) for j in 1:J-1 for k in j+1:J]
    return sum(vals) / length(vals)
end

"Peak Diversity Index, eq. (2)."
pdi(ngs::Vector{Nanogrid}) =
    1 - maximum(sum(n.demand for n in ngs)) / sum(maximum(n.demand) for n in ngs)

"Budget Heterogeneity Index (Gini-type), Section 2.1.1."
function bhi(budgets::Vector{Float64})
    b = sort(budgets); J = length(b)
    return 2 * sum(i * b[i] for i in 1:J) / (J * sum(b)) - (J + 1) / J
end

end # module
