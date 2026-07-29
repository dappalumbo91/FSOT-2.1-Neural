//! Fixed-point feature inject ABI — host text frames → Fixed lattice.
//! Same line format as inject_io.zig, but decimals land as Fixed (no f64 core).
//! Python media decode may still *write* the file; Zig owns mind steps.

const std = @import("std");
const fixed = @import("fixed.zig");
const Fixed = fixed.Fixed;

pub const MAX_FEAT: usize = 8;
pub const MAX_PKTS: usize = 16;

pub const ModalityF = enum(u8) {
    vision = 0,
    audio = 1,
    text = 2,
    sys_metric = 3,
    hid = 4,
    log = 5,
    network = 6,
    custom = 7,
};

pub const PacketF = struct {
    modality: ModalityF = .vision,
    strength: Fixed = 0,
    n_feat: usize = 0,
    features: [MAX_FEAT]Fixed = .{0} ** MAX_FEAT,
};

pub const MetricF = struct {
    cpu: Fixed = 0,
    mem: Fixed = 0,
    disk: Fixed = 0,
    net: Fixed = 0,
    temp: Fixed = 0,
};

pub const BusF = struct {
    packets: [MAX_PKTS]PacketF = undefined,
    n: usize = 0,
    metric: MetricF = .{},

    pub fn clear(self: *BusF) void {
        self.n = 0;
        self.metric = .{};
    }

    pub fn push(self: *BusF, p: PacketF) void {
        if (self.n >= MAX_PKTS) return;
        self.packets[self.n] = p;
        self.n += 1;
    }

    /// First vision packet features (or first packet) into fixed inject buffer.
    pub fn firstVisionFeats(self: *const BusF, out: *[MAX_FEAT]Fixed) usize {
        var i: usize = 0;
        while (i < self.n) : (i += 1) {
            if (self.packets[i].modality == .vision) {
                const nf = self.packets[i].n_feat;
                var k: usize = 0;
                while (k < nf) : (k += 1) out[k] = self.packets[i].features[k];
                return nf;
            }
        }
        if (self.n == 0) return 0;
        const nf = self.packets[0].n_feat;
        var k: usize = 0;
        while (k < nf) : (k += 1) out[k] = self.packets[0].features[k];
        return nf;
    }
};

fn parseModality(s: []const u8) ?ModalityF {
    if (std.mem.eql(u8, s, "vision")) return .vision;
    if (std.mem.eql(u8, s, "audio")) return .audio;
    if (std.mem.eql(u8, s, "text")) return .text;
    if (std.mem.eql(u8, s, "sys_metric")) return .sys_metric;
    if (std.mem.eql(u8, s, "hid")) return .hid;
    if (std.mem.eql(u8, s, "log")) return .log;
    if (std.mem.eql(u8, s, "network")) return .network;
    if (std.mem.eql(u8, s, "custom")) return .custom;
    return null;
}

fn parseFixedTok(s: []const u8) Fixed {
    // fromDecimalStr handles optional leading '-' and '.'
    return fixed.fromDecimalStr(s);
}

pub fn parseFeatureText(text: []const u8, bus: *BusF) !usize {
    bus.clear();
    var n_pkt: usize = 0;
    var it = std.mem.splitScalar(u8, text, '\n');
    while (it.next()) |raw| {
        var line = raw;
        if (std.mem.indexOfScalar(u8, line, '\r')) |r| line = line[0..r];
        if (std.mem.indexOfScalar(u8, line, '#')) |c| line = line[0..c];
        line = std.mem.trim(u8, line, " \t");
        if (line.len == 0) continue;

        var parts = std.mem.tokenizeAny(u8, line, " \t");
        const head = parts.next() orelse continue;
        if (std.mem.eql(u8, head, "metric")) {
            var vals: [5]Fixed = .{0} ** 5;
            var k: usize = 0;
            while (parts.next()) |tok| {
                if (k >= 5) break;
                vals[k] = parseFixedTok(tok);
                k += 1;
            }
            bus.metric = .{
                .cpu = vals[0],
                .mem = vals[1],
                .disk = vals[2],
                .net = vals[3],
                .temp = vals[4],
            };
            continue;
        }
        const mod = parseModality(head) orelse continue;
        const strength_s = parts.next() orelse continue;
        const strength = parseFixedTok(strength_s);
        var p: PacketF = .{
            .modality = mod,
            .strength = strength,
        };
        while (parts.next()) |tok| {
            if (p.n_feat >= MAX_FEAT) break;
            p.features[p.n_feat] = parseFixedTok(tok);
            p.n_feat += 1;
        }
        if (p.n_feat == 0) continue;
        bus.push(p);
        n_pkt += 1;
    }
    return n_pkt;
}

pub fn loadFeatureFile(path: []const u8, bus: *BusF) !usize {
    const file = try std.fs.cwd().openFile(path, .{});
    defer file.close();
    var buf: [128 * 1024]u8 = undefined;
    const nread = try file.readAll(&buf);
    return parseFeatureText(buf[0..nread], bus);
}

/// Embedded demo frames — host gate needs no Desktop path / external file.
pub const DEMO_TEXT =
    \\# Feature inject for Zig fixed mind
    \\metric 0.22 0.28 0.12 0.08 0.18
    \\vision 0.85 0.91 -0.42 0.63 0.12 -0.18 0.55 0.20
    \\text 0.70 0.15 0.40 -0.25 0.80 0.05 0.10 -0.05
    \\audio 0.60 0.33 -0.11 0.44 0.02 0.20 -0.30 0.15
;

pub fn selfTest() bool {
    var bus: BusF = .{};
    const n = parseFeatureText(DEMO_TEXT, &bus) catch return false;
    if (n < 3) return false;
    if (bus.n < 3) return false;
    // metric cpu ≈ 0.22
    if (fixed.lt(bus.metric.cpu, fixed.fromDecimalStr("0.20"))) return false;
    if (fixed.gt(bus.metric.cpu, fixed.fromDecimalStr("0.24"))) return false;
    var feats: [MAX_FEAT]Fixed = .{0} ** MAX_FEAT;
    const nf = bus.firstVisionFeats(&feats);
    if (nf < 4) return false;
    // first vision feature ≈ 0.91
    if (fixed.lt(feats[0], fixed.fromDecimalStr("0.85"))) return false;
    return true;
}
