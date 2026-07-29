//! Biological FI metrics on fixed-point neurons — wet-lab accuracy gate.

const fixed = @import("fixed.zig");
const neuron_f = @import("neuron_fixed.zig");
const Fixed = fixed.Fixed;

pub const UnitParamsF = struct {
    d_eff: Fixed = fixed.fromInt(13),
    fire_thr: Fixed = fixed.fromDecimalStr("1.05"),
    ref_steps: i32 = 45,
    adapt_gain: Fixed = fixed.fromDecimalStr("0.03"),
    adapt_decay: Fixed = fixed.fromDecimalStr("0.991"),
    adapt_step: Fixed = fixed.fromDecimalStr("0.7"),
    fi_stim: Fixed = fixed.fromDecimalStr("0.48"),
};

pub const PopReportF = struct {
    n_units: u32 = 0,
    mean_rate_Hz: f64 = 0, // report as f64 for lab only
    mean_isi_ms: f64 = 0,
    mean_adapt: f64 = 0,
    n_with_isi: u32 = 0,
    total_spikes: u32 = 0,
};

fn applyParams(n: *neuron_f.NeuronF, p: UnitParamsF) void {
    n.d_eff = p.d_eff;
    n.fire_thr = p.fire_thr;
    n.ref_steps = p.ref_steps;
    n.adapt_gain = p.adapt_gain;
    n.adapt_decay = p.adapt_decay;
    n.adapt_step = p.adapt_step;
}

pub fn defaultBioParams(out: []UnitParamsF) void {
    var i: usize = 0;
    while (i < out.len) : (i += 1) {
        out[i] = .{
            .d_eff = fixed.add(fixed.fromInt(13), fixed.mul(fixed.fromDecimalStr("0.1"), fixed.fromInt(@intCast(i % 5)))),
            .fire_thr = fixed.fromDecimalStr("1.05"),
            .ref_steps = 45 + @as(i32, @intCast(i % 8)),
            .adapt_gain = fixed.fromDecimalStr("0.03"),
            .adapt_decay = fixed.fromDecimalStr("0.991"),
            .adapt_step = fixed.fromDecimalStr("0.7"),
            .fi_stim = fixed.fromDecimalStr("0.48"),
        };
    }
}

/// Load from same text format as bio_params_load (Allen-mapped).
pub fn loadParamsFromText(text: []const u8, out: []UnitParamsF) !usize {
    const std = @import("std");
    var n_target: ?usize = null;
    var filled: usize = 0;
    var it = std.mem.splitScalar(u8, text, '\n');
    while (it.next()) |raw| {
        var line = raw;
        if (std.mem.indexOfScalar(u8, line, '\r')) |r| line = line[0..r];
        if (std.mem.indexOfScalar(u8, line, '#')) |c| line = line[0..c];
        line = std.mem.trim(u8, line, " \t");
        if (line.len == 0) continue;
        if (n_target == null) {
            n_target = try std.fmt.parseInt(usize, line, 10);
            continue;
        }
        if (filled >= out.len or filled >= n_target.?) break;
        var parts = std.mem.tokenizeAny(u8, line, " \t");
        var vals: [7]f64 = undefined;
        var k: usize = 0;
        while (parts.next()) |tok| {
            if (k >= 7) break;
            vals[k] = try std.fmt.parseFloat(f64, tok);
            k += 1;
        }
        if (k < 7) return error.BadLine;
        out[filled] = .{
            .d_eff = fixed.fromF64Lab(vals[0]),
            .fire_thr = fixed.fromF64Lab(vals[1]),
            .ref_steps = @intFromFloat(vals[2]),
            .adapt_gain = fixed.fromF64Lab(vals[3]),
            .adapt_decay = fixed.fromF64Lab(vals[4]),
            .adapt_step = fixed.fromF64Lab(vals[5]),
            .fi_stim = fixed.fromF64Lab(vals[6]),
        };
        filled += 1;
    }
    return filled;
}

pub fn runFIUnit(p: UnitParamsF, steps: usize) struct {
    rate_Hz: f64,
    mean_isi_ms: f64,
    adapt: f64,
    spikes: u32,
} {
    var n = neuron_f.NeuronF{};
    applyParams(&n, p);
    n.reset();
    var times: [512]u32 = undefined;
    var nf: usize = 0;
    var t: usize = 0;
    while (t < steps) : (t += 1) {
        const r = n.step(p.fi_stim);
        if (r.fired and nf < times.len) {
            times[nf] = @intCast(t);
            nf += 1;
        }
    }
    const Tms = @as(f64, @floatFromInt(steps)); // dt=1ms
    const rate = @as(f64, @floatFromInt(nf)) / (Tms / 1000.0);
    var mean_isi: f64 = 0;
    var adapt: f64 = 0;
    if (nf >= 2) {
        var sum: f64 = 0;
        var i: usize = 1;
        while (i < nf) : (i += 1) {
            sum += @as(f64, @floatFromInt(times[i] - times[i - 1]));
        }
        mean_isi = sum / @as(f64, @floatFromInt(nf - 1));
    }
    if (nf >= 6) {
        const nisi = nf - 1;
        const k = @max(@as(usize, 1), nisi / 3);
        var early: f64 = 0;
        var late: f64 = 0;
        var i: usize = 0;
        while (i < k) : (i += 1) {
            early += @as(f64, @floatFromInt(times[i + 1] - times[i]));
            late += @as(f64, @floatFromInt(times[nisi - k + i + 1] - times[nisi - k + i]));
        }
        early /= @as(f64, @floatFromInt(k));
        late /= @as(f64, @floatFromInt(k));
        adapt = (late - early) / (late + early + 1e-6);
    }
    return .{ .rate_Hz = rate, .mean_isi_ms = mean_isi, .adapt = adapt, .spikes = @intCast(nf) };
}

pub fn runFIPopulation(params: []const UnitParamsF, steps: usize) PopReportF {
    var rep: PopReportF = .{ .n_units = @intCast(params.len) };
    if (params.len == 0) return rep;
    var sum_rate: f64 = 0;
    var sum_isi: f64 = 0;
    var sum_ad: f64 = 0;
    var n_isi: u32 = 0;
    var total_sp: u32 = 0;
    var u: usize = 0;
    while (u < params.len) : (u += 1) {
        const pr = runFIUnit(params[u], steps);
        sum_rate += pr.rate_Hz;
        sum_ad += pr.adapt;
        total_sp += pr.spikes;
        if (pr.spikes >= 2 and pr.mean_isi_ms > 0) {
            sum_isi += pr.mean_isi_ms;
            n_isi += 1;
        }
    }
    const nf: f64 = @floatFromInt(params.len);
    rep.mean_rate_Hz = sum_rate / nf;
    rep.mean_adapt = sum_ad / nf;
    rep.total_spikes = total_sp;
    rep.n_with_isi = n_isi;
    if (n_isi > 0) rep.mean_isi_ms = sum_isi / @as(f64, @floatFromInt(n_isi));
    return rep;
}

pub fn selfTest() bool {
    var p: UnitParamsF = .{};
    p.ref_steps = 40;
    p.fi_stim = fixed.fromDecimalStr("0.5");
    const pr = runFIUnit(p, 500);
    if (pr.spikes < 2) return false;
    if (pr.mean_isi_ms < 5 or pr.mean_isi_ms > 250) return false;
    if (pr.rate_Hz < 2 or pr.rate_Hz > 120) return false;
    return true;
}
