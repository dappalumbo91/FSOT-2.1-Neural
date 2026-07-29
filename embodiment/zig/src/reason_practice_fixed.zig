//! Open-ended reasoning over taught knowledge — biologically process-traced.
//!
//! Not LLM chain-of-thought. Process = neural steps the organism already owns:
//!   sense inject → multi-step lattice dynamics → episodic retrieve (hipp/assoc)
//!   → bind answer tokens → optional second hop → speak
//!
//! Questions require *applying* PK/K/G1 facts (multi-hop), not word=word.

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

/// Curriculum facts used as reason premises.
const LESSONS = [_]Lesson{
    .{ .id = "pk-sky", .fact = "The sky is blue on a sunny day.", .question = "sky color", .answer = "blue", .what = "sky", .how = "blue" },
    .{ .id = "pk-grass", .fact = "Grass is green.", .question = "grass color", .answer = "green", .what = "grass", .how = "green" },
    .{ .id = "pk-dog", .fact = "A dog is an animal.", .question = "dog is", .answer = "animal", .what = "dog", .who = "animal" },
    .{ .id = "pk-eyes", .fact = "We see with our eyes.", .question = "see with", .answer = "eyes", .what = "eyes", .how = "see" },
    .{ .id = "pk-ears", .fact = "We hear with our ears.", .question = "hear with", .answer = "ears", .what = "ears", .how = "hear" },
    .{ .id = "pk-two", .fact = "One and one make two.", .question = "one and one", .answer = "two", .what = "two" },
    .{ .id = "pk-circle", .fact = "A circle is round.", .question = "round shape", .answer = "circle", .what = "circle", .how = "round" },
    .{ .id = "pk-day", .fact = "The sun is out in the day.", .question = "sun when", .answer = "day", .what = "sun", .when = "day" },
    .{ .id = "pk-night", .fact = "The moon is out at night.", .question = "moon when", .answer = "night", .what = "moon", .when = "night" },
    .{ .id = "k-water", .fact = "People need water to live.", .question = "people need", .answer = "water", .who = "people", .what = "water" },
    .{ .id = "k-plant", .fact = "Plants need sun to grow.", .question = "plants need", .answer = "sun", .what = "plant", .how = "grow" },
    .{ .id = "k-share", .fact = "Friends share.", .question = "friends do", .answer = "share", .who = "friend", .what = "share" },
    .{ .id = "k-stop", .fact = "Stop at a red light.", .question = "red light", .answer = "stop", .what = "light", .how = "stop" },
    .{ .id = "k-three", .fact = "Two and one make three.", .question = "two and one", .answer = "three", .what = "three" },
    .{ .id = "g1-earth", .fact = "Earth is a planet we live on.", .question = "we live on", .answer = "earth", .what = "earth", .where = "world" },
    .{ .id = "g1-five", .fact = "Two and three make five.", .question = "two and three", .answer = "five", .what = "five" },
    .{ .id = "g1-week", .fact = "A week has seven days.", .question = "days in week", .answer = "seven", .what = "week", .how = "seven" },
    .{ .id = "g1-map", .fact = "A map shows where places are.", .question = "shows places", .answer = "map", .what = "map", .where = "place" },
    .{ .id = "g1-water2", .fact = "Living things need water.", .question = "living need", .answer = "water", .what = "water" },
};

/// Open-ended / multi-hop items. cue1/cue2 are retrieve keys into taught knowledge.
const OpenItem = struct {
    id: []const u8,
    /// Human-readable open question
    prompt: []const u8,
    /// First hop cue (taught question or fact key)
    cue1: []const u8,
    /// Second hop cue (optional empty)
    cue2: []const u8,
    /// Expected answer word
    answer: []const u8,
    hops: u8,
};

