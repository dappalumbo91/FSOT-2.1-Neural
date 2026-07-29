//! Cross-modal temporal bind — vision ⊗ audio → joint episode (fixed).
//! Spirit of sensory/cross_modal.py: co-occurrence binding, not filename tutors.
//! Either modality can cue the joint later. Speech-band energy is acoustic only
//! (no STT / no next-token language model).

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const Fixed = fixed.Fixed;

const FEAT: usize = 8;
const N_ITEMS: usize = 5;

pub const CrossModalReport = struct {
    ok: bool,
    n_items: u32,
    joint_correct: u32,
    joint_top1: f64,
    vision_only_correct: u32,
    vision_only_top1: f64,
    audio_only_correct: u32,
    audio_only_top1: f64,
    spikes: u32,
};

fn visionProto(seed: u32, out: *[FEAT]Fixed) void {
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        const u: u32 = seed *% 41 +% @as(u32, @intCast(i)) *% 13 +% 3;
        const a: i64 = @intCast(u % 181);
        out[i] = fixed.sub(fixed.div(fixed.fromInt(a), fixed.fromInt(90)), fixed.fromInt(1));
    }
}

fn audioProto(seed: u32, out: *[FEAT]Fixed) void {
    // distinct family from vision (different primes) — co-occur at bind time
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        const u: u32 = seed *% 53 +% @as(u32, @intCast(i)) *% 19 +% 7;
        const a: i64 = @intCast(u % 181);
        out[i] = fixed.sub(fixed.div(fixed.fromInt(a), fixed.fromInt(90)), fixed.fromInt(1));
    }
}

/// Joint feature = blend V and A (temporal co-occurrence signature).
fn jointFeats(v: *const [FEAT]Fixed, a: *const [FEAT]Fixed, out: *[FEAT]Fixed) void {
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        out[i] = fixed.add(
            fixed.mul(v[i], fixed.fromDecimalStr("0.55")),
            fixed.mul(a[i], fixed.fromDecimalStr("0.45")),
        );
    }
}

/// Partial cue: vision only (audio channel zeroed in blend).
fn visionCue(v: *const [FEAT]Fixed, out: *[FEAT]Fixed) void {
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        out[i] = fixed.mul(v[i], fixed.fromDecimalStr("0.55"));
    }
}

fn audioCue(a: *const [FEAT]Fixed, out: *[FEAT]Fixed) void {
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        out[i] = fixed.mul(a[i], fixed.fromDecimalStr("0.45"));
    }
}

pub fn runCrossModalProbe() CrossModalReport {
    var b = brain_f.BrainF.initSeeded(37, false);
    var store: memory_f.StoreF = .{};
    store.clear();

    var joints: [N_ITEMS][FEAT]Fixed = undefined;
    var visions: [N_ITEMS][FEAT]Fixed = undefined;
    var audios: [N_ITEMS][FEAT]Fixed = undefined;
    var ids: [N_ITEMS]u32 = undefined;

    var i: usize = 0;
    while (i < N_ITEMS) : (i += 1) {
        visionProto(@intCast(i + 2), &visions[i]);
        audioProto(@intCast(i + 2), &audios[i]);
        jointFeats(&visions[i], &audios[i], &joints[i]);
        // tokens mark modality co-bind — not used at retrieve
        const tok = [_]u32{
            memory_f.hashToken("av_joint"),
            memory_f.hashToken("see_hear"),
            0,
            0,
            0,
            memory_f.hashToken("cross"),
        };
        ids[i] = store.encode(&b, joints[i][0..], 0b100011, tok);
    }

    // delay
    var ext: [brain_f.N_TOTAL]Fixed = .{fixed.fromDecimalStr("0.04")} ** brain_f.N_TOTAL;
    var d: usize = 0;
    while (d < 12) : (d += 1) b.step(ext[0..]);

    var joint_ok: u32 = 0;
    var v_ok: u32 = 0;
    var a_ok: u32 = 0;
    i = 0;
    while (i < N_ITEMS) : (i += 1) {
        var sim: Fixed = 0;
        if (store.retrieve(&b, joints[i][0..], &sim) == ids[i]) joint_ok += 1;

        var vc: [FEAT]Fixed = undefined;
        visionCue(&visions[i], &vc);
        var sim_v: Fixed = 0;
        if (store.retrieve(&b, vc[0..], &sim_v) == ids[i]) v_ok += 1;

        var ac: [FEAT]Fixed = undefined;
        audioCue(&audios[i], &ac);
        var sim_a: Fixed = 0;
        if (store.retrieve(&b, ac[0..], &sim_a) == ids[i]) a_ok += 1;
    }

    const nf: f64 = @floatFromInt(N_ITEMS);
    const jtop = @as(f64, @floatFromInt(joint_ok)) / nf;
    const vtop = @as(f64, @floatFromInt(v_ok)) / nf;
    const atop = @as(f64, @floatFromInt(a_ok)) / nf;
    // joint must be strong; at least one single-modality above chance
    const ok = jtop >= 0.6 and (vtop >= 0.4 or atop >= 0.4);
    return .{
        .ok = ok,
        .n_items = N_ITEMS,
        .joint_correct = joint_ok,
        .joint_top1 = jtop,
        .vision_only_correct = v_ok,
        .vision_only_top1 = vtop,
        .audio_only_correct = a_ok,
        .audio_only_top1 = atop,
        .spikes = b.totalSpikes(),
    };
}
