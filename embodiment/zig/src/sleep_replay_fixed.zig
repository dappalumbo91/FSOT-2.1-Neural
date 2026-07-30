//! Offline consolidation: sleep-like replay on Fixed lattice.
//!
//! Biology (process, Creery/Sederberg-style instrumental targets):
//!   1) Wake encode with high ACh/NE (attention) + optional DA tag on encode
//!   2) Quiet rest (decay neuromod)
//!   3) NREM-like offline: low ACh/NE, elevated 5-HT, soft replay of encoded
//!      fingerprints into hipp/assoc (+ sparse thal packets)
//!   4) During replay: STDP with neuromod η scale (reactivation tagging)
//!   5) Probe retention top-1 after delay ± consolidate
//!
//! Not wall-clock PC sleep — biological *schedule* in model-ms ticks.
//! See docs/STAGE_RETENTION_CONSOLIDATION.md · docs/LEARNING_ALIGNMENT.md

const std = @import("std");
const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const neuromod_f = @import("neuromod_fixed.zig");
const stdp_f = @import("stdp_fixed.zig");
const network_f = @import("network_fixed.zig");
const Fixed = fixed.Fixed;

pub const N_ITEMS: usize = 8;
pub const ENCODE_STEPS: usize = 12;
pub const DELAY_STEPS: usize = 80;
pub const REPLAY_ROUNDS: usize = 3;
pub const REPLAY_STEPS: usize = 10;
pub const PROBE_STEPS: usize = 12;

pub const ConsolReport = struct {
    ok: bool = false,
    n_items: u32 = 0,
    top1_immediate: f64 = 0,
    top1_after_delay: f64 = 0,
    top1_after_consol: f64 = 0,
    consolidate_improved: bool = false,
    mean_sigma: f64 = 0,
    mean_da: f64 = 0,
    mean_ach_wake: f64 = 0,
    mean_ach_sleep: f64 = 0,
    n_stdp_replay: u32 = 0,
    n_da_pulses: u32 = 0,
    neuromod_selftest: bool = false,
    n_replay_events: u32 = 0,
};

fn itemFeatures(item: usize, out: *[8]Fixed) void {
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        const h = (@as(u32, @intCast(item + 1)) *% 2654435761) +% (@as(u32, @intCast(i)) *% 97);
        out[i] = fixed.sub(fixed.div(fixed.fromInt(@intCast(h % 201)), fixed.fromInt(100)), fixed.fromInt(1));
    }
}

fn itemTokens(item: usize) [6]u32 {
    var t: [6]u32 = .{0} ** 6;
    t[0] = memory_f.hashToken("item");
    t[1] = @as(u32, @intCast(item + 1)) *% 10007 +% 3;
    t[2] = memory_f.hashToken("fact");
    t[3] = @as(u32, @intCast(item + 1)) *% 30011 +% 11;
    return t;
}

fn driveExternal(b: *brain_f.BrainF, feat: []const Fixed, gain: Fixed, quiet: Fixed, t: usize, ext: []Fixed) void {
    var i: usize = 0;
    while (i < b.n) : (i += 1) {
        var e = fixed.mul(fixed.fromDecimalStr("0.03"), quiet);
        const f = if (feat.len == 0) 0 else feat[i % feat.len];
        switch (b.region_of[i]) {
            .thal => {
                if ((t % 40) < 12) e = fixed.add(e, fixed.mul(fixed.fromDecimalStr("0.35"), gain));
                e = fixed.add(e, fixed.mul(fixed.mul(fixed.fromDecimalStr("0.12"), f), gain));
            },
            .sens => e = fixed.add(e, fixed.mul(fixed.mul(fixed.fromDecimalStr("0.80"), f), gain)),
            .assoc => e = fixed.add(e, fixed.mul(fixed.mul(fixed.fromDecimalStr("0.55"), f), gain)),
            .hipp => e = fixed.add(e, fixed.mul(fixed.mul(fixed.fromDecimalStr("0.70"), f), gain)),
        }
        ext[i] = fixed.clamp(e, fixed.fromDecimalStr("-0.5"), fixed.fromDecimalStr("1.6"));
    }
}

