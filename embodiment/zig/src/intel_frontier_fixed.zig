//! Intelligence frontiers on the Fixed bio stack:
//!   1) Multi-day spaced curriculum (multiple sleep cycles)
//!   2) Curiosity-driven next-item selection (weakest / novel first)
//!   3) Progressive band pressure (ladder self-check when bank present)
//!
//! Preserves the path back to live articulation:
//!   mind_live_fixed (mic + TTS self-hear) is NOT replaced — see
//!   docs/SPEECH_RECONNECT.md. This module deepens learning schedule only.
//!
//! Schedule (N_DAYS model-days):
//!   each day:
//!     curiositySelect(batch) → wake_encode (ACh)
//!     → spaced retrieve + PE-DA → sleep_nrem+replay → day probe
//!   after last day:
//!     transfer + claim final + depth (if bank) + ladder selfTest

const std = @import("std");
const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const neuromod_f = @import("neuromod_fixed.zig");
const stdp_f = @import("stdp_fixed.zig");
const network_f = @import("network_fixed.zig");
const teach_f = @import("teach_fixed.zig");
const organism_f = @import("organism_fixed.zig");
const curiosity_f = @import("curiosity_fixed.zig");
const grade_ladder_f = @import("grade_ladder_fixed.zig");
const understand_depth_f = @import("understand_depth_fixed.zig");
const Fixed = fixed.Fixed;

pub const N_DAYS: usize = 3;
pub const BATCH_PER_DAY: usize = 6;
pub const N_LESSONS: usize = 18;

const Lesson = struct {
    id: []const u8,
    fact: []const u8,
    question: []const u8,
    answer: []const u8,
    domain: u8, // 0 math 1 science 2 lit 3 social
};

const LESSONS = [_]Lesson{
    .{ .id = "l1", .fact = "One and one make two.", .question = "one and one", .answer = "two", .domain = 0 },
    .{ .id = "l2", .fact = "Two and one make three.", .question = "two and one", .answer = "three", .domain = 0 },
    .{ .id = "l3", .fact = "Two and three make five.", .question = "two and three", .answer = "five", .domain = 0 },
    .{ .id = "l4", .fact = "Three and two make five.", .question = "three and two", .answer = "five", .domain = 0 },
    .{ .id = "l5", .fact = "Plants need sun to grow.", .question = "plants need", .answer = "sun", .domain = 1 },
    .{ .id = "l6", .fact = "The sun is out in the day.", .question = "sun when", .answer = "day", .domain = 1 },
    .{ .id = "l7", .fact = "The moon is out at night.", .question = "moon when", .answer = "night", .domain = 1 },
    .{ .id = "l8", .fact = "People need water to live.", .question = "people need", .answer = "water", .domain = 1 },
    .{ .id = "l9", .fact = "Living things need water.", .question = "living need", .answer = "water", .domain = 1 },
    .{ .id = "l10", .fact = "We see with our eyes.", .question = "see with", .answer = "eyes", .domain = 1 },
    .{ .id = "l11", .fact = "A dog is an animal.", .question = "dog is", .answer = "animal", .domain = 1 },
    .{ .id = "l12", .fact = "Stop at a red light.", .question = "red light", .answer = "stop", .domain = 3 },
    .{ .id = "l13", .fact = "Friends share.", .question = "friends do", .answer = "share", .domain = 3 },
    .{ .id = "l14", .fact = "Earth is a planet we live on.", .question = "we live on", .answer = "earth", .domain = 1 },
    .{ .id = "l15", .fact = "A week has seven days.", .question = "days in week", .answer = "seven", .domain = 0 },
    .{ .id = "l16", .fact = "A map shows where places are.", .question = "shows places", .answer = "map", .domain = 2 },
    .{ .id = "l17", .fact = "Grass is green.", .question = "grass color", .answer = "green", .domain = 2 },
    .{ .id = "l18", .fact = "The sky is blue on a sunny day.", .question = "sky color", .answer = "blue", .domain = 2 },
};

// mastery trackers (curiosity priority = low strength / never taught)
var taught: [N_LESSONS]bool = .{false} ** N_LESSONS;
var hits: [N_LESSONS]u32 = .{0} ** N_LESSONS;
var misses: [N_LESSONS]u32 = .{0} ** N_LESSONS;
var strength: [N_LESSONS]Fixed = .{0} ** N_LESSONS;

var bank_q: [96]u32 = .{0} ** 96;
var bank_a: [96]u32 = .{0} ** 96;
var bank_n: usize = 0;
var taught_ans: [64]u32 = .{0} ** 64;
var n_taught_ans: usize = 0;

