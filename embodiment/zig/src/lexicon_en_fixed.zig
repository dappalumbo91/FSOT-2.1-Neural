//! English lexicon codec — real words bound to machine-language tokens.
//!
//! Mind tongue stays TritWord / FSOT frames (machine_lang_fixed).
//! This module is the **translation library**:
//!   choose English words from meaning / 5W1H
//!   ↔ machine tokens
//!   → phrase for human / TTS plant
//!
//! Not an LLM. Finite dictionary + nearest-prototype choice (like symbol anchors).

const std = @import("std");
const fixed = @import("fixed.zig");
const memory_f = @import("memory_fixed.zig");
const machine_lang = @import("machine_lang_fixed.zig");
const Fixed = fixed.Fixed;

pub const FEAT: usize = 8;
pub const MAX_PHRASE: usize = 160;
pub const MAX_WORDS_IN: usize = 12;

pub const Role = enum(u8) {
    who = 0,
    verb = 1,
    what = 2,
    where = 3,
    when = 4,
    how = 5,
    adj = 6,
    link = 7,
};

pub const Entry = struct {
    word: []const u8,
    role: Role,
    /// stable machine token (hash of word)
    token: u32,
};

/// Core English inventory the mind may *choose* (not free generation).
const WORDS = [_]struct { []const u8, Role }{
    // who
    .{ "I", .who },
    .{ "you", .who },
    .{ "self", .who },
    .{ "agent", .who },
    .{ "mind", .who },
    // verbs
    .{ "see", .verb },
    .{ "hear", .verb },
    .{ "say", .verb },
    .{ "know", .verb },
    .{ "learn", .verb },
    .{ "want", .verb },
    .{ "feel", .verb },
    .{ "think", .verb },
    .{ "speak", .verb },
    .{ "encode", .verb },
    .{ "recall", .verb },
    // what / nouns
    .{ "light", .what },
    .{ "sound", .what },
    .{ "person", .what },
    .{ "place", .what },
    .{ "thing", .what },
    .{ "frame", .what },
    .{ "machine", .what },
    .{ "word", .what },
    .{ "pattern", .what },
    .{ "noise", .what },
    .{ "voice", .what },
    .{ "scene", .what },
    .{ "memory", .what },
    .{ "signal", .what },
    // where
    .{ "here", .where },
    .{ "host", .where },
    .{ "room", .where },
    .{ "world", .where },
    // when
    .{ "now", .when },
    .{ "before", .when },
    .{ "again", .when },
    // how
    .{ "well", .how },
    .{ "clearly", .how },
    .{ "softly", .how },
    // adj
    .{ "good", .adj },
    .{ "bad", .adj },
    .{ "new", .adj },
    .{ "own", .adj },
    .{ "live", .adj },
    // links
    .{ "the", .link },
    .{ "a", .link },
    .{ "and", .link },
    .{ "to", .link },
};

pub const N_WORDS: usize = WORDS.len;

fn entryAt(i: usize) Entry {
    return .{
        .word = WORDS[i][0],
        .role = WORDS[i][1],
        .token = memory_f.hashToken(WORDS[i][0]),
    };
}

/// Deterministic meaning prototype for a word (same spirit as symbol anchors).
pub fn wordProto(word: []const u8, out: *[FEAT]Fixed) void {
    const h = memory_f.hashToken(word);
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        const u: u32 = h *% 47 +% @as(u32, @intCast(i)) *% 13 +% 9;
        const a: i64 = @intCast(u % 181);
        out[i] = fixed.sub(fixed.div(fixed.fromInt(a), fixed.fromInt(90)), fixed.fromInt(1));
    }
}

fn dist2(a: *const [FEAT]Fixed, b: *const [FEAT]Fixed) Fixed {
    var s: Fixed = 0;
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        const d = fixed.sub(a[i], b[i]);
        s = fixed.add(s, fixed.mul(d, d));
    }
    return s;
}

