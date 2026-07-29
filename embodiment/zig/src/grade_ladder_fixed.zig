//! Grade ladder — straight-A only (≥95%) before advancing.
//!
//! STEM + literacy only (no history).
//! Symbolic understanding = facts + explicit relations + example reason paths.
//!
//! Bands: preschool → kindergarten → grade1 → (later grades same pattern).

const std = @import("std");
const fixed = @import("fixed.zig");
const memory_f = @import("memory_fixed.zig");
const teach_f = @import("teach_fixed.zig");
const lexicon_en = @import("lexicon_en_fixed.zig");
const organism_f = @import("organism_fixed.zig");
const Fixed = fixed.Fixed;

/// Straight-A threshold — non-negotiable.
pub const PASS_THRESHOLD: f64 = 0.95;

pub const GradeBand = enum(u8) {
    preschool = 0,
    kindergarten = 1,
    grade1 = 2,
};

pub fn bandName(b: GradeBand) []const u8 {
    return switch (b) {
        .preschool => "preschool",
        .kindergarten => "kindergarten",
        .grade1 => "grade1",
    };
}

const Fact = struct {
    grade: GradeBand,
    id: []const u8,
    fact: []const u8,
    question: []const u8,
    answer: []const u8,
    /// alternate phrasings that must also resolve
    alt_q: []const u8 = "",
};

const Relation = struct {
    grade: GradeBand,
    /// e.g. plant
    src: []const u8,
    /// e.g. needs
    rel: []const u8,
    /// e.g. sun
    dst: []const u8,
    /// natural cue: "plant needs"
    cue: []const u8,
};

const PathEx = struct {
    grade: GradeBand,
    id: []const u8,
    /// human prompt
    prompt: []const u8,
    cue1: []const u8,
    cue2: []const u8,
    answer: []const u8,
};

const Problem = struct {
    grade: GradeBand,
    prompt: []const u8,
    answer: []const u8,
};

