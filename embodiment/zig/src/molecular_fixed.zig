//! WET BIOPHYSICS — multi-species synaptic cascade on Fixed lattice.
//!
//! NOT a 4-scalar "tag/camk/ampa/protein" toy.
//! Each E→E connection carries a spine micro-compartment with ODEs:
//!
//!   Presynaptic release
//!     glu_cleft  ← vesicle dump on pre-spike; cleared by EAAT (glia uptake)
//!   Postsynaptic receptors
//!     NMDA open  ← f(glu, V) with Mg²⁺ block
//!     AMPA g     ← surface density × phosphorylation
//!   Calcium
//!     Ca²⁺       ← NMDA influx − pumps − buffer exchange
//!     Ca_buf     ← reversible buffer
//!   Kinases / phosphatases (LTP vs LTD branch)
//!     CaMKII_c   ← Ca-bound
//!     CaMKII_p   ← autophosphorylated (persistent)
//!     PP1        ← phosphatase (LTD path; moderate Ca)
//!   Trafficking / late LTP
//!     AMPA_surf  ← insertion (CaMKII_p) − endocytosis (PP1)
//!     AMPA_phos  ← CaMKII_p driven
//!     protein    ← synthesis when CaMKII_p high (late LTP)
//!
//! Integration: forward Euler substeps on Fixed (dt from lattice tick).
//! Rates are literature-inspired order-of-magnitude, scaled to lattice time
//! (1 tick ≈ 1 ms class). FSOT seeds scale plasticity (ψ_con, η_eff, k, p_new).
//!
//! Doctrine: genetics as code; connection law still multiplies through
//! fsotPairWeight at the W-update boundary. This module IS the wet path.

