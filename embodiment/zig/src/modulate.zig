//! Self-modulation — POOF/SUCTION homeostasis (seed-lawful).
//! Replaces fsot_nuron/self_modulation.py core policy for Zig mind.

const seeds = @import("seeds.zig");
const sensory = @import("sensory.zig");
const pathways = @import("pathways.zig");

pub const Mode = enum(u8) {
    dampen = 0,
    balanced = 1,
    explore = 2,
};

pub const State = struct {
    load: f64 = 0,
    stim_scale: f64 = 1.0,
    syn_scale: f64 = 1.0,
    poof_gain: f64 = 0,
    suction_gain: f64 = 0,
    dt_ms_scale: f64 = 1.0,
    mode: Mode = .balanced,
};

fn clamp(x: f64, lo: f64, hi: f64) f64 {
    if (x < lo) return lo;
    if (x > hi) return hi;
    return x;
}

/// Map plant metrics + own fire fraction → autonomic scales.
pub fn fromMetrics(metric: sensory.Metric, fire_frac: f64) State {
    const load = metric.driveScalar();
    const stress = @max(load, @max(metric.cpu, metric.mem * 0.9));
    const fire = clamp(fire_frac, 0, 1);
    const poof = seeds.poof;
    const suction = seeds.suction;
    const gate = pathways.consciousnessGate();

    var st: State = .{ .load = load };

    if (stress > 0.65 or fire > 0.35) {
        const excess = @max(0.0, stress - 0.5) + @max(0.0, fire - 0.25);
        st.poof_gain = @min(1.0, poof * 4.0 * excess);
        st.stim_scale = @max(0.35, 1.0 - st.poof_gain * gate);
        st.syn_scale = @max(0.45, 1.0 - 0.5 * st.poof_gain);
        st.dt_ms_scale = 1.0 + 0.5 * st.poof_gain;
        st.mode = .dampen;
    } else if (stress < 0.25 and fire < 0.08) {
        st.suction_gain = @min(1.0, suction * 3.0 * (0.3 - stress + 0.05));
        st.stim_scale = @min(1.25, 1.0 + st.suction_gain * gate * 0.5);
        st.syn_scale = @min(1.15, 1.0 + 0.2 * st.suction_gain);
        st.mode = .explore;
    } else {
        st.mode = .balanced;
        st.stim_scale = 1.0;
        st.syn_scale = 1.0;
    }
    return st;
}

pub fn selfTest() bool {
    const high = sensory.Metric{ .cpu = 0.9, .mem = 0.85, .disk = 0.5, .net = 0.4, .temp = 0.6 };
    const d = fromMetrics(high, 0.4);
    if (d.mode != .dampen) return false;
    if (d.stim_scale >= 1.0) return false;

    const low = sensory.Metric{ .cpu = 0.05, .mem = 0.1, .disk = 0.05, .net = 0.0, .temp = 0.1 };
    const e = fromMetrics(low, 0.02);
    if (e.mode != .explore) return false;
    if (e.stim_scale < 1.0) return false;
    return true;
}
