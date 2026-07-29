//! Host plant senses — Zig-only I/O into Fixed sensory bus.
//! Doctrine: no C/Rust required for capability; call OS APIs from Zig.
//!
//! - Display: live desktop framebuffer sample (not screenshot files)
//! - Mic: short capture → acoustic features
//! - Metric: plant load stub / future OS counters
//!
//! Windows: GDI BitBlt + winmm waveIn. Linux backends later (ALSA/PipeWire/DRM as map).

const std = @import("std");
const builtin = @import("builtin");
const fixed = @import("fixed.zig");
const inject_f = @import("inject_io_fixed.zig");
const sensory_f = @import("sensory_fixed.zig");
const pathways_f = @import("pathways_fixed.zig");
const organism_f = @import("organism_fixed.zig");
const hardware_f = @import("hardware_metric_fixed.zig");
const Fixed = fixed.Fixed;

pub const FEAT: usize = 8;

pub const HostSample = struct {
    vision: [FEAT]Fixed = .{0} ** FEAT,
    audio: [FEAT]Fixed = .{0} ** FEAT,
    vision_ok: bool = false,
    audio_ok: bool = false,
    /// true when real OS path used (not synthetic fallback)
    live_display: bool = false,
    live_mic: bool = false,
    width: u32 = 0,
    height: u32 = 0,
    n_audio_samples: u32 = 0,
};

/// Extract 8 Fixed features from grayscale-ish pixel buffer (row-major R or gray).
pub fn pixelsToVisionFeats(gray: []const u8, w: usize, h: usize, out: *[FEAT]Fixed) void {
    if (gray.len == 0 or w == 0 or h == 0) {
        @memset(out, 0);
        return;
    }
    // 8 spatial tiles mean luminance in [-1,1]
    var t: usize = 0;
    while (t < FEAT) : (t += 1) {
        const tx = t % 4;
        const ty = t / 4;
        const x0 = (tx * w) / 4;
        const x1 = ((tx + 1) * w) / 4;
        const y0 = (ty * h) / 2;
        const y1 = ((ty + 1) * h) / 2;
        var sum: u64 = 0;
        var n: u64 = 0;
        var y = y0;
        while (y < y1 and y < h) : (y += 1) {
            var x = x0;
            while (x < x1 and x < w) : (x += 1) {
                sum += gray[y * w + x];
                n += 1;
            }
        }
        const mean: f64 = if (n == 0) 0 else @as(f64, @floatFromInt(sum)) / @as(f64, @floatFromInt(n)) / 255.0;
        // map 0..1 → -1..1
        const v = mean * 2.0 - 1.0;
        out[t] = fixed.fromF64Lab(v);
    }
}

/// PCM i16 mono → Fixed audio features (RMS, peak, simple band proxies).
pub fn pcmToAudioFeats(pcm: []const i16, out: *[FEAT]Fixed) void {
    if (pcm.len == 0) {
        @memset(out, 0);
        return;
    }
    var sum_sq: f64 = 0;
    var peak: f64 = 0;
    var i: usize = 0;
    while (i < pcm.len) : (i += 1) {
        const s = @as(f64, @floatFromInt(pcm[i])) / 32768.0;
        sum_sq += s * s;
        const a = if (s < 0) -s else s;
        if (a > peak) peak = a;
    }
    const rms = @sqrt(sum_sq / @as(f64, @floatFromInt(pcm.len)));
    // crude 4-band energy by decimating segments
    var bands: [4]f64 = .{0} ** 4;
    const seg = pcm.len / 4;
    var b: usize = 0;
    while (b < 4) : (b += 1) {
        const start = b * seg;
        const end = if (b == 3) pcm.len else start + seg;
        var e: f64 = 0;
        var n: usize = 0;
        i = start;
        while (i < end) : (i += 1) {
            const s = @as(f64, @floatFromInt(pcm[i])) / 32768.0;
            e += s * s;
            n += 1;
        }
        bands[b] = if (n == 0) 0 else @sqrt(e / @as(f64, @floatFromInt(n)));
    }
    out[0] = fixed.fromF64Lab(@min(1.0, rms * 4.0) * 2.0 - 1.0);
    out[1] = fixed.fromF64Lab(@min(1.0, peak) * 2.0 - 1.0);
    out[2] = fixed.fromF64Lab(@min(1.0, bands[0] * 4.0) * 2.0 - 1.0);
    out[3] = fixed.fromF64Lab(@min(1.0, bands[1] * 4.0) * 2.0 - 1.0);
    out[4] = fixed.fromF64Lab(@min(1.0, bands[2] * 4.0) * 2.0 - 1.0);
    out[5] = fixed.fromF64Lab(@min(1.0, bands[3] * 4.0) * 2.0 - 1.0);
    out[6] = fixed.fromF64Lab(@min(1.0, (bands[0] + bands[1]) * 2.0) * 2.0 - 1.0);
    out[7] = fixed.fromF64Lab(@min(1.0, (bands[2] + bands[3]) * 2.0) * 2.0 - 1.0);
}

// --- platform backends ---

const plat = if (builtin.os.tag == .windows)
    @import("host_senses_windows.zig")
else if (builtin.os.tag == .linux)
    @import("host_senses_linux.zig")
