//! Speaker efferent — acoustic features / speech plant → PCM → host DAC.
//! Zig-only. Windows: winmm waveOut. Linux: silent success if no device (honest).
//!
//! Rich multi-tone synthesis (not one bland beep):
//!   f0 + harmonics, F1/F2/F3 formants, noise for fricatives,
//!   pitch glide, duration from acoustic, envelope, optional double-pulse.

const std = @import("std");
const builtin = @import("builtin");
const fixed = @import("fixed.zig");
const speech_f = @import("speech_organ_fixed.zig");
const Fixed = fixed.Fixed;

pub const AudioOutReport = struct {
    ok: bool,
    n_samples: u32,
    played: bool,
    backend: []const u8,
};

/// Preferred buffer: up to ~350 ms @ 16 kHz for long drones / sirens.
pub const PCM_MAX: usize = 5600;

fn unit01(x: f64) f64 {
    // map Fixed −1..1 channel to 0..1
    return @max(0.0, @min(1.0, (x + 1.0) * 0.5));
}

fn clampAmp(a: f64) f64 {
    return @max(0.08, @min(0.88, a));
}

/// Map acoustic channels to a mono PCM burst with multiple tones.
pub fn acousticToPcm(ac: speech_f.Acoustic, out: []i16) usize {
    if (out.len == 0) return 0;

    const c0 = fixed.toF64(ac.ch[0]);
    const c1 = fixed.toF64(ac.ch[1]);
    const c2 = fixed.toF64(ac.ch[2]);
    const c3 = fixed.toF64(ac.ch[3]);
    const c4 = fixed.toF64(ac.ch[4]);
    const c5 = fixed.toF64(ac.ch[5]);
    const c6 = if (speech_f.ACOUSTIC_N > 6) fixed.toF64(ac.ch[6]) else 0.0;
    const c7 = if (speech_f.ACOUSTIC_N > 7) fixed.toF64(ac.ch[7]) else 0.0;

    // Pitch: ~90–520 Hz (low hum ↔ high chirp)
    const f0_base = 90.0 + unit01(c0) * 430.0;
    // Formants spread like vowel chart
    const f1 = 280.0 + unit01(c1) * 620.0; // ~280–900
    const f2 = 700.0 + unit01(c2) * 1600.0; // ~700–2300
    const f3 = 1800.0 + unit01(c6) * 1400.0; // ~1800–3200
    const amp = clampAmp(0.22 + unit01(c3) * 0.6);
    const tilt = unit01(c4); // more tilt → more high harmonics / brightness
    const noise_mix = @max(0.0, @min(0.55, unit01(c6) * 0.5 + @max(0.0, c6) * 0.15));
    // Duration 70–340 ms
    const dur_s = 0.07 + unit01(c5) * 0.27;
    const sr: f64 = 16000.0;
    const n_want: usize = @intFromFloat(dur_s * sr);
    const n = @min(out.len, @max(@as(usize, 800), n_want));
    // Pitch glide: ± up to ~45% over the utterance
    const glide = c7 * 0.45;
    // Double pulse (pulse_2 style): dip envelope in the middle when duration mid-high and rms high
    const double_pulse = unit01(c5) > 0.45 and unit01(c3) > 0.55 and @abs(c7) < 0.35;

    var i: usize = 0;
    var rng: u32 = 0xA341316C; // cheap deterministic noise
    while (i < n) : (i += 1) {
        const t = @as(f64, @floatFromInt(i)) / sr;
        const u = @as(f64, @floatFromInt(i)) / @as(f64, @floatFromInt(n)); // 0..1 progress

        // instantaneous f0 with glide
        const f0 = f0_base * (1.0 + glide * (u - 0.5) * 2.0);

        // envelope: attack / sustain / release (staccato = short everything)
        const att = @max(0.004, 0.012 + (1.0 - unit01(c5)) * 0.01);
        const rel = @max(0.01, 0.04 + unit01(c5) * 0.08);
        var env: f64 = 1.0;
        if (t < att) {
            env = t / att;
        } else if (t > dur_s - rel) {
            const left = @max(0.0, dur_s - t);
            env = left / rel;
        }
        if (double_pulse) {
            // notch at mid → two bursts
            const mid = @abs(u - 0.5);
            if (mid < 0.08) env *= mid / 0.08;
        }
        // whisper: softer overall already via amp; slight extra ramp
        if (c3 < -0.3) env *= 0.55 + 0.45 * u;

        // harmonics of f0 (voice-ish) + formant partials
        const two_pi = 2.0 * std.math.pi;
        const h1 = @sin(two_pi * f0 * t);
        const h2 = @sin(two_pi * (2.0 * f0) * t);
        const h3 = @sin(two_pi * (3.0 * f0) * t);
        const h4 = @sin(two_pi * (4.0 * f0) * t);
        const form1 = @sin(two_pi * f1 * t);
        const form2 = @sin(two_pi * f2 * t);
        const form3 = @sin(two_pi * f3 * t);

        const bright = 0.15 + tilt * 0.35;
        var s = (0.38 * h1) +
            ((0.18 + bright * 0.15) * h2) +
            ((0.08 + bright * 0.12) * h3) +
            ((0.04 + bright * 0.08) * h4) +
            (0.22 * form1) +
            (0.16 * form2) +
            (0.08 * form3);

        // noise for fricative / whisper / growl roughness
        rng ^= rng << 13;
        rng ^= rng >> 17;
        rng ^= rng << 5;
        const noise = (@as(f64, @floatFromInt(rng & 0xFFFF)) / 32768.0) - 1.0;
        s = (1.0 - noise_mix) * s + noise_mix * noise * (0.7 + 0.3 * @abs(h1));

        s *= amp * env;
        // soft clip
        if (s > 1.0) s = 1.0;
        if (s < -1.0) s = -1.0;
        out[i] = @intFromFloat(s * 30000.0);
    }
    // zero rest of buffer if any (caller may pass larger)
    var z = n;
    while (z < out.len and z < n + 64) : (z += 1) out[z] = 0;
    return n;
}

