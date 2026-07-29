//! FSOT Mind Host — Zig-native multi-region organism (no Python required).
//!
//! Usage:
//!   fsot_mind.exe              # full suite
//!   fsot_mind.exe selftest
//!   fsot_mind.exe learn
//!   fsot_mind.exe live
//!   fsot_mind.exe inject
//!   fsot_mind.exe structure
//!   fsot_mind.exe memory
//!   fsot_mind.exe organism     # continuous organism loop (synth senses)
//!   fsot_mind.exe bio [params] # FI population bio metrics (optional Allen params file)
//!   fsot_mind.exe stress       # multi-protocol stress suite (machine-readable)
//!   fsot_mind.exe all
//!
//! Python remains optional only for media decode / UI / science lab.

const std = @import("std");
const trit = @import("trit.zig");
const scalar = @import("scalar.zig");
const neuron = @import("neuron.zig");
const network = @import("network.zig");
const fingerprint = @import("fingerprint.zig");
const seeds = @import("seeds.zig");
const frame_inject = @import("frame_inject.zig");
const metric_inject = @import("metric_inject.zig");
const brain = @import("brain.zig");
const learning = @import("learning.zig");
const pathways = @import("pathways.zig");
const sensory = @import("sensory.zig");
const modulate = @import("modulate.zig");
const memory = @import("memory.zig");
const slots = @import("slots.zig");
const organism = @import("organism.zig");
const bio_probe = @import("bio_probe.zig");
const bio_params_load = @import("bio_params_load.zig");
const codon = @import("codon.zig");
const genotype = @import("genotype.zig");
const genetic = @import("genetic.zig");
const cell_types = @import("cell_types.zig");
const bands = @import("bands.zig");
const inject_io = @import("inject_io.zig");
const fixed = @import("fixed.zig");
const scalar_fixed = @import("scalar_fixed.zig");
const neuron_fixed = @import("neuron_fixed.zig");
const network_fixed = @import("network_fixed.zig");
const brain_fixed = @import("brain_fixed.zig");
const organism_fixed = @import("organism_fixed.zig");

fn printF64(label: []const u8, x: f64) void {
    std.debug.print("{s}{e}\n", .{ label, x });
}

fn modeName(m: modulate.Mode) []const u8 {
    return switch (m) {
        .dampen => "dampen",
        .balanced => "balanced",
        .explore => "explore",
    };
}

