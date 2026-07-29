//! Transfer probes — retrieve without title/label cheats (fixed mind).
//! Spirit of benchmarks/transfer_test.py:
//!   - teach on content patterns A
//!   - probe with partial / noisy / paraphrased cues B
//!   - distractors in store; long delay
//!   - success = content identity, never title-token channel

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const Fixed = fixed.Fixed;

pub const TransferReport = struct {
    ok: bool,
    n_items: u32,
    n_distractors: u32,
    correct: u32,
    top1: f64,
    partial_correct: u32,
    partial_top1: f64,
    noisy_correct: u32,
    noisy_top1: f64,
    delay_steps: u32,
    spikes: u32,
};

const N_ITEMS: usize = 6;
const N_DIST: usize = 3;
const FEAT: usize = 8;
const DELAY: usize = 20;

fn makeItem(seed: u32, out: *[FEAT]Fixed) void {
    // Stronger separation than pure LCG noise — distinct bases per seed (pixel-id spirit)
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        const base_u: u32 = seed *% 41 +% @as(u32, @intCast(i)) *% 17 +% seed *% seed *% 3 +% 5;
        const a: i64 = @intCast(base_u % 181);
        out[i] = fixed.sub(fixed.div(fixed.fromInt(a), fixed.fromInt(90)), fixed.fromInt(1));
    }
}

fn partialCue(full: *const [FEAT]Fixed, out: *[FEAT]Fixed) void {
    // zero last third — no label/title channel
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        out[i] = if (i >= 5) 0 else full[i];
    }
}

/// Paraphrase / sensor noise: small fixed jitter, not a new identity.
fn noisyCue(full: *const [FEAT]Fixed, noise_seed: u32, out: *[FEAT]Fixed) void {
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        const n: i64 = @intCast((noise_seed *% 17 +% @as(u32, @intCast(i)) *% 3) % 9);
        const jit = fixed.div(fixed.sub(fixed.fromInt(n), fixed.fromInt(4)), fixed.fromInt(60));
        out[i] = fixed.clamp(fixed.add(full[i], jit), fixed.fromInt(-1), fixed.fromInt(1));
    }
}

pub fn runTransferProbe() TransferReport {
    var b = brain_f.BrainF.initSeeded(19, false);
    var store: memory_f.StoreF = .{};
    store.clear();

    var fulls: [N_ITEMS][FEAT]Fixed = undefined;
    var ids: [N_ITEMS]u32 = undefined;

    // Target items — tokens hold "title" hashes that MUST NOT be needed at retrieve
    var i: usize = 0;
    while (i < N_ITEMS) : (i += 1) {
        makeItem(@intCast(i + 3), &fulls[i]);
        // title tokens present in store (cheat channel) but retrieve is feature-only
        const title = memory_f.hashToken("TITLE_BAN");
        const tok = [_]u32{ title, title, 0, 0, 0, memory_f.hashToken("fsot") };
        ids[i] = store.encode(&b, fulls[i][0..], 0b100011, tok);
    }

    // Distractors — competing patterns in the same store
    var d_i: usize = 0;
    while (d_i < N_DIST) : (d_i += 1) {
        var dist: [FEAT]Fixed = undefined;
        makeItem(@intCast(100 + d_i * 7), &dist);
        const tok = [_]u32{ memory_f.hashToken("DIST"), 0, 0, 0, 0, memory_f.hashToken("noise") };
        _ = store.encode(&b, dist[0..], 0b000001, tok);
    }

    // Long delay / interference
    var ext: [brain_f.N_TOTAL]Fixed = .{fixed.fromDecimalStr("0.05")} ** brain_f.N_TOTAL;
    var d: usize = 0;
    while (d < DELAY) : (d += 1) {
        // mild ongoing drive so delay is not pure freeze
        if ((d % 7) == 0) {
            var u: usize = 0;
            while (u < brain_f.N_TOTAL) : (u += 1) {
                ext[u] = fixed.fromDecimalStr("0.07");
            }
        } else {
            var u: usize = 0;
            while (u < brain_f.N_TOTAL) : (u += 1) {
                ext[u] = fixed.fromDecimalStr("0.03");
            }
        }
        b.step(ext[0..]);
    }

    var correct: u32 = 0;
    var partial_correct: u32 = 0;
    var noisy_correct: u32 = 0;
    i = 0;
    while (i < N_ITEMS) : (i += 1) {
        var sim: Fixed = 0;
        const hit = store.retrieve(&b, fulls[i][0..], &sim);
        if (hit == ids[i]) correct += 1;

        var cue: [FEAT]Fixed = undefined;
        partialCue(&fulls[i], &cue);
        var sim2: Fixed = 0;
        const hit2 = store.retrieve(&b, cue[0..], &sim2);
        if (hit2 == ids[i]) partial_correct += 1;

        var ncue: [FEAT]Fixed = undefined;
        noisyCue(&fulls[i], @intCast(i + 11), &ncue);
        var sim3: Fixed = 0;
        const hit3 = store.retrieve(&b, ncue[0..], &sim3);
        if (hit3 == ids[i]) noisy_correct += 1;
    }

    const n_f: f64 = @floatFromInt(N_ITEMS);
    const top1 = @as(f64, @floatFromInt(correct)) / n_f;
    const ptop = @as(f64, @floatFromInt(partial_correct)) / n_f;
    const ntop = @as(f64, @floatFromInt(noisy_correct)) / n_f;
    // Stronger than baseline transfer: distractors + delay + noise; still content-only
    // Chance with 6 targets + 3 distractors ~ 1/9; require clearly above chance.
    const ok = top1 >= 0.5 and ptop >= 0.4 and ntop >= 0.5;
    return .{
        .ok = ok,
        .n_items = @intCast(N_ITEMS),
        .n_distractors = @intCast(N_DIST),
        .correct = correct,
        .top1 = top1,
        .partial_correct = partial_correct,
        .partial_top1 = ptop,
        .noisy_correct = noisy_correct,
        .noisy_top1 = ntop,
        .delay_steps = DELAY,
        .spikes = b.totalSpikes(),
    };
}
