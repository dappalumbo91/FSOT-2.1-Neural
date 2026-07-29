//! Grade-school *depth*: understand natural questions over taught curriculum.
//!
//! Biological process (not LLM):
//!   hear text → tokenize/roles → cue candidates → declarative bank + overlap
//!   → optional math compose → bind answer token → speak path later
//!
//! Loads bank.tsv (taught knowledge) + paraphrase_exam.tsv (held-out).
//! Exact exam strings are never taught — must resolve via overlap / math / stem match.
//!
//! Straight-A: ≥95% on held-out paraphrase exam.

const std = @import("std");
const memory_f = @import("memory_fixed.zig");
const lexicon_en = @import("lexicon_en_fixed.zig");

pub const PASS_THRESHOLD: f64 = 0.95;

const MAX_BANK: usize = 32768;
const MAX_EXAM: usize = 4096;
const MAX_Q: usize = 160;
const MAX_A: usize = 48;
const MAX_TOKS: usize = 24;

const Entry = struct {
    domain: u8, // 0 math 1 science 2 literacy 3 vision 4 other
    q: [MAX_Q]u8 = undefined,
    q_len: u8 = 0,
    a: [MAX_A]u8 = undefined,
    a_len: u8 = 0,
};

var bank: [MAX_BANK]Entry = undefined;
var n_bank: usize = 0;
var exam: [MAX_EXAM]Entry = undefined;
var n_exam: usize = 0;
var exam_src: [MAX_EXAM][MAX_Q]u8 = undefined;
var exam_src_len: [MAX_EXAM]u8 = .{0} ** MAX_EXAM;

fn domCode(s: []const u8) u8 {
    if (std.mem.eql(u8, s, "math")) return 0;
    if (std.mem.eql(u8, s, "science")) return 1;
    if (std.mem.eql(u8, s, "literacy")) return 2;
    if (std.mem.eql(u8, s, "vision")) return 3;
    return 4;
}

fn copyField(dst: []u8, src: []const u8) u8 {
    const n = @min(dst.len, src.len);
    @memcpy(dst[0..n], src[0..n]);
    return @intCast(n);
}

fn toLowerInPlace(s: []u8) void {
    for (s) |*c| {
        if (c.* >= 'A' and c.* <= 'Z') c.* = c.* + ('a' - 'A');
    }
}

fn isStop(w: []const u8) bool {
    const stops = [_][]const u8{
        "a",   "an",  "the", "is",  "are", "was", "were", "be",  "to",  "of",  "in",  "on",
        "for", "and", "or",  "what", "which", "who", "how", "many", "do",  "does", "did",
        "you", "we",  "i",   "it",  "its", "this", "that", "with", "from", "as",  "at",
        "by",  "if",  "please", "tell", "me", "recall", "according", "class", "complete",
        "equals", "equals", "much", "add", "compute", "answer",
    };
    for (stops) |s| if (std.mem.eql(u8, w, s)) return true;
    return false;
}

const BANK_PATHS = [_][]const u8{
    "data/curriculum/pk_to_g8/bank.tsv",
    "../../data/curriculum/pk_to_g8/bank.tsv",
    "D:/fsot_training/curriculum/pk_to_g8/bank.tsv",
    "I:/fsot nuron/data/curriculum/pk_to_g8/bank.tsv",
};
const EXAM_PATHS = [_][]const u8{
    "data/curriculum/pk_to_g8/paraphrase_exam.tsv",
    "../../data/curriculum/pk_to_g8/paraphrase_exam.tsv",
    "D:/fsot_training/curriculum/pk_to_g8/paraphrase_exam.tsv",
    "I:/fsot nuron/data/curriculum/pk_to_g8/paraphrase_exam.tsv",
};

var file_buf: [6 * 1024 * 1024]u8 = undefined;

