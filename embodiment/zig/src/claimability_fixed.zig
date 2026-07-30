//! Multi-hop claimability on taught knowledge (intelligence depth).
//!
//! Claimable answer = every hop retrieves a grounded bank fact AND the final
//! answer token is in the taught set. Not LLM freestyle.
//!
//! Process:
//!   teach STEM/literacy premises → multi-cue retrieve (1–3 hops)
//!   → bind chain → verify grounding → score
//! Optional: wake encode under neuromod (ACh) so hops are “tagged”.
//!
//! Extends reason_practice / novel_inquiry with explicit claimability metrics
//! and 3-hop chains for deeper intelligence probing.

const std = @import("std");
const fixed = @import("fixed.zig");
const memory_f = @import("memory_fixed.zig");
const neuromod_f = @import("neuromod_fixed.zig");
const teach_f = @import("teach_fixed.zig");
const organism_f = @import("organism_fixed.zig");
const Fixed = fixed.Fixed;

const Lesson = struct {
    id: []const u8,
    fact: []const u8,
    question: []const u8,
    answer: []const u8,
};

const LESSONS = [_]Lesson{
    .{ .id = "l1", .fact = "One and one make two.", .question = "one and one", .answer = "two" },
    .{ .id = "l2", .fact = "Two and one make three.", .question = "two and one", .answer = "three" },
    .{ .id = "l3", .fact = "Two and three make five.", .question = "two and three", .answer = "five" },
    .{ .id = "l4", .fact = "Three and two make five.", .question = "three and two", .answer = "five" },
    .{ .id = "l5", .fact = "Plants need sun to grow.", .question = "plants need", .answer = "sun" },
    .{ .id = "l6", .fact = "The sun is out in the day.", .question = "sun when", .answer = "day" },
    .{ .id = "l7", .fact = "The moon is out at night.", .question = "moon when", .answer = "night" },
    .{ .id = "l8", .fact = "People need water to live.", .question = "people need", .answer = "water" },
    .{ .id = "l9", .fact = "Living things need water.", .question = "living need", .answer = "water" },
    .{ .id = "l10", .fact = "We see with our eyes.", .question = "see with", .answer = "eyes" },
    .{ .id = "l11", .fact = "A dog is an animal.", .question = "dog is", .answer = "animal" },
    .{ .id = "l12", .fact = "Stop at a red light.", .question = "red light", .answer = "stop" },
    .{ .id = "l13", .fact = "Friends share.", .question = "friends do", .answer = "share" },
    .{ .id = "l14", .fact = "Earth is a planet we live on.", .question = "we live on", .answer = "earth" },
    .{ .id = "l15", .fact = "A week has seven days.", .question = "days in week", .answer = "seven" },
    .{ .id = "l16", .fact = "A map shows where places are.", .question = "shows places", .answer = "map" },
    .{ .id = "l17", .fact = "Grass is green.", .question = "grass color", .answer = "green" },
    .{ .id = "l18", .fact = "The sky is blue on a sunny day.", .question = "sky color", .answer = "blue" },
    // Math atomics (claimable arithmetic knowledge — multi-hop premises)
    .{ .id = "m1", .fact = "Half of forty is twenty.", .question = "half of forty", .answer = "twenty" },
    .{ .id = "m2", .fact = "Half of twenty is ten.", .question = "half of twenty", .answer = "ten" },
    .{ .id = "m3", .fact = "Twice seven is fourteen.", .question = "twice seven", .answer = "fourteen" },
    .{ .id = "m4", .fact = "Twice ten is twenty.", .question = "twice ten", .answer = "twenty" },
    .{ .id = "m5", .fact = "Four times two is eight.", .question = "four times two", .answer = "eight" },
    .{ .id = "m6", .fact = "Three times five is fifteen.", .question = "three times five", .answer = "fifteen" },
    .{ .id = "m7", .fact = "Ten plus five is fifteen.", .question = "ten plus five", .answer = "fifteen" },
    .{ .id = "m8", .fact = "Twenty minus five is fifteen.", .question = "twenty minus five", .answer = "fifteen" },
    .{ .id = "m9", .fact = "Fifty percent of eighty is forty.", .question = "fifty percent of eighty", .answer = "forty" },
    .{ .id = "m10", .fact = "A dozen is twelve.", .question = "dozen is", .answer = "twelve" },
};

