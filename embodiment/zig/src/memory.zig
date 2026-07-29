//! Fixed-capacity episodic fingerprint memory (no allocator).
//! Replaces Python learning_memory store + episode_memory core match.
//!
//! Full media titles stay in optional host/Python; bare metal stores:
//!   item_id, domain_tag, feature fingerprint, slot mask, encode ticks.

const brain = @import("brain.zig");
const seeds = @import("seeds.zig");

pub const FP_DIM: usize = brain.N_TOTAL * 2;
pub const MAX_EPISODES: usize = 32;
pub const ENCODE_STEPS: usize = 40;

pub const Domain = enum(u8) {
    generic = 0,
    biology = 1,
    physics_fsot = 2,
    narrative = 3,
    media = 4,
    learning = 5,
};

pub const Episode = struct {
    id: u32 = 0,
    domain: Domain = .generic,
    /// Bit0=who … bit5=how filled
    slot_mask: u8 = 0,
    /// Compact token hashes for 5W1H (first filled token per slot)
    who: u32 = 0,
    what: u32 = 0,
    why: u32 = 0,
    where: u32 = 0,
    when: u32 = 0,
    how: u32 = 0,
    fp: [FP_DIM]f64 = .{0} ** FP_DIM,
    valid: bool = false,
};

pub const Store = struct {
    n: usize = 0,
    next_id: u32 = 1,
    episodes: [MAX_EPISODES]Episode = undefined,

    pub fn clear(self: *Store) void {
        self.n = 0;
        self.next_id = 1;
        var i: usize = 0;
        while (i < MAX_EPISODES) : (i += 1) self.episodes[i] = .{};
    }

    pub fn count(self: *const Store) usize {
        return self.n;
    }

    /// Soft-reset dynamics for encode window; preserves lifetime spike totals for host metrics.
    pub fn encode(
        self: *Store,
        b: *brain.Brain,
        features: []const f64,
        domain: Domain,
        slot_mask: u8,
        tokens: [6]u32,
    ) u32 {
        // soft reset units (keep spike_count so organism lifetime metrics don't underflow)
        var u: usize = 0;
        while (u < b.n) : (u += 1) {
            const kept_spikes = b.net.units[u].spike_count;
            b.net.units[u].reset();
            b.net.units[u].spike_count = kept_spikes;
            b.net.last_fired[u] = false;
        }

        var sum_s: [brain.N_TOTAL]f64 = .{0} ** brain.N_TOTAL;
        var sum_f: [brain.N_TOTAL]f64 = .{0} ** brain.N_TOTAL;
        var ext: [brain.N_TOTAL]f64 = undefined;
        var t: usize = 0;
        while (t < ENCODE_STEPS) : (t += 1) {
            buildDrive(b, features, t, false, ext[0..]);
            b.step(ext[0..]);
            u = 0;
            while (u < b.n) : (u += 1) {
                sum_s[u] += b.net.units[u].S;
                if (b.net.last_fired[u]) sum_f[u] += 1.0;
            }
        }
        var ep: Episode = .{
            .id = self.next_id,
            .domain = domain,
            .slot_mask = slot_mask,
            .who = tokens[0],
            .what = tokens[1],
            .why = tokens[2],
            .where = tokens[3],
            .when = tokens[4],
            .how = tokens[5],
            .valid = true,
        };
        self.next_id += 1;
        const sf: f64 = @floatFromInt(ENCODE_STEPS);
        u = 0;
        while (u < b.n) : (u += 1) {
            ep.fp[u] = sum_s[u] / sf;
            ep.fp[brain.N_TOTAL + u] = sum_f[u] / sf;
        }

        if (self.n < MAX_EPISODES) {
            self.episodes[self.n] = ep;
            self.n += 1;
        } else {
            // ring: drop oldest
            var i: usize = 0;
            while (i + 1 < MAX_EPISODES) : (i += 1) self.episodes[i] = self.episodes[i + 1];
            self.episodes[MAX_EPISODES - 1] = ep;
        }
        return ep.id;
    }

    /// Cue with partial features; return best episode id and cosine, or 0 if empty.
    pub fn retrieve(
        self: *Store,
        b: *brain.Brain,
        features: []const f64,
        out_sim: *f64,
    ) u32 {
        if (self.n == 0) {
            out_sim.* = 0;
            return 0;
        }
        var cue: [FP_DIM]f64 = undefined;
        fingerprintCue(b, features, &cue);
        var best_i: usize = 0;
        var best_s: f64 = -2;
        var i: usize = 0;
        while (i < self.n) : (i += 1) {
            const s = cosine(&cue, &self.episodes[i].fp);
            if (s > best_s) {
                best_s = s;
                best_i = i;
            }
        }
        out_sim.* = best_s;
        return self.episodes[best_i].id;
    }

    pub fn getById(self: *const Store, id: u32) ?*const Episode {
        var i: usize = 0;
        while (i < self.n) : (i += 1) {
            if (self.episodes[i].id == id) return &self.episodes[i];
        }
        return null;
    }

    /// Fill empty slots from nearest neighbors when tokens match domain.
    pub fn tryFillSlot(self: *Store, id: u32, slot: u3, token: u32) bool {
        var i: usize = 0;
        while (i < self.n) : (i += 1) {
            if (self.episodes[i].id != id) continue;
            const bit: u8 = @as(u8, 1) << slot;
            if ((self.episodes[i].slot_mask & bit) != 0) return false; // already filled
            switch (slot) {
                0 => self.episodes[i].who = token,
                1 => self.episodes[i].what = token,
                2 => self.episodes[i].why = token,
                3 => self.episodes[i].where = token,
                4 => self.episodes[i].when = token,
                5 => self.episodes[i].how = token,
                else => return false,
            }
            self.episodes[i].slot_mask |= bit;
            return true;
        }
        return false;
    }

    pub fn emptySlotCount(self: *const Store, id: u32) u32 {
        const ep = self.getById(id) orelse return 0;
        var empty: u32 = 0;
        var s: u3 = 0;
        while (s < 6) : (s += 1) {
            const bit: u8 = @as(u8, 1) << s;
            if ((ep.slot_mask & bit) == 0) empty += 1;
        }
        return empty;
    }
};