/// Look up exact word (case-insensitive ASCII).
pub fn findWord(word: []const u8) ?Entry {
    var i: usize = 0;
    while (i < N_WORDS) : (i += 1) {
        if (std.ascii.eqlIgnoreCase(WORDS[i][0], word)) return entryAt(i);
    }
    return null;
}

pub fn findByToken(tok: u32) ?Entry {
    var i: usize = 0;
    while (i < N_WORDS) : (i += 1) {
        if (memory_f.hashToken(WORDS[i][0]) == tok) return entryAt(i);
    }
    return null;
}

/// CHOOSE: nearest lexicon word of a given role to the meaning vector.
pub fn chooseByRole(meaning: *const [FEAT]Fixed, role: Role) Entry {
    var best_i: usize = 0;
    var best_d: Fixed = fixed.fromInt(999);
    var found = false;
    var proto: [FEAT]Fixed = undefined;
    var i: usize = 0;
    while (i < N_WORDS) : (i += 1) {
        if (WORDS[i][1] != role) continue;
        wordProto(WORDS[i][0], &proto);
        const d = dist2(meaning, &proto);
        if (!found or fixed.lt(d, best_d)) {
            best_d = d;
            best_i = i;
            found = true;
        }
    }
    if (!found) {
        // fallback first word of any role
        return entryAt(0);
    }
    return entryAt(best_i);
}

/// Nearest word of any role (free choice under meaning).
pub fn chooseAny(meaning: *const [FEAT]Fixed) Entry {
    var best_i: usize = 0;
    var best_d: Fixed = fixed.fromInt(999);
    var proto: [FEAT]Fixed = undefined;
    var i: usize = 0;
    while (i < N_WORDS) : (i += 1) {
        wordProto(WORDS[i][0], &proto);
        const d = dist2(meaning, &proto);
        if (i == 0 or fixed.lt(d, best_d)) {
            best_d = d;
            best_i = i;
        }
    }
    return entryAt(best_i);
}

fn appendStr(dst: []u8, pos: *usize, s: []const u8) void {
    if (pos.* >= dst.len) return;
    const n = @min(s.len, dst.len - pos.*);
    @memcpy(dst[pos.* .. pos.* + n], s[0..n]);
    pos.* += n;
}

fn appendWord(dst: []u8, pos: *usize, w: []const u8, first: *bool) void {
    if (!first.*) appendStr(dst, pos, " ");
    appendStr(dst, pos, w);
    first.* = false;
}

/// EXPORT: build English phrase from meaning (chosen words, not echo of inject bytes).
/// Template: "{who} {verb} {adj?} {what} {where?} {when?}."
pub fn phraseFromMeaning(meaning: *const [FEAT]Fixed, out: []u8) struct {
    n: usize,
    who: Entry,
    verb: Entry,
    what: Entry,
    where_e: Entry,
    when_e: Entry,
    tokens: [6]u32,
} {
    const who = chooseByRole(meaning, .who);
    const verb = chooseByRole(meaning, .verb);
    const what = chooseByRole(meaning, .what);
    const where_e = chooseByRole(meaning, .where);
    const when_e = chooseByRole(meaning, .when);
    const adj = chooseByRole(meaning, .adj);

    // Mild diversity: include adj if meaning energy mid-high
    var energy: Fixed = 0;
    var i: usize = 0;
    while (i < FEAT) : (i += 1) energy = fixed.add(energy, fixed.abs(meaning[i]));
    const use_adj = fixed.gt(energy, fixed.fromDecimalStr("1.5"));
    const use_where = fixed.gt(energy, fixed.fromDecimalStr("2.0"));
    const use_when = fixed.gt(energy, fixed.fromDecimalStr("2.5"));

    // Template: "{who} {verb} the [{adj}] {what} [{where}] [{when}]."
    var pos: usize = 0;
    var first = true;
    appendWord(out, &pos, who.word, &first);
    appendWord(out, &pos, verb.word, &first);
    appendWord(out, &pos, "the", &first);
    if (use_adj and !std.mem.eql(u8, adj.word, "own")) {
        // skip weak "own" that reads like a grammar bug before "the"
        appendWord(out, &pos, adj.word, &first);
    }
    appendWord(out, &pos, what.word, &first);
    if (use_where) {
        appendWord(out, &pos, "here", &first); // normalize place tail
        if (!std.mem.eql(u8, where_e.word, "here")) appendWord(out, &pos, where_e.word, &first);
    }
    if (use_when) appendWord(out, &pos, when_e.word, &first);
    appendStr(out, &pos, ".");

    const tokens = [_]u32{
        who.token,
        verb.token,
        what.token,
        if (use_where) where_e.token else 0,
        if (use_when) when_e.token else 0,
        adj.token,
    };
    return .{
        .n = pos,
        .who = who,
        .verb = verb,
        .what = what,
        .where_e = where_e,
        .when_e = when_e,
        .tokens = tokens,
    };
}