fn cosineTop1(store: *memory_f.StoreF, b: *brain_f.BrainF, n_items: usize) struct { correct: u32, n: u32 } {
    var correct: u32 = 0;
    var i: usize = 0;
    while (i < n_items) : (i += 1) {
        var feat: [8]Fixed = undefined;
        itemFeatures(i, &feat);
        var sim: Fixed = 0;
        const id = store.retrieve(b, feat[0..], &sim);
        // expected id was encode order starting at 1
        if (id == @as(u32, @intCast(i + 1))) correct += 1;
    }
    return .{ .correct = correct, .n = @intCast(n_items) };
}

fn runRest(b: *brain_f.BrainF, nm: *neuromod_f.NeuromodState, steps: usize, phase: neuromod_f.Phase) void {
    var ext: [brain_f.N_TOTAL]Fixed = undefined;
    var t: usize = 0;
    while (t < steps) : (t += 1) {
        neuromod_f.step(nm, phase, 0, 0, 0, 0, fixed.fromInt(1));
        const quiet = neuromod_f.restQuietGain(nm);
        driveExternal(b, &[_]Fixed{}, fixed.fromDecimalStr("0.15"), quiet, t, ext[0..]);
        b.step(ext[0..]);
    }
}

fn encodeAll(store: *memory_f.StoreF, b: *brain_f.BrainF, nm: *neuromod_f.NeuromodState, n_items: usize) void {
    var i: usize = 0;
    while (i < n_items) : (i += 1) {
        var feat: [8]Fixed = undefined;
        itemFeatures(i, &feat);
        // wake encode neuromod
        var t: usize = 0;
        var ext: [brain_f.N_TOTAL]Fixed = undefined;
        while (t < ENCODE_STEPS) : (t += 1) {
            neuromod_f.step(nm, .wake_encode, 0, fixed.fromDecimalStr("0.05"), fixed.fromDecimalStr("0.03"), 0, fixed.fromInt(1));
            const g = neuromod_f.encodeGain(nm);
            driveExternal(b, feat[0..], g, fixed.fromInt(1), t, ext[0..]);
            b.step(ext[0..]);
        }
        // DA tag on successful encode
        neuromod_f.pulseDa(nm, fixed.fromDecimalStr("0.35"));
        _ = store.encode(b, feat[0..], 0x3f, itemTokens(i));
    }
}

fn replayConsolidate(store: *memory_f.StoreF, b: *brain_f.BrainF, nm: *neuromod_f.NeuromodState, n_items: usize, last_spike: []i32, global_tick: *i32) struct { n_stdp: u32, n_events: u32, sigma_sum: Fixed, sigma_n: u32 } {
    _ = store; // fingerprints already in store; replay drives features by item index
    var n_stdp: u32 = 0;
    var n_events: u32 = 0;
    var sigma_sum: Fixed = 0;
    var sigma_n: u32 = 0;
    var ext: [brain_f.N_TOTAL]Fixed = undefined;
    var round: usize = 0;
    while (round < REPLAY_ROUNDS) : (round += 1) {
        var item: usize = 0;
        while (item < n_items) : (item += 1) {
            var feat: [8]Fixed = undefined;
            itemFeatures(item, &feat);
            var t: usize = 0;
            while (t < REPLAY_STEPS) : (t += 1) {
                neuromod_f.step(nm, .sleep_replay, fixed.fromDecimalStr("0.1"), 0, 0, fixed.fromDecimalStr("0.02"), fixed.fromInt(1));
                // soft replay drive (weaker than wake encode)
                const g = fixed.mul(neuromod_f.encodeGain(nm), fixed.fromDecimalStr("0.45"));
                const quiet = neuromod_f.restQuietGain(nm);
                driveExternal(b, feat[0..], g, quiet, t, ext[0..]);
                // sparse thal only emphasis already in driveExternal
                b.step(ext[0..]);
                global_tick.* += 1;
                // update last spike ticks
                var u: usize = 0;
                while (u < b.n) : (u += 1) {
                    if (b.net.last_fired[u]) last_spike[u] = global_tick.*;
                }
                const react = fixed.fromDecimalStr("0.5");
                const sig = neuromod_f.sigmaProxy(nm, react);
                sigma_sum = fixed.add(sigma_sum, sig);
                sigma_n += 1;
                n_events += 1;
            }
            // STDP epoch under neuromod η scale → fold into elig as uniform scale
            var elig: [network_f.MAX_N * network_f.MAX_N]Fixed = undefined;
            const eta = neuromod_f.stdpEtaScale(nm);
            var ei: usize = 0;
            while (ei < network_f.MAX_N * network_f.MAX_N) : (ei += 1) elig[ei] = eta;
            n_stdp += stdp_f.applyStdpEpochModulated(b, last_spike, global_tick.*, null, elig[0..]);
            neuromod_f.pulseDa(nm, fixed.fromDecimalStr("0.15"));
        }
        // inter-round NREM quiet
        runRest(b, nm, 20, .sleep_nrem);
    }
    return .{ .n_stdp = n_stdp, .n_events = n_events, .sigma_sum = sigma_sum, .sigma_n = sigma_n };
}