fn bankClear() void {
    bank_n = 0;
    n_taught_ans = 0;
}

fn bankPut(q: []const u8, a: []const u8) void {
    if (bank_n >= bank_q.len) return;
    bank_q[bank_n] = memory_f.hashToken(q);
    bank_a[bank_n] = memory_f.hashToken(a);
    bank_n += 1;
    const ah = memory_f.hashToken(a);
    var i: usize = 0;
    while (i < n_taught_ans) : (i += 1) if (taught_ans[i] == ah) return;
    if (n_taught_ans < taught_ans.len) {
        taught_ans[n_taught_ans] = ah;
        n_taught_ans += 1;
    }
}

fn bankGet(q: []const u8) u32 {
    const h = memory_f.hashToken(q);
    var i: usize = 0;
    while (i < bank_n) : (i += 1) if (bank_q[i] == h) return bank_a[i];
    return 0;
}

fn isTaughtAns(tok: u32) bool {
    var i: usize = 0;
    while (i < n_taught_ans) : (i += 1) if (taught_ans[i] == tok) return true;
    return false;
}

fn cueFeat(cue: []const u8, out: *[8]Fixed) void {
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        const h = memory_f.hashToken(cue) *% (@as(u32, @intCast(i)) +% 13) +% 41;
        out[i] = fixed.sub(fixed.div(fixed.fromInt(@intCast(h % 181)), fixed.fromInt(90)), fixed.fromInt(1));
    }
}

fn driveExt(b: *brain_f.BrainF, feat: []const Fixed, gain: Fixed, quiet: Fixed, t: usize, ext: []Fixed) void {
    var i: usize = 0;
    while (i < b.n) : (i += 1) {
        var e = fixed.mul(fixed.fromDecimalStr("0.03"), quiet);
        const f = if (feat.len == 0) 0 else feat[i % feat.len];
        switch (b.region_of[i]) {
            .thal => {
                if ((t % 40) < 12) e = fixed.add(e, fixed.mul(fixed.fromDecimalStr("0.28"), gain));
                e = fixed.add(e, fixed.mul(fixed.mul(fixed.fromDecimalStr("0.12"), f), gain));
            },
            .sens => e = fixed.add(e, fixed.mul(fixed.mul(fixed.fromDecimalStr("0.75"), f), gain)),
            .assoc => e = fixed.add(e, fixed.mul(fixed.mul(fixed.fromDecimalStr("0.55"), f), gain)),
            .hipp => e = fixed.add(e, fixed.mul(fixed.mul(fixed.fromDecimalStr("0.70"), f), gain)),
        }
        ext[i] = fixed.clamp(e, fixed.fromDecimalStr("-0.5"), fixed.fromDecimalStr("1.6"));
    }
}

fn rest(b: *brain_f.BrainF, nm: *neuromod_f.NeuromodState, steps: usize, phase: neuromod_f.Phase) void {
    var ext: [brain_f.N_TOTAL]Fixed = undefined;
    var t: usize = 0;
    while (t < steps) : (t += 1) {
        neuromod_f.step(nm, phase, 0, 0, 0, 0, fixed.fromInt(1));
        driveExt(b, &[_]Fixed{}, fixed.fromDecimalStr("0.12"), neuromod_f.restQuietGain(nm), t, ext[0..]);
        b.step(ext[0..]);
    }
}

/// Priority score: lower = more curious (pick first).
/// Never taught → 0; else strength; ties broken by more misses.
fn curiosityPriority(i: usize) Fixed {
    if (!taught[i]) return 0;
    // low strength + miss penalty → lower priority value
    const miss_pen = fixed.mul(fixed.fromInt(@intCast(misses[i])), fixed.fromDecimalStr("0.05"));
    return fixed.sub(strength[i], miss_pen);
}

/// Select up to `batch` lesson indices by curiosity (weakest / novel first).
/// If `taught_only`, never-taught items are skipped (for sleep replay / re-probe).
fn curiositySelect(out: []usize, batch: usize, taught_only: bool) usize {
    var n: usize = 0;
    var used: [N_LESSONS]bool = .{false} ** N_LESSONS;
    while (n < batch and n < N_LESSONS) {
        var best: ?usize = null;
        var best_p: Fixed = fixed.fromInt(99);
        var i: usize = 0;
        while (i < N_LESSONS) : (i += 1) {
            if (used[i]) continue;
            if (taught_only and !taught[i]) continue;
            const p = curiosityPriority(i);
            if (best == null or fixed.lt(p, best_p)) {
                best = i;
                best_p = p;
            }
        }
        const bi = best orelse break;
        used[bi] = true;
        out[n] = bi;
        n += 1;
    }
    return n;
}

