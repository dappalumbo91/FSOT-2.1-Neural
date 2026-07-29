//! Auditory scene analysis — analyze noise, label it, selectively ignore.
//!
//! Biological doctrine (human / animal):
//!   The world is full of sound. Sensing is not "louder wins."
//!   The system *profiles* background, *recognizes* recurring sources,
//!   and *attenuates* what has been classified as ignore-able noise so
//!   figure (own voice, novel signal) can stand out.
//!
//! This is selective attention + habituation on Fixed features — not an LLM.

const std = @import("std");
const builtin = @import("builtin");
const fixed = @import("fixed.zig");
const host_f = @import("host_senses_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const eeg = @import("eeg_gate_anchors_fixed.zig");
const Fixed = fixed.Fixed;

pub const FEAT: usize = 8;
pub const MAX_NOISE_SOURCES: usize = 8;

pub const NoiseSource = struct {
    /// running mean feature signature of this noise class
    profile: [FEAT]Fixed = .{0} ** FEAT,
    /// how many times observed
    hits: u32 = 0,
    /// energy scale of this source
    energy: Fixed = 0,
    /// ignore weight 0..1 (higher = more suppressed in figure path)
    ignore: Fixed = fixed.fromDecimalStr("0.85"),
    /// label hash (e.g. "room_hum", "kids_chaos", "hvac")
    label: u32 = 0,
    valid: bool = false,
};

pub const SceneAnalyzer = struct {
    /// continuous ambient baseline (EMA of non-speech mic)
    baseline: [FEAT]Fixed = .{0} ** FEAT,
    baseline_n: u32 = 0,
    baseline_energy: Fixed = 0,
    sources: [MAX_NOISE_SOURCES]NoiseSource = [_]NoiseSource{.{}} ** MAX_NOISE_SOURCES,
    n_sources: usize = 0,
    /// samples used to build scene
    n_samples: u32 = 0,
    n_filtered: u32 = 0,
    n_ignored: u32 = 0,
    last_match_src: i32 = -1,
    last_novelty: Fixed = 0,

    pub fn init() SceneAnalyzer {
        return .{};
    }

    fn energyOf(f: *const [FEAT]Fixed) Fixed {
        var s: Fixed = 0;
        var i: usize = 0;
        while (i < 4) : (i += 1) s = fixed.add(s, fixed.abs(f[i]));
        return fixed.div(s, fixed.fromInt(4));
    }

    fn cosine(a: *const [FEAT]Fixed, b: *const [FEAT]Fixed) Fixed {
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

    fn emaInto(dst: *[FEAT]Fixed, src: *const [FEAT]Fixed, alpha: Fixed) void {
        const keep = fixed.sub(fixed.fromInt(1), alpha);
        var i: usize = 0;
        while (i < FEAT) : (i += 1) {
            dst[i] = fixed.add(fixed.mul(dst[i], keep), fixed.mul(src[i], alpha));
        }
    }

    /// Capture one ambient mic snapshot (when not speaking).
    pub fn sampleMic(out: *[FEAT]Fixed) bool {
        var pcm: [4096]i16 = undefined;
        const ns = if (builtin.os.tag == .windows)
            @import("host_senses_windows.zig").captureMic(pcm[0..])
        else
            @import("host_senses_linux.zig").captureMic(pcm[0..]);
        if (ns < 32) return false;
        host_f.pcmToAudioFeats(pcm[0..ns], out);
        return true;
    }

    /// Observe ambient (call on quiet / non-speak ticks). Builds baseline + noise classes.
    pub fn observeAmbient(self: *SceneAnalyzer, mic: *const [FEAT]Fixed) void {
        self.n_samples += 1;
        const e = energyOf(mic);
        // EMA baseline
        if (self.baseline_n == 0) {
            @memcpy(self.baseline[0..], mic[0..]);
            self.baseline_energy = e;
        } else {
            emaInto(&self.baseline, mic, fixed.fromDecimalStr("0.12"));
            self.baseline_energy = fixed.add(
                fixed.mul(self.baseline_energy, fixed.fromDecimalStr("0.88")),
                fixed.mul(e, fixed.fromDecimalStr("0.12")),
            );
        }
        self.baseline_n += 1;

        // Match existing noise source or allocate new class
        var best_i: i32 = -1;
        var best_c: Fixed = fixed.fromDecimalStr("-1");
        var i: usize = 0;
        while (i < self.n_sources) : (i += 1) {
            if (!self.sources[i].valid) continue;
            const c = cosine(mic, &self.sources[i].profile);
            if (fixed.gt(c, best_c)) {
                best_c = c;
                best_i = @intCast(i);
            }
        }

        // high similarity → same recurring noise (kids / TV / HVAC family)
        // match thresh from EEG-anchor chain (1/φ soft), not a free knob
        const class_thresh = eeg.noiseClassMatchThresh();
        if (best_i >= 0 and fixed.gt(best_c, class_thresh)) {
            const si: usize = @intCast(best_i);
            emaInto(&self.sources[si].profile, mic, fixed.fromDecimalStr("0.2"));
            self.sources[si].hits += 1;
            self.sources[si].energy = fixed.add(
                fixed.mul(self.sources[si].energy, fixed.fromDecimalStr("0.8")),
                fixed.mul(e, fixed.fromDecimalStr("0.2")),
            );
            // more hits → more confident ignore (habituation)
            if (self.sources[si].hits > 5) {
                self.sources[si].ignore = fixed.fromDecimalStr("0.9");
            } else if (self.sources[si].hits > 2) {
                self.sources[si].ignore = fixed.fromDecimalStr("0.75");
            }
            self.last_match_src = best_i;
        } else if (self.n_sources < MAX_NOISE_SOURCES and fixed.gt(e, eeg.noveltyFloor())) {
            // novel noise class — provisional ignore from noiseClassMatchThresh
            const si = self.n_sources;
            self.sources[si] = .{
                .profile = mic.*,
                .hits = 1,
                .energy = e,
                .ignore = class_thresh, // provisional until stable
                .label = memory_f.hashToken("ambient_src"),
                .valid = true,
            };
            // diversify labels by index
            self.sources[si].label = memory_f.hashToken("ambient_src") +% @as(u32, @intCast(si));
            self.n_sources += 1;
            self.last_match_src = @intCast(si);
        } else {
            self.last_match_src = -1;
        }
    }

    /// Subtract baseline + matched noise sources from mic → figure path.
    /// Returns filtered features and whether content was largely ignored as known noise.
    pub fn filterMic(self: *SceneAnalyzer, mic: *const [FEAT]Fixed, out: *[FEAT]Fixed) struct {
        ignored: bool,
        match_src: i32,
        novelty: Fixed,
        suppressed: Fixed,
    } {
        // start from mic
        @memcpy(out[0..], mic[0..]);
        var suppressed: Fixed = 0;

        // 1) remove continuous baseline (room floor)
        if (self.baseline_n >= 2) {
            var i: usize = 0;
            while (i < FEAT) : (i += 1) {
                const sub = fixed.mul(self.baseline[i], fixed.fromDecimalStr("0.85"));
                out[i] = fixed.sub(out[i], sub);
            }
            suppressed = fixed.add(suppressed, fixed.fromDecimalStr("0.3"));
        }

        // 2) remove best-matching known noise source (selective ignore)
        // suppress floor: half of class-match (EEG-anchored chain)
        var best_i: i32 = -1;
        var best_c: Fixed = fixed.mul(eeg.noiseClassMatchThresh(), fixed.fromDecimalStr("0.6"));
        var si: usize = 0;
        while (si < self.n_sources) : (si += 1) {
            if (!self.sources[si].valid) continue;
            const c = cosine(out, &self.sources[si].profile);
            if (fixed.gt(c, best_c)) {
                best_c = c;
                best_i = @intCast(si);
            }
        }
        if (best_i >= 0) {
            const s = self.sources[@intCast(best_i)];
            const alpha = fixed.mul(s.ignore, best_c); // stronger match → more ignore
            var i: usize = 0;
            while (i < FEAT) : (i += 1) {
                out[i] = fixed.sub(out[i], fixed.mul(s.profile[i], alpha));
            }
            suppressed = fixed.add(suppressed, alpha);
            self.n_filtered += 1;
            if (fixed.gt(alpha, fixed.fromDecimalStr("0.5"))) self.n_ignored += 1;
        }

        // clamp
        var i: usize = 0;
        while (i < FEAT) : (i += 1) {
            out[i] = fixed.clamp(out[i], fixed.fromInt(-1), fixed.fromInt(1));
        }

        const nov = energyOf(out);
        self.last_novelty = nov;
        self.last_match_src = best_i;
        // "ignored" = little novelty left after stripping known noise (EEG novelty floor)
        const ignored = fixed.lt(nov, eeg.noveltyFloor()) and best_i >= 0;
        return .{
            .ignored = ignored,
            .match_src = best_i,
            .novelty = nov,
            .suppressed = suppressed,
        };
    }

    /// Full pipeline for self-hear: filter noise from mic, then match to predicted self.
    pub fn cleanMicForSelf(
        self: *SceneAnalyzer,
        mic: *const [FEAT]Fixed,
        pred: *const [FEAT]Fixed,
        cleaned: *[FEAT]Fixed,
    ) struct { match: Fixed, ignored_noise: bool, novelty: Fixed } {
        const fr = self.filterMic(mic, cleaned);
        // cosine(pred, cleaned)
        const m = cosine(pred, cleaned);
        return .{ .match = m, .ignored_noise = fr.ignored, .novelty = fr.novelty };
    }
};

pub fn captureMicFeats(out: *[FEAT]Fixed) bool {
    return SceneAnalyzer.sampleMic(out);
}