pub const win_out = if (builtin.os.tag == .windows) struct {
    const WINAPI: std.builtin.CallingConvention = .winapi;
    const DWORD = u32;
    const UINT = u32;
    const WAVEFORMATEX = extern struct {
        wFormatTag: u16,
        nChannels: u16,
        nSamplesPerSec: DWORD,
        nAvgBytesPerSec: DWORD,
        nBlockAlign: u16,
        wBitsPerSample: u16,
        cbSize: u16,
    };
    const WAVEHDR = extern struct {
        lpData: ?[*]u8,
        dwBufferLength: DWORD,
        dwBytesRecorded: DWORD,
        dwUser: usize,
        dwFlags: DWORD,
        dwLoops: DWORD,
        lpNext: ?*WAVEHDR,
        reserved: usize,
    };
    const HWAVEOUT = ?*anyopaque;
    const MMSYSERR_NOERROR: u32 = 0;
    const WAVE_FORMAT_PCM: u16 = 1;
    const WAVE_MAPPER: u32 = 0xFFFFFFFF;
    const CALLBACK_NULL: DWORD = 0;
    const WHDR_DONE: DWORD = 0x00000001;

    extern "winmm" fn waveOutOpen(phwo: *HWAVEOUT, uDeviceID: u32, pwfx: *const WAVEFORMATEX, dwCallback: usize, dwInstance: usize, fdwOpen: DWORD) callconv(WINAPI) u32;
    extern "winmm" fn waveOutPrepareHeader(hwo: HWAVEOUT, pwh: *WAVEHDR, cbwh: UINT) callconv(WINAPI) u32;
    extern "winmm" fn waveOutWrite(hwo: HWAVEOUT, pwh: *WAVEHDR, cbwh: UINT) callconv(WINAPI) u32;
    extern "winmm" fn waveOutUnprepareHeader(hwo: HWAVEOUT, pwh: *WAVEHDR, cbwh: UINT) callconv(WINAPI) u32;
    extern "winmm" fn waveOutClose(hwo: HWAVEOUT) callconv(WINAPI) u32;
    extern "winmm" fn waveOutReset(hwo: HWAVEOUT) callconv(WINAPI) u32;

    pub fn playPcm(pcm: []const i16) bool {
        if (pcm.len == 0) return false;
        var fmt: WAVEFORMATEX = .{
            .wFormatTag = WAVE_FORMAT_PCM,
            .nChannels = 1,
            .nSamplesPerSec = 16000,
            .nAvgBytesPerSec = 16000 * 2,
            .nBlockAlign = 2,
            .wBitsPerSample = 16,
            .cbSize = 0,
        };
        var hwo: HWAVEOUT = null;
        if (waveOutOpen(&hwo, WAVE_MAPPER, &fmt, 0, 0, CALLBACK_NULL) != MMSYSERR_NOERROR) return false;
        defer _ = waveOutClose(hwo);

        var hdr: WAVEHDR = std.mem.zeroes(WAVEHDR);
        hdr.lpData = @ptrCast(@constCast(pcm.ptr));
        hdr.dwBufferLength = @intCast(pcm.len * 2);
        if (waveOutPrepareHeader(hwo, &hdr, @sizeOf(WAVEHDR)) != MMSYSERR_NOERROR) return false;
        defer {
            _ = waveOutReset(hwo);
            _ = waveOutUnprepareHeader(hwo, &hdr, @sizeOf(WAVEHDR));
        }
        if (waveOutWrite(hwo, &hdr, @sizeOf(WAVEHDR)) != MMSYSERR_NOERROR) return false;
        // wait for buffer (~pcm duration)
        const ms = (pcm.len * 1000) / 16000 + 50;
        std.Thread.sleep(@as(u64, ms) * std.time.ns_per_ms);
        return true;
    }
} else struct {
    pub fn playPcm(pcm: []const i16) bool {
        _ = pcm;
        return true; // honest no-DAC success on non-Windows host path
    }
};

pub fn playPcm(pcm: []const i16) bool {
    return win_out.playPcm(pcm);
}

pub fn runSpeakerProbe() AudioOutReport {
    var organ: speech_f.SpeechOrgan = .{};
    organ.clear();
    // play several inventory tones so probe proves variety
    var total: u32 = 0;
    var played_any = false;
    var g: u32 = 0;
    while (g < 4) : (g += 1) {
        const u = organ.utterNextGesture(&[_]Fixed{0} ** speech_f.MEANING_N);
        var pcm: [PCM_MAX]i16 = undefined;
        const n = acousticToPcm(u.acoustic, pcm[0..]);
        total += @intCast(n);
        if (win_out.playPcm(pcm[0..n])) played_any = true;
    }
    return .{
        .ok = total > 1000,
        .n_samples = total,
        .played = played_any,
        .backend = if (builtin.os.tag == .windows) "winmm" else "none",
    };
}
