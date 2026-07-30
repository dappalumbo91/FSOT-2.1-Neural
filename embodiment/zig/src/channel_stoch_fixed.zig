//! Stochastic single-channel kinetics — refined biophysics (Fixed lattice).
//!
//! Improvements over coarse 3/4-state ms shortcuts:
//!   • Explicit lattice time: NETWORK_TICK_MS = 1 ms; channel dt = 50 µs
//!   • Transition probability P = 1 − exp(−k·dt)  (not min(1,k·dt))
//!   • Competing exits: rate-weighted choice among transitions
//!   • AMPA multi-binding: C0 → C1 → O, desens D (Jonas-class topology)
//!   • NMDA multi-binding + Mg block state: C0 → C1 → O ↔ B_Mg, D
//!   • More channels/spine (AMPA 48, NMDA 16) — finite but synapse-scale
//!   • Quantal release: binomial + release-site refractory
//!
//! Still NOT all-atom MD. This is stochastic single-channel Markov at
//! biophysically motivated rates on the FSOT Fixed mind.

const fixed = @import("fixed.zig");
const Fixed = fixed.Fixed;

/// Network spike/chem outer tick duration (ms).
pub const NETWORK_TICK_MS: Fixed = fixed.fromInt(1);
/// Channel Markov integration step (ms) = 0.05 ms = 50 µs.
pub const CHANNEL_DT_MS: Fixed = fixed.fromDecimalStr("0.05");
/// Channel substeps per 1 ms network tick = 20.
pub const CHANNEL_SUBSTEPS_PER_MS: u32 = 20;

pub const N_AMPA: usize = 48;
pub const N_NMDA: usize = 16;
pub const N_RELEASE_SITES: u32 = 12; // docked vesicle sites

// --- AMPA states (ligand-gated multi-binding) ---
// C0: unbound closed | C1: one Glu bound closed | O: open | D: desensitized
pub const AMPA_C0: u8 = 0;
pub const AMPA_C1: u8 = 1;
pub const AMPA_O: u8 = 2;
pub const AMPA_D: u8 = 3;

// --- NMDA states ---
// C0 unbound | C1 Glu-bound | O open | B Mg-blocked | D desensitized
pub const NMDA_C0: u8 = 0;
pub const NMDA_C1: u8 = 1;
pub const NMDA_O: u8 = 2;
pub const NMDA_B: u8 = 3;
pub const NMDA_D: u8 = 4;

pub const Rng = struct {
    s: u64,
    pub fn init(seed: u64) Rng {
        return .{ .s = if (seed == 0) 0x9E3779B97F4A7C15 else seed };
    }
    pub fn next(self: *Rng) u64 {
        var x = self.s;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.s = x;
        return x *% 0x2545F4914F6CDD1D;
    }
    pub fn nextUnit(self: *Rng) Fixed {
        const u = self.next() >> 32;
        const wide: i128 = @as(i128, @intCast(u)) * @as(i128, fixed.SCALE);
        return @intCast(wide >> 32);
    }
    pub fn bernoulli(self: *Rng, p: Fixed) bool {
        if (p <= 0) return false;
        if (!fixed.lt(p, fixed.fromInt(1))) return true;
        return fixed.lt(self.nextUnit(), p);
    }
};

/// Exact discrete-time survival: P(event) = 1 − exp(−rate·dt), rate in 1/ms, dt in ms.
pub fn markovProb(rate: Fixed, dt: Fixed) Fixed {
    if (rate <= 0 or dt <= 0) return 0;
    const x = fixed.mul(rate, dt);
    // clamp large: if x > 5, exp(-x)≈0 → p≈1
    if (fixed.gt(x, fixed.fromInt(5))) return fixed.fromInt(1);
    const e = fixed.exp(fixed.negate(x));
    return fixed.clamp(fixed.sub(fixed.fromInt(1), e), 0, fixed.fromInt(1));
}

/// Competing transitions: with probability 1-exp(-sum r dt), pick transition i ∝ r_i.
/// Returns index of chosen transition, or -1 if none.
pub fn competing(rng: *Rng, rates: []const Fixed, dt: Fixed) i32 {
    var sum: Fixed = 0;
    for (rates) |r| {
        if (fixed.gt(r, 0)) sum = fixed.add(sum, r);
    }
    if (sum <= 0) return -1;
    const p_any = markovProb(sum, dt);
    if (!rng.bernoulli(p_any)) return -1;
    // pick proportional to rate
    const u = rng.nextUnit();
    var acc: Fixed = 0;
    var i: usize = 0;
    while (i < rates.len) : (i += 1) {
        if (rates[i] <= 0) continue;
        acc = fixed.add(acc, fixed.div(rates[i], sum));
        if (!fixed.lt(u, acc)) continue;
        return @intCast(i);
    }
    return @intCast(rates.len - 1);
}