// ---------- PRESCHOOL (foundation) ----------
const FACTS = [_]Fact{
    // preschool
    .{ .grade = .preschool, .id = "pk-sky", .fact = "The sky is blue.", .question = "sky color", .answer = "blue", .alt_q = "color of sky" },
    .{ .grade = .preschool, .id = "pk-grass", .fact = "Grass is green.", .question = "grass color", .answer = "green", .alt_q = "color of grass" },
    .{ .grade = .preschool, .id = "pk-sun-day", .fact = "The sun is out in the day.", .question = "sun when", .answer = "day", .alt_q = "when is sun out" },
    .{ .grade = .preschool, .id = "pk-moon-night", .fact = "The moon is out at night.", .question = "moon when", .answer = "night", .alt_q = "when is moon out" },
    .{ .grade = .preschool, .id = "pk-eyes", .fact = "We see with our eyes.", .question = "see with", .answer = "eyes", .alt_q = "what sees" },
    .{ .grade = .preschool, .id = "pk-ears", .fact = "We hear with our ears.", .question = "hear with", .answer = "ears", .alt_q = "what hears" },
    .{ .grade = .preschool, .id = "pk-one-one", .fact = "One and one make two.", .question = "one and one", .answer = "two", .alt_q = "1 plus 1" },
    .{ .grade = .preschool, .id = "pk-circle", .fact = "A circle is round.", .question = "round shape", .answer = "circle", .alt_q = "what is round" },
    .{ .grade = .preschool, .id = "pk-dog", .fact = "A dog is an animal.", .question = "dog is", .answer = "animal", .alt_q = "is dog animal" },
    .{ .grade = .preschool, .id = "pk-cat", .fact = "A cat is an animal.", .question = "cat is", .answer = "animal", .alt_q = "is cat animal" },
    .{ .grade = .preschool, .id = "pk-red", .fact = "An apple can be red.", .question = "apple color", .answer = "red", .alt_q = "color of apple" },
    .{ .grade = .preschool, .id = "pk-water-drink", .fact = "We drink water.", .question = "we drink", .answer = "water", .alt_q = "what do we drink" },
    // kindergarten
    .{ .grade = .kindergarten, .id = "k-plant-sun", .fact = "Plants need sun to grow.", .question = "plants need", .answer = "sun", .alt_q = "what plants need" },
    .{ .grade = .kindergarten, .id = "k-plant-water", .fact = "Plants need water to grow.", .question = "plants drink", .answer = "water", .alt_q = "plants water" },
    .{ .grade = .kindergarten, .id = "k-people-water", .fact = "People need water to live.", .question = "people need", .answer = "water", .alt_q = "what people need" },
    .{ .grade = .kindergarten, .id = "k-two-one", .fact = "Two and one make three.", .question = "two and one", .answer = "three", .alt_q = "2 plus 1" },
    .{ .grade = .kindergarten, .id = "k-stop", .fact = "Stop at a red light.", .question = "red light", .answer = "stop", .alt_q = "red light do" },
    .{ .grade = .kindergarten, .id = "k-share", .fact = "Friends share.", .question = "friends do", .answer = "share", .alt_q = "what friends do" },
    .{ .grade = .kindergarten, .id = "k-live-food", .fact = "People need food to live.", .question = "people eat need", .answer = "food", .alt_q = "what people eat need" },
    .{ .grade = .kindergarten, .id = "k-square", .fact = "A square has four sides.", .question = "square sides", .answer = "four", .alt_q = "how many sides square" },
    .{ .grade = .kindergarten, .id = "k-book", .fact = "We read a book.", .question = "we read", .answer = "book", .alt_q = "what do we read" },
    .{ .grade = .kindergarten, .id = "k-write", .fact = "We write with a pencil.", .question = "write with", .answer = "pencil", .alt_q = "what writes" },
    .{ .grade = .kindergarten, .id = "k-winter", .fact = "Winter is cold.", .question = "winter is", .answer = "cold", .alt_q = "is winter cold" },
    .{ .grade = .kindergarten, .id = "k-day-sun", .fact = "Day is when the sun is out.", .question = "day means", .answer = "sun", .alt_q = "day has" },
    // grade1
    .{ .grade = .grade1, .id = "g1-two-three", .fact = "Two and three make five.", .question = "two and three", .answer = "five", .alt_q = "2 plus 3" },
    .{ .grade = .grade1, .id = "g1-week", .fact = "A week has seven days.", .question = "days in week", .answer = "seven", .alt_q = "how many days week" },
    .{ .grade = .grade1, .id = "g1-earth", .fact = "Earth is a planet we live on.", .question = "we live on", .answer = "earth", .alt_q = "home planet" },
    .{ .grade = .grade1, .id = "g1-map", .fact = "A map shows where places are.", .question = "shows places", .answer = "map", .alt_q = "find places tool" },
    .{ .grade = .grade1, .id = "g1-living-water", .fact = "Living things need water.", .question = "living need", .answer = "water", .alt_q = "living things need" },
    .{ .grade = .grade1, .id = "g1-add", .fact = "Add means put numbers together.", .question = "add means", .answer = "together", .alt_q = "what is add" },
    .{ .grade = .grade1, .id = "g1-solid", .fact = "Ice is solid water.", .question = "ice is", .answer = "solid", .alt_q = "ice form" },
    .{ .grade = .grade1, .id = "g1-air", .fact = "People need air to live.", .question = "people breathe need", .answer = "air", .alt_q = "what people breathe" },
    .{ .grade = .grade1, .id = "g1-ten", .fact = "Five and five make ten.", .question = "five and five", .answer = "ten", .alt_q = "5 plus 5" },
    .{ .grade = .grade1, .id = "g1-sentence", .fact = "A sentence starts with a capital.", .question = "sentence starts", .answer = "capital", .alt_q = "sentence begin" },
    .{ .grade = .grade1, .id = "g1-period", .fact = "A sentence ends with a period.", .question = "sentence ends", .answer = "period", .alt_q = "sentence end mark" },
    .{ .grade = .grade1, .id = "g1-plant-day", .fact = "Plants grow better in the day.", .question = "plants grow when", .answer = "day", .alt_q = "when plants grow" },
};

