//! Spike-timing-dependent plasticity (STDP) on Fixed lattice.
//!
//! Bio: classical STDP — pre→post (causal, Δt>0 small) potentiates;
//! post→pre (anti-causal) depresses (Bi & Poo; Song, Miller, Abbott).
//!
//! FSOT solidification of the update:
//!   Δw = η * s * fsotPairWeight(spin_pre, spin_post, q_pre, q_post, dist)
//!   s  = +1 causal LTP window, −1 anti-causal LTD window, 0 outside
//!   η  = HEBB_LR * psi_con  (FSOT consciousness-coupling scale)
//!
//! Not full molecular cascade (CaMKII, AMPA trafficking) — that is the next depth.

const fixed = @import("fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const genetic_f = @import("genetic_fixed.zig");
const brain_f = @import("brain_fixed.zig");
const network_f = @import("network_fixed.zig");
const Fixed = fixed.Fixed;

/// Causal window (pre then post) in ticks — coarse discrete STDP.
pub const CAUSAL_WIN: i32 = 8;
/// Anti-causal window (post then pre).
pub const ANTI_WIN: i32 = 8;

pub const STDP_CAP: Fixed = fixed.fromDecimalStr("0.45");

/// η base = 0.012 * ψ_con  (learning_fixed HEBB_LR * FSOT seed)
pub fn etaStdp() Fixed {
    return fixed.mul(fixed.fromDecimalStr("0.012"), seeds_f.psi_con);
}

/// Sign of STDP from discrete fire times (tick of last spike).
/// Returns +1 LTP, -1 LTD, 0 no update.
pub fn stdpSign(t_pre: i32, t_post: i32) i8 {
    if (t_pre < 0 or t_post < 0) return 0;
    const dt: i32 = t_post - t_pre; // >0 means pre before post (causal)
    if (dt > 0 and dt <= CAUSAL_WIN) return 1;
    if (dt < 0 and (-dt) <= ANTI_WIN) return -1;
    if (dt == 0) return 1; // same-step co-fire: weak Hebbian LTP
    return 0;
}

/// FSOT-scaled weight delta for one pre→post pair.
pub fn fsotStdpDelta(
    spin_pre: Fixed,
    spin_post: Fixed,
    charge_pre: Fixed,
    charge_post: Fixed,
    dist: usize,
    sign: i8,
) Fixed {
    if (sign == 0) return 0;
    const pair = genetic_f.fsotPairWeight(spin_pre, spin_post, charge_pre, charge_post, if (dist < 1) 1 else dist);
    // normalize pair influence into modest scale
    const scaled = fixed.mul(pair, fixed.fromDecimalStr("0.02"));
    const mag = fixed.mul(etaStdp(), fixed.add(fixed.fromDecimalStr("0.5"), fixed.abs(scaled)));
    if (sign > 0) return mag;
    return fixed.negate(mag);
}

/// Apply STDP over the network using last_spike_tick[i].
/// Returns number of edges updated.
pub fn applyStdpEpoch(
    b: *brain_f.BrainF,
    last_spike_tick: []const i32,
    global_tick: i32,
) u32 {
    _ = global_tick;
    var n_upd: u32 = 0;
    const n = b.n;
    var post: usize = 0;
    while (post < n) : (post += 1) {
        if (b.genotypes[post].synapse_sign <= 0) continue;
        var pre: usize = 0;
        while (pre < n) : (pre += 1) {
            if (pre == post) continue;
            if (b.genotypes[pre].synapse_sign <= 0) continue;
            const sgn = stdpSign(last_spike_tick[pre], last_spike_tick[post]);
            if (sgn == 0) continue;
            const dist = if (post > pre) post - pre else pre - post;
            const dw = fsotStdpDelta(
                b.genotypes[pre].composite_spin,
                b.genotypes[post].composite_spin,
                b.genotypes[pre].composite_charge,
                b.genotypes[post].composite_charge,
                dist,
                sgn,
            );
            if (dw == 0) continue;
            const idx = post * network_f.MAX_N + pre;
            var w = b.net.W[idx];
            // synaptogenesis: absent contact gets FSOT-seeded birth weight
            if (w == 0 and sgn > 0) {
                w = fixed.mul(
                    genetic_f.fsotPairWeight(
                        b.genotypes[pre].composite_spin,
                        b.genotypes[post].composite_spin,
                        b.genotypes[pre].composite_charge,
                        b.genotypes[post].composite_charge,
                        dist + 1,
                    ),
                    fixed.fromDecimalStr("0.01"),
                );
            }
            w = fixed.add(w, dw);
            if (fixed.gt(w, STDP_CAP)) w = STDP_CAP;
            if (fixed.lt(w, fixed.negate(STDP_CAP))) w = fixed.negate(STDP_CAP);
            // prune near-zero anti-causal remnants
            if (fixed.lt(fixed.abs(w), fixed.fromDecimalStr("0.002")) and sgn < 0) w = 0;
            b.net.W[idx] = w;
            n_upd += 1;
        }
    }
    return n_upd;
}

pub fn selfTest() bool {
    // causal pre then post → LTP sign
    if (stdpSign(10, 14) != 1) return false;
    // anti-causal → LTD
    if (stdpSign(14, 10) != -1) return false;
    // far → 0
    if (stdpSign(1, 100) != 0) return false;
    const d = fsotStdpDelta(
        fixed.fromDecimalStr("0.5"),
        fixed.fromDecimalStr("-0.2"),
        fixed.fromDecimalStr("0.1"),
        fixed.fromDecimalStr("0.1"),
        2,
        1,
    );
    return fixed.gt(d, 0);
}
