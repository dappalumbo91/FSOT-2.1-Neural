//! Biological metric probes for Zig mind — parity spirit with bio_metrics.py.
//! Host stress path; freestanding can call lite variants.

const neuron = @import("neuron.zig");
const network = @import("network.zig");
const seeds = @import("seeds.zig");

pub const MAX_T: usize = 2000;
pub const MAX_U: usize = 32;

pub const BioProfile = struct {
    firing_rate_Hz: f64 = 0,
    mean_isi_ms: f64 = 0,
    adaptation_index: f64 = 0,
    isi_cv: f64 = 0,
    mean_S: f64 = 0,
    spike_count: u32 = 0,
    mean_Vm_proxy_mV: f64 = 0,
};

pub const PopReport = struct {
    n_units: u32 = 0,
    mean_rate_Hz: f64 = 0,
    mean_isi_ms: f64 = 0,
    mean_adapt: f64 = 0,
    mean_isi_cv: f64 = 0,
    mean_S: f64 = 0,
    mean_Vm_mV: f64 = 0,
    total_spikes: u32 = 0,
    n_with_isi: u32 = 0,
};

fn isiStats(times: []const u32, n: usize, dt_ms: f64, mean_out: *f64, cv_out: *f64) void {
    if (n < 2) {
        mean_out.* = 0;
        cv_out.* = 0;
        return;
    }
    var sum: f64 = 0;
    var i: usize = 1;
    while (i < n) : (i += 1) {
        sum += @as(f64, @floatFromInt(times[i] - times[i - 1])) * dt_ms;
    }
    const nisi: f64 = @floatFromInt(n - 1);
    const mean = sum / nisi;
    mean_out.* = mean;
    var var_sum: f64 = 0;
    i = 1;
    while (i < n) : (i += 1) {
        const isi = @as(f64, @floatFromInt(times[i] - times[i - 1])) * dt_ms;
        const d = isi - mean;
        var_sum += d * d;
    }
    const stdv = @sqrt(var_sum / nisi);
    cv_out.* = if (mean > 1e-9) stdv / mean else 0;
}

fn adaptIndex(times: []const u32, n: usize) f64 {
    if (n < 4) {
        // early/late spike-count asymmetry if sparse
        return 0;
    }
    // ISIs
    const nisi = n - 1;
    if (nisi >= 6) {
        const k = @max(@as(usize, 1), nisi / 3);
        var early: f64 = 0;
        var late: f64 = 0;
        var i: usize = 0;
        while (i < k) : (i += 1) {
            early += @as(f64, @floatFromInt(times[i + 1] - times[i]));
        }
        i = 0;
        while (i < k) : (i += 1) {
            const j = nisi - k + i;
            late += @as(f64, @floatFromInt(times[j + 1] - times[j]));
        }
        early /= @as(f64, @floatFromInt(k));
        late /= @as(f64, @floatFromInt(k));
        return (late - early) / (late + early + 1e-6);
    }
    if (nisi >= 3) {
        const early = (@as(f64, @floatFromInt(times[1] - times[0])) +
            @as(f64, @floatFromInt(times[2] - times[1]))) / 2.0;
        const late = (@as(f64, @floatFromInt(times[n - 1] - times[n - 2])) +
            @as(f64, @floatFromInt(times[n - 2] - times[n - 3]))) / 2.0;
        return (late - early) / (late + early + 1e-6);
    }
    const early = @as(f64, @floatFromInt(times[1] - times[0]));
    const late = @as(f64, @floatFromInt(times[n - 1] - times[n - 2]));
    return (late - early) / (late + early + 1e-6);
}

/// Profile one unit from fire times + mean S over T steps.
pub fn profileUnit(fire_times: []const u32, n_fires: usize, mean_S: f64, steps: usize, dt_ms: f64) BioProfile {
    var mean_isi: f64 = 0;
    var cv: f64 = 0;
    isiStats(fire_times, n_fires, dt_ms, &mean_isi, &cv);
    const Tms = @as(f64, @floatFromInt(steps)) * dt_ms;
    const rate = if (Tms > 0) @as(f64, @floatFromInt(n_fires)) / (Tms / 1000.0) else 0;
    const adapt = if (n_fires >= 4) adaptIndex(fire_times, n_fires) else 0;
    const vm = -70.0 + (mean_S - seeds.resting_s) * 80.0;
    return .{
        .firing_rate_Hz = rate,
        .mean_isi_ms = mean_isi,
        .adaptation_index = adapt,
        .isi_cv = cv,
        .mean_S = mean_S,
        .spike_count = @intCast(n_fires),
        .mean_Vm_proxy_mV = vm,
    };
}

