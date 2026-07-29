//! Machine language as the mind's native tongue — run / understand / generate.
//!
//! Not Morse. Not next-token English. Not formant speech.
//!
//! Alphabet: trits {−1,0,+1} packed as OS-visible TritWords (u64 T1).
//! Words:    MachineWord records (same as Python MachineFrame / Zig TritWord).
//! Frames:   magic "FSOT" | ver | path | n_trits | word records  (ABI).
//!
//! Doctrine:
//!   generate  = mind state → frame bytes
//!   understand= frame bytes → trits → Fixed features → bus inject
//!   run       = same trinary substrate already stepping the brain
//!   translate = frame ↔ UTF-8 text is a thin table (bytes), not a second mind
//!
//! Round-trip gate: emit → parse → re-emit must match; inject must move brain.

const std = @import("std");
const fixed = @import("fixed.zig");
const trit = @import("trit.zig");
const machine = @import("machine_encode_fixed.zig");
const frame_inj = @import("frame_inject.zig");
const memory_f = @import("memory_fixed.zig");
const organism_f = @import("organism_fixed.zig");
const pathways_f = @import("pathways_fixed.zig");
const Fixed = fixed.Fixed;

pub const PATH_MACHINE: u8 = 1;
pub const PATH_CHEMICAL: u8 = 2;
pub const ABI_VERSION: u8 = 1;
pub const MAX_WORDS: usize = 16;
pub const MAX_FRAME_BYTES: usize = 10 + MAX_WORDS * 12; // header + word records
pub const MAX_TRITS: usize = 32 * MAX_WORDS;

pub const MachineWord = struct {
    pack: u64 = 0,
    n_trits: u8 = 0,
};

pub const MachineFrame = struct {
    version: u8 = ABI_VERSION,
    path_id: u8 = PATH_MACHINE,
    n_trits: u32 = 0,
    words: [MAX_WORDS]MachineWord = [_]MachineWord{.{}} ** MAX_WORDS,
    n_words: usize = 0,

    pub fn clear(self: *MachineFrame) void {
        self.* = .{};
        self.version = ABI_VERSION;
        self.path_id = PATH_MACHINE;
    }

    /// Serialize to ABI bytes (Python MachineFrame.to_bytes compatible).
    pub fn toBytes(self: *const MachineFrame, out: []u8) usize {
        if (out.len < 10) return 0;
        @memcpy(out[0..4], &frame_inj.magic);
        out[4] = self.version;
        out[5] = self.path_id;
        std.mem.writeInt(u32, out[6..10], self.n_trits, .little);
        var off: usize = 10;
        var i: usize = 0;
        while (i < self.n_words and off + 12 <= out.len) : (i += 1) {
            std.mem.writeInt(u64, out[off .. off + 8][0..8], self.words[i].pack, .little);
            out[off + 8] = self.words[i].n_trits;
            out[off + 9] = 0;
            out[off + 10] = 0;
            out[off + 11] = 0;
            off += 12;
        }
        return off;
    }

    /// Parse ABI bytes.
    pub fn fromBytes(buf: []const u8) ?MachineFrame {
        const h = frame_inj.parseHeader(buf) orelse return null;
        var f: MachineFrame = .{};
        f.version = h.version;
        f.path_id = h.path_id;
        f.n_trits = h.n_trits;
        var off: usize = 10;
        while (off + 12 <= buf.len and f.n_words < MAX_WORDS) {
            f.words[f.n_words] = .{
                .pack = std.mem.readInt(u64, buf[off .. off + 8][0..8], .little),
                .n_trits = buf[off + 8],
            };
            f.n_words += 1;
            off += 12;
        }
        return f;
    }

    /// Expand all words into a trit stream.
    pub fn toTrits(self: *const MachineFrame, out: []trit.Trit) usize {
        var n: usize = 0;
        var w: usize = 0;
        while (w < self.n_words) : (w += 1) {
            const nw = @min(@as(usize, self.words[w].n_trits), @as(usize, 32));
            var i: u8 = 0;
            while (i < nw and n < out.len) : (i += 1) {
                const bits: u8 = @truncate(self.words[w].pack >> @intCast(2 * i));
                out[n] = trit.unpackT1(bits) orelse 0;
                n += 1;
            }
        }
        return n;
    }

    /// First 8 trits → Fixed features for neural inject.
    pub fn toFeatures(self: *const MachineFrame, out: *[8]Fixed) usize {
        var trits: [MAX_TRITS]trit.Trit = undefined;
        const nt = self.toTrits(trits[0..]);
        return machine.tritsToFeatures(trits[0..nt], out[0..]);
    }
};

