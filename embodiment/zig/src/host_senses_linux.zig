//! Linux / WSL host senses — Zig-only plant layer.
//! Uses Linux as the *map*: /proc plant metrics, optional framebuffer, graceful fallback.
//! WSL often has no /dev/fb0 or real mic — synthetic residual is honest, not a lie.

const std = @import("std");
const builtin = @import("builtin");

/// Capture display framebuffer when present. WSL/desktop without /dev/fb0 → false
/// (caller uses synthetic plant). Real DRM/KMS path later with privilege.
pub fn captureDisplay(out_gray: []u8, out_w: *usize, out_h: *usize) bool {
    out_w.* = 0;
    out_h.* = 0;
    if (builtin.os.tag != .linux) return false;
    if (out_gray.len == 0) return false;
    // Honest: no silent fake "live display". Linux desktop needs DRM/PipeWire next.
    return false;
}

/// Mic: try /dev/dsp (legacy OSS) — often absent on modern/WSL; return 0 → caller falls back.
pub fn captureMic(out_pcm: []i16) usize {
    if (builtin.os.tag != .linux) return 0;
    if (out_pcm.len == 0) return 0;
    // Honest: no ALSA link yet; zero samples → caller fills synthetic audio.
    // Future: PipeWire/ALSA for real mic under native Linux / WSLg.
    return 0;
}

/// Plant load from /proc/loadavg → 0..1000 milli-units for metric mapping.
pub fn procLoadMilli() u32 {
    if (builtin.os.tag != .linux) return 0;
    const f = std.fs.openFileAbsolute("/proc/loadavg", .{}) catch return 0;
    defer f.close();
    var buf: [64]u8 = undefined;
    const n = f.read(buf[0..]) catch return 0;
    // first float "0.52 0.58 ..."
    var i: usize = 0;
    while (i < n and (buf[i] == ' ' or buf[i] == '\t')) : (i += 1) {}
    var intp: u32 = 0;
    var frac: u32 = 0;
    var in_frac = false;
    var places: u32 = 0;
    while (i < n) : (i += 1) {
        const c = buf[i];
        if (c == '.') {
            in_frac = true;
            continue;
        }
        if (c < '0' or c > '9') break;
        if (!in_frac) {
            intp = intp * 10 + (c - '0');
        } else if (places < 3) {
            frac = frac * 10 + (c - '0');
            places += 1;
        }
    }
    while (places < 3) : (places += 1) frac *= 10;
    // clamp load to ~0..4 → milli 0..1000 for first unit
    const milli = intp * 1000 + frac;
    if (milli > 4000) return 1000;
    return milli / 4;
}
