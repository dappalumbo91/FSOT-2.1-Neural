//! Speaker efferent — acoustic features / speech plant → PCM → host DAC.
//! Zig-only. Windows: winmm waveOut. Linux: silent success if no device (honest).

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

/// Map acoustic channels to a short mono PCM burst (carrier + formant proxies).
pub fn acousticToPcm(ac: speech_f.Acoustic, out: []i16) usize {
    if (out.len == 0) return 0;
    const f0 = 220.0 + fixed.toF64(ac.ch[0]) * 180.0; // ~pitch
    const f1 = 500.0 + fixed.toF64(ac.ch[1]) * 400.0;
    const f2 = 1200.0 + fixed.toF64(ac.ch[2]) * 800.0;
    const amp = @max(0.05, @min(0.45, 0.15 + fixed.toF64(ac.ch[3]) * 0.3));
    const sr: f64 = 16000.0;
    var i: usize = 0;
    while (i < out.len) : (i += 1) {
        const t = @as(f64, @floatFromInt(i)) / sr;
        const env = if (i < 200) @as(f64, @floatFromInt(i)) / 200.0 else if (i + 400 > out.len) @as(f64, @floatFromInt(out.len - i)) / 400.0 else 1.0;
        const s = amp * env * (
            0.5 * @sin(2.0 * std.math.pi * f0 * t) +
            0.3 * @sin(2.0 * std.math.pi * f1 * t) +
            0.2 * @sin(2.0 * std.math.pi * f2 * t)
        );
        out[i] = @intFromFloat(s * 30000.0);
    }
    return out.len;
}

const win_out = if (builtin.os.tag == .windows) struct {
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
        std.Thread.sleep(ms * std.time.ns_per_ms);
        return true;
    }
} else struct {
    pub fn playPcm(pcm: []const i16) bool {
        _ = pcm;
        return false;
    }
};

pub fn runSpeakerProbe() AudioOutReport {
    // utter a fixed meaning through speech plant → PCM → speakers
    var meaning: [speech_f.MEANING_N]Fixed = undefined;
    var i: usize = 0;
    while (i < speech_f.MEANING_N) : (i += 1) {
        meaning[i] = fixed.sub(fixed.div(fixed.fromInt(@intCast((i * 17 + 3) % 100)), fixed.fromInt(50)), fixed.fromInt(1));
    }
    const u = speech_f.SpeechOrgan.utter(meaning[0..]);
    var pcm: [3200]i16 = undefined; // 200 ms @ 16k
    const n = acousticToPcm(u.acoustic, pcm[0..]);
    const played = win_out.playPcm(pcm[0..n]);
    // ok if we synthesized PCM; played may be false headless
    const ok = n >= 100;
    return .{
        .ok = ok,
        .n_samples = @intCast(n),
        .played = played,
        .backend = if (builtin.os.tag == .windows) "winmm_waveOut" else "none_linux_stub",
    };
}
