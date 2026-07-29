//! Encode–delay–retrieve on fixed genetic brain (replaces learning.zig for mind authority).

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const Fixed = fixed.Fixed;

pub const N_ITEMS: usize = 6;
pub const FP_DIM: usize = brain_f.N_TOTAL * 2;
pub const ENCODE_STEPS: usize = 40;
pub const RETRIEVE_STEPS: usize = 30;
pub const DELAY_STEPS: usize = 15;
pub const HEBB_LR: Fixed = fixed.fromDecimalStr("0.012");
pub const HEBB_CAP: Fixed = fixed.fromDecimalStr("0.45");

fn itemFeat(item: usize, u: usize) Fixed {
    const a: u32 = @intCast(item *% 7919 + u *% 104729 + 17);
    const b: u32 = @intCast((item + 1) *% (u + 3) *% 9973);
    const x = fixed.sub(fixed.div(fixed.fromInt(@intCast(a % 1000)), fixed.fromInt(500)), fixed.fromInt(1));
    const y = fixed.div(fixed.fromInt(@intCast(b % 1000)), fixed.fromInt(1000));
    return fixed.add(fixed.mul(fixed.fromDecimalStr("0.7"), x), fixed.mul(fixed.fromDecimalStr("0.3"), fixed.sub(fixed.mul(y, fixed.fromInt(2)), fixed.fromInt(1))));
}

fn hebbStep(b: *brain_f.BrainF) void {
    const n = b.n;
    var post: usize = 0;
    while (post < n) : (post += 1) {
        if (b.genotypes[post].synapse_sign <= 0) continue;
        if (!b.net.last_fired[post] and fixed.lt(b.net.units[post].S, fixed.fromDecimalStr("0.55"))) continue;
        var pre: usize = 0;
        while (pre < n) : (pre += 1) {
            if (pre == post) continue;
            if (b.genotypes[pre].synapse_sign <= 0) continue;
            if (!b.net.last_fired[pre]) continue;
            const idx = post * @import("network_fixed.zig").MAX_N + pre;
            var w = b.net.W[idx];
            w = fixed.add(w, HEBB_LR);
            if (fixed.gt(w, HEBB_CAP)) w = HEBB_CAP;
            if (fixed.lt(w, fixed.negate(HEBB_CAP))) w = fixed.negate(HEBB_CAP);
            b.net.W[idx] = w;
        }
    }
}

fn buildDrive(b: *const brain_f.BrainF, item: usize, t: usize, partial: bool, out: []Fixed) void {
    const n = b.n;
    const packet = (t % 80) < 20;
    var u: usize = 0;
    while (u < n and u < out.len) : (u += 1) {
        var e = fixed.fromDecimalStr("0.04");
        const silenced = partial and (u >= (2 * n) / 3);
        const f = if (silenced) 0 else itemFeat(item, u);
        switch (b.region_of[u]) {
            .thal => {
                if (packet) e = fixed.add(e, if (b.genotypes[u].synapse_sign > 0) fixed.fromDecimalStr("0.55") else fixed.fromDecimalStr("0.18"));
                e = fixed.add(e, fixed.div(fixed.mul(fixed.fromDecimalStr("0.18"), f), seeds_f.phi));
            },
            .sens => e = fixed.add(e, fixed.mul(fixed.fromDecimalStr("0.55"), f)),
            .assoc => e = fixed.add(e, fixed.mul(fixed.fromDecimalStr("0.42"), f)),
            .hipp => e = fixed.add(e, fixed.mul(fixed.fromDecimalStr("0.48"), f)),
        }
        out[u] = fixed.clamp(e, fixed.fromDecimalStr("-0.8"), fixed.fromDecimalStr("1.5"));
    }
}

