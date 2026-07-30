//! WET BIOPHYSICS + FULL STOCHASTIC SINGLE-CHANNEL KINETICS (Fixed lattice).
//!
//! Per E→E spine:
//!   1) Stochastic vesicle release (binomial quanta) on pre-spike
//!   2) Glu cleft + EAAT clear (glia scale)
//!   3) AMPA / NMDA as Markov single channels (channel_stoch_fixed)
//!   4) Ca²⁺ from open NMDA unitary currents (stochastic)
//!   5) CaMKII / PP1 / AMPA traffic / late protein ODEs on Fixed
//!   6) consolidateToW for structural boundary
//!
//! No continuous open-probability shortcut for receptor current.
//! Channel transitions = Bernoulli(markovProb(rate,dt)) via integer xorshift.

const fixed = @import("fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const network_f = @import("network_fixed.zig");
const brain_f = @import("brain_fixed.zig");
const ch = @import("channel_stoch_fixed.zig");
const Fixed = fixed.Fixed;

pub const MAX_N: usize = network_f.MAX_N;
pub const MAX_E: usize = MAX_N * MAX_N;
pub const CHEM_SUBSTEPS: u32 = 4;

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
    return fixed.fromDecimalStr("0.28");
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
    return fixed.fromDecimalStr("0.06");
}
fn kProteinDecay() Fixed {
    return fixed.fromDecimalStr("0.01");
}
fn kGluUptakeBase() Fixed {
    return fixed.fromDecimalStr("0.40");
}

pub const Spine = struct {
    glu: Fixed = 0,
    ca: Fixed = fixed.fromDecimalStr("0.05"),
    ca_buf: Fixed = fixed.fromDecimalStr("0.1"),
    /// fraction open from single-channel count (diagnostic)
    nmda_open: Fixed = 0,
    ampa_g: Fixed = 0,
    camk_c: Fixed = 0,
    camk_p: Fixed = 0,
    pp1: Fixed = fixed.fromDecimalStr("0.15"),
    ampa_surf: Fixed = fixed.fromDecimalStr("0.5"),
    ampa_phos: Fixed = 0,
    protein: Fixed = 0,
    channels: ch.ChannelBank = .{},
    active: bool = false,
};

