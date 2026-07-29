//! Molecular cascade stand-in for late LTP (Fixed lattice, FSOT-seeded).
//!
//! Human (compressed):
//!   early LTP  — Ca²⁺ influx, kinase activation (CaMKII), AMPA phosphorylation
//!   late LTP   — gene expression / protein synthesis → lasting structural change
//!   eligibility — synapse tagged by coincident activity, consolidated if cascade completes
//!
//! Our process (claimable, not full biochemistry):
//!   tag[edge]   += activity               (early eligibility)
//!   camk[edge]  → integrates tag (kinase)
//!   ampa[edge]  → tracks camk (receptor insertion stand-in)
//!   protein[edge] consolidates if camk high for long enough → lock W boost
//!
//! All Fixed; rates use FSOT seeds (psi_con, eta_eff, p_new, k).

const fixed = @import("fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const network_f = @import("network_fixed.zig");
const brain_f = @import("brain_fixed.zig");
const Fixed = fixed.Fixed;

pub const MAX_E: usize = network_f.MAX_N * network_f.MAX_N;

pub const CascadeState = struct {
    tag: [MAX_E]Fixed = .{0} ** MAX_E,
    camk: [MAX_E]Fixed = .{0} ** MAX_E,
    ampa: [MAX_E]Fixed = .{0} ** MAX_E,
    protein: [MAX_E]Fixed = .{0} ** MAX_E,
    n_tags: u32 = 0,
    n_camk_peak: u32 = 0,
    n_ampa_up: u32 = 0,
    n_consolidate: u32 = 0,

    pub fn init() CascadeState {
        return .{};
    }

    fn idx(post: usize, pre: usize) usize {
        return post * network_f.MAX_N + pre;
    }

    /// Tag synapses that co-fired this tick (early LTP eligibility).
    pub fn tagCoactive(self: *CascadeState, b: *const brain_f.BrainF) void {
        const n = b.n;
        var post: usize = 0;
        while (post < n) : (post += 1) {
            if (!b.net.last_fired[post]) continue;
            if (b.genotypes[post].synapse_sign <= 0) continue;
            var pre: usize = 0;
            while (pre < n) : (pre += 1) {
                if (pre == post) continue;
                if (!b.net.last_fired[pre]) continue;
                if (b.genotypes[pre].synapse_sign <= 0) continue;
                const i = idx(post, pre);
                // tag += p_new * psi_con
                const d = fixed.mul(seeds_f.p_new, seeds_f.psi_con);
                self.tag[i] = fixed.add(self.tag[i], d);
                if (fixed.gt(self.tag[i], fixed.fromInt(1))) self.tag[i] = fixed.fromInt(1);
                self.n_tags += 1;
            }
        }
    }

    /// Advance molecular stages one tick (CaMKII → AMPA → protein).
    pub fn cascadeStep(self: *CascadeState) void {
        var i: usize = 0;
        while (i < MAX_E) : (i += 1) {
            if (self.tag[i] == 0 and self.camk[i] == 0 and self.ampa[i] == 0 and self.protein[i] == 0) continue;

            // CaMKII integrates tag (kinase activation) — rates set for lattice timescale
            const drive = fixed.mul(seeds_f.k, fixed.mul(self.tag[i], fixed.sub(fixed.fromInt(1), self.camk[i])));
            self.camk[i] = fixed.add(self.camk[i], fixed.mul(drive, fixed.fromDecimalStr("2.5")));
            self.camk[i] = fixed.sub(self.camk[i], fixed.mul(self.camk[i], fixed.fromDecimalStr("0.02")));
            self.camk[i] = fixed.clamp(self.camk[i], 0, fixed.fromInt(1));
            if (fixed.gt(self.camk[i], fixed.fromDecimalStr("0.45"))) self.n_camk_peak += 1;

            // AMPA trafficking stand-in follows camk
            const ampa_drive = fixed.mul(seeds_f.eta_eff, fixed.mul(self.camk[i], fixed.sub(fixed.fromInt(1), self.ampa[i])));
            self.ampa[i] = fixed.add(self.ampa[i], fixed.mul(ampa_drive, fixed.fromDecimalStr("0.35")));
            self.ampa[i] = fixed.sub(self.ampa[i], fixed.mul(self.ampa[i], fixed.fromDecimalStr("0.02")));
            self.ampa[i] = fixed.clamp(self.ampa[i], 0, fixed.fromInt(1));
            if (fixed.gt(self.ampa[i], fixed.fromDecimalStr("0.3"))) self.n_ampa_up += 1;

            // Protein synthesis / late LTP when camk elevated
            if (fixed.gt(self.camk[i], fixed.fromDecimalStr("0.35"))) {
                self.protein[i] = fixed.add(self.protein[i], fixed.mul(seeds_f.psi_con, fixed.fromDecimalStr("0.12")));
                if (fixed.gt(self.protein[i], fixed.fromInt(1))) self.protein[i] = fixed.fromInt(1);
            } else {
                self.protein[i] = fixed.mul(self.protein[i], fixed.fromDecimalStr("0.98"));
            }

            // tag decays (Ca clearance stand-in)
            self.tag[i] = fixed.mul(self.tag[i], fixed.fromDecimalStr("0.92"));
            if (fixed.lt(self.tag[i], fixed.fromDecimalStr("0.01"))) self.tag[i] = 0;
        }
    }

    /// Consolidation: if protein high, permanently nudge W (late LTP).
    pub fn consolidateToW(self: *CascadeState, b: *brain_f.BrainF) u32 {
        var n: u32 = 0;
        const n_u = b.n;
        var post: usize = 0;
        while (post < n_u) : (post += 1) {
            var pre: usize = 0;
            while (pre < n_u) : (pre += 1) {
                if (pre == post) continue;
                const i = idx(post, pre);
                if (fixed.lt(self.protein[i], fixed.fromDecimalStr("0.45"))) continue;
                const wi = post * network_f.MAX_N + pre;
                var w = b.net.W[wi];
                // late LTP boost proportional to protein * ampa * psi_con
                const boost = fixed.mul(
                    fixed.mul(self.protein[i], self.ampa[i]),
                    fixed.mul(seeds_f.psi_con, fixed.fromDecimalStr("0.06")),
                );
                if (w == 0) {
                    w = fixed.fromDecimalStr("0.03");
                }
                w = fixed.add(w, boost);
                if (fixed.gt(w, fixed.fromDecimalStr("0.5"))) w = fixed.fromDecimalStr("0.5");
                b.net.W[wi] = w;
                // consume some protein (used for structural change)
                self.protein[i] = fixed.mul(self.protein[i], fixed.fromDecimalStr("0.7"));
                n += 1;
                self.n_consolidate += 1;
            }
        }
        return n;
    }

    /// Eligibility scale for STDP (early cascade multiplies η).
    pub fn eligibility(self: *const CascadeState, post: usize, pre: usize) Fixed {
        const i = idx(post, pre);
        // 0.5 + 0.5*ampa + 0.25*tag
        return fixed.clamp(
            fixed.add(
                fixed.fromDecimalStr("0.5"),
                fixed.add(
                    fixed.mul(self.ampa[i], fixed.fromDecimalStr("0.5")),
                    fixed.mul(self.tag[i], fixed.fromDecimalStr("0.25")),
                ),
            ),
            fixed.fromDecimalStr("0.4"),
            fixed.fromDecimalStr("1.8"),
        );
    }
};

pub fn selfTest() bool {
    var c = CascadeState.init();
    var b = brain_f.BrainF.initSeeded(3, false);
    var t: u32 = 0;
    while (t < 30) : (t += 1) {
        var ext: [brain_f.N_TOTAL]Fixed = .{fixed.fromDecimalStr("0.55")} ** brain_f.N_TOTAL;
        b.step(ext[0..]);
        c.tagCoactive(&b);
        c.cascadeStep();
    }
    _ = c.consolidateToW(&b);
    return c.n_tags >= 1;
}
