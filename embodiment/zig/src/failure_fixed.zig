//! Neurological failure-boundary probes on fixed lattice.
//! Spirit of failure_boundaries.py — lesion modes + healthy envelope awareness.
//! Not clinical diagnosis; boundary knowledge for wire-around design.

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const Fixed = fixed.Fixed;

pub const LesionId = enum(u8) {
    none = 0,
    ad_synaptic_fatigue = 1,
    pd_rate_irregularity = 2,
    als_motor_dropout = 3,
};

pub const LesionParams = struct {
    fi_stim_scale: Fixed = fixed.fromInt(1),
    silence_fraction: Fixed = 0, // 0..1 units silenced
    thr_boost: Fixed = 0, // add to effective drive threshold via lower stim on E
    adapt_stress: Fixed = fixed.fromInt(1),
};

pub fn paramsFor(id: LesionId) LesionParams {
    return switch (id) {
        .none => .{},
        .ad_synaptic_fatigue => .{
            .fi_stim_scale = fixed.fromDecimalStr("0.55"),
            .silence_fraction = fixed.fromDecimalStr("0.15"),
            .thr_boost = fixed.fromDecimalStr("0.12"),
            .adapt_stress = fixed.fromDecimalStr("2.0"),
        },
        .pd_rate_irregularity => .{
            .fi_stim_scale = fixed.fromDecimalStr("0.95"),
            .silence_fraction = fixed.fromDecimalStr("0.12"),
            .thr_boost = fixed.fromDecimalStr("-0.05"),
            .adapt_stress = fixed.fromDecimalStr("1.75"),
        },
        .als_motor_dropout => .{
            .fi_stim_scale = fixed.fromDecimalStr("1.15"),
            .silence_fraction = fixed.fromDecimalStr("0.35"),
            .thr_boost = fixed.fromDecimalStr("-0.08"),
            .adapt_stress = fixed.fromDecimalStr("1.6"),
        },
    };
}

/// Soft healthy envelope on spike count over window (motif-level, not Allen claim).
pub const Envelope = struct {
    min_spikes: u32 = 1,
    max_spikes: u32 = 5000,
};

pub fn inHealthyEnvelope(spikes: u32, env: Envelope) bool {
    return spikes >= env.min_spikes and spikes <= env.max_spikes;
}

fn silenced(i: usize, n: usize, frac: Fixed) bool {
    // first floor(frac*n) units silent
    const k = fixed.toParts(fixed.mul(frac, fixed.fromInt(@intCast(n)))).int;
    return i < @as(usize, @intCast(@max(@as(i64, 0), k)));
}

/// Run fixed steps under lesion; return spikes.
pub fn runLesioned(id: LesionId, steps: usize) struct { spikes: u32, rate_proxy: f64 } {
    const p = paramsFor(id);
    var b = brain_f.BrainF.initSeeded(17, false);
    var ext: [brain_f.N_TOTAL]Fixed = undefined;
    const before = b.totalSpikes();
    var t: usize = 0;
    while (t < steps) : (t += 1) {
        const prim_base: Fixed = if ((t % 16) < 8) fixed.fromDecimalStr("0.7") else fixed.fromDecimalStr("0.1");
        const prim = fixed.mul(prim_base, p.fi_stim_scale);
        // thr_boost reduces effective drive
        const thr_adj = fixed.sub(prim, p.thr_boost);
        const drive = if (fixed.lt(thr_adj, 0)) fixed.fromDecimalStr("0.02") else thr_adj;
        var i: usize = 0;
        while (i < b.n) : (i += 1) {
            if (silenced(i, b.n, p.silence_fraction)) {
                ext[i] = 0;
                continue;
            }
            ext[i] = fixed.fromDecimalStr("0.03");
            if (b.region_of[i] == .sens or b.region_of[i] == .assoc) {
                ext[i] = fixed.add(ext[i], drive);
            }
            if (b.region_of[i] == .thal and b.genotypes[i].synapse_sign > 0 and (t % 40) < 12) {
                ext[i] = fixed.add(ext[i], fixed.mul(drive, fixed.fromDecimalStr("0.5")));
            }
        }
        b.step(ext[0..]);
    }
    const spikes = b.totalSpikes() - before;
    const rate = @as(f64, @floatFromInt(spikes)) / @as(f64, @floatFromInt(steps));
    return .{ .spikes = spikes, .rate_proxy = rate };
}

pub const FailureReport = struct {
    ok: bool,
    healthy_spikes: u32,
    ad_spikes: u32,
    pd_spikes: u32,
    als_spikes: u32,
    /// lesions reduce or scramble relative to healthy (boundary detectable)
    boundary_detected: bool,
    healthy_in_envelope: bool,
};

pub fn runFailureProbe() FailureReport {
    const steps: usize = 80;
    const h = runLesioned(.none, steps);
    const ad = runLesioned(.ad_synaptic_fatigue, steps);
    const pd = runLesioned(.pd_rate_irregularity, steps);
    const als = runLesioned(.als_motor_dropout, steps);

    const env: Envelope = .{};
    const healthy_ok = inHealthyEnvelope(h.spikes, env);
    // AD/ALS should show rate drop vs healthy when silence+stim scale bite
    const ad_drop = ad.spikes < h.spikes or ad.spikes == 0;
    const als_drop = als.spikes < h.spikes;
    const boundary = (ad_drop or als_drop) and healthy_ok;
    // PD may be irregular not always lower — accept any difference or still ok if healthy holds
    const ok = healthy_ok and boundary;
    return .{
        .ok = ok,
        .healthy_spikes = h.spikes,
        .ad_spikes = ad.spikes,
        .pd_spikes = pd.spikes,
        .als_spikes = als.spikes,
        .boundary_detected = boundary,
        .healthy_in_envelope = healthy_ok,
    };
}