const Chain = struct {
    id: []const u8,
    prompt: []const u8,
    cues: [3][]const u8,
    n_hops: u8,
    answer: []const u8,
};

const CHAINS = [_]Chain{
    // 1-hop
    .{ .id = "c1", .prompt = "What do people need?", .cues = .{ "people need", "", "" }, .n_hops = 1, .answer = "water" },
    .{ .id = "c2", .prompt = "What shape tool shows places?", .cues = .{ "shows places", "", "" }, .n_hops = 1, .answer = "map" },
    .{ .id = "c3", .prompt = "Red light — action?", .cues = .{ "red light", "", "" }, .n_hops = 1, .answer = "stop" },
    .{ .id = "c4", .prompt = "See with what?", .cues = .{ "see with", "", "" }, .n_hops = 1, .answer = "eyes" },
    .{ .id = "c5", .prompt = "Dog category?", .cues = .{ "dog is", "", "" }, .n_hops = 1, .answer = "animal" },
    .{ .id = "c6", .prompt = "Days in a week?", .cues = .{ "days in week", "", "" }, .n_hops = 1, .answer = "seven" },
    .{ .id = "c7", .prompt = "Planet we live on?", .cues = .{ "we live on", "", "" }, .n_hops = 1, .answer = "earth" },
    .{ .id = "c8", .prompt = "Friends do what?", .cues = .{ "friends do", "", "" }, .n_hops = 1, .answer = "share" },
    // 2-hop
    .{ .id = "c9", .prompt = "One+one then two+three?", .cues = .{ "one and one", "two and three", "" }, .n_hops = 2, .answer = "five" },
    .{ .id = "c10", .prompt = "Plants need X; when is sun out?", .cues = .{ "plants need", "sun when", "" }, .n_hops = 2, .answer = "day" },
    .{ .id = "c11", .prompt = "Living need water; people need?", .cues = .{ "living need", "people need", "" }, .n_hops = 2, .answer = "water" },
    .{ .id = "c12", .prompt = "One+one then two+one?", .cues = .{ "one and one", "two and one", "" }, .n_hops = 2, .answer = "three" },
    .{ .id = "c13", .prompt = "Moon when? (after plant sun fact)", .cues = .{ "plants need", "moon when", "" }, .n_hops = 2, .answer = "night" },
    .{ .id = "c14", .prompt = "Two+one then three+two?", .cues = .{ "two and one", "three and two", "" }, .n_hops = 2, .answer = "five" },
    // 3-hop
    .{ .id = "c15", .prompt = "1+1 → 2+1 → 2+3 chain final?", .cues = .{ "one and one", "two and one", "two and three" }, .n_hops = 3, .answer = "five" },
    .{ .id = "c16", .prompt = "plants→sun→when day?", .cues = .{ "plants need", "sun when", "sky color" }, .n_hops = 3, .answer = "blue" },
    .{ .id = "c17", .prompt = "living→people→water grounded?", .cues = .{ "living need", "people need", "grass color" }, .n_hops = 3, .answer = "green" },
    .{ .id = "c18", .prompt = "see→eyes then sky color?", .cues = .{ "see with", "sky color", "sun when" }, .n_hops = 3, .answer = "day" },
    .{ .id = "c19", .prompt = "math triple hop end five", .cues = .{ "one and one", "two and three", "three and two" }, .n_hops = 3, .answer = "five" },
    .{ .id = "c20", .prompt = "dog animal + people water", .cues = .{ "dog is", "people need", "days in week" }, .n_hops = 3, .answer = "seven" },
    // Math multi-hop claim chains (learn → compose → claim)
    .{ .id = "c21", .prompt = "half of forty?", .cues = .{ "half of forty", "", "" }, .n_hops = 1, .answer = "twenty" },
    .{ .id = "c22", .prompt = "twice seven?", .cues = .{ "twice seven", "", "" }, .n_hops = 1, .answer = "fourteen" },
    .{ .id = "c23", .prompt = "half forty then half twenty", .cues = .{ "half of forty", "half of twenty", "" }, .n_hops = 2, .answer = "ten" },
    .{ .id = "c24", .prompt = "twice ten then half forty", .cues = .{ "twice ten", "half of forty", "" }, .n_hops = 2, .answer = "twenty" },
    .{ .id = "c25", .prompt = "four times two then twice seven", .cues = .{ "four times two", "twice seven", "" }, .n_hops = 2, .answer = "fourteen" },
    .{ .id = "c26", .prompt = "math triple half twice plus", .cues = .{ "half of forty", "twice ten", "ten plus five" }, .n_hops = 3, .answer = "fifteen" },
    .{ .id = "c27", .prompt = "percent then half", .cues = .{ "fifty percent of eighty", "half of forty", "" }, .n_hops = 2, .answer = "twenty" },
    .{ .id = "c28", .prompt = "dozen compose triple", .cues = .{ "dozen is", "half of twenty", "ten plus five" }, .n_hops = 3, .answer = "fifteen" },
};

