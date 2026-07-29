//! Continuous organism — bare-metal intelligence loop on genetic FSOT brain.
//!
//! Doctrine: trinary codon structure *is* the genetic code of the mind.
//! Each unit's SCN/KCN/CACNA/LEAK ORFs fold into phenotype → W → dynamics.
//! Watching composite_spin / expression under ops is watching genetic folding
//! during "biological" operation in code.
//!
//! Pipeline each tick:
//!   sense → modulate → genetic brain.step → encode → curiosity
//! No Python required for the mind step.

const brain = @import("brain.zig");
const sensory = @import("sensory.zig");
const modulate = @import("modulate.zig");
const memory = @import("memory.zig");
const slots = @import("slots.zig");
const pathways = @import("pathways.zig");
const learning = @import("learning.zig");
const bands = @import("bands.zig");
const genotype = @import("genotype.zig");

pub const TickReport = struct {
    tick: u32,
    mean_s: f64,
    spikes: u32,
    fire_frac: f64,
    stim_scale: f64,
    mode: modulate.Mode,
    n_episodes: u32,
    last_encode_id: u32,
    curiosity_resolved: u32,
    mean_spin: f64,
    n_synapses: u32,
};

pub const IntelReport = struct {
    ok: bool,
    ticks: u32,
    episodes: u32,
    total_spikes: u32,
    curiosity: u32,
    final_mean_s: f64,
    mean_spin: f64,
    n_pyr: u32,
    n_i: u32,
    n_synapses: u32,
    sme_ok: bool,
    learn_ok: bool,
    learn_top1: f64,
};

