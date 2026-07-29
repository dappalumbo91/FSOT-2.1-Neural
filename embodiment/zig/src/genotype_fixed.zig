//! Genotype + phenotype on fixed lattice (codon ORFs → expression → knobs).
//! Twin of genotype.zig continuous math without IEEE float dynamics.

const fixed = @import("fixed.zig");
const codon = @import("codon.zig");
const codon_f = @import("codon_fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const cell_types = @import("cell_types.zig");
const genotype = @import("genotype.zig");
const Fixed = fixed.Fixed;

pub const GeneProgramF = struct {
    name: genotype.GeneName,
    spin: Fixed = 0,
    expression: Fixed = fixed.fromInt(1),
    charge_balance: i32 = 0,
    n_codons: u8 = 0,
};

pub const PhenotypeF = struct {
    n_channels: Fixed = fixed.fromInt(4),
    p_props: Fixed = fixed.fromInt(3),
    d_eff: Fixed = fixed.fromInt(13),
    fire_threshold: Fixed = fixed.fromDecimalStr("1.05"),
    refractory_steps: Fixed = fixed.fromInt(12),
    adapt_step: Fixed = fixed.fromDecimalStr("0.7"),
    adapt_gain: Fixed = fixed.fromDecimalStr("0.02"),
    adapt_decay: Fixed = fixed.fromDecimalStr("0.988"),
    resting_bias: Fixed = seeds_f.resting_s,
    fi_stim: Fixed = fixed.fromDecimalStr("0.5"),
    composite_spin: Fixed = 0,
    composite_charge: Fixed = 0,
};

pub const NeuronGenotypeF = struct {
    unit_id: u32 = 0,
    cell_type: cell_types.CellType = .pyr,
    synapse_sign: i8 = 1,
    genes: [4]GeneProgramF = undefined,
    phenotype: PhenotypeF = .{},
    composite_spin: Fixed = 0,
    composite_charge: Fixed = 0,
};

fn baseOrf(name: genotype.GeneName) []const u8 {
    return switch (name) {
        .scn => genotype.ORF_SCN,
        .kcn => genotype.ORF_KCN,
        .cacna => genotype.ORF_CACNA,
        .leak => genotype.ORF_LEAK,
    };
}

fn cellOrf(ct: cell_types.CellType, name: genotype.GeneName) []const u8 {
    // reuse DNA strings from genotype.zig
    return switch (ct) {
        .pyr => switch (name) {
            .scn => genotype.ORF_PYR_SCN,
            .kcn => genotype.ORF_PYR_KCN,
            .cacna => genotype.ORF_PYR_CACNA,
            .leak => genotype.ORF_PYR_LEAK,
        },
        .pv => switch (name) {
            .scn => genotype.ORF_PV_SCN,
            .kcn => genotype.ORF_PV_KCN,
            .cacna => genotype.ORF_PV_CACNA,
            .leak => genotype.ORF_PV_LEAK,
        },
        .sst => switch (name) {
            .scn => genotype.ORF_SST_SCN,
            .kcn => genotype.ORF_SST_KCN,
            .cacna => genotype.ORF_SST_CACNA,
            .leak => genotype.ORF_SST_LEAK,
        },
        .vip => switch (name) {
            .scn => genotype.ORF_VIP_SCN,
            .kcn => genotype.ORF_VIP_KCN,
            .cacna => genotype.ORF_VIP_CACNA,
            .leak => genotype.ORF_VIP_LEAK,
        },
    };
}

fn expressionBias(ct: cell_types.CellType, name: genotype.GeneName) Fixed {
    return switch (ct) {
        .pyr => switch (name) {
            .scn => fixed.fromDecimalStr("1.15"),
            .kcn => fixed.fromDecimalStr("0.95"),
            .cacna => fixed.fromDecimalStr("1.10"),
            .leak => fixed.fromInt(1),
        },
        .pv => switch (name) {
            .scn => fixed.fromDecimalStr("1.25"),
            .kcn => fixed.fromDecimalStr("1.45"),
            .cacna => fixed.fromDecimalStr("0.70"),
            .leak => fixed.fromDecimalStr("0.95"),
        },
        .sst => switch (name) {
            .scn => fixed.fromDecimalStr("0.95"),
            .kcn => fixed.fromDecimalStr("1.05"),
            .cacna => fixed.fromDecimalStr("1.35"),
            .leak => fixed.fromDecimalStr("1.05"),
        },
        .vip => switch (name) {
            .scn => fixed.fromDecimalStr("1.05"),
            .kcn => fixed.fromDecimalStr("0.90"),
            .cacna => fixed.fromDecimalStr("1.15"),
            .leak => fixed.fromDecimalStr("1.10"),
        },
    };
}

pub fn buildGeneProgram(name: genotype.GeneName, dna: []const u8) GeneProgramF {
    var res: [codon.MAX_RESIDUES]codon.Residue = undefined;
    const nr = codon.decodeOrf(dna, &res);
    var g: GeneProgramF = .{ .name = name };
    if (nr == 0) return g;
    g.n_codons = @intCast(nr);
    g.spin = codon_f.meanSpin(res[0..nr]);
    g.expression = codon_f.geneExpression(res[0..nr]);
    g.charge_balance = codon.chargeBalance(res[0..nr]);
    return g;
}

pub fn phenotypeFromGenes(genes: *const [4]GeneProgramF) PhenotypeF {
    const scn = genes[0].expression;
    const kcn = genes[1].expression;
    const ca = genes[2].expression;
    const leak = genes[3].expression;
    const one = fixed.fromInt(1);
    const mean_expr = fixed.div(fixed.add(fixed.add(scn, kcn), fixed.add(ca, leak)), fixed.fromInt(4));

    var d_eff = fixed.add(
        seeds_f.neuro_d_eff,
        fixed.add(
            fixed.mul(fixed.mul(seeds_f.phi, fixed.sub(ca, one)), fixed.fromDecimalStr("0.35")),
            fixed.mul(fixed.mul(seeds_f.gamma, fixed.sub(scn, kcn)), fixed.fromDecimalStr("0.2")),
        ),
    );
    d_eff = fixed.clamp(d_eff, fixed.fromInt(8), fixed.fromInt(20));

    var fire = fixed.add(
        fixed.fromDecimalStr("1.05"),
        fixed.add(
            fixed.mul(fixed.fromDecimalStr("-0.12"), fixed.sub(scn, one)),
            fixed.mul(fixed.fromDecimalStr("0.06"), fixed.sub(kcn, one)),
        ),
    );
    fire = fixed.clamp(fire, fixed.fromDecimalStr("0.85"), fixed.fromDecimalStr("1.25"));

    var ref = fixed.mul(fixed.fromInt(12), fixed.add(fixed.fromDecimalStr("0.85"), fixed.mul(fixed.fromDecimalStr("0.30"), kcn)));
    ref = fixed.clamp(ref, fixed.fromInt(4), fixed.fromInt(40));

    var adapt_step = fixed.mul(fixed.fromDecimalStr("0.7"), fixed.add(fixed.fromDecimalStr("0.6"), fixed.mul(fixed.fromDecimalStr("0.8"), ca)));
    adapt_step = fixed.clamp(adapt_step, 0, fixed.fromInt(8));

    const adapt_gain = fixed.mul(fixed.fromDecimalStr("0.02"), fixed.add(fixed.fromDecimalStr("0.7"), fixed.mul(fixed.fromDecimalStr("0.6"), ca)));
    var adapt_decay = fixed.sub(fixed.fromDecimalStr("0.988"), fixed.mul(fixed.fromDecimalStr("0.004"), fixed.sub(ca, one)));
    adapt_decay = fixed.clamp(adapt_decay, fixed.fromDecimalStr("0.96"), fixed.fromDecimalStr("0.995"));

    var rest = fixed.add(seeds_f.resting_s, fixed.mul(fixed.mul(fixed.fromDecimalStr("0.02"), fixed.sub(scn, leak)), seeds_f.eta_eff));
    rest = fixed.clamp(rest, fixed.fromDecimalStr("0.30"), fixed.fromDecimalStr("0.65"));

    var fi = fixed.mul(
        fixed.fromDecimalStr("0.50"),
        fixed.add(
            fixed.fromDecimalStr("0.85"),
            fixed.sub(fixed.mul(fixed.fromDecimalStr("0.25"), scn), fixed.mul(fixed.fromDecimalStr("0.10"), kcn)),
        ),
    );
    fi = fixed.clamp(fi, fixed.fromDecimalStr("0.25"), fixed.fromDecimalStr("0.95"));

    var sum_spin_w: Fixed = 0;
    var sum_expr: Fixed = 0;
    var sum_q: Fixed = 0;
    var i: usize = 0;
    while (i < 4) : (i += 1) {
        sum_spin_w = fixed.add(sum_spin_w, fixed.mul(genes[i].spin, genes[i].expression));
        sum_expr = fixed.add(sum_expr, genes[i].expression);
        sum_q = fixed.add(sum_q, fixed.mul(fixed.fromInt(genes[i].charge_balance), genes[i].expression));
    }
    const cspin = if (sum_expr != 0) fixed.div(sum_spin_w, sum_expr) else 0;
    const ccharge = fixed.div(sum_q, fixed.fromInt(4));

    return .{
        .n_channels = fixed.mul(seeds_f.neuro_n_channels, fixed.add(fixed.fromDecimalStr("0.75"), fixed.mul(fixed.fromDecimalStr("0.25"), mean_expr))),
        .p_props = seeds_f.neuro_p,
        .d_eff = d_eff,
        .fire_threshold = fire,
        .refractory_steps = ref,
        .adapt_step = adapt_step,
        .adapt_gain = adapt_gain,
        .adapt_decay = adapt_decay,
        .resting_bias = rest,
        .fi_stim = fi,
        .composite_spin = cspin,
        .composite_charge = ccharge,
    };
}

fn applyClassNudge(ct: cell_types.CellType, ph: *PhenotypeF) void {
    switch (ct) {
        .pv => {
            ph.refractory_steps = fixed.clamp(fixed.mul(ph.refractory_steps, fixed.fromDecimalStr("0.45")), fixed.fromInt(3), fixed.fromInt(40));
            ph.adapt_step = fixed.mul(ph.adapt_step, fixed.fromDecimalStr("0.35"));
            ph.fire_threshold = fixed.clamp(fixed.sub(ph.fire_threshold, fixed.fromDecimalStr("0.04")), fixed.fromDecimalStr("0.85"), fixed.fromDecimalStr("1.25"));
            ph.fi_stim = fixed.clamp(fixed.mul(ph.fi_stim, fixed.fromDecimalStr("1.15")), fixed.fromDecimalStr("0.25"), fixed.fromDecimalStr("0.95"));
        },
        .sst => {
            ph.adapt_step = fixed.clamp(fixed.mul(ph.adapt_step, fixed.fromDecimalStr("1.4")), 0, fixed.fromInt(10));
            ph.refractory_steps = fixed.mul(ph.refractory_steps, fixed.fromDecimalStr("1.05"));
        },
        .vip => {
            ph.fi_stim = fixed.mul(ph.fi_stim, fixed.fromDecimalStr("0.9"));
            ph.d_eff = fixed.clamp(fixed.add(ph.d_eff, fixed.mul(fixed.fromDecimalStr("0.3"), seeds_f.phi)), fixed.fromInt(8), fixed.fromInt(20));
        },
        .pyr => {
            ph.adapt_step = fixed.mul(ph.adapt_step, fixed.fromDecimalStr("1.05"));
        },
    }
}

pub fn buildCellTypeGenotype(unit_id: u32, ct: cell_types.CellType, diversity: bool) NeuronGenotypeF {
    var gt: NeuronGenotypeF = .{
        .unit_id = unit_id,
        .cell_type = ct,
        .synapse_sign = cell_types.specOf(ct).sign,
    };
    const names = [_]genotype.GeneName{ .scn, .kcn, .cacna, .leak };
    var mutbuf: [32]u8 = undefined;
    var i: usize = 0;
    while (i < 4) : (i += 1) {
        const name = names[i];
        const base = cellOrf(ct, name);
        const dna = if (diversity) genotype.mutateOrf(base, unit_id, @intCast(i), &mutbuf) else base;
        var g = buildGeneProgram(name, dna);
        const bias = expressionBias(ct, name);
        g.expression = fixed.clamp(fixed.mul(g.expression, bias), fixed.fromDecimalStr("0.05"), fixed.fromDecimalStr("3.5"));
        gt.genes[i] = g;
    }
    gt.phenotype = phenotypeFromGenes(&gt.genes);
    applyClassNudge(ct, &gt.phenotype);
    gt.composite_spin = gt.phenotype.composite_spin;
    gt.composite_charge = gt.phenotype.composite_charge;
    return gt;
}

pub fn selfTest() bool {
    if (!codon_f.selfTest()) return false;
    const pyr = buildCellTypeGenotype(0, .pyr, false);
    // spin ~0.104, ref ~13.44
    if (fixed.lt(pyr.composite_spin, fixed.fromDecimalStr("0.05"))) return false;
    if (fixed.gt(pyr.composite_spin, fixed.fromDecimalStr("0.20"))) return false;
    if (fixed.lt(pyr.phenotype.refractory_steps, fixed.fromInt(10))) return false;
    if (fixed.gt(pyr.phenotype.refractory_steps, fixed.fromInt(18))) return false;
    const pv = buildCellTypeGenotype(0, .pv, false);
    if (!fixed.lt(pv.phenotype.refractory_steps, pyr.phenotype.refractory_steps)) return false;
    return true;
}