pub const ChannelBank = struct {
    ampa: [N_AMPA]u8 = .{AMPA_C0} ** N_AMPA,
    nmda: [N_NMDA]u8 = .{NMDA_C0} ** N_NMDA,
    /// release-site available (1) or refractory (0)
    site_ready: [N_RELEASE_SITES]u8 = .{1} ** N_RELEASE_SITES,
    site_ref_left: [N_RELEASE_SITES]u8 = .{0} ** N_RELEASE_SITES,
    n_ampa_open: u8 = 0,
    n_nmda_open: u8 = 0,
    n_nmda_blocked: u8 = 0,
    n_ampa_openings: u32 = 0,
    n_nmda_openings: u32 = 0,
    n_nmda_block: u32 = 0,
    n_nmda_unblock: u32 = 0,
    n_transitions: u32 = 0,
    n_binding: u32 = 0,

    pub fn recount(self: *ChannelBank) void {
        var ao: u8 = 0;
        var no: u8 = 0;
        var nb: u8 = 0;
        var i: usize = 0;
        while (i < N_AMPA) : (i += 1) {
            if (self.ampa[i] == AMPA_O) ao += 1;
        }
        i = 0;
        while (i < N_NMDA) : (i += 1) {
            if (self.nmda[i] == NMDA_O) no += 1;
            if (self.nmda[i] == NMDA_B) nb += 1;
        }
        self.n_ampa_open = ao;
        self.n_nmda_open = no;
        self.n_nmda_blocked = nb;
    }

    /// AMPA rates (1/ms). Kon scaled by [Glu] (glu Fixed is relative concentration).
    fn stepAmpaOne(self: *ChannelBank, i: usize, rng: *Rng, glu: Fixed, dt: Fixed) void {
        const st = self.ampa[i];
        // binding rate ∝ [Glu]; unbinding, open, desens literature-class ms⁻¹
        const kon = fixed.mul(fixed.fromDecimalStr("12.0"), glu); // C0→C1
        const koff = fixed.fromDecimalStr("4.0"); // C1→C0
        const beta = fixed.fromDecimalStr("8.0"); // C1→O open
        const alpha = fixed.fromDecimalStr("3.5"); // O→C1 close
        const des = fixed.fromDecimalStr("1.8"); // O→D
        const res = fixed.fromDecimalStr("0.25"); // D→C0 recover
        var next = st;
        switch (st) {
            AMPA_C0 => {
                if (rng.bernoulli(markovProb(kon, dt))) {
                    next = AMPA_C1;
                    self.n_binding += 1;
                    self.n_transitions += 1;
                }
            },
            AMPA_C1 => {
                const rates = [_]Fixed{ koff, beta };
                const choice = competing(rng, rates[0..], dt);
                if (choice == 0) {
                    next = AMPA_C0;
                    self.n_transitions += 1;
                } else if (choice == 1) {
                    next = AMPA_O;
                    self.n_ampa_openings += 1;
                    self.n_transitions += 1;
                }
            },
            AMPA_O => {
                const rates = [_]Fixed{ alpha, des };
                const choice = competing(rng, rates[0..], dt);
                if (choice == 0) {
                    next = AMPA_C1;
                    self.n_transitions += 1;
                } else if (choice == 1) {
                    next = AMPA_D;
                    self.n_transitions += 1;
                }
            },
            AMPA_D => {
                if (rng.bernoulli(markovProb(res, dt))) {
                    next = AMPA_C0;
                    self.n_transitions += 1;
                }
            },
            else => next = AMPA_C0,
        }
        self.ampa[i] = next;
    }

    fn stepNmdaOne(self: *ChannelBank, i: usize, rng: *Rng, glu: Fixed, mg_relief: Fixed, dt: Fixed) void {
        const st = self.nmda[i];
        const kon = fixed.mul(fixed.fromDecimalStr("6.0"), glu);
        const koff = fixed.fromDecimalStr("1.5");
        const beta = fixed.fromDecimalStr("4.5"); // open
        const alpha = fixed.fromDecimalStr("2.0"); // close
        // Mg: block rate high at rest; unblock ∝ relief
        const k_block = fixed.mul(fixed.fromDecimalStr("15.0"), fixed.sub(fixed.fromInt(1), mg_relief));
        const k_unblock = fixed.mul(fixed.fromDecimalStr("12.0"), fixed.add(mg_relief, fixed.fromDecimalStr("0.05")));
        const des = fixed.fromDecimalStr("0.9");
        const res = fixed.fromDecimalStr("0.15");
        var next = st;
        switch (st) {
            NMDA_C0 => {
                if (rng.bernoulli(markovProb(kon, dt))) {
                    next = NMDA_C1;
                    self.n_binding += 1;
                    self.n_transitions += 1;
                }
            },
            NMDA_C1 => {
                const rates = [_]Fixed{ koff, beta };
                const choice = competing(rng, rates[0..], dt);
                if (choice == 0) {
                    next = NMDA_C0;
                    self.n_transitions += 1;
                } else if (choice == 1) {
                    next = NMDA_O;
                    self.n_nmda_openings += 1;
                    self.n_transitions += 1;
                }
            },
            NMDA_O => {
                const rates = [_]Fixed{ alpha, k_block, des };
                const choice = competing(rng, rates[0..], dt);
                if (choice == 0) {
                    next = NMDA_C1;
                    self.n_transitions += 1;
                } else if (choice == 1) {
                    next = NMDA_B;
                    self.n_nmda_block += 1;
                    self.n_transitions += 1;
                } else if (choice == 2) {
                    next = NMDA_D;
                    self.n_transitions += 1;
                }
            },
            NMDA_B => {
                const rates = [_]Fixed{ k_unblock, fixed.mul(alpha, fixed.fromDecimalStr("0.3")) };
                const choice = competing(rng, rates[0..], dt);
                if (choice == 0) {
                    next = NMDA_O;
                    self.n_nmda_unblock += 1;
                    self.n_transitions += 1;
                } else if (choice == 1) {
                    next = NMDA_C1;
                    self.n_transitions += 1;
                }
            },
            NMDA_D => {
                if (rng.bernoulli(markovProb(res, dt))) {
                    next = NMDA_C0;
                    self.n_transitions += 1;
                }
            },
            else => next = NMDA_C0,
        }
        self.nmda[i] = next;
    }

    /// Advance all channels by dt (typically CHANNEL_DT_MS = 50 µs).
    pub fn step(self: *ChannelBank, rng: *Rng, glu: Fixed, mg_relief: Fixed, dt: Fixed) void {
        var i: usize = 0;
        while (i < N_AMPA) : (i += 1) self.stepAmpaOne(i, rng, glu, dt);
        i = 0;
        while (i < N_NMDA) : (i += 1) self.stepNmdaOne(i, rng, glu, mg_relief, dt);
        // release-site recovery (refractory countdown in channel steps)
        i = 0;
        while (i < N_RELEASE_SITES) : (i += 1) {
            if (self.site_ref_left[i] > 0) {
                self.site_ref_left[i] -= 1;
                if (self.site_ref_left[i] == 0) self.site_ready[i] = 1;
            }
        }
        self.recount();
    }

    /// Full 1 ms of channel kinetics = 20 × 50 µs steps.
    pub fn stepOneMs(self: *ChannelBank, rng: *Rng, glu: Fixed, mg_relief: Fixed) void {
        var s: u32 = 0;
        while (s < CHANNEL_SUBSTEPS_PER_MS) : (s += 1) {
            self.step(rng, glu, mg_relief, CHANNEL_DT_MS);
        }
    }

    pub fn ampaCurrent(self: *const ChannelBank) Fixed {
        // unitary g_AMPA relative; scale by open count / N
        return fixed.mul(fixed.fromInt(@intCast(self.n_ampa_open)), fixed.fromDecimalStr("0.035"));
    }

    pub fn nmdaCaCurrent(self: *const ChannelBank) Fixed {
        return fixed.mul(fixed.fromInt(@intCast(self.n_nmda_open)), fixed.fromDecimalStr("0.09"));
    }
};