/// INPUT: English text (space-separated known words) → tokens + blended meaning.
pub fn inputEnglish(
    text: []const u8,
    tokens_out: *[6]u32,
    meaning_out: *[FEAT]Fixed,
) struct { n_known: u32, n_tok: u32 } {
    var i: usize = 0;
    while (i < FEAT) : (i += 1) meaning_out[i] = 0;
    var t: usize = 0;
    while (t < 6) : (t += 1) tokens_out[t] = 0;

    var n_known: u32 = 0;
    var n_tok: u32 = 0;
    var start: usize = 0;
    var pos: usize = 0;
    var proto: [FEAT]Fixed = undefined;
    var count: u32 = 0;

    const flush = struct {
        fn go(
            word: []const u8,
            tokens_out2: *[6]u32,
            meaning_out2: *[FEAT]Fixed,
            n_known2: *u32,
            n_tok2: *u32,
            count2: *u32,
            proto2: *[FEAT]Fixed,
        ) void {
            if (word.len == 0) return;
            // strip trailing punctuation
            var w = word;
            while (w.len > 0) {
                const c = w[w.len - 1];
                if (c == '.' or c == ',' or c == '!' or c == '?') w = w[0 .. w.len - 1] else break;
            }
            if (w.len == 0) return;
            if (findWord(w)) |e| {
                n_known2.* += 1;
                if (n_tok2.* < 6) {
                    tokens_out2[n_tok2.*] = e.token;
                    n_tok2.* += 1;
                }
                wordProto(e.word, proto2);
                var k: usize = 0;
                while (k < FEAT) : (k += 1) {
                    meaning_out2[k] = fixed.add(meaning_out2[k], proto2[k]);
                }
                count2.* += 1;
            }
        }
    }.go;

    while (pos <= text.len) : (pos += 1) {
        const at_end = pos == text.len;
        const sep = if (at_end) true else (text[pos] == ' ' or text[pos] == '\t' or text[pos] == '\n');
        if (sep) {
            if (pos > start) {
                flush(text[start..pos], tokens_out, meaning_out, &n_known, &n_tok, &count, &proto);
            }
            start = pos + 1;
        }
    }
    if (count > 0) {
        const den = fixed.fromInt(@intCast(count));
        i = 0;
        while (i < FEAT) : (i += 1) {
            meaning_out[i] = fixed.div(meaning_out[i], den);
        }
    }
    return .{ .n_known = n_known, .n_tok = n_tok };
}

/// Full path: meaning → choose phrase → machine frame tokens from chosen words.
pub fn utterEnglish(
    meaning: *const [FEAT]Fixed,
    phrase_out: []u8,
    frame: *machine_lang.MachineFrame,
) struct { phrase_n: usize, frame_bytes_need: usize } {
    const ph = phraseFromMeaning(meaning, phrase_out);
    // Pad tokens to 6
    var toks = ph.tokens;
    machine_lang.generateFromMind(&toks, meaning[0..], frame);
    return .{ .phrase_n = ph.n, .frame_bytes_need = 10 + frame.n_words * 12 };
}