const fixed = @import("fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const network_f = @import("network_fixed.zig");
const brain_f = @import("brain_fixed.zig");
const Fixed = fixed.Fixed;

pub const MAX_N: usize = network_f.MAX_N;
pub const MAX_E: usize = MAX_N * MAX_N;

/// Substeps of wet chemistry per network tick (stiffer than spike step).
pub const CHEM_SUBSTEPS: u32 = 4;

// ---------- kinetic constants (Fixed, lattice-scaled) ----------
// Cleared as fractions of state per ms-class tick / substep.
fn kGluRelease() Fixed {
    return fixed.fromDecimalStr("0.85"); // peak cleft load on spike
}
fn kGluUptakeBase() Fixed {
    return fixed.fromDecimalStr("0.45"); // EAAT / diffusion
}
fn kNmdaOpen() Fixed {
    return fixed.fromDecimalStr("0.85");
}
fn kNmdaClose() Fixed {
    return fixed.fromDecimalStr("0.22");
}
fn kCaInflux() Fixed {
    return fixed.fromDecimalStr("1.15");
}
fn kCaPump() Fixed {
    return fixed.fromDecimalStr("0.18");
}
fn kCaBufOn() Fixed {
    return fixed.fromDecimalStr("0.40");
}
fn kCaBufOff() Fixed {
    return fixed.fromDecimalStr("0.12");
}
fn kCamkBind() Fixed {
    return fixed.fromDecimalStr("0.50");
}
fn kCamkUnbind() Fixed {
    return fixed.fromDecimalStr("0.15");
}
fn kCamkAutoP() Fixed {
    return fixed.fromDecimalStr("0.22");
}
fn kCamkDeP() Fixed {
    return fixed.fromDecimalStr("0.04");
}
fn kPp1Act() Fixed {
    return fixed.fromDecimalStr("0.18");
}
fn kPp1Inact() Fixed {
    return fixed.fromDecimalStr("0.10");
}
fn kAmpaInsert() Fixed {
    return fixed.fromDecimalStr("0.08");
}
fn kAmpaEndo() Fixed {
    return fixed.fromDecimalStr("0.06");
}
fn kAmpaPhos() Fixed {
    return fixed.fromDecimalStr("0.20");
}
fn kAmpaDephos() Fixed {
    return fixed.fromDecimalStr("0.10");
}
fn kProteinSynth() Fixed {
    return fixed.fromDecimalStr("0.05");
}
fn kProteinDecay() Fixed {
    return fixed.fromDecimalStr("0.01");
}

/// One excitatory spine / synapse micro-compartment.
pub const Spine = struct {
    glu: Fixed = 0, // cleft glutamate (0..~2)
    ca: Fixed = fixed.fromDecimalStr("0.05"), // free Ca (rest low)
    ca_buf: Fixed = fixed.fromDecimalStr("0.1"),
    nmda_open: Fixed = 0,
    camk_c: Fixed = 0, // Ca-bound CaMKII
    camk_p: Fixed = 0, // autophosphorylated CaMKII
    pp1: Fixed = fixed.fromDecimalStr("0.15"), // basal phosphatase
    ampa_surf: Fixed = fixed.fromDecimalStr("0.5"), // surface AMPA density
    ampa_phos: Fixed = 0,
    protein: Fixed = 0, // late-LTP products
    /// last chemical activity (for diagnostics)
    active: bool = false,
};

pub const CascadeState = struct {
    spines: [MAX_E]Spine = undefined,
    /// glia uptake scale [0.2, 2] set externally each tick
    eaat_scale: Fixed = fixed.fromInt(1),
    // counters
    n_releases: u32 = 0,
    n_tags: u32 = 0, // co-active tags (API compat)
    n_nmda_events: u32 = 0,
    n_ca_peaks: u32 = 0,
    n_camk_peak: u32 = 0,
    n_ampa_up: u32 = 0,
    n_ltd_events: u32 = 0,
    n_consolidate: u32 = 0,
    n_chem_steps: u32 = 0,

    pub fn init() CascadeState {
        var s: CascadeState = .{
            .spines = undefined,
            .eaat_scale = fixed.fromInt(1),
        };
        var i: usize = 0;
        while (i < MAX_E) : (i += 1) {
            s.spines[i] = .{};
        }
        return s;
    }

    pub fn idx(post: usize, pre: usize) usize {
        return post * MAX_N + pre;
    }

    pub fn spinePtr(self: *CascadeState, post: usize, pre: usize) *Spine {
        return &self.spines[idx(post, pre)];
    }

    /// Map lattice S to relative depolarization 0..1 for Mg block.
    fn vFromS(S: Fixed) Fixed {
        // S typically ~0.2..1.5; map (S - rest) / range
        const rest = seeds_f.resting_s;
        const x = fixed.sub(S, rest);
        const n = fixed.div(x, fixed.fromDecimalStr("1.2"));
        return fixed.clamp(n, 0, fixed.fromInt(1));
    }

    /// Mg²⁺ block: high at rest, relieves with depolarization.
    /// B = 1 / (1 + exp(-k*(V-V0))) style via linear Fixed approx.
    fn mgRelief(v: Fixed) Fixed {
        // relief ≈ 0.05 + 0.95 * v^2  (stronger open when depolarized)
        const v2 = fixed.mul(v, v);
        return fixed.add(fixed.fromDecimalStr("0.05"), fixed.mul(fixed.fromDecimalStr("0.95"), v2));
    }

    /// One chemistry substep for a single spine.
    fn chemSubstep(self: *CascadeState, sp: *Spine, v_post: Fixed, pre_spike: bool, post_spike: bool) void {
        self.n_chem_steps += 1;
        const dt = fixed.div(fixed.fromInt(1), fixed.fromInt(CHEM_SUBSTEPS));

        // --- release ---
        if (pre_spike) {
            sp.glu = fixed.add(sp.glu, kGluRelease());
            if (fixed.gt(sp.glu, fixed.fromInt(2))) sp.glu = fixed.fromInt(2);
            self.n_releases += 1;
            sp.active = true;
        }

        // --- glutamate clearance (diffusion + EAAT; glia scale) ---
        const uptake = fixed.mul(kGluUptakeBase(), self.eaat_scale);
        const d_glu = fixed.mul(fixed.mul(uptake, sp.glu), dt);
        sp.glu = fixed.sub(sp.glu, d_glu);
        if (fixed.lt(sp.glu, 0)) sp.glu = 0;

        // --- NMDA open (glu · Mg relief) ---
        const relief = mgRelief(v_post);
        const nmda_drive = fixed.mul(fixed.mul(kNmdaOpen(), sp.glu), relief);
        // dn/dt = drive*(1-n) - close*n
        const d_n_open = fixed.sub(
            fixed.mul(nmda_drive, fixed.sub(fixed.fromInt(1), sp.nmda_open)),
            fixed.mul(kNmdaClose(), sp.nmda_open),
        );
        sp.nmda_open = fixed.add(sp.nmda_open, fixed.mul(d_n_open, dt));
        sp.nmda_open = fixed.clamp(sp.nmda_open, 0, fixed.fromInt(1));
        if (fixed.gt(sp.nmda_open, fixed.fromDecimalStr("0.08"))) self.n_nmda_events += 1;

        // --- Ca influx through NMDA; extra if post also active (assoc) ---
        var ca_in = fixed.mul(kCaInflux(), sp.nmda_open);
        if (post_spike) ca_in = fixed.add(ca_in, fixed.mul(sp.nmda_open, fixed.fromDecimalStr("0.25")));
        // pumps
        const ca_out = fixed.mul(kCaPump(), sp.ca);
        // buffer exchange: free ↔ buf
        const on = fixed.mul(kCaBufOn(), sp.ca);
        const off = fixed.mul(kCaBufOff(), sp.ca_buf);
        sp.ca = fixed.add(sp.ca, fixed.mul(fixed.sub(fixed.add(ca_in, off), fixed.add(ca_out, on)), dt));
        sp.ca_buf = fixed.add(sp.ca_buf, fixed.mul(fixed.sub(on, off), dt));
        sp.ca = fixed.clamp(sp.ca, fixed.fromDecimalStr("0.01"), fixed.fromInt(3));
        sp.ca_buf = fixed.clamp(sp.ca_buf, 0, fixed.fromInt(3));
        if (fixed.gt(sp.ca, fixed.fromDecimalStr("0.25"))) self.n_ca_peaks += 1;

        // --- CaMKII: bind Ca, then autophosphorylate at high Ca ---
        // camk_c' = bind*ca*(1-camk_c-camk_p) - unbind*camk_c - autoP*camk_c
        const free_camk = fixed.sub(fixed.fromInt(1), fixed.add(sp.camk_c, sp.camk_p));
        const free_c = if (fixed.lt(free_camk, 0)) @as(Fixed, 0) else free_camk;
        const bind = fixed.mul(kCamkBind(), fixed.mul(sp.ca, free_c));
        const unbind = fixed.mul(kCamkUnbind(), sp.camk_c);
        // autophosphorylation requires high Ca (thresholded)
        const hi_ca = if (fixed.gt(sp.ca, fixed.fromDecimalStr("0.22"))) sp.ca else 0;
        const autop = fixed.mul(kCamkAutoP(), fixed.mul(hi_ca, sp.camk_c));
        const dep = fixed.mul(kCamkDeP(), sp.camk_p);
        // PP1 can dephosphorylate CaMKII_p
        const pp_dep = fixed.mul(sp.pp1, fixed.mul(sp.camk_p, fixed.fromDecimalStr("0.08")));
        sp.camk_c = fixed.add(sp.camk_c, fixed.mul(fixed.sub(bind, fixed.add(unbind, autop)), dt));
        sp.camk_p = fixed.add(sp.camk_p, fixed.mul(fixed.sub(autop, fixed.add(dep, pp_dep)), dt));
        sp.camk_c = fixed.clamp(sp.camk_c, 0, fixed.fromInt(1));
        sp.camk_p = fixed.clamp(sp.camk_p, 0, fixed.fromInt(1));
        if (fixed.gt(sp.camk_p, fixed.fromDecimalStr("0.12"))) self.n_camk_peak += 1;

        // --- PP1: LTD branch — activated by moderate Ca (not extreme) ---
        // bell-ish: act when ca ~ 0.2..0.5
        const mid = fixed.sub(sp.ca, fixed.fromDecimalStr("0.3"));
        const mid2 = fixed.mul(mid, mid);
        const bell = fixed.sub(fixed.fromDecimalStr("0.25"), mid2); // crude peak at 0.3
        const pp_drive = if (fixed.gt(bell, 0)) fixed.mul(kPp1Act(), bell) else 0;
        const pp_off = fixed.mul(kPp1Inact(), sp.pp1);
        // high CaMKII_p suppresses PP1 (classic LTP vs LTD competition)
        const suppress = fixed.mul(sp.camk_p, fixed.fromDecimalStr("0.2"));
        sp.pp1 = fixed.add(sp.pp1, fixed.mul(fixed.sub(pp_drive, fixed.add(pp_off, suppress)), dt));
        sp.pp1 = fixed.clamp(sp.pp1, fixed.fromDecimalStr("0.02"), fixed.fromInt(1));
        if (fixed.gt(sp.pp1, fixed.fromDecimalStr("0.4")) and fixed.gt(sp.ca, fixed.fromDecimalStr("0.15")))
            self.n_ltd_events += 1;

        // --- AMPA surface trafficking ---
        // insert ∝ camk_p; endocytosis ∝ pp1
        const ins = fixed.mul(kAmpaInsert(), fixed.mul(sp.camk_p, fixed.sub(fixed.fromInt(1), sp.ampa_surf)));
        const endo = fixed.mul(kAmpaEndo(), fixed.mul(sp.pp1, sp.ampa_surf));
        sp.ampa_surf = fixed.add(sp.ampa_surf, fixed.mul(fixed.sub(ins, endo), dt));
        sp.ampa_surf = fixed.clamp(sp.ampa_surf, fixed.fromDecimalStr("0.1"), fixed.fromInt(1));
        if (fixed.gt(sp.ampa_surf, fixed.fromDecimalStr("0.55"))) self.n_ampa_up += 1;

        // phosphorylation of AMPA
        const ph = fixed.mul(kAmpaPhos(), fixed.mul(sp.camk_p, fixed.sub(fixed.fromInt(1), sp.ampa_phos)));
        const dph = fixed.mul(kAmpaDephos(), fixed.mul(sp.pp1, sp.ampa_phos));
        sp.ampa_phos = fixed.add(sp.ampa_phos, fixed.mul(fixed.sub(ph, dph), dt));
        sp.ampa_phos = fixed.clamp(sp.ampa_phos, 0, fixed.fromInt(1));

        // --- late LTP protein synthesis (gene expression stand-in) ---
        if (fixed.gt(sp.camk_p, fixed.fromDecimalStr("0.15"))) {
            const syn = fixed.mul(kProteinSynth(), fixed.mul(sp.camk_p, seeds_f.psi_con));
            sp.protein = fixed.add(sp.protein, fixed.mul(syn, dt));
        }
        sp.protein = fixed.sub(sp.protein, fixed.mul(kProteinDecay(), sp.protein));
        sp.protein = fixed.clamp(sp.protein, 0, fixed.fromInt(1));
    }

    /// Integrate chemistry for all E→E pairs given current brain fire state.
    pub fn integrateNetwork(self: *CascadeState, b: *const brain_f.BrainF) void {
        const n = b.n;
        var post: usize = 0;
        while (post < n) : (post += 1) {
            if (b.genotypes[post].synapse_sign <= 0) continue;
            const v = vFromS(b.net.units[post].S);
            const post_spk = b.net.last_fired[post];
            var pre: usize = 0;
            while (pre < n) : (pre += 1) {
                if (pre == post) continue;
                if (b.genotypes[pre].synapse_sign <= 0) continue;
                const sp = self.spinePtr(post, pre);
                const pre_spk = b.net.last_fired[pre];
                // only burn substeps if something is happening or spine active
                if (!pre_spk and !post_spk and !sp.active and sp.glu == 0 and fixed.lt(sp.ca, fixed.fromDecimalStr("0.1")))
                    continue;
                var s: u32 = 0;
                while (s < CHEM_SUBSTEPS) : (s += 1) {
                    // pre spike only on first substep of a tick where pre fired
                    self.chemSubstep(sp, v, pre_spk and s == 0, post_spk and s == 0);
                }
                if (fixed.lt(sp.glu, fixed.fromDecimalStr("0.02")) and fixed.lt(sp.ca, fixed.fromDecimalStr("0.12")) and fixed.lt(sp.camk_p, fixed.fromDecimalStr("0.05")))
                    sp.active = false;
            }
        }
    }

    /// API: tag coactive pairs (counts + ensures spine marked).
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
                self.spinePtr(post, pre).active = true;
                self.n_tags += 1;
            }
        }
        self.integrateNetwork(b);
    }

    /// API: cascade step without new spikes (decay / continue chemistry).
    pub fn cascadeStep(self: *CascadeState) void {
        // no brain context — decay only active spines lightly
        var i: usize = 0;
        while (i < MAX_E) : (i += 1) {
            const sp = &self.spines[i];
            if (!sp.active and sp.glu == 0) continue;
            // passive decay tick without voltage (V=0 → strong Mg block)
            self.chemSubstep(sp, 0, false, false);
        }
    }

    /// Map spine state → STDP eligibility multiplier.
    pub fn eligibility(self: *const CascadeState, post: usize, pre: usize) Fixed {
        const sp = self.spines[idx(post, pre)];
        // high AMPA surface + CaMKII_p + protein → stronger plastic gain
        // high PP1 → reduce LTP eligibility (favor LTD)
        const ltp = fixed.add(
            fixed.mul(sp.ampa_surf, fixed.fromDecimalStr("0.6")),
            fixed.add(
                fixed.mul(sp.camk_p, fixed.fromDecimalStr("0.5")),
                fixed.mul(sp.protein, fixed.fromDecimalStr("0.4")),
            ),
        );
        const ltd_pen = fixed.mul(sp.pp1, fixed.fromDecimalStr("0.35"));
        const e = fixed.add(fixed.fromDecimalStr("0.35"), fixed.sub(ltp, ltd_pen));
        return fixed.clamp(e, fixed.fromDecimalStr("0.15"), fixed.fromDecimalStr("2.2"));
    }

    /// Effective synaptic multiplier for W (conductance scaling).
    pub fn conductanceScale(self: *const CascadeState, post: usize, pre: usize) Fixed {
        const sp = self.spines[idx(post, pre)];
        // g ∝ ampa_surf * (1 + 0.5 phos) * (1 + 0.4 protein)
        const ph = fixed.add(fixed.fromInt(1), fixed.mul(sp.ampa_phos, fixed.fromDecimalStr("0.5")));
        const pr = fixed.add(fixed.fromInt(1), fixed.mul(sp.protein, fixed.fromDecimalStr("0.4")));
        return fixed.clamp(fixed.mul(fixed.mul(sp.ampa_surf, ph), pr), fixed.fromDecimalStr("0.2"), fixed.fromDecimalStr("2.5"));
    }

    /// Late LTP / LTD: bake molecular state into W (structural boundary).
    pub fn consolidateToW(self: *CascadeState, b: *brain_f.BrainF) u32 {
        var n: u32 = 0;
        const n_u = b.n;
        var post: usize = 0;
        while (post < n_u) : (post += 1) {
            if (b.genotypes[post].synapse_sign <= 0) continue;
            var pre: usize = 0;
            while (pre < n_u) : (pre += 1) {
                if (pre == post) continue;
                if (b.genotypes[pre].synapse_sign <= 0) continue;
                const sp = self.spinePtr(post, pre);
                const wi = post * network_f.MAX_N + pre;
                var w = b.net.W[wi];

                // LTP consolidation: protein + camk_p high
                if (fixed.gt(sp.protein, fixed.fromDecimalStr("0.12")) and fixed.gt(sp.camk_p, fixed.fromDecimalStr("0.1"))) {
                    const boost = fixed.mul(
                        fixed.mul(sp.protein, sp.ampa_surf),
                        fixed.mul(seeds_f.psi_con, fixed.fromDecimalStr("0.08")),
                    );
                    if (w == 0) w = fixed.fromDecimalStr("0.04");
                    w = fixed.add(w, boost);
                    // consume protein (structural use)
                    sp.protein = fixed.mul(sp.protein, fixed.fromDecimalStr("0.65"));
                    n += 1;
                    self.n_consolidate += 1;
                }
                // LTD consolidation: high PP1, low camk_p
                if (fixed.gt(sp.pp1, fixed.fromDecimalStr("0.45")) and fixed.lt(sp.camk_p, fixed.fromDecimalStr("0.2"))) {
                    w = fixed.mul(w, fixed.fromDecimalStr("0.92"));
                    if (fixed.lt(fixed.abs(w), fixed.fromDecimalStr("0.01"))) w = 0;
                    n += 1;
                    self.n_ltd_events += 1;
                }
                // scale existing W gently by conductance (ongoing AMPA)
                if (w != 0) {
                    const g = self.conductanceScale(post, pre);
                    // mix: W ← 0.85 W + 0.15 W*g  (soft track receptors)
                    const tracked = fixed.mul(w, g);
                    w = fixed.add(fixed.mul(w, fixed.fromDecimalStr("0.85")), fixed.mul(tracked, fixed.fromDecimalStr("0.15")));
                }
                if (fixed.gt(w, fixed.fromDecimalStr("0.55"))) w = fixed.fromDecimalStr("0.55");
                if (fixed.lt(w, fixed.fromDecimalStr("-0.55"))) w = fixed.fromDecimalStr("-0.55");
                b.net.W[wi] = w;
            }
        }
        return n;
    }

    /// Set EAAT / glial uptake scale for next chemistry (from glia_fixed).
    pub fn setEaatScale(self: *CascadeState, scale: Fixed) void {
        self.eaat_scale = fixed.clamp(scale, fixed.fromDecimalStr("0.25"), fixed.fromDecimalStr("2.5"));
    }

    /// Diagnostic snapshot of a busy spine (first active found).
    pub fn sampleBusy(self: *const CascadeState) Spine {
        var i: usize = 0;
        while (i < MAX_E) : (i += 1) {
            if (self.spines[i].active or fixed.gt(self.spines[i].camk_p, fixed.fromDecimalStr("0.1")))
                return self.spines[i];
        }
        return .{};
    }
};

pub fn selfTest() bool {
    var c = CascadeState.init();
    var b = brain_f.BrainF.initSeeded(11, false);
    // strong paired stimulation protocol (LTP-like)
    var t: u32 = 0;
    while (t < 40) : (t += 1) {
        var ext: [brain_f.N_TOTAL]Fixed = .{fixed.fromDecimalStr("0.05")} ** brain_f.N_TOTAL;
        // drive many E cells hard in packets
        if ((t % 5) < 2) {
            var u: usize = 0;
            while (u < b.n) : (u += 1) {
                if (b.genotypes[u].synapse_sign > 0) ext[u] = fixed.fromDecimalStr("0.95");
            }
        }
        b.step(ext[0..]);
        c.tagCoactive(&b);
    }
    _ = c.consolidateToW(&b);
    // must have seen release, Ca or CaMKII activity
    if (c.n_releases < 1) return false;
    if (c.n_tags < 1) return false;
    if (c.n_chem_steps < 10) return false;
    // at least some cascade progression
    return c.n_ca_peaks >= 1 or c.n_camk_peak >= 1 or c.n_nmda_events >= 1;
}
