//! Sensory / interoception bus for Zig mind.
//! Replaces fsot_nuron/sensory/packets.py + bus buildExternal (core).
//! Media *decode* stays optional host/Python; features land here as floats.

const brain = @import("brain.zig");
const pathways = @import("pathways.zig");
const seeds = @import("seeds.zig");

pub const MAX_FEAT: usize = 32;
pub const MAX_PACKETS: usize = 8;

pub const Metric = struct {
    cpu: f64 = 0,
    mem: f64 = 0,
    disk: f64 = 0,
    net: f64 = 0,
    temp: f64 = 0,

    pub fn driveScalar(self: Metric) f64 {
        var s: f64 = 0;
        const vals = [_]f64{ self.cpu, self.mem, self.disk, self.net, self.temp };
        var i: usize = 0;
        while (i < vals.len) : (i += 1) {
            var v = vals[i];
            if (v < 0) v = 0;
            if (v > 1) v = 1;
            s += v;
        }
        return s / @as(f64, @floatFromInt(vals.len));
    }
};

pub const Packet = struct {
    modality: pathways.Modality = .custom,
    n_feat: usize = 0,
    features: [MAX_FEAT]f64 = .{0} ** MAX_FEAT,
    strength: f64 = 1.0,
    timestamp_ms: u32 = 0,

    pub fn fromSlice(mod: pathways.Modality, feats: []const f64, strength: f64) Packet {
        var p: Packet = .{
            .modality = mod,
            .strength = strength,
        };
        const n = @min(feats.len, MAX_FEAT);
        p.n_feat = n;
        var i: usize = 0;
        while (i < n) : (i += 1) p.features[i] = feats[i];
        return p;
    }
};

pub const Bus = struct {
    n: usize = 0,
    packets: [MAX_PACKETS]Packet = undefined,
    metric: Metric = .{},

    pub fn clear(self: *Bus) void {
        self.n = 0;
    }

    pub fn push(self: *Bus, p: Packet) void {
        if (self.n >= MAX_PACKETS) {
            // drop oldest
            var i: usize = 0;
            while (i + 1 < MAX_PACKETS) : (i += 1) self.packets[i] = self.packets[i + 1];
            self.n = MAX_PACKETS - 1;
        }
        self.packets[self.n] = p;
        self.n += 1;
    }

    /// Build external drive for multi-region brain from queued packets + metric.
    pub fn buildExternal(self: *const Bus, b: *const brain.Brain, stim_scale: f64, out: []f64) void {
        const n = b.n;
        var i: usize = 0;
        while (i < n and i < out.len) : (i += 1) out[i] = 0.02;

        // interoception → thal
        const intero = pathways.pathwayGain(.intero) * self.metric.driveScalar() * stim_scale;
        i = 0;
        while (i < n and i < out.len) : (i += 1) {
            if (b.region_of[i] == .thal) {
                const seat: f64 = if ((i % 2) == 0) @as(f64, 1.0) else @as(f64, 0.3);
                out[i] += intero * seat;
            }
        }

        var pi: usize = 0;
        while (pi < self.n) : (pi += 1) {
            const p = self.packets[pi];
            const rt = pathways.routeFor(p.modality);
            const g_pri = pathways.pathwayGain(.primary) * p.strength * stim_scale;
            const g_rel = pathways.pathwayGain(.relay) * p.strength * stim_scale;
            injectRegion(b, rt.primary, p.features[0..p.n_feat], g_pri, out);
            if (rt.relay) |rel| {
                injectRegion(b, rel, p.features[0..p.n_feat], g_rel, out);
            }
            // episodic bind: vision/audio also light hipp
            if (p.modality == .vision or p.modality == .audio) {
                injectRegion(b, .hipp, p.features[0..p.n_feat], pathways.pathwayGain(.hipp_bind) * p.strength * stim_scale, out);
            }
        }

        // clamp
        i = 0;
        while (i < n and i < out.len) : (i += 1) {
            if (out[i] < -0.8) out[i] = -0.8;
            if (out[i] > 1.5) out[i] = 1.5;
        }
    }
};

fn injectRegion(
    b: *const brain.Brain,
    reg: brain.RegionId,
    feats: []const f64,
    scale: f64,
    out: []f64,
) void {
    if (feats.len == 0 or scale == 0) return;
    var sens_i: usize = 0;
    var i: usize = 0;
    while (i < b.n and i < out.len) : (i += 1) {
        if (b.region_of[i] != reg) continue;
        const f = feats[sens_i % feats.len];
        const seat: f64 = if ((i % 2) == 0) 1.0 else 0.28;
        out[i] += scale * f * seat;
        // slight φ geometry on odd seats
        if ((i % 2) != 0) out[i] *= (1.0 / seeds.phi + 0.5);
        sens_i += 1;
    }
}

pub fn selfTest() bool {
    var bus: Bus = .{};
    const feats = [_]f64{ 0.8, -0.3, 0.5, 0.1 };
    bus.push(Packet.fromSlice(.vision, feats[0..], 0.9));
    bus.metric = .{ .cpu = 0.2, .mem = 0.3, .disk = 0.1, .net = 0.0, .temp = 0.1 };
    var b = brain.Brain.init();
    var ext: [brain.N_TOTAL]f64 = undefined;
    bus.buildExternal(&b, 1.0, ext[0..]);
    // some units should have non-baseline drive
    var max_e: f64 = 0;
    for (ext) |e| {
        const a = if (e < 0) -e else e;
        if (a > max_e) max_e = a;
    }
    return max_e > 0.05 and bus.metric.driveScalar() > 0.1;
}
