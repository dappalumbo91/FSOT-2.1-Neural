//! Tutor-ablated pixel / pattern identity on fixed lattice (expanded multi-seed).
//! Spirit of character_pixel_id / media_pixel_id: features alone → name.
//! Synthetic RF-like patterns stand in for host media decode (real films later).

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const Fixed = fixed.Fixed;

pub const FEAT: usize = 8;
pub const N_CHARS: usize = 8;
pub const N_TRAIN: usize = 3;
pub const N_TEST: usize = 2;
pub const N_SEEDS: usize = 3;

const CHAR_NAMES = [_][]const u8{ "neo", "trinity", "alice", "wesker", "oracle", "morpheus", "claire", "becky" };

pub const PixelIdReport = struct {
    ok: bool,
    n_characters: u32,
    n_train: u32,
    n_test: u32,
    n_seeds: u32,
    correct: u32,
    top1: f64,
    multi_seed_mean: f64,
    chance: f64,
    tutor_ablated: bool,
    spikes: u32,
};

fn charFrame(char_i: u32, sample: u32, seed_tag: u32, out: *[FEAT]Fixed) void {
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        const base_u: u32 = char_i *% 41 +% @as(u32, @intCast(i)) *% 13 +% 3 +% seed_tag *% 2;
        const base_num: i64 = @intCast(base_u % 181);
        const base = fixed.sub(fixed.div(fixed.fromInt(base_num), fixed.fromInt(90)), fixed.fromInt(1));
        const jn: i64 = @intCast((sample *% 7 +% @as(u32, @intCast(i)) *% 3 +% char_i +% seed_tag) % 11);
        const jit = fixed.div(fixed.sub(fixed.fromInt(jn), fixed.fromInt(5)), fixed.fromInt(80));
        out[i] = fixed.clamp(fixed.add(base, jit), fixed.fromInt(-1), fixed.fromInt(1));
    }
}

fn findEpisodeWho(store: *const memory_f.StoreF, id: u32) u32 {
    var j: usize = 0;
    while (j < store.n) : (j += 1) {
        if (store.episodes[j].id == id) return store.episodes[j].tokens[0];
    }
    return 0;
}

fn runOneSeed(brain_seed: u32) struct { correct: u32, n_test: u32, spikes: u32 } {
    var b = brain_f.BrainF.initSeeded(brain_seed, false);
    var store: memory_f.StoreF = .{};
    store.clear();

    var name_tok: [N_CHARS]u32 = undefined;
    var c: u32 = 0;
    while (c < N_CHARS) : (c += 1) name_tok[c] = memory_f.hashToken(CHAR_NAMES[c]);

    c = 0;
    while (c < N_CHARS) : (c += 1) {
        var s: u32 = 0;
        while (s < N_TRAIN) : (s += 1) {
            var feats: [FEAT]Fixed = undefined;
            charFrame(c, s, brain_seed, &feats);
            const tok = [_]u32{
                name_tok[c],
                memory_f.hashToken("frame"),
                0,
                0,
                0,
                memory_f.hashToken("pixel"),
            };
            _ = store.encode(&b, feats[0..], 0b100011, tok);
        }
    }

    var ext: [brain_f.N_TOTAL]Fixed = .{fixed.fromDecimalStr("0.04")} ** brain_f.N_TOTAL;
    var d: usize = 0;
    while (d < 10) : (d += 1) b.step(ext[0..]);

    var correct: u32 = 0;
    var n_test: u32 = 0;
    c = 0;
    while (c < N_CHARS) : (c += 1) {
        var s: u32 = 0;
        while (s < N_TEST) : (s += 1) {
            const sample = @as(u32, @intCast(N_TRAIN)) + s + 1;
            var cue: [FEAT]Fixed = undefined;
            charFrame(c, sample, brain_seed, &cue);
            var sim: Fixed = 0;
            const hit = store.retrieve(&b, cue[0..], &sim);
            const who = findEpisodeWho(&store, hit);
            if (who == name_tok[c] and who != 0) correct += 1;
            n_test += 1;
        }
    }
    return .{ .correct = correct, .n_test = n_test, .spikes = b.totalSpikes() };
}

pub fn runPixelIdProbe() PixelIdReport {
    const seeds = [_]u32{ 23, 29, 41 };
    var sum_top: f64 = 0;
    var total_correct: u32 = 0;
    var total_test: u32 = 0;
    var spikes: u32 = 0;
    var si: usize = 0;
    while (si < N_SEEDS) : (si += 1) {
        const r = runOneSeed(seeds[si]);
        const t1 = @as(f64, @floatFromInt(r.correct)) / @as(f64, @floatFromInt(r.n_test));
        sum_top += t1;
        total_correct += r.correct;
        total_test += r.n_test;
        spikes += r.spikes;
    }
    const multi = sum_top / @as(f64, @floatFromInt(N_SEEDS));
    const top1 = @as(f64, @floatFromInt(total_correct)) / @as(f64, @floatFromInt(total_test));
    const chance = 1.0 / @as(f64, @floatFromInt(N_CHARS));
    const ok = multi >= 0.55 and multi > chance + 0.2 and total_test >= 8;
    return .{
        .ok = ok,
        .n_characters = N_CHARS,
        .n_train = N_CHARS * N_TRAIN,
        .n_test = total_test,
        .n_seeds = N_SEEDS,
        .correct = total_correct,
        .top1 = top1,
        .multi_seed_mean = multi,
        .chance = chance,
        .tutor_ablated = true,
        .spikes = spikes,
    };
}