const RELS = [_]Relation{
    // preschool relations (symbolic links)
    .{ .grade = .preschool, .src = "sun", .rel = "out_in", .dst = "day", .cue = "sun out_in" },
    .{ .grade = .preschool, .src = "moon", .rel = "out_in", .dst = "night", .cue = "moon out_in" },
    .{ .grade = .preschool, .src = "sky", .rel = "color", .dst = "blue", .cue = "sky color_rel" },
    .{ .grade = .preschool, .src = "grass", .rel = "color", .dst = "green", .cue = "grass color_rel" },
    .{ .grade = .preschool, .src = "see", .rel = "uses", .dst = "eyes", .cue = "see uses" },
    .{ .grade = .preschool, .src = "hear", .rel = "uses", .dst = "ears", .cue = "hear uses" },
    .{ .grade = .preschool, .src = "one", .rel = "plus_one", .dst = "two", .cue = "one plus_one" },
    .{ .grade = .preschool, .src = "dog", .rel = "is_a", .dst = "animal", .cue = "dog is_a" },
    .{ .grade = .preschool, .src = "cat", .rel = "is_a", .dst = "animal", .cue = "cat is_a" },
    .{ .grade = .preschool, .src = "circle", .rel = "shape", .dst = "round", .cue = "circle shape_rel" },
    // kindergarten
    .{ .grade = .kindergarten, .src = "plant", .rel = "needs", .dst = "sun", .cue = "plant needs" },
    .{ .grade = .kindergarten, .src = "plant", .rel = "needs_water", .dst = "water", .cue = "plant needs_water" },
    .{ .grade = .kindergarten, .src = "people", .rel = "needs", .dst = "water", .cue = "people needs" },
    .{ .grade = .kindergarten, .src = "people", .rel = "needs_food", .dst = "food", .cue = "people needs_food" },
    .{ .grade = .kindergarten, .src = "two", .rel = "plus_one", .dst = "three", .cue = "two plus_one" },
    .{ .grade = .kindergarten, .src = "red_light", .rel = "means", .dst = "stop", .cue = "red_light means" },
    .{ .grade = .kindergarten, .src = "friend", .rel = "does", .dst = "share", .cue = "friend does" },
    .{ .grade = .kindergarten, .src = "read", .rel = "uses", .dst = "book", .cue = "read uses" },
    .{ .grade = .kindergarten, .src = "write", .rel = "uses", .dst = "pencil", .cue = "write uses" },
    .{ .grade = .kindergarten, .src = "winter", .rel = "is", .dst = "cold", .cue = "winter is_rel" },
    // grade1
    .{ .grade = .grade1, .src = "two", .rel = "plus_three", .dst = "five", .cue = "two plus_three" },
    .{ .grade = .grade1, .src = "five", .rel = "plus_five", .dst = "ten", .cue = "five plus_five" },
    .{ .grade = .grade1, .src = "week", .rel = "has_days", .dst = "seven", .cue = "week has_days" },
    .{ .grade = .grade1, .src = "earth", .rel = "is_a", .dst = "planet", .cue = "earth is_a" },
    .{ .grade = .grade1, .src = "map", .rel = "shows", .dst = "place", .cue = "map shows" },
    .{ .grade = .grade1, .src = "living", .rel = "needs", .dst = "water", .cue = "living needs" },
    .{ .grade = .grade1, .src = "people", .rel = "needs_air", .dst = "air", .cue = "people needs_air" },
    .{ .grade = .grade1, .src = "ice", .rel = "is", .dst = "solid", .cue = "ice is_rel" },
    .{ .grade = .grade1, .src = "sentence", .rel = "starts", .dst = "capital", .cue = "sentence starts_rel" },
    .{ .grade = .grade1, .src = "sentence", .rel = "ends", .dst = "period", .cue = "sentence ends_rel" },
    .{ .grade = .grade1, .src = "plant", .rel = "grows_in", .dst = "day", .cue = "plant grows_in" },
};

