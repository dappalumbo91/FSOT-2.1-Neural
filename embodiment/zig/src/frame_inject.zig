//! MachineFrame inject scaffold (host-side).
//! Matches Python fsot_nuron.machine_encode.MachineFrame:
//!   magic "FSOT" | version u8 | path_id u8 | n_trits u32 LE
//!   word records: pack u64 LE | n_trits u8 | pad 3
//!
//! Python lab builds frames; Zig body consumes them for sensory drive.
//! Full multi-region brain still Python — this is the ABI seam.

const std = @import("std");
const trit = @import("trit.zig");

pub const magic = [4]u8{ 'F', 'S', 'O', 'T' };

pub const FrameHeader = struct {
    version: u8,
    path_id: u8,
    n_trits: u32,
};

pub const WordRec = struct {
    pack: u64,
    n: u8,
};

pub fn parseHeader(buf: []const u8) ?FrameHeader {
    if (buf.len < 10) return null;
    if (!std.mem.eql(u8, buf[0..4], &magic)) return null;
    const version = buf[4];
    const path_id = buf[5];
    const n_trits = std.mem.readInt(u32, buf[6..10], .little);
    return .{ .version = version, .path_id = path_id, .n_trits = n_trits };
}

pub fn firstWord(buf: []const u8) ?WordRec {
    if (buf.len < 22) return null; // 10 header + 12 word
    const pack = std.mem.readInt(u64, buf[10..18], .little);
    const n = buf[18];
    return .{ .pack = pack, .n = n };
}

/// Expand first word into trits for drive inject (max 32).
pub fn firstWordTrits(buf: []const u8, out: *[32]trit.Trit) ?u8 {
    const w = firstWord(buf) orelse return null;
    const n: u8 = @min(w.n, 32);
    var i: u8 = 0;
    while (i < n) : (i += 1) {
        const bits: u8 = @truncate(w.pack >> @intCast(2 * i));
        out[i] = trit.unpackT1(bits) orelse 0;
    }
    return n;
}

test "header parse empty body" {
    var buf: [10]u8 = undefined;
    @memcpy(buf[0..4], &magic);
    buf[4] = 1;
    buf[5] = 1; // machine
    std.mem.writeInt(u32, buf[6..10], 32, .little);
    const h = parseHeader(&buf).?;
    try std.testing.expect(h.n_trits == 32);
    try std.testing.expect(h.path_id == 1);
}
