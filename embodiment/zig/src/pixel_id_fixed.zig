//! Tutor-ablated pixel / pattern identity on fixed lattice.
//! Spirit of character_pixel_id / media_pixel_id: features alone → name.
//! No path/title/subtitle/lexicon injected into the *test* cue.
//! Synthetic RF-like 8-d patterns stand in for host media decode.

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const Fixed = fixed.Fixed;

pub const FEAT: usize = 8;
pub const N_CHARS: usize = 5;
pub const N_TRAIN: usize = 2;
pub const N_TEST: usize = 2;

const CHAR_NAMES = [_][]const u8{ "neo", "trinity", "alice", "wesker", "oracle" };

pub const PixelIdReport = struct {
    ok: bool,
    n_characters: u32,
    n_train: u32,
    n_test: u32,
    correct: u32,
    top1: f64,
    chance: f64,
    tutor_ablated: bool,
    spikes: u32,
};

/// Distinct character prototype + small sample jitter (train/test frames).
fn charFrame(char_i: u32, sample: u32, out: *[FEAT]Fixed) void {
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        // base direction unique per character (spread in [-1, 1])
        const base_u: u32 = char_i *% 41 +% @as(u32, @intCast(i)) *% 13 +% 3;
        const base_num: i64 = @intCast(base_u % 181);
        const base = fixed.sub(fixed.div(fixed.fromInt(base_num), fixed.fromInt(90)), fixed.fromInt(1));
        // frame jitter — small, not identity-destroying
        const jn: i64 = @intCast((sample *% 7 +% @as(u32, @intCast(i)) *% 3 +% char_i) % 11);
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

pub fn runPixelIdProbe() PixelIdReport {
    var b = brain_f.BrainF.initSeeded(23, false);
    var store: memory_f.StoreF = .{};
    store.clear();

    const name_tok: [N_CHARS]u32 = .{
        memory_f.hashToken(CHAR_NAMES[0]),
        memory_f.hashToken(CHAR_NAMES[1]),
        memory_f.hashToken(CHAR_NAMES[2]),
        memory_f.hashToken(CHAR_NAMES[3]),
        memory_f.hashToken(CHAR_NAMES[4]),
    };

    // --- train: caption/name allowed only as teaching token (who slot) ---
    var c: u32 = 0;
    while (c < N_CHARS) : (c += 1) {
        var s: u32 = 0;
        while (s < N_TRAIN) : (s += 1) {
            var feats: [FEAT]Fixed = undefined;
            charFrame(c, s, &feats);
            const tok = [_]u32{
                name_tok[c],
                memory_f.hashToken("frame"),
                0,
                0,
                0,
                memory_f.hashToken("pixel"),
            };
            // who + what + how filled; test will not use tokens
            _ = store.encode(&b, feats[0..], 0b100011, tok);
        }
    }

    // delay / interference
    var ext: [brain_f.N_TOTAL]Fixed = .{fixed.fromDecimalStr("0.04")} ** brain_f.N_TOTAL;
    var d: usize = 0;
    while (d < 12) : (d += 1) b.step(ext[0..]);

    // --- test: tutor-ablated — features only, never name/path ---
    var correct: u32 = 0;
    var n_test: u32 = 0;
    c = 0;
    while (c < N_CHARS) : (c += 1) {
        var s: u32 = 0;
        while (s < N_TEST) : (s += 1) {
            // held-out sample indices (not train 0..N_TRAIN-1)
            const sample: u32 = @as(u32, @intCast(N_TRAIN)) + s + 1;
            var cue: [FEAT]Fixed = undefined;
            charFrame(c, sample, &cue);
            var sim: Fixed = 0;
            const hit = store.retrieve(&b, cue[0..], &sim);
            const who = findEpisodeWho(&store, hit);
            if (who == name_tok[c] and who != 0) correct += 1;
            n_test += 1;
        }
    }

    const top1 = if (n_test == 0) 0.0 else @as(f64, @floatFromInt(correct)) / @as(f64, @floatFromInt(n_test));
    const chance = 1.0 / @as(f64, @floatFromInt(N_CHARS));
    // Gate: clearly above chance; synthetic lattice floor (not open-world claim)
    const ok = top1 >= 0.6 and top1 > chance + 0.15 and n_test >= 4;
    return .{
        .ok = ok,
        .n_characters = N_CHARS,
        .n_train = N_CHARS * N_TRAIN,
        .n_test = n_test,
        .correct = correct,
        .top1 = top1,
        .chance = chance,
        .tutor_ablated = true,
        .spikes = b.totalSpikes(),
    };
}