/// Stochastic multi-site quantal release with site refractory (~few ms).
pub fn stochasticRelease(rng: *Rng, bank: *ChannelBank, p_base: Fixed) struct { quanta: u32, glu: Fixed } {
    var q: u32 = 0;
    var i: u32 = 0;
    while (i < N_RELEASE_SITES) : (i += 1) {
        if (bank.site_ready[i] == 0) continue;
        if (rng.bernoulli(p_base)) {
            q += 1;
            bank.site_ready[i] = 0;
            // refractory ~ 3–8 ms of channel steps (60–160 × 50µs)
            const extra = @as(u8, @intCast(rng.next() % 100));
            bank.site_ref_left[i] = 60 + extra;
        }
    }
    const glu = fixed.mul(fixed.fromInt(@intCast(q)), fixed.fromDecimalStr("0.18"));
    return .{ .quanta = q, .glu = glu };
}

pub fn selfTest() bool {
    var rng = Rng.init(0xA11CE);
    var bank = ChannelBank{};
    // high glu, depolarized — should open many channels stochastically
    var t: u32 = 0;
    while (t < 40) : (t += 1) {
        bank.stepOneMs(&rng, fixed.fromDecimalStr("1.5"), fixed.fromDecimalStr("0.95"));
    }
    if (bank.n_transitions < 50) return false;
    if (bank.n_ampa_openings < 5) return false;
    if (bank.n_nmda_openings < 1) return false;
    // exact exp form: rate 1/ms, dt 1ms → p = 1-e^-1 ≈ 0.632
    const p = markovProb(fixed.fromInt(1), fixed.fromInt(1));
    // allow band around 0.63
    if (fixed.lt(p, fixed.fromDecimalStr("0.55"))) return false;
    if (fixed.gt(p, fixed.fromDecimalStr("0.72"))) return false;
    const rel = stochasticRelease(&rng, &bank, fixed.fromDecimalStr("0.5"));
    return rel.quanta <= N_RELEASE_SITES;
}
