//! Continuous organism on fixed-point genetic brain + episodic memory.

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const inject_f = @import("inject_io_fixed.zig");
const modulate_f = @import("modulate_fixed.zig");
const Fixed = fixed.Fixed;

pub const OrganismF = struct {
    brain: brain_f.BrainF,
    store: memory_f.StoreF,
    tick: u32 = 0,
    steps_per_tick: u32 = 4,
    encode_every: u32 = 15,
    last_encode_id: u32 = 0,
    /// optional external inject features (vision etc.)
    inject_feats: [8]Fixed = .{0} ** 8,
    inject_n: usize = 0,
    inject_active: bool = false,
    /// host plant metric for self-modulation (Fixed)
    metric: inject_f.MetricF = .{},
    last_mod: modulate_f.State = .{},

    pub fn init() OrganismF {
        var o: OrganismF = .{
            .brain = brain_f.BrainF.initSeeded(42, false),
            .store = .{},
        };
        o.store.clear();
        return o;
    }

    pub fn setInject(self: *OrganismF, feats: []const Fixed) void {
        const n = @min(feats.len, 8);
        var i: usize = 0;
        while (i < n) : (i += 1) self.inject_feats[i] = feats[i];
        self.inject_n = n;
        self.inject_active = n > 0;
    }

    pub fn setMetric(self: *OrganismF, m: inject_f.MetricF) void {
        self.metric = m;
    }

    pub fn tickOnce(self: *OrganismF) struct { tick: u32, mean_s: Fixed, spikes: u32, episodes: u32 } {
        const before = self.brain.totalSpikes();
        // fire_frac proxy from recent spikes density (soft)
        const fire_frac = fixed.div(fixed.fromInt(@intCast(@min(before, 32))), fixed.fromInt(64));
        self.last_mod = modulate_f.fromMetric(self.metric, fire_frac);
        const stim = self.last_mod.stim_scale;

        var ext: [brain_f.N_TOTAL]Fixed = undefined;
        var s: u32 = 0;
        while (s < self.steps_per_tick) : (s += 1) {
            const t = self.tick + s;
            if (self.inject_active) {
                // inject into sens/assoc from feature bus, scaled by autonomic stim
                var i: usize = 0;
                while (i < self.brain.n) : (i += 1) {
                    ext[i] = fixed.fromDecimalStr("0.04");
                    if (self.brain.region_of[i] == .sens or self.brain.region_of[i] == .assoc) {
                        const f = self.inject_feats[i % self.inject_n];
                        ext[i] = fixed.add(ext[i], fixed.mul(fixed.mul(fixed.fromDecimalStr("0.55"), f), stim));
                    }
                    if ((t % 80) < 15 and self.brain.region_of[i] == .thal and self.brain.genotypes[i].synapse_sign > 0) {
                        ext[i] = fixed.add(ext[i], fixed.mul(fixed.fromDecimalStr("0.4"), stim));
                    }
                }
            } else {
                const prim_base: Fixed = if ((t % 30) < 12) fixed.fromDecimalStr("0.7") else fixed.fromDecimalStr("0.08");
                const prim = fixed.mul(prim_base, stim);
                const reg: brain_f.RegionId = if ((t / 30) % 2 == 0) .sens else .assoc;
                self.brain.buildExternal(prim, reg, ext[0..]);
            }
            self.brain.step(ext[0..]);
        }
        if (self.encode_every > 0 and (self.tick % self.encode_every) == (self.encode_every - 1)) {
            var feats: [8]Fixed = .{fixed.fromDecimalStr("0.1")} ** 8;
            if (self.inject_active) {
                var i: usize = 0;
                while (i < self.inject_n) : (i += 1) feats[i] = self.inject_feats[i];
            } else {
                // synthetic item from tick
                var i: usize = 0;
                while (i < 8) : (i += 1) {
                    const a: i64 = @intCast((self.tick +% @as(u32, @intCast(i)) *% 17) % 200);
                    feats[i] = fixed.sub(fixed.div(fixed.fromInt(a), fixed.fromInt(100)), fixed.fromInt(1));
                }
            }
            const tok = [_]u32{
                memory_f.hashToken("agent"),
                memory_f.hashToken("event"),
                memory_f.hashToken("genetic_fold"),
                0,
                0,
                memory_f.hashToken("fsot_fixed"),
            };
            self.last_encode_id = self.store.encode(&self.brain, feats[0..], 0b100111, tok);
        }
        self.tick +%= 1;
        const after = self.brain.totalSpikes();
        return .{
            .tick = self.tick,
            .mean_s = self.brain.meanS(),
            .spikes = after -% before,
            .episodes = @intCast(self.store.n),
        };
    }

    pub fn run(self: *OrganismF, n_ticks: u32) struct { ok: bool, ticks: u32, spikes: u32, n_syn: u32, episodes: u32 } {
        var t: u32 = 0;
        while (t < n_ticks) : (t += 1) {
            _ = self.tickOnce();
        }
        const st = self.brain.structureReport();
        return .{
            .ok = self.brain.totalSpikes() >= 1 and st.n_synapses >= 100 and self.store.n >= 1,
            .ticks = self.tick,
            .spikes = self.brain.totalSpikes(),
            .n_syn = st.n_synapses,
            .episodes = @intCast(self.store.n),
        };
    }
};

pub fn selfTest() bool {
    var o = OrganismF.init();
    o.encode_every = 8;
    o.steps_per_tick = 3;
    const r = o.run(20);
    if (!r.ok or r.episodes < 1) return false;
    const feats = [_]Fixed{
        fixed.fromDecimalStr("0.9"),
        fixed.fromDecimalStr("-0.3"),
        fixed.fromDecimalStr("0.5"),
        fixed.fromDecimalStr("0.1"),
    };
    o.setInject(feats[0..]);
    _ = o.tickOnce();
    return o.brain.totalSpikes() >= 1;
}
