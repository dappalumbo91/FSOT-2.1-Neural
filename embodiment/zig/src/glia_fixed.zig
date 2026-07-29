//! Glial modulation layer on Fixed lattice (FSOT-seeded, no free IEEE mind).
//!
//! Human maps (simplified, claimable process — not full wet biophysics):
//!   Astrocytes (tripartite synapse)
//!     - clear / buffer "transmitter" load after spikes
//!     - supply metabolic factor that scales plasticity η
//!     - local calcium-like slow wave (supply oscillation)
//!   Microglia
//!     - activity-dependent prune bias (weaken idle / over-strong edges)
//!   Oligodendrocytes
//!     - myelination stand-in: scale effective conduction of strong long-range W
//!
//! FSOT solidification:
//!   supply  += poof·activity − suction·load   (seeds)
//!   η_eff   = η_base · (c_eff + psi_con·supply)
//!   prune   ∝ (1 − supply) · micro_gain
//!
//! Hardware is silicon; glia here is **process code** coupled to genetic W.

const fixed = @import("fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const brain_f = @import("brain_fixed.zig");
const network_f = @import("network_fixed.zig");
const Fixed = fixed.Fixed;

pub const N_ASTRO: usize = 8; // coarse tiling over units (every 4 units → 1 astro)

pub const GliaState = struct {
    /// Astrocyte metabolic supply per tile [0,1]-ish Fixed
    supply: [N_ASTRO]Fixed = .{0} ** N_ASTRO,
    /// Transmitter / glutamate-like load per tile
    load: [N_ASTRO]Fixed = .{0} ** N_ASTRO,
    /// Slow Ca-like phase per tile
    ca_phase: [N_ASTRO]Fixed = .{0} ** N_ASTRO,
    /// Microglia prune readiness [0,1]
    micro: Fixed = fixed.fromDecimalStr("0.2"),
    /// Oligo myelination gain for long-range strong edges
    myelo: Fixed = fixed.fromDecimalStr("0.15"),
    tick: u32 = 0,
    n_clear_events: u32 = 0,
    n_prune_events: u32 = 0,
    n_myelo_events: u32 = 0,

    pub fn init() GliaState {
        var g: GliaState = .{};
        var i: usize = 0;
        while (i < N_ASTRO) : (i += 1) {
            g.supply[i] = fixed.fromDecimalStr("0.55");
            g.load[i] = 0;
            g.ca_phase[i] = fixed.div(fixed.fromInt(@intCast(i)), fixed.fromInt(N_ASTRO));
        }
        return g;
    }

    fn tileOf(unit: usize) usize {
        return @min(unit / 4, N_ASTRO - 1);
    }

    /// After a network step: deposit load from spikes, clear with supply, update Ca phase.
    pub fn stepAfterSpikes(self: *GliaState, b: *const brain_f.BrainF) void {
        self.tick += 1;
        // deposit
        var i: usize = 0;
        while (i < b.n) : (i += 1) {
            if (!b.net.last_fired[i]) continue;
            const t = tileOf(i);
            // load += poof (release)
            self.load[t] = fixed.add(self.load[t], seeds_f.poof);
        }
        // astrocyte clear + supply dynamics
        i = 0;
        while (i < N_ASTRO) : (i += 1) {
            // clear load with suction · supply
            const cleared = fixed.mul(seeds_f.suction, fixed.add(self.supply[i], fixed.fromDecimalStr("0.1")));
            if (fixed.gt(self.load[i], cleared)) {
                self.load[i] = fixed.sub(self.load[i], cleared);
                self.n_clear_events += 1;
            } else {
                if (fixed.gt(self.load[i], 0)) self.n_clear_events += 1;
                self.load[i] = 0;
            }
            // supply: recover toward c_eff, depleted by load, boosted by activity residue
            // supply' = supply + α*(c_eff - supply) - β*load + γ*poof_leak
            const err = fixed.sub(seeds_f.c_eff, self.supply[i]);
            const rec = fixed.mul(fixed.fromDecimalStr("0.08"), err);
            const drain = fixed.mul(fixed.fromDecimalStr("0.12"), self.load[i]);
            self.supply[i] = fixed.add(self.supply[i], fixed.sub(rec, drain));
            // slow Ca-like phase advance (astrocyte wave)
            self.ca_phase[i] = fixed.add(self.ca_phase[i], fixed.fromDecimalStr("0.07"));
            if (fixed.gt(self.ca_phase[i], fixed.fromInt(1))) {
                self.ca_phase[i] = fixed.sub(self.ca_phase[i], fixed.fromInt(1));
                // Ca peak briefly boosts supply
                self.supply[i] = fixed.add(self.supply[i], fixed.mul(seeds_f.poof, fixed.fromDecimalStr("0.5")));
            }
            self.supply[i] = fixed.clamp(self.supply[i], fixed.fromDecimalStr("0.05"), fixed.fromInt(1));
            self.load[i] = fixed.clamp(self.load[i], 0, fixed.fromInt(2));
        }
        // microglia: rises when average load high (inflammation/surveillance stand-in)
        var sum_load: Fixed = 0;
        i = 0;
        while (i < N_ASTRO) : (i += 1) sum_load = fixed.add(sum_load, self.load[i]);
        const mean_load = fixed.div(sum_load, fixed.fromInt(N_ASTRO));
        self.micro = fixed.clamp(
            fixed.add(fixed.fromDecimalStr("0.15"), fixed.mul(mean_load, fixed.fromDecimalStr("0.4"))),
            fixed.fromDecimalStr("0.05"),
            fixed.fromDecimalStr("0.85"),
        );
    }

    /// Plasticity gain scale for a post unit (astrocyte supply · FSOT psi).
    pub fn plasticityGain(self: *const GliaState, post_unit: usize) Fixed {
        const t = tileOf(post_unit);
        // η_scale = c_eff*0.5 + supply*psi_con + ca_bump
        const ca_bump = if (fixed.lt(self.ca_phase[t], fixed.fromDecimalStr("0.15")))
            fixed.fromDecimalStr("0.12")
        else
            0;
        const base = fixed.add(
            fixed.mul(seeds_f.c_eff, fixed.fromDecimalStr("0.45")),
            fixed.mul(self.supply[t], seeds_f.psi_con),
        );
        return fixed.clamp(fixed.add(base, ca_bump), fixed.fromDecimalStr("0.2"), fixed.fromDecimalStr("1.6"));
    }

    /// Microglia-biased prune: weaken weak/idle edges when micro high.
    pub fn microglialPrune(self: *GliaState, b: *brain_f.BrainF) u32 {
        var n: u32 = 0;
        if (fixed.lt(self.micro, fixed.fromDecimalStr("0.25"))) return 0;
        const thr = fixed.fromDecimalStr("0.04");
        const factor = fixed.sub(fixed.fromInt(1), fixed.mul(self.micro, fixed.fromDecimalStr("0.15")));
        var post: usize = 0;
        while (post < b.n) : (post += 1) {
            var pre: usize = 0;
            while (pre < b.n) : (pre += 1) {
                if (pre == post) continue;
                const idx = post * network_f.MAX_N + pre;
                const w = b.net.W[idx];
                if (w == 0) continue;
                if (fixed.lt(fixed.abs(w), thr)) {
                    b.net.W[idx] = 0;
                    n += 1;
                    self.n_prune_events += 1;
                } else if (fixed.lt(fixed.abs(w), fixed.fromDecimalStr("0.12"))) {
                    b.net.W[idx] = fixed.mul(w, factor);
                    n += 1;
                    self.n_prune_events += 1;
                }
            }
        }
        return n;
    }

    /// Oligodendrocyte myelination: boost strong long-range |W| slightly (conduction).
    pub fn myelinate(self: *GliaState, b: *brain_f.BrainF) u32 {
        var n: u32 = 0;
        const strong = fixed.fromDecimalStr("0.18");
        var post: usize = 0;
        while (post < b.n) : (post += 1) {
            var pre: usize = 0;
            while (pre < b.n) : (pre += 1) {
                if (pre == post) continue;
                const dist = if (post > pre) post - pre else pre - post;
                if (dist < 4) continue; // long-range only
                const idx = post * network_f.MAX_N + pre;
                const w = b.net.W[idx];
                if (fixed.lt(fixed.abs(w), strong)) continue;
                // |w| *= (1 + myelo * eta_eff * 0.02)
                const boost = fixed.add(
                    fixed.fromInt(1),
                    fixed.mul(fixed.mul(self.myelo, seeds_f.eta_eff), fixed.fromDecimalStr("0.02")),
                );
                b.net.W[idx] = fixed.mul(w, boost);
                // recap
                if (fixed.gt(b.net.W[idx], fixed.fromDecimalStr("0.5"))) b.net.W[idx] = fixed.fromDecimalStr("0.5");
                if (fixed.lt(b.net.W[idx], fixed.fromDecimalStr("-0.5"))) b.net.W[idx] = fixed.fromDecimalStr("-0.5");
                n += 1;
                self.n_myelo_events += 1;
            }
        }
        return n;
    }

    pub fn meanSupply(self: *const GliaState) Fixed {
        var s: Fixed = 0;
        var i: usize = 0;
        while (i < N_ASTRO) : (i += 1) s = fixed.add(s, self.supply[i]);
        return fixed.div(s, fixed.fromInt(N_ASTRO));
    }

    pub fn meanLoad(self: *const GliaState) Fixed {
        var s: Fixed = 0;
        var i: usize = 0;
        while (i < N_ASTRO) : (i += 1) s = fixed.add(s, self.load[i]);
        return fixed.div(s, fixed.fromInt(N_ASTRO));
    }
};

pub fn selfTest() bool {
    var g = GliaState.init();
    var b = brain_f.BrainF.initSeeded(7, false);
    // force some fires
    var t: u32 = 0;
    while (t < 20) : (t += 1) {
        var ext: [brain_f.N_TOTAL]Fixed = .{fixed.fromDecimalStr("0.5")} ** brain_f.N_TOTAL;
        b.step(ext[0..]);
        g.stepAfterSpikes(&b);
    }
    const pg = g.plasticityGain(0);
    if (fixed.lt(pg, fixed.fromDecimalStr("0.2"))) return false;
    _ = g.microglialPrune(&b);
    _ = g.myelinate(&b);
    return g.tick >= 20 and g.n_clear_events >= 1;
}