pub const LexReport = struct {
    ok: bool,
    n_words: u32,
    n_choose_ok: u32,
    n_input_known: u32,
    n_input_words: u32,
    phrase_sample: [64]u8 = .{0} ** 64,
    phrase_n: usize = 0,
    frame_roundtrip: bool,
    choose_not_echo: bool,
};

pub fn runLexiconProbe() LexReport {
    var rep: LexReport = .{
        .ok = false,
        .n_words = @intCast(N_WORDS),
        .n_choose_ok = 0,
        .n_input_known = 0,
        .n_input_words = 0,
        .frame_roundtrip = false,
        .choose_not_echo = false,
    };

    // 1) choose is deterministic and role-correct
    var m0: [FEAT]Fixed = undefined;
    wordProto("light", &m0);
    const c_what = chooseByRole(&m0, .what);
    if (c_what.role == .what) rep.n_choose_ok += 1;
    const c_verb = chooseByRole(&m0, .verb);
    if (c_verb.role == .verb) rep.n_choose_ok += 1;
    const c_who = chooseByRole(&m0, .who);
    if (c_who.role == .who) rep.n_choose_ok += 1;

    // 2) input English → known counts
    var toks: [6]u32 = undefined;
    var min: [FEAT]Fixed = undefined;
    const inp = inputEnglish("I see the light now", &toks, &min);
    rep.n_input_known = inp.n_known;
    rep.n_input_words = inp.n_tok;

    // 3) utter: phrase + machine frame round-trip
    var phrase: [MAX_PHRASE]u8 = undefined;
    var frame: machine_lang.MachineFrame = .{};
    const u = utterEnglish(&min, phrase[0..], &frame);
    rep.phrase_n = @min(u.phrase_n, rep.phrase_sample.len);
    @memcpy(rep.phrase_sample[0..rep.phrase_n], phrase[0..rep.phrase_n]);

    var raw: [machine_lang.MAX_FRAME_BYTES]u8 = undefined;
    const nb = frame.toBytes(raw[0..]);
    if (machine_lang.MachineFrame.fromBytes(raw[0..nb])) |f2| {
        rep.frame_roundtrip = f2.n_words == frame.n_words;
    }

    // 4) choose_not_echo: different meanings → different what-words often
    var m1: [FEAT]Fixed = undefined;
    var m2: [FEAT]Fixed = undefined;
    wordProto("sound", &m1);
    wordProto("person", &m2);
    const w1 = chooseByRole(&m1, .what);
    const w2 = chooseByRole(&m2, .what);
    // At least phrases differ OR words differ
    rep.choose_not_echo = !std.mem.eql(u8, w1.word, w2.word) or true; // always record; soft
    // stronger: two phrases from different protos
    var p1: [MAX_PHRASE]u8 = undefined;
    var p2: [MAX_PHRASE]u8 = undefined;
    const a1 = phraseFromMeaning(&m1, p1[0..]);
    const a2 = phraseFromMeaning(&m2, p2[0..]);
    rep.choose_not_echo = a1.n != a2.n or !std.mem.eql(u8, p1[0..a1.n], p2[0..a2.n]);

    rep.ok = rep.n_choose_ok >= 3 and rep.n_input_known >= 4 and rep.frame_roundtrip and rep.phrase_n >= 5 and rep.choose_not_echo;
    return rep;
}

pub fn selfTest() bool {
    if (N_WORDS < 20) return false;
    if (findWord("see") == null) return false;
    if (findWord("SEE") == null) return false;
    var m: [FEAT]Fixed = undefined;
    wordProto("I", &m);
    const e = chooseByRole(&m, .who);
    if (e.role != .who) return false;
    return runLexiconProbe().ok;
}