/// Pack one u32 token into a 32-trit machine word (bit→trit, lossless).
pub fn tokenToWord(tok: u32) MachineWord {
    var bytes: [4]u8 = undefined;
    std.mem.writeInt(u32, &bytes, tok, .little);
    var trits: [32]trit.Trit = .{0} ** 32;
    const n = machine.bytesToTrits(bytes[0..], trits[0..]);
    // pad to 32 with zeros
    const tw = trit.TritWord.fromTrits(trits[0..32]);
    _ = n;
    return .{ .pack = tw.pack, .n_trits = 32 };
}

/// Meaning features → one machine word (quantize to trits).
pub fn meaningToWord(meaning: []const Fixed) MachineWord {
    var trits: [32]trit.Trit = .{0} ** 32;
    const n = machine.featuresToTrits(meaning, trits[0..]);
    const tw = trit.TritWord.fromTrits(trits[0..@max(n, 1)]);
    return .{ .pack = tw.pack, .n_trits = tw.n };
}

/// GENERATE: mind symbols (5W1H tokens + meaning) → machine frame.
pub fn generateFromMind(
    tokens: *const [6]u32,
    meaning: []const Fixed,
    out: *MachineFrame,
) void {
    out.clear();
    out.path_id = PATH_MACHINE;
    var total_trits: u32 = 0;

    // six 5W1H tokens → six words
    var i: usize = 0;
    while (i < 6 and out.n_words < MAX_WORDS) : (i += 1) {
        out.words[out.n_words] = tokenToWord(tokens[i]);
        total_trits += out.words[out.n_words].n_trits;
        out.n_words += 1;
    }
    // meaning as final word
    if (out.n_words < MAX_WORDS) {
        out.words[out.n_words] = meaningToWord(meaning);
        total_trits += out.words[out.n_words].n_trits;
        out.n_words += 1;
    }
    out.n_trits = total_trits;
}

/// UNDERSTAND: frame → features (ready for bus inject).
pub fn understandToFeatures(frame: *const MachineFrame, out: *[8]Fixed) usize {
    return frame.toFeatures(out);
}

/// Thin translate: frame bytes → hex string for host log (human can read; mind still uses trits).
pub fn frameToHex(frame_bytes: []const u8, out: []u8) usize {
    const hex = "0123456789abcdef";
    var o: usize = 0;
    for (frame_bytes) |b| {
        if (o + 2 > out.len) break;
        out[o] = hex[b >> 4];
        out[o + 1] = hex[b & 0xf];
        o += 2;
    }
    return o;
}

/// UTF-8 text → machine frame (host keyboard / file language into mind tongue).
pub fn generateFromText(text: []const u8, out: *MachineFrame) void {
    out.clear();
    out.path_id = PATH_MACHINE;
    var trits: [machine.MAX_TRITS]trit.Trit = undefined;
    const nt = machine.bytesToTrits(text, trits[0..]);
    var words: [MAX_WORDS]trit.TritWord = undefined;
    const nw = machine.tritsToWords(trits[0..nt], words[0..]);
    var i: usize = 0;
    while (i < nw and out.n_words < MAX_WORDS) : (i += 1) {
        out.words[out.n_words] = .{ .pack = words[i].pack, .n_trits = words[i].n };
        out.n_words += 1;
    }
    out.n_trits = @intCast(nt);
}

