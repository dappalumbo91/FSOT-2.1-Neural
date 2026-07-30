//! Neuromodulators as first-class Fixed ODEs (not free gain knobs).
//!
//! Biological map (process scale, not receptor kinetics):
//!   DA  (dopamine, VTA/SNc proxy)     — reward / RPE → STDP LTP gain
//!   ACh (acetylcholine, BF proxy)    — attention / encoding sharpness
//!   NE  (norepinephrine, LC proxy)   — arousal / external drive gain
//!   5-HT (serotonin, raphe proxy)    — quiet / rest tone (opposes NE-like arousal)
//!
//! Law (per species, 1 ms step) — exponential approach to phase target:
//!   x_target = clamp(tonic + drive, 0, x_max)
//!   dx = (x_target − x) / τ · dt
//!   x ← clamp(x + dx, 0, x_max)
//!
//! Coupling into plasticity (exported scales, unitless Fixed):
//!   η_stdp   = η0 · (1 + k_da · DA) · (1 + k_ach · ACh)
//!   g_encode = (1 + k_ach_e · ACh) · (1 + k_ne · NE)
//!   g_rest   = (1 + k_ht · HT) / (1 + k_ne_r · NE)
//!
//! FSOT: rates/time constants are seed-scaled (ψ_con, η_eff, φ) — zero free LSQ.