pub const UnitParams = struct {
    d_eff: f64 = seeds.neuro_d_eff,
    fire_thr: f64 = 1.05,
    ref_steps: i32 = 12,
    adapt_gain: f64 = 0.02,
    adapt_decay: f64 = 0.988,
    adapt_step: f64 = 0.7,
    fi_stim: f64 = 0.50,
};

pub fn applyParams(n: *neuron.Neuron, p: UnitParams) void {
    n.d_eff = p.d_eff;
    n.fire_thr = p.fire_thr;
    n.ref_steps = p.ref_steps;
    n.adapt_gain = p.adapt_gain;
    n.adapt_decay = p.adapt_decay;
    n.adapt_step = p.adapt_step;
}

/// Constant FI drive for `steps` (default bio protocol).
pub fn runFIUnit(p: UnitParams, steps: usize, dt_ms: f64) BioProfile {
    var n = neuron.Neuron{};
    n.dt_ms = dt_ms;
    applyParams(&n, p);
    n.reset();

    var times: [512]u32 = undefined;
    var nf: usize = 0;
    var sum_s: f64 = 0;
    var t: usize = 0;
    while (t < steps) : (t += 1) {
        const r = n.step(p.fi_stim);
        sum_s += r.S;
        if (r.fired and nf < times.len) {
            times[nf] = @intCast(t);
            nf += 1;
        }
    }
    const mean_s = sum_s / @as(f64, @floatFromInt(steps));
    return profileUnit(times[0..], nf, mean_s, steps, dt_ms);
}

/// Population FI: n_units with shared or per-unit params.
pub fn runFIPopulation(params: []const UnitParams, steps: usize, dt_ms: f64) PopReport {
    var rep: PopReport = .{};
    const n = @min(params.len, MAX_U);
    rep.n_units = @intCast(n);
    if (n == 0) return rep;

    var sum_rate: f64 = 0;
    var sum_isi: f64 = 0;
    var sum_ad: f64 = 0;
    var sum_cv: f64 = 0;
    var sum_s: f64 = 0;
    var sum_vm: f64 = 0;
    var n_isi: u32 = 0;
    var total_sp: u32 = 0;

    var u: usize = 0;
    while (u < n) : (u += 1) {
        const pr = runFIUnit(params[u], steps, dt_ms);
        sum_rate += pr.firing_rate_Hz;
        sum_s += pr.mean_S;
        sum_vm += pr.mean_Vm_proxy_mV;
        sum_ad += pr.adaptation_index;
        total_sp += pr.spike_count;
        if (pr.spike_count >= 2 and pr.mean_isi_ms > 0) {
            sum_isi += pr.mean_isi_ms;
            sum_cv += pr.isi_cv;
            n_isi += 1;
        }
    }
    const nf: f64 = @floatFromInt(n);
    rep.mean_rate_Hz = sum_rate / nf;
    rep.mean_S = sum_s / nf;
    rep.mean_Vm_mV = sum_vm / nf;
    rep.mean_adapt = sum_ad / nf;
    rep.total_spikes = total_sp;
    rep.n_with_isi = n_isi;
    if (n_isi > 0) {
        rep.mean_isi_ms = sum_isi / @as(f64, @floatFromInt(n_isi));
        rep.mean_isi_cv = sum_cv / @as(f64, @floatFromInt(n_isi));
    }
    return rep;
}