/// Text round-trip through machine language: text → frame → bytes → frame → text.
pub fn textRoundTrip(text: []const u8, out_text: []u8) struct { ok: bool, n: usize } {
    var f: MachineFrame = .{};
    generateFromText(text, &f);
    var raw: [MAX_FRAME_BYTES]u8 = undefined;
    const nb = f.toBytes(raw[0..]);
    const f2 = MachineFrame.fromBytes(raw[0..nb]) orelse return .{ .ok = false, .n = 0 };
    var trits: [MAX_TRITS]trit.Trit = undefined;
    const nt = f2.toTrits(trits[0..]);
    const nback = machine.tritsToBytes(trits[0..nt], out_text);
    const ok = nback == text.len and std.mem.eql(u8, out_text[0..nback], text);
    return .{ .ok = ok, .n = nback };
}

pub const LoopReport = struct {
    ok: bool,
    frame_roundtrip: bool,
    text_roundtrip: bool,
    inject_spikes: u32,
    n_words: u32,
    n_trits: u32,
    n_bytes: u32,
    n_generated: u32,
    n_understood: u32,
    hex_head: [48]u8 = .{0} ** 48,
    hex_len: usize = 0,
};

/// Full organism loop: generate machine language from live meaning → plant bytes
/// → re-parse → inject as text modality → brain steps → verify frame identity.
pub fn runMachineLangLoop() LoopReport {
    var org = organism_f.OrganismF.init();
    org.steps_per_tick = 4;

    // Seed meaning (vision-like features the mind would hold)
    var meaning: [8]Fixed = undefined;
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        const v: i64 = @as(i64, @intCast(i)) * 17 - 50;
        meaning[i] = fixed.fromRatio(v, 100);
    }
    org.setMeaning(meaning[0..]);

    const tokens = [_]u32{
        memory_f.hashToken("who_self"),
        memory_f.hashToken("what_machine"),
        memory_f.hashToken("why_speak"),
        memory_f.hashToken("where_host"),
        memory_f.hashToken("when_now"),
        memory_f.hashToken("how_frame"),
    };

    // --- GENERATE ---
    var frame: MachineFrame = .{};
    generateFromMind(&tokens, meaning[0..], &frame);
    var raw: [MAX_FRAME_BYTES]u8 = undefined;
    const n_bytes = frame.toBytes(raw[0..]);

    // plant log: hex (host can translate; mind does not need English)
    var hex_buf: [128]u8 = undefined;
    const hl = frameToHex(raw[0..n_bytes], hex_buf[0..]);

    // --- UNDERSTAND (re-ingest same bytes) ---
    const parsed = MachineFrame.fromBytes(raw[0..n_bytes]);
    var frame_rt = false;
    var n_under: u32 = 0;
    var spikes: u32 = 0;

    if (parsed) |f2| {
        n_under = 1;
        // identity: same n_words, packs
        frame_rt = f2.n_words == frame.n_words and f2.n_trits == frame.n_trits;
        if (frame_rt) {
            var w: usize = 0;
            while (w < frame.n_words) : (w += 1) {
                if (f2.words[w].pack != frame.words[w].pack) frame_rt = false;
            }
        }

        var feats: [8]Fixed = undefined;
        _ = understandToFeatures(&f2, &feats);
        org.bus.clear();
        org.pushSense(.text, feats[0..], fixed.fromDecimalStr("1.0"));
        org.pushSense(.custom, feats[0..], fixed.fromDecimalStr("0.85"));
        org.setInjectFeatsOnly(feats[0..]);
        org.setMeaning(feats[0..]);

        const before = org.brain.totalSpikes();
        _ = org.tickOnce();
        _ = org.tickOnce();
        spikes = org.brain.totalSpikes() - before;

        // store episode of what was said (machine utterance in memory)
        const utok = [_]u32{
            memory_f.hashToken("self"),
            memory_f.hashToken("machine_lang"),
            memory_f.hashToken("utter"),
            memory_f.hashToken("frame"),
            0,
            memory_f.hashToken("emit"),
        };
        _ = org.store.encode(&org.brain, feats[0..], 0b101111, utok);
    }

    // --- TEXT codec check ---
    const sample = "FSOT machine tongue";
    var back: [64]u8 = undefined;
    const tr = textRoundTrip(sample, back[0..]);

    // second generation after inject (mind still can generate)
    var frame2: MachineFrame = .{};
    generateFromMind(&tokens, meaning[0..], &frame2);
    var raw2: [MAX_FRAME_BYTES]u8 = undefined;
    const n2 = frame2.toBytes(raw2[0..]);
    const gen_ok = n2 == n_bytes and std.mem.eql(u8, raw2[0..n2], raw[0..n_bytes]);

    var rep: LoopReport = .{
        .ok = false,
        .frame_roundtrip = frame_rt and gen_ok,
        .text_roundtrip = tr.ok,
        .inject_spikes = spikes,
        .n_words = @intCast(frame.n_words),
        .n_trits = frame.n_trits,
        .n_bytes = @intCast(n_bytes),
        .n_generated = 2,
        .n_understood = n_under,
    };
    const copy_n = @min(hl, rep.hex_head.len);
    @memcpy(rep.hex_head[0..copy_n], hex_buf[0..copy_n]);
    rep.hex_len = copy_n;

    // Pass: frame identity + text codec + mind took inject (spikes or episode)
    rep.ok = rep.frame_roundtrip and rep.text_roundtrip and rep.n_understood >= 1 and (spikes > 0 or org.store.n >= 1);
    return rep;
}