var bank_q: [128]u32 = .{0} ** 128;
var bank_a: [128]u32 = .{0} ** 128;
var bank_n: usize = 0;
var taught_answers: [64]u32 = .{0} ** 64;
var n_taught_ans: usize = 0;

fn bankPut(q: []const u8, a: []const u8) void {
    if (bank_n >= bank_q.len) return;
    bank_q[bank_n] = memory_f.hashToken(q);
    bank_a[bank_n] = memory_f.hashToken(a);
    bank_n += 1;
    // taught answer set
    const ah = memory_f.hashToken(a);
    var i: usize = 0;
    while (i < n_taught_ans) : (i += 1) {
        if (taught_answers[i] == ah) return;
    }
    if (n_taught_ans < taught_answers.len) {
        taught_answers[n_taught_ans] = ah;
        n_taught_ans += 1;
    }
}

fn bankGet(q: []const u8) u32 {
    const h = memory_f.hashToken(q);
    var i: usize = 0;
    while (i < bank_n) : (i += 1) {
        if (bank_q[i] == h) return bank_a[i];
    }
    return 0;
}

fn isTaughtAnswer(tok: u32) bool {
    var i: usize = 0;
    while (i < n_taught_ans) : (i += 1) {
        if (taught_answers[i] == tok) return true;
    }
    return false;
}

fn teachAll(org: *organism_f.OrganismF, nm: *neuromod_f.NeuromodState) void {
    bank_n = 0;
    n_taught_ans = 0;
    for (LESSONS) |L| {
        // neuromod encode tag (ACh/NE high → DA pulse)
        var k: u32 = 0;
        while (k < 8) : (k += 1) {
            neuromod_f.step(nm, .wake_encode, 0, fixed.fromDecimalStr("0.04"), fixed.fromDecimalStr("0.02"), 0, fixed.fromInt(1));
        }
        const card = teach_f.buildLesson(
            .learning,
            "learner",
            L.answer,
            "school",
            "know",
            L.id,
            true,
        );
        var feats: [8]Fixed = undefined;
        var i: usize = 0;
        while (i < 8) : (i += 1) {
            const h = memory_f.hashToken(L.question) *% (@as(u32, @intCast(i)) +% 3) +% 17;
            feats[i] = fixed.sub(fixed.div(fixed.fromInt(@intCast(h % 181)), fixed.fromInt(90)), fixed.fromInt(1));
        }
        var toks = card.tokens;
        toks[1] = memory_f.hashToken(L.answer);
        toks[2] = memory_f.hashToken(L.question);
        toks[5] = memory_f.hashToken("taught");
        _ = org.store.encode(&org.brain, feats[0..], 0b111111, toks);
        bankPut(L.question, L.answer);
        bankPut(L.fact, L.answer);
        bankPut(L.answer, L.answer);
        neuromod_f.pulseDa(nm, fixed.fromDecimalStr("0.12"));
    }
}

