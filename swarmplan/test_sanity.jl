# Sanity checks for SwarmPlan. Each check states a property the model must satisfy.
#   julia --project=.. test_sanity.jl
include("SwarmPlan.jl"); using .SwarmPlan
include("village.jl")
using Test

v = build_village(single_day = true)
tol = 0.5        # EUR per week; MILP solves use a 0.1 % gap on a welfare of about 230

@testset "SwarmPlan sanity" begin
    iso = plan(v, static_tree(); strategy = :isolated)
    sw = plan(v, static_tree(); strategy = :swarm, gap = 0.001)
    mg = plan(v, static_tree(); strategy = :minigrid)

    @testset "pathways are nested: more options never hurt" begin
        @test sw.welfare >= iso.welfare - tol
        lad = plan(v, static_tree(); strategy = :ladder, gap = 0.001, time_limit = 120.0)
        @test lad.welfare >= max(sw.welfare, mg.welfare) - tol
    end

    @testset "without budgets and with free energy value, everything is served" begin
        free = plan(v, static_tree(); strategy = :isolated, ignore_budgets = true)
        @test free.served_share > 0.999
        @test free.welfare >= iso.welfare - 1e-6
    end

    @testset "a prohibitive hub cost reproduces the swarm solution" begin
        lad = plan(v, static_tree(); strategy = :ladder, tech = Tech(hub_fixed = 1e4), gap = 0.001, time_limit = 120.0)
        @test lad.hub[1] == 0
        @test abs(lad.welfare - sw.welfare) <= tol
    end

    @testset "prohibitive line cost reproduces isolated nanogrids" begin
        s2 = plan(v, static_tree(); strategy = :swarm, tech = Tech(c_line = 1e3))
        @test s2.lines[1] == 0
        @test abs(s2.welfare - iso.welfare) <= 1e-4
    end

    @testset "welfare falls as the tariff rises above the lowest WTP" begin
        w = [plan(v, static_tree(); strategy = :isolated, price = p, operator = true, ignore_budgets = true).welfare
             for p in (0.2, 0.7, 2.0)]
        @test w[1] >= w[2] >= w[3]
    end

    @testset "stranding only matters when a hub exists, and it never helps" begin
        s0 = plan(v, static_tree(); strategy = :swarm, tech = Tech(strand = 1.0), gap = 0.001)
        @test abs(s0.welfare - sw.welfare) <= tol
        h0 = plan(v, static_tree(); strategy = :ladder, hub_pattern = [1], gap = 0.001, time_limit = 120.0)
        h1 = plan(v, static_tree(); strategy = :ladder, hub_pattern = [1], tech = Tech(strand = 1.0), gap = 0.001, time_limit = 120.0)
        @test h1.welfare <= h0.welfare + tol
        @test h1.welfare >= mg.welfare - tol      # full stranding leaves at least the classic mini-grid
    end

    @testset "scaling demand and budgets together leaves the served share unchanged" begin
        tr = two_stage_tree(1.0, 3.0)
        r = plan(v, tr; strategy = :isolated)
        @test abs(r.served_by_node[3] - r.served_by_node[1]) <= 1e-3
    end
end
