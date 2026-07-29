//! Continuous organism on fixed-point genetic brain + episodic memory.

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const inject_f = @import("inject_io_fixed.zig");
const modulate_f = @import("modulate_fixed.zig");
const sensory_f = @import("sensory_fixed.zig");
const pathways_f = @import("pathways_fixed.zig");
const speech_f = @import("speech_organ_fixed.zig");
const Fixed = fixed.Fixed;

pub const OrganismF = struct {
    brain: brain_f.BrainF,
    store: memory_f.StoreF,
    tick: u32 = 0,
    steps_per_tick: u32 = 4,
    encode_every: u32 = 15,
    last_encode_id: u32 = 0,
    /// optional external inject features (vision etc.) — legacy single-stream
    inject_feats: [8]Fixed = .{0} ** 8,
    inject_n: usize = 0,
    inject_active: bool = false,
    inject_modality: pathways_f.Modality = .vision,
    /// bio multi-packet bus (anatomical routes)
    bus: sensory_f.BusF = .{},
    use_bio_bus: bool = false,
    /// host plant metric for self-modulation (Fixed)
    metric: inject_f.MetricF = .{},
    last_mod: modulate_f.State = .{},
    /// speech organ (efferent plant — not LM)
    speech: speech_f.SpeechOrgan = .{},
    last_motor: speech_f.Motor = .{},
    last_acoustic: speech_f.Acoustic = .{},
    speak_every: u32 = 0, // 0 = off; else utter from recent meaning each N ticks
    last_meaning: [speech_f.MEANING_N]Fixed = .{0} ** speech_f.MEANING_N,
    has_meaning: bool = false,

    pub fn init() OrganismF {
        var o: OrganismF = .{
            .brain = brain_f.BrainF.initSeeded(42, false),
            .store = .{},
        };
        o.store.clear();
        o.speech.clear();
        return o;
    }

    pub fn setInject(self: *OrganismF, feats: []const Fixed) void {
        const n = @min(feats.len, 8);
        var i: usize = 0;
        while (i < n) : (i += 1) self.inject_feats[i] = feats[i];
        self.inject_n = n;
        self.inject_active = n > 0;
        // also mirror into bio bus as vision by default
        self.bus.clear();
        if (n > 0) {
            self.bus.push(sensory_f.PacketF.fromSlice(self.inject_modality, feats[0..n], fixed.fromDecimalStr("0.85")));
            self.use_bio_bus = true;
        }
    }

    pub fn setMetric(self: *OrganismF, m: inject_f.MetricF) void {
        self.metric = m;
        self.bus.metric = m;
    }

    /// Push anatomical sensory packet (vision/audio/hid/…).
    pub fn pushSense(self: *OrganismF, mod: pathways_f.Modality, feats: []const Fixed, strength: Fixed) void {
        self.bus.push(sensory_f.PacketF.fromSlice(mod, feats, strength));
        self.use_bio_bus = true;
    }

    /// Efferent: set concept meaning the speech plant should articulate.
    pub fn setMeaning(self: *OrganismF, meaning: []const Fixed) void {
        const n = @min(meaning.len, speech_f.MEANING_N);
        var i: usize = 0;
        while (i < n) : (i += 1) self.last_meaning[i] = meaning[i];
        while (i < speech_f.MEANING_N) : (i += 1) self.last_meaning[i] = 0;
        self.has_meaning = n > 0;
    }

    /// One motor→sound frame; re-afference into audio + proprio paths.
    pub fn speakNow(self: *OrganismF) void {
        if (!self.has_meaning) return;
        const u = speech_f.SpeechOrgan.utter(self.last_meaning[0..]);
        self.last_motor = u.motor;
        self.last_acoustic = u.acoustic;
        var a_feats: [8]Fixed = undefined;
        var m_feats: [8]Fixed = undefined;
        var i: usize = 0;
        while (i < 8) : (i += 1) {
            a_feats[i] = if (i < speech_f.ACOUSTIC_N) u.acoustic.ch[i] else 0;
            m_feats[i] = if (i < speech_f.MOTOR_N) u.motor.ch[i] else 0;
        }
        // re-afferent self-hearing + proprioception (biological closed loop)
        self.bus.push(sensory_f.PacketF.fromSlice(.speech_sound, a_feats[0..], fixed.fromDecimalStr("0.8")));
        self.bus.push(sensory_f.PacketF.fromSlice(.motor_proprio, m_feats[0..], fixed.fromDecimalStr("0.45")));
        self.use_bio_bus = true;
    }

    pub fn tickOnce(self: *OrganismF) struct { tick: u32, mean_s: Fixed, spikes: u32, episodes: u32 } {
        const before = self.brain.totalSpikes();
        // fire_frac proxy from recent spikes density (soft)
        const fire_frac = fixed.div(fixed.fromInt(@intCast(@min(before, 32))), fixed.fromInt(64));
        self.last_mod = modulate_f.fromMetric(self.metric, fire_frac);
        const stim = self.last_mod.stim_scale;

        // scheduled efferent speech (motor plant, not token LM)
        if (self.speak_every > 0 and self.has_meaning and (self.tick % self.speak_every) == 0) {
            self.speakNow();
        }

        var ext: [brain_f.N_TOTAL]Fixed = undefined;
        var s: u32 = 0;
        while (s < self.steps_per_tick) : (s += 1) {
            const t = self.tick + s;
            if (self.use_bio_bus and self.bus.n > 0) {
                // anatomical multi-modal bus (bio-accurate routes)
                self.bus.metric = self.metric;
                self.bus.buildExternal(&self.brain, stim, ext[0..]);
            } else if (self.inject_active) {
                // legacy single-stream inject into sens/assoc
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