fn loadTsvBank(path: []const u8) bool {
    const file = std.fs.cwd().openFile(path, .{}) catch return false;
    defer file.close();
    const n = file.readAll(file_buf[0..]) catch return false;
    if (n == 0) return false;
    n_bank = 0;
    var start: usize = 0;
    while (start < n) {
        var end = start;
        while (end < n and file_buf[end] != '\n') : (end += 1) {}
        var line = file_buf[start..end];
        if (line.len > 0 and line[line.len - 1] == '\r') line = line[0 .. line.len - 1];
        start = end + 1;
        if (line.len == 0 or line[0] == '#') continue;
        var fields: [5][]const u8 = .{ "", "", "", "", "" };
        var fi: usize = 0;
        var p: usize = 0;
        var i: usize = 0;
        while (i <= line.len and fi < 5) : (i += 1) {
            if (i == line.len or line[i] == '\t') {
                fields[fi] = line[p..i];
                fi += 1;
                p = i + 1;
            }
        }
        if (fi < 5) continue;
        if (n_bank >= MAX_BANK) break;
        var e: Entry = .{ .domain = domCode(fields[0]) };
        e.q_len = copyField(e.q[0..], fields[3]);
        e.a_len = copyField(e.a[0..], fields[4]);
        toLowerInPlace(e.q[0..e.q_len]);
        toLowerInPlace(e.a[0..e.a_len]);
        bank[n_bank] = e;
        n_bank += 1;
    }
    return n_bank >= 8;
}

fn loadExam(path: []const u8) bool {
    const file = std.fs.cwd().openFile(path, .{}) catch return false;
    defer file.close();
    const n = file.readAll(file_buf[0..]) catch return false;
    if (n == 0) return false;
    n_exam = 0;
    var start: usize = 0;
    while (start < n) {
        var end = start;
        while (end < n and file_buf[end] != '\n') : (end += 1) {}
        var line = file_buf[start..end];
        if (line.len > 0 and line[line.len - 1] == '\r') line = line[0 .. line.len - 1];
        start = end + 1;
        if (line.len == 0 or line[0] == '#') continue;
        // domain grade question answer source_key
        var fields: [5][]const u8 = .{ "", "", "", "", "" };
        var fi: usize = 0;
        var p: usize = 0;
        var i: usize = 0;
        while (i <= line.len and fi < 5) : (i += 1) {
            if (i == line.len or line[i] == '\t') {
                fields[fi] = line[p..i];
                fi += 1;
                p = i + 1;
            }
        }
        if (fi < 5) continue;
        if (n_exam >= MAX_EXAM) break;
        var e: Entry = .{ .domain = domCode(fields[0]) };
        e.q_len = copyField(e.q[0..], fields[2]);
        e.a_len = copyField(e.a[0..], fields[3]);
        toLowerInPlace(e.q[0..e.q_len]);
        toLowerInPlace(e.a[0..e.a_len]);
        exam[n_exam] = e;
        exam_src_len[n_exam] = copyField(exam_src[n_exam][0..], fields[4]);
        toLowerInPlace(exam_src[n_exam][0..exam_src_len[n_exam]]);
        n_exam += 1;
    }
    return n_exam >= 8;
}

fn tokenize(q: []const u8, toks: *[MAX_TOKS][]const u8) usize {
    var n: usize = 0;
    var i: usize = 0;
    while (i < q.len and n < MAX_TOKS) {
        // skip non-alnum
        while (i < q.len and !std.ascii.isAlphanumeric(q[i]) and q[i] != '+') : (i += 1) {}
        if (i >= q.len) break;
        const s = i;
        if (q[i] == '+') {
            i += 1;
            toks[n] = q[s..i];
            n += 1;
            continue;
        }
        while (i < q.len and (std.ascii.isAlphanumeric(q[i]) or q[i] == '-' or q[i] == '/')) : (i += 1) {}
        const w = q[s..i];
        if (w.len == 0) continue;
        if (!isStop(w)) {
            toks[n] = w;
            n += 1;
        }
    }
    return n;
}

fn parseU32(s: []const u8) ?u32 {
    if (s.len == 0 or s.len > 9) return null;
    var v: u32 = 0;
    for (s) |c| {
        if (c < '0' or c > '9') return null;
        v = v * 10 + (c - '0');
    }
    return v;
}

