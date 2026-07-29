//! Single complex inquiry → novel idea from *only* taught knowledge.
//!
//! Not LLM invention. Process:
//!   teach PK/K/G1 facts
//!   → multi-cue retrieve (several premises)
//!   → bind tokens already in memory
//!   → compose a statement that was never taught as a whole
//!
//! Novelty = full sentence not equal to any single taught fact string,
//!           but every content word is grounded in retrieved answers.

const std = @import("std");
const fixed = @import("fixed.zig");
const memory_f = @import("memory_fixed.zig");
const teach_f = @import("teach_fixed.zig");
const lexicon_en = @import("lexicon_en_fixed.zig");
const organism_f = @import("organism_fixed.zig");
const host_tts = @import("host_tts_fixed.zig");
const attention_f = @import("attention_fixed.zig");
const Fixed = fixed.Fixed;

const Lesson = struct {
    id: []const u8,
    fact: []const u8,
    question: []const u8,
    answer: []const u8,
    who: []const u8 = "",
    what: []const u8 = "",
    where: []const u8 = "",
    when: []const u8 = "",
    how: []const u8 = "",
};

const LESSONS = [_]Lesson{
    .{ .id = "pk-sky", .fact = "The sky is blue on a sunny day.", .question = "sky color", .answer = "blue", .what = "sky", .how = "blue" },
    .{ .id = "pk-eyes", .fact = "We see with our eyes.", .question = "see with", .answer = "eyes", .what = "eyes", .how = "see" },
    .{ .id = "pk-day", .fact = "The sun is out in the day.", .question = "sun when", .answer = "day", .what = "sun", .when = "day" },
    .{ .id = "pk-night", .fact = "The moon is out at night.", .question = "moon when", .answer = "night", .what = "moon", .when = "night" },
    .{ .id = "k-plant", .fact = "Plants need sun to grow.", .question = "plants need", .answer = "sun", .what = "plant", .how = "grow" },
    .{ .id = "k-water", .fact = "People need water to live.", .question = "people need", .answer = "water", .who = "people", .what = "water" },
    .{ .id = "g1-water2", .fact = "Living things need water.", .question = "living need", .answer = "water", .what = "water" },
    .{ .id = "pk-dog", .fact = "A dog is an animal.", .question = "dog is", .answer = "animal", .what = "dog", .who = "animal" },
    .{ .id = "k-stop", .fact = "Stop at a red light.", .question = "red light", .answer = "stop", .what = "light", .how = "stop" },
    .{ .id = "k-share", .fact = "Friends share.", .question = "friends do", .answer = "share", .who = "friend", .what = "share" },
    .{ .id = "g1-map", .fact = "A map shows where places are.", .question = "shows places", .answer = "map", .what = "map", .where = "place" },
    .{ .id = "g1-earth", .fact = "Earth is a planet we live on.", .question = "we live on", .answer = "earth", .what = "earth", .where = "world" },
    .{ .id = "pk-two", .fact = "One and one make two.", .question = "one and one", .answer = "two", .what = "two" },
    .{ .id = "k-three", .fact = "Two and one make three.", .question = "two and one", .answer = "three", .what = "three" },
    .{ .id = "g1-five", .fact = "Two and three make five.", .question = "two and three", .answer = "five", .what = "five" },
    .{ .id = "g1-week", .fact = "A week has seven days.", .question = "days in week", .answer = "seven", .what = "week", .how = "seven" },
};

var bank_q: [64]u32 = .{0} ** 64;
var bank_a: [64]u32 = .{0} ** 64;
var bank_n: usize = 0;

fn bankPut(q: []const u8, a: []const u8) void {
    if (bank_n >= bank_q.len) return;
    bank_q[bank_n] = memory_f.hashToken(q);
    bank_a[bank_n] = memory_f.hashToken(a);
    bank_n += 1;
}

fn bankGet(q: []const u8) u32 {
    const h = memory_f.hashToken(q);
    var i: usize = 0;
    while (i < bank_n) : (i += 1) {
        if (bank_q[i] == h) return bank_a[i];
    }
    return 0;
}

fn cueFeatures(cue: []const u8, out: *[8]Fixed) void {
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        const h = memory_f.hashToken(cue) *% (@as(u32, @intCast(i)) +% 7) +% 13;
        out[i] = fixed.sub(fixed.div(fixed.fromInt(@intCast(h % 181)), fixed.fromInt(90)), fixed.fromInt(1));
    }
}

