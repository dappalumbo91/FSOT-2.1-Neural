//! Multi-unit FSOT batch + genetic-style W apply (float64 host/kernel).
//! Parallel in the architectural sense: one step advances all units;
//! synaptic current is W @ spikes (dense).

const neuron = @import("neuron.zig");
const trit = @import("trit.zig");

pub const MAX_N: usize = 64;

pub const Network = struct {
    n: usize,
    units: [MAX_N]neuron.Neuron = undefined,
    /// Row-major W[post][pre] — current into post when pre fired last step
    W: [MAX_N * MAX_N]f64 = undefined,
    last_fired: [MAX_N]bool = undefined,

    pub fn init(n: usize) Network {
        var net: Network = .{ .n = @min(n, MAX_N) };
        var i: usize = 0;
        while (i < net.n) : (i += 1) {
            net.units[i] = neuron.Neuron{};
            net.units[i].reset();
            net.last_fired[i] = false;
            var j: usize = 0;
            while (j < net.n) : (j += 1) {
                net.W[i * MAX_N + j] = 0;
            }
        }
        return net;
    }

    /// Simple geometric + trinary-pair style weights (host sets detailed genetics).
    pub fn setDefaultGeneticW(self: *Network, syn_scale: f64) void {
        const n = self.n;
        var i: usize = 0;
        while (i < n) : (i += 1) {
            var j: usize = 0;
            while (j < n) : (j += 1) {
                if (i == j) {
                    self.W[i * MAX_N + j] = 0;
                    continue;
                }
                // distance falloff + fixed pair (placeholder spins ±1 by index parity)
                const si: trit.Trit = if ((i % 2) == 0) 1 else -1;
                const sj: trit.Trit = if ((j % 2) == 0) 1 else -1;
                const pair = trit.pair(si, sj);
                const dist: f64 = @floatFromInt(if (i > j) i - j else j - i);
                const geom = 1.0 / (1.0 + dist * 0.15);
                self.W[i * MAX_N + j] = syn_scale * geom * @as(f64, @floatFromInt(pair));
            }
        }
    }

    pub fn step(self: *Network, external: []const f64) void {
        const n = self.n;
        // synaptic current from previous spikes
        var syn: [MAX_N]f64 = undefined;
        var i: usize = 0;
        while (i < n) : (i += 1) {
            var s: f64 = 0;
            var j: usize = 0;
            while (j < n) : (j += 1) {
                if (self.last_fired[j]) {
                    s += self.W[i * MAX_N + j];
                }
            }
            syn[i] = s;
        }
        i = 0;
        while (i < n) : (i += 1) {
            const ext = if (i < external.len) external[i] else 0;
            const r = self.units[i].step(ext + syn[i]);
            self.last_fired[i] = r.fired;
        }
    }

    pub fn totalSpikes(self: *const Network) u32 {
        var s: u32 = 0;
        var i: usize = 0;
        while (i < self.n) : (i += 1) {
            s += self.units[i].spike_count;
        }
        return s;
    }
};

pub fn networkSelfTest() struct { ok: bool, spikes: u32 } {
    var net = Network.init(16);
    net.setDefaultGeneticW(0.08);
    var t: usize = 0;
    while (t < 100) : (t += 1) {
        var ext: [16]f64 = .{0.05} ** 16;
        if ((t % 80) < 20) {
            var k: usize = 0;
            while (k < 16) : (k += 1) {
                ext[k] = 0.65;
            }
        }
        net.step(ext[0..]);
    }
    const sp = net.totalSpikes();
    return .{ .ok = sp >= 1, .spikes = sp };
}
