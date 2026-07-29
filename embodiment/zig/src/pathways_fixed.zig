//! Biologically routed pathway gains — Fixed lattice (seed-lawful only).
//! Anatomical map matches docs/BIO_SENSORY_SYSTEM.md:
//!   vision/audio/hid → thal relay + sens primary (+ hipp bind for V/A)
//!   text/log         → assoc
//!   sys_metric       → thal interoception
//!   motor/speech out → efferent plant (separate organ), re-afference as audio

const fixed = @import("fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const brain_f = @import("brain_fixed.zig");
const Fixed = fixed.Fixed;

pub const Modality = enum(u8) {
    vision = 0,
    audio = 1,
    text = 2,
    sys_metric = 3,
    hid = 4,
    log = 5,
    network = 6,
    custom = 7,
    /// re-afferent copy of own speech sound (not next-token)
    speech_sound = 8,
    /// proprioceptive feedback from articulators
    motor_proprio = 9,
};

pub fn consciousnessGate() Fixed {
    // φ/(1+φ)
    return fixed.div(seeds_f.phi, fixed.add(fixed.fromInt(1), seeds_f.phi));
}

pub fn pathwayGain(role: enum { primary, relay, intero, hipp_bind, motor_eff }) Fixed {
    const g = consciousnessGate();
    return switch (role) {
        .relay => fixed.mul(fixed.div(fixed.fromInt(1), seeds_f.phi), g),
        .intero => fixed.mul(
            fixed.mul(fixed.fromDecimalStr("0.5"), fixed.add(fixed.abs(seeds_f.poof), fixed.abs(seeds_f.suction))),
            g,
        ),
        .hipp_bind => fixed.mul(g, seeds_f.psi_con),
        .primary => g,
        // efferent drive to speech plant (weaker than primary sensory)
        .motor_eff => fixed.mul(g, fixed.fromDecimalStr("0.85")),
    };
}

pub const Route = struct {
    primary: brain_f.RegionId,
    relay: ?brain_f.RegionId,
    hipp_bind: bool,
};

/// Anatomical routing (simplified neocortex + loops).
pub fn routeFor(m: Modality) Route {
    return switch (m) {
        .vision, .audio, .hid, .speech_sound => .{ .primary = .sens, .relay = .thal, .hipp_bind = true },
        .motor_proprio => .{ .primary = .sens, .relay = .thal, .hipp_bind = false },
        .text, .log, .custom => .{ .primary = .assoc, .relay = null, .hipp_bind = true },
        .sys_metric, .network => .{ .primary = .thal, .relay = null, .hipp_bind = false },
    };
}

pub fn selfTest() bool {
    const g = consciousnessGate();
    // ≈ 0.618
    if (fixed.lt(g, fixed.fromDecimalStr("0.61"))) return false;
    if (fixed.gt(g, fixed.fromDecimalStr("0.62"))) return false;
    const r = routeFor(.vision);
    if (r.primary != .sens) return false;
    if (r.relay == null or r.relay.? != .thal) return false;
    if (!r.hipp_bind) return false;
    // relay gain < primary
    if (!fixed.lt(pathwayGain(.relay), pathwayGain(.primary))) return false;
    const ri = routeFor(.sys_metric);
    if (ri.primary != .thal) return false;
    return true;
}