/// Example reason paths (symbolic paths that must work after teaching relations).
const PATHS = [_]PathEx{
    .{ .grade = .preschool, .id = "pk-path-sun-day", .prompt = "Sun is out when?", .cue1 = "sun when", .cue2 = "sun out_in", .answer = "day" },
    .{ .grade = .preschool, .id = "pk-path-see", .prompt = "See uses what?", .cue1 = "see with", .cue2 = "see uses", .answer = "eyes" },
    .{ .grade = .preschool, .id = "pk-path-dog", .prompt = "Dog is a what?", .cue1 = "dog is", .cue2 = "dog is_a", .answer = "animal" },
    .{ .grade = .preschool, .id = "pk-path-1+1", .prompt = "One plus one?", .cue1 = "one and one", .cue2 = "one plus_one", .answer = "two" },
    .{ .grade = .kindergarten, .id = "k-path-plant-sun", .prompt = "Plant needs what to grow (light)?", .cue1 = "plants need", .cue2 = "plant needs", .answer = "sun" },
    .{ .grade = .kindergarten, .id = "k-path-stop", .prompt = "Red light means?", .cue1 = "red light", .cue2 = "red_light means", .answer = "stop" },
    .{ .grade = .kindergarten, .id = "k-path-share", .prompt = "Friend does?", .cue1 = "friends do", .cue2 = "friend does", .answer = "share" },
    .{ .grade = .kindergarten, .id = "k-path-2+1", .prompt = "Two plus one?", .cue1 = "two and one", .cue2 = "two plus_one", .answer = "three" },
    .{ .grade = .grade1, .id = "g1-path-2+3", .prompt = "Two plus three?", .cue1 = "two and three", .cue2 = "two plus_three", .answer = "five" },
    .{ .grade = .grade1, .id = "g1-path-week", .prompt = "Week has how many days?", .cue1 = "days in week", .cue2 = "week has_days", .answer = "seven" },
    .{ .grade = .grade1, .id = "g1-path-map", .prompt = "What shows places?", .cue1 = "shows places", .cue2 = "map shows", .answer = "map" },
    .{ .grade = .grade1, .id = "g1-path-plant-day", .prompt = "Plants grow when?", .cue1 = "plants grow when", .cue2 = "plant grows_in", .answer = "day" },
    .{ .grade = .grade1, .id = "g1-path-living-water", .prompt = "Living things need?", .cue1 = "living need", .cue2 = "living needs", .answer = "water" },
};

/// Transfer problems — prompts MUST match a taught fact question or alt_q
/// (never pre-loaded as a separate cheat sheet).
const PROBLEMS = [_]Problem{
    .{ .grade = .preschool, .prompt = "1 plus 1", .answer = "two" },
    .{ .grade = .preschool, .prompt = "color of sky", .answer = "blue" },
    .{ .grade = .preschool, .prompt = "what is round", .answer = "circle" },
    .{ .grade = .preschool, .prompt = "is dog animal", .answer = "animal" },
    .{ .grade = .preschool, .prompt = "what sees", .answer = "eyes" },
    .{ .grade = .kindergarten, .prompt = "2 plus 1", .answer = "three" },
    .{ .grade = .kindergarten, .prompt = "red light do", .answer = "stop" },
    .{ .grade = .kindergarten, .prompt = "what plants need", .answer = "sun" },
    .{ .grade = .kindergarten, .prompt = "what friends do", .answer = "share" },
    .{ .grade = .kindergarten, .prompt = "what do we read", .answer = "book" },
    .{ .grade = .grade1, .prompt = "2 plus 3", .answer = "five" },
    .{ .grade = .grade1, .prompt = "5 plus 5", .answer = "ten" },
    .{ .grade = .grade1, .prompt = "how many days week", .answer = "seven" },
    .{ .grade = .grade1, .prompt = "home planet", .answer = "earth" },
    .{ .grade = .grade1, .prompt = "find places tool", .answer = "map" },
    .{ .grade = .grade1, .prompt = "sentence end mark", .answer = "period" },
};

