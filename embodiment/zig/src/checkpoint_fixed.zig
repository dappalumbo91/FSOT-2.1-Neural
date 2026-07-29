//! Biological checkpoint — save/load organism episodic memory + identity.
//!
//! Analogous to LLM checkpoint / game save, but only what this lattice owns:
//!   episodes (tokens + fingerprints), next_id, tick, seed, last_meaning.
//! Not full float weight dumps — Fixed lattice + episodic store.
//!
//! Format (text, portable):
//!   FSOTCHK1
//!   seed <u32>
//!   tick <u32>
//!   next_id <u32>
//!   n_ep <u32>
//!   meaning f0..f7
//!   EP id mask t0..t5
//!   FP <FP_DIM fixed decimals>

const std = @import("std");
const fixed = @import("fixed.zig");
const memory_f = @import("memory_fixed.zig");
const organism_f = @import("organism_fixed.zig");
const Fixed = fixed.Fixed;

const MAGIC = "FSOTCHK1";

fn writeFixed(w: anytype, x: Fixed) !void {
    // integer Fixed as decimal via toF64 for portable text (load parses decimal)
    try w.print("{d:.12} ", .{fixed.toF64(x)});
}

fn parseFixedTok(tok: []const u8) Fixed {
    // reuse inject-style: simple decimal
    if (tok.len == 0) return 0;
    return fixed.fromDecimalStr(tok);
}

/// Save organism learning state to path.
pub fn saveOrganism(path: []const u8, org: *const organism_f.OrganismF) !void {
    const file = try std.fs.cwd().createFile(path, .{});
    defer file.close();
    var buf: [64 * 1024]u8 = undefined;
    var fbs = std.io.fixedBufferStream(&buf);
    const w = fbs.writer();

    try w.print("{s}\n", .{MAGIC});
    try w.print("seed {d}\n", .{org.brain.seed});
    try w.print("tick {d}\n", .{org.tick});
    try w.print("next_id {d}\n", .{org.store.next_id});
    try w.print("n_ep {d}\n", .{org.store.n});
    try w.writeAll("meaning ");
    var i: usize = 0;
    while (i < 8) : (i += 1) try writeFixed(w, org.last_meaning[i]);
    try w.writeAll("\n");

    var e: usize = 0;
    while (e < org.store.n) : (e += 1) {
        const ep = org.store.episodes[e];
        if (!ep.valid) continue;
        try w.print("EP {d} {d}", .{ ep.id, ep.slot_mask });
        var t: usize = 0;
        while (t < 6) : (t += 1) try w.print(" {d}", .{ep.tokens[t]});
        try w.writeAll("\nFP ");
        var f: usize = 0;
        while (f < memory_f.FP_DIM) : (f += 1) try writeFixed(w, ep.fp[f]);
        try w.writeAll("\n");
    }

    try file.writeAll(fbs.getWritten());
}

