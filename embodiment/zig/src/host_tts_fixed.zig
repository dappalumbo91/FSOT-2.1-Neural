//! Host text-to-speech plant — English string → OS voice.
//!
//! Translation layer only: the mind chose machine language + lexicon words;
//! this plant speaks the English phrase. Not formant synthesis, not an LLM.
//!
//! Windows: System.Speech via PowerShell (no C/Rust dep).
//! Other OS: no-op success with spoken=false (honest).

const std = @import("std");
const builtin = @import("builtin");

pub const TtsReport = struct {
    ok: bool,
    spoken: bool,
    backend: []const u8,
    n_chars: u32,
};

/// Escape single quotes for PowerShell single-quoted string.
fn psEscape(src: []const u8, dst: []u8) usize {
    var o: usize = 0;
    for (src) |c| {
        if (o >= dst.len) break;
        if (c == '\'') {
            // PowerShell: '' inside single quotes
            if (o + 2 > dst.len) break;
            dst[o] = '\'';
            dst[o + 1] = '\'';
            o += 2;
        } else if (c >= 32 and c < 127) {
            dst[o] = c;
            o += 1;
        } else if (c == ' ') {
            dst[o] = ' ';
            o += 1;
        }
        // drop other bytes (lexicon is ASCII)
    }
    return o;
}

/// Speak English phrase on the host (blocking until done on Windows).
pub fn speakEnglish(phrase: []const u8) TtsReport {
    if (phrase.len == 0) {
        return .{ .ok = true, .spoken = false, .backend = "empty", .n_chars = 0 };
    }
    if (builtin.os.tag != .windows) {
        return .{ .ok = true, .spoken = false, .backend = "none", .n_chars = @intCast(phrase.len) };
    }

    var esc: [256]u8 = undefined;
    const ne = psEscape(phrase, esc[0..]);
    if (ne == 0) {
        return .{ .ok = false, .spoken = false, .backend = "win_sapi", .n_chars = 0 };
    }

    // System.Speech.SpeechSynthesizer — built into Windows desktop.
    // Keep command short; phrase is ASCII lexicon English.
    var cmd_buf: [512]u8 = undefined;
    const cmd = std.fmt.bufPrint(cmd_buf[0..], "Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Rate=1; $s.Speak('{s}')", .{esc[0..ne]}) catch {
        return .{ .ok = false, .spoken = false, .backend = "win_sapi", .n_chars = @intCast(phrase.len) };
    };

    var child = std.process.Child.init(&.{ "powershell", "-NoProfile", "-NonInteractive", "-Command", cmd }, std.heap.page_allocator);
    child.stdout_behavior = .Ignore;
    child.stderr_behavior = .Ignore;
    const run = child.spawnAndWait() catch {
        return .{ .ok = false, .spoken = false, .backend = "win_sapi", .n_chars = @intCast(phrase.len) };
    };
    const spoken = switch (run) {
        .Exited => |code| code == 0,
        else => false,
    };
    return .{
        .ok = true, // plant attempted; spoken may be false if SAPI missing
        .spoken = spoken,
        .backend = "win_sapi",
        .n_chars = @intCast(phrase.len),
    };
}

pub fn runTtsProbe() TtsReport {
    // Short lexicon phrase
    return speakEnglish("I see the light.");
}