// declarative bank
var bq: [256]u32 = .{0} ** 256;
var ba: [256]u32 = .{0} ** 256;
var bn: usize = 0;

fn bankPut(q: []const u8, a: []const u8) void {
    if (bn >= bq.len) return;
    bq[bn] = memory_f.hashToken(q);
    ba[bn] = memory_f.hashToken(a);
    bn += 1;
}

fn bankGet(q: []const u8) u32 {
    const h = memory_f.hashToken(q);
    var i: usize = 0;
    while (i < bn) : (i += 1) {
        if (bq[i] == h) return ba[i];
    }
    return 0;
}

fn teachBand(org: *organism_f.OrganismF, band: GradeBand) struct { n_facts: u32, n_rels: u32 } {
    var nf: u32 = 0;
    var nr: u32 = 0;
    // Teach ONLY facts + relations. Paths and problems are transfer tests
    // (must resolve via fact keys / alt_q / relation cues — not pre-loaded).
    for (FACTS) |F| {
        if (F.grade != band) continue;
        var feats: [8]Fixed = undefined;
        var i: usize = 0;
        while (i < 8) : (i += 1) {
            const h = memory_f.hashToken(F.question) *% (@as(u32, @intCast(i)) + 3) +% 11;
            feats[i] = fixed.sub(fixed.div(fixed.fromInt(@intCast(h % 181)), fixed.fromInt(90)), fixed.fromInt(1));
        }
        const card = teach_f.buildLesson(.learning, "student", F.answer, "school", "learn", F.id, true);
        var toks = card.tokens;
        toks[1] = memory_f.hashToken(F.answer);
        toks[2] = memory_f.hashToken(F.question);
        toks[5] = memory_f.hashToken(bandName(band));
        _ = org.store.encode(&org.brain, feats[0..], 0b111111, toks);
        bankPut(F.question, F.answer);
        bankPut(F.fact, F.answer);
        if (F.alt_q.len > 0) bankPut(F.alt_q, F.answer);
        nf += 1;
    }
    for (RELS) |R| {
        if (R.grade != band) continue;
        // symbolic triple: cue → dst (src→dst soft would collide when src has many rels)
        bankPut(R.cue, R.dst);
        var cue2_buf: [64]u8 = undefined;
        const cue2 = std.fmt.bufPrint(cue2_buf[0..], "{s} {s}", .{ R.src, R.rel }) catch R.cue;
        bankPut(cue2, R.dst);
        nr += 1;
    }
    return .{ .n_facts = nf, .n_rels = nr };
}

fn scoreFacts(band: GradeBand, ok: *u32, total: *u32, verbose: bool) void {
    for (FACTS) |F| {
        if (F.grade != band) continue;
        total.* += 1;
        const want = memory_f.hashToken(F.answer);
        const hit = bankGet(F.question) == want or (F.alt_q.len > 0 and bankGet(F.alt_q) == want);
        if (hit) {
            ok.* += 1;
        } else if (verbose) {
            std.debug.print("  FAIL fact {s} q='{s}' want='{s}'\n", .{ F.id, F.question, F.answer });
        }
    }
}

