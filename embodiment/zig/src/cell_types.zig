//! Cortical cell-type labels + largest-remainder allocation (Python cell_types.py).
//! Phenotype/spin always come from genotype.zig codon ORFs — never from this file alone.

pub const CellType = enum(u8) {
    pyr = 0,
    pv = 1,
    sst = 2,
    vip = 3,
};

pub const Spec = struct {
    ctype: CellType,
    sign: i8,
    transmitter: []const u8,
    cortical_frac: f64,
};

pub const SPECS = [_]Spec{
    .{ .ctype = .pyr, .sign = 1, .transmitter = "glutamate", .cortical_frac = 0.80 },
    .{ .ctype = .pv, .sign = -1, .transmitter = "gaba", .cortical_frac = 0.08 },
    .{ .ctype = .sst, .sign = -1, .transmitter = "gaba", .cortical_frac = 0.07 },
    .{ .ctype = .vip, .sign = -1, .transmitter = "gaba", .cortical_frac = 0.05 },
};

pub fn specOf(ct: CellType) Spec {
    return SPECS[@intFromEnum(ct)];
}

pub const Mix = struct {
    pyr: f64,
    pv: f64,
    sst: f64,
    vip: f64,
};

pub const MIX_CORTICAL = Mix{ .pyr = 0.80, .pv = 0.08, .sst = 0.07, .vip = 0.05 };
pub const MIX_THAL = Mix{ .pyr = 0.85, .pv = 0.15, .sst = 0.0, .vip = 0.0 };
pub const MIX_HIPP = Mix{ .pyr = 0.75, .pv = 0.12, .sst = 0.08, .vip = 0.05 };

/// Largest-remainder allocation — exact twin of Python allocate_cell_types.
pub fn allocate(n_units: usize, mix: Mix, out: []CellType) usize {
    if (n_units == 0 or out.len < n_units) return 0;
    var fracs = [_]f64{ mix.pyr, mix.pv, mix.sst, mix.vip };
    var total: f64 = 0;
    for (fracs) |f| total += f;
    if (total < 1e-12) total = 1;
    var i: usize = 0;
    while (i < 4) : (i += 1) fracs[i] /= total;

    var raw: [4]f64 = undefined;
    var base: [4]usize = undefined;
    var n_base: usize = 0;
    i = 0;
    while (i < 4) : (i += 1) {
        raw[i] = fracs[i] * @as(f64, @floatFromInt(n_units));
        base[i] = @intFromFloat(@floor(raw[i]));
        n_base += base[i];
    }
    // fill labels grouped by type order Pyr,PV,SST,VIP
    var pos: usize = 0;
    i = 0;
    while (i < 4) : (i += 1) {
        var c: usize = 0;
        while (c < base[i] and pos < n_units) : (c += 1) {
            out[pos] = @enumFromInt(@as(u8, @intCast(i)));
            pos += 1;
        }
    }
    // remainders
    const rem = n_units - pos;
    // order by fractional part descending
    var order = [_]usize{ 0, 1, 2, 3 };
    // simple bubble sort by (raw-base)
    var a: usize = 0;
    while (a < 4) : (a += 1) {
        var b: usize = a + 1;
        while (b < 4) : (b += 1) {
            const fa = raw[order[a]] - @as(f64, @floatFromInt(base[order[a]]));
            const fb = raw[order[b]] - @as(f64, @floatFromInt(base[order[b]]));
            if (fb > fa) {
                const tmp = order[a];
                order[a] = order[b];
                order[b] = tmp;
            }
        }
    }
    var r: usize = 0;
    while (r < rem and pos < n_units) : (r += 1) {
        out[pos] = @enumFromInt(@as(u8, @intCast(order[r % 4])));
        pos += 1;
    }
    // safety n>=4
    if (n_units >= 4) {
        var has_pyr = false;
        var has_inh = false;
        i = 0;
        while (i < n_units) : (i += 1) {
            if (out[i] == .pyr) has_pyr = true;
            if (out[i] != .pyr) has_inh = true;
        }
        if (!has_pyr) out[0] = .pyr;
        if (!has_inh) out[n_units - 1] = .pv;
        // stable group sort Pyr PV SST VIP
        // insertion sort by type id
        i = 1;
        while (i < n_units) : (i += 1) {
            const key = out[i];
            var j: isize = @intCast(i);
            while (j > 0 and @intFromEnum(out[@intCast(j - 1)]) > @intFromEnum(key)) : (j -= 1) {
                out[@intCast(j)] = out[@intCast(j - 1)];
            }
            out[@intCast(j)] = key;
        }
    }
    return n_units;
}

/// LCG shuffle of unit ids (same constants as Python).
pub fn shuffleIds(n: usize, seed: u32, ids: []usize) void {
    var i: usize = 0;
    while (i < n) : (i += 1) ids[i] = i;
    var state: u32 = seed & 0x7FFFFFFF;
    const a: u32 = 1103515245;
    const c: u32 = 12345;
    const m: u32 = 1 << 31;
    if (n < 2) return;
    i = n - 1;
    while (true) {
        state = (a *% state +% c) % m;
        const j = state % @as(u32, @intCast(i + 1));
        const tmp = ids[i];
        ids[i] = ids[j];
        ids[j] = tmp;
        if (i == 0) break;
        i -= 1;
    }
}

pub fn selfTest() bool {
    var out: [20]CellType = undefined;
    const n = allocate(20, MIX_CORTICAL, out[0..]);
    if (n != 20) return false;
    var n_pyr: u32 = 0;
    var i: usize = 0;
    while (i < 20) : (i += 1) {
        if (out[i] == .pyr) n_pyr += 1;
    }
    // 0.80*20=16
    if (n_pyr < 15 or n_pyr > 17) return false;
    if (specOf(.pv).sign >= 0) return false;
    return true;
}
