//! Single FSOT active neuron step — parity with fsot_nuron/neuron_batch.py
//! (one unit, sub-ms residual enabled, f64).

const scalar = @import("scalar.zig");
const seeds = @import("seeds.zig");
const trit = @import("trit.zig");

pub const Neuron = struct {
    S: f64 = seeds.resting_s,
    phase: f64 = 0.05,
    refractory: i32 = 0,
    ref_residual: f64 = 0.0,
    adapt: f64 = 0.0,
    ternary: trit.Trit = 0,
    spike_count: u32 = 0,
    train_count: i32 = 0,
    quiet_count: i32 = 0,
    steps_run: u32 = 0,

    // phenotype knobs (genetic / Allen lock may set these)
    n_channels: f64 = seeds.neuro_n_channels,
    p_props: f64 = seeds.neuro_p,
    d_eff: f64 = seeds.neuro_d_eff,
    fire_thr: f64 = 1.05,
    ref_steps: i32 = 12,
    adapt_step: f64 = 0.7,
    adapt_gain: f64 = 0.02,
    adapt_decay: f64 = 0.988,
    resting_S: f64 = seeds.resting_s,
    dt_ms: f64 = 1.0,
    observed: bool = true,
    subms: bool = true,

    pub fn reset(self: *Neuron) void {
        self.S = self.resting_S;
        self.phase = 0.05;
        self.refractory = 0;
        self.ref_residual = 0.0;
        self.adapt = 0.0;
        self.ternary = 0;
        self.spike_count = 0;
        self.train_count = 0;
        self.quiet_count = 0;
        self.steps_run = 0;
    }

    pub fn step(self: *Neuron, stimulus: f64) struct { S: f64, fired: bool, phase: f64, ternary: trit.Trit } {
        // refractory tick
        var in_ref: bool = false;
        if (self.subms) {
            self.ref_residual -= self.dt_ms;
            if (self.ref_residual < 0) self.ref_residual = 0;
            const residual_block = self.ref_residual > 1e-6;
            in_ref = (self.refractory > 0) or residual_block;
            if ((self.refractory > 0) and !residual_block) {
                self.refractory -= 1;
            }
        } else {
            in_ref = self.refractory > 0;
            if (self.refractory > 0) self.refractory -= 1;
        }

        self.adapt *= self.adapt_decay;

        var stim_eff = stimulus - self.adapt;
        if (stim_eff < -0.5) stim_eff = -0.5;
        if (stim_eff > 1.5) stim_eff = 1.5;

        const recent_hits: f64 = if (in_ref) 2.0 else blk: {
            var rh = self.adapt * 2.5;
            if (rh < 0) rh = 0;
            if (rh > 2) rh = 2;
            break :blk rh;
        };
        const delta_psi: f64 = if (in_ref)
            self.phase * 0.4
        else
            self.phase * 0.85 + 0.05 + stim_eff * 0.04;
        const delta_theta = 1.0 + @abs(stim_eff) * 0.8;
        const rho = 1.0 + (self.S - self.resting_S) * 0.08 + 0.55 * stim_eff - 0.2 * self.adapt;

        const S = scalar.computeScalar(
            self.n_channels,
            self.p_props,
            self.d_eff,
            recent_hits,
            delta_psi,
            delta_theta,
            rho,
            1.0,
            1.0,
            0.0,
            self.observed,
        );
        self.S = S;
        self.ternary = trit.fromS(@floatCast(S), -0.4, 0.4);

        const stim_pos = if (stim_eff > 0) stim_eff else 0;
        const dphase = 0.0015 + 0.10 * stim_pos + 0.02 * self.adapt;
        self.phase = @mod(self.phase + dphase, 2.0 * seeds.pi);

        const thr = self.fire_thr + 0.35 * self.adapt - 0.50 * stim_pos;
        const fired = (!in_ref) and (S > thr);

        if (fired) {
            self.quiet_count = 0;
            self.train_count += 1;
            const total_ref_ms = @as(f64, @floatFromInt(self.ref_steps)) +
                @as(f64, @floatFromInt(self.train_count)) * self.adapt_step;
            var int_ref: i32 = @intFromFloat(@floor(total_ref_ms));
            if (int_ref < 0) int_ref = 0;
            if (int_ref > 250) int_ref = 250;
            const frac = total_ref_ms - @floor(total_ref_ms);
            self.refractory = int_ref;
            if (self.subms) {
                var fr = frac;
                if (fr < 0) fr = 0;
                if (fr > 0.999) fr = 0.999;
                self.ref_residual = fr * self.dt_ms;
            }
            self.phase = 0.0;
            self.spike_count += 1;
            self.adapt += self.adapt_gain;
            if (self.adapt > 0.35) self.adapt = 0.35;
        } else {
            self.quiet_count += 1;
            if (self.quiet_count > 150) self.train_count = 0;
        }

        self.steps_run += 1;
        return .{ .S = self.S, .fired = fired, .phase = self.phase, .ternary = self.ternary };
    }
};

/// Fixed protocol for parity: rest 5 steps, then stim 0.65 for 20, etc.
pub fn runParityTrace(out_S: []f64, out_fired: []u8, out_tern: []i8) void {
    var n = Neuron{};
    n.reset();
    const n_steps = out_S.len;
    var t: usize = 0;
    while (t < n_steps) : (t += 1) {
        // periodic: 80-step cycle, 20-step burst of 0.65 (matches neuron_batch periodic)
        const stim: f64 = if ((t % 80) < 20) 0.65 else 0.05;
        const r = n.step(stim);
        out_S[t] = r.S;
        out_fired[t] = if (r.fired) 1 else 0;
        out_tern[t] = r.ternary;
    }
}

pub fn paritySelfTest() struct { ok: bool, spikes: u32, last_S: f64 } {
    var S: [200]f64 = undefined;
    var fired: [200]u8 = undefined;
    var tern: [200]i8 = undefined;
    runParityTrace(S[0..], fired[0..], tern[0..]);
    var spikes: u32 = 0;
    for (fired) |f| {
        if (f != 0) spikes += 1;
    }
    // Sanity: under periodic drive we should get some spikes and finite S
    const last = S[199];
    const finite = last == last and last > -3.1 and last < 3.1;
    const ok = finite and spikes >= 1;
    return .{ .ok = ok, .spikes = spikes, .last_S = last };
}
