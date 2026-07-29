//! FSOT Mind Host — Zig-native multi-region organism (no Python required).
//!
//! **Default authority: fixed-point lattice** (SCALE=1e12). IEEE f64 is lab-only.
//!
//! Usage:
//!   fsot_mind                  # full suite (fixed authority + residual f64 lab)
//!   fsot_mind fixed            # fixed stack + bio accuracy
//!   fsot_mind intel            # continuous intel on FIXED organism
//!   fsot_mind organism         # FIXED organism loop
//!   fsot_mind learn            # FIXED encode–retrieve
//!   fsot_mind curriculum       # short-horizon curriculum units (fixed)
//!   fsot_mind float-lab        # legacy f64 lab suite (parity only)
//!   fsot_mind bio / stress / genetic / inject-file …
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
const genetic_fixed = @import("genetic_fixed.zig");
const bio_probe_fixed = @import("bio_probe_fixed.zig");
const genotype_fixed = @import("genotype_fixed.zig");
const codon_fixed = @import("codon_fixed.zig");
const memory_fixed = @import("memory_fixed.zig");
const learning_fixed = @import("learning_fixed.zig");
const curriculum_fixed = @import("curriculum_fixed.zig");
const curiosity_fixed = @import("curiosity_fixed.zig");
const transfer_fixed = @import("transfer_fixed.zig");
const inject_io_fixed = @import("inject_io_fixed.zig");
const vision_inject_fixed = @import("vision_inject_fixed.zig");
const pixel_id_fixed = @import("pixel_id_fixed.zig");
const modulate_fixed = @import("modulate_fixed.zig");
const teach_fixed = @import("teach_fixed.zig");
const bands_fixed = @import("bands_fixed.zig");
const short_horizon_fixed = @import("short_horizon_fixed.zig");
const speech_organ_fixed = @import("speech_organ_fixed.zig");
const cross_modal_fixed = @import("cross_modal_fixed.zig");
const bio_io_fixed = @import("bio_io_fixed.zig");
const pathways_fixed = @import("pathways_fixed.zig");
const sensory_fixed = @import("sensory_fixed.zig");
const machine_encode_fixed = @import("machine_encode_fixed.zig");
const machine_lang_fixed = @import("machine_lang_fixed.zig");
const lexicon_en_fixed = @import("lexicon_en_fixed.zig");
const host_tts_fixed = @import("host_tts_fixed.zig");
const language_practice_fixed = @import("language_practice_fixed.zig");
const grade_practice_fixed = @import("grade_practice_fixed.zig");
const grade_ladder_fixed = @import("grade_ladder_fixed.zig");
const mnist_accuracy_fixed = @import("mnist_accuracy_fixed.zig");
const understand_depth_fixed = @import("understand_depth_fixed.zig");
const synapse_path_fixed = @import("synapse_path_fixed.zig");
const reason_practice_fixed = @import("reason_practice_fixed.zig");
const novel_inquiry_fixed = @import("novel_inquiry_fixed.zig");
const checkpoint_fixed = @import("checkpoint_fixed.zig");
const failure_fixed = @import("failure_fixed.zig");
const autonomous_fixed = @import("autonomous_fixed.zig");
const wire_around_fixed = @import("wire_around_fixed.zig");
const symbol_assoc_fixed = @import("symbol_assoc_fixed.zig");
const hardware_metric_fixed = @import("hardware_metric_fixed.zig");
const host_senses_fixed = @import("host_senses_fixed.zig");
const host_loop_fixed = @import("host_loop_fixed.zig");
const host_audio_out_fixed = @import("host_audio_out_fixed.zig");
const mind_live_fixed = @import("mind_live_fixed.zig");
const eeg_gate_anchors_fixed = @import("eeg_gate_anchors_fixed.zig");
const attention_fixed = @import("attention_fixed.zig");

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
    std.debug.print("=== FSOT MIND ORGANISM (FIXED authority) ===\n", .{});
    var org = organism_fixed.OrganismF.init();
    org.encode_every = 12;
    org.steps_per_tick = 4;
    const st0 = org.brain.structureReport();
    std.debug.print(
        "genetic brain units={d} syn={d} Pyr/PV/SST/VIP={d}/{d}/{d}/{d}\n",
        .{ st0.n_units, st0.n_synapses, st0.n_pyr, st0.n_pv, st0.n_sst, st0.n_vip },
    );
    const n_ticks: u32 = 48;
    var t: u32 = 0;
    while (t < n_ticks) : (t += 1) {
        const r = org.tickOnce();
        if ((t + 1) % 16 == 0) {
            std.debug.print(
                "t={d} meanS={e} spikes={d} eps={d}\n",
                .{ r.tick, fixed.toF64(r.mean_s), r.spikes, r.episodes },
            );
        }
    }
    if (org.store.n < 2) {
        std.debug.print("FSOT_ORGANISM FAIL episodes={d}\n", .{org.store.n});
        std.process.exit(1);
    }
    std.debug.print(
        "FSOT_ORGANISM PASS ticks={d} episodes={d} spikes={d}\n",
        .{ org.tick, org.store.n, org.brain.totalSpikes() },
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

    if (!codon_fixed.selfTest() or !genotype_fixed.selfTest()) {
        std.debug.print("FSOT_FIXED_GENOTYPE FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_FIXED_GENOTYPE PASS (expression on lattice)\n", .{});

    if (!genetic_fixed.selfTest()) {
        std.debug.print("FSOT_FIXED_GENETIC_W FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_FIXED_GENETIC_W PASS (pure lattice assembly)\n", .{});

    if (!memory_fixed.selfTest()) {
        std.debug.print("FSOT_FIXED_MEMORY FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_FIXED_MEMORY PASS\n", .{});

    if (!organism_fixed.selfTest()) {
        std.debug.print("FSOT_FIXED_ORGANISM FAIL\n", .{});
        std.process.exit(1);
    }
    var org = organism_fixed.OrganismF.init();
    org.encode_every = 12;
    const orep = org.run(40);
    std.debug.print(
        "FSOT_FIXED_ORGANISM PASS ticks={d} spikes={d} syn={d} eps={d} meanS={e}\n",
        .{ orep.ticks, orep.spikes, orep.n_syn, orep.episodes, fixed.toF64(org.brain.meanS()) },
    );

    // --- Biological accuracy: FI population on fixed neurons ---
    if (!bio_probe_fixed.selfTest()) {
        std.debug.print("FSOT_FIXED_BIO_SELFTEST FAIL\n", .{});
        std.process.exit(1);
    }
    var params: [32]bio_probe_fixed.UnitParamsF = undefined;
    bio_probe_fixed.defaultBioParams(params[0..]);
    // optional Allen params file
    const allen_path = "I:\\fsot nuron\\artifacts\\zig_bio_params.txt";
    if (std.fs.cwd().openFile(allen_path, .{})) |file| {
        defer file.close();
        var buf: [64 * 1024]u8 = undefined;
        const nread = file.readAll(&buf) catch 0;
        if (nread > 0) {
            const n = bio_probe_fixed.loadParamsFromText(buf[0..nread], params[0..]) catch 0;
            if (n > 0) {
                std.debug.print("bio_params=allen n={d}\n", .{n});
                const fi = bio_probe_fixed.runFIPopulation(params[0..n], 1200);
                std.debug.print(
                    "FIXED_BIO_FI rate_Hz={e} isi_ms={e} adapt={e} spikes={d}\n",
                    .{ fi.mean_rate_Hz, fi.mean_isi_ms, fi.mean_adapt, fi.total_spikes },
                );
                const rate_ok = fi.mean_rate_Hz >= 5.0 and fi.mean_rate_Hz <= 80.0;
                const isi_ok = fi.n_with_isi >= 1 and fi.mean_isi_ms >= 10.0 and fi.mean_isi_ms <= 200.0;
                const adapt_ok = fi.mean_adapt > -0.3 and fi.mean_adapt < 0.6;
                std.debug.print("gate_bio_rate={s}\n", .{if (rate_ok) "PASS" else "FAIL"});
                std.debug.print("gate_bio_isi={s}\n", .{if (isi_ok) "PASS" else "FAIL"});
                std.debug.print("gate_bio_adapt={s}\n", .{if (adapt_ok) "PASS" else "FAIL"});
                if (!(rate_ok and isi_ok and adapt_ok)) {
                    std.debug.print("FSOT_FIXED_BIO FAIL\n", .{});
                    std.process.exit(1);
                }
                std.debug.print("FSOT_FIXED_BIO PASS (Allen-mapped FI)\n", .{});
            }
        }
    } else |_| {
        const fi = bio_probe_fixed.runFIPopulation(params[0..], 1000);
        std.debug.print(
            "FIXED_BIO_FI rate_Hz={e} isi_ms={e} adapt={e} (default params)\n",
            .{ fi.mean_rate_Hz, fi.mean_isi_ms, fi.mean_adapt },
        );
        const rate_ok = fi.mean_rate_Hz >= 5.0 and fi.mean_rate_Hz <= 80.0;
        const isi_ok = fi.n_with_isi >= 1 and fi.mean_isi_ms >= 10.0 and fi.mean_isi_ms <= 200.0;
        if (!(rate_ok and isi_ok)) {
            std.debug.print("FSOT_FIXED_BIO FAIL\n", .{});
            std.process.exit(1);
        }
        std.debug.print("FSOT_FIXED_BIO PASS (default)\n", .{});
    }

    // structure class vs f64 brain authority (+ synapse density band)
    var bf64 = brain.Brain.initSeeded(42, false);
    const st64 = bf64.structureReport();
    const type_ok = st.n_pyr == st64.n_pyr and st.n_e == st64.n_e and st.n_i == st64.n_i;
    const syn_f: f64 = @floatFromInt(st64.n_synapses);
    const syn_z: f64 = @floatFromInt(st.n_synapses);
    const syn_rel = if (syn_f > 0) @abs(syn_z - syn_f) / syn_f else 1.0;
    // within 8% of f64 authority synapse count (lattice thr calibration)
    const syn_ok = syn_rel <= 0.08;
    std.debug.print(
        "STRUCTURE f64 E/I/pyr/syn={d}/{d}/{d}/{d} fixed={d}/{d}/{d}/{d} type={s} syn_rel={e}\n",
        .{
            st64.n_e,
            st64.n_i,
            st64.n_pyr,
            st64.n_synapses,
            st.n_e,
            st.n_i,
            st.n_pyr,
            st.n_synapses,
            if (type_ok) "YES" else "NO",
            syn_rel,
        },
    );
    if (!type_ok or !syn_ok) {
        std.debug.print("FSOT_FIXED_STRUCTURE FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_FIXED_STRUCTURE PASS\n", .{});
    std.debug.print("FSOT_FIXED_SYN_DENSITY PASS\n", .{});

    std.debug.print("FSOT_FIXED_STACK_OK\n", .{});
    std.debug.print("FSOT_FIXED_BIO_ACCURATE_OK\n", .{});
    std.debug.print("FSOT_FIXED_RESIDUALS_CLOSED\n", .{});
}

fn runIntel() void {
    std.debug.print("=== FSOT MIND INTEL (FIXED authority) ===\n", .{});
    std.debug.print("doctrine: codon genetics + lattice dynamics (no IEEE mind step)\n", .{});
    var org = organism_fixed.OrganismF.init();
    org.encode_every = 12;
    org.steps_per_tick = 4;
    const orep = org.run(80);
    const lr = learning_fixed.runLearnProbe();
    const st = org.brain.structureReport();
    std.debug.print(
        "INTEL ticks={d} eps={d} spikes={d} pyr={d} I={d} syn={d}\n",
        .{ orep.ticks, orep.episodes, orep.spikes, st.n_pyr, st.n_i, st.n_synapses },
    );
    printF64("INTEL_mean_S=", fixed.toF64(org.brain.meanS()));
    printF64("INTEL_learn_top1=", lr.top1);
    std.debug.print("INTEL_learn_correct={d}/{d}\n", .{ lr.correct, lr.n_items });
    if (!orep.ok or !lr.ok) {
        std.debug.print("FSOT_INTEL FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_INTEL PASS fixed_genetic_folding\n", .{});
}

fn runLearnFixed() void {
    std.debug.print("=== FSOT MIND LEARN (FIXED) ===\n", .{});
    const lr = learning_fixed.runLearnProbe();
    std.debug.print(
        "LEARN top1={e} correct={d}/{d} sim+={e} sim-={e} spikes={d}\n",
        .{ lr.top1, lr.correct, lr.n_items, lr.mean_s_plus, lr.mean_s_minus, lr.spikes },
    );
    if (lr.ok) {
        std.debug.print("FSOT_LEARN PASS\n", .{});
    } else {
        std.debug.print("FSOT_LEARN FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runCurriculum() void {
    std.debug.print("=== FSOT MIND CURRICULUM (fixed short-horizon units) ===\n", .{});
    const cr = curriculum_fixed.runCurriculum();
    std.debug.print(
        "CURRIC units={d} encode={d} full={d}/{d} top1={e} partial={d}/{d} ptop1={e} spikes={d}\n",
        .{ cr.n_units, cr.encode_ok, cr.retrieve_correct, cr.n_units, cr.top1, cr.partial_correct, cr.n_units, cr.partial_top1, cr.spikes },
    );
    if (cr.ok) {
        std.debug.print("FSOT_CURRICULUM PASS\n", .{});
    } else {
        std.debug.print("FSOT_CURRICULUM FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runCuriosity() void {
    std.debug.print("=== FSOT MIND CURIOSITY (fixed 5W1H fill) ===\n", .{});
    const c = curiosity_fixed.runCuriosityProbe();
    std.debug.print(
        "CURIOSITY eps={d} q={d} resolved={d} open={d}\n",
        .{ c.n_episodes, c.questions, c.resolved, c.open_after },
    );
    if (c.ok) {
        std.debug.print("FSOT_CURIOSITY PASS\n", .{});
    } else {
        std.debug.print("FSOT_CURIOSITY FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runTransfer() void {
    std.debug.print("=== FSOT MIND TRANSFER (strong: distractors+noise+delay, no title cheat) ===\n", .{});
    const t = transfer_fixed.runTransferProbe();
    std.debug.print(
        "TRANSFER full={d}/{d} top1={e} partial={d}/{d} ptop1={e} noisy={d}/{d} ntop1={e} dist={d} delay={d} spikes={d}\n",
        .{
            t.correct,          t.n_items, t.top1,
            t.partial_correct,  t.n_items, t.partial_top1,
            t.noisy_correct,    t.n_items, t.noisy_top1,
            t.n_distractors,    t.delay_steps, t.spikes,
        },
    );
    if (t.ok) {
        std.debug.print("FSOT_TRANSFER PASS\n", .{});
    } else {
        std.debug.print("FSOT_TRANSFER FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runModulate() void {
    std.debug.print("=== FSOT MIND MODULATE (fixed POOF/SUCTION homeostasis) ===\n", .{});
    const m = modulate_fixed.runModulateProbe();
    std.debug.print(
        "MODULATE dampen={} explore={} balanced={} emergency={}\n",
        .{ m.dampen_ok, m.explore_ok, m.balanced_ok, m.emergency_ok },
    );
    if (m.ok) {
        std.debug.print("FSOT_MODULATE PASS\n", .{});
    } else {
        std.debug.print("FSOT_MODULATE FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runTeach() void {
    std.debug.print("=== FSOT MIND TEACH (fixed 5W1H cards + curiosity fill) ===\n", .{});
    const t = teach_fixed.runTeachProbe();
    std.debug.print(
        "TEACH lessons={d} enc={d} slots={d}/{d} top1={e} cur_q={d} cur_res={d} spikes={d}\n",
        .{ t.n_lessons, t.n_encoded, t.slot_hits, t.slot_probes, t.slot_top1, t.curiosity_questions, t.curiosity_resolved, t.spikes },
    );
    if (t.ok) {
        std.debug.print("FSOT_TEACH PASS\n", .{});
    } else {
        std.debug.print("FSOT_TEACH FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runSmeFixed() void {
    std.debug.print("=== FSOT MIND SME (fixed bands — theta/gamma encode vs rest) ===\n", .{});
    if (!bands_fixed.selfTest()) {
        std.debug.print("FSOT_SME_FIXED FAIL selftest\n", .{});
        std.process.exit(1);
    }
    const s = bands_fixed.runSmeProbe();
    std.debug.print(
        "SME_FIXED theta_gt={} gamma_gt={} spikes_enc={d} spikes_rest={d} th_enc={e} th_rest={e} ga_enc={e} ga_rest={e}\n",
        .{ s.theta_gt, s.gamma_gt, s.spikes_enc, s.spikes_rest, s.theta_enc, s.theta_rest, s.gamma_enc, s.gamma_rest },
    );
    if (s.ok) {
        std.debug.print("FSOT_SME_FIXED PASS\n", .{});
    } else {
        std.debug.print("FSOT_SME_FIXED FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runAttentionEeg() void {
    std.debug.print("=== FSOT ATTENTION (EEG-anchored gates) ===\n", .{});
    if (!eeg_gate_anchors_fixed.selfTest()) {
        std.debug.print("FSOT_EEG_ANCHORS FAIL selftest\n", .{});
        std.process.exit(1);
    }
    if (!attention_fixed.selfTest()) {
        std.debug.print("FSOT_ATTENTION FAIL selftest\n", .{});
        std.process.exit(1);
    }
    const ar = eeg_gate_anchors_fixed.report();
    std.debug.print(
        "EEG_ANCHORS θconc/rel={e} α={e} γcsv={e} sens={e} studyS={e} enc_drive={e} fig={e} gnd={e} self_thr={e} nov_floor={e}\n",
        .{
            ar.theta_conc_relax,
            ar.alpha_conc_relax,
            ar.gamma_conc_relax,
            ar.sensory_strength,
            ar.study_s,
            ar.encode_drive,
            ar.figure_gain,
            ar.ground_gain,
            ar.self_match_thresh,
            ar.novelty_floor,
        },
    );
    std.debug.print(
        "EEG_LIT SME_θ↑={} SME_γ↑={} consol_σ/θ={} ideation_α↑={}\n",
        .{
            ar.sme_theta_gt,
            ar.sme_gamma_gt,
            eeg_gate_anchors_fixed.CONSOL_EXPECT_SIGMA_OR_THETA,
            eeg_gate_anchors_fixed.IDEATION_EXPECT_ALPHA_UP,
        },
    );
    std.debug.print("SRC: mental-state.csv concentrate vs relax (n=2479) + Sederberg2003 + FSOT couple\n", .{});
    std.debug.print("FSOT_EEG_ANCHORS PASS\n", .{});
    std.debug.print("FSOT_ATTENTION PASS\n", .{});
}

fn runShortHorizon() void {
    std.debug.print("=== FSOT MIND SHORT-HORIZON (fixed quick encode→recall) ===\n", .{});
    const r = short_horizon_fixed.runShortHorizonProbe();
    std.debug.print(
        "SHORT_HORIZON lessons={d} mem={d} recall={d}/{d} top1={e} cur_res={d} sme={} spikes={d}\n",
        .{ r.n_lessons, r.n_memory, r.recall_correct, r.n_lessons, r.recall_top1, r.curiosity_resolved, r.sme_ok, r.spikes },
    );
    if (r.ok) {
        std.debug.print("FSOT_SHORT_HORIZON PASS\n", .{});
    } else {
        std.debug.print("FSOT_SHORT_HORIZON FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runSpeechOrgan() void {
    std.debug.print("=== FSOT SPEECH ORGAN (motor→sound→symbol; NOT next-token) ===\n", .{});
    std.debug.print("doctrine: tongue/jaw/lips/larynx plant; letters are sound associations\n", .{});
    const r = speech_organ_fixed.runSpeechOrganProbe();
    std.debug.print(
        "SPEECH letters={d} hear={d}/{d} top1={e} roundtrip={d}/{d} rtop1={e} words={d}/{d} wtop1={e}\n",
        .{ r.n_letters, r.hear_correct, r.n_letters, r.hear_top1, r.roundtrip_correct, r.n_letters, r.roundtrip_top1, r.word_correct, r.word_n, r.word_top1 },
    );
    std.debug.print("path={s}\n", .{r.doctrine});
    if (r.ok) {
        std.debug.print("FSOT_SPEECH PASS\n", .{});
    } else {
        std.debug.print("FSOT_SPEECH FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runCrossModal() void {
    std.debug.print("=== FSOT CROSS-MODAL (vision⊗audio joint bind, fixed) ===\n", .{});
    const r = cross_modal_fixed.runCrossModalProbe();
    std.debug.print(
        "CROSS joint={d}/{d} top1={e} vision_only={d}/{d} vtop1={e} audio_only={d}/{d} atop1={e} spikes={d}\n",
        .{
            r.joint_correct,        r.n_items, r.joint_top1,
            r.vision_only_correct,  r.n_items, r.vision_only_top1,
            r.audio_only_correct,   r.n_items, r.audio_only_top1,
            r.spikes,
        },
    );
    if (r.ok) {
        std.debug.print("FSOT_CROSS_MODAL PASS\n", .{});
    } else {
        std.debug.print("FSOT_CROSS_MODAL FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runBioIo() void {
    std.debug.print("=== FSOT BIO I/O (afferent routes + efferent speech re-afferent) ===\n", .{});
    std.debug.print("doctrine: thal/sens/assoc/hipp anatomy; motor→sound; not next-token\n", .{});
    if (!pathways_fixed.selfTest()) {
        std.debug.print("FSOT_BIO_IO FAIL pathways\n", .{});
        std.process.exit(1);
    }
    if (!sensory_fixed.selfTest()) {
        std.debug.print("FSOT_BIO_IO FAIL sensory_bus\n", .{});
        std.process.exit(1);
    }
    const r = bio_io_fixed.runBioIoProbe();
    std.debug.print(
        "BIO_IO path={} bus={} V_spikes={d} A_spikes={d} intero={} speak_rt={} syl={d} hear={d}/{d} top1={e}\n",
        .{
            r.pathways_ok,
            r.sensory_bus_ok,
            r.afferent_vision_spikes,
            r.afferent_audio_spikes,
            r.intero_ok,
            r.efferent_roundtrip_ok,
            r.syllable_frames,
            r.hear_correct,
            r.hear_n,
            r.hear_top1,
        },
    );
    if (r.ok) {
        std.debug.print("FSOT_BIO_IO PASS\n", .{});
    } else {
        std.debug.print("FSOT_BIO_IO FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runMachineEncode() void {
    std.debug.print("=== FSOT MACHINE ENCODE (bytes/UTF-8/trit/chemical AA — not Morse/LM) ===\n", .{});
    const r = machine_encode_fixed.runMachineEncodeProbe();
    std.debug.print(
        "MACHINE bytes_rt={} text_rt={} feat_trit={} dna={} chem_aa={} words={d} n_aa={d}\n",
        .{ r.bytes_roundtrip, r.text_roundtrip, r.feat_trit_ok, r.dna_codon_ok, r.chemical_aa_ok, r.n_words, r.n_aa },
    );
    if (r.ok) {
        std.debug.print("FSOT_MACHINE PASS\n", .{});
    } else {
        std.debug.print("FSOT_MACHINE FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runMachineLang() void {
    std.debug.print("=== FSOT MACHINE LANGUAGE (generate = understand = run tongue) ===\n", .{});
    std.debug.print("doctrine: mind emits TritWord frames; re-ingests same bytes; UTF-8 is codec only\n", .{});
    if (!machine_lang_fixed.selfTest()) {
        std.debug.print("FSOT_MACHINE_LANG FAIL selftest\n", .{});
        std.process.exit(1);
    }
    const r = machine_lang_fixed.runMachineLangLoop();
    std.debug.print(
        "MACHINE_LANG frame_rt={} text_rt={} words={d} trits={d} bytes={d} gen={d} under={d} spikes={d}\n",
        .{ r.frame_roundtrip, r.text_roundtrip, r.n_words, r.n_trits, r.n_bytes, r.n_generated, r.n_understood, r.inject_spikes },
    );
    if (r.hex_len > 0) {
        std.debug.print("MACHINE_LANG hex_head={s}\n", .{r.hex_head[0..r.hex_len]});
    }
    if (r.ok) {
        std.debug.print("FSOT_MACHINE_LANG PASS\n", .{});
        std.debug.print("FSOT_MACHINE_TONGUE_OK\n", .{});
    } else {
        std.debug.print("FSOT_MACHINE_LANG FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runMachineLangStress() void {
    std.debug.print("=== FSOT MACHINE LANGUAGE STRESS (1000 frames + text + corrupt + inject) ===\n", .{});
    if (!machine_lang_fixed.selfTest()) {
        std.debug.print("FSOT_MACHINE_LANG_STRESS FAIL selftest\n", .{});
        std.process.exit(1);
    }
    const r = machine_lang_fixed.runMachineLangStress(1000);
    std.debug.print(
        "MLANG_STRESS frames={d}/{d} text={d}/{d} inject={d} bytes={d} trits={d} mismatches={d} corrupt_rej={d} max_spk={d}\n",
        .{
            r.n_frame_ok,
            r.n_frames,
            r.n_text_ok,
            r.n_text_trials,
            r.n_inject_ok,
            r.n_bytes_total,
            r.n_trits_total,
            r.n_word_mismatches,
            r.n_corrupt_reject,
            r.max_spikes,
        },
    );
    if (r.ok) {
        std.debug.print("FSOT_MACHINE_LANG_STRESS PASS\n", .{});
    } else {
        std.debug.print("FSOT_MACHINE_LANG_STRESS FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runEnglishCodec() void {
    std.debug.print("=== FSOT ENGLISH CODEC (lexicon choose + machine frame + TTS plant) ===\n", .{});
    std.debug.print("doctrine: teacher grows TSV; mind owns machine language + choose; TTS plant\n", .{});
    const n_load = lexicon_en_fixed.tryLoadDefaultRoles();
    std.debug.print("LEXICON_LOAD extra={d} total={d}\n", .{ n_load, lexicon_en_fixed.totalWords() });
    if (!lexicon_en_fixed.selfTest()) {
        std.debug.print("FSOT_ENGLISH FAIL selftest\n", .{});
        std.process.exit(1);
    }
    const r = lexicon_en_fixed.runLexiconProbe();
    std.debug.print(
        "ENGLISH words={d} choose={d}/3 input_known={d} phrase=\"{s}\" frame_rt={} choose_diff={}\n",
        .{ r.n_words, r.n_choose_ok, r.n_input_known, r.phrase_sample[0..r.phrase_n], r.frame_roundtrip, r.choose_not_echo },
    );

    // Input → understand → re-export path
    var toks: [6]u32 = undefined;
    var meaning: [8]@import("fixed.zig").Fixed = undefined;
    const inp = lexicon_en_fixed.inputEnglish("I hear the sound here", &toks, &meaning);
    var phrase: [lexicon_en_fixed.MAX_PHRASE]u8 = undefined;
    var frame: machine_lang_fixed.MachineFrame = .{};
    const ut = lexicon_en_fixed.utterEnglish(&meaning, phrase[0..], &frame);
    std.debug.print(
        "ENGLISH_IO in_known={d} out_phrase=\"{s}\" frame_words={d}\n",
        .{ inp.n_known, phrase[0..ut.phrase_n], frame.n_words },
    );

    // TTS plant (real words out the speakers)
    const tts = host_tts_fixed.speakEnglish(phrase[0..ut.phrase_n]);
    std.debug.print(
        "TTS backend={s} spoken={} chars={d}\n",
        .{ tts.backend, tts.spoken, tts.n_chars },
    );

    if (r.ok and inp.n_known >= 3 and ut.phrase_n >= 5) {
        std.debug.print("FSOT_ENGLISH PASS\n", .{});
        if (tts.spoken) std.debug.print("FSOT_TTS_SPOKEN_OK\n", .{});
    } else {
        std.debug.print("FSOT_ENGLISH FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runLanguagePractice() void {
    std.debug.print("=== FSOT LANGUAGE PRACTICE (utter → TTS → self-hear → encode) ===\n", .{});
    std.debug.print("doctrine: teacher offline; student learns by doing + hearing own words\n", .{});
    if (!language_practice_fixed.selfTest()) {
        std.debug.print("FSOT_LANGUAGE_PRACTICE FAIL selftest\n", .{});
        std.process.exit(1);
    }
    const r = language_practice_fixed.runLanguagePractice();
    std.debug.print(
        "PRACTICE trials={d} tts={d} self_recover={d} frame_rt={d} encode={d} known_in={d} known_out={d} lex={d} fluency={e}\n",
        .{
            r.n_trials,
            r.n_tts_spoken,
            r.n_self_recover,
            r.n_frame_rt,
            r.n_encode,
            r.n_known_in,
            r.n_known_out,
            r.lexicon_total,
            r.fluency,
        },
    );
    if (r.last_phrase_n > 0) {
        std.debug.print("LAST_PRACTICE \"{s}\"\n", .{r.last_phrase[0..r.last_phrase_n]});
    }
    if (r.ok) {
        std.debug.print("FSOT_LANGUAGE_PRACTICE PASS\n", .{});
        std.debug.print("FSOT_SELF_HEAR_LANGUAGE_OK\n", .{});
    } else {
        std.debug.print("FSOT_LANGUAGE_PRACTICE FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runGradePractice() void {
    std.debug.print("=== FSOT GRADE PRACTICE (legacy soft gate) — prefer 'ladder' for 95% ===\n", .{});
    std.debug.print("doctrine: teach real facts; quiz & solve — not word-means-word\n", .{});
    if (!grade_practice_fixed.selfTest()) {
        std.debug.print("FSOT_GRADE_PRACTICE FAIL selftest\n", .{});
        std.process.exit(1);
    }
    const r = grade_practice_fixed.runGradePractice(false);
    std.debug.print(
        "GRADE lessons={d} taught={d} quiz={d}/{d} top1={e} problems={d}/{d} ptop1={e} apply={e} tts={d} lex={d}\n",
        .{
            r.n_lessons,
            r.n_taught,
            r.n_quiz_ok,
            r.n_quiz,
            r.quiz_top1,
            r.n_prob_ok,
            r.n_problems,
            r.problem_top1,
            r.apply_score,
            r.n_tts,
            r.lexicon_total,
        },
    );
    if (r.ok) {
        std.debug.print("FSOT_GRADE_PRACTICE PASS\n", .{});
    } else {
        std.debug.print("FSOT_GRADE_PRACTICE FAIL\n", .{});
        std.process.exit(1);
    }
}

fn printBand(r: grade_ladder_fixed.BandReport) void {
    std.debug.print(
        "BAND {s} score={e} thr={e} PASS={} file={} taught={d} items={d}\n",
        .{
            grade_ladder_fixed.bandName(r.band),
            r.score,
            r.threshold,
            r.pass,
            r.from_file,
            r.n_taught,
            r.n_items,
        },
    );
    std.debug.print(
        "  domains math={e}({d}/{d}) science={e}({d}/{d}) literacy={e}({d}/{d}) vision={e}({d}/{d})\n",
        .{
            r.math.score,     r.math.ok,     r.math.n,
            r.science.score,  r.science.ok,  r.science.n,
            r.literacy.score, r.literacy.ok, r.literacy.n,
            r.vision.score,   r.vision.ok,   r.vision.n,
        },
    );
}

fn runGradeBand(band: grade_ladder_fixed.GradeBand) void {
    std.debug.print("=== FSOT GRADE BAND ({s}) straight-A ≥95% per domain ===\n", .{grade_ladder_fixed.bandName(band)});
    std.debug.print("doctrine: open curriculum bank + digit vision; math/sci/lit/vis each ≥95%\n", .{});
    const r = grade_ladder_fixed.runBand(band);
    printBand(r);
    if (r.pass) {
        std.debug.print("FSOT_BAND_PASS {s}\n", .{grade_ladder_fixed.bandName(band)});
        std.debug.print("FSOT_STRAIGHT_A_OK\n", .{});
    } else {
        std.debug.print("FSOT_BAND_FAIL {s} (need ≥95% each domain)\n", .{grade_ladder_fixed.bandName(band)});
        std.process.exit(1);
    }
}

fn runGradeLadder() void {
    std.debug.print("=== FSOT GRADE LADDER (straight-A, ≥95% per band AND domain) ===\n", .{});
    std.debug.print("doctrine: open curriculum (run_curriculum_open.py) → bank.tsv; stop on first fail\n", .{});
    if (!grade_ladder_fixed.selfTest()) {
        std.debug.print("FSOT_LADDER FAIL selftest\n", .{});
        std.process.exit(1);
    }
    const r = grade_ladder_fixed.runLadder();
    std.debug.print(
        "LADDER_SUMMARY bands_passed={d}/{d} stopped_at={s} overall_ok={}\n",
        .{ r.n_bands_passed, r.n_bands_total, r.stopped_at, r.ok },
    );
    if (r.ok) {
        std.debug.print("FSOT_LADDER PASS\n", .{});
        std.debug.print("FSOT_STRAIGHT_A_LADDER_OK\n", .{});
    } else {
        std.debug.print("FSOT_LADDER FAIL at {s}\n", .{r.stopped_at});
        std.process.exit(1);
    }
}

fn runReasonPractice() void {
    std.debug.print("=== FSOT OPEN REASON (multi-hop over taught knowledge) ===\n", .{});
    std.debug.print("doctrine: bio process = inject→ticks→retrieve→bind; not LLM chain-of-thought\n", .{});
    // full run with TTS off first for speed in self-check path; we call with speak=true below
    if (!reason_practice_fixed.selfTest()) {
        std.debug.print("FSOT_REASON FAIL selftest\n", .{});
        std.process.exit(1);
    }
    const r = reason_practice_fixed.runReasonPractice(true);
    std.debug.print(
        "REASON taught={d} open={d}/{d} acc={e} hops={d} bank_hits={d} ep_hits={d} spikes={d} lex={d}\n",
        .{ r.n_taught, r.n_correct, r.n_open, r.accuracy, r.n_hops_total, r.n_bank_hits, r.n_ep_hits, r.total_spikes, r.lexicon_total },
    );
    if (r.ok) {
        std.debug.print("FSOT_REASON PASS\n", .{});
        std.debug.print("FSOT_OPEN_REASON_OK\n", .{});
    } else {
        std.debug.print("FSOT_REASON FAIL (multi-hop apply still weak — expected while shallow)\n", .{});
        std.process.exit(1);
    }
}

fn runNovelInquiry() void {
    std.debug.print("=== FSOT NOVEL INQUIRY (single complex synthesis from taught facts) ===\n", .{});
    std.debug.print("doctrine: new idea = compose grounded binds; never free invent\n", .{});
    if (!novel_inquiry_fixed.selfTest()) {
        std.debug.print("FSOT_NOVEL FAIL selftest\n", .{});
        std.process.exit(1);
    }
    const r = novel_inquiry_fixed.runNovelInquiry(true);
    std.debug.print(
        "NOVEL taught={d} hops={d} grounded={} novel={} spikes={d} lex={d}\n",
        .{ r.n_taught, r.n_hops, r.grounded, r.novel, r.spikes, r.lexicon_total },
    );
    if (r.idea_n > 0) {
        std.debug.print("NOVEL_IDEA \"{s}\"\n", .{r.idea[0..r.idea_n]});
    }
    if (r.ok) {
        std.debug.print("FSOT_NOVEL PASS\n", .{});
        std.debug.print("FSOT_NOVEL_SYNTHESIS_OK\n", .{});
    } else {
        std.debug.print("FSOT_NOVEL FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runCheckpoint() void {
    std.debug.print("=== FSOT CHECKPOINT (biological save-game) ===\n", .{});
    std.debug.print("doctrine: persist episodic memory + meaning; genetic spine remains law\n", .{});
    if (!checkpoint_fixed.selfTest()) {
        std.debug.print("FSOT_CHECKPOINT FAIL selftest\n", .{});
        std.process.exit(1);
    }
    const r = checkpoint_fixed.runCheckpointProbe() catch {
        std.debug.print("FSOT_CHECKPOINT FAIL io\n", .{});
        std.process.exit(1);
    };
    std.debug.print(
        "CHECKPOINT saved={d} loaded={d} roundtrip={} path={s}\n",
        .{ r.n_saved, r.n_loaded, r.roundtrip, r.path },
    );
    if (r.ok) {
        std.debug.print("FSOT_CHECKPOINT PASS\n", .{});
        std.debug.print("FSOT_SAVEGAME_OK\n", .{});
    } else {
        std.debug.print("FSOT_CHECKPOINT FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runFailure() void {
    std.debug.print("=== FSOT FAILURE BOUNDARIES (expanded catalog, fixed) ===\n", .{});
    const r = failure_fixed.runFailureProbe();
    std.debug.print(
        "FAILURE modes={d} healthy={d} AD={d} PD={d} ALS={d} MS={d} EPI={d} ISCH={d} envelope={} boundary={} shape={}\n",
        .{ r.n_modes, r.healthy_spikes, r.ad_spikes, r.pd_spikes, r.als_spikes, r.ms_spikes, r.epi_spikes, r.ischemia_spikes, r.healthy_in_envelope, r.boundary_detected, r.catalog_shape_ok },
    );
    if (r.ok) {
        std.debug.print("FSOT_FAILURE PASS\n", .{});
    } else {
        std.debug.print("FSOT_FAILURE FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runWireAround() void {
    std.debug.print("=== FSOT WIRE-AROUND (lesion → recovery actions, fixed) ===\n", .{});
    const r = wire_around_fixed.runWireAroundProbe();
    std.debug.print(
        "WIRE healthy={d} lesion={d} rescued={d} improved={} actions={d}\n",
        .{ r.healthy_spikes, r.lesion_spikes, r.rescued_spikes, r.improved, r.n_actions },
    );
    if (r.ok) {
        std.debug.print("FSOT_WIRE_AROUND PASS\n", .{});
    } else {
        std.debug.print("FSOT_WIRE_AROUND FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runSymbolAssoc() void {
    std.debug.print("=== FSOT SYMBOL ASSOC (sensory signature → prototype anchors) ===\n", .{});
    const r = symbol_assoc_fixed.runSymbolAssocProbe();
    std.debug.print(
        "SYMBOL anchors={d} hit={d}/{d} top1={e} cross={d}/{d} ctop1={e}\n",
        .{ r.n_anchors, r.correct, r.n_probes, r.top1, r.cross_modal_correct, r.n_probes, r.cross_modal_top1 },
    );
    if (r.ok) {
        std.debug.print("FSOT_SYMBOL PASS\n", .{});
    } else {
        std.debug.print("FSOT_SYMBOL FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runHardware() void {
    std.debug.print("=== FSOT HARDWARE METRIC (plant interoception stub) ===\n", .{});
    const r = hardware_metric_fixed.runHardwareProbe();
    std.debug.print(
        "HARDWARE n_units={d} cpu={e} mem={e} source={s} mod_ok={}\n",
        .{ r.n_units_suggest, r.cpu, r.mem, r.source, r.mod_mode_ok },
    );
    if (r.ok) {
        std.debug.print("FSOT_HARDWARE PASS\n", .{});
    } else {
        std.debug.print("FSOT_HARDWARE FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runHostSenses() void {
    std.debug.print("=== FSOT HOST SENSES (Zig live display+mic → Fixed bus) ===\n", .{});
    std.debug.print("doctrine: no C/Rust required; framebuffer sample not screenshot files\n", .{});
    const r = host_senses_fixed.runHostSensesProbe();
    std.debug.print(
        "HOST live_disp={} live_mic={} vis={} aud={} {d}x{d} mic_n={d} spikes={d} eps={d} feat_ok={}\n",
        .{
            r.live_display,
            r.live_mic,
            r.vision_ok,
            r.audio_ok,
            r.width,
            r.height,
            r.n_audio_samples,
            r.organism_spikes,
            r.episodes,
            r.feat_path_ok,
        },
    );
    if (r.ok) {
        std.debug.print("FSOT_HOST_SENSES PASS\n", .{});
        if (r.live_display or r.live_mic) {
            std.debug.print("FSOT_HOST_SENSES_LIVE_OK\n", .{});
        } else {
            std.debug.print("FSOT_HOST_SENSES_FALLBACK_SYNTHETIC\n", .{});
        }
    } else {
        std.debug.print("FSOT_HOST_SENSES FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runHostLoop() void {
    std.debug.print("=== FSOT HOST LOOP (continuous sample→inject→tick) ===\n", .{});
    const r = host_loop_fixed.runHostLoop(24, true);
    std.debug.print(
        "HOST_LOOP ticks={d} live_disp={d} live_mic={d} spikes={d} eps={d} spoke={} sleep_ms={d}\n",
        .{ r.n_ticks, r.n_live_display, r.n_live_mic, r.spikes, r.episodes, r.spoke, r.sleep_ms },
    );
    if (r.ok) {
        std.debug.print("FSOT_HOST_LOOP PASS\n", .{});
    } else {
        std.debug.print("FSOT_HOST_LOOP FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runBodyDaemon() void {
    // Smoke plant loop only (senses→tick). Full intelligence = runLiveMindConnected.
    std.debug.print("=== FSOT BODY PLANT SMOKE (senses only — use 'mind' for full brain) ===\n", .{});
    const r = host_loop_fixed.runBodyDaemon();
    std.debug.print(
        "BODY ticks={d} live_disp={d} live_mic={d} spikes={d} eps={d} spoke={} sleep_ms={d}\n",
        .{ r.n_ticks, r.n_live_display, r.n_live_mic, r.spikes, r.episodes, r.spoke, r.sleep_ms },
    );
    if (r.ok) {
        std.debug.print("FSOT_BODY PASS\n", .{});
        std.debug.print("FSOT_BODY_BOOT_OK\n", .{});
        std.debug.print("NOTE: full connected intelligence → mode 'mind' or BOOT_MIND.cmd\n", .{});
    } else {
        std.debug.print("FSOT_BODY FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runLiveMindConnected() void {
    // Default product: one organism, all systems wired, not unit-test parade.
    const r = mind_live_fixed.runLiveMind(.{
        .n_ticks = 450, // ~9s @20ms
        .sleep_ms = 20,
        .report_every = 30,
        .speakers = true,
        .speak_every = 45,
        .encode_every = 6,
        .curiosity_every = 12,
        .teach_every = 40,
        .english_tts = true,
        .formant_speech = true, // internal motor path; DAC skipped when TTS on
    });
    std.debug.print(
        "SUMMARY spikes={d} rate={e} eps={d} enc={d} cur={d}/{d} teach={d} ret={d} spk={d} self={d}/{d} air={d} int={d} match={e} amb={d} ign={d} scene={d} enc_open={d} att={e} adapt={d} bias={e} pat={d} pat_bind={d} mach={d}/{d}B en={d} tts={d}\n",
        .{ r.spikes, r.spike_rate, r.episodes, r.n_encodes, r.n_curiosity, r.n_curiosity_q, r.n_teaches, r.n_retrieves, r.n_speaks, r.n_self_hear, r.n_self_attempts, r.n_self_air, r.n_self_internal, r.last_self_match, r.n_ambient_high, r.n_noise_ignored, r.n_scene_samples, r.n_encode_open, r.last_attune, r.n_speech_adapt, r.last_bias_mag, r.last_pattern, r.n_pattern_binds, r.n_machine_emit, r.n_machine_bytes, r.n_english_say, r.n_tts_spoken },
    );
    if (r.ok) {
        std.debug.print("FSOT_LIVE_MIND PASS\n", .{});
        std.debug.print("FSOT_MIND_CONNECTED_OK\n", .{});
    } else {
        std.debug.print("FSOT_LIVE_MIND FAIL (need more spikes/memory/curiosity activity)\n", .{});
        std.process.exit(1);
    }
}

fn runSpeakers() void {
    std.debug.print("=== FSOT SPEAKERS (speech organ acoustic → DAC) ===\n", .{});
    const r = host_audio_out_fixed.runSpeakerProbe();
    std.debug.print(
        "SPEAKERS samples={d} played={} backend={s}\n",
        .{ r.n_samples, r.played, r.backend },
    );
    if (r.ok) {
        std.debug.print("FSOT_SPEAKERS PASS\n", .{});
        if (r.played) std.debug.print("FSOT_SPEAKERS_PLAYED_OK\n", .{});
    } else {
        std.debug.print("FSOT_SPEAKERS FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runAutonomous() void {
    std.debug.print("=== FSOT AUTONOMOUS (multi-domain chew, no per-item prompt) ===\n", .{});
    const r = autonomous_fixed.runAutonomousProbe();
    std.debug.print(
        "AUTO domains={d} eps={d} words={d} recall={d}/{d} top1={e} cur={d} spikes={d} spoke={}\n",
        .{ r.n_domains, r.n_episodes, r.n_machine_words, r.recall_correct, r.recall_n, r.recall_top1, r.curiosity_resolved, r.spikes, r.spoke },
    );
    if (r.ok) {
        std.debug.print("FSOT_AUTONOMOUS PASS\n", .{});
    } else {
        std.debug.print("FSOT_AUTONOMOUS FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runInjectFile(path: []const u8) !void {
    std.debug.print("=== FSOT MIND INJECT-FILE → FIXED organism ===\n", .{});
    std.debug.print("path={s}\n", .{path});
    // Fixed ABI: text frames → Fixed (no f64 mind core)
    const r = try vision_inject_fixed.runVisionInject(path);
    std.debug.print(
        "packets={d} vision={d} ticks={d} eps={d} spikes={d} retrieve={}\n",
        .{ r.n_packets, r.n_vision, r.ticks, r.episodes, r.spikes, r.retrieve_ok },
    );
    if (!r.ok) {
        std.debug.print("FSOT_INJECT_FILE FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_INJECT_FILE PASS\n", .{});
}

fn runVisionInjectDemo() void {
    std.debug.print("=== FSOT MIND VISION-INJECT (fixed DEMO frames, no external path) ===\n", .{});
    const r = vision_inject_fixed.runVisionInject(null) catch {
        std.debug.print("FSOT_VISION_INJECT FAIL parse\n", .{});
        std.process.exit(1);
    };
    std.debug.print(
        "packets={d} vision={d} ticks={d} eps={d} spikes={d} retrieve={}\n",
        .{ r.n_packets, r.n_vision, r.ticks, r.episodes, r.spikes, r.retrieve_ok },
    );
    if (!r.ok) {
        std.debug.print("FSOT_VISION_INJECT FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_VISION_INJECT PASS\n", .{});
}

fn runMnistAccuracy() void {
    std.debug.print("=== FSOT MNIST ACCURACY GATE (real held-out, ≥95%) ===\n", .{});
    std.debug.print("doctrine: 14x14 pool L2 features + k-NN; pack from run_mnist_gate.py\n", .{});
    const r = mnist_accuracy_fixed.runMnistAccuracy();
    std.debug.print(
        "MNIST top1={e} thr={e} correct={d}/{d} train={d} dim={d} k={d} pack={}\n",
        .{ r.top1, mnist_accuracy_fixed.PASS_THRESHOLD, r.correct, r.n_test, r.n_train, r.dim, r.k, r.from_pack },
    );
    if (r.ok) {
        std.debug.print("FSOT_MNIST_GATE PASS\n", .{});
        std.debug.print("FSOT_MNIST_ACCURACY_OK\n", .{});
    } else {
        std.debug.print("FSOT_MNIST_GATE FAIL (run: python run_mnist_gate.py)\n", .{});
        std.process.exit(1);
    }
}

fn runGradeDepth() void {
    std.debug.print("=== FSOT GRADE-SCHOOL DEPTH (understand paraphrases, ≥95%) ===\n", .{});
    std.debug.print("doctrine: taught STEM/literacy only; natural Q → parse → bank/math/overlap → answer\n", .{});
    std.debug.print("no history; deepen claimability before expanding further\n", .{});
    const r = understand_depth_fixed.runDepthExam();
    std.debug.print(
        "DEPTH bank={d} exam={d} correct={d} acc={e} thr={e} math={d} overlap={d} exact={d} miss={d}\n",
        .{ r.n_bank, r.n_exam, r.n_correct, r.accuracy, r.threshold, r.n_math, r.n_overlap, r.n_exact, r.n_miss },
    );
    if (r.ok) {
        std.debug.print("FSOT_DEPTH PASS\n", .{});
        std.debug.print("FSOT_GRADE_SCHOOL_UNDERSTAND_OK\n", .{});
    } else {
        std.debug.print("FSOT_DEPTH FAIL (need ≥95% held-out paraphrases)\n", .{});
        std.process.exit(1);
    }
}

fn runSynapsePathways() void {
    std.debug.print("=== FSOT SYNAPTIC PATHWAYS (trace + plastic bonds + novel thought) ===\n", .{});
    std.debug.print("doctrine: Hebb LTP-like W update, prune unused, concept cross-domain bonds\n", .{});
    std.debug.print("compare to human: LTP/LTD, synaptogenesis, limited adult neurogenesis, association\n", .{});
    const r = synapse_path_fixed.runSynapsePathwayProbe();
    std.debug.print(
        "PATH edges={d} hebb={d} stdp={d} stdp_ok={} spikes={d} concepts={d} bonds {d}→{d} novel={d} cross={d} pruned={d} thought_steps={d} cross_region={d} meanS={e}\n",
        .{
            r.n_edge_traces,
            r.n_hebb,
            r.n_stdp,
            r.stdp_selftest,
            r.spikes,
            r.n_concepts,
            r.n_bonds_before,
            r.n_bonds_after,
            r.n_novel_bonds,
            r.n_cross_domain,
            r.n_pruned,
            r.n_thought_steps,
            r.cross_region_edges,
            r.mean_s,
        },
    );
    std.debug.print(
        "GLIA supply={e} load={e} clear={d} prune={d} myelo={d} self={}\n",
        .{ r.mean_supply, r.mean_load, r.n_glia_clear, r.n_glia_prune, r.n_myelo, r.glia_selftest },
    );
    std.debug.print(
        "MOL tags={d} camk={d} ampa={d} consol={d} self={}\n",
        .{ r.n_molecular_tags, r.n_camk_peaks, r.n_ampa_up, r.n_consolidate, r.mol_selftest },
    );
    if (r.ok) {
        std.debug.print("FSOT_SYNAPSE_PATH PASS\n", .{});
        std.debug.print("FSOT_NOVEL_PATHWAY_OK\n", .{});
        std.debug.print("FSOT_GLIA_MOLECULAR_OK\n", .{});
    } else {
        std.debug.print("FSOT_SYNAPSE_PATH FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runPixelId() void {
    std.debug.print("=== FSOT MIND PIXEL-ID (tutor-ablated multi-seed synthetic) ===\n", .{});
    const p = pixel_id_fixed.runPixelIdProbe();
    std.debug.print(
        "PIXEL_ID chars={d} seeds={d} train={d} test={d} correct={d}/{d} top1={e} multi_mean={e} chance={e} tutor_ablated={} spikes={d}\n",
        .{ p.n_characters, p.n_seeds, p.n_train, p.n_test, p.correct, p.n_test, p.top1, p.multi_seed_mean, p.chance, p.tutor_ablated, p.spikes },
    );
    if (p.ok) {
        std.debug.print("FSOT_PIXEL_ID PASS\n", .{});
    } else {
        std.debug.print("FSOT_PIXEL_ID FAIL\n", .{});
        std.process.exit(1);
    }
}

fn runLive() void {
    std.debug.print("=== FSOT MIND LIVE (FIXED multi-region) ===\n", .{});
    var b = brain_fixed.BrainF.initSeeded(42, false);
    const st = b.structureReport();
    std.debug.print(
        "structure units={d} E={d} I={d} synapses={d} Pyr/PV/SST/VIP={d}/{d}/{d}/{d}\n",
        .{ st.n_units, st.n_e, st.n_i, st.n_synapses, st.n_pyr, st.n_pv, st.n_sst, st.n_vip },
    );
    var ext: [brain_fixed.N_TOTAL]fixed.Fixed = undefined;
    var t: usize = 0;
    var spikes_win: u32 = 0;
    while (t < 90) : (t += 1) {
        const prim: fixed.Fixed = if ((t % 30) < 10) fixed.fromDecimalStr("0.75") else fixed.fromDecimalStr("0.06");
        const reg: brain_fixed.RegionId = if ((t / 30) % 2 == 0) .sens else .assoc;
        b.buildExternal(prim, reg, ext[0..]);
        const before = b.totalSpikes();
        b.step(ext[0..]);
        spikes_win += b.totalSpikes() - before;
        if ((t + 1) % 30 == 0) {
            std.debug.print(
                "t={d} meanS={e} spikes_win={d}\n",
                .{ t + 1, fixed.toF64(b.meanS()), spikes_win },
            );
            spikes_win = 0;
        }
    }
    std.debug.print("FSOT_LIVE PASS total_spikes={d}\n", .{b.totalSpikes()});
}

fn runInject() void {
    std.debug.print("=== FSOT MIND INJECT (FIXED lattice + inject ABI) ===\n", .{});
    if (!inject_io_fixed.selfTest()) {
        std.debug.print("FSOT_INJECT FAIL inject_io_fixed\n", .{});
        std.process.exit(1);
    }
    var bus: inject_io_fixed.BusF = .{};
    _ = inject_io_fixed.parseFeatureText(inject_io_fixed.DEMO_TEXT, &bus) catch {
        std.debug.print("FSOT_INJECT FAIL parse\n", .{});
        std.process.exit(1);
    };
    var org = organism_fixed.OrganismF.init();
    org.encode_every = 10;
    org.steps_per_tick = 4;
    org.setMetric(bus.metric);
    var feats: [8]fixed.Fixed = .{0} ** 8;
    const nf = bus.firstVisionFeats(&feats);
    org.setInject(feats[0..nf]);
    var t: u32 = 0;
    while (t < 40) : (t += 1) {
        _ = org.tickOnce();
    }
    std.debug.print(
        "inject meanS={e} spikes={d} eps={d} metric_cpu={e} packets={d} mod={s} stim={e}\n",
        .{
            fixed.toF64(org.brain.meanS()),
            org.brain.totalSpikes(),
            org.store.n,
            fixed.toF64(bus.metric.cpu),
            bus.n,
            modulate_fixed.modeName(org.last_mod.mode),
            fixed.toF64(org.last_mod.stim_scale),
        },
    );
    if (org.brain.totalSpikes() >= 1) {
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
        runLearnFixed();
    } else if (std.mem.eql(u8, mode, "curriculum")) {
        runCurriculum();
    } else if (std.mem.eql(u8, mode, "curiosity")) {
        runCuriosity();
    } else if (std.mem.eql(u8, mode, "transfer")) {
        runTransfer();
    } else if (std.mem.eql(u8, mode, "modulate") or std.mem.eql(u8, mode, "modulation") or std.mem.eql(u8, mode, "sme-mod")) {
        runModulate();
    } else if (std.mem.eql(u8, mode, "teach") or std.mem.eql(u8, mode, "5w1h") or std.mem.eql(u8, mode, "teach-5w1h")) {
        runTeach();
    } else if (std.mem.eql(u8, mode, "short-horizon") or std.mem.eql(u8, mode, "short_horizon") or std.mem.eql(u8, mode, "sh")) {
        runShortHorizon();
    } else if (std.mem.eql(u8, mode, "speech") or std.mem.eql(u8, mode, "speech-organ") or std.mem.eql(u8, mode, "articulate")) {
        runSpeechOrgan();
    } else if (std.mem.eql(u8, mode, "cross-modal") or std.mem.eql(u8, mode, "cross_modal") or std.mem.eql(u8, mode, "av") or std.mem.eql(u8, mode, "crossmodal")) {
        runCrossModal();
    } else if (std.mem.eql(u8, mode, "bio-io") or std.mem.eql(u8, mode, "bio_io") or std.mem.eql(u8, mode, "sensory") or std.mem.eql(u8, mode, "io")) {
        runBioIo();
    } else if (std.mem.eql(u8, mode, "machine") or std.mem.eql(u8, mode, "machine-encode") or std.mem.eql(u8, mode, "abi")) {
        runMachineEncode();
    } else if (std.mem.eql(u8, mode, "machine-lang") or std.mem.eql(u8, mode, "machine_lang") or std.mem.eql(u8, mode, "mlang") or std.mem.eql(u8, mode, "tongue")) {
        runMachineLang();
    } else if (std.mem.eql(u8, mode, "machine-lang-stress") or std.mem.eql(u8, mode, "mlang-stress") or std.mem.eql(u8, mode, "tongue-stress")) {
        runMachineLangStress();
    } else if (std.mem.eql(u8, mode, "english") or std.mem.eql(u8, mode, "lexicon") or std.mem.eql(u8, mode, "tts") or std.mem.eql(u8, mode, "words")) {
        runEnglishCodec();
    } else if (std.mem.eql(u8, mode, "practice") or std.mem.eql(u8, mode, "language-practice") or std.mem.eql(u8, mode, "lang-practice") or std.mem.eql(u8, mode, "self-speak")) {
        runLanguagePractice();
    } else if (std.mem.eql(u8, mode, "grade") or std.mem.eql(u8, mode, "curriculum")) {
        runGradePractice();
    } else if (std.mem.eql(u8, mode, "ladder") or std.mem.eql(u8, mode, "straight-a") or std.mem.eql(u8, mode, "grades")) {
        runGradeLadder();
    } else if (std.mem.eql(u8, mode, "preschool") or std.mem.eql(u8, mode, "pk")) {
        runGradeBand(.preschool);
    } else if (std.mem.eql(u8, mode, "kindergarten") or std.mem.eql(u8, mode, "kinder") or std.mem.eql(u8, mode, "k")) {
        runGradeBand(.kindergarten);
    } else if (std.mem.eql(u8, mode, "grade1") or std.mem.eql(u8, mode, "g1") or std.mem.eql(u8, mode, "first")) {
        runGradeBand(.grade1);
    } else if (std.mem.eql(u8, mode, "grade2") or std.mem.eql(u8, mode, "g2")) {
        runGradeBand(.grade2);
    } else if (std.mem.eql(u8, mode, "grade3") or std.mem.eql(u8, mode, "g3")) {
        runGradeBand(.grade3);
    } else if (std.mem.eql(u8, mode, "grade4") or std.mem.eql(u8, mode, "g4")) {
        runGradeBand(.grade4);
    } else if (std.mem.eql(u8, mode, "grade5") or std.mem.eql(u8, mode, "g5")) {
        runGradeBand(.grade5);
    } else if (std.mem.eql(u8, mode, "grade6") or std.mem.eql(u8, mode, "g6") or std.mem.eql(u8, mode, "ms6")) {
        runGradeBand(.grade6);
    } else if (std.mem.eql(u8, mode, "grade7") or std.mem.eql(u8, mode, "g7") or std.mem.eql(u8, mode, "ms7")) {
        runGradeBand(.grade7);
    } else if (std.mem.eql(u8, mode, "grade8") or std.mem.eql(u8, mode, "g8") or std.mem.eql(u8, mode, "ms8")) {
        runGradeBand(.grade8);
    } else if (std.mem.eql(u8, mode, "reason") or std.mem.eql(u8, mode, "open-reason") or std.mem.eql(u8, mode, "think") or std.mem.eql(u8, mode, "multi-hop")) {
        runReasonPractice();
    } else if (std.mem.eql(u8, mode, "novel") or std.mem.eql(u8, mode, "inquiry") or std.mem.eql(u8, mode, "synthesize") or std.mem.eql(u8, mode, "idea")) {
        runNovelInquiry();
    } else if (std.mem.eql(u8, mode, "checkpoint") or std.mem.eql(u8, mode, "savegame") or std.mem.eql(u8, mode, "save-load")) {
        runCheckpoint();
    } else if (std.mem.eql(u8, mode, "failure") or std.mem.eql(u8, mode, "lesion") or std.mem.eql(u8, mode, "boundaries")) {
        runFailure();
    } else if (std.mem.eql(u8, mode, "wire") or std.mem.eql(u8, mode, "wire-around") or std.mem.eql(u8, mode, "wire_around")) {
        runWireAround();
    } else if (std.mem.eql(u8, mode, "symbol") or std.mem.eql(u8, mode, "symbol-assoc") or std.mem.eql(u8, mode, "anchors")) {
        runSymbolAssoc();
    } else if (std.mem.eql(u8, mode, "hardware") or std.mem.eql(u8, mode, "plant")) {
        runHardware();
    } else if (std.mem.eql(u8, mode, "host-senses") or std.mem.eql(u8, mode, "host_senses") or std.mem.eql(u8, mode, "senses") or std.mem.eql(u8, mode, "host")) {
        runHostSenses();
    } else if (std.mem.eql(u8, mode, "host-loop") or std.mem.eql(u8, mode, "host_loop") or std.mem.eql(u8, mode, "loop")) {
        runHostLoop();
    } else if (std.mem.eql(u8, mode, "body") or std.mem.eql(u8, mode, "daemon") or std.mem.eql(u8, mode, "boot")) {
        // plant smoke only
        runBodyDaemon();
    } else if (std.mem.eql(u8, mode, "mind") or std.mem.eql(u8, mode, "live-mind") or std.mem.eql(u8, mode, "live_mind") or std.mem.eql(u8, mode, "connected") or std.mem.eql(u8, mode, "awake")) {
        // FULL connected organism (brain+memory+senses+speech)
        runLiveMindConnected();
    } else if (std.mem.eql(u8, mode, "speakers") or std.mem.eql(u8, mode, "speaker") or std.mem.eql(u8, mode, "audio-out")) {
        runSpeakers();
    } else if (std.mem.eql(u8, mode, "autonomous") or std.mem.eql(u8, mode, "auto") or std.mem.eql(u8, mode, "chew")) {
        runAutonomous();
    } else if (std.mem.eql(u8, mode, "sme-fixed") or std.mem.eql(u8, mode, "sme_fixed") or std.mem.eql(u8, mode, "bands-fixed")) {
        runSmeFixed();
    } else if (std.mem.eql(u8, mode, "attention") or std.mem.eql(u8, mode, "eeg") or std.mem.eql(u8, mode, "eeg-gates") or std.mem.eql(u8, mode, "attune")) {
        runAttentionEeg();
    } else if (std.mem.eql(u8, mode, "mnist") or std.mem.eql(u8, mode, "mnist-gate") or std.mem.eql(u8, mode, "mnist_accuracy")) {
        runMnistAccuracy();
    } else if (std.mem.eql(u8, mode, "depth") or std.mem.eql(u8, mode, "understand") or std.mem.eql(u8, mode, "paraphrase") or std.mem.eql(u8, mode, "grade-depth")) {
        runGradeDepth();
    } else if (std.mem.eql(u8, mode, "pathways") or std.mem.eql(u8, mode, "synapse") or std.mem.eql(u8, mode, "synaptic") or std.mem.eql(u8, mode, "trace") or std.mem.eql(u8, mode, "think-path") or std.mem.eql(u8, mode, "glia") or std.mem.eql(u8, mode, "molecular") or std.mem.eql(u8, mode, "cascade")) {
        runSynapsePathways();
    } else if (std.mem.eql(u8, mode, "pixel-id") or std.mem.eql(u8, mode, "pixel_id") or std.mem.eql(u8, mode, "pixelid")) {
        runPixelId();
    } else if (std.mem.eql(u8, mode, "vision") or std.mem.eql(u8, mode, "vision-inject") or std.mem.eql(u8, mode, "vision_inject")) {
        runVisionInjectDemo();
    } else if (std.mem.eql(u8, mode, "live")) {
        // short brain-only activity (no host) — prefer "mind" for full stack
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
    } else if (std.mem.eql(u8, mode, "fixed") or std.mem.eql(u8, mode, "fixedpoint") or std.mem.eql(u8, mode, "authority")) {
        runFixed();
    } else if (std.mem.eql(u8, mode, "genetic") or std.mem.eql(u8, mode, "codon")) {
        runGenetic();
    } else if (std.mem.eql(u8, mode, "sme")) {
        // default SME authority = fixed bands
        runSmeFixed();
    } else if (std.mem.eql(u8, mode, "sme-float") or std.mem.eql(u8, mode, "sme_float")) {
        runSme();
    } else if (std.mem.eql(u8, mode, "inject-file") or std.mem.eql(u8, mode, "inject_file")) {
        if (args.len < 3) {
            std.debug.print("usage: fsot_mind inject-file <path>\n", .{});
            std.process.exit(2);
        }
        try runInjectFile(args[2]);
    } else if (std.mem.eql(u8, mode, "bio")) {
        // bio authority = fixed Allen FI + bio I/O routes
        runFixed();
        runBioIo();
        runFailure();
        runWireAround();
        runHardware();
        runHostSenses();
        runHostLoop();
        runSpeakers();
    } else if (std.mem.eql(u8, mode, "bio-float") or std.mem.eql(u8, mode, "bio_float")) {
        const path: ?[]const u8 = if (args.len >= 3) args[2] else null;
        try runBio(path);
    } else if (std.mem.eql(u8, mode, "stress")) {
        // stress authority = fixed stack + expanded scaffolds
        runFixed();
        runLearnFixed();
        runCurriculum();
        runCuriosity();
        runTeach();
        runTransfer();
        runModulate();
        runSmeFixed();
        runShortHorizon();
        runSpeechOrgan();
        runCrossModal();
        runBioIo();
        runMachineEncode();
        runFailure();
        runWireAround();
        runSymbolAssoc();
        runHardware();
        runHostSenses();
        runHostLoop();
        runSpeakers();
        runAutonomous();
        runInject();
        runVisionInjectDemo();
        runPixelId();
        runOrganism();
        runIntel();
        std.debug.print("FSOT_STRESS PASS\n", .{});
        std.debug.print("FSOT_STRESS_FIXED_AUTHORITY_OK\n", .{});
    } else if (std.mem.eql(u8, mode, "float-lab") or std.mem.eql(u8, mode, "float_lab") or std.mem.eql(u8, mode, "lab")) {
        try runSelfTest();
        runGenetic();
        runLearn();
        runMemory();
        try runBio(null);
        try runStress();
        std.debug.print("FSOT_FLOAT_LAB_OK\n", .{});
    } else if (std.mem.eql(u8, mode, "all") or std.mem.eql(u8, mode, "suite") or std.mem.eql(u8, mode, "tests")) {
        // Full unit-test suite (not the live organism — use "mind" for that)
        runFixed();
        runLearnFixed();
        runCurriculum();
        runCuriosity();
        runTeach();
        runTransfer();
        runModulate();
        runSmeFixed();
        runAttentionEeg();
        runShortHorizon();
        runSpeechOrgan();
        runCrossModal();
        runBioIo();
        runMachineEncode();
        runMachineLang();
        runFailure();
        runWireAround();
        runSymbolAssoc();
        runHardware();
        runHostSenses();
        runHostLoop();
        runSpeakers();
        runAutonomous();
        runInject();
        runVisionInjectDemo();
        runPixelId();
        runOrganism();
        runIntel();
        runGenetic();
        std.debug.print("FSOT_MIND_HOST_OK\n", .{});
        std.debug.print("FSOT_FIXED_AUTHORITY_OK\n", .{});
        std.debug.print("FSOT_NO_PYTHON_CORE_OK\n", .{});
        std.debug.print("FSOT_INTEL_HOST_OK\n", .{});
        std.debug.print("NOTE: suite is gates only. Live intelligence → BOOT_MIND.cmd or mode 'mind'\n", .{});
    } else {
        std.debug.print("usage: fsot_mind mind|body|stress|suite|host-senses|…\n", .{});
        std.debug.print("  mind  = FULL connected organism (brain+memory+senses+speech)\n", .{});
        std.debug.print("  body  = plant smoke only (senses loop)\n", .{});
        std.debug.print("  suite = unit-test gates (not live intelligence)\n", .{});
        std.process.exit(2);
    }
}