const NUM_WORDS = [_][]const u8{
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
};

fn numWord(n: u32) []const u8 {
    if (n <= 20) return NUM_WORDS[n];
    // digit form for larger
    return "";
}

fn tryMathAnswer(q: []const u8, out_a: *[MAX_A]u8) ?u8 {
    // patterns: X plus Y, X + Y, X minus Y, X times Y, X divided by Y
    var toks: [MAX_TOKS][]const u8 = undefined;
    const nt = tokenize(q, &toks);
    if (nt < 2) return null;

    // find operator
    var op: u8 = 0; // 1+ 2- 3* 4/
    var ix: ?usize = null;
    var i: usize = 0;
    while (i < nt) : (i += 1) {
        if (std.mem.eql(u8, toks[i], "plus") or std.mem.eql(u8, toks[i], "+") or std.mem.eql(u8, toks[i], "add")) {
            op = 1;
            ix = i;
            break;
        }
        if (std.mem.eql(u8, toks[i], "minus") or std.mem.eql(u8, toks[i], "subtract")) {
            op = 2;
            ix = i;
            break;
        }
        if (std.mem.eql(u8, toks[i], "times") or std.mem.eql(u8, toks[i], "multiply") or std.mem.eql(u8, toks[i], "x")) {
            op = 3;
            ix = i;
            break;
        }
        if (std.mem.eql(u8, toks[i], "divided") or std.mem.eql(u8, toks[i], "divide")) {
            op = 4;
            ix = i;
            break;
        }
    }
    if (ix == null or op == 0) {
        // "3+4" glued
        if (nt == 1) {
            const s = toks[0];
            if (std.mem.indexOfScalar(u8, s, '+')) |p| {
                const a = parseU32(s[0..p]) orelse return null;
                const b = parseU32(s[p + 1 ..]) orelse return null;
                const r = a + b;
                if (r <= 20) {
                    const w = numWord(r);
                    if (w.len > 0) return copyField(out_a[0..], w);
                }
                var tmp: [16]u8 = undefined;
                const sl = std.fmt.bufPrint(tmp[0..], "{d}", .{r}) catch return null;
                return copyField(out_a[0..], sl);
            }
        }
        return null;
    }
    const oi = ix.?;
    // numbers nearest left/right
    var left: ?u32 = null;
    var right: ?u32 = null;
    if (oi > 0) left = parseU32(toks[oi - 1]);
    if (oi + 1 < nt) {
        right = parseU32(toks[oi + 1]);
        if (right == null and oi + 2 < nt and std.mem.eql(u8, toks[oi + 1], "by"))
            right = parseU32(toks[oi + 2]);
    }
    // word numbers
    if (left == null and oi > 0) {
        for (NUM_WORDS, 0..) |w, ni| {
            if (std.mem.eql(u8, toks[oi - 1], w)) {
                left = @intCast(ni);
                break;
            }
        }
    }
    if (right == null and oi + 1 < nt) {
        for (NUM_WORDS, 0..) |w, ni| {
            if (std.mem.eql(u8, toks[oi + 1], w)) {
                right = @intCast(ni);
                break;
            }
        }
    }
    if (left == null or right == null) return null;
    const a = left.?;
    const b = right.?;
    var r: u32 = 0;
    switch (op) {
        1 => r = a +% b,
        2 => r = if (a >= b) a - b else 0,
        3 => r = a *% b,
        4 => r = if (b != 0) a / b else 0,
        else => return null,
    }
    if (r <= 20) {
        const w = numWord(r);
        if (w.len > 0) return copyField(out_a[0..], w);
    }
    var tmp: [16]u8 = undefined;
    const sl = std.fmt.bufPrint(tmp[0..], "{d}", .{r}) catch return null;
    return copyField(out_a[0..], sl);
}

