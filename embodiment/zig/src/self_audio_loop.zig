//! Speaker ↔ mic closed loop with *scene analysis* (not volume war).
//!
//! 1. Predict self (efference copy / bone-like internal)
//! 2. Hear mic (air path — full of room noise)
//! 3. AmbientScene strips baseline + known noise classes
//! 4. Match cleaned mic to predicted self
//! 5. Residual after self-cancel = novel world / unignored noise
//!
//! Doctrine: animals analyze the stream, identify noise, selectively ignore it.

const std = @import("std");
const builtin = @import("builtin");
const fixed = @import("fixed.zig");
const speech_f = @import("speech_organ_fixed.zig");
const host_f = @import("host_senses_fixed.zig");
const audio_out = @import("host_audio_out_fixed.zig");
const scene = @import("ambient_scene_fixed.zig");
const Fixed = fixed.Fixed;

pub const FEAT: usize = 8;

pub fn acousticToFeats(ac: speech_f.Acoustic, out: *[FEAT]Fixed) void {
    var pcm: [audio_out.PCM_MAX]i16 = undefined;
    const n = audio_out.acousticToPcm(ac, pcm[0..]);
    if (n > 32) {
        host_f.pcmToAudioFeats(pcm[0..n], out);
        return;
    }
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        out[i] = if (i < speech_f.ACOUSTIC_N) ac.ch[i] else 0;
    }
}

pub fn cosineFeats(a: *const [FEAT]Fixed, b: *const [FEAT]Fixed) Fixed {
    var dot: Fixed = 0;
    var na: Fixed = 0;
    var nb: Fixed = 0;
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        dot = fixed.add(dot, fixed.mul(a[i], b[i]));
        na = fixed.add(na, fixed.mul(a[i], a[i]));
        nb = fixed.add(nb, fixed.mul(b[i], b[i]));
    }
    if (fixed.lt(na, fixed.fromDecimalStr("0.000000000001")) or fixed.lt(nb, fixed.fromDecimalStr("0.000000000001"))) return 0;
    const den = fixed.mul(fixed.sqrt(na), fixed.sqrt(nb));
    if (fixed.lt(den, fixed.fromDecimalStr("0.000000000001"))) return 0;
    return fixed.div(dot, den);
}

pub fn residualWorld(mic: *const [FEAT]Fixed, pred: *const [FEAT]Fixed, alpha: Fixed, out: *[FEAT]Fixed) void {
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        out[i] = fixed.clamp(fixed.sub(mic[i], fixed.mul(pred[i], alpha)), fixed.fromInt(-1), fixed.fromInt(1));
    }
}

pub fn energy(f: *const [FEAT]Fixed) Fixed {
    var s: Fixed = 0;
    var i: usize = 0;
    while (i < 4) : (i += 1) s = fixed.add(s, fixed.abs(f[i]));
    return fixed.div(s, fixed.fromInt(4));
}

fn pcmShapeCorr(pred: []const i16, mic: []const i16) f64 {
    if (pred.len < 64 or mic.len < 64) return 0;
    const n = @min(pred.len, mic.len);
    const step = @max(@as(usize, 1), n / 128);
    var sum_p: f64 = 0;
    var sum_m: f64 = 0;
    var cnt: f64 = 0;
    var i: usize = 0;
    while (i < n) : (i += step) {
        sum_p += @as(f64, @floatFromInt(pred[i]));
        sum_m += @as(f64, @floatFromInt(mic[i]));
        cnt += 1;
    }
    if (cnt < 8) return 0;
    const mp = sum_p / cnt;
    const mm = sum_m / cnt;
    var num: f64 = 0;
    var dp: f64 = 0;
    var dm: f64 = 0;
    i = 0;
    while (i < n) : (i += step) {
        const a = @as(f64, @floatFromInt(pred[i])) - mp;
        const b = @as(f64, @floatFromInt(mic[i])) - mm;
        num += a * b;
        dp += a * a;
        dm += b * b;
    }
    const den = @sqrt(dp * dm);
    if (den < 1e-9) return 0;
    return num / den;
}

pub const SelfHearResult = struct {
    pred: [FEAT]Fixed = .{0} ** FEAT,
    mic_raw: [FEAT]Fixed = .{0} ** FEAT,
    mic_clean: [FEAT]Fixed = .{0} ** FEAT,
    residual: [FEAT]Fixed = .{0} ** FEAT,
    match: Fixed = 0,
    match_raw: Fixed = 0,
    pcm_corr: f64 = 0,
    self_heard_air: bool = false,
    self_heard_internal: bool = true,
    ambient_high: bool = false,
    noise_ignored: bool = false,
    noise_src: i32 = -1,
    mic_ok: bool = false,
    self_heard: bool = false,
};

/// After speakers play: mic → scene filter → match predicted self.
pub fn hearSelfAfterSpeak(
    predicted: speech_f.Acoustic,
    match_thresh: Fixed,
    analyzer: *scene.SceneAnalyzer,
) SelfHearResult {
    var r: SelfHearResult = .{};

    var pred_pcm: [audio_out.PCM_MAX]i16 = undefined;
    const np = audio_out.acousticToPcm(predicted, pred_pcm[0..]);
    if (np > 32) {
        host_f.pcmToAudioFeats(pred_pcm[0..np], &r.pred);
    } else {
        acousticToFeats(predicted, &r.pred);
    }

    // Capture long enough for long drones / sirens (~350 ms + margin)
    var mic_pcm: [8192]i16 = undefined;
    const ns = if (builtin.os.tag == .windows)
        @import("host_senses_windows.zig").captureMic(mic_pcm[0..])
    else
        @import("host_senses_linux.zig").captureMic(mic_pcm[0..]);

    if (ns > 32) {
        host_f.pcmToAudioFeats(mic_pcm[0..ns], &r.mic_raw);
        r.mic_ok = true;
        r.pcm_corr = pcmShapeCorr(pred_pcm[0..np], mic_pcm[0..ns]);
    } else {
        r.mic_raw = r.pred;
        r.mic_ok = false;
    }

    // --- scene analysis: strip known noise, keep figure ---
    const cleaned = analyzer.cleanMicForSelf(&r.mic_raw, &r.pred, &r.mic_clean);
    r.noise_ignored = cleaned.ignored_noise;
    r.noise_src = analyzer.last_match_src;
    r.match_raw = cosineFeats(&r.pred, &r.mic_raw);
    r.match = cleaned.match; // match on *filtered* mic

    const match_f = fixed.toF64(r.match);
    const match_raw_f = fixed.toF64(r.match_raw);
    const feat_ok = match_f > fixed.toF64(match_thresh);
    const pcm_ok = r.pcm_corr > 0.10;
    const soft_ok = match_f > 0.08 or (match_f > match_raw_f + 0.05); // filter helped
    r.self_heard_air = r.mic_ok and (feat_ok or pcm_ok or soft_ok);
    r.self_heard_internal = true;
    r.self_heard = r.self_heard_air or r.self_heard_internal;

    const alpha = if (r.self_heard_air) fixed.fromDecimalStr("0.7") else fixed.fromDecimalStr("0.35");
    // residual world from cleaned mic (noise already reduced)
    residualWorld(&r.mic_clean, &r.pred, alpha, &r.residual);
    r.ambient_high = fixed.gt(energy(&r.residual), fixed.fromDecimalStr("0.28"));
    return r;
}