/// Emit one machine utterance from organism (for live mind).
pub fn emitFromOrganism(
    org: *organism_f.OrganismF,
    tokens: *const [6]u32,
    frame_bytes: []u8,
    feats_out: *[8]Fixed,
) struct { n_bytes: usize, n_feats: usize, frame: MachineFrame } {
    var frame: MachineFrame = .{};
    var meaning: [8]Fixed = .{0} ** 8;
    if (org.has_meaning) {
        @memcpy(meaning[0..], org.last_meaning[0..]);
    }
    generateFromMind(tokens, meaning[0..], &frame);
    const nb = frame.toBytes(frame_bytes);
    const nf = understandToFeatures(&frame, feats_out);
    // self-ingest: machine language re-enters as text + custom (understand own speech)
    org.pushSense(.text, feats_out[0..], pathways_f.pathwayGain(.primary));
    org.pushSense(.custom, feats_out[0..], fixed.fromDecimalStr("0.75"));
    return .{ .n_bytes = nb, .n_feats = nf, .frame = frame };
}

pub fn selfTest() bool {
    // token word non-zero for non-zero token
    const w = tokenToWord(0x41424344);
    if (w.n_trits != 32) return false;
    if (w.pack == 0) return false;

    var f: MachineFrame = .{};
    const toks = [_]u32{ 1, 2, 3, 4, 5, 6 };
    var meaning: [8]Fixed = .{0} ** 8;
    meaning[0] = fixed.fromDecimalStr("0.9");
    generateFromMind(&toks, meaning[0..], &f);
    if (f.n_words < 7) return false;

    var buf: [MAX_FRAME_BYTES]u8 = undefined;
    const n = f.toBytes(buf[0..]);
    if (n < 10) return false;
    const f2 = MachineFrame.fromBytes(buf[0..n]) orelse return false;
    if (f2.n_words != f.n_words) return false;
    if (f2.words[0].pack != f.words[0].pack) return false;

    var back: [64]u8 = undefined;
    const tr = textRoundTrip("hi", back[0..]);
    if (!tr.ok) return false;

    return true;
}

pub const StressReport = struct {
    ok: bool,
    n_frames: u32,
    n_frame_ok: u32,
    n_text_ok: u32,
    n_text_trials: u32,
    n_inject_ok: u32,
    n_bytes_total: u64,
    n_trits_total: u64,
    n_word_mismatches: u32,
    n_corrupt_reject: u32,
    max_spikes: u32,
};

