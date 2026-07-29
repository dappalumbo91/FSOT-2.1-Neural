//! Multi-unit fixed-point network — W @ spikes, no IEEE float.

const fixed = @import("fixed.zig");
const neuron_f = @import("neuron_fixed.zig");
const Fixed = fixed.Fixed;

pub const MAX_N: usize = 64;

pub const NetworkF = struct {
    n: usize,
    units: [MAX_N]neuron_f.NeuronF = undefined,
    W: [MAX_N * MAX_N]Fixed = undefined,
    last_fired: [MAX_N]bool = undefined,

    pub fn init(n: usize) NetworkF {
        var net: NetworkF = .{ .n = @min(n, MAX_N) };
        var i: usize = 0;
        while (i < net.n) : (i += 1) {
            net.units[i] = neuron_f.NeuronF{};
            net.units[i].reset();
            net.last_fired[i] = false;
            var j: usize = 0;
            while (j < net.n) : (j += 1) {
                net.W[i * MAX_N + j] = 0;
            }
        }
        return net;
    }

    pub fn setDefaultGeneticW(self: *NetworkF, syn_scale: Fixed) void {
        const n = self.n;
        var i: usize = 0;
        while (i < n) : (i += 1) {
            var j: usize = 0;
            while (j < n) : (j += 1) {
                if (i == j) {
                    self.W[i * MAX_N + j] = 0;
                    continue;
                }
                const dist: i64 = @intCast(if (i > j) i - j else j - i);
                // geom = 1/(1+dist*0.15)
                const geom = fixed.div(fixed.fromInt(1), fixed.add(fixed.fromInt(1), fixed.mul(fixed.fromInt(dist), fixed.fromDecimalStr("0.15"))));
                const pair: Fixed = if ((i % 2) == (j % 2)) fixed.fromInt(1) else fixed.fromInt(-1);
                self.W[i * MAX_N + j] = fixed.mul(fixed.mul(syn_scale, geom), pair);
            }
        }
    }

    pub fn step(self: *NetworkF, external: []const Fixed) void {
        const n = self.n;
        var syn: [MAX_N]Fixed = undefined;
        var i: usize = 0;
        while (i < n) : (i += 1) {
            var s: Fixed = 0;
            var j: usize = 0;
            while (j < n) : (j += 1) {
                if (self.last_fired[j]) s = fixed.add(s, self.W[i * MAX_N + j]);
            }
            syn[i] = s;
        }
        i = 0;
        while (i < n) : (i += 1) {
            const ext = if (i < external.len) external[i] else 0;
            const r = self.units[i].step(fixed.add(ext, syn[i]));
            self.last_fired[i] = r.fired;
        }
    }

    pub fn totalSpikes(self: *const NetworkF) u32 {
        var s: u32 = 0;
        var i: usize = 0;
        while (i < self.n) : (i += 1) s += self.units[i].spike_count;
        return s;
    }
};

pub fn networkSelfTest() struct { ok: bool, spikes: u32 } {
    var net = NetworkF.init(16);
    net.setDefaultGeneticW(fixed.fromDecimalStr("0.08"));
    var t: usize = 0;
    while (t < 100) : (t += 1) {
        var ext: [16]Fixed = .{fixed.fromDecimalStr("0.05")} ** 16;
        if ((t % 80) < 20) {
            var k: usize = 0;
            while (k < 16) : (k += 1) ext[k] = fixed.fromDecimalStr("0.65");
        }
        net.step(ext[0..]);
    }
    const sp = net.totalSpikes();
    return .{ .ok = sp >= 1, .spikes = sp };
}