fn fingerprint(b: *brain_f.BrainF, item: usize, steps: usize, partial: bool, apply_hebb: bool, out: *[FP_DIM]Fixed) void {
    var u: usize = 0;
    while (u < b.n) : (u += 1) {
        const kept = b.net.units[u].spike_count;
        b.net.units[u].reset();
        b.net.units[u].spike_count = kept;
        b.net.last_fired[u] = false;
    }
    var sum_s: [brain_f.N_TOTAL]Fixed = .{0} ** brain_f.N_TOTAL;
    var sum_f: [brain_f.N_TOTAL]Fixed = .{0} ** brain_f.N_TOTAL;
    var ext: [brain_f.N_TOTAL]Fixed = undefined;
    var t: usize = 0;
    while (t < steps) : (t += 1) {
        buildDrive(b, item, t, partial, ext[0..]);
        b.step(ext[0..]);
        if (apply_hebb) hebbStep(b);
        u = 0;
        while (u < b.n) : (u += 1) {
            sum_s[u] = fixed.add(sum_s[u], b.net.units[u].S);
            if (b.net.last_fired[u]) sum_f[u] = fixed.add(sum_f[u], fixed.fromInt(1));
        }
    }
    const sf = fixed.fromInt(@intCast(steps));
    u = 0;
    while (u < b.n) : (u += 1) {
        out[u] = fixed.div(sum_s[u], sf);
        out[brain_f.N_TOTAL + u] = fixed.div(sum_f[u], sf);
    }
}

fn cosine(a: *const [FP_DIM]Fixed, b: *const [FP_DIM]Fixed) Fixed {
    var dot: Fixed = 0;
    var na: Fixed = 0;
    var nb: Fixed = 0;
    var i: usize = 0;
    while (i < FP_DIM) : (i += 1) {
        dot = fixed.add(dot, fixed.mul(a[i], b[i]));
        na = fixed.add(na, fixed.mul(a[i], a[i]));
        nb = fixed.add(nb, fixed.mul(b[i], b[i]));
    }
    if (fixed.lt(na, fixed.fromDecimalStr("0.000000000001")) or fixed.lt(nb, fixed.fromDecimalStr("0.000000000001"))) return 0;
    return fixed.div(dot, fixed.mul(fixed.sqrt(na), fixed.sqrt(nb)));
}

pub const LearnReport = struct {
    ok: bool,
    top1: f64,
    correct: u32,
    n_items: u32,
    mean_s_plus: f64,
    mean_s_minus: f64,
    spikes: u32,
};

pub fn runLearnProbe() LearnReport {
    var b = brain_f.BrainF.initSeeded(42, false);
    var fps: [N_ITEMS][FP_DIM]Fixed = undefined;
    var i: usize = 0;
    while (i < N_ITEMS) : (i += 1) {
        fingerprint(&b, i, ENCODE_STEPS, false, true, &fps[i]);
    }
    var ext: [brain_f.N_TOTAL]Fixed = .{fixed.fromDecimalStr("0.05")} ** brain_f.N_TOTAL;
    var d: usize = 0;
    while (d < DELAY_STEPS) : (d += 1) b.step(ext[0..]);

    var correct: u32 = 0;
    var sum_plus: Fixed = 0;
    var sum_minus: Fixed = 0;
    var n_minus: i64 = 0;
    i = 0;
    while (i < N_ITEMS) : (i += 1) {
        var cue: [FP_DIM]Fixed = undefined;
        fingerprint(&b, i, RETRIEVE_STEPS, true, false, &cue);
        var best: usize = 0;
        var best_s: Fixed = fixed.fromInt(-2);
        var j: usize = 0;
        while (j < N_ITEMS) : (j += 1) {
            const s = cosine(&cue, &fps[j]);
            if (fixed.gt(s, best_s)) {
                best_s = s;
                best = j;
            }
            if (j == i) sum_plus = fixed.add(sum_plus, s) else {
                sum_minus = fixed.add(sum_minus, s);
                n_minus += 1;
            }
        }
        if (best == i) correct += 1;
    }
    const top1 = @as(f64, @floatFromInt(correct)) / @as(f64, @floatFromInt(N_ITEMS));
    const ms_plus = fixed.toF64(fixed.div(sum_plus, fixed.fromInt(N_ITEMS)));
    const ms_minus = if (n_minus > 0) fixed.toF64(fixed.div(sum_minus, fixed.fromInt(n_minus))) else 0;
    return .{
        .ok = top1 >= 0.5 and ms_plus > ms_minus + 0.01,
        .top1 = top1,
        .correct = correct,
        .n_items = N_ITEMS,
        .mean_s_plus = ms_plus,
        .mean_s_minus = ms_minus,
        .spikes = b.totalSpikes(),
    };
}