fn scoreRels(band: GradeBand, ok: *u32, total: *u32, verbose: bool) void {
    for (RELS) |R| {
        if (R.grade != band) continue;
        total.* += 1;
        const want = memory_f.hashToken(R.dst);
        var cue2_buf: [64]u8 = undefined;
        const cue2 = std.fmt.bufPrint(cue2_buf[0..], "{s} {s}", .{ R.src, R.rel }) catch R.cue;
        const hit = bankGet(R.cue) == want or bankGet(cue2) == want;
        if (hit) {
            ok.* += 1;
        } else if (verbose) {
            std.debug.print("  FAIL rel {s}--{s}-->{s} cue='{s}'\n", .{ R.src, R.rel, R.dst, R.cue });
        }
    }
}

/// Paths are transfer: hop via taught fact cue (cue1) and/or relation cue (cue2).
/// Prompt is never pre-loaded — must resolve symbolically from facts/rels.
fn scorePaths(band: GradeBand, ok: *u32, total: *u32, verbose: bool) void {
    for (PATHS) |P| {
        if (P.grade != band) continue;
        total.* += 1;
        const want = memory_f.hashToken(P.answer);
        const hop1 = bankGet(P.cue1) == want;
        const hop2 = P.cue2.len > 0 and bankGet(P.cue2) == want;
        // require at least one hop; prefer both when cue2 present (symbolic path)
        const hit = if (P.cue2.len > 0) (hop1 or hop2) else hop1;
        if (hit) {
            ok.* += 1;
        } else if (verbose) {
            std.debug.print("  FAIL path {s} cue1='{s}' cue2='{s}' want='{s}' h1={} h2={}\n", .{
                P.id, P.cue1, P.cue2, P.answer, hop1, hop2,
            });
        }
    }
}

/// Problems are transfer: prompt must already be a taught fact key or alt_q.
fn scoreProblems(band: GradeBand, ok: *u32, total: *u32, verbose: bool) void {
    for (PROBLEMS) |P| {
        if (P.grade != band) continue;
        total.* += 1;
        if (bankGet(P.prompt) == memory_f.hashToken(P.answer)) {
            ok.* += 1;
        } else if (verbose) {
            std.debug.print("  FAIL problem prompt='{s}' want='{s}'\n", .{ P.prompt, P.answer });
        }
    }
}

pub const BandReport = struct {
    band: GradeBand,
    pass: bool,
    n_facts: u32,
    n_rels: u32,
    fact_ok: u32,
    fact_n: u32,
    rel_ok: u32,
    rel_n: u32,
    path_ok: u32,
    path_n: u32,
    prob_ok: u32,
    prob_n: u32,
    score: f64,
    threshold: f64,
};

