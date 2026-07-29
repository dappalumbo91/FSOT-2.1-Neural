//! Self-modulation on fixed lattice — POOF/SUCTION homeostasis.
//! Replaces fsot_nuron/self_modulation.py for Zig fixed authority.
//! Gains seed-lawful (poof, suction, φ-gate); no free fits.

const fixed = @import("fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const inject_f = @import("inject_io_fixed.zig");
const Fixed = fixed.Fixed;

pub const Mode = enum(u8) {
    dampen = 0,
    balanced = 1,
    explore = 2,
};

pub const State = struct {
    load: Fixed = 0,
    stim_scale: Fixed = fixed.fromInt(1),
    syn_scale: Fixed = fixed.fromInt(1),
    poof_gain: Fixed = 0,
    suction_gain: Fixed = 0,
    dt_ms_scale: Fixed = fixed.fromInt(1),
    mode: Mode = .balanced,
};

fn clamp(x: Fixed, lo: Fixed, hi: Fixed) Fixed {
    return fixed.clamp(x, lo, hi);
}

/// φ / (1+φ) consciousness gate
fn gate() Fixed {
    return fixed.div(seeds_f.phi, fixed.add(fixed.fromInt(1), seeds_f.phi));
}

/// Map plant metrics + fire fraction → autonomic scales (Fixed).
pub fn fromMetric(metric: inject_f.MetricF, fire_frac: Fixed) State {
    // load ≈ max-ish blend of plant channels
    var load = metric.cpu;
    if (fixed.gt(metric.mem, load)) load = metric.mem;
    if (fixed.gt(metric.disk, load)) load = fixed.mul(metric.disk, fixed.fromDecimalStr("0.8"));
    // stress = max(load, cpu, mem*0.9)
    var stress = load;
    if (fixed.gt(metric.cpu, stress)) stress = metric.cpu;
    const mem09 = fixed.mul(metric.mem, fixed.fromDecimalStr("0.9"));
    if (fixed.gt(mem09, stress)) stress = mem09;

    const fire = clamp(fire_frac, 0, fixed.fromInt(1));
    const poof = seeds_f.poof;
    const suction = seeds_f.suction;
    const g = gate();

    var st: State = .{ .load = load };

    const thr_high = fixed.fromDecimalStr("0.65");
    const thr_fire = fixed.fromDecimalStr("0.35");
    const thr_low = fixed.fromDecimalStr("0.25");
    const thr_quiet = fixed.fromDecimalStr("0.08");

    if (fixed.gt(stress, thr_high) or fixed.gt(fire, thr_fire)) {
        // POOF dampen
        const excess_s = if (fixed.gt(stress, fixed.fromDecimalStr("0.5")))
            fixed.sub(stress, fixed.fromDecimalStr("0.5"))
        else
            0;
        const excess_f = if (fixed.gt(fire, fixed.fromDecimalStr("0.25")))
            fixed.sub(fire, fixed.fromDecimalStr("0.25"))
        else
            0;
        const excess = fixed.add(excess_s, excess_f);
        st.poof_gain = clamp(fixed.mul(fixed.mul(poof, fixed.fromInt(4)), excess), 0, fixed.fromInt(1));
        st.stim_scale = clamp(
            fixed.sub(fixed.fromInt(1), fixed.mul(st.poof_gain, g)),
            fixed.fromDecimalStr("0.35"),
            fixed.fromInt(1),
        );
        st.syn_scale = clamp(
            fixed.sub(fixed.fromInt(1), fixed.mul(fixed.fromDecimalStr("0.5"), st.poof_gain)),
            fixed.fromDecimalStr("0.45"),
            fixed.fromInt(1),
        );
        st.dt_ms_scale = fixed.add(fixed.fromInt(1), fixed.mul(fixed.fromDecimalStr("0.5"), st.poof_gain));
        st.mode = .dampen;
    } else if (fixed.lt(stress, thr_low) and fixed.lt(fire, thr_quiet)) {
        // SUCTION explore
        const spare = fixed.add(fixed.sub(thr_low, stress), fixed.sub(thr_quiet, fire));
        st.suction_gain = clamp(fixed.mul(fixed.mul(suction, fixed.fromInt(5)), spare), 0, fixed.fromInt(1));
        st.stim_scale = clamp(
            fixed.add(fixed.fromInt(1), fixed.mul(fixed.mul(st.suction_gain, g), fixed.fromDecimalStr("0.5"))),
            fixed.fromInt(1),
            fixed.fromDecimalStr("1.35"),
        );
        st.syn_scale = clamp(
            fixed.add(fixed.fromInt(1), fixed.mul(fixed.fromDecimalStr("0.25"), st.suction_gain)),
            fixed.fromInt(1),
            fixed.fromDecimalStr("1.2"),
        );
        st.dt_ms_scale = clamp(
            fixed.sub(fixed.fromInt(1), fixed.mul(fixed.fromDecimalStr("0.15"), st.suction_gain)),
            fixed.fromDecimalStr("0.75"),
            fixed.fromInt(1),
        );
        st.mode = .explore;
    } else {
        st.mode = .balanced;
        st.stim_scale = fixed.fromInt(1);
        st.syn_scale = fixed.fromInt(1);
    }

    // emergency mem/temp clamp
    if (fixed.gt(metric.mem, fixed.fromDecimalStr("0.92")) or fixed.gt(metric.temp, fixed.fromDecimalStr("0.85"))) {
        const em = fixed.sub(fixed.fromInt(1), poof);
        if (fixed.gt(st.stim_scale, em)) st.stim_scale = em;
        st.mode = .dampen;
    }

    return st;
}

pub fn modeName(m: Mode) []const u8 {
    return switch (m) {
        .dampen => "dampen",
        .balanced => "balanced",
        .explore => "explore",
    };
}

pub fn selfTest() bool {
    const high = inject_f.MetricF{
        .cpu = fixed.fromDecimalStr("0.9"),
        .mem = fixed.fromDecimalStr("0.85"),
        .disk = fixed.fromDecimalStr("0.5"),
        .net = fixed.fromDecimalStr("0.4"),
        .temp = fixed.fromDecimalStr("0.6"),
    };
    const d = fromMetric(high, fixed.fromDecimalStr("0.4"));
    if (d.mode != .dampen) return false;
    if (!fixed.lt(d.stim_scale, fixed.fromInt(1))) return false;

    const low = inject_f.MetricF{
        .cpu = fixed.fromDecimalStr("0.05"),
        .mem = fixed.fromDecimalStr("0.1"),
        .disk = fixed.fromDecimalStr("0.05"),
        .net = 0,
        .temp = fixed.fromDecimalStr("0.1"),
    };
    const e = fromMetric(low, fixed.fromDecimalStr("0.02"));
    if (e.mode != .explore) return false;
    if (!fixed.gt(e.stim_scale, fixed.fromInt(1))) return false;

    const mid = inject_f.MetricF{
        .cpu = fixed.fromDecimalStr("0.4"),
        .mem = fixed.fromDecimalStr("0.4"),
        .disk = fixed.fromDecimalStr("0.2"),
        .net = fixed.fromDecimalStr("0.1"),
        .temp = fixed.fromDecimalStr("0.3"),
    };
    const b = fromMetric(mid, fixed.fromDecimalStr("0.15"));
    if (b.mode != .balanced) return false;
    return true;
}

pub const ModulateReport = struct {
    ok: bool,
    dampen_ok: bool,
    explore_ok: bool,
    balanced_ok: bool,
    emergency_ok: bool,
};

pub fn runModulateProbe() ModulateReport {
    const ok_st = selfTest();
    const high = inject_f.MetricF{
        .cpu = fixed.fromDecimalStr("0.9"),
        .mem = fixed.fromDecimalStr("0.85"),
        .disk = fixed.fromDecimalStr("0.5"),
        .net = fixed.fromDecimalStr("0.4"),
        .temp = fixed.fromDecimalStr("0.6"),
    };
    const d = fromMetric(high, fixed.fromDecimalStr("0.4"));
    const low = inject_f.MetricF{
        .cpu = fixed.fromDecimalStr("0.05"),
        .mem = fixed.fromDecimalStr("0.1"),
        .disk = fixed.fromDecimalStr("0.05"),
        .net = 0,
        .temp = fixed.fromDecimalStr("0.1"),
    };
    const e = fromMetric(low, fixed.fromDecimalStr("0.02"));
    const mid = inject_f.MetricF{
        .cpu = fixed.fromDecimalStr("0.4"),
        .mem = fixed.fromDecimalStr("0.4"),
        .disk = fixed.fromDecimalStr("0.2"),
        .net = fixed.fromDecimalStr("0.1"),
        .temp = fixed.fromDecimalStr("0.3"),
    };
    const b = fromMetric(mid, fixed.fromDecimalStr("0.15"));
    const em_m = inject_f.MetricF{
        .cpu = fixed.fromDecimalStr("0.5"),
        .mem = fixed.fromDecimalStr("0.95"),
        .disk = fixed.fromDecimalStr("0.2"),
        .net = fixed.fromDecimalStr("0.1"),
        .temp = fixed.fromDecimalStr("0.9"),
    };
    const em = fromMetric(em_m, fixed.fromDecimalStr("0.1"));
    return .{
        .ok = ok_st and d.mode == .dampen and e.mode == .explore and b.mode == .balanced and em.mode == .dampen,
        .dampen_ok = d.mode == .dampen and fixed.lt(d.stim_scale, fixed.fromInt(1)),
        .explore_ok = e.mode == .explore and fixed.gt(e.stim_scale, fixed.fromInt(1)),
        .balanced_ok = b.mode == .balanced,
        .emergency_ok = em.mode == .dampen,
    };
}
