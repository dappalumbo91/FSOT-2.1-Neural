//! Host: trinary + neuron step parity dump (lines for Python harness).
const std = @import("std");
const trit = @import("trit.zig");
const scalar = @import("scalar.zig");
const neuron = @import("neuron.zig");
const network = @import("network.zig");
const fingerprint = @import("fingerprint.zig");
const seeds = @import("seeds.zig");
const frame_inject = @import("frame_inject.zig");
const metric_inject = @import("metric_inject.zig");

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

    const nst = network.networkSelfTest();
    if (!nst.ok) {
        std.debug.print("FSOT_NETWORK FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_NETWORK PASS units=16 spikes={d}\n", .{nst.spikes});

    const fp = fingerprint.fingerprintSelfTest();
    if (!fp.ok) {
        std.debug.print("FSOT_FP FAIL correct={d}/{d}\n", .{ fp.correct, fp.n });
        std.process.exit(1);
    }
    std.debug.print("FSOT_FP PASS correct={d}/{d}\n", .{ fp.correct, fp.n });

    printF64("SEEDS_K=", seeds.k);

    // MachineFrame ABI scaffold (Python machine_encode → Zig body seam)
    var demo: [22]u8 = undefined;
    @memcpy(demo[0..4], &frame_inject.magic);
    demo[4] = 1;
    demo[5] = 1; // machine path
    std.mem.writeInt(u32, demo[6..10], 4, .little);
    // one word: pack=0, n=4
    std.mem.writeInt(u64, demo[10..18], 0, .little);
    demo[18] = 4;
    demo[19] = 0;
    demo[20] = 0;
    demo[21] = 0;
    if (frame_inject.parseHeader(demo[0..])) |h| {
        std.debug.print("FSOT_FRAME path={d} n_trits={d}\n", .{ h.path_id, h.n_trits });
    } else {
        std.debug.print("FSOT_FRAME FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_FRAME PASS\n", .{});

    // Interoception MetricPacket ABI (standalone plant → body)
    if (!metric_inject.selfTest()) {
        std.debug.print("FSOT_METRIC FAIL\n", .{});
        std.process.exit(1);
    }
    std.debug.print("FSOT_METRIC PASS\n", .{});

    std.debug.print("FSOT_STAGE_ZIG_NEURON_OK\n", .{});
}
