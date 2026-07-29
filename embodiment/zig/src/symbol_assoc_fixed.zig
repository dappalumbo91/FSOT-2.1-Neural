//! Symbolic association — sensory signature → prototype anchors (fixed).
//! Spirit of sensory/symbol_assoc.py. Not open-world vision claim; nearest-symbol bind.

const fixed = @import("fixed.zig");
const memory_f = @import("memory_fixed.zig");
const Fixed = fixed.Fixed;

pub const FEAT: usize = 8;
pub const N_ANCHORS: usize = 12;

const ANCHOR_NAMES = [_][]const u8{
    "person", "face", "place", "animal", "music", "action",
    "night",  "day",  "dark",  "bright", "scene", "sound",
};

pub const Signature = struct {
    vec: [FEAT]Fixed = .{0} ** FEAT,
};

fn anchorProto(idx: u32, out: *[FEAT]Fixed) void {
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        const u: u32 = idx *% 47 +% @as(u32, @intCast(i)) *% 13 +% 9;
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

/// Nearest prototype anchor id (0..N_ANCHORS-1).
pub fn nearestAnchor(sig: *const [FEAT]Fixed) u32 {
    var best: u32 = 0;
    var proto: [FEAT]Fixed = undefined;
    anchorProto(0, &proto);
    var best_d = dist2(sig, &proto);
    var a: u32 = 1;
    while (a < N_ANCHORS) : (a += 1) {
        anchorProto(a, &proto);
        const d = dist2(sig, &proto);
        if (fixed.lt(d, best_d)) {
            best_d = d;
            best = a;
        }
    }
    return best;
}

pub fn anchorToken(idx: u32) u32 {
    if (idx >= N_ANCHORS) return memory_f.hashToken("unknown");
    return memory_f.hashToken(ANCHOR_NAMES[idx]);
}

/// Build signature from vision-like + audio-like channels (cross-modal soft blend).
pub fn blendSignature(vision: *const [FEAT]Fixed, audio: *const [FEAT]Fixed, out: *[FEAT]Fixed) void {
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        out[i] = fixed.add(
            fixed.mul(vision[i], fixed.fromDecimalStr("0.6")),
            fixed.mul(audio[i], fixed.fromDecimalStr("0.4")),
        );
    }
}

pub const SymbolReport = struct {
    ok: bool,
    n_anchors: u32,
    n_probes: u32,
    correct: u32,
    top1: f64,
    cross_modal_correct: u32,
    cross_modal_top1: f64,
};

pub fn runSymbolAssocProbe() SymbolReport {
    // Teach: each anchor's clean proto is known; probe with jittered sample
    var correct: u32 = 0;
    var cm_ok: u32 = 0;
    var a: u32 = 0;
    while (a < N_ANCHORS) : (a += 1) {
        var clean: [FEAT]Fixed = undefined;
        anchorProto(a, &clean);
        // jittered vision
        var noisy: [FEAT]Fixed = undefined;
        var i: usize = 0;
        while (i < FEAT) : (i += 1) {
            const jn: i64 = @intCast((a *% 3 +% @as(u32, @intCast(i))) % 7);
            const jit = fixed.div(fixed.sub(fixed.fromInt(jn), fixed.fromInt(3)), fixed.fromInt(50));
            noisy[i] = fixed.clamp(fixed.add(clean[i], jit), fixed.fromInt(-1), fixed.fromInt(1));
        }
        if (nearestAnchor(&noisy) == a) correct += 1;

        // cross-modal: half vision clean, half audio from same anchor family
        var aud: [FEAT]Fixed = undefined;
        anchorProto(a, &aud);
        // slightly different mix seed for "audio"
        i = 0;
        while (i < FEAT) : (i += 1) {
            aud[i] = fixed.mul(aud[i], fixed.fromDecimalStr("0.9"));
        }
        var joint: [FEAT]Fixed = undefined;
        blendSignature(&noisy, &aud, &joint);
        if (nearestAnchor(&joint) == a) cm_ok += 1;
    }
    const n: f64 = @floatFromInt(N_ANCHORS);
    const top1 = @as(f64, @floatFromInt(correct)) / n;
    const ctop = @as(f64, @floatFromInt(cm_ok)) / n;
    // chance 1/12 ≈ 0.083
    const ok = top1 >= 0.7 and ctop >= 0.6;
    return .{
        .ok = ok,
        .n_anchors = N_ANCHORS,
        .n_probes = N_ANCHORS,
        .correct = correct,
        .top1 = top1,
        .cross_modal_correct = cm_ok,
        .cross_modal_top1 = ctop,
    };
}