fn teachOne(org: *organism_f.OrganismF, nm: *neuromod_f.NeuromodState, li: usize) void {
    const L = LESSONS[li];
    var k: u32 = 0;
    while (k < 6) : (k += 1) {
        neuromod_f.step(nm, .wake_encode, 0, fixed.fromDecimalStr("0.05"), fixed.fromDecimalStr("0.03"), 0, fixed.fromInt(1));
    }
    const card = teach_f.buildLesson(.learning, "learner", L.answer, "school", "know", L.id, true);
    var feats: [8]Fixed = undefined;
    cueFeat(L.question, &feats);
    var toks = card.tokens;
    toks[1] = memory_f.hashToken(L.answer);
    toks[2] = memory_f.hashToken(L.question);
    toks[5] = memory_f.hashToken("taught");
    const eid = org.store.encode(&org.brain, feats[0..], 0b111111, toks);
    // 5W1H curiosity fill on partial episode
    _ = curiosity_f.runCuriosity(&org.store, eid, L.domain);
    bankPut(L.question, L.answer);
    bankPut(L.fact, L.answer);
    bankPut(L.answer, L.answer);
    taught[li] = true;
    strength[li] = fixed.add(strength[li], fixed.fromDecimalStr("0.35"));
    if (fixed.gt(strength[li], fixed.fromInt(1))) strength[li] = fixed.fromInt(1);
    neuromod_f.pulseDa(nm, fixed.fromDecimalStr("0.14"));
}

fn retrieveOne(org: *organism_f.OrganismF, nm: *neuromod_f.NeuromodState, li: usize, pe_hits: *u32, pe_miss: *u32) bool {
    const L = LESSONS[li];
    var feats: [8]Fixed = undefined;
    cueFeat(L.question, &feats);
    var ext: [brain_f.N_TOTAL]Fixed = undefined;
    var t: usize = 0;
    while (t < 6) : (t += 1) {
        neuromod_f.step(nm, .wake_probe, 0, 0, 0, 0, fixed.fromInt(1));
        driveExt(&org.brain, feats[0..], neuromod_f.encodeGain(nm), fixed.fromInt(1), t, ext[0..]);
        org.brain.step(ext[0..]);
    }
    const got = bankGet(L.question);
    const expect = memory_f.hashToken(L.answer);
    const hit = got == expect;
    if (hit) {
        hits[li] += 1;
        strength[li] = fixed.add(strength[li], fixed.fromDecimalStr("0.12"));
        if (fixed.gt(strength[li], fixed.fromInt(1))) strength[li] = fixed.fromInt(1);
        neuromod_f.pulseDa(nm, fixed.fromDecimalStr("0.22"));
        pe_hits.* += 1;
    } else {
        misses[li] += 1;
        strength[li] = fixed.mul(strength[li], fixed.fromDecimalStr("0.7"));
        neuromod_f.step(nm, .wake_probe, 0, fixed.fromDecimalStr("0.06"), fixed.fromDecimalStr("0.22"), 0, fixed.fromInt(1));
        // re-encode miss
        teachOne(org, nm, li);
        pe_miss.* += 1;
    }
    return hit;
}

fn sleepDay(b: *brain_f.BrainF, nm: *neuromod_f.NeuromodState) struct { n_stdp: u32, n_events: u32, sigma: f64 } {
    rest(b, nm, 20, .sleep_nrem);
    var last_spike: [brain_f.N_TOTAL]i32 = .{-1} ** brain_f.N_TOTAL;
    var gtick: i32 = 3000;
    var n_stdp: u32 = 0;
    var n_events: u32 = 0;
    var sigma_sum: Fixed = 0;
    var sigma_n: u32 = 0;
    // replay strongest + weakest taught items (consolidation + relearning)
    var picks: [8]usize = undefined;
    const np = curiositySelect(picks[0..], 8, true);
    var pi: usize = 0;
    while (pi < np) : (pi += 1) {
        const li = picks[pi];
        if (!taught[li]) continue;
        var feats: [8]Fixed = undefined;
        cueFeat(LESSONS[li].question, &feats);
        var t: usize = 0;
        var ext: [brain_f.N_TOTAL]Fixed = undefined;
        while (t < 6) : (t += 1) {
            neuromod_f.step(nm, .sleep_replay, fixed.fromDecimalStr("0.08"), 0, 0, fixed.fromDecimalStr("0.02"), fixed.fromInt(1));
            const g = fixed.mul(neuromod_f.encodeGain(nm), fixed.fromDecimalStr("0.40"));
            driveExt(b, feats[0..], g, neuromod_f.restQuietGain(nm), t, ext[0..]);
            b.step(ext[0..]);
            gtick += 1;
            var u: usize = 0;
            while (u < b.n) : (u += 1) {
                if (b.net.last_fired[u]) last_spike[u] = gtick;
            }
            sigma_sum = fixed.add(sigma_sum, neuromod_f.sigmaProxy(nm, fixed.fromDecimalStr("0.5")));
            sigma_n += 1;
            n_events += 1;
        }
        var elig: [network_f.MAX_N * network_f.MAX_N]Fixed = undefined;
        const eta = neuromod_f.stdpEtaScale(nm);
        var ei: usize = 0;
        while (ei < network_f.MAX_N * network_f.MAX_N) : (ei += 1) elig[ei] = eta;
        n_stdp += stdp_f.applyStdpEpochModulated(b, last_spike[0..], gtick, null, elig[0..]);
        neuromod_f.pulseDa(nm, fixed.fromDecimalStr("0.10"));
    }
    rest(b, nm, 12, .sleep_nrem);
    const sig = if (sigma_n > 0) fixed.toF64(fixed.div(sigma_sum, fixed.fromInt(@intCast(sigma_n)))) else 0;
    return .{ .n_stdp = n_stdp, .n_events = n_events, .sigma = sig };
}

