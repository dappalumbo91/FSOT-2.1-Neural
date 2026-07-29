//! Multi-region genetic brain — fixed-point continuous state.
//! Same structure as brain.zig (codon genotypes → phenotype → W → step)
//! but unit dynamics and W magnitudes are Fixed (no IEEE float on the path).

const fixed = @import("fixed.zig");
const network_f = @import("network_fixed.zig");
const neuron_f = @import("neuron_fixed.zig");
const genotype = @import("genotype.zig");
const cell_types = @import("cell_types.zig");
const genetic_fixed = @import("genetic_fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const Fixed = fixed.Fixed;

pub const MAX_N: usize = 32;
pub const N_THAL: usize = 4;
pub const N_SENS: usize = 12;
pub const N_ASSOC: usize = 10;
pub const N_HIPP: usize = 6;
pub const N_TOTAL: usize = 32;

pub const RegionId = enum(u8) { thal = 0, sens = 1, assoc = 2, hipp = 3 };

pub const BrainF = struct {
    net: network_f.NetworkF,
    region_of: [MAX_N]RegionId = undefined,
    region_local: [MAX_N]usize = undefined,
    cell_of: [MAX_N]cell_types.CellType = undefined,
    genotypes: [MAX_N]genotype.NeuronGenotype = undefined,
    n: usize = N_TOTAL,
    seed: u32 = 42,

    pub fn init() BrainF {
        return initSeeded(42, true);
    }

    pub fn initSeeded(seed: u32, diversity: bool) BrainF {
        var b: BrainF = .{
            .net = network_f.NetworkF.init(N_TOTAL),
            .n = N_TOTAL,
            .seed = seed,
        };
        var u: usize = 0;
        while (u < N_THAL) : (u += 1) {
            b.region_of[u] = .thal;
            b.region_local[u] = u;
        }
        while (u < N_THAL + N_SENS) : (u += 1) {
            b.region_of[u] = .sens;
            b.region_local[u] = u - N_THAL;
        }
        while (u < N_THAL + N_SENS + N_ASSOC) : (u += 1) {
            b.region_of[u] = .assoc;
            b.region_local[u] = u - N_THAL - N_SENS;
        }
        while (u < N_TOTAL) : (u += 1) {
            b.region_of[u] = .hipp;
            b.region_local[u] = u - N_THAL - N_SENS - N_ASSOC;
        }

        const regions = [_]struct { start: usize, n: usize, mix: cell_types.Mix, seed_off: u32 }{
            .{ .start = 0, .n = N_THAL, .mix = cell_types.MIX_THAL, .seed_off = 0 },
            .{ .start = N_THAL, .n = N_SENS, .mix = cell_types.MIX_CORTICAL, .seed_off = 17 },
            .{ .start = N_THAL + N_SENS, .n = N_ASSOC, .mix = cell_types.MIX_CORTICAL, .seed_off = 34 },
            .{ .start = N_THAL + N_SENS + N_ASSOC, .n = N_HIPP, .mix = cell_types.MIX_HIPP, .seed_off = 51 },
        };

        for (regions) |rg| {
            var labels: [MAX_N]cell_types.CellType = undefined;
            _ = cell_types.allocate(rg.n, rg.mix, labels[0..rg.n]);
            var ids: [MAX_N]usize = undefined;
            cell_types.shuffleIds(rg.n, seed +% rg.seed_off, ids[0..rg.n]);
            var local: usize = 0;
            while (local < rg.n) : (local += 1) {
                const gid = rg.start + local;
                const ct = labels[local];
                b.cell_of[gid] = ct;
                b.genotypes[gid] = genotype.buildCellTypeGenotype(@intCast(ids[local]), ct, diversity);
                b.genotypes[gid].unit_id = @intCast(gid);
                applyPhenotype(&b.net.units[gid], &b.genotypes[gid]);
            }
        }
        b.wireGenetic();
        return b;
    }

    fn applyPhenotype(n: *neuron_f.NeuronF, g: *const genotype.NeuronGenotype) void {
        const ph = g.phenotype;
        // genotype phenotype is still f64 from codon path — convert once at construction
        // (codon expression uses f64 seeds today; lattice is for *dynamics*)
        n.d_eff = fixed.fromF64Lab(ph.d_eff);
        n.fire_thr = fixed.fromF64Lab(ph.fire_threshold);
        n.ref_steps = @intFromFloat(@round(ph.refractory_steps));
        n.adapt_gain = fixed.fromF64Lab(ph.adapt_gain);
        n.adapt_decay = fixed.fromF64Lab(ph.adapt_decay);
        n.adapt_step = fixed.fromF64Lab(ph.adapt_step);
        n.resting_S = fixed.fromF64Lab(ph.resting_bias);
        n.n_channels = fixed.fromF64Lab(ph.n_channels);
        n.p_props = fixed.fromF64Lab(ph.p_props);
        n.reset();
    }

    pub fn wireGenetic(self: *BrainF) void {
        // Pure fixed lattice W — no IEEE float assembly (genetic_fixed.zig).
        var reg: [MAX_N]u8 = undefined;
        var loc: [MAX_N]usize = undefined;
        var i: usize = 0;
        while (i < self.n) : (i += 1) {
            reg[i] = @intFromEnum(self.region_of[i]);
            loc[i] = self.region_local[i];
        }
        genetic_fixed.wireFromGenotypes(
            self.net.W[0..],
            network_f.MAX_N,
            self.n,
            self.genotypes[0..self.n],
            reg[0..self.n],
            loc[0..self.n],
            fixed.fromDecimalStr("0.14"),
        );
    }

    pub fn reset(self: *BrainF) void {
        var i: usize = 0;
        while (i < self.n) : (i += 1) {
            self.net.units[i].reset();
            self.net.last_fired[i] = false;
        }
    }

    pub fn buildExternal(self: *const BrainF, primary: Fixed, region: RegionId, out: []Fixed) void {
        var i: usize = 0;
        while (i < self.n and i < out.len) : (i += 1) {
            out[i] = fixed.fromDecimalStr("0.02");
            if (self.region_of[i] == region) {
                if (self.genotypes[i].synapse_sign > 0) out[i] = primary else out[i] = fixed.mul(primary, fixed.fromDecimalStr("0.25"));
            }
            if (region == .sens and self.region_of[i] == .thal and self.genotypes[i].synapse_sign > 0) {
                out[i] = fixed.div(primary, seeds_f.phi);
            }
        }
    }

    pub fn step(self: *BrainF, external: []const Fixed) void {
        self.net.step(external);
    }

    pub fn meanS(self: *const BrainF) Fixed {
        var s: Fixed = 0;
        var i: usize = 0;
        while (i < self.n) : (i += 1) s = fixed.add(s, self.net.units[i].S);
        return fixed.div(s, fixed.fromInt(@intCast(self.n)));
    }

    pub fn totalSpikes(self: *const BrainF) u32 {
        return self.net.totalSpikes();
    }

    pub fn structureReport(self: *const BrainF) struct {
        n_units: u32,
        n_e: u32,
        n_i: u32,
        n_synapses: u32,
        n_pyr: u32,
        n_pv: u32,
        n_sst: u32,
        n_vip: u32,
    } {
        var n_e: u32 = 0;
        var n_i: u32 = 0;
        var n_syn: u32 = 0;
        var n_pyr: u32 = 0;
        var n_pv: u32 = 0;
        var n_sst: u32 = 0;
        var n_vip: u32 = 0;
        var i: usize = 0;
        while (i < self.n) : (i += 1) {
            if (self.genotypes[i].synapse_sign > 0) n_e += 1 else n_i += 1;
            switch (self.cell_of[i]) {
                .pyr => n_pyr += 1,
                .pv => n_pv += 1,
                .sst => n_sst += 1,
                .vip => n_vip += 1,
            }
            var j: usize = 0;
            while (j < self.n) : (j += 1) {
                if (self.net.W[i * network_f.MAX_N + j] != 0) n_syn += 1;
            }
        }
        return .{
            .n_units = @intCast(self.n),
            .n_e = n_e,
            .n_i = n_i,
            .n_synapses = n_syn,
            .n_pyr = n_pyr,
            .n_pv = n_pv,
            .n_sst = n_sst,
            .n_vip = n_vip,
        };
    }
};

pub fn brainSelfTest() struct { ok: bool, spikes: u32 } {
    var b = BrainF.initSeeded(42, false);
    var ext: [N_TOTAL]Fixed = undefined;
    var t: usize = 0;
    while (t < 40) : (t += 1) {
        const prim: Fixed = if ((t % 20) < 10) fixed.fromDecimalStr("0.7") else fixed.fromDecimalStr("0.08");
        b.buildExternal(prim, .sens, ext[0..]);
        b.step(ext[0..]);
    }
    const st = b.structureReport();
    const sp = b.totalSpikes();
    return .{ .ok = sp >= 1 and st.n_synapses >= 100 and st.n_pyr >= 20, .spikes = sp };
}
