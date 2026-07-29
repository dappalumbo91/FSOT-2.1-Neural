//! Short-horizon learning on fixed lattice.
//! Spirit of learn/short_horizon.py: quick encode → immediate recall (no long training).
//! Media/docs stay optional host I/O; mind steps are Zig Fixed only.

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const teach_f = @import("teach_fixed.zig");
const curiosity_f = @import("curiosity_fixed.zig");
const bands_f = @import("bands_fixed.zig");
const Fixed = fixed.Fixed;

pub const ShortHorizonReport = struct {
    ok: bool,
    n_lessons: u32,
    n_memory: u32,
    recall_top1: f64,
    recall_correct: u32,
    curiosity_resolved: u32,
    sme_ok: bool,
    spikes: u32,
};

fn lessonFeatures(seed: u32, out: *[8]Fixed) void {
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        const base_u: u32 = seed *% 43 +% @as(u32, @intCast(i)) *% 19 +% 11;
        const a: i64 = @intCast(base_u % 181);
        out[i] = fixed.sub(fixed.div(fixed.fromInt(a), fixed.fromInt(90)), fixed.fromInt(1));
    }
}

pub fn runShortHorizonProbe() ShortHorizonReport {
    var b = brain_f.BrainF.initSeeded(29, false);
    var store: memory_f.StoreF = .{};
    store.clear();

    // Quick multi-domain teach cards (minutes-scale spirit → few encodes)
    const domains = [_]teach_f.Domain{ .physics_fsot, .biology, .narrative, .learning, .media };
    const who = [_][]const u8{ "agent", "pyr", "neo", "learner", "viewer" };
    const what = [_][]const u8{ "scalar", "ei", "choice", "probe", "frame" };
    const n_lessons: usize = 5;

    var fulls: [5][8]Fixed = undefined;
    var who_tok: [5]u32 = undefined;
    var ids: [5]u32 = undefined;

    var i: usize = 0;
    while (i < n_lessons) : (i += 1) {
        const card = teach_f.buildLesson(
            domains[i],
            who[i],
            what[i],
            "host",
            "fixed",
            "sh_lesson",
            i != 2, // leave one why empty for curiosity
        );
        lessonFeatures(@intCast(i * 17 + 3), &fulls[i]);
        who_tok[i] = card.tokens[0];
        ids[i] = store.encode(&b, fulls[i][0..], card.slot_mask, card.tokens);
    }

    // Curiosity on open slots (episode 3 — index 2)
    const cur = curiosity_f.runCuriosity(&store, ids[2], 2);

    // Brief consolidation delay
    var ext: [brain_f.N_TOTAL]Fixed = .{fixed.fromDecimalStr("0.05")} ** brain_f.N_TOTAL;
    var d: usize = 0;
    while (d < 12) : (d += 1) b.step(ext[0..]);

    // Immediate recall by content features (not title)
    var correct: u32 = 0;
    i = 0;
    while (i < n_lessons) : (i += 1) {
        var sim: Fixed = 0;
        const hit = store.retrieve(&b, fulls[i][0..], &sim);
        var got: u32 = 0;
        var j: usize = 0;
        while (j < store.n) : (j += 1) {
            if (store.episodes[j].id == hit) {
                got = store.episodes[j].tokens[0];
                break;
            }
        }
        if (got == who_tok[i] and got != 0) correct += 1;
    }

    const top1 = @as(f64, @floatFromInt(correct)) / @as(f64, @floatFromInt(n_lessons));
    const sme = bands_f.runSmeProbe();

    const ok = top1 >= 0.6 and store.n >= n_lessons and (cur.n_questions == 0 or cur.n_resolved > 0) and sme.ok;
    return .{
        .ok = ok,
        .n_lessons = @intCast(n_lessons),
        .n_memory = @intCast(store.n),
        .recall_top1 = top1,
        .recall_correct = correct,
        .curiosity_resolved = cur.n_resolved,
        .sme_ok = sme.ok,
        .spikes = b.totalSpikes() + sme.spikes_enc,
    };
}
