//! Multi-unit memory fingerprints for QEMU serial logging.
//! Compact regional stats over a short encode window — parity spirit with
//! Python learning_memory.fingerprint_from_hist (simplified for freestanding).

const network = @import("network.zig");
const serial = @import("serial.zig");

// Sized for freestanding soft-FPU under QEMU (full FSOT step is expensive)
pub const N_ITEMS: usize = 2;
pub const N_UNITS: usize = 8;
pub const ENCODE_STEPS: usize = 24;
pub const FP_DIM: usize = 8; // mean S in 4 blocks + spike duty

/// Deterministic item feature (no alloc).
fn itemFeat(item: usize, k: usize) f64 {
    // simple hash-like pattern in [-1,1]
    const a: u32 = @intCast(item * 17 + k * 31 + 3);
    const x = @as(f64, @floatFromInt(a % 200)) / 100.0 - 1.0;
    return x;
}

fn runEncode(net: *network.Network, item: usize, out_fp: *[FP_DIM]f64) void {
    net.* = network.Network.init(N_UNITS);
    net.setDefaultGeneticW(0.08);

    var sum_s: [N_UNITS]f64 = .{0} ** N_UNITS;
    var sum_f: [N_UNITS]f64 = .{0} ** N_UNITS;
    var t: usize = 0;
    while (t < ENCODE_STEPS) : (t += 1) {
        var ext: [N_UNITS]f64 = undefined;
        var u: usize = 0;
        while (u < N_UNITS) : (u += 1) {
            // thalamic packet + item pattern on "sens" half
            var e: f64 = 0.05;
            if ((t % 40) < 10) e += 0.5;
            if (u < N_UNITS / 2) {
                e += 0.4 * itemFeat(item, u);
            } else {
                e += 0.25 * itemFeat(item, u);
            }
            ext[u] = e;
        }
        net.step(ext[0..]);
        u = 0;
        while (u < N_UNITS) : (u += 1) {
            sum_s[u] += net.units[u].S;
            if (net.last_fired[u]) sum_f[u] += 1.0;
        }
    }
    // fingerprint: 4 block mean S + 4 block spike duty
    const block = N_UNITS / 4;
    var b: usize = 0;
    while (b < 4) : (b += 1) {
        var ms: f64 = 0;
        var mf: f64 = 0;
        var i: usize = 0;
        while (i < block) : (i += 1) {
            const u = b * block + i;
            ms += sum_s[u] / @as(f64, @floatFromInt(ENCODE_STEPS));
            mf += sum_f[u] / @as(f64, @floatFromInt(ENCODE_STEPS));
        }
        out_fp[b] = ms / @as(f64, @floatFromInt(block));
        out_fp[4 + b] = mf / @as(f64, @floatFromInt(block));
    }
}

fn cosine(a: *const [FP_DIM]f64, b: *const [FP_DIM]f64) f64 {
    var dot: f64 = 0;
    var na: f64 = 0;
    var nb: f64 = 0;
    var i: usize = 0;
    while (i < FP_DIM) : (i += 1) {
        dot += a[i] * b[i];
        na += a[i] * a[i];
        nb += b[i] * b[i];
    }
    if (na < 1e-18 or nb < 1e-18) return 0;
    return dot / (@sqrt(na) * @sqrt(nb));
}

/// Encode N_ITEMS, then for each item re-encode as cue and pick max cosine.
pub fn fingerprintSelfTest() struct { ok: bool, correct: u32, n: u32 } {
    var fps: [N_ITEMS][FP_DIM]f64 = undefined;
    var net = network.Network.init(N_UNITS);

    var i: usize = 0;
    while (i < N_ITEMS) : (i += 1) {
        runEncode(&net, i, &fps[i]);
    }

    var correct: u32 = 0;
    i = 0;
    while (i < N_ITEMS) : (i += 1) {
        var cue: [FP_DIM]f64 = undefined;
        runEncode(&net, i, &cue);
        var best: usize = 0;
        var best_s: f64 = -2;
        var j: usize = 0;
        while (j < N_ITEMS) : (j += 1) {
            const s = cosine(&cue, &fps[j]);
            if (s > best_s) {
                best_s = s;
                best = j;
            }
        }
        if (best == i) correct += 1;
    }
    return .{ .ok = correct >= 1, .correct = correct, .n = N_ITEMS };
}

pub fn logFingerprintsSerial() void {
    // One encode pass + one retrieve pass (no double selfTest — freestanding FPU is slow)
    var fps: [N_ITEMS][FP_DIM]f64 = undefined;
    var net = network.Network.init(N_UNITS);
    serial.write("FP_ENCODE begin items=");
    serial.writeU32(N_ITEMS);
    serial.write(" units=");
    serial.writeU32(N_UNITS);
    serial.write("\n");

    var i: usize = 0;
    while (i < N_ITEMS) : (i += 1) {
        runEncode(&net, i, &fps[i]);
        serial.write("FP item=");
        serial.writeU32(@intCast(i));
        serial.write("\n");
    }

    var correct: u32 = 0;
    i = 0;
    while (i < N_ITEMS) : (i += 1) {
        var cue: [FP_DIM]f64 = undefined;
        runEncode(&net, i, &cue);
        var best: usize = 0;
        var best_s: f64 = -2;
        var j: usize = 0;
        while (j < N_ITEMS) : (j += 1) {
            const s = cosine(&cue, &fps[j]);
            if (s > best_s) {
                best_s = s;
                best = j;
            }
        }
        if (best == i) correct += 1;
    }
    serial.write("FP_RETRIEVE correct=");
    serial.writeU32(correct);
    serial.write("/");
    serial.writeU32(N_ITEMS);
    serial.write("\n");
    if (correct >= 1) {
        serial.write("FSOT_FP PASS\n");
    } else {
        serial.write("FSOT_FP FAIL\n");
    }
}
