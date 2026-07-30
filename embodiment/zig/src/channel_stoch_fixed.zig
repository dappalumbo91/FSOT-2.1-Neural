//! Full stochastic single-channel kinetics (Markov) on Fixed lattice.
//!
//! No continuous "open probability" shortcut for receptor current.
//! Each physical channel is a discrete Markov state; transitions are
//! Bernoulli trials with Fixed rates × dt (integer xorshift PRNG).
//!
//! AMPA (3-state, glu-dependent):
//!   C  closed
//!   O  open  (unitary AMPA current)
//!   D  desensitized
//!
//! NMDA (4-state, glu + voltage / Mg):
//!   C  closed
//!   O  open  (unitary Ca²⁺-permeable current)
//!   B  Mg²⁺-blocked (bound, not conducting)
//!   D  desensitized
//!
//! Literature-class scheme (simplified topology, lattice-timed rates):
//!   AMPA: Jonas/Sakmann style C↔O, O→D, D→C
//!   NMDA: yearwood/Jahr-style open + Mg block as separate state
//!
//! All Fixed; no IEEE float on the path.

const fixed = @import("fixed.zig");
const Fixed = fixed.Fixed;

pub const N_AMPA: usize = 12;
pub const N_NMDA: usize = 8;

// AMPA states
pub const AMPA_C: u8 = 0;
pub const AMPA_O: u8 = 1;
pub const AMPA_D: u8 = 2;

// NMDA states
pub const NMDA_C: u8 = 0;
pub const NMDA_O: u8 = 1;
pub const NMDA_B: u8 = 2; // Mg blocked
pub const NMDA_D: u8 = 3;

/// Integer PRNG — deterministic, no float (xorshift64*).
pub const Rng = struct {
    s: u64,

    pub fn init(seed: u64) Rng {
        var s = seed;
        if (s == 0) s = 0x9E3779B97F4A7C15;
        return .{ .s = s };
    }

    pub fn next(self: *Rng) u64 {
        var x = self.s;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.s = x;
        return x *% 0x2545F4914F6CDD1D;
    }

    /// Uniform Fixed in [0, 1).
    pub fn nextUnit(self: *Rng) Fixed {
        // top 32 bits → fraction of SCALE
        const u = self.next() >> 32;
        // (u / 2^32) * SCALE
        const wide: i128 = @as(i128, @intCast(u)) * @as(i128, fixed.SCALE);
        return @intCast(wide >> 32);
    }

    /// Bernoulli: true with probability p (Fixed in [0,1]).
    pub fn bernoulli(self: *Rng, p: Fixed) bool {
        if (p <= 0) return false;
        if (fixed.gt(p, fixed.fromInt(1)) or p == fixed.fromInt(1)) return true;
        return fixed.lt(self.nextUnit(), p);
    }
};

/// p = 1 - exp(-k*dt) ≈ min(1, k*dt) for small rates (Fixed).
pub fn markovProb(rate: Fixed, dt: Fixed) Fixed {
    const p = fixed.mul(rate, dt);
    if (fixed.gt(p, fixed.fromInt(1))) return fixed.fromInt(1);
    if (fixed.lt(p, 0)) return 0;
    return p;
}