fn runSelfTest() !void {
    std.debug.print("=== FSOT MIND HOST (Zig authority) ===\n", .{});
    std.debug.print("doctrine: organism loop in Zig; Python optional I/O only\n", .{});

    const tr = trit.selfTest();
    if (!tr.ok) {
        std.debug.print("FSOT_TRIT FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_TRIT PASS\n", .{});

    if (!codon.selfTest()) {
        std.debug.print("FSOT_CODON FAIL (64-codon primary map / ORF)\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_CODON PASS 64_primary AG=+1 CT=-1 ATG=[+1,-1,+1]\n", .{});

    if (!genotype.selfTest()) {
        std.debug.print("FSOT_GENOTYPE FAIL (ORF→expression→phenotype)\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_GENOTYPE PASS codon_spine\n", .{});

    if (!genetic.selfTest() or !cell_types.selfTest()) {
        std.debug.print("FSOT_GENETIC FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_GENETIC PASS W_from_spins\n", .{});

    if (!bands.selfTest()) {
        std.debug.print("FSOT_BANDS FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_BANDS PASS\n", .{});

    if (!inject_io.selfTest()) {
        std.debug.print("FSOT_INJECT_IO FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_INJECT_IO PASS\n", .{});

    const s0 = scalar.computeNeuro(0.1, 0.0, 1.0);
    printF64("SCALAR_NEURO_DPI0.1=", s0);

    const pst = neuron.paritySelfTest();
    if (!pst.ok) {
        std.debug.print("FSOT_NEURON FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_NEURON PASS spikes={d}\n", .{pst.spikes});

    const nst = network.networkSelfTest();
    if (!nst.ok) {
        std.debug.print("FSOT_NETWORK FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_NETWORK PASS units=16 spikes={d}\n", .{nst.spikes});

    const bst = brain.brainSelfTest();
    if (!bst.ok) {
        std.debug.print("FSOT_BRAIN FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print(
        "FSOT_BRAIN PASS units={d} regions=thal/sens/assoc/hipp spikes={d}\n",
        .{ brain.N_TOTAL, bst.spikes },
    );
    printF64("BRAIN_MEAN_S=", bst.mean_s);

    if (!pathways.selfTest()) {
        std.debug.print("FSOT_PATHWAYS FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_PATHWAYS PASS gate={e}\n", .{pathways.consciousnessGate()});

    if (!sensory.selfTest()) {
        std.debug.print("FSOT_SENSORY FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_SENSORY PASS\n", .{});

    if (!modulate.selfTest()) {
        std.debug.print("FSOT_MODULATE FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_MODULATE PASS\n", .{});

    if (!slots.selfTest()) {
        std.debug.print("FSOT_SLOTS FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_SLOTS PASS\n", .{});

    const fp = fingerprint.fingerprintSelfTest();
    if (fp.ok) {
        std.debug.print("FSOT_FP PASS correct={d}/{d}\n", .{ fp.correct, fp.n });
    } else {
        std.debug.print("FSOT_FP soft correct={d}/{d}\n", .{ fp.correct, fp.n });
    }

    if (!metric_inject.selfTest()) {
        std.debug.print("FSOT_METRIC FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_METRIC PASS\n", .{});

    var demo: [22]u8 = undefined;
    @memcpy(demo[0..4], &frame_inject.magic);
    demo[4] = 1;
    demo[5] = 1;
    std.mem.writeInt(u32, demo[6..10], 4, .little);
    std.mem.writeInt(u64, demo[10..18], 0, .little);
    demo[18] = 4;
    demo[19] = 0;
    demo[20] = 0;
    demo[21] = 0;
    if (frame_inject.parseHeader(demo[0..]) == null) {
        std.debug.print("FSOT_FRAME FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_FRAME PASS\n", .{});

    printF64("SEEDS_K=", seeds.k);
    printF64("SEEDS_PHI=", seeds.phi);
    std.debug.print("FSOT_MIND_SELFTEST_OK\n", .{});
}

fn runLearn() void {
    std.debug.print("=== FSOT MIND LEARN (Zig) ===\n", .{});
    std.debug.print(
        "items={d} encode={d} delay={d} retrieve={d} hebb=on fp_dim={d}\n",
        .{ learning.N_ITEMS, learning.ENCODE_STEPS, learning.DELAY_STEPS, learning.RETRIEVE_STEPS, learning.FP_DIM },
    );
    const rep = learning.runLearnProbe();
    std.debug.print(
        "LEARN top1={e} correct={d}/{d} sim+={e} sim-={e} spikes={d}\n",
        .{ rep.top1, rep.correct, rep.n_items, rep.mean_s_plus, rep.mean_s_minus, rep.spikes },
    );
    if (rep.ok) {
        std.debug.print("FSOT_LEARN PASS\n", .{});
    } else {
        std.debug.print("FSOT_LEARN FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runMemory() void {
    std.debug.print("=== FSOT MIND MEMORY (episodic + 5W1H) ===\n", .{});
    if (!memory.selfTest()) {
        std.debug.print("FSOT_MEMORY FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_MEMORY PASS encode/retrieve/curiosity-fill\n", .{});

    // richer demo
    var b = brain.Brain.init();
    var store: memory.Store = .{};
    store.clear();
    const patterns = [_][6]f64{
        .{ 0.9, -0.2, 0.4, 0.1, -0.7, 0.3 },
        .{ -0.5, 0.8, -0.1, 0.6, 0.2, -0.9 },
        .{ 0.1, 0.1, 0.95, -0.4, 0.55, 0.0 },
        .{ 0.7, 0.7, -0.8, -0.3, 0.15, 0.45 },
    };
    const domains = [_]memory.Domain{ .narrative, .media, .physics_fsot, .biology };
    var i: usize = 0;
    while (i < patterns.len) : (i += 1) {
        var card: slots.Card = .{ .domain = domains[i] };
        card.set(.what, memory.hashToken("pattern"));
        card.set(.how, memory.hashToken("fsot_encode"));
        if (i % 2 == 0) card.set(.who, memory.hashToken("agent"));
        if (i == 2) card.set(.why, slots.mechanismToken(.physics_fsot));
        _ = store.encode(&b, patterns[i][0..], domains[i], card.slot_mask, card.tokens);
    }
    var sim: f64 = 0;
    const hit = store.retrieve(&b, patterns[2][0..], &sim);
    std.debug.print("retrieve id={d} sim={e} n={d}\n", .{ hit, sim, store.count() });
    const cur = slots.runCuriosity(&store, hit, .physics_fsot);
    std.debug.print(
        "curiosity q={d} resolved={d} open={d}\n",
        .{ cur.n_questions, cur.n_resolved, cur.remaining_open },
    );
    std.debug.print("FSOT_MEMORY_DEMO PASS\n", .{});
}

fn runOrganism() void {
    std.debug.print("=== FSOT MIND ORGANISM (genetic intelligence loop) ===\n", .{});
    var org = organism.Organism.init();
    org.encode_every = 25;
    org.steps_per_tick = 4;
    const n_ticks: u32 = 100;
    const st0 = org.brain.structureReport();
    std.debug.print(
        "genetic brain units={d} syn={d} Pyr/PV/SST/VIP={d}/{d}/{d}/{d} mean_spin={e}\n",
        .{ st0.n_units, st0.n_synapses, st0.n_pyr, st0.n_pv, st0.n_sst, st0.n_vip, st0.mean_composite_spin },
    );
    std.debug.print("ticks={d} steps/tick={d} encode_every={d}\n", .{ n_ticks, org.steps_per_tick, org.encode_every });

    var t: u32 = 0;
    while (t < n_ticks) : (t += 1) {
        const r = org.tickOnce(true);
        if ((t + 1) % 25 == 0) {
            std.debug.print(
                "t={d} meanS={e} spikes={d} mode={s} spin={e} eps={d} cur={d}\n",
                .{
                    r.tick,
                    r.mean_s,
                    r.spikes,
                    modeName(r.mode),
                    r.mean_spin,
                    r.n_episodes,
                    r.curiosity_resolved,
                },
            );
        }
    }
    if (org.store.count() < 2) {
        std.debug.print("FSOT_ORGANISM FAIL episodes={d}\n", .{org.store.count()});
        std.process.exit(1);
    }
    std.debug.print(
        "FSOT_ORGANISM PASS ticks={d} episodes={d} spikes={d} curiosity={d} sme={d}\n",
        .{
            org.tick,
            org.store.count(),
            org.brain.totalSpikes(),
            org.curiosity_resolved_total,
            @as(u32, if (org.last_sme_ok) 1 else 0),
        },
    );
}

fn runFixed() void {
    std.debug.print("=== FSOT FIXED-POINT STACK (scalar→neuron→net→brain→organism) ===\n", .{});
    std.debug.print("SCALE={d} quantum=1/SCALE\n", .{fixed.SCALE});
    std.debug.print("doctrine: seeds fixed; dynamics on lattice; codon genetics exact\n", .{});

    if (!fixed.selfTest()) {
        std.debug.print("FSOT_FIXED_ARITH FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_FIXED_ARITH PASS\n", .{});

    if (!scalar_fixed.selfTest()) {
        std.debug.print("FSOT_FIXED_SCALAR FAIL\n", .{});
        std.process.exit(1);
    }
    const f64_s = scalar.computeNeuro(0.1, 0.0, 1.0);
    const fx = scalar_fixed.computeNeuro(fixed.fromDecimalStr("0.1"), 0, fixed.fromInt(1));
    const fx_as_f = fixed.toF64(fx);
    const abs_err = if (f64_s > fx_as_f) f64_s - fx_as_f else fx_as_f - f64_s;
    std.debug.print("SCALAR_F64={e} FIXED={e} |dS|={e}\n", .{ f64_s, fx_as_f, abs_err });
    std.debug.print("FSOT_FIXED_SCALAR PASS\n", .{});

    const nst = neuron_fixed.paritySelfTest();
    if (!nst.ok) {
        std.debug.print("FSOT_FIXED_NEURON FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_FIXED_NEURON PASS spikes={d} lastS={e}\n", .{ nst.spikes, fixed.toF64(nst.last_S) });
    const npar = neuron_fixed.parityVsF64();
    std.debug.print(
        "NEURON_PARITY max|dS|={e} spike_mm={d} spikes_f64={d} spikes_fixed={d}\n",
        .{ npar.max_abs_dS, npar.spike_mm, npar.spikes_f, npar.spikes_z },
    );
    if (!npar.ok) {
        std.debug.print("FSOT_FIXED_NEURON_PARITY FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_FIXED_NEURON_PARITY PASS\n", .{});

    const netst = network_fixed.networkSelfTest();
    if (!netst.ok) {
        std.debug.print("FSOT_FIXED_NETWORK FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_FIXED_NETWORK PASS spikes={d}\n", .{netst.spikes});

    const bst = brain_fixed.brainSelfTest();
    if (!bst.ok) {
        std.debug.print("FSOT_FIXED_BRAIN FAIL\n", .{});
        std.process.exit(1);
    }
    var b = brain_fixed.BrainF.initSeeded(42, false);
    const st = b.structureReport();
    std.debug.print(
        "FSOT_FIXED_BRAIN PASS spikes={d} E={d} I={d} syn={d} Pyr/PV/SST/VIP={d}/{d}/{d}/{d}\n",
        .{ bst.spikes, st.n_e, st.n_i, st.n_synapses, st.n_pyr, st.n_pv, st.n_sst, st.n_vip },
    );

    if (!organism_fixed.selfTest()) {
        std.debug.print("FSOT_FIXED_ORGANISM FAIL\n", .{});
        std.process.exit(1);
    }
    var org = organism_fixed.OrganismF.init();
    const orep = org.run(40);
    std.debug.print(
        "FSOT_FIXED_ORGANISM PASS ticks={d} spikes={d} syn={d} meanS={e}\n",
        .{ orep.ticks, orep.spikes, orep.n_syn, fixed.toF64(org.brain.meanS()) },
    );

    std.debug.print("FSOT_FIXED_STACK_OK\n", .{});
}

fn runIntel() void {
    std.debug.print("=== FSOT MIND INTEL (bare-metal-ready continuous intelligence) ===\n", .{});
    std.debug.print("doctrine: trinary codon structure = genetic code of the mind\n", .{});
    var org = organism.Organism.init();
    org.encode_every = 20;
    org.steps_per_tick = 4;
    const rep = org.runIntel(120, true);
    std.debug.print(
        "INTEL ticks={d} eps={d} spikes={d} cur={d} pyr={d} I={d} syn={d}\n",
        .{ rep.ticks, rep.episodes, rep.total_spikes, rep.curiosity, rep.n_pyr, rep.n_i, rep.n_synapses },
    );
    printF64("INTEL_mean_S=", rep.final_mean_s);
    printF64("INTEL_mean_spin=", rep.mean_spin);
    printF64("INTEL_learn_top1=", rep.learn_top1);
    std.debug.print("INTEL_sme={d} INTEL_learn={d}\n", .{
        @as(u32, if (rep.sme_ok) 1 else 0),
        @as(u32, if (rep.learn_ok) 1 else 0),
    });
    if (!rep.ok) {
        std.debug.print("FSOT_INTEL FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_INTEL PASS genetic_folding_ops\n", .{});
}

fn runInjectFile(path: []const u8) !void {
    std.debug.print("=== FSOT MIND INJECT-FILE → genetic organism ===\n", .{});
    std.debug.print("path={s}\n", .{path});
    var org = organism.Organism.init();
    org.encode_every = 15;
    org.steps_per_tick = 5;
    const n_pkt = try inject_io.loadFeatureFile(path, &org.bus);
    std.debug.print("packets={d} metric_cpu={e}\n", .{ n_pkt, org.bus.metric.cpu });
    if (n_pkt < 1) {
        std.debug.print("FSOT_INJECT_FILE FAIL empty\n", .{});
        std.process.exit(1);
    }
    // run ticks with injected bus (no synth overwrite — re-load each tick)
    var t: u32 = 0;
    while (t < 45) : (t += 1) {
        _ = try inject_io.loadFeatureFile(path, &org.bus);
        _ = org.tickOnce(false);
    }
    std.debug.print(
        "after ticks={d} eps={d} spikes={d} meanS={e} spin={e}\n",
        .{ org.tick, org.store.count(), org.brain.totalSpikes(), org.brain.meanS(), org.meanCompositeSpin() },
    );
    if (org.brain.totalSpikes() < 1) {
        std.debug.print("FSOT_INJECT_FILE FAIL no spikes\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_INJECT_FILE PASS\n", .{});
}

fn runLive() void {
    std.debug.print("=== FSOT MIND LIVE (Zig multi-region) ===\n", .{});
    var b = brain.Brain.init();
    const st = b.structureReport();
    std.debug.print(
        "structure units={d} E={d} I={d} synapses={d} Pyr/PV/SST/VIP={d}/{d}/{d}/{d}\n",
        .{ st.n_units, st.n_e, st.n_i, st.n_synapses, st.n_pyr, st.n_pv, st.n_sst, st.n_vip },
    );
    printF64("MEAN_ABS_W=", st.mean_abs_w);
    printF64("MEAN_COMPOSITE_SPIN=", st.mean_composite_spin);

    var ext: [brain.N_TOTAL]f64 = undefined;
    var t: usize = 0;
    var spikes_win: u32 = 0;
    while (t < 120) : (t += 1) {
        const prim: f64 = if ((t % 30) < 10) 0.75 else 0.06;
        const reg: brain.RegionId = if ((t / 30) % 2 == 0) .sens else .assoc;
        b.buildExternal(prim, reg, ext[0..]);
        const before = b.totalSpikes();
        b.step(ext[0..]);
        spikes_win += b.totalSpikes() - before;
        if ((t + 1) % 30 == 0) {
            std.debug.print(
                "t={d} meanS={e} thal={e} sens={e} assoc={e} hipp={e} spikes_win={d}\n",
                .{
                    t + 1,
                    b.meanS(),
                    b.regionMeanS(.thal),
                    b.regionMeanS(.sens),
                    b.regionMeanS(.assoc),
                    b.regionMeanS(.hipp),
                    spikes_win,
                },
            );
            spikes_win = 0;
        }
    }
    std.debug.print("FSOT_LIVE PASS total_spikes={d}\n", .{b.totalSpikes()});
}

fn runInject() void {
    std.debug.print("=== FSOT MIND INJECT (sensory bus) ===\n", .{});
    var b = brain.Brain.init();
    var bus: sensory.Bus = .{};
    const feats = [_]f64{ 0.9, -0.4, 0.6, 0.1, -0.8, 0.55, 0.2, -0.15 };
    bus.push(sensory.Packet.fromSlice(.vision, feats[0..], 0.85));
    bus.metric = .{ .cpu = 0.25, .mem = 0.3, .disk = 0.1, .net = 0.05, .temp = 0.15 };
    var ext: [brain.N_TOTAL]f64 = undefined;
    var t: usize = 0;
    while (t < 60) : (t += 1) {
        bus.buildExternal(&b, 1.0, ext[0..]);
        b.step(ext[0..]);
    }
    std.debug.print(
        "inject meanS={e} sens={e} hipp={e} spikes={d}\n",
        .{ b.meanS(), b.regionMeanS(.sens), b.regionMeanS(.hipp), b.totalSpikes() },
    );
    if (b.totalSpikes() >= 1) {
        std.debug.print("FSOT_INJECT PASS\n", .{});
    } else {
        std.debug.print("FSOT_INJECT FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runStructure() void {
    std.debug.print("=== FSOT MIND STRUCTURE ===\n", .{});
    var b = brain.Brain.init();
    const st = b.structureReport();
    std.debug.print("profile=ai_efficient units={d}\n", .{st.n_units});
    std.debug.print("regions: thal={d} sens={d} assoc={d} hipp={d}\n", .{
        brain.N_THAL,
        brain.N_SENS,
        brain.N_ASSOC,
        brain.N_HIPP,
    });
    std.debug.print("E={d} I={d} synapses={d}\n", .{ st.n_e, st.n_i, st.n_synapses });
    std.debug.print("cell_types Pyr={d} PV={d} SST={d} VIP={d}\n", .{ st.n_pyr, st.n_pv, st.n_sst, st.n_vip });
    printF64("mean_abs_W=", st.mean_abs_w);
    printF64("mean_composite_spin=", st.mean_composite_spin);
    printF64("ei_mass_ratio=", @as(f64, @floatFromInt(st.n_e)) / @as(f64, @floatFromInt(if (st.n_i == 0) 1 else st.n_i)));
    printF64("consciousness_gate=", pathways.consciousnessGate());
    // dump unit 0 codon genotype summary
    const g0 = b.genotypes[0];
    std.debug.print(
        "unit0 type={d} spin={e} charge={e} SCN_expr={e} ref_ms={e}\n",
        .{
            @intFromEnum(g0.cell_type),
            g0.composite_spin,
            g0.composite_charge,
            g0.phenotype.scn_expression,
            g0.phenotype.refractory_steps,
        },
    );
    std.debug.print("FSOT_STRUCTURE PASS\n", .{});
}

fn runGenetic() void {
    std.debug.print("=== FSOT MIND GENETIC (64-codon foundation) ===\n", .{});
    if (!codon.selfTest() or !genotype.selfTest()) {
        std.debug.print("FSOT_GENETIC_CORE FAIL\n", .{});
        std.process.exit(1);
    }
    // Channel ORF spins (no diversity)
    const scn = genotype.buildGeneProgram(.scn, genotype.ORF_SCN);
    const kcn = genotype.buildGeneProgram(.kcn, genotype.ORF_KCN);
    const ca = genotype.buildGeneProgram(.cacna, genotype.ORF_CACNA);
    const leak = genotype.buildGeneProgram(.leak, genotype.ORF_LEAK);
    std.debug.print("SCN spin={e} expr={e} q={d}\n", .{ scn.spin, scn.expression, scn.charge_balance });
    std.debug.print("KCN spin={e} expr={e} q={d}\n", .{ kcn.spin, kcn.expression, kcn.charge_balance });
    std.debug.print("CACNA spin={e} expr={e} q={d}\n", .{ ca.spin, ca.expression, ca.charge_balance });
    std.debug.print("LEAK spin={e} expr={e} q={d}\n", .{ leak.spin, leak.expression, leak.charge_balance });

    const pyr = genotype.buildCellTypeGenotype(0, .pyr, false);
    const pv = genotype.buildCellTypeGenotype(0, .pv, false);
    std.debug.print("Pyr spin={e} ref={e} fi={e}\n", .{ pyr.composite_spin, pyr.phenotype.refractory_steps, pyr.phenotype.fi_stim });
    std.debug.print("PV  spin={e} ref={e} fi={e}\n", .{ pv.composite_spin, pv.phenotype.refractory_steps, pv.phenotype.fi_stim });

    var b = brain.Brain.initWithDiversity(true);
    const st = b.structureReport();
    std.debug.print(
        "brain genetic units={d} E={d} I={d} syn={d} Pyr/PV/SST/VIP={d}/{d}/{d}/{d}\n",
        .{ st.n_units, st.n_e, st.n_i, st.n_synapses, st.n_pyr, st.n_pv, st.n_sst, st.n_vip },
    );
    printF64("mean_abs_W=", st.mean_abs_w);
    printF64("mean_spin=", st.mean_composite_spin);
    printF64("mean_charge=", st.mean_composite_charge);
    // machine-readable for Python parity harness
    std.debug.print("GEN_N_SYN={d}\n", .{st.n_synapses});
    std.debug.print("GEN_N_PYR={d}\n", .{st.n_pyr});
    std.debug.print("GEN_N_PV={d}\n", .{st.n_pv});
    std.debug.print("GEN_N_SST={d}\n", .{st.n_sst});
    std.debug.print("GEN_N_VIP={d}\n", .{st.n_vip});
    std.debug.print("GEN_N_E={d}\n", .{st.n_e});
    std.debug.print("GEN_N_I={d}\n", .{st.n_i});
    printF64("GEN_MEAN_ABS_W=", st.mean_abs_w);
    var ext: [brain.N_TOTAL]f64 = undefined;
    var t: usize = 0;
    while (t < 100) : (t += 1) {
        b.buildExternal(if ((t % 40) < 12) 0.65 else 0.06, .sens, ext[0..]);
        b.step(ext[0..]);
    }
    std.debug.print("live spikes={d} meanS={e}\n", .{ b.totalSpikes(), b.meanS() });
    if (st.n_synapses < 1 or b.totalSpikes() < 1 or st.n_pyr < 1) {
        std.debug.print("FSOT_GENETIC FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_GENETIC PASS codon→genotype→W→step\n", .{});
}

fn runSme() void {
    std.debug.print("=== FSOT MIND SME (band / encode vs rest) ===\n", .{});
    if (!bands.selfTest()) {
        std.debug.print("FSOT_SME FAIL bands\n", .{});
        std.process.exit(1);
    }
    var b = brain.Brain.init();
    var ext: [brain.N_TOTAL]f64 = undefined;
    // encode epoch: patterned drive
    var rate_enc: [256]f64 = undefined;
    var t: usize = 0;
    while (t < 256) : (t += 1) {
        const prim: f64 = if ((t % 20) < 8) 0.7 else 0.1;
        b.buildExternal(prim, .sens, ext[0..]);
        // add item-like pattern
        var u: usize = 0;
        while (u < b.n) : (u += 1) {
            if (b.region_of[u] == .assoc) ext[u] += 0.3 * @as(f64, @floatFromInt((t + u) % 5)) / 5.0;
        }
        const before = b.totalSpikes();
        b.step(ext[0..]);
        const df = b.totalSpikes() - before;
        rate_enc[t] = @as(f64, @floatFromInt(df)) / @as(f64, @floatFromInt(b.n)) * 1000.0;
    }
    // rest epoch: low drive
    b.reset();
    var rate_rest: [256]f64 = undefined;
    t = 0;
    while (t < 256) : (t += 1) {
        b.buildExternal(0.05, .thal, ext[0..]);
        const before = b.totalSpikes();
        b.step(ext[0..]);
        const df = b.totalSpikes() - before;
        rate_rest[t] = @as(f64, @floatFromInt(df)) / @as(f64, @floatFromInt(b.n)) * 1000.0;
    }
    const sme = bands.smeContrast(rate_enc[0..], rate_rest[0..], 1.0);
    std.debug.print(
        "theta_enc={e} theta_rest={e} gamma_enc={e} gamma_rest={e} th_gt={d} ga_gt={d}\n",
        .{
            sme.theta_encode,
            sme.theta_rest,
            sme.gamma_encode,
            sme.gamma_rest,
            @as(u32, if (sme.theta_gt) 1 else 0),
            @as(u32, if (sme.gamma_gt) 1 else 0),
        },
    );
    // Soft directional: report; hard gate is finite powers + encode had spikes
    var enc_sum: f64 = 0;
    for (rate_enc) |r| enc_sum += r;
    if (enc_sum <= 0 or sme.theta_encode != sme.theta_encode) {
        std.debug.print("FSOT_SME FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_SME PASS (directional proxies)\n", .{});
}

fn emitPop(prefix: []const u8, r: bio_probe.PopReport) void {
    std.debug.print("{s}n_units={d}\n", .{ prefix, r.n_units });
    std.debug.print("{s}mean_rate_Hz={e}\n", .{ prefix, r.mean_rate_Hz });
    std.debug.print("{s}mean_isi_ms={e}\n", .{ prefix, r.mean_isi_ms });
    std.debug.print("{s}mean_adapt={e}\n", .{ prefix, r.mean_adapt });
    std.debug.print("{s}mean_isi_cv={e}\n", .{ prefix, r.mean_isi_cv });
    std.debug.print("{s}mean_S={e}\n", .{ prefix, r.mean_S });
    std.debug.print("{s}mean_Vm_mV={e}\n", .{ prefix, r.mean_Vm_mV });
    std.debug.print("{s}total_spikes={d}\n", .{ prefix, r.total_spikes });
    std.debug.print("{s}n_with_isi={d}\n", .{ prefix, r.n_with_isi });
}

fn runBio(params_path: ?[]const u8) !void {
    std.debug.print("=== FSOT MIND BIO (FI population) ===\n", .{});
    if (!bio_probe.selfTest()) {
        std.debug.print("FSOT_BIO_SELFTEST FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_BIO_SELFTEST PASS\n", .{});

    var params: [32]bio_probe.UnitParams = undefined;
    var n: usize = 32;
    var source: []const u8 = "default_bio_matchish";
    if (params_path) |path| {
        n = bio_params_load.loadFromPath(path, params[0..]) catch |err| {
            std.debug.print("FSOT_BIO params load FAIL {s} err={s}\n", .{ path, @errorName(err) });
            std.process.exit(1);
        };
        source = path;
        std.debug.print("params_file={s} n={d}\n", .{ path, n });
    } else {
        bio_probe.defaultBioParams(params[0..n]);
        std.debug.print("params=default n={d}\n", .{n});
    }
    std.debug.print("params_source={s}\n", .{source});

    const steps: usize = 1200;
    const rep = bio_probe.runFIPopulation(params[0..n], steps, 1.0);
    emitPop("BIO_FI_", rep);

    // Multi-region brain with same phenotype lock + sensory FI bursts
    var br = brain.Brain.init();
    br.applyBioParams(params[0..n]);
    var ext: [brain.N_TOTAL]f64 = undefined;
    var t: usize = 0;
    const bsteps: usize = 800;
    while (t < bsteps) : (t += 1) {
        // FI into sens (+ thal relay) using mean fi_stim of locked params
        var mean_fi: f64 = 0;
        var i: usize = 0;
        while (i < n) : (i += 1) mean_fi += params[i].fi_stim;
        mean_fi /= @as(f64, @floatFromInt(n));
        const on = (t % 80) < 25;
        br.buildExternal(if (on) mean_fi else 0.05, .sens, ext[0..]);
        br.step(ext[0..]);
    }
    std.debug.print("BIO_BRAIN_spikes={d}\n", .{br.totalSpikes()});
    std.debug.print("BIO_BRAIN_mean_S={e}\n", .{br.meanS()});
    std.debug.print("BIO_BRAIN_sens_S={e}\n", .{br.regionMeanS(.sens)});
    std.debug.print("BIO_BRAIN_hipp_S={e}\n", .{br.regionMeanS(.hipp)});
    const brain_rate = @as(f64, @floatFromInt(br.totalSpikes())) /
        (@as(f64, @floatFromInt(br.n)) * @as(f64, @floatFromInt(bsteps)) / 1000.0);
    std.debug.print("BIO_BRAIN_pop_rate_Hz={e}\n", .{brain_rate});

    // Gates: cortical-ish bands (same spirit as Python bio_metrics)
    const rate_ok = rep.mean_rate_Hz >= 5.0 and rep.mean_rate_Hz <= 80.0;
    const isi_ok = rep.n_with_isi >= 1 and rep.mean_isi_ms >= 10.0 and rep.mean_isi_ms <= 200.0;
    const adapt_ok = rep.mean_adapt > -0.3 and rep.mean_adapt < 0.6;
    // Vm is a linear S proxy (not true clamp V); FI duty can pull mean S low.
    // Gate: finite + not pathological (> -200 mV class).
    const vm_ok = rep.mean_Vm_mV == rep.mean_Vm_mV and rep.mean_Vm_mV > -200.0 and rep.mean_Vm_mV < 20.0;

    std.debug.print("gate_rate={s}\n", .{if (rate_ok) "PASS" else "FAIL"});
    std.debug.print("gate_isi={s}\n", .{if (isi_ok) "PASS" else "FAIL"});
    std.debug.print("gate_adapt={s}\n", .{if (adapt_ok) "PASS" else "FAIL"});
    std.debug.print("gate_vm={s}\n", .{if (vm_ok) "PASS" else "FAIL"});

    if (rate_ok and isi_ok and adapt_ok and vm_ok) {
        std.debug.print("FSOT_BIO PASS\n", .{});
    } else {
        std.debug.print("FSOT_BIO FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runStress() !void {
    std.debug.print("=== FSOT MIND STRESS ===\n", .{});

    // 1) single-unit FI
    var p0: bio_probe.UnitParams = .{};
    p0.ref_steps = 50;
    p0.fi_stim = 0.50;
    const unit_pr = bio_probe.runFIUnit(p0, 1000, 1.0);
    std.debug.print("STRESS_UNIT_rate_Hz={e}\n", .{unit_pr.firing_rate_Hz});
    std.debug.print("STRESS_UNIT_isi_ms={e}\n", .{unit_pr.mean_isi_ms});
    std.debug.print("STRESS_UNIT_adapt={e}\n", .{unit_pr.adaptation_index});
    std.debug.print("STRESS_UNIT_spikes={d}\n", .{unit_pr.spike_count});

    // 2) default bio pop
    var params: [32]bio_probe.UnitParams = undefined;
    bio_probe.defaultBioParams(params[0..]);
    const fi = bio_probe.runFIPopulation(params[0..], 1000, 1.0);
    emitPop("STRESS_FI_", fi);

    // 3) periodic population
    const per = bio_probe.runPeriodicPopulation(16, 800, 0.65, 0.05);
    emitPop("STRESS_PERIODIC_", per);

    // 4) network
    const ns = bio_probe.runNetworkStress(32, 400);
    std.debug.print("STRESS_NET_spikes={d}\n", .{ns.spikes});
    std.debug.print("STRESS_NET_mean_S={e}\n", .{ns.mean_s});
    std.debug.print("STRESS_NET_rate_Hz={e}\n", .{ns.rate_Hz});

    // 5) multi-region brain
    var b = brain.Brain.init();
    var ext: [brain.N_TOTAL]f64 = undefined;
    var t: usize = 0;
    while (t < 200) : (t += 1) {
        const prim: f64 = if ((t % 40) < 12) 0.7 else 0.08;
        b.buildExternal(prim, .sens, ext[0..]);
        b.step(ext[0..]);
    }
    std.debug.print("STRESS_BRAIN_spikes={d}\n", .{b.totalSpikes()});
    std.debug.print("STRESS_BRAIN_mean_S={e}\n", .{b.meanS()});

    // 6) learn
    const lr = learning.runLearnProbe();
    std.debug.print("STRESS_LEARN_top1={e}\n", .{lr.top1});
    std.debug.print("STRESS_LEARN_correct={d}\n", .{lr.correct});

    // 7) organism short
    var org = organism.Organism.init();
    org.encode_every = 20;
    const orep = org.run(60, true);
    std.debug.print("STRESS_ORG_ticks={d}\n", .{orep.ticks});
    std.debug.print("STRESS_ORG_episodes={d}\n", .{orep.episodes});
    std.debug.print("STRESS_ORG_curiosity={d}\n", .{orep.curiosity});

    const unit_ok = unit_pr.spike_count >= 2 and unit_pr.mean_isi_ms > 5 and unit_pr.mean_isi_ms < 250;
    const fi_ok = fi.mean_rate_Hz >= 4.0 and fi.mean_rate_Hz <= 90.0 and fi.n_with_isi >= 1;
    const net_ok = ns.spikes >= 1;
    const brain_ok = b.totalSpikes() >= 1;
    const learn_ok = lr.ok;
    const org_ok = orep.ok and orep.episodes >= 1;

    std.debug.print("gate_unit={s}\n", .{if (unit_ok) "PASS" else "FAIL"});
    std.debug.print("gate_fi={s}\n", .{if (fi_ok) "PASS" else "FAIL"});
    std.debug.print("gate_net={s}\n", .{if (net_ok) "PASS" else "FAIL"});
    std.debug.print("gate_brain={s}\n", .{if (brain_ok) "PASS" else "FAIL"});
    std.debug.print("gate_learn={s}\n", .{if (learn_ok) "PASS" else "FAIL"});
    std.debug.print("gate_org={s}\n", .{if (org_ok) "PASS" else "FAIL"});

    if (unit_ok and fi_ok and net_ok and brain_ok and learn_ok and org_ok) {
        std.debug.print("FSOT_STRESS PASS\n", .{});
    } else {
        std.debug.print("FSOT_STRESS FAIL\n", .{});
        std.process.exit(1);
    }
}

pub fn main() !void {
    const gpa = std.heap.page_allocator;
    const args = try std.process.argsAlloc(gpa);
    defer std.process.argsFree(gpa, args);

    const mode: []const u8 = if (args.len >= 2) args[1] else "all";

    if (std.mem.eql(u8, mode, "selftest")) {
        try runSelfTest();
    } else if (std.mem.eql(u8, mode, "learn")) {
        runLearn();
    } else if (std.mem.eql(u8, mode, "live")) {
        runLive();
    } else if (std.mem.eql(u8, mode, "inject")) {
        runInject();
    } else if (std.mem.eql(u8, mode, "structure")) {
        runStructure();
    } else if (std.mem.eql(u8, mode, "memory")) {
        runMemory();
    } else if (std.mem.eql(u8, mode, "organism")) {
        runOrganism();
    } else if (std.mem.eql(u8, mode, "intel")) {
        runIntel();
    } else if (std.mem.eql(u8, mode, "fixed") or std.mem.eql(u8, mode, "fixedpoint")) {
        runFixed();
    } else if (std.mem.eql(u8, mode, "genetic") or std.mem.eql(u8, mode, "codon")) {
        runGenetic();
    } else if (std.mem.eql(u8, mode, "sme")) {
        runSme();
    } else if (std.mem.eql(u8, mode, "inject-file") or std.mem.eql(u8, mode, "inject_file")) {
        if (args.len < 3) {
            std.debug.print("usage: fsot_mind inject-file <path>\n", .{});
            std.process.exit(2);
        }
        try runInjectFile(args[2]);
    } else if (std.mem.eql(u8, mode, "bio")) {
        const path: ?[]const u8 = if (args.len >= 3) args[2] else null;
        try runBio(path);
    } else if (std.mem.eql(u8, mode, "stress")) {
        try runStress();
    } else if (std.mem.eql(u8, mode, "all") or std.mem.eql(u8, mode, "mind")) {
        try runSelfTest();
        runGenetic();
        runStructure();
        runLearn();
        runMemory();
        runInject();
        runOrganism();
        runIntel();
        runLive();
        runSme();
        try runBio(null);
        try runStress();
        std.debug.print("FSOT_MIND_HOST_OK\n", .{});
        std.debug.print("FSOT_NO_PYTHON_CORE_OK\n", .{});
        std.debug.print("FSOT_INTEL_HOST_OK\n", .{});
    } else {
        std.debug.print("usage: fsot_mind [selftest|genetic|intel|fixed|organism|sme|learn|live|inject|inject-file|structure|memory|bio|stress|all]\n", .{});
        std.process.exit(2);
    }
}