pub const Organism = struct {
    brain: brain.Brain,
    bus: sensory.Bus,
    store: memory.Store,
    mod: modulate.State,
    tick: u32,
    total_spikes_prev: u32,
    last_encode_id: u32,
    curiosity_resolved_total: u32,
    encode_every: u32,
    steps_per_tick: u32,
    /// last SME contrast after encode window
    last_sme_ok: bool,
    rate_window: [128]f64,
    rate_n: usize,

    pub fn init() Organism {
        return initSeeded(42, true);
    }

    pub fn initSeeded(seed: u32, diversity: bool) Organism {
        var o: Organism = .{
            .brain = brain.Brain.initSeeded(seed, diversity),
            .bus = .{},
            .store = .{},
            .mod = .{},
            .tick = 0,
            .total_spikes_prev = 0,
            .last_encode_id = 0,
            .curiosity_resolved_total = 0,
            .encode_every = 40,
            .steps_per_tick = 4,
            .last_sme_ok = false,
            .rate_window = .{0} ** 128,
            .rate_n = 0,
        };
        o.store.clear();
        return o;
    }

    pub fn reset(self: *Organism) void {
        const seed = self.brain.seed;
        self.* = initSeeded(seed, true);
    }

    pub fn meanCompositeSpin(self: *const Organism) f64 {
        var s: f64 = 0;
        var i: usize = 0;
        while (i < self.brain.n) : (i += 1) {
            s += self.brain.genotypes[i].composite_spin;
        }
        return s / @as(f64, @floatFromInt(self.brain.n));
    }

    /// One organism cycle. synth=true generates codon-lawful pattern senses.
    pub fn tickOnce(self: *Organism, synth: bool) TickReport {
        if (synth) self.syntheticSense();

        const spikes_before = self.brain.totalSpikes();
        const recent = if (spikes_before > self.total_spikes_prev)
            spikes_before - self.total_spikes_prev
        else
            0;
        const fire_frac = @as(f64, @floatFromInt(recent)) /
            @as(f64, @floatFromInt(self.brain.n * @max(self.steps_per_tick, 1)));
        self.mod = modulate.fromMetrics(self.bus.metric, fire_frac);

        var ext: [brain.N_TOTAL]f64 = undefined;
        var s: u32 = 0;
        var win_spikes: u32 = 0;
        while (s < self.steps_per_tick) : (s += 1) {
            self.bus.buildExternal(&self.brain, self.mod.stim_scale, ext[0..]);
            const b0 = self.brain.totalSpikes();
            self.brain.step(ext[0..]);
            win_spikes += self.brain.totalSpikes() - b0;
        }

        // population rate sample for SME window (Hz proxy)
        const rate = @as(f64, @floatFromInt(win_spikes)) /
            (@as(f64, @floatFromInt(self.brain.n)) * @as(f64, @floatFromInt(self.steps_per_tick)) / 1000.0);
        if (self.rate_n < self.rate_window.len) {
            self.rate_window[self.rate_n] = rate;
            self.rate_n += 1;
        } else {
            var i: usize = 0;
            while (i + 1 < self.rate_window.len) : (i += 1) self.rate_window[i] = self.rate_window[i + 1];
            self.rate_window[self.rate_window.len - 1] = rate;
        }

        const spikes_after_step = self.brain.totalSpikes();
        const win: u32 = if (spikes_after_step >= spikes_before)
            spikes_after_step - spikes_before
        else
            0;

        var encoded: u32 = 0;
        if (self.encode_every > 0 and (self.tick % self.encode_every) == (self.encode_every - 1)) {
            // SME: first half window vs second half as encode vs rest proxy if enough samples
            if (self.rate_n >= 32) {
                const mid = self.rate_n / 2;
                const sme = bands.smeContrast(self.rate_window[0..mid], self.rate_window[mid..self.rate_n], 1.0);
                self.last_sme_ok = sme.ok;
            }
            encoded = self.encodeCurrent();
            if (encoded != 0) {
                const ep = self.store.getById(encoded);
                const dom = if (ep) |e| e.domain else .generic;
                const cur = slots.runCuriosity(&self.store, encoded, dom);
                self.curiosity_resolved_total +%= cur.n_resolved;
            }
        }

        self.tick +%= 1;
        self.total_spikes_prev = self.brain.totalSpikes();
        const st = self.brain.structureReport();

        return .{
            .tick = self.tick,
            .mean_s = self.brain.meanS(),
            .spikes = win,
            .fire_frac = fire_frac,
            .stim_scale = self.mod.stim_scale,
            .mode = self.mod.mode,
            .n_episodes = @intCast(self.store.count()),
            .last_encode_id = if (encoded != 0) encoded else self.last_encode_id,
            .curiosity_resolved = self.curiosity_resolved_total,
            .mean_spin = self.meanCompositeSpin(),
            .n_synapses = st.n_synapses,
        };
    }

    fn syntheticSense(self: *Organism) void {
        self.bus.clear();
        // Features derived from tick + mean genetic spin (folding signature in drive)
        const spin = self.meanCompositeSpin();
        const mod_phase = self.tick % 120;
        var feats: [8]f64 = undefined;
        var i: usize = 0;
        while (i < 8) : (i += 1) {
            const a: u32 = self.tick *% 17 +% @as(u32, @intCast(i)) *% 31;
            const base = @as(f64, @floatFromInt(a % 200)) / 100.0 - 1.0;
            // mix spin so genetic structure modulates sensory fold
            feats[i] = 0.85 * base + 0.15 * spin;
        }
        const mod: pathways.Modality = switch (mod_phase / 30) {
            0 => .vision,
            1 => .audio,
            2 => .text,
            else => .sys_metric,
        };
        self.bus.push(sensory.Packet.fromSlice(mod, feats[0..], 0.75));
        const load_phase = @as(f64, @floatFromInt(self.tick % 64)) / 64.0;
        const tri: f64 = if (load_phase < 0.5) load_phase * 2.0 else (1.0 - load_phase) * 2.0;
        const load = 0.15 + 0.1 * tri;
        self.bus.metric = .{
            .cpu = load,
            .mem = load * 0.8,
            .disk = 0.1,
            .net = if (mod == .sys_metric) 0.4 else 0.05,
            .temp = 0.2,
        };
    }

    fn encodeCurrent(self: *Organism) u32 {
        var feats: [8]f64 = .{0.1} ** 8;
        var domain: memory.Domain = .generic;
        var mask: u8 = 0;
        var tokens: [6]u32 = .{0} ** 6;

        if (self.bus.n > 0) {
            const p = self.bus.packets[0];
            const n = @min(p.n_feat, 8);
            var i: usize = 0;
            while (i < n) : (i += 1) feats[i] = p.features[i];
            domain = switch (p.modality) {
                .vision, .audio => .media,
                .text, .log => .narrative,
                .sys_metric, .network => .learning,
                else => .generic,
            };
            tokens[1] = memory.hashToken("event");
            mask |= 0b00000010;
            tokens[5] = memory.hashToken("fsot_codon_step");
            mask |= 0b00100000;
            // bind genetic spin as HOW/mechanism flavor
            tokens[2] = memory.hashToken("genetic_fold");
            mask |= 0b00000100;
            if (p.modality == .vision) {
                tokens[0] = memory.hashToken("visual_agent");
                mask |= 0b00000001;
            }
            if (domain == .media) {
                tokens[3] = memory.hashToken("media_stream");
                mask |= 0b00001000;
            }
        }
        const id = self.store.encode(&self.brain, feats[0..], domain, mask, tokens);
        self.last_encode_id = id;
        return id;
    }

    /// Full intelligence run: organism ticks + independent learn probe on genetic substrate.
    pub fn runIntel(self: *Organism, n_ticks: u32, synth: bool) IntelReport {
        var t: u32 = 0;
        while (t < n_ticks) : (t += 1) {
            _ = self.tickOnce(synth);
        }
        const st = self.brain.structureReport();
        const lr = learning.runLearnProbe();
        const ms = self.brain.meanS();
        return .{
            .ok = self.store.count() >= 1 and st.n_synapses >= 1 and st.n_pyr >= 1 and ms == ms and lr.ok,
            .ticks = self.tick,
            .episodes = @intCast(self.store.count()),
            .total_spikes = self.brain.totalSpikes(),
            .curiosity = self.curiosity_resolved_total,
            .final_mean_s = ms,
            .mean_spin = self.meanCompositeSpin(),
            .n_pyr = st.n_pyr,
            .n_i = st.n_i,
            .n_synapses = st.n_synapses,
            .sme_ok = self.last_sme_ok,
            .learn_ok = lr.ok,
            .learn_top1 = lr.top1,
        };
    }

    pub fn run(self: *Organism, n_ticks: u32, synth: bool) struct {
        ok: bool,
        ticks: u32,
        episodes: u32,
        total_spikes: u32,
        curiosity: u32,
        final_mean_s: f64,
    } {
        const r = self.runIntel(n_ticks, synth);
        return .{
            .ok = r.ok,
            .ticks = r.ticks,
            .episodes = r.episodes,
            .total_spikes = r.total_spikes,
            .curiosity = r.curiosity,
            .final_mean_s = r.final_mean_s,
        };
    }
};

pub fn selfTest() bool {
    var org = Organism.init();
    org.encode_every = 20;
    org.steps_per_tick = 3;
    const rep = org.runIntel(60, true);
    if (!rep.ok) return false;
    if (rep.episodes < 2) return false;
    if (rep.n_synapses < 100) return false;
    // codon genotype present
    const g0 = genotype.buildGeneProgram(.scn, genotype.ORF_SCN);
    if (@abs(g0.spin) > 1e-9) return false;
    return pathways.selfTest();
}