/// Bundle of single channels for one spine.
pub const ChannelBank = struct {
    ampa: [N_AMPA]u8 = .{AMPA_C} ** N_AMPA,
    nmda: [N_NMDA]u8 = .{NMDA_C} ** N_NMDA,
    n_ampa_open: u8 = 0,
    n_nmda_open: u8 = 0,
    n_nmda_blocked: u8 = 0,
    // event counters
    n_ampa_openings: u32 = 0,
    n_nmda_openings: u32 = 0,
    n_nmda_block: u32 = 0,
    n_nmda_unblock: u32 = 0,
    n_transitions: u32 = 0,

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

    /// AMPA rates (1/ms class) as function of cleft glu (0..2).
    fn ampaRates(glu: Fixed) struct { c2o: Fixed, o2c: Fixed, o2d: Fixed, d2c: Fixed } {
        // α_open ∝ glu / (glu + K_d)
        const kd = fixed.fromDecimalStr("0.35");
        const sat = fixed.div(glu, fixed.add(glu, kd));
        return .{
            .c2o = fixed.mul(fixed.fromDecimalStr("2.8"), sat),
            .o2c = fixed.fromDecimalStr("1.2"),
            .o2d = fixed.fromDecimalStr("0.55"),
            .d2c = fixed.fromDecimalStr("0.18"),
        };
    }

    /// NMDA rates: open from C depends on glu; block/unblock on V (0..1 relief).
    fn nmdaRates(glu: Fixed, mg_relief: Fixed) struct {
        c2o: Fixed,
        o2c: Fixed,
        o2b: Fixed,
        b2o: Fixed,
        o2d: Fixed,
        d2c: Fixed,
    } {
        const kd = fixed.fromDecimalStr("0.28");
        const sat = fixed.div(glu, fixed.add(glu, kd));
        // Mg block rate high when relief low
        const block = fixed.mul(fixed.fromDecimalStr("3.5"), fixed.sub(fixed.fromInt(1), mg_relief));
        const unblock = fixed.mul(fixed.fromDecimalStr("2.2"), mg_relief);
        return .{
            .c2o = fixed.mul(fixed.fromDecimalStr("1.6"), sat),
            .o2c = fixed.fromDecimalStr("0.9"),
            .o2b = block,
            .b2o = unblock,
            .o2d = fixed.fromDecimalStr("0.35"),
            .d2c = fixed.fromDecimalStr("0.12"),
        };
    }

    /// One stochastic substep for all channels.
    pub fn step(self: *ChannelBank, rng: *Rng, glu: Fixed, mg_relief: Fixed, dt: Fixed) void {
        const ar = ampaRates(glu);
        const nr = nmdaRates(glu, mg_relief);

        var i: usize = 0;
        while (i < N_AMPA) : (i += 1) {
            const st = self.ampa[i];
            var next = st;
            switch (st) {
                AMPA_C => {
                    if (rng.bernoulli(markovProb(ar.c2o, dt))) {
                        next = AMPA_O;
                        self.n_ampa_openings += 1;
                        self.n_transitions += 1;
                    }
                },
                AMPA_O => {
                    // competing O→C vs O→D
                    const p_c = markovProb(ar.o2c, dt);
                    const p_d = markovProb(ar.o2d, dt);
                    // sequential trial (approx independent for small p)
                    if (rng.bernoulli(p_d)) {
                        next = AMPA_D;
                        self.n_transitions += 1;
                    } else if (rng.bernoulli(p_c)) {
                        next = AMPA_C;
                        self.n_transitions += 1;
                    }
                },
                AMPA_D => {
                    if (rng.bernoulli(markovProb(ar.d2c, dt))) {
                        next = AMPA_C;
                        self.n_transitions += 1;
                    }
                },
                else => next = AMPA_C,
            }
            self.ampa[i] = next;
        }

        i = 0;
        while (i < N_NMDA) : (i += 1) {
            const st = self.nmda[i];
            var next = st;
            switch (st) {
                NMDA_C => {
                    if (rng.bernoulli(markovProb(nr.c2o, dt))) {
                        next = NMDA_O;
                        self.n_nmda_openings += 1;
                        self.n_transitions += 1;
                    }
                },
                NMDA_O => {
                    const p_c = markovProb(nr.o2c, dt);
                    const p_b = markovProb(nr.o2b, dt);
                    const p_d = markovProb(nr.o2d, dt);
                    if (rng.bernoulli(p_b)) {
                        next = NMDA_B;
                        self.n_nmda_block += 1;
                        self.n_transitions += 1;
                    } else if (rng.bernoulli(p_d)) {
                        next = NMDA_D;
                        self.n_transitions += 1;
                    } else if (rng.bernoulli(p_c)) {
                        next = NMDA_C;
                        self.n_transitions += 1;
                    }
                },
                NMDA_B => {
                    if (rng.bernoulli(markovProb(nr.b2o, dt))) {
                        next = NMDA_O;
                        self.n_nmda_unblock += 1;
                        self.n_transitions += 1;
                    } else if (rng.bernoulli(markovProb(nr.o2c, dt))) {
                        // leave block into closed occasionally
                        next = NMDA_C;
                        self.n_transitions += 1;
                    }
                },
                NMDA_D => {
                    if (rng.bernoulli(markovProb(nr.d2c, dt))) {
                        next = NMDA_C;
                        self.n_transitions += 1;
                    }
                },
                else => next = NMDA_C,
            }
            self.nmda[i] = next;
        }
        self.recount();
    }

    /// Unitary conductances (relative Fixed).
    pub fn ampaCurrent(self: *const ChannelBank) Fixed {
        // i = n_open * g_unit * driving (normalized)
        return fixed.mul(fixed.fromInt(@intCast(self.n_ampa_open)), fixed.fromDecimalStr("0.08"));
    }

    pub fn nmdaCaCurrent(self: *const ChannelBank) Fixed {
        // Ca-permeable fraction through open NMDA
        return fixed.mul(fixed.fromInt(@intCast(self.n_nmda_open)), fixed.fromDecimalStr("0.14"));
    }
};

/// Stochastic vesicle release: binomial N_ves trials with p_release.
pub const N_VESICLES: u32 = 8;

pub fn stochasticRelease(rng: *Rng, p_release: Fixed) struct { quanta: u32, glu: Fixed } {
    var q: u32 = 0;
    var i: u32 = 0;
    while (i < N_VESICLES) : (i += 1) {
        if (rng.bernoulli(p_release)) q += 1;
    }
    // each quantum adds fixed glu load
    const glu = fixed.mul(fixed.fromInt(@intCast(q)), fixed.fromDecimalStr("0.22"));
    return .{ .quanta = q, .glu = glu };
}

pub fn selfTest() bool {
    var rng = Rng.init(0xC0FFEE);
    var bank = ChannelBank{};
    const dt = fixed.div(fixed.fromInt(1), fixed.fromInt(4));
    // high glu, depolarized → many openings
    var t: u32 = 0;
    while (t < 200) : (t += 1) {
        bank.step(&rng, fixed.fromDecimalStr("1.2"), fixed.fromDecimalStr("0.9"), dt);
    }
    if (bank.n_transitions < 10) return false;
    if (bank.n_ampa_openings < 1 and bank.n_nmda_openings < 1) return false;
    // stochastic release
    const rel = stochasticRelease(&rng, fixed.fromDecimalStr("0.4"));
    return rel.quanta <= N_VESICLES;
}