pub const CascadeState = struct {
    spines: [MAX_E]Spine = undefined,
    eaat_scale: Fixed = fixed.fromInt(1),
    rng: ch.Rng = ch.Rng.init(0xFEEDBEEFCAFEBABE),
    n_releases: u32 = 0,
    n_quanta: u32 = 0,
    n_tags: u32 = 0,
    n_nmda_events: u32 = 0,
    n_ca_peaks: u32 = 0,
    n_camk_peak: u32 = 0,
    n_ampa_up: u32 = 0,
    n_ltd_events: u32 = 0,
    n_consolidate: u32 = 0,
    n_chem_steps: u32 = 0,
    n_channel_transitions: u32 = 0,
    n_ampa_openings: u32 = 0,
    n_nmda_openings: u32 = 0,
    n_stoch_fail_silent: u32 = 0, // release attempts with 0 quanta

    pub fn init() CascadeState {
        var s: CascadeState = .{
            .spines = undefined,
            .rng = ch.Rng.init(0xC0DEC0DEBEEF42),
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

    fn vFromS(S: Fixed) Fixed {
        const rest = seeds_f.resting_s;
        const x = fixed.sub(S, rest);
        return fixed.clamp(fixed.div(x, fixed.fromDecimalStr("1.2")), 0, fixed.fromInt(1));
    }

    fn mgRelief(v: Fixed) Fixed {
        const v2 = fixed.mul(v, v);
        return fixed.add(fixed.fromDecimalStr("0.05"), fixed.mul(fixed.fromDecimalStr("0.95"), v2));
    }

    fn chemSubstep(self: *CascadeState, sp: *Spine, v_post: Fixed, pre_spike: bool, post_spike: bool) void {
        self.n_chem_steps += 1;
        const dt = fixed.div(fixed.fromInt(1), fixed.fromInt(CHEM_SUBSTEPS));
        const relief = mgRelief(v_post);

        // --- stochastic quantal release ---
        if (pre_spike) {
            // p_release elevated by residual Ca in terminal (use glu residue as proxy)
            const p_rel = fixed.clamp(
                fixed.add(fixed.fromDecimalStr("0.25"), fixed.mul(sp.glu, fixed.fromDecimalStr("0.15"))),
                fixed.fromDecimalStr("0.1"),
                fixed.fromDecimalStr("0.85"),
            );
            const rel = ch.stochasticRelease(&self.rng, p_rel);
            if (rel.quanta == 0) {
                self.n_stoch_fail_silent += 1;
            } else {
                sp.glu = fixed.add(sp.glu, rel.glu);
                if (fixed.gt(sp.glu, fixed.fromInt(3))) sp.glu = fixed.fromInt(3);
                self.n_releases += 1;
                self.n_quanta += rel.quanta;
                sp.active = true;
            }
        }

        // --- EAAT / diffusion clear ---
        const uptake = fixed.mul(kGluUptakeBase(), self.eaat_scale);
        const d_glu = fixed.mul(fixed.mul(uptake, sp.glu), dt);
        sp.glu = fixed.sub(sp.glu, d_glu);
        if (fixed.lt(sp.glu, 0)) sp.glu = 0;

        // --- FULL STOCHASTIC SINGLE-CHANNEL STEP ---
        const tr0 = sp.channels.n_transitions;
        const ao0 = sp.channels.n_ampa_openings;
        const no0 = sp.channels.n_nmda_openings;
        sp.channels.step(&self.rng, sp.glu, relief, dt);
        self.n_channel_transitions += sp.channels.n_transitions - tr0;
        self.n_ampa_openings += sp.channels.n_ampa_openings - ao0;
        self.n_nmda_openings += sp.channels.n_nmda_openings - no0;

        // open fractions for diagnostics / ODEs
        sp.nmda_open = fixed.div(fixed.fromInt(@intCast(sp.channels.n_nmda_open)), fixed.fromInt(ch.N_NMDA));
        sp.ampa_g = sp.channels.ampaCurrent();
        if (sp.channels.n_nmda_open > 0) self.n_nmda_events += 1;

        // --- Ca from unitary NMDA currents (stochastic open count) ---
        var ca_in = sp.channels.nmdaCaCurrent();
        if (post_spike) ca_in = fixed.add(ca_in, fixed.mul(sp.nmda_open, fixed.fromDecimalStr("0.2")));
        const ca_out = fixed.mul(kCaPump(), sp.ca);
        const on = fixed.mul(kCaBufOn(), sp.ca);
        const off = fixed.mul(kCaBufOff(), sp.ca_buf);
        sp.ca = fixed.add(sp.ca, fixed.mul(fixed.sub(fixed.add(ca_in, off), fixed.add(ca_out, on)), dt));
        sp.ca_buf = fixed.add(sp.ca_buf, fixed.mul(fixed.sub(on, off), dt));
        sp.ca = fixed.clamp(sp.ca, fixed.fromDecimalStr("0.01"), fixed.fromInt(4));
        sp.ca_buf = fixed.clamp(sp.ca_buf, 0, fixed.fromInt(4));
        if (fixed.gt(sp.ca, fixed.fromDecimalStr("0.25"))) self.n_ca_peaks += 1;

        // --- CaMKII ---
        const free_camk = fixed.sub(fixed.fromInt(1), fixed.add(sp.camk_c, sp.camk_p));
        const free_c = if (fixed.lt(free_camk, 0)) @as(Fixed, 0) else free_camk;
        const bind = fixed.mul(kCamkBind(), fixed.mul(sp.ca, free_c));
        const unbind = fixed.mul(kCamkUnbind(), sp.camk_c);
        const hi_ca = if (fixed.gt(sp.ca, fixed.fromDecimalStr("0.22"))) sp.ca else 0;
        const autop = fixed.mul(kCamkAutoP(), fixed.mul(hi_ca, sp.camk_c));
        const dep = fixed.mul(kCamkDeP(), sp.camk_p);
        const pp_dep = fixed.mul(sp.pp1, fixed.mul(sp.camk_p, fixed.fromDecimalStr("0.08")));
        sp.camk_c = fixed.add(sp.camk_c, fixed.mul(fixed.sub(bind, fixed.add(unbind, autop)), dt));
        sp.camk_p = fixed.add(sp.camk_p, fixed.mul(fixed.sub(autop, fixed.add(dep, pp_dep)), dt));
        sp.camk_c = fixed.clamp(sp.camk_c, 0, fixed.fromInt(1));
        sp.camk_p = fixed.clamp(sp.camk_p, 0, fixed.fromInt(1));
        if (fixed.gt(sp.camk_p, fixed.fromDecimalStr("0.12"))) self.n_camk_peak += 1;

        // --- PP1 LTD ---
        const mid = fixed.sub(sp.ca, fixed.fromDecimalStr("0.3"));
        const mid2 = fixed.mul(mid, mid);
        const bell = fixed.sub(fixed.fromDecimalStr("0.25"), mid2);
        const pp_drive = if (fixed.gt(bell, 0)) fixed.mul(kPp1Act(), bell) else 0;
        const pp_off = fixed.mul(kPp1Inact(), sp.pp1);
        const suppress = fixed.mul(sp.camk_p, fixed.fromDecimalStr("0.2"));
        sp.pp1 = fixed.add(sp.pp1, fixed.mul(fixed.sub(pp_drive, fixed.add(pp_off, suppress)), dt));
        sp.pp1 = fixed.clamp(sp.pp1, fixed.fromDecimalStr("0.02"), fixed.fromInt(1));
        if (fixed.gt(sp.pp1, fixed.fromDecimalStr("0.4")) and fixed.gt(sp.ca, fixed.fromDecimalStr("0.15")))
            self.n_ltd_events += 1;

        // --- AMPA trafficking (modulated by open-channel activity too) ---
        const open_boost = fixed.mul(sp.ampa_g, fixed.fromDecimalStr("0.3"));
        const ins = fixed.mul(kAmpaInsert(), fixed.mul(fixed.add(sp.camk_p, open_boost), fixed.sub(fixed.fromInt(1), sp.ampa_surf)));
        const endo = fixed.mul(kAmpaEndo(), fixed.mul(sp.pp1, sp.ampa_surf));
        sp.ampa_surf = fixed.add(sp.ampa_surf, fixed.mul(fixed.sub(ins, endo), dt));
        sp.ampa_surf = fixed.clamp(sp.ampa_surf, fixed.fromDecimalStr("0.1"), fixed.fromInt(1));
        if (fixed.gt(sp.ampa_surf, fixed.fromDecimalStr("0.55"))) self.n_ampa_up += 1;

        const ph = fixed.mul(kAmpaPhos(), fixed.mul(sp.camk_p, fixed.sub(fixed.fromInt(1), sp.ampa_phos)));
        const dph = fixed.mul(kAmpaDephos(), fixed.mul(sp.pp1, sp.ampa_phos));
        sp.ampa_phos = fixed.add(sp.ampa_phos, fixed.mul(fixed.sub(ph, dph), dt));
        sp.ampa_phos = fixed.clamp(sp.ampa_phos, 0, fixed.fromInt(1));

        if (fixed.gt(sp.camk_p, fixed.fromDecimalStr("0.15"))) {
            const syn = fixed.mul(kProteinSynth(), fixed.mul(sp.camk_p, seeds_f.psi_con));
            sp.protein = fixed.add(sp.protein, fixed.mul(syn, dt));
        }
        sp.protein = fixed.sub(sp.protein, fixed.mul(kProteinDecay(), sp.protein));
        sp.protein = fixed.clamp(sp.protein, 0, fixed.fromInt(1));
    }

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
                if (!pre_spk and !post_spk and !sp.active and sp.glu == 0 and fixed.lt(sp.ca, fixed.fromDecimalStr("0.1")) and sp.channels.n_nmda_open == 0 and sp.channels.n_ampa_open == 0)
                    continue;
                var s: u32 = 0;
                while (s < CHEM_SUBSTEPS) : (s += 1) {
                    self.chemSubstep(sp, v, pre_spk and s == 0, post_spk and s == 0);
                }
                if (fixed.lt(sp.glu, fixed.fromDecimalStr("0.02")) and fixed.lt(sp.ca, fixed.fromDecimalStr("0.12")) and fixed.lt(sp.camk_p, fixed.fromDecimalStr("0.05")) and sp.channels.n_nmda_open == 0)
                    sp.active = false;
            }
        }
    }

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

    pub fn cascadeStep(self: *CascadeState) void {
        var i: usize = 0;
        while (i < MAX_E) : (i += 1) {
            const sp = &self.spines[i];
            if (!sp.active and sp.glu == 0 and sp.channels.n_nmda_open == 0) continue;
            self.chemSubstep(sp, 0, false, false);
        }
    }

    pub fn eligibility(self: *const CascadeState, post: usize, pre: usize) Fixed {
        const sp = self.spines[idx(post, pre)];
        const ch_boost = fixed.mul(fixed.fromInt(@intCast(sp.channels.n_nmda_open + sp.channels.n_ampa_open)), fixed.fromDecimalStr("0.05"));
        const ltp = fixed.add(
            fixed.mul(sp.ampa_surf, fixed.fromDecimalStr("0.6")),
            fixed.add(
                fixed.mul(sp.camk_p, fixed.fromDecimalStr("0.5")),
                fixed.add(fixed.mul(sp.protein, fixed.fromDecimalStr("0.4")), ch_boost),
            ),
        );
        const ltd_pen = fixed.mul(sp.pp1, fixed.fromDecimalStr("0.35"));
        return fixed.clamp(
            fixed.add(fixed.fromDecimalStr("0.35"), fixed.sub(ltp, ltd_pen)),
            fixed.fromDecimalStr("0.15"),
            fixed.fromDecimalStr("2.5"),
        );
    }

    pub fn conductanceScale(self: *const CascadeState, post: usize, pre: usize) Fixed {
        const sp = self.spines[idx(post, pre)];
        // include instantaneous open AMPA channels
        const open = fixed.add(sp.ampa_surf, fixed.mul(sp.ampa_g, fixed.fromDecimalStr("0.5")));
        const ph = fixed.add(fixed.fromInt(1), fixed.mul(sp.ampa_phos, fixed.fromDecimalStr("0.5")));
        const pr = fixed.add(fixed.fromInt(1), fixed.mul(sp.protein, fixed.fromDecimalStr("0.4")));
        return fixed.clamp(fixed.mul(fixed.mul(open, ph), pr), fixed.fromDecimalStr("0.2"), fixed.fromDecimalStr("2.8"));
    }

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
                if (fixed.gt(sp.protein, fixed.fromDecimalStr("0.12")) and fixed.gt(sp.camk_p, fixed.fromDecimalStr("0.1"))) {
                    const boost = fixed.mul(
                        fixed.mul(sp.protein, sp.ampa_surf),
                        fixed.mul(seeds_f.psi_con, fixed.fromDecimalStr("0.08")),
                    );
                    if (w == 0) w = fixed.fromDecimalStr("0.04");
                    w = fixed.add(w, boost);
                    sp.protein = fixed.mul(sp.protein, fixed.fromDecimalStr("0.65"));
                    n += 1;
                    self.n_consolidate += 1;
                }
                if (fixed.gt(sp.pp1, fixed.fromDecimalStr("0.45")) and fixed.lt(sp.camk_p, fixed.fromDecimalStr("0.2"))) {
                    w = fixed.mul(w, fixed.fromDecimalStr("0.92"));
                    if (fixed.lt(fixed.abs(w), fixed.fromDecimalStr("0.01"))) w = 0;
                    n += 1;
                    self.n_ltd_events += 1;
                }
                if (w != 0) {
                    const g = self.conductanceScale(post, pre);
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

    pub fn setEaatScale(self: *CascadeState, scale: Fixed) void {
        self.eaat_scale = fixed.clamp(scale, fixed.fromDecimalStr("0.25"), fixed.fromDecimalStr("2.5"));
    }

    pub fn sampleBusy(self: *const CascadeState) Spine {
        var i: usize = 0;
        while (i < MAX_E) : (i += 1) {
            if (self.spines[i].active or fixed.gt(self.spines[i].camk_p, fixed.fromDecimalStr("0.05")) or self.spines[i].channels.n_nmda_open > 0)
                return self.spines[i];
        }
        return .{};
    }
};

pub fn selfTest() bool {
    if (!ch.selfTest()) return false;
    var c = CascadeState.init();
    var b = brain_f.BrainF.initSeeded(11, false);
    var t: u32 = 0;
    while (t < 50) : (t += 1) {
        var ext: [brain_f.N_TOTAL]Fixed = .{fixed.fromDecimalStr("0.05")} ** brain_f.N_TOTAL;
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
    // must have stochastic channel activity
    if (c.n_channel_transitions < 20) return false;
    if (c.n_ampa_openings < 1 and c.n_nmda_openings < 1) return false;
    if (c.n_releases < 1) return false;
    if (c.n_chem_steps < 10) return false;
    return c.n_ca_peaks >= 1 or c.n_nmda_events >= 1 or c.n_nmda_openings >= 1;
}
