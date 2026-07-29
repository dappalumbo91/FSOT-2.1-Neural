//! Population oscillatory band proxies from spike trains (SME-style).
//! Replaces fsot_nuron/learning_bands.py for Zig mind (no torch FFT).

const seeds = @import("seeds.zig");

pub const BandPowers = struct {
    theta: f64 = 0,
    alpha: f64 = 0,
    sigma: f64 = 0,
    gamma: f64 = 0,
    total: f64 = 0,
    theta_rel: f64 = 0,
    alpha_rel: f64 = 0,
    sigma_rel: f64 = 0,
    gamma_rel: f64 = 0,
};

/// DFT band power on real signal (Goertzel-style sum of bins).
fn bandPower(x: []const f64, fs: f64, f_lo: f64, f_hi: f64) f64 {
    const n = x.len;
    if (n < 16) return 0;
    // mean remove
    var mean: f64 = 0;
    for (x) |v| mean += v;
    mean /= @as(f64, @floatFromInt(n));

    // Periodogram via DFT of length n (O(n^2) but T~512 is fine)
    // Only sum power in frequency bins [f_lo, f_hi)
    var power: f64 = 0;
    const nf: f64 = @floatFromInt(n);
    // k for freq = k * fs / n
    const k_lo: usize = @intFromFloat(@floor(f_lo * nf / fs));
    const k_hi: usize = @intFromFloat(@ceil(f_hi * nf / fs));
    var k: usize = if (k_lo < 1) 1 else k_lo;
    const k_max = @min(k_hi, n / 2);
    while (k < k_max) : (k += 1) {
        const omega = 2.0 * seeds.pi * @as(f64, @floatFromInt(k)) / nf;
        var re: f64 = 0;
        var im: f64 = 0;
        var t: usize = 0;
        while (t < n) : (t += 1) {
            const v = x[t] - mean;
            const ang = omega * @as(f64, @floatFromInt(t));
            re += v * @cos(ang);
            im += v * @sin(ang);
        }
        power += (re * re + im * im) / nf;
    }
    return power;
}

/// fired_frac[t] = fraction of units firing at step t (0..1).
/// Convert to rate Hz = frac * (1000/dt_ms), then band-power.
pub fn bandPowersFromRate(rate_hz: []const f64, dt_ms: f64) BandPowers {
    const fs = 1000.0 / dt_ms;
    var bp: BandPowers = .{};
    bp.theta = bandPower(rate_hz, fs, 4.0, 8.0);
    bp.alpha = bandPower(rate_hz, fs, 8.0, 12.0);
    bp.sigma = bandPower(rate_hz, fs, 12.0, 16.0);
    bp.gamma = bandPower(rate_hz, fs, 28.0, 64.0);
    bp.total = bandPower(rate_hz, fs, 1.0, @min(fs / 2.0 - 1.0, 100.0));
    const tot = if (bp.total > 1e-18) bp.total else 1.0;
    bp.theta_rel = bp.theta / tot;
    bp.alpha_rel = bp.alpha / tot;
    bp.sigma_rel = bp.sigma / tot;
    bp.gamma_rel = bp.gamma / tot;
    return bp;
}

pub const SmeReport = struct {
    ok: bool,
    theta_encode: f64,
    theta_rest: f64,
    gamma_encode: f64,
    gamma_rest: f64,
    theta_gt: bool,
    gamma_gt: bool,
};

/// SME-style: encoding epoch vs rest — expect theta/gamma elevation direction.
pub fn smeContrast(rate_encode: []const f64, rate_rest: []const f64, dt_ms: f64) SmeReport {
    const enc = bandPowersFromRate(rate_encode, dt_ms);
    const rest = bandPowersFromRate(rate_rest, dt_ms);
    const th = enc.theta > rest.theta;
    const ga = enc.gamma > rest.gamma;
    return .{
        .ok = th or ga, // directional: at least one elevation
        .theta_encode = enc.theta,
        .theta_rest = rest.theta,
        .gamma_encode = enc.gamma,
        .gamma_rest = rest.gamma,
        .theta_gt = th,
        .gamma_gt = ga,
    };
}

pub fn selfTest() bool {
    // synthetic ~6 Hz oscillation in rate
    var rate: [256]f64 = undefined;
    var t: usize = 0;
    while (t < 256) : (t += 1) {
        const tt = @as(f64, @floatFromInt(t)) * 0.001; // 1 ms
        rate[t] = 20.0 + 10.0 * @sin(2.0 * seeds.pi * 6.0 * tt);
    }
    const bp = bandPowersFromRate(rate[0..], 1.0);
    if (bp.theta <= 0) return false;
    // theta should dominate gamma for pure 6 Hz
    if (bp.theta < bp.gamma * 0.5 and bp.theta_rel < 0.05) return false;
    return true;
}
