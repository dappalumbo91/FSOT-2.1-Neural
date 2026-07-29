//! Language practice loop — learn like a human (teacher + self-behavior).
//!
//! 1) Student utters English chosen from meaning (lexicon)
//! 2) Machine frame generated (native tongue)
//! 3) TTS speaks real words
//! 4) Self-hear: re-ingest own phrase (corollary / bone-like) + optional mic residual
//! 5) Score: known-word recovery, frame identity, encode episode
//!
//! Teacher (Ollama) grows lexicon offline; this loop is *implementation learning*.

const std = @import("std");
const fixed = @import("fixed.zig");
const memory_f = @import("memory_fixed.zig");
const lexicon_en = @import("lexicon_en_fixed.zig");
const machine_lang = @import("machine_lang_fixed.zig");
const host_tts = @import("host_tts_fixed.zig");
const organism_f = @import("organism_fixed.zig");
const Fixed = fixed.Fixed;

pub const PracticeReport = struct {
    ok: bool,
    n_trials: u32,
    n_tts_spoken: u32,
    n_self_recover: u32,
    n_frame_rt: u32,
    n_encode: u32,
    n_known_in: u32,
    n_known_out: u32,
    lexicon_total: u32,
    last_phrase: [96]u8 = .{0} ** 96,
    last_phrase_n: usize = 0,
    fluency: f64,
};

/// Seed meaning from a prototype word (teacher card stand-in).
fn meaningFromWord(word: []const u8, out: *[8]Fixed) void {
    lexicon_en.wordProto(word, out);
}

/// Count how many space-separated tokens in phrase are known lexicon words.
fn countKnownInPhrase(phrase: []const u8) u32 {
    var n: u32 = 0;
    var start: usize = 0;
    var i: usize = 0;
    while (i <= phrase.len) : (i += 1) {
        const end = i == phrase.len;
        if (end or phrase[i] == ' ') {
            if (i > start) {
                var w = phrase[start..i];
                while (w.len > 0 and (w[w.len - 1] == '.' or w[w.len - 1] == ','))
                    w = w[0 .. w.len - 1];
                if (w.len > 0 and lexicon_en.findWord(w) != null) n += 1;
            }
            start = i + 1;
        }
    }
    return n;
}

/// One practice trial: utter → TTS → self re-ingest → encode.
fn oneTrial(
    org: *organism_f.OrganismF,
    seed_word: []const u8,
    rep: *PracticeReport,
) void {
    var meaning: [8]Fixed = undefined;
    meaningFromWord(seed_word, &meaning);
    org.setMeaning(meaning[0..]);

    var phrase: [lexicon_en.MAX_PHRASE]u8 = undefined;
    var frame: machine_lang.MachineFrame = .{};
    const ut = lexicon_en.utterEnglish(&meaning, phrase[0..], &frame);
    if (ut.phrase_n == 0) return;

    rep.n_trials += 1;
    rep.n_known_out += countKnownInPhrase(phrase[0..ut.phrase_n]);

    // save last phrase for report
    rep.last_phrase_n = @min(ut.phrase_n, rep.last_phrase.len);
    @memcpy(rep.last_phrase[0..rep.last_phrase_n], phrase[0..rep.last_phrase_n]);

    // machine frame round-trip
    var raw: [machine_lang.MAX_FRAME_BYTES]u8 = undefined;
    const nb = frame.toBytes(raw[0..]);
    if (machine_lang.MachineFrame.fromBytes(raw[0..nb])) |f2| {
        if (f2.n_words == frame.n_words) rep.n_frame_rt += 1;
    }

    // TTS plant (real words)
    const tts = host_tts.speakEnglish(phrase[0..ut.phrase_n]);
    if (tts.spoken) rep.n_tts_spoken += 1;

    // SELF-HEAR (implementation learning): re-ingest own English as input
    // = corollary discharge / bone-like path (mind knows what it said)
    var toks: [6]u32 = undefined;
    var heard_m: [8]Fixed = undefined;
    const inp = lexicon_en.inputEnglish(phrase[0..ut.phrase_n], &toks, &heard_m);
    rep.n_known_in += inp.n_known;
    if (inp.n_known >= 2) rep.n_self_recover += 1;

    // inject recovered meaning + machine features
    var feats: [8]Fixed = undefined;
    _ = machine_lang.understandToFeatures(&frame, &feats);
    org.bus.clear();
    org.pushSense(.text, heard_m[0..], fixed.fromDecimalStr("1.0"));
    org.pushSense(.custom, feats[0..], fixed.fromDecimalStr("0.85"));
    org.setInjectFeatsOnly(feats[0..]);
    _ = org.tickOnce();

    const ep = [_]u32{
        memory_f.hashToken("self"),
        memory_f.hashToken("practice"),
        memory_f.hashToken("say"),
        memory_f.hashToken(seed_word),
        toks[0],
        memory_f.hashToken("hear"),
    };
    _ = org.store.encode(&org.brain, feats[0..], 0b111111, ep);
    rep.n_encode += 1;
}