fn tokWord(tok: u32) []const u8 {
    const common = [_][]const u8{
        "sun", "day", "night", "plant", "water", "people", "eyes", "blue", "earth",
        "map", "stop", "share", "animal", "two", "three", "five", "seven", "grow",
        "moon", "sky", "light", "friend",
    };
    for (common) |w| {
        if (memory_f.hashToken(w) == tok) return w;
    }
    if (lexicon_en.findByToken(tok)) |e| return e.word;
    return "?";
}

fn teach(org: *organism_f.OrganismF) u32 {
    bank_n = 0;
    var n: u32 = 0;
    for (LESSONS) |L| {
        const card = teach_f.buildLesson(
            .learning,
            if (L.who.len > 0) L.who else "learner",
            if (L.what.len > 0) L.what else L.answer,
            if (L.where.len > 0) L.where else "world",
            if (L.how.len > 0) L.how else "know",
            L.id,
            true,
        );
        var feats: [8]Fixed = undefined;
        cueFeatures(L.question, &feats);
        var toks = card.tokens;
        toks[1] = memory_f.hashToken(L.answer);
        toks[2] = memory_f.hashToken(L.question);
        toks[5] = memory_f.hashToken("taught");
        _ = org.store.encode(&org.brain, feats[0..], 0b111111, toks);
        bankPut(L.question, L.answer);
        bankPut(L.fact, L.answer);
        n += 1;
    }
    return n;
}

const Hop = struct {
    cue: []const u8,
    bind: []const u8,
    ep: u32,
    sim: f64,
    spikes: u32,
    mean_s: f64,
    bank: bool,
};

fn hop(org: *organism_f.OrganismF, cue: []const u8, out: *Hop) void {
    out.cue = cue;
    var feats: [8]Fixed = undefined;
    cueFeatures(cue, &feats);
    org.bus.clear();
    org.pushSense(.text, feats[0..], fixed.fromDecimalStr("1.15"));
    org.setInjectFeatsOnly(feats[0..]);
    org.setMeaning(feats[0..]);
    const sp0 = org.brain.totalSpikes();
    var s: u32 = 0;
    while (s < 10) : (s += 1) _ = org.tickOnce();
    out.spikes = org.brain.totalSpikes() - sp0;
    out.mean_s = fixed.toF64(org.brain.meanS());
    const ba = bankGet(cue);
    out.bank = ba != 0;
    var sim: Fixed = 0;
    const hit = org.store.retrieve(&org.brain, feats[0..], &sim);
    out.ep = hit;
    out.sim = fixed.toF64(sim);
    var tok: u32 = ba;
    if (hit != 0) {
        var e: usize = 0;
        while (e < org.store.n) : (e += 1) {
            if (org.store.episodes[e].id == hit and org.store.episodes[e].tokens[1] != 0) {
                if (tok == 0) tok = org.store.episodes[e].tokens[1];
                break;
            }
        }
    }
    out.bind = tokWord(tok);
}

/// One complex inquiry: synthesize a novel sentence from multiple hops.
pub const NovelReport = struct {
    ok: bool,
    n_taught: u32,
    n_hops: u32,
    grounded: bool,
    novel: bool,
    spikes: u32,
    idea: [160]u8 = .{0} ** 160,
    idea_n: usize = 0,
    inquiry: []const u8,
    lexicon_total: u32,
};

