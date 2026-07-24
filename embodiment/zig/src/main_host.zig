//! Host: trinary + neuron step parity dump (lines for Python harness).
const std = @import("std");
const trit = @import("trit.zig");
const scalar = @import("scalar.zig");
const neuron = @import("neuron.zig");
const seeds = @import("seeds.zig");

fn printF64(label: []const u8, x: f64) void {
    // Zig 0.15: scientific via {e}
    std.debug.print("{s}{e}\n", .{ label, x });
}

pub fn main() !void {
    const tr = trit.selfTest();
    if (!tr.ok) {
        std.debug.print("FSOT_TRIT FAIL fails={d}\n", .{tr.fails});
        std.process.exit(1);
    }
    std.debug.print("FSOT_TRIT PASS\n", .{});

    const s0 = scalar.computeNeuro(0.1, 0.0, 1.0);
    printF64("SCALAR_NEURO_DPI0.1=", s0);

    var S: [200]f64 = undefined;
    var fired: [200]u8 = undefined;
    var tern: [200]i8 = undefined;
    neuron.runParityTrace(S[0..], fired[0..], tern[0..]);

    var spikes: u32 = 0;
    for (fired) |f| {
        if (f != 0) spikes += 1;
    }
    std.debug.print("NEURON_SPIKES={d}\n", .{spikes});
    printF64("NEURON_LAST_S=", S[199]);
    printF64("NEURON_S0=", S[0]);
    printF64("NEURON_S19=", S[19]);
    printF64("NEURON_S80=", S[80]);

    std.debug.print("TRACE_BEGIN\n", .{});
    var t: usize = 0;
    while (t < 200) : (t += 1) {
        std.debug.print("{d},{e},{d},{d}\n", .{ t, S[t], fired[t], tern[t] });
    }
    std.debug.print("TRACE_END\n", .{});

    const pst = neuron.paritySelfTest();
    if (!pst.ok) {
        std.debug.print("FSOT_NEURON FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_NEURON PASS spikes={d}\n", .{pst.spikes});
    printF64("SEEDS_K=", seeds.k);
    std.debug.print("FSOT_STAGE_ZIG_NEURON_OK\n", .{});
}
