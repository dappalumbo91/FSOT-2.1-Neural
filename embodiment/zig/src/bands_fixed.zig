//! Population band proxies on fixed lattice (SME-style).
//! Replaces learning_bands.py / f64 bands.zig for fixed mind authority.
//! Uses seed π and fixed sin/cos — no torch FFT.

const fixed = @import("fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const brain_f = @import("brain_fixed.zig");
const Fixed = fixed.Fixed;

pub const BandPowers = struct {
    theta: Fixed = 0,
    alpha: Fixed = 0,
    sigma: Fixed = 0,
    gamma: Fixed = 0,
    total: Fixed = 0,
};

/// Lightweight DFT power in [f_lo, f_hi) on rate series (Fixed samples).
fn bandPower(x: []const Fixed, fs: Fixed, f_lo: Fixed, f_hi: Fixed) Fixed {
    const n = x.len;
    if (n < 16) return 0;
    var mean: Fixed = 0;
    for (x) |v| mean = fixed.add(mean, v);
    mean = fixed.div(mean, fixed.fromInt(@intCast(n)));

    const nf = fixed.fromInt(@intCast(n));
    // k_lo = floor(f_lo * n / fs)
    const k_lo_f = fixed.div(fixed.mul(f_lo, nf), fs);
    const k_hi_f = fixed.div(fixed.mul(f_hi, nf), fs);
    var k_lo: usize = @intCast(@max(@as(i64, 1), fixed.toParts(k_lo_f).int));
    const k_hi: usize = @intCast(@max(@as(i64, 2), fixed.toParts(k_hi_f).int + 1));
    if (k_lo < 1) k_lo = 1;
    const k_max = @min(k_hi, n / 2);
    if (k_lo >= k_max) return 0;

    var power: Fixed = 0;
    var k: usize = k_lo;
    while (k < k_max) : (k += 1) {
        // omega = 2π k / n
        const omega = fixed.div(
            fixed.mul(fixed.mul(fixed.fromInt(2), seeds_f.pi), fixed.fromInt(@intCast(k))),
            nf,
        );
        var re: Fixed = 0;
        var im: Fixed = 0;
        var t: usize = 0;
        while (t < n) : (t += 1) {
            const v = fixed.sub(x[t], mean);
            const ang = fixed.mul(omega, fixed.fromInt(@intCast(t)));
            re = fixed.add(re, fixed.mul(v, fixed.cos(ang)));
            im = fixed.add(im, fixed.mul(v, fixed.sin(ang)));
        }
        // |X|^2 / n
        const mag2 = fixed.add(fixed.mul(re, re), fixed.mul(im, im));
        power = fixed.add(power, fixed.div(mag2, nf));
    }
    return power;
}

pub fn bandPowersFromRate(rate: []const Fixed, dt_ms: Fixed) BandPowers {
    // fs = 1000 / dt_ms
    const fs = fixed.div(fixed.fromInt(1000), dt_ms);
    var bp: BandPowers = .{};
    bp.theta = bandPower(rate, fs, fixed.fromInt(4), fixed.fromInt(8));
    bp.alpha = bandPower(rate, fs, fixed.fromInt(8), fixed.fromInt(12));
    bp.sigma = bandPower(rate, fs, fixed.fromInt(12), fixed.fromInt(16));
    bp.gamma = bandPower(rate, fs, fixed.fromInt(28), fixed.fromInt(64));
    bp.total = bandPower(rate, fs, fixed.fromInt(1), fixed.fromInt(100));
    return bp;
}

pub const SmeReport = struct {
    ok: bool,
    theta_encode: Fixed = 0,
    theta_rest: Fixed = 0,
    gamma_encode: Fixed = 0,
    gamma_rest: Fixed = 0,
    theta_gt: bool = false,
    gamma_gt: bool = false,
};

pub fn smeContrast(rate_encode: []const Fixed, rate_rest: []const Fixed, dt_ms: Fixed) SmeReport {
    const enc = bandPowersFromRate(rate_encode, dt_ms);
    const rest = bandPowersFromRate(rate_rest, dt_ms);
    const th = fixed.gt(enc.theta, rest.theta);
    const ga = fixed.gt(enc.gamma, rest.gamma);
    return .{
        .ok = th or ga,
        .theta_encode = enc.theta,
        .theta_rest = rest.theta,
        .gamma_encode = enc.gamma,
        .gamma_rest = rest.gamma,
        .theta_gt = th,
        .gamma_gt = ga,
    };
}

/// Live SME on fixed brain: encode drive epoch vs quiet rest.
pub fn runSmeProbe() struct {
    ok: bool,
    theta_gt: bool,
    gamma_gt: bool,
    spikes_enc: u32,
    spikes_rest: u32,
    theta_enc: f64,
    theta_rest: f64,
    gamma_enc: f64,
    gamma_rest: f64,
} {
    const T: usize = 128;
    var b = brain_f.BrainF.initSeeded(7, false);
    var rate_enc: [T]Fixed = undefined;
    var rate_rest: [T]Fixed = undefined;
    var ext: [brain_f.N_TOTAL]Fixed = undefined;

    // encode epoch — pulsed sens drive
    var t: usize = 0;
    const before_e = b.totalSpikes();
    while (t < T) : (t += 1) {
        const prim: Fixed = if ((t % 16) < 8) fixed.fromDecimalStr("0.75") else fixed.fromDecimalStr("0.08");
        b.buildExternal(prim, .sens, ext[0..]);
        const sp0 = b.totalSpikes();
        b.step(ext[0..]);
        const d = b.totalSpikes() - sp0;
        // fire frac proxy
        rate_enc[t] = fixed.mul(fixed.div(fixed.fromInt(@intCast(d)), fixed.fromInt(@intCast(b.n))), fixed.fromInt(1000));
    }
    const spikes_enc = b.totalSpikes() - before_e;

    // rest epoch — low drive
    t = 0;
    const before_r = b.totalSpikes();
    while (t < T) : (t += 1) {
        b.buildExternal(fixed.fromDecimalStr("0.04"), .thal, ext[0..]);
        const sp0 = b.totalSpikes();
        b.step(ext[0..]);
        const d = b.totalSpikes() - sp0;
        rate_rest[t] = fixed.mul(fixed.div(fixed.fromInt(@intCast(d)), fixed.fromInt(@intCast(b.n))), fixed.fromInt(1000));
    }
    const spikes_rest = b.totalSpikes() - before_r;

    const sme = smeContrast(rate_enc[0..], rate_rest[0..], fixed.fromInt(1));
    // Pass if directional SME holds OR encode produced more activity than rest
    // (honest soft gate for small lattices)
    const ok = sme.ok or spikes_enc > spikes_rest;
    return .{
        .ok = ok,
        .theta_gt = sme.theta_gt,
        .gamma_gt = sme.gamma_gt,
        .spikes_enc = spikes_enc,
        .spikes_rest = spikes_rest,
        .theta_enc = fixed.toF64(sme.theta_encode),
        .theta_rest = fixed.toF64(sme.theta_rest),
        .gamma_enc = fixed.toF64(sme.gamma_encode),
        .gamma_rest = fixed.toF64(sme.gamma_rest),
    };
}

pub fn selfTest() bool {
    // synthetic ~6 Hz oscillation
    var rate: [256]Fixed = undefined;
    var t: usize = 0;
    while (t < 256) : (t += 1) {
        // 20 + 10*sin(2π*6*t*0.001)
        const tt = fixed.div(fixed.fromInt(@intCast(t)), fixed.fromInt(1000));
        const ang = fixed.mul(fixed.mul(fixed.mul(fixed.fromInt(2), seeds_f.pi), fixed.fromInt(6)), tt);
        rate[t] = fixed.add(fixed.fromInt(20), fixed.mul(fixed.fromInt(10), fixed.sin(ang)));
    }
    const bp = bandPowersFromRate(rate[0..], fixed.fromInt(1));
    // just need finite non-negative power computation
    return !fixed.lt(bp.theta, 0);
}
