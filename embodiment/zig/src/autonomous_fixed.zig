//! Autonomous multi-domain learning loop (fixed) — minimal instruction.
//! Spirit of learn/autonomous_loop.py: chew available patterns without
//! per-item human prompts. Not next-token LLM training.
//! Media/docs remain optional host I/O; here we use synthetic multi-domain
//! "worlds" + machine-encode + bio bus + episodic memory.

const fixed = @import("fixed.zig");
const organism_f = @import("organism_fixed.zig");
const teach_f = @import("teach_fixed.zig");
const machine_f = @import("machine_encode_fixed.zig");
const pathways_f = @import("pathways_fixed.zig");
const speech_f = @import("speech_organ_fixed.zig");
const curiosity_f = @import("curiosity_fixed.zig");
const Fixed = fixed.Fixed;

pub const AutonomousReport = struct {
    ok: bool,
    n_domains: u32,
    n_episodes: u32,
    n_machine_words: u32,
    recall_correct: u32,
    recall_n: u32,
    recall_top1: f64,
    curiosity_resolved: u32,
    spikes: u32,
    spoke: bool,
};

pub fn runAutonomousProbe() AutonomousReport {
    var org = organism_f.OrganismF.init();
    org.encode_every = 6;
    org.steps_per_tick = 3;
    org.speak_every = 10;

    // Domain "worlds" available to the organism (no human prompt per item)
    const domains = [_]teach_f.Domain{ .physics_fsot, .biology, .narrative, .learning, .media };
    const tags = [_][]const u8{ "scalar", "ei_balance", "choice", "encode", "frame" };
    const n_dom: usize = 5;

    var fulls: [5][8]Fixed = undefined;
    var who: [5]u32 = undefined;
    var ids: [5]u32 = undefined;
    var i: usize = 0;
    while (i < n_dom) : (i += 1) {
        const card = teach_f.buildLesson(
            domains[i],
            tags[i],
            tags[i],
            "world",
            "auto",
            "autonomous",
            i != 2,
        );
        // machine path: tag bytes → trits → features
        var trits: [64]@import("trit.zig").Trit = undefined;
        const nt = machine_f.bytesToTrits(tags[i], trits[0..]);
        var feats: [8]Fixed = .{0} ** 8;
        _ = machine_f.tritsToFeatures(trits[0..@min(nt, 8)], feats[0..]);
        // blend with lesson-seeded pattern for separability
        var k: usize = 0;
        while (k < 8) : (k += 1) {
            const u: u32 = @as(u32, @intCast(i)) *% 41 +% @as(u32, @intCast(k)) *% 7 +% 3;
            const base = fixed.sub(fixed.div(fixed.fromInt(@intCast(u % 181)), fixed.fromInt(90)), fixed.fromInt(1));
            fulls[i][k] = fixed.add(fixed.mul(feats[k], fixed.fromDecimalStr("0.35")), fixed.mul(base, fixed.fromDecimalStr("0.65")));
        }
        who[i] = card.tokens[0];
        // push sense + encode
        org.pushSense(.custom, fulls[i][0..], fixed.fromDecimalStr("0.8"));
        org.setMeaning(fulls[i][0..]);
        var t: u32 = 0;
        while (t < 8) : (t += 1) _ = org.tickOnce();
        ids[i] = org.store.encode(&org.brain, fulls[i][0..], card.slot_mask, card.tokens);
    }

    // curiosity on open slots of one episode
    const cur = curiosity_f.runCuriosity(&org.store, ids[2], 2);

    // consolidation ticks
    var d: u32 = 0;
    while (d < 12) : (d += 1) _ = org.tickOnce();

    // autonomous recall by content features
    var correct: u32 = 0;
    i = 0;
    while (i < n_dom) : (i += 1) {
        var sim: Fixed = 0;
        const hit = org.store.retrieve(&org.brain, fulls[i][0..], &sim);
        var got: u32 = 0;
        var j: usize = 0;
        while (j < org.store.n) : (j += 1) {
            if (org.store.episodes[j].id == hit) {
                got = org.store.episodes[j].tokens[0];
                break;
            }
        }
        if (got == who[i] and got != 0) correct += 1;
    }

    // machine word count sample
    var sample_trits: [128]@import("trit.zig").Trit = undefined;
    const nst = machine_f.bytesToTrits("autonomous", sample_trits[0..]);
    var words: [8]@import("trit.zig").TritWord = undefined;
    const nw = machine_f.tritsToWords(sample_trits[0..nst], words[0..]);

    const top1 = @as(f64, @floatFromInt(correct)) / @as(f64, @floatFromInt(n_dom));
    const spoke = org.has_meaning; // meaning set; speak_every may have fired
    const ok = top1 >= 0.6 and org.store.n >= n_dom and nw >= 1;
    return .{
        .ok = ok,
        .n_domains = @intCast(n_dom),
        .n_episodes = @intCast(org.store.n),
        .n_machine_words = @intCast(nw),
        .recall_correct = correct,
        .recall_n = @intCast(n_dom),
        .recall_top1 = top1,
        .curiosity_resolved = cur.n_resolved,
        .spikes = org.brain.totalSpikes(),
        .spoke = spoke,
    };
}
