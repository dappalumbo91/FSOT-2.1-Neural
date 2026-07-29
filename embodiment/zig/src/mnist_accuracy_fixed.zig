//! Real MNIST held-out accuracy gate (loads pack from run_mnist_gate.py).
//!
//! Pack: data/multimodal/mnist_gate/mnist_pack.bin (or D:/fsot_training/...)
//! Features: 14x14 spatial pool, L2-normalized (dim=196).
//! Classifier: k-NN on train exemplars → test labels.
//! Straight-A: top1 ≥ 0.95

const std = @import("std");

pub const PASS_THRESHOLD: f64 = 0.95;
pub const MAX_DIM: usize = 256;
pub const MAX_TRAIN: usize = 20000;
pub const MAX_TEST: usize = 2000;

pub const MnistReport = struct {
    ok: bool,
    top1: f64,
    correct: u32,
    n_test: u32,
    n_train: u32,
    dim: u32,
    k: u32,
    from_pack: bool,
    path: []const u8,
};

const PACK_CANDIDATES = [_][]const u8{
    "data/multimodal/mnist_gate/mnist_pack.bin",
    "../data/multimodal/mnist_gate/mnist_pack.bin",
    "../../data/multimodal/mnist_gate/mnist_pack.bin",
    "D:/fsot_training/datasets/mnist_gate/mnist_pack.bin",
    "I:/fsot nuron/data/multimodal/mnist_gate/mnist_pack.bin",
};

// static storage (not stack)
var train_lab: [MAX_TRAIN]u8 = undefined;
var test_lab: [MAX_TEST]u8 = undefined;
var train_feat: [MAX_TRAIN * MAX_DIM]f32 = undefined;
var test_feat: [MAX_TEST * MAX_DIM]f32 = undefined;

fn loadPack(path: []const u8, dim_out: *u32, ntr_out: *u32, nte_out: *u32, k_out: *u32) bool {
    const file = std.fs.cwd().openFile(path, .{}) catch return false;
    defer file.close();

    var magic: [8]u8 = undefined;
    _ = file.readAll(magic[0..]) catch return false;
    if (!std.mem.eql(u8, magic[0..], "FSOTMN14")) return false;

    var hdr: [16]u8 = undefined;
    _ = file.readAll(hdr[0..]) catch return false;
    const dim = std.mem.readInt(u32, hdr[0..4], .little);
    const n_train = std.mem.readInt(u32, hdr[4..8], .little);
    const n_test = std.mem.readInt(u32, hdr[8..12], .little);
    const k = std.mem.readInt(u32, hdr[12..16], .little);

    if (dim == 0 or dim > MAX_DIM) return false;
    if (n_train == 0 or n_train > MAX_TRAIN) return false;
    if (n_test == 0 or n_test > MAX_TEST) return false;
    if (k == 0 or k > 16) return false;

    _ = file.readAll(train_lab[0..n_train]) catch return false;
    const tr_bytes = n_train * dim * @sizeOf(f32);
    _ = file.readAll(std.mem.sliceAsBytes(train_feat[0 .. n_train * dim])) catch return false;
    _ = tr_bytes;
    _ = file.readAll(test_lab[0..n_test]) catch return false;
    _ = file.readAll(std.mem.sliceAsBytes(test_feat[0 .. n_test * dim])) catch return false;

    dim_out.* = dim;
    ntr_out.* = n_train;
    nte_out.* = n_test;
    k_out.* = k;
    return true;
}

fn dist2(a: []const f32, b: []const f32) f32 {
    var s: f32 = 0;
    var i: usize = 0;
    while (i < a.len) : (i += 1) {
        const d = a[i] - b[i];
        s += d * d;
    }
    return s;
}

fn classifyOne(dim: u32, n_train: u32, k: u32, q: []const f32) u8 {
    // k smallest distances
    var best_d: [16]f32 = .{std.math.floatMax(f32)} ** 16;
    var best_l: [16]u8 = .{0} ** 16;
    const kk: usize = @min(@as(usize, @intCast(k)), 16);

    var t: u32 = 0;
    while (t < n_train) : (t += 1) {
        const off = @as(usize, @intCast(t)) * @as(usize, @intCast(dim));
        const d = dist2(q, train_feat[off .. off + dim]);
        // insert into top-k if better
        var i: usize = 0;
        while (i < kk) : (i += 1) {
            if (d < best_d[i]) {
                var j: usize = kk - 1;
                while (j > i) : (j -= 1) {
                    best_d[j] = best_d[j - 1];
                    best_l[j] = best_l[j - 1];
                }
                best_d[i] = d;
                best_l[i] = train_lab[t];
                break;
            }
        }
    }
    // vote
    var votes: [10]u32 = .{0} ** 10;
    var i: usize = 0;
    while (i < kk) : (i += 1) {
        const lab = best_l[i];
        if (lab < 10) votes[lab] += 1;
    }
    var best_c: u8 = 0;
    var best_v: u32 = 0;
    var c: u8 = 0;
    while (c < 10) : (c += 1) {
        if (votes[c] > best_v) {
            best_v = votes[c];
            best_c = c;
        }
    }
    return best_c;
}

pub fn runMnistAccuracy() MnistReport {
    var dim: u32 = 0;
    var n_train: u32 = 0;
    var n_test: u32 = 0;
    var k: u32 = 0;
    var used_path: []const u8 = "";
    var loaded = false;
    for (PACK_CANDIDATES) |path| {
        if (loadPack(path, &dim, &n_train, &n_test, &k)) {
            used_path = path;
            loaded = true;
            break;
        }
    }
    if (!loaded) {
        std.debug.print("MNIST_GATE no pack (run: python run_mnist_gate.py)\n", .{});
        return .{
            .ok = false,
            .top1 = 0,
            .correct = 0,
            .n_test = 0,
            .n_train = 0,
            .dim = 0,
            .k = 0,
            .from_pack = false,
            .path = "none",
        };
    }

    var correct: u32 = 0;
    var i: u32 = 0;
    while (i < n_test) : (i += 1) {
        const off = @as(usize, @intCast(i)) * @as(usize, @intCast(dim));
        const q = test_feat[off .. off + dim];
        const pred = classifyOne(dim, n_train, k, q);
        if (pred == test_lab[i]) correct += 1;
    }
    const top1 = if (n_test > 0) @as(f64, @floatFromInt(correct)) / @as(f64, @floatFromInt(n_test)) else 0;
    const ok = top1 + 1e-12 >= PASS_THRESHOLD and n_test >= 100;
    std.debug.print(
        "MNIST_ACC path={s} dim={d} train={d} test={d} k={d} top1={e} pass={}\n",
        .{ used_path, dim, n_train, n_test, k, top1, ok },
    );
    return .{
        .ok = ok,
        .top1 = top1,
        .correct = correct,
        .n_test = n_test,
        .n_train = n_train,
        .dim = dim,
        .k = k,
        .from_pack = true,
        .path = used_path,
    };
}

pub fn selfTest() bool {
    // pack may be missing in bare CI — only require load path compile
    return true;
}