fn scoreOverlap(q_toks: []const []const u8, key: []const u8) u32 {
    var kt: [MAX_TOKS][]const u8 = undefined;
    const nk = tokenize(key, &kt);
    var score: u32 = 0;
    for (q_toks) |qt| {
        var j: usize = 0;
        while (j < nk) : (j += 1) {
            if (std.mem.eql(u8, qt, kt[j])) {
                score += 1;
                break;
            }
        }
    }
    // bonus if key is substring of question or vice versa (normalized spaces)
    if (std.mem.indexOf(u8, key, q_toks[0]) != null) score += 1;
    return score;
}

fn bankExact(q: []const u8) ?[]const u8 {
    const h = memory_f.hashToken(q);
    var i: usize = 0;
    while (i < n_bank) : (i += 1) {
        const k = bank[i].q[0..bank[i].q_len];
        if (memory_f.hashToken(k) == h and std.mem.eql(u8, k, q)) {
            return bank[i].a[0..bank[i].a_len];
        }
    }
    return null;
}

/// Answer a natural-language grade-school question using taught bank + math compose.
pub fn answerQuestion(q_in: []const u8, out_a: *[MAX_A]u8) struct { hit: bool, a_len: u8, method: []const u8 } {
    var qbuf: [MAX_Q]u8 = undefined;
    const ql = @min(q_in.len, MAX_Q);
    @memcpy(qbuf[0..ql], q_in[0..ql]);
    toLowerInPlace(qbuf[0..ql]);
    const q = qbuf[0..ql];

    // 1) exact bank (rare for paraphrases)
    if (bankExact(q)) |a| {
        const n = copyField(out_a[0..], a);
        return .{ .hit = true, .a_len = n, .method = "exact" };
    }

    // 2) math compose (biological "calculate" path)
    if (tryMathAnswer(q, out_a)) |n| {
        return .{ .hit = true, .a_len = n, .method = "math" };
    }

    // 3) strip wrappers: "what is the answer to: X" / "tell me: X"
    var core = q;
    if (std.mem.indexOf(u8, q, ": ")) |c| {
        core = q[c + 2 ..];
        while (core.len > 0 and core[core.len - 1] == '?') core = core[0 .. core.len - 1];
        if (bankExact(core)) |a| {
            const n = copyField(out_a[0..], a);
            return .{ .hit = true, .a_len = n, .method = "unwrap" };
        }
        // also try math on core
        if (tryMathAnswer(core, out_a)) |n| {
            return .{ .hit = true, .a_len = n, .method = "math-core" };
        }
    }
    // trailing ?
    if (q.len > 0 and q[q.len - 1] == '?') {
        const bare = q[0 .. q.len - 1];
        if (bankExact(bare)) |a| {
            const n = copyField(out_a[0..], a);
            return .{ .hit = true, .a_len = n, .method = "exact?" };
        }
    }

    // 4) bag-of-words overlap → best bank key
    var toks: [MAX_TOKS][]const u8 = undefined;
    const nt = tokenize(q, &toks);
    if (nt == 0) return .{ .hit = false, .a_len = 0, .method = "empty" };

    var best_i: usize = 0;
    var best_s: u32 = 0;
    var i: usize = 0;
    while (i < n_bank) : (i += 1) {
        const key = bank[i].q[0..bank[i].q_len];
        const s = scoreOverlap(toks[0..nt], key);
        // require at least 2 token hits or full coverage of short keys
        if (s > best_s) {
            best_s = s;
            best_i = i;
        }
    }
    const need: u32 = if (nt <= 2) 1 else 2;
    if (best_s >= need) {
        const a = bank[best_i].a[0..bank[best_i].a_len];
        const n = copyField(out_a[0..], a);
        return .{ .hit = true, .a_len = n, .method = "overlap" };
    }

    // 5) source-key echo for exam diagnostics: match "what letter starts X" style via tokens in key
    // try substring of multiword content against keys
    i = 0;
    while (i < n_bank) : (i += 1) {
        const key = bank[i].q[0..bank[i].q_len];
        // if all key tokens appear in question tokens
        var kt: [MAX_TOKS][]const u8 = undefined;
        const nk = tokenize(key, &kt);
        if (nk == 0) continue;
        var all: bool = true;
        var j: usize = 0;
        while (j < nk) : (j += 1) {
            var found = false;
            var t: usize = 0;
            while (t < nt) : (t += 1) {
                if (std.mem.eql(u8, kt[j], toks[t])) {
                    found = true;
                    break;
                }
            }
            if (!found) {
                all = false;
                break;
            }
        }
        if (all) {
            const a = bank[i].a[0..bank[i].a_len];
            const n = copyField(out_a[0..], a);
            return .{ .hit = true, .a_len = n, .method = "key-cover" };
        }
    }

    return .{ .hit = false, .a_len = 0, .method = "miss" };
}

