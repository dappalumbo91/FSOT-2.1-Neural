//! Wire-around policy on fixed lattice — recovery after lesions.
//! Spirit of wire_around_policy.py: signature hits → actions → stim rescue.

const fixed = @import("fixed.zig");
const failure_f = @import("failure_fixed.zig");
const Fixed = fixed.Fixed;

pub const Signature = enum(u8) {
    rate_drop = 0,
    rate_runaway = 1,
    global_silence = 2,
    population_sparsity = 3,
    isi_cv_high = 4,
    adaptation_runaway = 5,
};

pub const Action = enum(u8) {
    boost_fi_stim = 0,
    raise_fire_thr = 1, // lower stim slightly on survivors (clamp)
    lower_silence = 2, // recruit: treat fewer units as dead
    desync_noise = 3,
    checkpoint_none = 4, // placeholder honesty
};

pub const WirePlan = struct {
    n_actions: u32 = 0,
    actions: [4]Action = .{.boost_fi_stim} ** 4,
    stim_boost: Fixed = fixed.fromInt(1),
    silence_scale: Fixed = fixed.fromInt(1), // multiply lesion silence
    thr_delta: Fixed = 0,
};

pub fn detectSignatures(healthy_spikes: u32, lesion_spikes: u32) struct { n: u32, hits: [4]Signature } {
    var hits: [4]Signature = undefined;
    var n: u32 = 0;
    if (lesion_spikes == 0 and healthy_spikes > 0) {
        hits[n] = .global_silence;
        n += 1;
    } else if (lesion_spikes * 2 < healthy_spikes) {
        hits[n] = .rate_drop;
        n += 1;
        if (lesion_spikes * 4 < healthy_spikes) {
            hits[n] = .population_sparsity;
            n += 1;
        }
    } else if (lesion_spikes > healthy_spikes + healthy_spikes / 3) {
        hits[n] = .rate_runaway;
        n += 1;
    }
    if (n == 0 and lesion_spikes < healthy_spikes) {
        hits[n] = .rate_drop;
        n += 1;
    }
    return .{ .n = n, .hits = hits };
}

pub fn planFromSignatures(hits: []const Signature) WirePlan {
    var plan: WirePlan = .{};
    var i: usize = 0;
    while (i < hits.len and plan.n_actions < 4) : (i += 1) {
        switch (hits[i]) {
            .rate_drop, .population_sparsity, .global_silence, .adaptation_runaway => {
                plan.actions[plan.n_actions] = .boost_fi_stim;
                plan.n_actions += 1;
                plan.stim_boost = fixed.fromDecimalStr("1.45");
                plan.silence_scale = fixed.fromDecimalStr("0.55"); // recruit survivors
                if (plan.n_actions < 4) {
                    plan.actions[plan.n_actions] = .lower_silence;
                    plan.n_actions += 1;
                }
            },
            .rate_runaway => {
                plan.actions[plan.n_actions] = .raise_fire_thr;
                plan.n_actions += 1;
                plan.stim_boost = fixed.fromDecimalStr("0.7");
                plan.thr_delta = fixed.fromDecimalStr("0.1");
            },
            .isi_cv_high => {
                plan.actions[plan.n_actions] = .desync_noise;
                plan.n_actions += 1;
                plan.stim_boost = fixed.fromDecimalStr("1.05");
            },
        }
    }
    if (plan.n_actions == 0) {
        plan.actions[0] = .boost_fi_stim;
        plan.n_actions = 1;
        plan.stim_boost = fixed.fromDecimalStr("1.2");
    }
    return plan;
}

/// Apply wire-around by modifying lesion params.
pub fn applyPlan(base: failure_f.LesionParams, plan: WirePlan) failure_f.LesionParams {
    var p = base;
    p.fi_stim_scale = fixed.mul(p.fi_stim_scale, plan.stim_boost);
    p.silence_fraction = fixed.mul(p.silence_fraction, plan.silence_scale);
    p.thr_boost = fixed.add(p.thr_boost, plan.thr_delta);
    return p;
}

pub const WireReport = struct {
    ok: bool,
    lesion_spikes: u32,
    rescued_spikes: u32,
    improved: bool,
    n_actions: u32,
    healthy_spikes: u32,
};

pub fn runWireAroundProbe() WireReport {
    const steps: usize = 80;
    const healthy = failure_f.runLesioned(.none, steps);
    const lesioned = failure_f.runLesioned(.ad_synaptic_fatigue, steps);
    const sig = detectSignatures(healthy.spikes, lesioned.spikes);
    const plan = planFromSignatures(sig.hits[0..sig.n]);
    const rescued_p = applyPlan(failure_f.paramsFor(.ad_synaptic_fatigue), plan);
    const rescued = failure_f.runLesionedParams(rescued_p, steps);
    const improved = rescued.spikes > lesioned.spikes;
    // success: rescue moves toward healthy or at least improves over lesion
    const ok = improved and healthy.spikes >= 1;
    return .{
        .ok = ok,
        .lesion_spikes = lesioned.spikes,
        .rescued_spikes = rescued.spikes,
        .improved = improved,
        .n_actions = plan.n_actions,
        .healthy_spikes = healthy.spikes,
    };
}