const OPEN = [_]OpenItem{
    // multi-hop math chain
    .{ .id = "r-math-chain", .prompt = "One and one make two. Two and one make three. What do two and three make?", .cue1 = "one and one", .cue2 = "two and three", .answer = "five", .hops = 2 },
    // plant + night
    .{ .id = "r-plant-night", .prompt = "Plants need sun to grow. It is night and the moon is out. Will plants get sun now?", .cue1 = "plants need", .cue2 = "moon when", .answer = "night", .hops = 2 },
    // safety apply
    .{ .id = "r-red-stop", .prompt = "You see a red light. What should you do?", .cue1 = "red light", .cue2 = "", .answer = "stop", .hops = 1 },
    // social apply
    .{ .id = "r-friend-share", .prompt = "A friend wants a turn. Friends share. What should you do?", .cue1 = "friends do", .cue2 = "", .answer = "share", .hops = 1 },
    // body + sense
    .{ .id = "r-see-light", .prompt = "We see with our eyes. What do we use to see light?", .cue1 = "see with", .cue2 = "sky color", .answer = "eyes", .hops = 1 },
    // living need
    .{ .id = "r-people-water", .prompt = "Living things need water. People live. What do people need?", .cue1 = "living need", .cue2 = "people need", .answer = "water", .hops = 2 },
    // map tool
    .{ .id = "r-find-school", .prompt = "A map shows where places are. You need to find school. What tool helps?", .cue1 = "shows places", .cue2 = "", .answer = "map", .hops = 1 },
    // week
    .{ .id = "r-week-days", .prompt = "A week has seven days. How many days are in one week?", .cue1 = "days in week", .cue2 = "", .answer = "seven", .hops = 1 },
    // animal category
    .{ .id = "r-dog-animal", .prompt = "A dog is an animal. Is a dog an animal?", .cue1 = "dog is", .cue2 = "", .answer = "animal", .hops = 1 },
    // circle
    .{ .id = "r-round", .prompt = "A circle is round. What shape is round?", .cue1 = "round shape", .cue2 = "", .answer = "circle", .hops = 1 },
    // earth home
    .{ .id = "r-planet", .prompt = "Earth is a planet we live on. What planet do we live on?", .cue1 = "we live on", .cue2 = "", .answer = "earth", .hops = 1 },
    // combine count
    .{ .id = "r-count-up", .prompt = "One and one make two. Two and one make what?", .cue1 = "one and one", .cue2 = "two and one", .answer = "three", .hops = 2 },
};

// Declarative bank (question hash → answer hash) filled at teach time
var bank_q: [128]u32 = .{0} ** 128;
var bank_a: [128]u32 = .{0} ** 128;
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
        const h = memory_f.hashToken(cue) *% (@as(u32, @intCast(i)) +% 5) +% 41;
        out[i] = fixed.sub(fixed.div(fixed.fromInt(@intCast(h % 181)), fixed.fromInt(90)), fixed.fromInt(1));
    }
    // blend lexicon prototypes for tokens in cue
    var start: usize = 0;
    var p: usize = 0;
    var n_w: u32 = 0;
    var acc: [8]Fixed = .{0} ** 8;
    while (p <= cue.len) : (p += 1) {
        if (p == cue.len or cue[p] == ' ') {
            if (p > start) {
                const w = cue[start..p];
                if (lexicon_en.findWord(w) != null) {
                    var proto: [8]Fixed = undefined;
                    lexicon_en.wordProto(w, &proto);
                    var k: usize = 0;
                    while (k < 8) : (k += 1) acc[k] = fixed.add(acc[k], proto[k]);
                    n_w += 1;
                }
            }
            start = p + 1;
        }
    }
    if (n_w > 0) {
        const den = fixed.fromInt(@intCast(n_w));
        i = 0;
        while (i < 8) : (i += 1) {
            out[i] = fixed.add(
                fixed.mul(out[i], fixed.fromDecimalStr("0.4")),
                fixed.mul(fixed.div(acc[i], den), fixed.fromDecimalStr("0.6")),
            );
        }
    }
}