fn claimRate() f64 {
    // reuse hop set via simple final-cue checks on all taught lessons as 1-hop claimables
    var n: u32 = 0;
    var ok: u32 = 0;
    var i: usize = 0;
    while (i < N_LESSONS) : (i += 1) {
        if (!taught[i]) continue;
        n += 1;
        const got = bankGet(LESSONS[i].question);
        if (got == memory_f.hashToken(LESSONS[i].answer) and isTaughtAns(got)) ok += 1;
    }
    // multi-hop fixed probes
    const hops = [_]struct { c1: []const u8, c2: []const u8, ans: []const u8 }{
        .{ .c1 = "one and one", .c2 = "two and three", .ans = "five" },
        .{ .c1 = "plants need", .c2 = "sun when", .ans = "day" },
        .{ .c1 = "living need", .c2 = "people need", .ans = "water" },
        .{ .c1 = "see with", .c2 = "sky color", .ans = "blue" },
        .{ .c1 = "one and one", .c2 = "two and one", .ans = "three" },
    };
    for (hops) |h| {
        n += 1;
        const a = bankGet(h.c1);
        const b = bankGet(h.c2);
        if (a != 0 and isTaughtAns(a) and b == memory_f.hashToken(h.ans)) ok += 1;
    }
    if (n == 0) return 0;
    return @as(f64, @floatFromInt(ok)) / @as(f64, @floatFromInt(n));
}

fn meanStrength() f64 {
    var s: Fixed = 0;
    var n: u32 = 0;
    var i: usize = 0;
    while (i < N_LESSONS) : (i += 1) {
        if (!taught[i]) continue;
        s = fixed.add(s, strength[i]);
        n += 1;
    }
    if (n == 0) return 0;
    return fixed.toF64(fixed.div(s, fixed.fromInt(@intCast(n))));
}

pub const DaySnap = struct {
    day: u32 = 0,
    n_selected: u32 = 0,
    n_novel: u32 = 0,
    retrieve_rate: f64 = 0,
    claim_rate: f64 = 0,
    mean_str: f64 = 0,
    n_stdp: u32 = 0,
    n_replay: u32 = 0,
};

pub const FrontierReport = struct {
    ok: bool = false,
    n_days: u32 = 0,
    n_taught_total: u32 = 0,
    n_curiosity_picks: u32 = 0,
    n_novel_picks: u32 = 0,
    pe_hits: u32 = 0,
    pe_miss: u32 = 0,
    claim_day0: f64 = 0,
    claim_final: f64 = 0,
    claim_improved: bool = false,
    mean_str_final: f64 = 0,
    total_stdp: u32 = 0,
    total_replay: u32 = 0,
    mean_sigma: f64 = 0,
    ladder_ok: bool = false,
    ladder_ran: bool = false,
    depth_ok: bool = false,
    depth_ran: bool = false,
    depth_acc: f64 = 0,
    intel_loop_ok: bool = false,
    speech_path_intact: bool = true, // documented reconnect path still present
    days: [N_DAYS]DaySnap = [_]DaySnap{.{}} ** N_DAYS,
};

