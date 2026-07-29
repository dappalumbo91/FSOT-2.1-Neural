//! Short-horizon curriculum units on fixed mind (expanded chain).
//! Domain-tagged lessons, progressive difficulty, partial-cue retrieve.

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const teach_f = @import("teach_fixed.zig");
const Fixed = fixed.Fixed;

pub const N_UNITS: usize = 8;

pub const CurriculumReport = struct {
    ok: bool,
    n_units: u32,
    encode_ok: u32,
    retrieve_correct: u32,
    partial_correct: u32,
    top1: f64,
    partial_top1: f64,
    spikes: u32,
};

fn unitFeats(unit: usize, out: *[8]Fixed) void {
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        const a: u32 = @intCast(unit *% 1009 + i *% 17 + 3);
        out[i] = fixed.sub(fixed.div(fixed.fromInt(@intCast(a % 200)), fixed.fromInt(100)), fixed.fromInt(1));
    }
}

fn partialCue(full: *const [8]Fixed, out: *[8]Fixed) void {
    // zero only last 2 dims — partial pattern, not title channel
    var i: usize = 0;
    while (i < 8) : (i += 1) out[i] = if (i >= 6) 0 else full[i];
}

pub fn runCurriculum() CurriculumReport {
    var b = brain_f.BrainF.initSeeded(7, false);
    var store: memory_f.StoreF = .{};
    store.clear();

    const domains = [_]teach_f.Domain{ .physics_fsot, .biology, .narrative, .learning, .media, .generic, .physics_fsot, .biology };
    var fulls: [N_UNITS][8]Fixed = undefined;
    var ids: [N_UNITS]u32 = undefined;
    var u: usize = 0;
    while (u < N_UNITS) : (u += 1) {
        unitFeats(u, &fulls[u]);
        const card = teach_f.buildLesson(
            domains[u],
            "agent",
            "lesson",
            "locus",
            "fsot",
            "curr",
            true,
        );
        ids[u] = store.encode(&b, fulls[u][0..], card.slot_mask, card.tokens);
    }

    var ext: [brain_f.N_TOTAL]Fixed = .{fixed.fromDecimalStr("0.05")} ** brain_f.N_TOTAL;
    var d: usize = 0;
    while (d < 16) : (d += 1) b.step(ext[0..]);

    var correct: u32 = 0;
    var partial: u32 = 0;
    u = 0;
    while (u < N_UNITS) : (u += 1) {
        var sim: Fixed = 0;
        if (store.retrieve(&b, fulls[u][0..], &sim) == ids[u]) correct += 1;
        var cue: [8]Fixed = undefined;
        partialCue(&fulls[u], &cue);
        var sim2: Fixed = 0;
        if (store.retrieve(&b, cue[0..], &sim2) == ids[u]) partial += 1;
    }
    const top1 = @as(f64, @floatFromInt(correct)) / @as(f64, @floatFromInt(N_UNITS));
    const ptop = @as(f64, @floatFromInt(partial)) / @as(f64, @floatFromInt(N_UNITS));
    return .{
        .ok = top1 >= 0.6 and ptop >= 0.35 and store.n == N_UNITS,
        .n_units = N_UNITS,
        .encode_ok = @intCast(store.n),
        .retrieve_correct = correct,
        .partial_correct = partial,
        .top1 = top1,
        .partial_top1 = ptop,
        .spikes = b.totalSpikes(),
    };
}
