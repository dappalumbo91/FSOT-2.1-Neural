//! Neurological failure-boundary probes on fixed lattice (expanded catalog).
//! Spirit of failure_boundaries.py — lesion modes + healthy envelope + wire-around hook.
//! Not clinical diagnosis; boundary knowledge for recovery design.

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const Fixed = fixed.Fixed;

pub const LesionId = enum(u8) {
    none = 0,
    ad_synaptic_fatigue = 1,
    pd_rate_irregularity = 2,
    als_motor_dropout = 3,
    ms_conduction_delay = 4,
    epi_runaway = 5,
    ischemia_collapse = 6,
};

pub const LesionParams = struct {
    fi_stim_scale: Fixed = fixed.fromInt(1),
    silence_fraction: Fixed = 0,
    thr_boost: Fixed = 0,
    adapt_stress: Fixed = fixed.fromInt(1),
    /// effective refractory stretch (MS): skip steps fraction as zero drive pulse
    ref_stretch: Fixed = fixed.fromInt(1),
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
        .ms_conduction_delay => .{
            .fi_stim_scale = fixed.fromDecimalStr("0.75"),
            .silence_fraction = fixed.fromDecimalStr("0.10"),
            .thr_boost = fixed.fromDecimalStr("0.08"),
            .ref_stretch = fixed.fromDecimalStr("1.85"),
        },
        .epi_runaway => .{
            .fi_stim_scale = fixed.fromDecimalStr("1.4"),
            .silence_fraction = 0,
            .thr_boost = fixed.fromDecimalStr("-0.22"),
            .adapt_stress = fixed.fromDecimalStr("0.35"),
            .ref_stretch = fixed.fromDecimalStr("0.55"),
        },
        .ischemia_collapse => .{
            .fi_stim_scale = fixed.fromDecimalStr("0.25"),
            .silence_fraction = fixed.fromDecimalStr("0.45"),
            .thr_boost = fixed.fromDecimalStr("0.25"),
            .adapt_stress = fixed.fromDecimalStr("2.5"),
        },
    };
}

pub const Envelope = struct {
    min_spikes: u32 = 1,
    max_spikes: u32 = 8000,
};

pub fn inHealthyEnvelope(spikes: u32, env: Envelope) bool {
    return spikes >= env.min_spikes and spikes <= env.max_spikes;
}

fn silenced(i: usize, n: usize, frac: Fixed) bool {
    const k = fixed.toParts(fixed.mul(frac, fixed.fromInt(@intCast(n)))).int;
    return i < @as(usize, @intCast(@max(@as(i64, 0), k)));
}

pub const LesionRun = struct { spikes: u32, rate_proxy: f64 };

pub fn runLesionedParams(p: LesionParams, steps: usize) LesionRun {
    var b = brain_f.BrainF.initSeeded(17, false);
    var ext: [brain_f.N_TOTAL]Fixed = undefined;
    const before = b.totalSpikes();
    // stretch refractory: occasionally zero whole drive (conduction block proxy)
    const stretch_i = fixed.toParts(fixed.mul(p.ref_stretch, fixed.fromInt(10))).int;
    var t: usize = 0;
    while (t < steps) : (t += 1) {
        const block = stretch_i > 12 and (t % @as(usize, @intCast(stretch_i))) < 2;
        const prim_base: Fixed = if ((t % 16) < 8) fixed.fromDecimalStr("0.7") else fixed.fromDecimalStr("0.1");
        var prim = fixed.mul(prim_base, p.fi_stim_scale);
        if (block) prim = fixed.fromDecimalStr("0.01");
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
            // PD-like: occasional extra pulse on odd units (jitter/burst proxy)
            if (fixed.gt(p.adapt_stress, fixed.fromDecimalStr("1.5")) and (i % 3 == 0) and (t % 7 == 0)) {
                ext[i] = fixed.add(ext[i], fixed.fromDecimalStr("0.15"));
            }
        }
        b.step(ext[0..]);
    }
    const spikes = b.totalSpikes() - before;
    const rate = @as(f64, @floatFromInt(spikes)) / @as(f64, @floatFromInt(steps));
    return .{ .spikes = spikes, .rate_proxy = rate };
}

pub fn runLesioned(id: LesionId, steps: usize) LesionRun {
    return runLesionedParams(paramsFor(id), steps);
}

pub const FailureReport = struct {
    ok: bool,
    healthy_spikes: u32,
    ad_spikes: u32,
    pd_spikes: u32,
    als_spikes: u32,
    ms_spikes: u32,
    epi_spikes: u32,
    ischemia_spikes: u32,
    n_modes: u32,
    boundary_detected: bool,
    healthy_in_envelope: bool,
    /// EPI should tend higher or equal drive; ischemia near silence
    catalog_shape_ok: bool,
};

pub fn runFailureProbe() FailureReport {
    const steps: usize = 80;
    const h = runLesioned(.none, steps);
    const ad = runLesioned(.ad_synaptic_fatigue, steps);
    const pd = runLesioned(.pd_rate_irregularity, steps);
    const als = runLesioned(.als_motor_dropout, steps);
    const ms = runLesioned(.ms_conduction_delay, steps);
    const epi = runLesioned(.epi_runaway, steps);
    const isch = runLesioned(.ischemia_collapse, steps);

    const env: Envelope = .{};
    const healthy_ok = inHealthyEnvelope(h.spikes, env);
    const ad_drop = ad.spikes < h.spikes;
    const als_drop = als.spikes < h.spikes;
    const isch_bad = isch.spikes < h.spikes / 2 or isch.spikes < 5;
    const boundary = (ad_drop or als_drop or isch_bad) and healthy_ok;
    // epi often higher rate; ischemia lowest-ish
    const catalog_shape = epi.spikes >= ad.spikes or isch.spikes <= als.spikes;
    const ok = healthy_ok and boundary and catalog_shape;
    return .{
        .ok = ok,
        .healthy_spikes = h.spikes,
        .ad_spikes = ad.spikes,
        .pd_spikes = pd.spikes,
        .als_spikes = als.spikes,
        .ms_spikes = ms.spikes,
        .epi_spikes = epi.spikes,
        .ischemia_spikes = isch.spikes,
        .n_modes = 6,
        .boundary_detected = boundary,
        .healthy_in_envelope = healthy_ok,
        .catalog_shape_ok = catalog_shape,
    };
}
