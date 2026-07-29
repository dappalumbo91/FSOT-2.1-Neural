//! Continuous organism on fixed-point genetic brain (no IEEE float dynamics).

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const Fixed = fixed.Fixed;

pub const OrganismF = struct {
    brain: brain_f.BrainF,
    tick: u32 = 0,
    steps_per_tick: u32 = 4,

    pub fn init() OrganismF {
        return .{ .brain = brain_f.BrainF.initSeeded(42, false) };
    }

    pub fn tickOnce(self: *OrganismF) struct { tick: u32, mean_s: Fixed, spikes: u32 } {
        const before = self.brain.totalSpikes();
        var ext: [brain_f.N_TOTAL]Fixed = undefined;
        var s: u32 = 0;
        while (s < self.steps_per_tick) : (s += 1) {
            const t = self.tick + s;
            const prim: Fixed = if ((t % 30) < 12) fixed.fromDecimalStr("0.7") else fixed.fromDecimalStr("0.08");
            const reg: brain_f.RegionId = if ((t / 30) % 2 == 0) .sens else .assoc;
            self.brain.buildExternal(prim, reg, ext[0..]);
            self.brain.step(ext[0..]);
        }
        self.tick +%= 1;
        const after = self.brain.totalSpikes();
        return .{
            .tick = self.tick,
            .mean_s = self.brain.meanS(),
            .spikes = after -% before,
        };
    }

    pub fn run(self: *OrganismF, n_ticks: u32) struct { ok: bool, ticks: u32, spikes: u32, n_syn: u32 } {
        var t: u32 = 0;
        while (t < n_ticks) : (t += 1) {
            _ = self.tickOnce();
        }
        const st = self.brain.structureReport();
        return .{
            .ok = self.brain.totalSpikes() >= 1 and st.n_synapses >= 100,
            .ticks = self.tick,
            .spikes = self.brain.totalSpikes(),
            .n_syn = st.n_synapses,
        };
    }
};

pub fn selfTest() bool {
    var o = OrganismF.init();
    const r = o.run(30);
    return r.ok;
}
