//! Multi-region FSOT brain — Zig mind core.
//! Foundation spine (no shortcuts):
//!   DNA codon (64 PRIMARY) → ORF genes → expression → phenotype
//!   → typed population (region mixes) → genetic W (motif/sparsity/recip)
//!   → FSOT step
//! Authority twin of brain_architecture.py + genetic_genotype.py + cell_types.py.

const network = @import("network.zig");
const seeds = @import("seeds.zig");
const cell_types = @import("cell_types.zig");
const genotype = @import("genotype.zig");
const genetic = @import("genetic.zig");
const bio_probe = @import("bio_probe.zig");

pub const MAX_N: usize = 32;

pub const RegionId = enum(u8) {
    thal = 0,
    sens = 1,
    assoc = 2,
    hipp = 3,
};

pub const N_THAL: usize = 4;
pub const N_SENS: usize = 12;
pub const N_ASSOC: usize = 10;
pub const N_HIPP: usize = 6;
pub const N_TOTAL: usize = N_THAL + N_SENS + N_ASSOC + N_HIPP;

pub const Brain = struct {
    net: network.Network,
    region_of: [MAX_N]RegionId = undefined,
    region_local: [MAX_N]usize = undefined,
    cell_of: [MAX_N]cell_types.CellType = undefined,
    genotypes: [MAX_N]genotype.NeuronGenotype = undefined,
    n: usize = N_TOTAL,
    seed: u32 = 42,

    pub fn init() Brain {
        return initSeeded(42, true);
    }

    pub fn initWithDiversity(diversity: bool) Brain {
        return initSeeded(42, diversity);
    }

    /// seed matches Python BrainDesignConfig.seed (default 42).
    pub fn initSeeded(seed: u32, diversity: bool) Brain {
        var b: Brain = .{
            .net = network.Network.init(N_TOTAL),
            .n = N_TOTAL,
            .seed = seed,
        };

        // region layout
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

        // per-region typed population (Python build_typed_population)
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
            // labels[local] paired with shuffled unit_id for diversity ORF
            var local: usize = 0;
            while (local < rg.n) : (local += 1) {
                const gid = rg.start + local;
                const ct = labels[local];
                const div_uid: u32 = @intCast(ids[local]);
                b.cell_of[gid] = ct;
                b.genotypes[gid] = genotype.buildCellTypeGenotype(div_uid, ct, diversity);
                b.genotypes[gid].unit_id = @intCast(gid);
                // apply codon-derived phenotype
                const p = genotype.phenotypeToUnitParams(b.genotypes[gid].phenotype);
                bio_probe.applyParams(&b.net.units[gid], p);
                b.net.units[gid].resting_S = b.genotypes[gid].phenotype.resting_bias;
                b.net.units[gid].n_channels = b.genotypes[gid].phenotype.n_channels;
                b.net.units[gid].p_props = b.genotypes[gid].phenotype.p_props;
                b.net.units[gid].reset();
            }
        }

        b.wireGenetic();
        return b;
    }

    pub fn reset(self: *Brain) void {
        var i: usize = 0;
        while (i < self.n) : (i += 1) {
            self.net.units[i].reset();
            self.net.last_fired[i] = false;
        }
    }

    pub fn wireGenetic(self: *Brain) void {
        var reg: [MAX_N]u8 = undefined;
        var loc: [MAX_N]usize = undefined;
        var i: usize = 0;
        while (i < self.n) : (i += 1) {
            reg[i] = @intFromEnum(self.region_of[i]);
            loc[i] = self.region_local[i];
        }
        genetic.wireFromGenotypes(
            self.net.W[0..],
            network.MAX_N,
            self.n,
            self.genotypes[0..self.n],
            reg[0..self.n],
            loc[0..self.n],
            0.14,
        );
    }

    pub fn wireDefault(self: *Brain) void {
        self.wireGenetic();
    }

    pub fn buildExternal(
        self: *const Brain,
        primary: f64,
        region: RegionId,
        out: []f64,
    ) void {
        const n = self.n;
        var i: usize = 0;
        while (i < n and i < out.len) : (i += 1) {
            out[i] = 0.02;
            if (self.region_of[i] == region) {
                if (self.genotypes[i].synapse_sign > 0) {
                    out[i] = primary;
                } else {
                    out[i] = primary * 0.25;
                }
            }
            if (region == .sens and self.region_of[i] == .thal and self.genotypes[i].synapse_sign > 0) {
                out[i] = primary * (1.0 / seeds.phi);
            }
        }
    }

    pub fn step(self: *Brain, external: []const f64) void {
        self.net.step(external);
    }

    pub fn meanS(self: *const Brain) f64 {
        var s: f64 = 0;
        var i: usize = 0;
        while (i < self.n) : (i += 1) s += self.net.units[i].S;
        return s / @as(f64, @floatFromInt(self.n));
    }

    pub fn totalSpikes(self: *const Brain) u32 {
        return self.net.totalSpikes();
    }

    pub fn regionMeanS(self: *const Brain, r: RegionId) f64 {
        var s: f64 = 0;
        var c: f64 = 0;
        var i: usize = 0;
        while (i < self.n) : (i += 1) {
            if (self.region_of[i] == r) {
                s += self.net.units[i].S;
                c += 1;
            }
        }
        if (c < 1) return 0;
        return s / c;
    }

    pub fn injectFeatures(self: *const Brain, feats: []const f64, scale: f64, out: []f64) void {
        const n = self.n;
        var i: usize = 0;
        while (i < n and i < out.len) : (i += 1) out[i] = 0.02;
        if (feats.len == 0) return;
        var sens_i: usize = 0;
        i = 0;
        while (i < n and i < out.len) : (i += 1) {
            if (self.region_of[i] == .sens) {
                const f = feats[sens_i % feats.len];
                out[i] = if (self.genotypes[i].synapse_sign > 0) scale * f else scale * f * 0.3;
                sens_i += 1;
            } else if (self.region_of[i] == .thal) {
                const f = feats[i % feats.len];
                out[i] = scale * f / seeds.phi;
            } else if (self.region_of[i] == .assoc) {
                const f = feats[(i * 3) % feats.len];
                out[i] = 0.55 * scale * f;
            }
        }
    }

    pub const StructureReport = struct {
        n_units: u32,
        n_e: u32,
        n_i: u32,
        n_synapses: u32,
        mean_abs_w: f64,
        n_pyr: u32,
        n_pv: u32,
        n_sst: u32,
        n_vip: u32,
        mean_composite_spin: f64,
        mean_composite_charge: f64,
    };

    pub fn applyBioParams(self: *Brain, params: []const bio_probe.UnitParams) void {
        var i: usize = 0;
        while (i < self.n) : (i += 1) {
            if (params.len == 0) break;
            bio_probe.applyParams(&self.net.units[i], params[i % params.len]);
        }
    }

    pub fn structureReport(self: *const Brain) StructureReport {
        var n_e: u32 = 0;
        var n_i: u32 = 0;
        var n_syn: u32 = 0;
        var sum_abs: f64 = 0;
        var n_pyr: u32 = 0;
        var n_pv: u32 = 0;
        var n_sst: u32 = 0;
        var n_vip: u32 = 0;
        var sum_spin: f64 = 0;
        var sum_ch: f64 = 0;
        var i: usize = 0;
        while (i < self.n) : (i += 1) {
            if (self.genotypes[i].synapse_sign > 0) n_e += 1 else n_i += 1;
            switch (self.cell_of[i]) {
                .pyr => n_pyr += 1,
                .pv => n_pv += 1,
                .sst => n_sst += 1,
                .vip => n_vip += 1,
            }
            sum_spin += self.genotypes[i].composite_spin;
            sum_ch += self.genotypes[i].composite_charge;
            var j: usize = 0;
            while (j < self.n) : (j += 1) {
                const w = self.net.W[i * network.MAX_N + j];
                if (w != 0) {
                    n_syn += 1;
                    sum_abs += if (w < 0) -w else w;
                }
            }
        }
        const mean_w = if (n_syn > 0) sum_abs / @as(f64, @floatFromInt(n_syn)) else 0;
        const nf: f64 = @floatFromInt(self.n);
        return .{
            .n_units = @intCast(self.n),
            .n_e = n_e,
            .n_i = n_i,
            .n_synapses = n_syn,
            .mean_abs_w = mean_w,
            .n_pyr = n_pyr,
            .n_pv = n_pv,
            .n_sst = n_sst,
            .n_vip = n_vip,
            .mean_composite_spin = sum_spin / nf,
            .mean_composite_charge = sum_ch / nf,
        };
    }
};

pub fn brainSelfTest() struct { ok: bool, spikes: u32, mean_s: f64 } {
    var b = Brain.init();
    var t: usize = 0;
    var ext: [N_TOTAL]f64 = undefined;
    while (t < 80) : (t += 1) {
        const prim: f64 = if ((t % 40) < 12) 0.7 else 0.08;
        b.buildExternal(prim, .sens, ext[0..]);
        b.step(ext[0..]);
    }
    const sp = b.totalSpikes();
    const ms = b.meanS();
    const st = b.structureReport();
    const ok = sp >= 1 and ms == ms and st.n_pyr >= 1 and st.n_i >= 1 and st.n_synapses >= 1;
    return .{ .ok = ok, .spikes = sp, .mean_s = ms };
}