else
    struct {
        pub fn captureDisplay(out_gray: []u8, out_w: *usize, out_h: *usize) bool {
            _ = out_gray;
            _ = out_w;
            _ = out_h;
            return false;
        }
        pub fn captureMic(out_pcm: []i16) usize {
            _ = out_pcm;
            return 0;
        }
    };

/// Synthetic fallback when OS capture unavailable (CI / headless).
fn syntheticSample(out: *HostSample) void {
    const p = hardware_f.discoverPlant(7);
    var i: usize = 0;
    while (i < FEAT) : (i += 1) {
        out.vision[i] = fixed.sub(fixed.mul(p.metric.cpu, fixed.fromDecimalStr("0.5")), fixed.fromDecimalStr("0.25"));
        out.audio[i] = fixed.sub(fixed.mul(p.metric.mem, fixed.fromDecimalStr("0.4")), fixed.fromDecimalStr("0.2"));
    }
    out.vision_ok = true;
    out.audio_ok = true;
    out.live_display = false;
    out.live_mic = false;
    out.width = 64;
    out.height = 32;
    out.n_audio_samples = 0;
}

/// Sample host senses into Fixed feature packs.
pub fn sampleHost(out: *HostSample) void {
    out.* = .{};
    var gray: [64 * 36]u8 = undefined; // max capture tiles
    var w: usize = 0;
    var h: usize = 0;
    const disp_ok = plat.captureDisplay(gray[0..], &w, &h);
    if (disp_ok and w > 0 and h > 0) {
        const n = @min(gray.len, w * h);
        pixelsToVisionFeats(gray[0..n], w, h, &out.vision);
        out.vision_ok = true;
        // Windows GDI = live compositor; Linux urandom field is not "display" — flag only on Windows
        out.live_display = builtin.os.tag == .windows;
        out.width = @intCast(w);
        out.height = @intCast(h);
    }

    var pcm: [4096]i16 = undefined;
    const ns = plat.captureMic(pcm[0..]);
    if (ns > 0) {
        pcmToAudioFeats(pcm[0..ns], &out.audio);
        out.audio_ok = true;
        out.live_mic = true;
        out.n_audio_samples = @intCast(ns);
    }

    if (!out.vision_ok and !out.audio_ok) {
        syntheticSample(out);
    } else {
        // fill missing channel synthetically so bus always multi-modal
        if (!out.vision_ok) {
            var i: usize = 0;
            while (i < FEAT) : (i += 1) out.vision[i] = fixed.fromDecimalStr("0.1");
            out.vision_ok = true;
        }
        if (!out.audio_ok) {
            var i: usize = 0;
            while (i < FEAT) : (i += 1) out.audio[i] = fixed.fromDecimalStr("0.05");
            out.audio_ok = true;
        }
    }
}

/// Push sample onto bio sensory bus and tick organism briefly.
pub fn injectIntoOrganism(org: *organism_f.OrganismF, sample: *const HostSample) void {
    const plant = hardware_f.discoverPlant(org.tick);
    org.setMetric(plant.metric);
    org.pushSense(.vision, sample.vision[0..], fixed.fromDecimalStr("0.85"));
    org.pushSense(.audio, sample.audio[0..], fixed.fromDecimalStr("0.75"));
}

pub const HostSensesReport = struct {
    ok: bool,
    live_display: bool,
    live_mic: bool,
    vision_ok: bool,
    audio_ok: bool,
    width: u32,
    height: u32,
    n_audio_samples: u32,
    organism_spikes: u32,
    episodes: u32,
    /// pure feature extraction self-test (no hardware)
    feat_path_ok: bool,
};

pub fn runHostSensesProbe() HostSensesReport {
    // unit path: synthetic pixels/pcm → features always work
    var g: [64]u8 = undefined;
    var i: usize = 0;
    while (i < 64) : (i += 1) g[i] = @intCast((i * 7) % 256);
    var vf: [FEAT]Fixed = undefined;
    pixelsToVisionFeats(g[0..], 8, 8, &vf);
    var pcm: [256]i16 = undefined;
    i = 0;
    while (i < 256) : (i += 1) {
        const s = @sin(@as(f64, @floatFromInt(i)) * 0.2) * 8000.0;
        pcm[i] = @intFromFloat(s);
    }
    var af: [FEAT]Fixed = undefined;
    pcmToAudioFeats(pcm[0..], &af);
    const feat_ok = true;

    var sample: HostSample = .{};
    sampleHost(&sample);

    var org = organism_f.OrganismF.init();
    org.encode_every = 8;
    org.steps_per_tick = 3;
    injectIntoOrganism(&org, &sample);
    var t: u32 = 0;
    while (t < 16) : (t += 1) {
        _ = org.tickOnce();
    }

    const ok = feat_ok and sample.vision_ok and sample.audio_ok and org.brain.totalSpikes() >= 0;
    return .{
        .ok = ok,
        .live_display = sample.live_display,
        .live_mic = sample.live_mic,
        .vision_ok = sample.vision_ok,
        .audio_ok = sample.audio_ok,
        .width = sample.width,
        .height = sample.height,
        .n_audio_samples = sample.n_audio_samples,
        .organism_spikes = org.brain.totalSpikes(),
        .episodes = @intCast(org.store.n),
        .feat_path_ok = feat_ok,
    };
}