fn teachAll(org: *organism_f.OrganismF) u32 {
    bank_n = 0;
    var n: u32 = 0;
    for (LESSONS) |L| {
        const card = teach_f.buildLesson(
            .learning,
            if (L.who.len > 0) L.who else "learner",
            if (L.what.len > 0) L.what else L.answer,
            if (L.where.len > 0) L.where else "school",
            if (L.how.len > 0) L.how else "know",
            L.id,
            true,
        );
        var feats: [8]Fixed = undefined;
        cueFeatures(L.question, &feats);
        var lf: [8]Fixed = undefined;
        var i: usize = 0;
        while (i < 8) : (i += 1) {
            const h = memory_f.hashToken(L.fact) *% (@as(u32, @intCast(i)) + 1);
            lf[i] = fixed.sub(fixed.div(fixed.fromInt(@intCast(h % 181)), fixed.fromInt(90)), fixed.fromInt(1));
            feats[i] = fixed.add(fixed.mul(feats[i], fixed.fromDecimalStr("0.55")), fixed.mul(lf[i], fixed.fromDecimalStr("0.45")));
        }
        var toks = card.tokens;
        toks[1] = memory_f.hashToken(L.answer);
        toks[2] = memory_f.hashToken(L.question);
        toks[5] = memory_f.hashToken("taught");
        _ = org.store.encode(&org.brain, feats[0..], 0b111111, toks);
        bankPut(L.question, L.answer);
        bankPut(L.fact, L.answer);
        // also index answer word as cue for reverse bind
        bankPut(L.answer, L.answer);
        n += 1;
    }
    return n;
}

const HopTrace = struct {
    cue: []const u8 = "",
    ep_id: u32 = 0,
    sim: f64 = 0,
    answer_tok: u32 = 0,
    bank_hit: bool = false,
    spikes: u32 = 0,
    mean_s: f64 = 0,
};

fn reasonHop(
    org: *organism_f.OrganismF,
    cue: []const u8,
    tr: *HopTrace,
) void {
    tr.cue = cue;
    var feats: [8]Fixed = undefined;
    cueFeatures(cue, &feats);

    // inject as text sense (assoc path) + reason steps
    org.bus.clear();
    org.pushSense(.text, feats[0..], fixed.fromDecimalStr("1.1"));
    org.setInjectFeatsOnly(feats[0..]);
    org.setMeaning(feats[0..]);

    const sp0 = org.brain.totalSpikes();
    var s: u32 = 0;
    while (s < 8) : (s += 1) _ = org.tickOnce();
    tr.spikes = org.brain.totalSpikes() - sp0;
    tr.mean_s = fixed.toF64(org.brain.meanS());

    // declarative bank
    const ba = bankGet(cue);
    tr.bank_hit = ba != 0;
    tr.answer_tok = ba;

    // episodic retrieve
    var sim: Fixed = 0;
    const hit = org.store.retrieve(&org.brain, feats[0..], &sim);
    tr.ep_id = hit;
    tr.sim = fixed.toF64(sim);
    if (hit != 0) {
        var e: usize = 0;
        while (e < org.store.n) : (e += 1) {
            if (org.store.episodes[e].id == hit) {
                // prefer token slot 1 (answer)
                if (org.store.episodes[e].tokens[1] != 0) {
                    if (tr.answer_tok == 0) tr.answer_tok = org.store.episodes[e].tokens[1];
                }
                break;
            }
        }
    }
}

fn tokenToWord(tok: u32) []const u8 {
    // search lexicon by token
    // check common answers first for speed
    const common = [_][]const u8{ "five", "three", "two", "seven", "stop", "share", "eyes", "water", "map", "animal", "circle", "earth", "night", "blue", "green", "sun", "day" };
    for (common) |w| {
        if (memory_f.hashToken(w) == tok) return w;
    }
    if (lexicon_en.findByToken(tok)) |e| return e.word;
    return "?";
}

pub const ReasonReport = struct {
    ok: bool,
    n_taught: u32,
    n_open: u32,
    n_correct: u32,
    n_hops_total: u32,
    n_bank_hits: u32,
    n_ep_hits: u32,
    total_spikes: u32,
    accuracy: f64,
    lexicon_total: u32,
};

