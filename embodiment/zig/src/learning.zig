//! Encode → delay → retrieve on Zig multi-region brain (mind-native learning).
//! Replaces Python learning_memory encode/retrieve probe as mind authority.
//!
//! Fingerprint = per-unit mean S + spike duty (parity spirit with
//! fingerprint_from_hist). Simple Hebbian on co-active E→E during encode.

const brain = @import("brain.zig");
const network = @import("network.zig");
const seeds = @import("seeds.zig");

pub const N_ITEMS: usize = 6;
pub const FP_DIM: usize = brain.N_TOTAL * 2; // mean S + duty per unit
pub const ENCODE_STEPS: usize = 60;
pub const RETRIEVE_STEPS: usize = 45;
pub const DELAY_STEPS: usize = 25;
pub const HEBB_LR: f64 = 0.012;
pub const HEBB_CAP: f64 = 0.45;

/// Deterministic item feature in [-1, 1] — unit-unique and item-unique.
fn itemFeat(item: usize, u: usize) f64 {
    const a: u32 = @intCast(item *% 7919 + u *% 104729 + 17);
    const b: u32 = @intCast((item + 1) *% (u + 3) *% 9973);
    const x = @as(f64, @floatFromInt(a % 1000)) / 500.0 - 1.0;
    const y = @as(f64, @floatFromInt(b % 1000)) / 1000.0;
    return 0.7 * x + 0.3 * (2.0 * y - 1.0);
}

fn clamp(x: f64, lo: f64, hi: f64) f64 {
    if (x < lo) return lo;
    if (x > hi) return hi;
    return x;
}

/// Drive external vector for an item (encode = full, retrieve = partial cue).
fn buildItemDrive(
    b: *const brain.Brain,
    item: usize,
    t: usize,
    partial: bool,
    out: []f64,
) void {
    const n = b.n;
    const packet: bool = (t % 80) < 20;
    var u: usize = 0;
    while (u < n and u < out.len) : (u += 1) {
        var e: f64 = 0.04;
        const feat = itemFeat(item, u);
        // partial cue: zero last third of feature space (by unit index)
        const silenced = partial and (u >= (2 * n) / 3);
        const f = if (silenced) 0.0 else feat;
        switch (b.region_of[u]) {
            .thal => {
                if (packet) e += if ((u % 2) == 0) 0.55 else 0.18;
                e += 0.18 * f / seeds.phi;
            },
            .sens => {
                e += 0.55 * f;
                if (packet) e += 0.12;
            },
            .assoc => {
                e += 0.42 * f;
            },
            .hipp => {
                e += 0.48 * f; // episodic binding
            },
        }
        out[u] = clamp(e, -0.8, 1.5);
    }
}

/// One-step Hebbian on pre-fired E → post E synapses (local scale).
fn hebbStep(b: *brain.Brain) void {
    const n = b.n;
    var post: usize = 0;
    while (post < n) : (post += 1) {
        if ((post % 2) != 0) continue; // E post only
        if (!b.net.last_fired[post] and b.net.units[post].S < 0.55) continue;
        var pre: usize = 0;
        while (pre < n) : (pre += 1) {
            if (pre == post) continue;
            if ((pre % 2) != 0) continue; // E pre
            if (!b.net.last_fired[pre]) continue;
            const idx = post * network.MAX_N + pre;
            var w = b.net.W[idx];
            w += HEBB_LR;
            if (w > HEBB_CAP) w = HEBB_CAP;
            if (w < -HEBB_CAP) w = -HEBB_CAP;
            b.net.W[idx] = w;
        }
    }
}