const fixed = @import("fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const Fixed = fixed.Fixed;

pub const Species = enum(u8) { da = 0, ach = 1, ne = 2, ht = 3 };

pub const NeuromodState = struct {
    da: Fixed = 0,
    ach: Fixed = 0,
    ne: Fixed = 0,
    ht: Fixed = 0,
    /// cumulative for diagnostics
    mean_da: Fixed = 0,
    mean_ach: Fixed = 0,
    mean_ne: Fixed = 0,
    mean_ht: Fixed = 0,
    n_steps: u32 = 0,
    n_da_pulses: u32 = 0,
    n_phase_set: u32 = 0,
};

/// Time constants (ms) — slow vs ion channels; seed-scaled order.
fn tauDa() Fixed {
    return fixed.mul(fixed.fromInt(200), seeds_f.phi); // ~324 ms
}
fn tauAch() Fixed {
    return fixed.mul(fixed.fromInt(150), seeds_f.psi_con); // ~95 ms-class effective
}
fn tauNe() Fixed {
    return fixed.fromInt(180);
}
fn tauHt() Fixed {
    return fixed.mul(fixed.fromInt(250), seeds_f.eta_eff); // slower quiet tone
}

fn xMax() Fixed {
    return fixed.fromDecimalStr("1.5");
}

pub const Phase = enum(u8) {
    wake_encode,
    wake_probe,
    wake_rest,
    sleep_nrem,
    sleep_replay,
};

/// Phase-dependent tonic drives (biologically ordered, not fitted).
pub fn phaseTonic(phase: Phase) struct { da: Fixed, ach: Fixed, ne: Fixed, ht: Fixed } {
    return switch (phase) {
        .wake_encode => .{
            .da = fixed.fromDecimalStr("0.08"),
            .ach = fixed.fromDecimalStr("0.55"),
            .ne = fixed.fromDecimalStr("0.40"),
            .ht = fixed.fromDecimalStr("0.20"),
        },
        .wake_probe => .{
            .da = fixed.fromDecimalStr("0.06"),
            .ach = fixed.fromDecimalStr("0.45"),
            .ne = fixed.fromDecimalStr("0.35"),
            .ht = fixed.fromDecimalStr("0.22"),
        },
        .wake_rest => .{
            .da = fixed.fromDecimalStr("0.03"),
            .ach = fixed.fromDecimalStr("0.15"),
            .ne = fixed.fromDecimalStr("0.12"),
            .ht = fixed.fromDecimalStr("0.35"),
        },
        .sleep_nrem => .{
            .da = fixed.fromDecimalStr("0.02"),
            .ach = fixed.fromDecimalStr("0.05"), // BF ACh low in SWS
            .ne = fixed.fromDecimalStr("0.04"), // LC quiet
            .ht = fixed.fromDecimalStr("0.50"),
        },
        .sleep_replay => .{
            .da = fixed.fromDecimalStr("0.25"), // reactivation tagging pulse baseline
            .ach = fixed.fromDecimalStr("0.08"),
            .ne = fixed.fromDecimalStr("0.06"),
            .ht = fixed.fromDecimalStr("0.40"),
        },
    };
}

fn stepOne(x: Fixed, tau: Fixed, drive: Fixed, tonic: Fixed, dt: Fixed) Fixed {
    // dx = (target - x) / tau * dt  — first-order approach to phase setpoint
    const target = fixed.clamp(fixed.add(tonic, drive), 0, xMax());
    const dx = fixed.mul(fixed.div(fixed.sub(target, x), tau), dt);
    return fixed.clamp(fixed.add(x, dx), 0, xMax());
}

/// One network tick (dt_ms usually 1).
pub fn step(s: *NeuromodState, phase: Phase, drive_da: Fixed, drive_ach: Fixed, drive_ne: Fixed, drive_ht: Fixed, dt_ms: Fixed) void {
    const t = phaseTonic(phase);
    s.da = stepOne(s.da, tauDa(), drive_da, t.da, dt_ms);
    s.ach = stepOne(s.ach, tauAch(), drive_ach, t.ach, dt_ms);
    s.ne = stepOne(s.ne, tauNe(), drive_ne, t.ne, dt_ms);
    s.ht = stepOne(s.ht, tauHt(), drive_ht, t.ht, dt_ms);
    s.mean_da = fixed.add(s.mean_da, s.da);
    s.mean_ach = fixed.add(s.mean_ach, s.ach);
    s.mean_ne = fixed.add(s.mean_ne, s.ne);
    s.mean_ht = fixed.add(s.mean_ht, s.ht);
    s.n_steps += 1;
}

/// Transient DA pulse (reward / successful encode tag).
pub fn pulseDa(s: *NeuromodState, amp: Fixed) void {
    s.da = fixed.clamp(fixed.add(s.da, amp), 0, xMax());
    s.n_da_pulses += 1;
}

pub fn setPhase(s: *NeuromodState, phase: Phase) void {
    _ = s;
    _ = phase;
    // reserved for future phase-locked stores; counter lives on probe
}

/// STDP learning-rate scale from neuromodulators.
pub fn stdpEtaScale(s: *const NeuromodState) Fixed {
    // η = 1 + 0.8*DA + 0.4*ACh  (Fixed)
    const one = fixed.fromInt(1);
    const da_t = fixed.mul(s.da, fixed.fromDecimalStr("0.80"));
    const ach_t = fixed.mul(s.ach, fixed.fromDecimalStr("0.40"));
    return fixed.add(one, fixed.add(da_t, ach_t));
}

/// External encode / sensory gain.
pub fn encodeGain(s: *const NeuromodState) Fixed {
    const one = fixed.fromInt(1);
    return fixed.mul(
        fixed.add(one, fixed.mul(s.ach, fixed.fromDecimalStr("0.70"))),
        fixed.add(one, fixed.mul(s.ne, fixed.fromDecimalStr("0.50"))),
    );
}

/// Rest / sleep quiet gain (high HT, low NE → more quiet).
pub fn restQuietGain(s: *const NeuromodState) Fixed {
    const num = fixed.add(fixed.fromInt(1), fixed.mul(s.ht, fixed.fromDecimalStr("0.60")));
    const den = fixed.add(fixed.fromInt(1), fixed.mul(s.ne, fixed.fromDecimalStr("0.80")));
    return fixed.div(num, den);
}

/// Sigma-band proxy (sleep spindle-ish) during NREM/replay: high HT * low ACh * reactivation.
pub fn sigmaProxy(s: *const NeuromodState, reactivate: Fixed) Fixed {
    const base = fixed.mul(s.ht, fixed.sub(fixed.fromInt(1), fixed.mul(s.ach, fixed.fromDecimalStr("0.5"))));
    return fixed.mul(fixed.add(base, fixed.fromDecimalStr("0.05")), fixed.add(fixed.fromInt(1), reactivate));
}

pub fn meansFinalize(s: *NeuromodState) void {
    if (s.n_steps == 0) return;
    const n = fixed.fromInt(@intCast(s.n_steps));
    s.mean_da = fixed.div(s.mean_da, n);
    s.mean_ach = fixed.div(s.mean_ach, n);
    s.mean_ne = fixed.div(s.mean_ne, n);
    s.mean_ht = fixed.div(s.mean_ht, n);
}

pub fn selfTest() bool {
    var s: NeuromodState = .{};
    var t: u32 = 0;
    while (t < 50) : (t += 1) {
        step(&s, .wake_encode, 0, 0, 0, 0, fixed.fromInt(1));
    }
    // ACh should rise under wake_encode tonic
    if (!fixed.gt(s.ach, fixed.fromDecimalStr("0.15"))) return false;
    if (!fixed.gt(s.ne, fixed.fromDecimalStr("0.08"))) return false;
    // sleep: ACh falls relative if we switch long enough
    t = 0;
    while (t < 80) : (t += 1) {
        step(&s, .sleep_nrem, 0, 0, 0, 0, fixed.fromInt(1));
    }
    if (!fixed.lt(s.ach, fixed.fromDecimalStr("0.35"))) return false;
    pulseDa(&s, fixed.fromDecimalStr("0.5"));
    if (!fixed.gt(s.da, fixed.fromDecimalStr("0.3"))) return false;
    const eta = stdpEtaScale(&s);
    if (!fixed.gt(eta, fixed.fromInt(1))) return false;
    return true;
}
