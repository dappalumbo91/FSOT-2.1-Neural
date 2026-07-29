//! Short-horizon curriculum units on fixed mind — Python learn/short_horizon spirit.
//! Each unit = synthetic lesson features + 5W1H slot mask; chain encode → retrieve.

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const Fixed = fixed.Fixed;

pub const N_UNITS: usize = 4;

pub const CurriculumReport = struct {
    ok: bool,
    n_units: u32,
    encode_ok: u32,
    retrieve_correct: u32,
    top1: f64,
    spikes: u32,
};

fn unitFeats(unit: usize, out: *[8]Fixed) void {
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        const a: u32 = @intCast(unit *% 1009 + i *% 17 + 3);
        out[i] = fixed.sub(fixed.div(fixed.fromInt(@intCast(a % 200)), fixed.fromInt(100)), fixed.fromInt(1));
    }
}

/// Teach 4 curriculum units (encode store), delay, retrieve by partial cue.
pub fn runCurriculum() CurriculumReport {
    var b = brain_f.BrainF.initSeeded(7, false);
    var store: memory_f.StoreF = .{};
    store.clear();

    var ids: [N_UNITS]u32 = undefined;
    var u: usize = 0;
    while (u < N_UNITS) : (u += 1) {
        var feats: [8]Fixed = undefined;
        unitFeats(u, &feats);
        const tok = [_]u32{
            memory_f.hashToken("who"),
            memory_f.hashToken("what"),
            memory_f.hashToken("why"),
            memory_f.hashToken("where"),
            0,
            memory_f.hashToken("how_fsot"),
        };
        // who/what/why/where/how filled bits
        ids[u] = store.encode(&b, feats[0..], 0b101111, tok);
    }

    // delay noise
    var ext: [brain_f.N_TOTAL]Fixed = .{fixed.fromDecimalStr("0.05")} ** brain_f.N_TOTAL;
    var d: usize = 0;
    while (d < 12) : (d += 1) b.step(ext[0..]);

    var correct: u32 = 0;
    u = 0;
    while (u < N_UNITS) : (u += 1) {
        var feats: [8]Fixed = undefined;
        unitFeats(u, &feats);
        var sim: Fixed = 0;
        const hit = store.retrieve(&b, feats[0..], &sim);
        if (hit == ids[u]) correct += 1;
    }
    const top1 = @as(f64, @floatFromInt(correct)) / @as(f64, @floatFromInt(N_UNITS));
    return .{
        .ok = top1 >= 0.5 and store.n == N_UNITS,
        .n_units = N_UNITS,
        .encode_ok = @intCast(store.n),
        .retrieve_correct = correct,
        .top1 = top1,
        .spikes = b.totalSpikes(),
    };
}