/// Full practice session over a small curriculum of seed words.
pub fn runLanguagePractice() PracticeReport {
    _ = lexicon_en.tryLoadDefaultRoles();

    var rep: PracticeReport = .{
        .ok = false,
        .n_trials = 0,
        .n_tts_spoken = 0,
        .n_self_recover = 0,
        .n_frame_rt = 0,
        .n_encode = 0,
        .n_known_in = 0,
        .n_known_out = 0,
        .lexicon_total = @intCast(lexicon_en.totalWords()),
        .fluency = 0,
    };

    var org = organism_f.OrganismF.init();
    org.steps_per_tick = 3;

    // Curriculum seeds (human-like: concrete → social → mind)
    const seeds = [_][]const u8{
        "light", "sound", "see", "hear", "I", "you",
        "person", "place", "say", "know", "learn", "good",
    };

    for (seeds) |w| {
        // only practice if word is in lexicon
        if (lexicon_en.findWord(w) == null) continue;
        oneTrial(&org, w, &rep);
    }

    if (rep.n_trials > 0) {
        const rec = @as(f64, @floatFromInt(rep.n_self_recover)) / @as(f64, @floatFromInt(rep.n_trials));
        const frt = @as(f64, @floatFromInt(rep.n_frame_rt)) / @as(f64, @floatFromInt(rep.n_trials));
        const tts = @as(f64, @floatFromInt(rep.n_tts_spoken)) / @as(f64, @floatFromInt(rep.n_trials));
        rep.fluency = 0.45 * rec + 0.35 * frt + 0.20 * tts;
    }

    // Pass: practiced, recovered own speech, frames stable, TTS worked at least once
    rep.ok = rep.n_trials >= 6 and rep.n_self_recover >= (rep.n_trials * 3 / 4) and rep.n_frame_rt >= (rep.n_trials * 3 / 4) and rep.n_tts_spoken >= 1 and rep.n_encode >= 6;
    return rep;
}

pub fn selfTest() bool {
    _ = lexicon_en.tryLoadDefaultRoles();
    if (lexicon_en.totalWords() < 20) return false;
    var meaning: [8]Fixed = undefined;
    lexicon_en.wordProto("light", &meaning);
    var phrase: [lexicon_en.MAX_PHRASE]u8 = undefined;
    var frame: machine_lang.MachineFrame = .{};
    const ut = lexicon_en.utterEnglish(&meaning, phrase[0..], &frame);
    if (ut.phrase_n < 3) return false;
    var toks: [6]u32 = undefined;
    var hm: [8]Fixed = undefined;
    const inp = lexicon_en.inputEnglish(phrase[0..ut.phrase_n], &toks, &hm);
    return inp.n_known >= 2;
}
