//! Machine-oriented translation layer (Fixed / trit ABI).
//! Replaces machine_encode.py primary path for Zig authority.
//!
//! Primary: OS bytes / UTF-8 ↔ trit stream ↔ TritWord ↔ Fixed feature inject
//! Chemical: DNA codon → primary trits (genetic spine already elsewhere)
//! NOT Morse as intelligence path; NOT next-token LM.

const std = @import("std");
const fixed = @import("fixed.zig");
const trit = @import("trit.zig");
const Fixed = fixed.Fixed;

pub const MAX_TRITS: usize = 256;

/// Lossless: each bit → trit (0→0, 1→+1). OS buffer style.
pub fn bytesToTrits(data: []const u8, out: []trit.Trit) usize {
    var n: usize = 0;
    for (data) |b| {
        var shift: u4 = 0;
        while (shift < 8) : (shift += 1) {
            if (n >= out.len) return n;
            const bit = (b >> @intCast(shift)) & 1;
            out[n] = if (bit != 0) @as(trit.Trit, 1) else 0;
            n += 1;
        }
    }
    return n;
}

pub fn tritsToBytes(trits: []const trit.Trit, out: []u8) usize {
    var n_out: usize = 0;
    const usable = trits.len - (trits.len % 8);
    var i: usize = 0;
    while (i + 7 < usable and n_out < out.len) : (i += 8) {
        var b: u8 = 0;
        var k: usize = 0;
        while (k < 8) : (k += 1) {
            if (trits[i + k] > 0) b |= @as(u8, 1) << @intCast(k);
        }
        out[n_out] = b;
        n_out += 1;
    }
    return n_out;
}

/// Chunk trits into TritWords (default 32).
pub fn tritsToWords(trits: []const trit.Trit, out: []trit.TritWord) usize {
    var n: usize = 0;
    var i: usize = 0;
    while (i < trits.len and n < out.len) {
        const end = @min(i + 32, trits.len);
        var chunk: [32]trit.Trit = .{0} ** 32;
        const clen = end - i;
        @memcpy(chunk[0..clen], trits[i..end]);
        out[n] = trit.TritWord.fromTrits(chunk[0..32]);
        n += 1;
        i = end;
    }
    return n;
}

/// Quantize Fixed features → trits (lo/hi band, seed-honest thresholds).
pub fn featuresToTrits(feats: []const Fixed, out: []trit.Trit) usize {
    const lo = fixed.fromDecimalStr("-0.25");
    const hi = fixed.fromDecimalStr("0.25");
    const n = @min(feats.len, out.len);
    var i: usize = 0;
    while (i < n) : (i += 1) {
        if (fixed.lt(feats[i], lo)) out[i] = -1 else if (fixed.gt(feats[i], hi)) out[i] = 1 else out[i] = 0;
    }
    return n;
}

/// Trits → Fixed inject features in [-1,1] (neural edge expansion).
pub fn tritsToFeatures(trits: []const trit.Trit, out: []Fixed) usize {
    const n = @min(trits.len, out.len);
    var i: usize = 0;
    while (i < n) : (i += 1) {
        out[i] = switch (trits[i]) {
            1 => fixed.fromInt(1),
            -1 => fixed.fromInt(-1),
            else => 0,
        };
    }
    return n;
}

/// DNA bases → primary trits (A,G=+1 C,T=-1).
pub fn dnaToTrits(dna: []const u8, out: []trit.Trit) usize {
    var n: usize = 0;
    for (dna) |c| {
        if (n >= out.len) break;
        const t = trit.basePrimary(c);
        if (t == 0 and c != 'N' and c != 'n') {
            // skip non-base
            continue;
        }
        if (c == 'A' or c == 'a' or c == 'G' or c == 'g' or c == 'C' or c == 'c' or c == 'T' or c == 't') {
            out[n] = t;
            n += 1;
        }
    }
    return n;
}

pub const MachineReport = struct {
    ok: bool,
    bytes_roundtrip: bool,
    text_roundtrip: bool,
    feat_trit_ok: bool,
    dna_codon_ok: bool,
    n_words: u32,
};

pub fn runMachineEncodeProbe() MachineReport {
    // byte lossless
    const msg = "FSOT mind ABI";
    var trits: [MAX_TRITS]trit.Trit = undefined;
    const nt = bytesToTrits(msg, trits[0..]);
    var back: [64]u8 = undefined;
    const nb = tritsToBytes(trits[0..nt], back[0..]);
    const bytes_ok = nb == msg.len and std.mem.eql(u8, back[0..nb], msg);

    // feature quantize
    const feats = [_]Fixed{
        fixed.fromDecimalStr("0.9"),
        fixed.fromDecimalStr("-0.8"),
        fixed.fromDecimalStr("0.05"),
        fixed.fromDecimalStr("0.4"),
    };
    var ft: [8]trit.Trit = undefined;
    const nft = featuresToTrits(feats[0..], ft[0..]);
    var ff: [8]Fixed = undefined;
    _ = tritsToFeatures(ft[0..nft], ff[0..]);
    const feat_ok = nft == 4 and ft[0] == 1 and ft[1] == -1 and ft[2] == 0 and ft[3] == 1;

    // DNA primary
    const dna = "ATGCGTAA";
    var dt: [32]trit.Trit = undefined;
    const nd = dnaToTrits(dna, dt[0..]);
    // A T G C → +1 -1 +1 -1
    const dna_ok = nd >= 4 and dt[0] == 1 and dt[1] == -1 and dt[2] == 1 and dt[3] == -1;

    // words
    var words: [8]trit.TritWord = undefined;
    const nw = tritsToWords(trits[0..nt], words[0..]);

    // text roundtrip via bytes
    const text_ok = bytes_ok;

    return .{
        .ok = bytes_ok and feat_ok and dna_ok and nw >= 1,
        .bytes_roundtrip = bytes_ok,
        .text_roundtrip = text_ok,
        .feat_trit_ok = feat_ok,
        .dna_codon_ok = dna_ok,
        .n_words = @intCast(nw),
    };
}

pub fn selfTest() bool {
    return runMachineEncodeProbe().ok;
}