/// Load into organism store (replaces episodes). Brain weights stay genetic init;
/// learning continuity is episodic + meaning (biological memory resume).
pub fn loadOrganism(path: []const u8, org: *organism_f.OrganismF) !void {
    const file = try std.fs.cwd().openFile(path, .{});
    defer file.close();
    var buf: [256 * 1024]u8 = undefined;
    const nread = try file.readAll(&buf);
    const text = buf[0..nread];

    org.store.clear();
    var lines = std.mem.splitScalar(u8, text, '\n');
    var first = true;
    var pending_ep: ?memory_f.EpisodeF = null;

    while (lines.next()) |raw| {
        var line = raw;
        if (line.len > 0 and line[line.len - 1] == '\r') line = line[0 .. line.len - 1];
        if (line.len == 0) continue;
        if (first) {
            if (!std.mem.eql(u8, line, MAGIC)) return error.BadMagic;
            first = false;
            continue;
        }
        if (std.mem.startsWith(u8, line, "seed ")) {
            // seed logged for audit; genetic brain already init
            continue;
        }
        if (std.mem.startsWith(u8, line, "tick ")) {
            org.tick = std.fmt.parseInt(u32, line[5..], 10) catch 0;
            continue;
        }
        if (std.mem.startsWith(u8, line, "next_id ")) {
            org.store.next_id = std.fmt.parseInt(u32, line[8..], 10) catch 1;
            continue;
        }
        if (std.mem.startsWith(u8, line, "n_ep ")) continue;
        if (std.mem.startsWith(u8, line, "meaning ")) {
            var it = std.mem.tokenizeAny(u8, line[8..], " \t");
            var k: usize = 0;
            while (it.next()) |tok| {
                if (k >= 8) break;
                org.last_meaning[k] = parseFixedTok(tok);
                k += 1;
            }
            org.has_meaning = k > 0;
            continue;
        }
        if (std.mem.startsWith(u8, line, "EP ")) {
            var it = std.mem.tokenizeAny(u8, line[3..], " \t");
            var ep: memory_f.EpisodeF = .{ .valid = true };
            ep.id = std.fmt.parseInt(u32, it.next() orelse "0", 10) catch 0;
            ep.slot_mask = @intCast(std.fmt.parseInt(u32, it.next() orelse "0", 10) catch 0);
            var t: usize = 0;
            while (t < 6) : (t += 1) {
                ep.tokens[t] = std.fmt.parseInt(u32, it.next() orelse "0", 10) catch 0;
            }
            pending_ep = ep;
            continue;
        }
        if (std.mem.startsWith(u8, line, "FP ") and pending_ep != null) {
            var ep = pending_ep.?;
            var it = std.mem.tokenizeAny(u8, line[3..], " \t");
            var f: usize = 0;
            while (it.next()) |tok| {
                if (f >= memory_f.FP_DIM) break;
                ep.fp[f] = parseFixedTok(tok);
                f += 1;
            }
            if (org.store.n < memory_f.MAX_EPISODES) {
                org.store.episodes[org.store.n] = ep;
                org.store.n += 1;
            }
            pending_ep = null;
            continue;
        }
    }
}

pub const CheckpointReport = struct {
    ok: bool,
    n_saved: u32,
    n_loaded: u32,
    roundtrip: bool,
    path: []const u8,
};

/// Encode a few lessons, save, fresh org load, verify episode count + token.
pub fn runCheckpointProbe() !CheckpointReport {
    const path = "data/checkpoints/organism_probe.fsotchk";
    // ensure dir
    std.fs.cwd().makePath("data/checkpoints") catch {};

    var org = organism_f.OrganismF.init();
    var feats: [8]Fixed = .{0} ** 8;
    feats[0] = fixed.fromDecimalStr("0.5");
    feats[1] = fixed.fromDecimalStr("-0.25");
    const tok = [_]u32{
        memory_f.hashToken("checkpoint"),
        memory_f.hashToken("probe"),
        memory_f.hashToken("digit"),
        memory_f.hashToken("3"),
        0,
        memory_f.hashToken("save"),
    };
    _ = org.store.encode(&org.brain, feats[0..], 0b111111, tok);
    _ = org.store.encode(&org.brain, feats[0..], 0b000111, tok);
    org.tick = 42;
    org.setMeaning(feats[0..]);

    try saveOrganism(path, &org);
    const n_saved: u32 = @intCast(org.store.n);

    var org2 = organism_f.OrganismF.init();
    try loadOrganism(path, &org2);
    const n_loaded: u32 = @intCast(org2.store.n);
    const rt = n_loaded == n_saved and org2.tick == 42 and org2.store.episodes[0].tokens[0] == tok[0];

    return .{
        .ok = rt and n_saved >= 1,
        .n_saved = n_saved,
        .n_loaded = n_loaded,
        .roundtrip = rt,
        .path = path,
    };
}

pub fn selfTest() bool {
    const r = runCheckpointProbe() catch return false;
    return r.ok;
}
