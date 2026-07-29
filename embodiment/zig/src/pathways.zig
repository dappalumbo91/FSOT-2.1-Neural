//! Biologically routed sensory pathway gains — seed-lawful only.
//! Replaces fsot_nuron/sensory/bio_pathways.py for bare-metal mind.

const seeds = @import("seeds.zig");
const brain = @import("brain.zig");

pub const Modality = enum(u8) {
    vision = 0,
    audio = 1,
    text = 2,
    sys_metric = 3,
    hid = 4,
    log = 5,
    network = 6,
    custom = 7,
};

/// Consciousness gate φ/(1+φ) — not free.
pub fn consciousnessGate() f64 {
    return seeds.phi / (1.0 + seeds.phi);
}

/// Seed-derived pathway gain by role.
pub fn pathwayGain(role: enum { primary, relay, intero, hipp_bind }) f64 {
    const g = consciousnessGate();
    return switch (role) {
        .relay => (1.0 / seeds.phi) * g,
        .intero => 0.5 * (@abs(seeds.poof) + @abs(seeds.suction)) * g,
        .hipp_bind => g * seeds.psi_con,
        .primary => g,
    };
}

pub const Route = struct {
    primary: brain.RegionId,
    relay: ?brain.RegionId,
};

/// Anatomical routing table (simplified neocortex + loops).
pub fn routeFor(m: Modality) Route {
    return switch (m) {
        .vision, .audio, .hid => .{ .primary = .sens, .relay = .thal },
        .text, .log, .custom => .{ .primary = .assoc, .relay = null },
        .sys_metric, .network => .{ .primary = .thal, .relay = null },
    };
}

pub fn selfTest() bool {
    const g = consciousnessGate();
    // φ/(1+φ) ≈ 0.618
    if (g < 0.61 or g > 0.62) return false;
    if (pathwayGain(.primary) != g) return false;
    const r = routeFor(.vision);
    if (r.primary != .sens) return false;
    if (r.relay == null or r.relay.? != .thal) return false;
    return true;
}
