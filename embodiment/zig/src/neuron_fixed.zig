//! FSOT active neuron — pure fixed-point continuous state (no IEEE float ops).
//! Twin of neuron.zig / neuron_batch single unit.

const fixed = @import("fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const scalar_f = @import("scalar_fixed.zig");
const trit = @import("trit.zig");

const Fixed = fixed.Fixed;

pub fn fromSFixed(s: Fixed, lo: Fixed, hi: Fixed) trit.Trit {
    if (fixed.lt(s, lo)) return -1;
    if (fixed.gt(s, hi)) return 1;
    return 0;
}

pub fn floorI32(x: Fixed) i32 {
    // trunc toward -inf for positive-dominant refractory; use trunc for parity with floor on +
    const q = @divTrunc(x, fixed.SCALE);
    return @intCast(q);
}

pub fn fracPart(x: Fixed) Fixed {
    const fl = @as(Fixed, @intCast(floorI32(x))) *% fixed.SCALE;
    return fixed.sub(x, fl);
}

/// phase = phase mod (2*pi) without float
pub fn modTwoPi(phase: Fixed) Fixed {
    const two_pi = fixed.mul(seeds_f.pi, fixed.fromInt(2));
    if (two_pi == 0) return phase;
    var p = phase;
    // keep in [0, 2pi)
    while (fixed.gt(p, two_pi) or p == two_pi) p = fixed.sub(p, two_pi);
    while (fixed.lt(p, 0)) p = fixed.add(p, two_pi);
    return p;
}

pub const NeuronF = struct {
    S: Fixed = seeds_f.resting_s,
    phase: Fixed = fixed.fromDecimalStr("0.05"),
    refractory: i32 = 0,
    ref_residual: Fixed = 0,
    adapt: Fixed = 0,
    ternary: trit.Trit = 0,
    spike_count: u32 = 0,
    train_count: i32 = 0,
    quiet_count: i32 = 0,
    steps_run: u32 = 0,

    n_channels: Fixed = seeds_f.neuro_n_channels,
    p_props: Fixed = seeds_f.neuro_p,
    d_eff: Fixed = seeds_f.neuro_d_eff,
    fire_thr: Fixed = fixed.fromDecimalStr("1.05"),
    ref_steps: i32 = 12,
    adapt_step: Fixed = fixed.fromDecimalStr("0.7"),
    adapt_gain: Fixed = fixed.fromDecimalStr("0.02"),
    adapt_decay: Fixed = fixed.fromDecimalStr("0.988"),
    resting_S: Fixed = seeds_f.resting_s,
    dt_ms: Fixed = fixed.fromInt(1),
    observed: bool = true,
    subms: bool = true,

    pub fn reset(self: *NeuronF) void {
        self.S = self.resting_S;
        self.phase = fixed.fromDecimalStr("0.05");
        self.refractory = 0;
        self.ref_residual = 0;
        self.adapt = 0;
        self.ternary = 0;
        self.spike_count = 0;
        self.train_count = 0;
        self.quiet_count = 0;
        self.steps_run = 0;
    }

    pub fn step(self: *NeuronF, stimulus: Fixed) struct { S: Fixed, fired: bool, phase: Fixed, ternary: trit.Trit } {
        var in_ref: bool = false;
        if (self.subms) {
            self.ref_residual = fixed.sub(self.ref_residual, self.dt_ms);
            if (fixed.lt(self.ref_residual, 0)) self.ref_residual = 0;
            const residual_block = fixed.gt(self.ref_residual, fixed.fromDecimalStr("0.000001"));
            in_ref = (self.refractory > 0) or residual_block;
            if ((self.refractory > 0) and !residual_block) {
                self.refractory -= 1;
            }
        } else {
            in_ref = self.refractory > 0;
            if (self.refractory > 0) self.refractory -= 1;
        }

        self.adapt = fixed.mul(self.adapt, self.adapt_decay);

        var stim_eff = fixed.sub(stimulus, self.adapt);
        stim_eff = fixed.clamp(stim_eff, fixed.fromDecimalStr("-0.5"), fixed.fromDecimalStr("1.5"));

        const recent_hits: Fixed = if (in_ref) fixed.fromInt(2) else blk: {
            var rh = fixed.mul(self.adapt, fixed.fromDecimalStr("2.5"));
            rh = fixed.clamp(rh, 0, fixed.fromInt(2));
            break :blk rh;
        };
        const delta_psi: Fixed = if (in_ref)
            fixed.mul(self.phase, fixed.fromDecimalStr("0.4"))
        else
            fixed.add(
                fixed.add(fixed.mul(self.phase, fixed.fromDecimalStr("0.85")), fixed.fromDecimalStr("0.05")),
                fixed.mul(stim_eff, fixed.fromDecimalStr("0.04")),
            );
        const delta_theta = fixed.add(fixed.fromInt(1), fixed.mul(fixed.abs(stim_eff), fixed.fromDecimalStr("0.8")));
        const rho = fixed.add(
            fixed.fromInt(1),
            fixed.sub(
                fixed.add(
                    fixed.mul(fixed.sub(self.S, self.resting_S), fixed.fromDecimalStr("0.08")),
                    fixed.mul(fixed.fromDecimalStr("0.55"), stim_eff),
                ),
                fixed.mul(fixed.fromDecimalStr("0.2"), self.adapt),
            ),
        );

        const S = scalar_f.computeScalar(
            self.n_channels,
            self.p_props,
            self.d_eff,
            recent_hits,
            delta_psi,
            delta_theta,
            rho,
            fixed.fromInt(1),
            fixed.fromInt(1),
            0,
            self.observed,
        );
        self.S = S;
        self.ternary = fromSFixed(S, fixed.fromDecimalStr("-0.4"), fixed.fromDecimalStr("0.4"));

        const stim_pos = if (fixed.gt(stim_eff, 0)) stim_eff else 0;
        const dphase = fixed.add(
            fixed.add(fixed.fromDecimalStr("0.0015"), fixed.mul(fixed.fromDecimalStr("0.10"), stim_pos)),
            fixed.mul(fixed.fromDecimalStr("0.02"), self.adapt),
        );
        self.phase = modTwoPi(fixed.add(self.phase, dphase));

        const thr = fixed.sub(
            fixed.add(self.fire_thr, fixed.mul(fixed.fromDecimalStr("0.35"), self.adapt)),
            fixed.mul(fixed.fromDecimalStr("0.50"), stim_pos),
        );
        const fired = (!in_ref) and fixed.gt(S, thr);

        if (fired) {
            self.quiet_count = 0;
            self.train_count += 1;
            const total_ref = fixed.add(
                fixed.fromInt(self.ref_steps),
                fixed.mul(fixed.fromInt(self.train_count), self.adapt_step),
            );
            var int_ref = floorI32(total_ref);
            if (int_ref < 0) int_ref = 0;
            if (int_ref > 250) int_ref = 250;
            self.refractory = int_ref;
            if (self.subms) {
                var fr = fracPart(total_ref);
                fr = fixed.clamp(fr, 0, fixed.fromDecimalStr("0.999"));
                self.ref_residual = fixed.mul(fr, self.dt_ms);
            }
            self.phase = 0;
            self.spike_count += 1;
            self.adapt = fixed.add(self.adapt, self.adapt_gain);
            if (fixed.gt(self.adapt, fixed.fromDecimalStr("0.35"))) self.adapt = fixed.fromDecimalStr("0.35");
        } else {
            self.quiet_count += 1;
            if (self.quiet_count > 150) self.train_count = 0;
        }

        self.steps_run += 1;
        return .{ .S = self.S, .fired = fired, .phase = self.phase, .ternary = self.ternary };
    }
};

pub fn runParityTrace(out_S: []Fixed, out_fired: []u8, out_tern: []i8) void {
    var n = NeuronF{};
    n.reset();
    var t: usize = 0;
    while (t < out_S.len) : (t += 1) {
        const stim: Fixed = if ((t % 80) < 20) fixed.fromDecimalStr("0.65") else fixed.fromDecimalStr("0.05");
        const r = n.step(stim);
        out_S[t] = r.S;
        out_fired[t] = if (r.fired) 1 else 0;
        out_tern[t] = r.ternary;
    }
}

pub fn paritySelfTest() struct { ok: bool, spikes: u32, last_S: Fixed } {
    var S: [200]Fixed = undefined;
    var fired: [200]u8 = undefined;
    var tern: [200]i8 = undefined;
    runParityTrace(S[0..], fired[0..], tern[0..]);
    var spikes: u32 = 0;
    for (fired) |f| {
        if (f != 0) spikes += 1;
    }
    const last = S[199];
    const ok = spikes >= 1 and fixed.gt(last, fixed.fromInt(-3)) and fixed.lt(last, fixed.fromInt(3));
    return .{ .ok = ok, .spikes = spikes, .last_S = last };
}

/// Compare fixed vs f64 neuron on same protocol (host lab gate).
pub fn parityVsF64() struct { ok: bool, max_abs_dS: f64, spike_mm: u32, spikes_f: u32, spikes_z: u32 } {
    const neuron_f64 = @import("neuron.zig");
    var Sf: [200]f64 = undefined;
    var ff: [200]u8 = undefined;
    var tf: [200]i8 = undefined;
    neuron_f64.runParityTrace(Sf[0..], ff[0..], tf[0..]);

    var Sz: [200]Fixed = undefined;
    var fz: [200]u8 = undefined;
    var tz: [200]i8 = undefined;
    runParityTrace(Sz[0..], fz[0..], tz[0..]);

    var max_ds: f64 = 0;
    var spike_mm: u32 = 0;
    var sp_f: u32 = 0;
    var sp_z: u32 = 0;
    var t: usize = 0;
    while (t < 200) : (t += 1) {
        const zs = fixed.toF64(Sz[t]);
        const ds = if (Sf[t] > zs) Sf[t] - zs else zs - Sf[t];
        if (ds > max_ds) max_ds = ds;
        if (ff[t] != fz[t]) spike_mm += 1;
        if (ff[t] != 0) sp_f += 1;
        if (fz[t] != 0) sp_z += 1;
    }
    // Gates: fixed should track f64; series residual can accumulate — allow modest dS
    const ok = max_ds < 0.15 and spike_mm <= 20 and sp_z >= 1;
    return .{ .ok = ok, .max_abs_dS = max_ds, .spike_mm = spike_mm, .spikes_f = sp_f, .spikes_z = sp_z };
}