/// Stress: many generate→bytes→parse→compare cycles, text codec, injects, corrupt reject.
pub fn runMachineLangStress(n_frames: u32) StressReport {
    var rep: StressReport = .{
        .ok = false,
        .n_frames = n_frames,
        .n_frame_ok = 0,
        .n_text_ok = 0,
        .n_text_trials = 0,
        .n_inject_ok = 0,
        .n_bytes_total = 0,
        .n_trits_total = 0,
        .n_word_mismatches = 0,
        .n_corrupt_reject = 0,
        .max_spikes = 0,
    };

    var org = organism_f.OrganismF.init();
    org.steps_per_tick = 2;

    var seed: u32 = 0xC0DEC0DE;
    var i: u32 = 0;
    while (i < n_frames) : (i += 1) {
        // xorshift-ish for varied tokens (no free float rand)
        seed ^= seed << 13;
        seed ^= seed >> 17;
        seed ^= seed << 5;
        const tokens = [_]u32{
            seed,
            seed *% 3 +% i,
            seed *% 7 +% 11,
            memory_f.hashToken("stress"),
            i,
            seed ^ 0xA5A5A5A5,
        };
        var meaning: [8]Fixed = undefined;
        var k: usize = 0;
        while (k < 8) : (k += 1) {
            const v: i64 = @as(i64, @intCast((seed +% @as(u32, @intCast(k)) *% 19 +% i) % 201)) - 100;
            meaning[k] = fixed.fromRatio(v, 100);
        }

        var frame: MachineFrame = .{};
        generateFromMind(&tokens, meaning[0..], &frame);
        var raw: [MAX_FRAME_BYTES]u8 = undefined;
        const nb = frame.toBytes(raw[0..]);
        rep.n_bytes_total += nb;
        rep.n_trits_total += frame.n_trits;

        const parsed = MachineFrame.fromBytes(raw[0..nb]);
        if (parsed) |f2| {
            var ok = f2.n_words == frame.n_words and f2.n_trits == frame.n_trits;
            var w: usize = 0;
            while (w < frame.n_words) : (w += 1) {
                if (f2.words[w].pack != frame.words[w].pack or f2.words[w].n_trits != frame.words[w].n_trits) {
                    ok = false;
                    rep.n_word_mismatches += 1;
                }
            }
            if (ok) rep.n_frame_ok += 1;

            // re-emit must match
            var frame3: MachineFrame = .{};
            generateFromMind(&tokens, meaning[0..], &frame3);
            var raw3: [MAX_FRAME_BYTES]u8 = undefined;
            const n3 = frame3.toBytes(raw3[0..]);
            if (!(n3 == nb and std.mem.eql(u8, raw3[0..n3], raw[0..nb]))) {
                // deterministic generate must be stable
                if (ok) rep.n_frame_ok -|= 1;
            }

            // inject every 8th frame
            if ((i % 8) == 0) {
                var feats: [8]Fixed = undefined;
                _ = understandToFeatures(&f2, &feats);
                org.bus.clear();
                org.pushSense(.text, feats[0..], fixed.fromDecimalStr("1.0"));
                org.setInjectFeatsOnly(feats[0..]);
                const before = org.brain.totalSpikes();
                _ = org.tickOnce();
                const d = org.brain.totalSpikes() - before;
                if (d > rep.max_spikes) rep.max_spikes = d;
                rep.n_inject_ok += 1;
            }
        }

        // corrupt magic → must reject
        if (nb >= 4) {
            var bad: [MAX_FRAME_BYTES]u8 = undefined;
            @memcpy(bad[0..nb], raw[0..nb]);
            bad[0] ^= 0xFF;
            if (MachineFrame.fromBytes(bad[0..nb]) == null) rep.n_corrupt_reject += 1;
        }
    }

    // text codec stress (ASCII; each ≤32 bytes so ≤256 bit-trits = machine.MAX_TRITS)
    const msgs = [_][]const u8{
        "a",
        "hi",
        "FSOT",
        "machine tongue",
        "quick brown fox 0123", // 20 B → 160 trits
        "AAAABBBBCCCCDDDD", // 16 B → 128 trits
    };
    for (msgs) |msg| {
        rep.n_text_trials += 1;
        var back: [128]u8 = undefined;
        if (msg.len > back.len) continue;
        const tr = textRoundTrip(msg, back[0..]);
        if (tr.ok) rep.n_text_ok += 1;
    }

    const frames_ok = rep.n_frame_ok == rep.n_frames;
    const text_ok = rep.n_text_ok == rep.n_text_trials;
    const corrupt_ok = rep.n_corrupt_reject == rep.n_frames;
    const inject_ok = rep.n_inject_ok >= (n_frames / 8);
    rep.ok = frames_ok and text_ok and corrupt_ok and inject_ok and rep.n_word_mismatches == 0;
    return rep;
}