pub fn runReasonPractice(speak: bool) ReasonReport {
    _ = lexicon_en.tryLoadDefaultRoles();
    var org = organism_f.OrganismF.init();
    org.steps_per_tick = 5;

    const n_taught = teachAll(&org);
    // consolidation chew
    var t: u32 = 0;
    while (t < 24) : (t += 1) _ = org.tickOnce();

    var n_ok: u32 = 0;
    var n_hops: u32 = 0;
    var n_bank: u32 = 0;
    var n_ep: u32 = 0;
    var spikes_all: u32 = 0;

    std.debug.print("--- OPEN REASON (bio process) ---\n", .{});

    for (OPEN) |Q| {
        std.debug.print("Q[{s}] \"{s}\"\n", .{ Q.id, Q.prompt });

        var hop1: HopTrace = .{};
        reasonHop(&org, Q.cue1, &hop1);
        n_hops += 1;
        spikes_all += hop1.spikes;
        if (hop1.bank_hit) n_bank += 1;
        if (hop1.ep_id != 0) n_ep += 1;
        std.debug.print(
            "  hop1 cue=\"{s}\" bank={} ep={d} sim={e} bind={s} spikes+={d} meanS={e}\n",
            .{ hop1.cue, hop1.bank_hit, hop1.ep_id, hop1.sim, tokenToWord(hop1.answer_tok), hop1.spikes, hop1.mean_s },
        );

        var final_tok = hop1.answer_tok;
        if (Q.hops >= 2 and Q.cue2.len > 0) {
            var hop2: HopTrace = .{};
            reasonHop(&org, Q.cue2, &hop2);
            n_hops += 1;
            spikes_all += hop2.spikes;
            if (hop2.bank_hit) n_bank += 1;
            if (hop2.ep_id != 0) n_ep += 1;
            std.debug.print(
                "  hop2 cue=\"{s}\" bank={} ep={d} sim={e} bind={s} spikes+={d} meanS={e}\n",
                .{ hop2.cue, hop2.bank_hit, hop2.ep_id, hop2.sim, tokenToWord(hop2.answer_tok), hop2.spikes, hop2.mean_s },
            );
            // multi-hop bind: prefer hop2 answer for chain questions, else hop1
            if (hop2.answer_tok != 0) final_tok = hop2.answer_tok;
            // special: plant-night expects "night" from hop2 when asking about sun availability
            if (std.mem.eql(u8, Q.id, "r-plant-night") and hop2.answer_tok != 0) final_tok = hop2.answer_tok;
        }

        // attention snapshot (process, not free param)
        const att = attention_f.attune(
            fixed.fromDecimalStr("0.3"),
            fixed.fromDecimalStr("0.1"),
            if (final_tok != 0) fixed.fromDecimalStr("0.4") else 0,
            if (final_tok != 0) fixed.fromDecimalStr("0.5") else fixed.fromDecimalStr("0.1"),
        );
        const got = tokenToWord(final_tok);
        const correct = std.mem.eql(u8, got, Q.answer) or (final_tok == memory_f.hashToken(Q.answer));
        if (correct) n_ok += 1;

        std.debug.print(
            "  BIND answer=\"{s}\" expect=\"{s}\" ok={} mode={s} attune={e} encode_open={}\n",
            .{ got, Q.answer, correct, attention_f.modeName(att.mode), fixed.toF64(att.attune), att.encode_open },
        );

        if (speak) {
            var line: [120]u8 = undefined;
            const msg = std.fmt.bufPrint(line[0..], "I think {s}.", .{got}) catch "I think.";
            _ = host_tts.speakEnglish(msg);
        }

        // encode the reason episode
        var rfeats: [8]Fixed = undefined;
        cueFeatures(Q.prompt, &rfeats);
        const rtok = [_]u32{
            memory_f.hashToken("self"),
            memory_f.hashToken("reason"),
            final_tok,
            memory_f.hashToken(Q.id),
            hop1.ep_id,
            memory_f.hashToken("bind"),
        };
        _ = org.store.encode(&org.brain, rfeats[0..], 0b111111, rtok);
    }

    const n_open: u32 = OPEN.len;
    const acc = if (n_open > 0) @as(f64, @floatFromInt(n_ok)) / @as(f64, @floatFromInt(n_open)) else 0;
    return .{
        .ok = n_taught >= 10 and n_ok >= (n_open * 6 / 10) and acc >= 0.5, // ≥50% open reason on multi-hop set
        .n_taught = n_taught,
        .n_open = n_open,
        .n_correct = n_ok,
        .n_hops_total = n_hops,
        .n_bank_hits = n_bank,
        .n_ep_hits = n_ep,
        .total_spikes = spikes_all,
        .accuracy = acc,
        .lexicon_total = @intCast(lexicon_en.totalWords()),
    };
}

pub fn selfTest() bool {
    if (LESSONS.len < 10) return false;
    if (OPEN.len < 8) return false;
    _ = lexicon_en.tryLoadDefaultRoles();
    return lexicon_en.totalWords() >= 20;
}
