//! Transfer probes — retrieve without title/label cheats (fixed mind).
//! Spirit of benchmarks/transfer_test.py: cue by *feature pattern only*.

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const Fixed = fixed.Fixed;

pub const TransferReport = struct {
    ok: bool,
    n_items: u32,
    correct: u32,
    top1: f64,
    /// partial-cue correct (last third of features zeroed)
    partial_correct: u32,
    partial_top1: f64,
    spikes: u32,
};

fn makeItem(seed: u32, out: *[8]Fixed) void {
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        const a: u32 = seed *% 7919 +% @as(u32, @intCast(i)) *% 104729 +% 13;
        out[i] = fixed.sub(fixed.div(fixed.fromInt(@intCast(a % 200)), fixed.fromInt(100)), fixed.fromInt(1));
    }
}

fn partialCue(full: *const [8]Fixed, out: *[8]Fixed) void {
    // zero last third — no label/title channel
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        out[i] = if (i >= 5) 0 else full[i];
    }
}

pub fn runTransferProbe() TransferReport {
    const n_items: usize = 5;
    var b = brain_f.BrainF.initSeeded(19, false);
    var store: memory_f.StoreF = .{};
    store.clear();

    var fulls: [5][8]Fixed = undefined;
    var ids: [5]u32 = undefined;
    var i: usize = 0;
    while (i < n_items) : (i += 1) {
        makeItem(@intCast(i + 3), &fulls[i]);
        // tokens are NOT usable at retrieve — only features
        const tok = [_]u32{ 0, 0, 0, 0, 0, memory_f.hashToken("fsot") };
        ids[i] = store.encode(&b, fulls[i][0..], 0b100000, tok);
    }

    // delay
    var ext: [brain_f.N_TOTAL]Fixed = .{fixed.fromDecimalStr("0.05")} ** brain_f.N_TOTAL;
    var d: usize = 0;
    while (d < 10) : (d += 1) b.step(ext[0..]);

    var correct: u32 = 0;
    var partial_correct: u32 = 0;
    i = 0;
    while (i < n_items) : (i += 1) {
        var sim: Fixed = 0;
        const hit = store.retrieve(&b, fulls[i][0..], &sim);
        if (hit == ids[i]) correct += 1;

        var cue: [8]Fixed = undefined;
        partialCue(&fulls[i], &cue);
        var sim2: Fixed = 0;
        const hit2 = store.retrieve(&b, cue[0..], &sim2);
        if (hit2 == ids[i]) partial_correct += 1;
    }

    const top1 = @as(f64, @floatFromInt(correct)) / @as(f64, @floatFromInt(n_items));
    const ptop = @as(f64, @floatFromInt(partial_correct)) / @as(f64, @floatFromInt(n_items));
    return .{
        .ok = top1 >= 0.6 and ptop >= 0.4,
        .n_items = @intCast(n_items),
        .correct = correct,
        .top1 = top1,
        .partial_correct = partial_correct,
        .partial_top1 = ptop,
        .spikes = b.totalSpikes(),
    };
}
