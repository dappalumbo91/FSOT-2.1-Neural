//! Host feature inject ABI — read float feature frames into sensory bus.
//! Format (text, one frame per line):
//!   modality strength f0 f1 f2 ...
//! modality: vision|audio|text|sys_metric|hid|log|network|custom
//!
//! Optional Metric line:
//!   metric cpu mem disk net temp
//!
//! Python media decode can write this file; Zig owns the mind step.

const std = @import("std");
const sensory = @import("sensory.zig");
const pathways = @import("pathways.zig");

fn parseModality(s: []const u8) ?pathways.Modality {
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

/// Load all frames from path into bus (clears bus first). Returns packet count.
pub fn loadFeatureFile(path: []const u8, bus: *sensory.Bus) !usize {
    const file = try std.fs.cwd().openFile(path, .{});
    defer file.close();
    var buf: [128 * 1024]u8 = undefined;
    const nread = try file.readAll(&buf);
    return parseFeatureText(buf[0..nread], bus);
}

pub fn parseFeatureText(text: []const u8, bus: *sensory.Bus) !usize {
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
            var vals: [5]f64 = .{0} ** 5;
            var k: usize = 0;
            while (parts.next()) |tok| {
                if (k >= 5) break;
                vals[k] = try std.fmt.parseFloat(f64, tok);
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
        const strength = try std.fmt.parseFloat(f64, strength_s);
        var feats: [sensory.MAX_FEAT]f64 = undefined;
        var nf: usize = 0;
        while (parts.next()) |tok| {
            if (nf >= sensory.MAX_FEAT) break;
            feats[nf] = try std.fmt.parseFloat(f64, tok);
            nf += 1;
        }
        if (nf == 0) continue;
        bus.push(sensory.Packet.fromSlice(mod, feats[0..nf], strength));
        n_pkt += 1;
    }
    return n_pkt;
}

pub fn selfTest() bool {
    const sample =
        \\# demo inject
        \\metric 0.2 0.3 0.1 0.05 0.15
        \\vision 0.85 0.9 -0.4 0.6 0.1
        \\text 0.7 0.2 0.3 -0.1 0.5 0.0
    ;
    var bus: sensory.Bus = .{};
    const n = parseFeatureText(sample, &bus) catch return false;
    if (n != 2) return false;
    if (bus.metric.cpu < 0.19 or bus.metric.cpu > 0.21) return false;
    if (bus.n != 2) return false;
    return true;
}