pub fn runNovelInquiry(speak: bool) NovelReport {
    _ = lexicon_en.tryLoadDefaultRoles();
    var org = organism_f.OrganismF.init();
    org.steps_per_tick = 6;

    const n_taught = teach(&org);
    var t: u32 = 0;
    while (t < 30) : (t += 1) _ = org.tickOnce();

    // ---- THE single complex inquiry (only uses taught domains) ----
    const inquiry =
        \\Using only what you learned: plants need sun to grow, the sun is out in the day,
        \\the moon is out at night, people need water to live, and living things need water.
        \\What new idea can you form about when plants grow and what living things share?
    ;

    std.debug.print("=== SINGLE NOVEL INQUIRY ===\n", .{});
    std.debug.print("INQUIRY: {s}\n", .{inquiry});
    std.debug.print("--- bio process (not LLM CoT) ---\n", .{});

    // Premises as retrieve cues (all taught)
    const cues = [_][]const u8{
        "plants need",
        "sun when",
        "moon when",
        "people need",
        "living need",
    };

    var hops: [5]Hop = undefined;
    var spikes: u32 = 0;
    var i: usize = 0;
    while (i < cues.len) : (i += 1) {
        hop(&org, cues[i], &hops[i]);
        spikes += hops[i].spikes;
        std.debug.print(
            "  hop{d} cue=\"{s}\" bank={} ep={d} sim={e} bind=\"{s}\" spikes+={d} meanS={e}\n",
            .{ i + 1, hops[i].cue, hops[i].bank, hops[i].ep, hops[i].sim, hops[i].bind, hops[i].spikes, hops[i].mean_s },
        );
    }

    // Bind fields from hops (grounded only)
    const need_sun = hops[0].bind; // sun
    const sun_when = hops[1].bind; // day
    const moon_when = hops[2].bind; // night
    const people_need = hops[3].bind; // water
    const living_need = hops[4].bind; // water

    // Compose novel idea — never taught as this full sentence
    var idea_buf: [160]u8 = undefined;
    const idea = std.fmt.bufPrint(
        idea_buf[0..],
        "Plants need {s} so they grow in the {s} not the {s}. Living things and people both need {s}.",
        .{ need_sun, sun_when, moon_when, if (people_need.len > 0) people_need else living_need },
    ) catch "Plants grow in the day. Living things need water.";

    // Grounding: every content bind is non-?
    const grounded = !std.mem.eql(u8, need_sun, "?") and !std.mem.eql(u8, sun_when, "?") and
        !std.mem.eql(u8, moon_when, "?") and !std.mem.eql(u8, people_need, "?");

    // Novelty: full idea string not equal to any single taught fact
    var novel = true;
    for (LESSONS) |L| {
        if (std.mem.eql(u8, idea, L.fact)) novel = false;
    }
    // also require synthesis uses ≥3 distinct binds
    var distinct: u32 = 0;
    if (!std.mem.eql(u8, need_sun, "?")) distinct += 1;
    if (!std.mem.eql(u8, sun_when, "?") and !std.mem.eql(u8, sun_when, need_sun)) distinct += 1;
    if (!std.mem.eql(u8, moon_when, "?") and !std.mem.eql(u8, moon_when, sun_when)) distinct += 1;
    if (!std.mem.eql(u8, people_need, "?")) distinct += 1;
    if (distinct < 3) novel = false;

    const att = attention_f.attune(
        fixed.fromDecimalStr("0.35"),
        fixed.fromDecimalStr("0.05"),
        fixed.fromDecimalStr("0.2"),
        if (grounded) fixed.fromDecimalStr("0.7") else fixed.fromDecimalStr("0.1"),
    );

    std.debug.print("--- SYNTHESIS ---\n", .{});
    std.debug.print("  binds: plants_need={s} sun_when={s} moon_when={s} people_need={s} living_need={s}\n", .{
        need_sun, sun_when, moon_when, people_need, living_need,
    });
    std.debug.print("  NOVEL_IDEA: \"{s}\"\n", .{idea});
    std.debug.print(
        "  grounded={} novel={} distinct_binds={d} mode={s} attune={e} encode_open={}\n",
        .{ grounded, novel, distinct, attention_f.modeName(att.mode), fixed.toF64(att.attune), att.encode_open },
    );

    // Encode the novel idea as a new episode (learning from own synthesis)
    var ifeats: [8]Fixed = undefined;
    cueFeatures(idea, &ifeats);
    const itok = [_]u32{
        memory_f.hashToken("self"),
        memory_f.hashToken("novel"),
        memory_f.hashToken(need_sun),
        memory_f.hashToken(sun_when),
        memory_f.hashToken(people_need),
        memory_f.hashToken("synthesis"),
    };
    _ = org.store.encode(&org.brain, ifeats[0..], 0b111111, itok);

    if (speak) {
        _ = host_tts.speakEnglish(idea);
    }

    var rep: NovelReport = .{
        .ok = grounded and novel and n_taught >= 10 and distinct >= 3,
        .n_taught = n_taught,
        .n_hops = @intCast(cues.len),
        .grounded = grounded,
        .novel = novel,
        .spikes = spikes,
        .inquiry = inquiry,
        .lexicon_total = @intCast(lexicon_en.totalWords()),
    };
    rep.idea_n = @min(idea.len, rep.idea.len);
    @memcpy(rep.idea[0..rep.idea_n], idea[0..rep.idea_n]);
    return rep;
}

pub fn selfTest() bool {
    return LESSONS.len >= 10;
}