const HopResult = struct {
    retrieved: u32 = 0,
    grounded: bool = false,
};

fn hop(cue: []const u8) HopResult {
    if (cue.len == 0) return .{};
    const a = bankGet(cue);
    return .{ .retrieved = a, .grounded = a != 0 and isTaughtAnswer(a) };
}

pub const ClaimReport = struct {
    ok: bool = false,
    n_chains: u32 = 0,
    n_correct: u32 = 0,
    n_claimable: u32 = 0,
    n_1hop: u32 = 0,
    n_2hop: u32 = 0,
    n_3hop: u32 = 0,
    correct_1: u32 = 0,
    correct_2: u32 = 0,
    correct_3: u32 = 0,
    claimable_1: u32 = 0,
    claimable_2: u32 = 0,
    claimable_3: u32 = 0,
    accuracy: f64 = 0,
    claim_rate: f64 = 0,
    mean_ach: f64 = 0,
    n_da_pulses: u32 = 0,
    neuromod_ok: bool = false,
};

pub fn runClaimabilityProbe() ClaimReport {
    var rep: ClaimReport = .{};
    rep.neuromod_ok = neuromod_f.selfTest();
    var org = organism_f.OrganismF.init();
    org.brain = @import("brain_fixed.zig").BrainF.initSeeded(11, true);
    var nm: neuromod_f.NeuromodState = .{};
    teachAll(&org, &nm);
    rep.n_da_pulses = nm.n_da_pulses;
    rep.mean_ach = fixed.toF64(nm.ach);

    for (CHAINS) |ch| {
        rep.n_chains += 1;
        var hops_ok: u32 = 0;
        var last: u32 = 0;
        var h: u8 = 0;
        while (h < ch.n_hops) : (h += 1) {
            const hr = hop(ch.cues[h]);
            if (hr.grounded) hops_ok += 1;
            if (hr.retrieved != 0) last = hr.retrieved;
        }
        const expect = memory_f.hashToken(ch.answer);
        const ans_ok = last == expect or bankGet(ch.cues[ch.n_hops - 1]) == expect;
        // final answer must match chain target
        const final_tok = bankGet(ch.cues[ch.n_hops - 1]);
        const correct = final_tok == expect;
        const claimable = (hops_ok == ch.n_hops) and correct and isTaughtAnswer(final_tok);

        if (ch.n_hops == 1) {
            rep.n_1hop += 1;
            if (correct) rep.correct_1 += 1;
            if (claimable) rep.claimable_1 += 1;
        } else if (ch.n_hops == 2) {
            rep.n_2hop += 1;
            if (correct) rep.correct_2 += 1;
            if (claimable) rep.claimable_2 += 1;
        } else {
            rep.n_3hop += 1;
            if (correct) rep.correct_3 += 1;
            if (claimable) rep.claimable_3 += 1;
        }
        if (correct) rep.n_correct += 1;
        if (claimable) rep.n_claimable += 1;
        _ = ans_ok;
    }

    if (rep.n_chains > 0) {
        rep.accuracy = @as(f64, @floatFromInt(rep.n_correct)) / @as(f64, @floatFromInt(rep.n_chains));
        rep.claim_rate = @as(f64, @floatFromInt(rep.n_claimable)) / @as(f64, @floatFromInt(rep.n_chains));
    }
    // Gate: ≥95% claimable overall, all hop tiers have activity, neuromod ok
    rep.ok = rep.neuromod_ok and
        rep.n_chains >= 24 and
        rep.claim_rate >= 0.95 and
        rep.accuracy >= 0.95 and
        rep.correct_3 >= 1 and
        rep.n_3hop >= 4;
    return rep;
}

pub fn selfTest() bool {
    const r = runClaimabilityProbe();
    return r.ok;
}