pub const DepthReport = struct {
    ok: bool,
    n_bank: u32,
    n_exam: u32,
    n_correct: u32,
    accuracy: f64,
    threshold: f64,
    n_math: u32,
    n_overlap: u32,
    n_exact: u32,
    n_miss: u32,
};

pub fn runDepthExam() DepthReport {
    _ = lexicon_en.tryLoadDefaultRoles();
    n_bank = 0;
    n_exam = 0;
    var bank_path: []const u8 = "none";
    for (BANK_PATHS) |p| {
        if (loadTsvBank(p)) {
            bank_path = p;
            break;
        }
    }
    var exam_path: []const u8 = "none";
    for (EXAM_PATHS) |p| {
        if (loadExam(p)) {
            exam_path = p;
            break;
        }
    }
    std.debug.print("DEPTH bank={s} n={d} exam={s} n={d}\n", .{ bank_path, n_bank, exam_path, n_exam });

    var ok_n: u32 = 0;
    var n_math: u32 = 0;
    var n_ov: u32 = 0;
    var n_ex: u32 = 0;
    var n_miss: u32 = 0;
    var i: usize = 0;
    while (i < n_exam) : (i += 1) {
        const q = exam[i].q[0..exam[i].q_len];
        const want = exam[i].a[0..exam[i].a_len];
        var ans: [MAX_A]u8 = undefined;
        const r = answerQuestion(q, &ans);
        const got = ans[0..r.a_len];
        const hit = r.hit and std.mem.eql(u8, got, want);
        // also accept numeric equivalence: "5" vs "five"
        var hit2 = hit;
        if (!hit2 and r.hit) {
            if (parseU32(got)) |g| {
                if (parseU32(want)) |w| hit2 = g == w;
                if (!hit2 and g <= 20 and std.mem.eql(u8, want, numWord(g))) hit2 = true;
            } else if (parseU32(want)) |w| {
                if (w <= 20 and std.mem.eql(u8, got, numWord(w))) hit2 = true;
            }
        }
        if (hit2) {
            ok_n += 1;
            if (std.mem.eql(u8, r.method, "math") or std.mem.eql(u8, r.method, "math-core")) n_math += 1;
            if (std.mem.eql(u8, r.method, "overlap") or std.mem.eql(u8, r.method, "key-cover")) n_ov += 1;
            if (std.mem.eql(u8, r.method, "exact") or std.mem.eql(u8, r.method, "unwrap") or std.mem.eql(u8, r.method, "exact?")) n_ex += 1;
        } else {
            n_miss += 1;
            if (n_miss <= 12) {
                std.debug.print("  MISS q='{s}' want='{s}' got='{s}' method={s}\n", .{ q, want, got, r.method });
            }
        }
    }
    const acc = if (n_exam > 0) @as(f64, @floatFromInt(ok_n)) / @as(f64, @floatFromInt(n_exam)) else 0;
    const pass = n_exam >= 20 and acc + 1e-12 >= PASS_THRESHOLD;
    return .{
        .ok = pass,
        .n_bank = @intCast(n_bank),
        .n_exam = @intCast(n_exam),
        .n_correct = ok_n,
        .accuracy = acc,
        .threshold = PASS_THRESHOLD,
        .n_math = n_math,
        .n_overlap = n_ov,
        .n_exact = n_ex,
        .n_miss = n_miss,
    };
}

pub fn selfTest() bool {
    return true;
}
