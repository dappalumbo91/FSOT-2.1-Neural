//! Fixed sensory / interoception bus with biological region routing.
//! Afferents land as Fixed features; mind never next-token decodes speech.
//! Media decode stays optional host I/O.

const fixed = @import("fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const brain_f = @import("brain_fixed.zig");
const pathways_f = @import("pathways_fixed.zig");
const inject_f = @import("inject_io_fixed.zig");
const Fixed = fixed.Fixed;

pub const MAX_FEAT: usize = 8;
pub const MAX_PACKETS: usize = 8;

pub const PacketF = struct {
    modality: pathways_f.Modality = .custom,
    n_feat: usize = 0,
    features: [MAX_FEAT]Fixed = .{0} ** MAX_FEAT,
    strength: Fixed = fixed.fromInt(1),

    pub fn fromSlice(mod: pathways_f.Modality, feats: []const Fixed, strength: Fixed) PacketF {
        var p: PacketF = .{ .modality = mod, .strength = strength };
        const n = @min(feats.len, MAX_FEAT);
        p.n_feat = n;
        var i: usize = 0;
        while (i < n) : (i += 1) p.features[i] = feats[i];
        return p;
    }
};

pub const BusF = struct {
    n: usize = 0,
    packets: [MAX_PACKETS]PacketF = undefined,
    metric: inject_f.MetricF = .{},

    pub fn clear(self: *BusF) void {
        self.n = 0;
        self.metric = .{};
    }

    pub fn push(self: *BusF, p: PacketF) void {
        if (self.n >= MAX_PACKETS) {
            var i: usize = 0;
            while (i + 1 < MAX_PACKETS) : (i += 1) self.packets[i] = self.packets[i + 1];
            self.n = MAX_PACKETS - 1;
        }
        self.packets[self.n] = p;
        self.n += 1;
    }

    fn metricDrive(self: *const BusF) Fixed {
        var s: Fixed = 0;
        s = fixed.add(s, self.metric.cpu);
        s = fixed.add(s, self.metric.mem);
        s = fixed.add(s, self.metric.disk);
        s = fixed.add(s, self.metric.net);
        s = fixed.add(s, self.metric.temp);
        return fixed.div(s, fixed.fromInt(5));
    }

    /// Build external drive: anatomical routes + intero + hipp bind.
    pub fn buildExternal(self: *const BusF, b: *const brain_f.BrainF, stim_scale: Fixed, out: []Fixed) void {
        const n = b.n;
        var i: usize = 0;
        while (i < n and i < out.len) : (i += 1) out[i] = fixed.fromDecimalStr("0.02");

        // interoception → thal only
        const intero = fixed.mul(fixed.mul(pathways_f.pathwayGain(.intero), self.metricDrive()), stim_scale);
        i = 0;
        while (i < n and i < out.len) : (i += 1) {
            if (b.region_of[i] == .thal) {
                const seat: Fixed = if ((i % 2) == 0) fixed.fromInt(1) else fixed.fromDecimalStr("0.3");
                out[i] = fixed.add(out[i], fixed.mul(intero, seat));
            }
        }

        var pi: usize = 0;
        while (pi < self.n) : (pi += 1) {
            const p = self.packets[pi];
            const rt = pathways_f.routeFor(p.modality);
            const g_pri = fixed.mul(fixed.mul(pathways_f.pathwayGain(.primary), p.strength), stim_scale);
            const g_rel = fixed.mul(fixed.mul(pathways_f.pathwayGain(.relay), p.strength), stim_scale);
            injectRegion(b, rt.primary, p.features[0..p.n_feat], g_pri, out);
            if (rt.relay) |rel| {
                injectRegion(b, rel, p.features[0..p.n_feat], g_rel, out);
            }
            if (rt.hipp_bind) {
                const g_h = fixed.mul(fixed.mul(pathways_f.pathwayGain(.hipp_bind), p.strength), stim_scale);
                injectRegion(b, .hipp, p.features[0..p.n_feat], g_h, out);
            }
        }

        // clamp
        i = 0;
        while (i < n and i < out.len) : (i += 1) {
            out[i] = fixed.clamp(out[i], fixed.fromDecimalStr("-0.8"), fixed.fromDecimalStr("1.5"));
        }
    }
};

fn injectRegion(
    b: *const brain_f.BrainF,
    reg: brain_f.RegionId,
    feats: []const Fixed,
    scale: Fixed,
    out: []Fixed,
) void {
    if (feats.len == 0) return;
    if (fixed.lt(scale, fixed.fromDecimalStr("0.000000000001")) and fixed.gt(scale, fixed.fromDecimalStr("-0.000000000001"))) return;
    var sens_i: usize = 0;
    var i: usize = 0;
    while (i < b.n and i < out.len) : (i += 1) {
        if (b.region_of[i] != reg) continue;
        // Prefer excitatory seats slightly (cell-type honesty soft)
        const prefer_e = b.genotypes[i].synapse_sign > 0;
        const seat: Fixed = if (prefer_e) fixed.fromInt(1) else fixed.fromDecimalStr("0.28");
        const f = feats[sens_i % feats.len];
        var add = fixed.mul(fixed.mul(scale, f), seat);
        if (!prefer_e) {
            add = fixed.mul(add, fixed.add(fixed.div(fixed.fromInt(1), seeds_f.phi), fixed.fromDecimalStr("0.5")));
        }
        out[i] = fixed.add(out[i], add);
        sens_i += 1;
    }
}

pub fn selfTest() bool {
    if (!pathways_f.selfTest()) return false;
    var bus: BusF = .{};
    const feats = [_]Fixed{
        fixed.fromDecimalStr("0.8"),
        fixed.fromDecimalStr("-0.3"),
        fixed.fromDecimalStr("0.5"),
        fixed.fromDecimalStr("0.1"),
    };
    bus.push(PacketF.fromSlice(.vision, feats[0..], fixed.fromDecimalStr("0.9")));
    bus.metric = .{
        .cpu = fixed.fromDecimalStr("0.2"),
        .mem = fixed.fromDecimalStr("0.3"),
        .disk = fixed.fromDecimalStr("0.1"),
        .net = 0,
        .temp = fixed.fromDecimalStr("0.1"),
    };
    var b = brain_f.BrainF.initSeeded(3, false);
    var ext: [brain_f.N_TOTAL]Fixed = undefined;
    bus.buildExternal(&b, fixed.fromInt(1), ext[0..]);
    // some drive non-zero on sens
    var any: bool = false;
    var i: usize = 0;
    while (i < b.n) : (i += 1) {
        if (b.region_of[i] == .sens and fixed.gt(ext[i], fixed.fromDecimalStr("0.05"))) any = true;
    }
    return any;
}
