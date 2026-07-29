//! Episodic fingerprint memory on fixed lattice.

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const Fixed = fixed.Fixed;

pub const FP_DIM: usize = brain_f.N_TOTAL * 2;
pub const MAX_EPISODES: usize = 16;
pub const ENCODE_STEPS: usize = 16;

pub const EpisodeF = struct {
    id: u32 = 0,
    slot_mask: u8 = 0,
    tokens: [6]u32 = .{0} ** 6,
    fp: [FP_DIM]Fixed = .{0} ** FP_DIM,
    valid: bool = false,
};

pub const StoreF = struct {
    n: usize = 0,
    next_id: u32 = 1,
    episodes: [MAX_EPISODES]EpisodeF = undefined,

    pub fn clear(self: *StoreF) void {
        self.n = 0;
        self.next_id = 1;
    }

    pub fn encode(
        self: *StoreF,
        b: *brain_f.BrainF,
        features: []const Fixed,
        slot_mask: u8,
        tokens: [6]u32,
    ) u32 {
        var u: usize = 0;
        while (u < b.n) : (u += 1) {
            const kept = b.net.units[u].spike_count;
            b.net.units[u].reset();
            b.net.units[u].spike_count = kept;
            b.net.last_fired[u] = false;
        }
        var sum_s: [brain_f.N_TOTAL]Fixed = .{0} ** brain_f.N_TOTAL;
        var sum_f: [brain_f.N_TOTAL]Fixed = .{0} ** brain_f.N_TOTAL;
        var ext: [brain_f.N_TOTAL]Fixed = undefined;
        var t: usize = 0;
        while (t < ENCODE_STEPS) : (t += 1) {
            var i: usize = 0;
            while (i < b.n) : (i += 1) {
                var e = fixed.fromDecimalStr("0.04");
                const f = if (features.len == 0) 0 else features[i % features.len];
                switch (b.region_of[i]) {
                    .thal => {
                        if ((t % 80) < 20) e = fixed.add(e, if (b.genotypes[i].synapse_sign > 0) fixed.fromDecimalStr("0.55") else fixed.fromDecimalStr("0.18"));
                        e = fixed.add(e, fixed.div(fixed.mul(fixed.fromDecimalStr("0.18"), f), @import("seeds_fixed.zig").phi));
                    },
                    .sens => e = fixed.add(e, fixed.mul(fixed.fromDecimalStr("0.55"), f)),
                    .assoc => e = fixed.add(e, fixed.mul(fixed.fromDecimalStr("0.42"), f)),
                    .hipp => e = fixed.add(e, fixed.mul(fixed.fromDecimalStr("0.48"), f)),
                }
                ext[i] = fixed.clamp(e, fixed.fromDecimalStr("-0.8"), fixed.fromDecimalStr("1.5"));
            }
            b.step(ext[0..]);
            i = 0;
            while (i < b.n) : (i += 1) {
                sum_s[i] = fixed.add(sum_s[i], b.net.units[i].S);
                if (b.net.last_fired[i]) sum_f[i] = fixed.add(sum_f[i], fixed.fromInt(1));
            }
        }
        var ep: EpisodeF = .{
            .id = self.next_id,
            .slot_mask = slot_mask,
            .tokens = tokens,
            .valid = true,
        };
        self.next_id += 1;
        const sf = fixed.fromInt(@intCast(ENCODE_STEPS));
        u = 0;
        while (u < b.n) : (u += 1) {
            ep.fp[u] = fixed.div(sum_s[u], sf);
            ep.fp[brain_f.N_TOTAL + u] = fixed.div(sum_f[u], sf);
        }
        if (self.n < MAX_EPISODES) {
            self.episodes[self.n] = ep;
            self.n += 1;
        } else {
            var i: usize = 0;
            while (i + 1 < MAX_EPISODES) : (i += 1) self.episodes[i] = self.episodes[i + 1];
            self.episodes[MAX_EPISODES - 1] = ep;
        }
        return ep.id;
    }

    pub fn retrieve(self: *StoreF, b: *brain_f.BrainF, features: []const Fixed, out_sim: *Fixed) u32 {
        if (self.n == 0) {
            out_sim.* = 0;
            return 0;
        }
        var cue: [FP_DIM]Fixed = undefined;
        // partial re-encode cue
        var u: usize = 0;
        while (u < b.n) : (u += 1) {
            b.net.units[u].reset();
            b.net.last_fired[u] = false;
        }
        var sum_s: [brain_f.N_TOTAL]Fixed = .{0} ** brain_f.N_TOTAL;
        var sum_f: [brain_f.N_TOTAL]Fixed = .{0} ** brain_f.N_TOTAL;
        var ext: [brain_f.N_TOTAL]Fixed = undefined;
        const steps: usize = 20;
        var t: usize = 0;
        while (t < steps) : (t += 1) {
            var i: usize = 0;
            while (i < b.n) : (i += 1) {
                const silenced = i >= (2 * b.n) / 3;
                const f = if (silenced or features.len == 0) 0 else features[i % features.len];
                ext[i] = fixed.add(fixed.fromDecimalStr("0.05"), fixed.mul(fixed.fromDecimalStr("0.4"), f));
            }
            b.step(ext[0..]);
            i = 0;
            while (i < b.n) : (i += 1) {
                sum_s[i] = fixed.add(sum_s[i], b.net.units[i].S);
                if (b.net.last_fired[i]) sum_f[i] = fixed.add(sum_f[i], fixed.fromInt(1));
            }
        }
        const sf = fixed.fromInt(@intCast(steps));
        u = 0;
        while (u < b.n) : (u += 1) {
            cue[u] = fixed.div(sum_s[u], sf);
            cue[brain_f.N_TOTAL + u] = fixed.div(sum_f[u], sf);
        }
        var best: usize = 0;
        var best_s: Fixed = fixed.fromInt(-2);
        var j: usize = 0;
        while (j < self.n) : (j += 1) {
            const s = cosine(&cue, &self.episodes[j].fp);
            if (fixed.gt(s, best_s)) {
                best_s = s;
                best = j;
            }
        }
        out_sim.* = best_s;
        return self.episodes[best].id;
    }
};

