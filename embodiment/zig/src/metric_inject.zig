//! Host MetricPacket ABI — interoception into the bare-metal / host body.
//! Standalone: no paths, no external files. Binary layout only.
//!
//! Layout (little-endian):
//!   magic "FSMT" (4)
//!   version u8 = 1
//!   n_channels u8
//!   reserved u16 = 0
//!   channels: n × f32  (cpu, mem, disk, net, temp, …)
//!
//! Python: fsot_nuron.hardware_body.pack_metric_frame

const std = @import("std");

pub const magic = [4]u8{ 'F', 'S', 'M', 'T' };

pub const MetricHeader = struct {
    version: u8,
    n_channels: u8,
};

pub fn parseHeader(buf: []const u8) ?MetricHeader {
    if (buf.len < 8) return null;
    if (!std.mem.eql(u8, buf[0..4], &magic)) return null;
    return .{
        .version = buf[4],
        .n_channels = buf[5],
    };
}

/// Read up to max_out f32 channels; returns count or null on hard fail.
pub fn readChannels(buf: []const u8, out: []f32) ?usize {
    const h = parseHeader(buf) orelse return null;
    const n: usize = @min(@as(usize, h.n_channels), out.len);
    const need = 8 + n * 4;
    if (buf.len < need) return null;
    var i: usize = 0;
    while (i < n) : (i += 1) {
        const off = 8 + i * 4;
        const bits = std.mem.readInt(u32, buf[off..][0..4], .little);
        out[i] = @bitCast(bits);
    }
    return n;
}

/// Equal-weight drive scalar in [0,1] from first 5 channels (plant mix).
pub fn driveScalar(channels: []const f32) f64 {
    if (channels.len == 0) return 0.0;
    var s: f64 = 0.0;
    const n = @min(channels.len, 5);
    var i: usize = 0;
    while (i < n) : (i += 1) {
        var v: f64 = channels[i];
        if (v < 0.0) v = 0.0;
        if (v > 1.0) v = 1.0;
        s += v;
    }
    return s / @as(f64, @floatFromInt(n));
}

pub fn selfTest() bool {
    // Build a tiny frame: 3 channels 0.1, 0.2, 0.3
    var buf: [8 + 3 * 4]u8 = undefined;
    @memcpy(buf[0..4], &magic);
    buf[4] = 1;
    buf[5] = 3;
    buf[6] = 0;
    buf[7] = 0;
    const vals = [_]f32{ 0.1, 0.2, 0.3 };
    var i: usize = 0;
    while (i < 3) : (i += 1) {
        const bits: u32 = @bitCast(vals[i]);
        std.mem.writeInt(u32, buf[8 + i * 4 ..][0..4], bits, .little);
    }
    var out: [5]f32 = undefined;
    const n = readChannels(buf[0..], out[0..]) orelse return false;
    if (n != 3) return false;
    const d = driveScalar(out[0..n]);
    // mean = 0.2
    if (d < 0.199 or d > 0.201) return false;
    return true;
}

test "metric frame roundtrip" {
    try std.testing.expect(selfTest());
}