fn clamp(x: f64, lo: f64, hi: f64) f64 {
    if (x < lo) return lo;
    if (x > hi) return hi;
    return x;
}

fn featAt(features: []const f64, u: usize) f64 {
    if (features.len == 0) return 0;
    return features[u % features.len];
}

fn buildDrive(b: *const brain.Brain, features: []const f64, t: usize, partial: bool, out: []f64) void {
    const n = b.n;
    const packet = (t % 80) < 20;
    var u: usize = 0;
    while (u < n and u < out.len) : (u += 1) {
        var e: f64 = 0.04;
        const silenced = partial and (u >= (2 * n) / 3);
        const f = if (silenced) 0.0 else featAt(features, u);
        switch (b.region_of[u]) {
            .thal => {
                if (packet) e += if ((u % 2) == 0) 0.55 else 0.18;
                e += 0.18 * f / seeds.phi;
            },
            .sens => e += 0.55 * f,
            .assoc => e += 0.42 * f,
            .hipp => e += 0.48 * f,
        }
        out[u] = clamp(e, -0.8, 1.5);
    }
}

fn fingerprintCue(b: *brain.Brain, features: []const f64, out: *[FP_DIM]f64) void {
    var u: usize = 0;
    while (u < b.n) : (u += 1) {
        b.net.units[u].reset();
        b.net.last_fired[u] = false;
    }
    var sum_s: [brain.N_TOTAL]f64 = .{0} ** brain.N_TOTAL;
    var sum_f: [brain.N_TOTAL]f64 = .{0} ** brain.N_TOTAL;
    var ext: [brain.N_TOTAL]f64 = undefined;
    const steps: usize = 30;
    var t: usize = 0;
    while (t < steps) : (t += 1) {
        buildDrive(b, features, t, true, ext[0..]);
        b.step(ext[0..]);
        u = 0;
        while (u < b.n) : (u += 1) {
            sum_s[u] += b.net.units[u].S;
            if (b.net.last_fired[u]) sum_f[u] += 1.0;
        }
    }
    const sf: f64 = @floatFromInt(steps);
    u = 0;
    while (u < b.n) : (u += 1) {
        out[u] = sum_s[u] / sf;
        out[brain.N_TOTAL + u] = sum_f[u] / sf;
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

/// Hash bytes → u32 token (FNV-1a-ish, freestanding).
pub fn hashToken(bytes: []const u8) u32 {
    var h: u32 = 2166136261;
    for (bytes) |c| {
        h ^= c;
        h *%= 16777619;
    }
    return if (h == 0) 1 else h;
}

pub fn selfTest() bool {
    var b = brain.Brain.init();
    var store: Store = .{};
    store.clear();

    const f0 = [_]f64{ 0.9, -0.4, 0.2, 0.7, -0.1, 0.5 };
    const f1 = [_]f64{ -0.8, 0.3, -0.6, 0.1, 0.9, -0.5 };
    const f2 = [_]f64{ 0.1, 0.2, 0.85, -0.9, 0.4, 0.15 };

    const t0 = [_]u32{ hashToken("alice"), hashToken("runs"), hashToken("fear"), 0, 0, hashToken("trit") };
    const t1 = [_]u32{ hashToken("bob"), hashToken("sings"), 0, hashToken("stage"), 0, 0 };
    const t2 = [_]u32{ 0, hashToken("scalar"), hashToken("phi"), 0, 0, hashToken("encode") };

    const id0 = store.encode(&b, f0[0..], .narrative, 0b00100111, t0); // who what why how
    const id1 = store.encode(&b, f1[0..], .media, 0b00101011, t1);
    const id2 = store.encode(&b, f2[0..], .physics_fsot, 0b00100110, t2);
    if (store.count() != 3) return false;
    if (id0 == 0 or id1 == 0 or id2 == 0) return false;

    var sim: f64 = 0;
    const hit = store.retrieve(&b, f0[0..], &sim);
    if (hit != id0) return false;
    if (sim < 0.3) return false;

    // curiosity: fill empty where on id0 from invented token
    const filled = store.tryFillSlot(id0, 3, hashToken("forest"));
    if (!filled) return false;
    if (store.emptySlotCount(id0) >= store.emptySlotCount(id1) + 6) return false;
    return true;
}