fn cosine(a: *const [FP_DIM]Fixed, b: *const [FP_DIM]Fixed) Fixed {
    var dot: Fixed = 0;
    var na: Fixed = 0;
    var nb: Fixed = 0;
    var i: usize = 0;
    while (i < FP_DIM) : (i += 1) {
        dot = fixed.add(dot, fixed.mul(a[i], b[i]));
        na = fixed.add(na, fixed.mul(a[i], a[i]));
        nb = fixed.add(nb, fixed.mul(b[i], b[i]));
    }
    if (fixed.lt(na, fixed.fromDecimalStr("0.000000000001")) or fixed.lt(nb, fixed.fromDecimalStr("0.000000000001"))) return 0;
    const denom = fixed.mul(fixed.sqrt(na), fixed.sqrt(nb));
    return fixed.div(dot, denom);
}

pub fn hashToken(bytes: []const u8) u32 {
    var h: u32 = 2166136261;
    for (bytes) |c| {
        h ^= c;
        h *%= 16777619;
    }
    return if (h == 0) 1 else h;
}

pub fn selfTest() bool {
    // Lightweight: encode two items, require distinct ids (full retrieve is heavy)
    var b = brain_f.BrainF.initSeeded(42, false);
    var store: StoreF = .{};
    store.clear();
    const f0 = [_]Fixed{ fixed.fromDecimalStr("0.9"), fixed.fromDecimalStr("-0.4"), fixed.fromDecimalStr("0.2") };
    const f1 = [_]Fixed{ fixed.fromDecimalStr("-0.8"), fixed.fromDecimalStr("0.3"), fixed.fromDecimalStr("-0.6") };
    const tok = [_]u32{ hashToken("a"), hashToken("b"), 0, 0, 0, hashToken("how") };
    const id0 = store.encode(&b, f0[0..], 0b100011, tok);
    const id1 = store.encode(&b, f1[0..], 0b000011, tok);
    return id0 != 0 and id1 != 0 and id0 != id1 and store.n == 2;
}