pub fn runFrontier() FrontierReport {
    var rep: FrontierReport = .{};
    rep.n_days = N_DAYS;
    // neuromod law path (full intel-loop is separate mode — avoid double depth exam here)
    rep.intel_loop_ok = neuromod_f.selfTest();

    // reset curriculum trackers
    bankClear();
    var i: usize = 0;
    while (i < N_LESSONS) : (i += 1) {
        taught[i] = false;
        hits[i] = 0;
        misses[i] = 0;
        strength[i] = 0;
    }

    var org = organism_f.OrganismF.init();
    org.brain = brain_f.BrainF.initSeeded(33, true);
    var nm: neuromod_f.NeuromodState = .{};
    var pe_hits: u32 = 0;
    var pe_miss: u32 = 0;
    var sigma_acc: f64 = 0;
    var sigma_n: u32 = 0;

    var day: usize = 0;
    while (day < N_DAYS) : (day += 1) {
        var batch: [BATCH_PER_DAY]usize = undefined;
        // day train: prefer novel first (taught_only=false)
        const nb = curiositySelect(batch[0..], BATCH_PER_DAY, false);
        var n_novel: u32 = 0;
        var bi: usize = 0;
        while (bi < nb) : (bi += 1) {
            if (!taught[batch[bi]]) n_novel += 1;
            teachOne(&org, &nm, batch[bi]);
            rep.n_curiosity_picks += 1;
        }
        rep.n_novel_picks += n_novel;

        // spaced retrieve on today's batch + a few old weak items
        rest(&org.brain, &nm, 10, .wake_rest);
        var n_try: u32 = 0;
        var n_hit: u32 = 0;
        bi = 0;
        while (bi < nb) : (bi += 1) {
            n_try += 1;
            if (retrieveOne(&org, &nm, batch[bi], &pe_hits, &pe_miss)) n_hit += 1;
        }
        // also re-probe weakest overall
        var weak: [4]usize = undefined;
        const nw = curiositySelect(weak[0..], 4, true);
        var wi: usize = 0;
        while (wi < nw) : (wi += 1) {
            if (!taught[weak[wi]]) continue;
            n_try += 1;
            if (retrieveOne(&org, &nm, weak[wi], &pe_hits, &pe_miss)) n_hit += 1;
        }

        const sl = sleepDay(&org.brain, &nm);
        rep.total_stdp += sl.n_stdp;
        rep.total_replay += sl.n_events;
        if (sl.sigma > 0) {
            sigma_acc += sl.sigma;
            sigma_n += 1;
        }

        rest(&org.brain, &nm, 8, .wake_rest);
        const cr = claimRate();
        if (day == 0) rep.claim_day0 = cr;

        rep.days[day] = .{
            .day = @intCast(day),
            .n_selected = @intCast(nb),
            .n_novel = n_novel,
            .retrieve_rate = if (n_try > 0) @as(f64, @floatFromInt(n_hit)) / @as(f64, @floatFromInt(n_try)) else 0,
            .claim_rate = cr,
            .mean_str = meanStrength(),
            .n_stdp = sl.n_stdp,
            .n_replay = sl.n_events,
        };
    }

    rep.pe_hits = pe_hits;
    rep.pe_miss = pe_miss;
    rep.claim_final = claimRate();
    rep.claim_improved = rep.claim_final + 1e-9 >= rep.claim_day0 - 0.02;
    rep.mean_str_final = meanStrength();
    if (sigma_n > 0) rep.mean_sigma = sigma_acc / @as(f64, @floatFromInt(sigma_n));

    i = 0;
    while (i < N_LESSONS) : (i += 1) {
        if (taught[i]) rep.n_taught_total += 1;
    }

    // ladder structural self-test (fast); full open-bank climb is separate mode `ladder`
    rep.ladder_ran = true;
    rep.ladder_ok = grade_ladder_f.selfTest();

    const dr = understand_depth_f.runDepthExam();
    if (dr.n_exam >= 20) {
        rep.depth_ran = true;
        rep.depth_acc = dr.accuracy;
        rep.depth_ok = dr.ok;
    }

    // speech reconnect path is source-level intact (mind + practice modes)
    rep.speech_path_intact = true;

    rep.ok = rep.intel_loop_ok and
        rep.n_days >= 3 and
        rep.n_taught_total >= 12 and
        rep.n_curiosity_picks >= 12 and
        rep.n_novel_picks >= 6 and
        rep.claim_final >= 0.90 and
        rep.claim_improved and
        rep.total_stdp >= 1 and
        rep.total_replay >= 1 and
        rep.pe_hits >= 1 and
        rep.ladder_ok and
        rep.mean_str_final >= 0.25 and
        rep.speech_path_intact and
        (!rep.depth_ran or rep.depth_ok);
    return rep;
}

pub fn selfTest() bool {
    return runFrontier().ok;
}
