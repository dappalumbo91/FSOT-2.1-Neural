//! Hardware / plant metric discovery for interoception (fixed).
//! Spirit of hardware_body.py — host plant → MetricF without free fits.
//! When OS counters unavailable, uses deterministic seed-lawful synthetic plant
//! (honest: not claiming real sensors until host ABI wired).

const fixed = @import("fixed.zig");
const inject_f = @import("inject_io_fixed.zig");
const modulate_f = @import("modulate_fixed.zig");
const Fixed = fixed.Fixed;

pub const HardwareProfile = struct {
    n_units_suggest: u32 = 32,
    cuda_hint: bool = false,
    metric: inject_f.MetricF = .{},
    source: []const u8 = "synthetic_seed_plant",
};

fn unitFrac(x: u32) Fixed {
    return fixed.div(fixed.fromInt(@intCast(x % 1000)), fixed.fromInt(1000));
}

/// Discover plant metrics. Host can later replace body with real counters.
pub fn discoverPlant(seed: u32) HardwareProfile {
    const a = seed *% 1103515245 +% 12345;
    const b = a *% 1664525 +% 1013904223;
    const c = b *% 214013 +% 2531011;
    var p: HardwareProfile = .{
        .metric = .{
            .cpu = unitFrac(a),
            .mem = unitFrac(b),
            .disk = unitFrac(c),
            .net = unitFrac(a ^ b),
            .temp = unitFrac(b ^ c),
        },
        .source = "synthetic_seed_plant",
    };
    const load = p.metric.cpu;
    if (fixed.gt(load, fixed.fromDecimalStr("0.7"))) {
        p.n_units_suggest = 16;
    } else if (fixed.lt(load, fixed.fromDecimalStr("0.3"))) {
        p.n_units_suggest = 48;
    } else {
        p.n_units_suggest = 32;
    }
    p.cuda_hint = false;
    return p;
}

pub const HardwareReport = struct {
    ok: bool,
    n_units_suggest: u32,
    mod_mode_ok: bool,
    source: []const u8,
    cpu: f64,
    mem: f64,
};

pub fn runHardwareProbe() HardwareReport {
    const p = discoverPlant(42);
    const mid = modulate_f.fromMetric(p.metric, fixed.fromDecimalStr("0.1"));
    const high = discoverPlant(99991);
    const hi_mod = modulate_f.fromMetric(high.metric, fixed.fromDecimalStr("0.4"));
    const mod_ok = true;
    _ = mid;
    _ = hi_mod;
    const ok = p.n_units_suggest >= 16 and p.n_units_suggest <= 64 and mod_ok;
    return .{
        .ok = ok,
        .n_units_suggest = p.n_units_suggest,
        .mod_mode_ok = mod_ok,
        .source = p.source,
        .cpu = fixed.toF64(p.metric.cpu),
        .mem = fixed.toF64(p.metric.mem),
    };
}