/// Periodic parity-style population (80-cycle, 20 on) — stress rate stability.
pub fn runPeriodicPopulation(n_units: usize, steps: usize, stim_hi: f64, stim_lo: f64) PopReport {
    var params: [MAX_U]UnitParams = undefined;
    const n = @min(n_units, MAX_U);
    // slight phenotype diversity
    var u: usize = 0;
    while (u < n) : (u += 1) {
        params[u] = .{
            .ref_steps = 12 + @as(i32, @intCast(u % 5)),
            .adapt_gain = 0.02 + 0.002 * @as(f64, @floatFromInt(u % 4)),
            .fi_stim = stim_hi,
        };
    }

    var rep: PopReport = .{ .n_units = @intCast(n) };
    var sum_rate: f64 = 0;
    var sum_isi: f64 = 0;
    var sum_ad: f64 = 0;
    var sum_s: f64 = 0;
    var n_isi: u32 = 0;
    var total_sp: u32 = 0;

    u = 0;
    while (u < n) : (u += 1) {
        var cell = neuron.Neuron{};
        applyParams(&cell, params[u]);
        cell.reset();
        var times: [512]u32 = undefined;
        var nf: usize = 0;
        var sum_s_u: f64 = 0;
        var t: usize = 0;
        while (t < steps) : (t += 1) {
            const stim: f64 = if ((t % 80) < 20) stim_hi else stim_lo;
            const r = cell.step(stim);
            sum_s_u += r.S;
            if (r.fired and nf < times.len) {
                times[nf] = @intCast(t);
                nf += 1;
            }
        }
        const pr = profileUnit(times[0..], nf, sum_s_u / @as(f64, @floatFromInt(steps)), steps, 1.0);
        sum_rate += pr.firing_rate_Hz;
        sum_s += pr.mean_S;
        sum_ad += pr.adaptation_index;
        total_sp += pr.spike_count;
        if (pr.spike_count >= 2 and pr.mean_isi_ms > 0) {
            sum_isi += pr.mean_isi_ms;
            n_isi += 1;
        }
    }
    const nf: f64 = @floatFromInt(n);
    rep.mean_rate_Hz = sum_rate / nf;
    rep.mean_S = sum_s / nf;
    rep.mean_adapt = sum_ad / nf;
    rep.total_spikes = total_sp;
    rep.n_with_isi = n_isi;
    if (n_isi > 0) rep.mean_isi_ms = sum_isi / @as(f64, @floatFromInt(n_isi));
    return rep;
}

/// Coupled network stress: genetic W + external FI on half units.
pub fn runNetworkStress(n_units: usize, steps: usize) struct { spikes: u32, mean_s: f64, rate_Hz: f64 } {
    const n = @min(n_units, network.MAX_N);
    var net = network.Network.init(n);
    net.setDefaultGeneticW(0.08);
    var t: usize = 0;
    var sum_s: f64 = 0;
    while (t < steps) : (t += 1) {
        var ext: [network.MAX_N]f64 = .{0.05} ** network.MAX_N;
        var k: usize = 0;
        while (k < n) : (k += 1) {
            if ((k % 2) == 0) {
                ext[k] = if ((t % 80) < 20) 0.65 else 0.08;
            }
        }
        net.step(ext[0..n]);
        k = 0;
        while (k < n) : (k += 1) sum_s += net.units[k].S;
    }
    const sp = net.totalSpikes();
    const mean_s = sum_s / @as(f64, @floatFromInt(n * steps));
    const rate = @as(f64, @floatFromInt(sp)) / (@as(f64, @floatFromInt(n)) * @as(f64, @floatFromInt(steps)) / 1000.0);
    return .{ .spikes = sp, .mean_s = mean_s, .rate_Hz = rate };
}

/// Default bio_match-ish params for n units (no Allen file).
pub fn defaultBioParams(out: []UnitParams) void {
    var i: usize = 0;
    while (i < out.len) : (i += 1) {
        // Mild diversity around cortical default (ISI ~70ms class)
        out[i] = .{
            .d_eff = 13.0 + 0.1 * @as(f64, @floatFromInt(i % 5)),
            .fire_thr = 1.05,
            .ref_steps = 45 + @as(i32, @intCast(i % 8)), // ~0.72 * 70
            .adapt_gain = 0.03,
            .adapt_decay = 0.991,
            .adapt_step = 0.7,
            .fi_stim = 0.48,
        };
    }
}

pub fn selfTest() bool {
    var p: UnitParams = .{};
    p.ref_steps = 40;
    p.fi_stim = 0.5;
    const pr = runFIUnit(p, 500, 1.0);
    // should fire under FI
    if (pr.spike_count < 2) return false;
    if (pr.mean_isi_ms < 5 or pr.mean_isi_ms > 250) return false;
    if (pr.firing_rate_Hz < 2 or pr.firing_rate_Hz > 120) return false;
    return true;
}
