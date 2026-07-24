//! Host-side Zig runner for trinary self-test (no QEMU required).
//! Zig 0.15+ compatible I/O.
const std = @import("std");
const trit = @import("trit.zig");

pub fn main() !void {
    const r = trit.selfTest();
    if (r.ok) {
        std.debug.print("FSOT_TRIT PASS (host)\n", .{});
    } else {
        std.debug.print("FSOT_TRIT FAIL fails={d}\n", .{r.fails});
        std.process.exit(1);
    }
    const atg = trit.codonPrimary('A', 'T', 'G');
    std.debug.print("ATG=[{d},{d},{d}]\n", .{ atg[0], atg[1], atg[2] });
}