/// Full protocol: encode → immediate probe → delay → delay probe → consolidate → consol probe.
pub fn runConsolidationProbe() ConsolReport {
    var rep: ConsolReport = .{};
    rep.neuromod_selftest = neuromod_f.selfTest();
    rep.n_items = N_ITEMS;

    var b = brain_f.BrainF.initSeeded(7, true);
    var store: memory_f.StoreF = .{};
    store.clear();
    var nm: neuromod_f.NeuromodState = .{};

    // 1) encode
    encodeAll(&store, &b, &nm, N_ITEMS);
    const imm = cosineTop1(&store, &b, N_ITEMS);
    rep.top1_immediate = @as(f64, @floatFromInt(imm.correct)) / @as(f64, @floatFromInt(imm.n));
    rep.mean_ach_wake = fixed.toF64(nm.ach);

    // 2) delay rest (no consolidate)
    runRest(&b, &nm, DELAY_STEPS, .wake_rest);
    const after_d = cosineTop1(&store, &b, N_ITEMS);
    rep.top1_after_delay = @as(f64, @floatFromInt(after_d.correct)) / @as(f64, @floatFromInt(after_d.n));

    // 3) offline consolidate (sleep replay) on a *fresh* store path:
    // re-encode on sister brain to compare fair retention with consolidate
    var b2 = brain_f.BrainF.initSeeded(7, true);
    var store2: memory_f.StoreF = .{};
    store2.clear();
    var nm2: neuromod_f.NeuromodState = .{};
    encodeAll(&store2, &b2, &nm2, N_ITEMS);
    runRest(&b2, &nm2, DELAY_STEPS / 2, .wake_rest);
    // NREM prelude
    runRest(&b2, &nm2, 30, .sleep_nrem);
    rep.mean_ach_sleep = fixed.toF64(nm2.ach);

    var last_spike: [brain_f.N_TOTAL]i32 = .{-1} ** brain_f.N_TOTAL;
    var gtick: i32 = 1000;
    const rr = replayConsolidate(&store2, &b2, &nm2, N_ITEMS, last_spike[0..], &gtick);
    rep.n_stdp_replay = rr.n_stdp;
    rep.n_replay_events = rr.n_events;
    if (rr.sigma_n > 0) rep.mean_sigma = fixed.toF64(fixed.div(rr.sigma_sum, fixed.fromInt(@intCast(rr.sigma_n))));
    neuromod_f.meansFinalize(&nm2);
    rep.mean_da = fixed.toF64(nm2.mean_da);
    rep.n_da_pulses = nm2.n_da_pulses;

    // post-sleep rest then probe
    runRest(&b2, &nm2, 20, .wake_rest);
    const after_c = cosineTop1(&store2, &b2, N_ITEMS);
    rep.top1_after_consol = @as(f64, @floatFromInt(after_c.correct)) / @as(f64, @floatFromInt(after_c.n));
    rep.consolidate_improved = rep.top1_after_consol + 1e-9 >= rep.top1_after_delay - 0.01;
    // Gate: neuromod ok, replay happened, immediate learn ≥ chance, consol not collapse
    const chance = 1.0 / @as(f64, @floatFromInt(N_ITEMS));
    rep.ok = rep.neuromod_selftest and
        rep.n_replay_events >= 1 and
        rep.n_stdp_replay >= 1 and
        rep.top1_immediate >= chance * 1.5 and
        rep.top1_after_consol >= chance and
        rep.mean_sigma > 0 and
        rep.n_da_pulses >= 1;
    return rep;
}

pub fn selfTest() bool {
    if (!neuromod_f.selfTest()) return false;
    const r = runConsolidationProbe();
    return r.ok;
}
