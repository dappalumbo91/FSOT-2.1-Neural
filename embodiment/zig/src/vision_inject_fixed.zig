//! Multi-packet vision inject → FIXED organism + episodic bind.
//! Host text frames (or embedded DEMO) drive the lattice; no Python core.

const fixed = @import("fixed.zig");
const organism_f = @import("organism_fixed.zig");
const inject_f = @import("inject_io_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const Fixed = fixed.Fixed;

pub const VisionInjectReport = struct {
    ok: bool,
    n_packets: u32,
    n_vision: u32,
    ticks: u32,
    episodes: u32,
    spikes: u32,
    retrieve_ok: bool,
};

/// Run organism on fixed inject bus text. If `path` is null, use DEMO_TEXT.
pub fn runVisionInject(path: ?[]const u8) !VisionInjectReport {
    var bus: inject_f.BusF = .{};
    const n_pkt: usize = if (path) |p|
        try inject_f.loadFeatureFile(p, &bus)
    else
        try inject_f.parseFeatureText(inject_f.DEMO_TEXT, &bus);

    var n_vision: u32 = 0;
    var i: usize = 0;
    while (i < bus.n) : (i += 1) {
        if (bus.packets[i].modality == .vision) n_vision += 1;
    }

    var org = organism_f.OrganismF.init();
    org.encode_every = 8;
    org.steps_per_tick = 4;

    var feats: [inject_f.MAX_FEAT]Fixed = .{0} ** inject_f.MAX_FEAT;
    const nf = bus.firstVisionFeats(&feats);
    if (nf == 0 and bus.n > 0) {
        // fall back to first packet
        const p0 = bus.packets[0];
        var k: usize = 0;
        while (k < p0.n_feat) : (k += 1) feats[k] = p0.features[k];
        org.setInject(feats[0..p0.n_feat]);
    } else {
        org.setInject(feats[0..nf]);
    }

    // tick with primary inject
    var t: u32 = 0;
    while (t < 24) : (t += 1) {
        _ = org.tickOnce();
    }

    // re-inject remaining vision packets as new episodes (multi-frame spirit)
    i = 0;
    while (i < bus.n) : (i += 1) {
        if (bus.packets[i].modality != .vision) continue;
        const p = bus.packets[i];
        org.setInject(p.features[0..p.n_feat]);
        var s: u32 = 0;
        while (s < 6) : (s += 1) _ = org.tickOnce();
        // explicit encode for this frame
        const tok = [_]u32{
            memory_f.hashToken("vision"),
            memory_f.hashToken("frame"),
            0,
            0,
            0,
            memory_f.hashToken("inject"),
        };
        _ = org.store.encode(&org.brain, p.features[0..p.n_feat], 0b100011, tok);
    }

    // retrieve first vision cue
    var retrieve_ok = false;
    if (nf > 0 and org.store.n > 0) {
        var sim: Fixed = 0;
        const hit = org.store.retrieve(&org.brain, feats[0..nf], &sim);
        retrieve_ok = hit != 0;
    }

    const spikes = org.brain.totalSpikes();
    const ok = n_pkt >= 1 and spikes >= 1 and org.store.n >= 1 and retrieve_ok;
    return .{
        .ok = ok,
        .n_packets = @intCast(n_pkt),
        .n_vision = n_vision,
        .ticks = org.tick,
        .episodes = @intCast(org.store.n),
        .spikes = spikes,
        .retrieve_ok = retrieve_ok,
    };
}

pub fn selfTest() bool {
    const r = runVisionInject(null) catch return false;
    return r.ok;
}
