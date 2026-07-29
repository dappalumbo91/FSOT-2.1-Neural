//! Host-only: load Allen-mapped unit params from a simple text file.
//! Written by scripts/stress_zig_mind.py — not used on freestanding kernel.

const std = @import("std");
const bio_probe = @import("bio_probe.zig");

/// Format (whitespace-separated lines; # comments):
///   first non-comment line: n
///   then n lines: d_eff fire_thr ref_steps adapt_gain adapt_decay adapt_step fi_stim
pub fn loadFromPath(path: []const u8, out: []bio_probe.UnitParams) !usize {
    const file = try std.fs.cwd().openFile(path, .{});
    defer file.close();
    var buf: [64 * 1024]u8 = undefined;
    const nread = try file.readAll(&buf);
    return parse(buf[0..nread], out);
}

pub fn parse(text: []const u8, out: []bio_probe.UnitParams) !usize {
    var n_target: ?usize = null;
    var filled: usize = 0;
    var it = std.mem.splitScalar(u8, text, '\n');
    while (it.next()) |raw| {
        var line = raw;
        if (std.mem.indexOfScalar(u8, line, '\r')) |r| line = line[0..r];
        // strip comment
        if (std.mem.indexOfScalar(u8, line, '#')) |c| line = line[0..c];
        line = std.mem.trim(u8, line, " \t");
        if (line.len == 0) continue;
        if (n_target == null) {
            n_target = try std.fmt.parseInt(usize, line, 10);
            continue;
        }
        if (filled >= out.len) break;
        if (filled >= n_target.?) break;
        var parts = std.mem.tokenizeAny(u8, line, " \t");
        var vals: [7]f64 = undefined;
        var k: usize = 0;
        while (parts.next()) |tok| {
            if (k >= 7) break;
            vals[k] = try std.fmt.parseFloat(f64, tok);
            k += 1;
        }
        if (k < 7) return error.BadLine;
        out[filled] = .{
            .d_eff = vals[0],
            .fire_thr = vals[1],
            .ref_steps = @intFromFloat(vals[2]),
            .adapt_gain = vals[3],
            .adapt_decay = vals[4],
            .adapt_step = vals[5],
            .fi_stim = vals[6],
        };
        filled += 1;
    }
    return filled;
}