fn fingerprint(
    b: *brain.Brain,
    item: usize,
    steps: usize,
    partial: bool,
    apply_hebb: bool,
    out: *[FP_DIM]f64,
) void {
    // Do NOT full-reset weights: plastic store survives encode→retrieve.
    // Soft-reset unit state only so dynamics start clean for this epoch.
    var u: usize = 0;
    while (u < b.n) : (u += 1) {
        b.net.units[u].reset();
        b.net.last_fired[u] = false;
    }

    var sum_s: [brain.N_TOTAL]f64 = .{0} ** brain.N_TOTAL;
    var sum_f: [brain.N_TOTAL]f64 = .{0} ** brain.N_TOTAL;
    var ext: [brain.N_TOTAL]f64 = undefined;
    var t: usize = 0;
    while (t < steps) : (t += 1) {
        buildItemDrive(b, item, t, partial, ext[0..]);
        b.step(ext[0..]);
        if (apply_hebb) hebbStep(b);
        u = 0;
        while (u < b.n) : (u += 1) {
            sum_s[u] += b.net.units[u].S;
            if (b.net.last_fired[u]) sum_f[u] += 1.0;
        }
    }
    const sf: f64 = @floatFromInt(steps);
    u = 0;
    while (u < b.n) : (u += 1) {
        out[u] = sum_s[u] / sf;
        out[brain.N_TOTAL + u] = sum_f[u] / sf;
    }
}

fn cosine(a: *const [FP_DIM]f64, bvec: *const [FP_DIM]f64) f64 {
    var dot: f64 = 0;
    var na: f64 = 0;
    var nb: f64 = 0;
    var i: usize = 0;
    while (i < FP_DIM) : (i += 1) {
        dot += a[i] * bvec[i];
        na += a[i] * a[i];
        nb += bvec[i] * bvec[i];
    }
    if (na < 1e-18 or nb < 1e-18) return 0;
    return dot / (@sqrt(na) * @sqrt(nb));
}

pub const LearnReport = struct {
    ok: bool,
    top1: f64,
    n_items: u32,
    correct: u32,
    mean_s_plus: f64,
    mean_s_minus: f64,
    spikes: u32,
};

/// Full encode all items (with Hebb) → delay noise → retrieve each by partial cue.
pub fn runLearnProbe() LearnReport {
    var b = brain.Brain.init();
    var fps: [N_ITEMS][FP_DIM]f64 = undefined;

    // encode store (plastic)
    var i: usize = 0;
    while (i < N_ITEMS) : (i += 1) {
        fingerprint(&b, i, ENCODE_STEPS, false, true, &fps[i]);
    }

    // delay: unstructured drive (no item pattern)
    var ext: [brain.N_TOTAL]f64 = .{0.05} ** brain.N_TOTAL;
    var d: usize = 0;
    while (d < DELAY_STEPS) : (d += 1) {
        b.step(ext[0..]);
    }

    var correct: u32 = 0;
    var sum_plus: f64 = 0;
    var sum_minus: f64 = 0;
    var n_minus: f64 = 0;
    i = 0;
    while (i < N_ITEMS) : (i += 1) {
        var cue: [FP_DIM]f64 = undefined;
        // retrieve: partial cue, no further Hebb (read-out)
        fingerprint(&b, i, RETRIEVE_STEPS, true, false, &cue);
        var best: usize = 0;
        var best_s: f64 = -2;
        var j: usize = 0;
        while (j < N_ITEMS) : (j += 1) {
            const s = cosine(&cue, &fps[j]);
            if (s > best_s) {
                best_s = s;
                best = j;
            }
            if (j == i) {
                sum_plus += s;
            } else {
                sum_minus += s;
                n_minus += 1;
            }
        }
        if (best == i) correct += 1;
    }
    const top1 = @as(f64, @floatFromInt(correct)) / @as(f64, @floatFromInt(N_ITEMS));
    const ms_plus = sum_plus / @as(f64, @floatFromInt(N_ITEMS));
    const ms_minus = if (n_minus > 0) sum_minus / n_minus else 0;
    return .{
        .ok = top1 >= 0.5 and ms_plus > ms_minus + 0.01,
        .top1 = top1,
        .n_items = N_ITEMS,
        .correct = correct,
        .mean_s_plus = ms_plus,
        .mean_s_minus = ms_minus,
        .spikes = b.totalSpikes(),
    };
}