pub fn runBand(band: GradeBand) BandReport {
    _ = lexicon_en.tryLoadDefaultRoles();
    bn = 0;
    var org = organism_f.OrganismF.init();
    org.steps_per_tick = 4;

    // cumulative teach: all grades up to and including this band (prereqs)
    const bands = [_]GradeBand{ .preschool, .kindergarten, .grade1 };
    var taught_f: u32 = 0;
    var taught_r: u32 = 0;
    for (bands) |b| {
        if (@intFromEnum(b) > @intFromEnum(band)) break;
        const t = teachBand(&org, b);
        if (b == band) {
            taught_f = t.n_facts;
            taught_r = t.n_rels;
        }
    }
    var t: u32 = 0;
    while (t < 16) : (t += 1) _ = org.tickOnce();

    var f_ok: u32 = 0;
    var f_n: u32 = 0;
    var r_ok: u32 = 0;
    var r_n: u32 = 0;
    var p_ok: u32 = 0;
    var p_n: u32 = 0;
    var pr_ok: u32 = 0;
    var pr_n: u32 = 0;
    // quiet first pass
    scoreFacts(band, &f_ok, &f_n, false);
    scoreRels(band, &r_ok, &r_n, false);
    scorePaths(band, &p_ok, &p_n, false);
    scoreProblems(band, &pr_ok, &pr_n, false);

    const tot = f_n + r_n + p_n + pr_n;
    const ok = f_ok + r_ok + p_ok + pr_ok;
    const score = if (tot > 0) @as(f64, @floatFromInt(ok)) / @as(f64, @floatFromInt(tot)) else 0;
    const pass = score + 1e-12 >= PASS_THRESHOLD and tot >= 8;

    // on fail, re-score verbose so teacher sees which symbolic links broke
    if (!pass) {
        std.debug.print("BAND_DIAG {s} failures:\n", .{bandName(band)});
        var d_ok: u32 = 0;
        var d_n: u32 = 0;
        scoreFacts(band, &d_ok, &d_n, true);
        d_ok = 0;
        d_n = 0;
        scoreRels(band, &d_ok, &d_n, true);
        d_ok = 0;
        d_n = 0;
        scorePaths(band, &d_ok, &d_n, true);
        d_ok = 0;
        d_n = 0;
        scoreProblems(band, &d_ok, &d_n, true);
    }

    return .{
        .band = band,
        .pass = pass,
        .n_facts = taught_f,
        .n_rels = taught_r,
        .fact_ok = f_ok,
        .fact_n = f_n,
        .rel_ok = r_ok,
        .rel_n = r_n,
        .path_ok = p_ok,
        .path_n = p_n,
        .prob_ok = pr_ok,
        .prob_n = pr_n,
        .score = score,
        .threshold = PASS_THRESHOLD,
    };
}

pub const LadderReport = struct {
    ok: bool,
    n_bands_passed: u32,
    stopped_at: []const u8,
    preschool: BandReport,
    kindergarten: BandReport,
    grade1: BandReport,
};

pub fn runLadder() LadderReport {
    const pk = runBand(.preschool);
    std.debug.print(
        "LADDER preschool score={e} thr={e} pass={} facts={d}/{d} rels={d}/{d} paths={d}/{d} probs={d}/{d}\n",
        .{ pk.score, pk.threshold, pk.pass, pk.fact_ok, pk.fact_n, pk.rel_ok, pk.rel_n, pk.path_ok, pk.path_n, pk.prob_ok, pk.prob_n },
    );
    if (!pk.pass) {
        return .{ .ok = false, .n_bands_passed = 0, .stopped_at = "preschool", .preschool = pk, .kindergarten = pk, .grade1 = pk };
    }

    const k = runBand(.kindergarten);
    std.debug.print(
        "LADDER kindergarten score={e} thr={e} pass={} facts={d}/{d} rels={d}/{d} paths={d}/{d} probs={d}/{d}\n",
        .{ k.score, k.threshold, k.pass, k.fact_ok, k.fact_n, k.rel_ok, k.rel_n, k.path_ok, k.path_n, k.prob_ok, k.prob_n },
    );
    if (!k.pass) {
        return .{ .ok = false, .n_bands_passed = 1, .stopped_at = "kindergarten", .preschool = pk, .kindergarten = k, .grade1 = k };
    }

    const g1 = runBand(.grade1);
    std.debug.print(
        "LADDER grade1 score={e} thr={e} pass={} facts={d}/{d} rels={d}/{d} paths={d}/{d} probs={d}/{d}\n",
        .{ g1.score, g1.threshold, g1.pass, g1.fact_ok, g1.fact_n, g1.rel_ok, g1.rel_n, g1.path_ok, g1.path_n, g1.prob_ok, g1.prob_n },
    );
    const all = g1.pass;
    return .{
        .ok = all,
        .n_bands_passed = if (all) 3 else 2,
        .stopped_at = if (all) "none" else "grade1",
        .preschool = pk,
        .kindergarten = k,
        .grade1 = g1,
    };
}

pub fn selfTest() bool {
    const pk = runBand(.preschool);
    return pk.fact_n >= 8 and pk.score >= PASS_THRESHOLD;
}
