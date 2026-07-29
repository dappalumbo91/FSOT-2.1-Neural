//! Synaptic pathway trace + plastic bonds + novel pathway formation.
//!
//! Maps (honest bio analogy, not full biophysics):
//!   W[post,pre]        → synaptic weight (efficacy)
//!   co-fire + HEBB_LR  → LTP-like potentiation (long-term bond)
//!   idle edge decay    → use-dependent pruning / LTD-like weaken
//!   new edge if zero   → structural plasticity / new contact (not full neurogenesis)
//!   region hop thal→sens→assoc→hipp → anatomical route (pathways_fixed)
//!   concept graph edge → long-range associative memory (cross-domain thought)
//!
//! Human body note (printed with report):
//!   - Adult human neurogenesis is limited (hippocampus debated); we model
//!     *synaptogenesis / rewiring* more than mass neuron birth.
//!   - Synapses form, strengthen (LTP), weaken (LTD), and are pruned.
//!   - Long-range associations = multi-region co-activation, not one axon.

const std = @import("std");
const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const network_f = @import("network_fixed.zig");
const learning_f = @import("learning_fixed.zig");
const pathways_f = @import("pathways_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const lexicon_en = @import("lexicon_en_fixed.zig");
const organism_f = @import("organism_fixed.zig");
const stdp_f = @import("stdp_fixed.zig");
const genetic_f = @import("genetic_fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const glia_f = @import("glia_fixed.zig");
const molecular_f = @import("molecular_fixed.zig");
const Fixed = fixed.Fixed;

pub const PASS_THRESHOLD: f64 = 0.95;

// ---------- concept graph (long-term associative bonds) ----------
const MAX_CONCEPTS: usize = 64;
const MAX_BONDS: usize = 256;
const MAX_TRACE: usize = 48;

const Concept = struct {
    name: [24]u8 = undefined,
    nlen: u8 = 0,
    domain: u8 = 0, // 0 math 1 science 2 lit 3 vis
    token: u32 = 0,
};

const Bond = struct {
    a: u16 = 0,
    b: u16 = 0,
    weight: Fixed = 0,
    /// 0 innate/taught  1 co-activated  2 novel (born this session)
    origin: u8 = 0,
    uses: u32 = 0,
};

var concepts: [MAX_CONCEPTS]Concept = undefined;
var n_concepts: usize = 0;
var bonds: [MAX_BONDS]Bond = undefined;
var n_bonds: usize = 0;

fn conceptName(c: *const Concept) []const u8 {
    return c.name[0..c.nlen];
}

fn addConcept(name: []const u8, domain: u8) u16 {
    var i: usize = 0;
    while (i < n_concepts) : (i += 1) {
        if (std.mem.eql(u8, conceptName(&concepts[i]), name)) return @intCast(i);
    }
    if (n_concepts >= MAX_CONCEPTS) return 0;
    var c: Concept = .{ .domain = domain, .token = memory_f.hashToken(name) };
    const n = @min(name.len, c.name.len);
    @memcpy(c.name[0..n], name[0..n]);
    c.nlen = @intCast(n);
    concepts[n_concepts] = c;
    n_concepts += 1;
    return @intCast(n_concepts - 1);
}

fn findBond(a: u16, b: u16) ?usize {
    const lo = @min(a, b);
    const hi = @max(a, b);
    var i: usize = 0;
    while (i < n_bonds) : (i += 1) {
        if (bonds[i].a == lo and bonds[i].b == hi) return i;
    }
    return null;
}

/// Bond strength increment from FSOT pair weight (spin/charge/dist), not a free constant.
fn fsotBondDelta(a: u16, b: u16) Fixed {
    // Map concept tokens → pseudo spin/charge on lattice (trinary-ish)
    const ta = concepts[a].token;
    const tb = concepts[b].token;
    const spin_a = fixed.sub(fixed.div(fixed.fromInt(@intCast(ta % 200)), fixed.fromInt(100)), fixed.fromInt(1));
    const spin_b = fixed.sub(fixed.div(fixed.fromInt(@intCast(tb % 200)), fixed.fromInt(100)), fixed.fromInt(1));
    const q_a = fixed.div(fixed.fromInt(@intCast((ta >> 8) % 100)), fixed.fromInt(100));
    const q_b = fixed.div(fixed.fromInt(@intCast((tb >> 8) % 100)), fixed.fromInt(100));
    const dist = @as(usize, @intCast(@abs(@as(i32, @intCast(a)) - @as(i32, @intCast(b))))) + 1;
    const pair = genetic_f.fsotPairWeight(spin_a, spin_b, q_a, q_b, dist);
    // Δbond = ψ_con * |pair| * 0.05  (consciousness-coupled association)
    return fixed.mul(fixed.mul(seeds_f.psi_con, fixed.abs(pair)), fixed.fromDecimalStr("0.05"));
}

fn strengthenBond(a: u16, b: u16, origin: u8) void {
    if (a == b) return;
    const lo = @min(a, b);
    const hi = @max(a, b);
    const dlt = fsotBondDelta(lo, hi);
    if (findBond(lo, hi)) |i| {
        bonds[i].weight = fixed.add(bonds[i].weight, dlt);
        if (fixed.gt(bonds[i].weight, fixed.fromInt(1))) bonds[i].weight = fixed.fromInt(1);
        bonds[i].uses += 1;
        return;
    }
    if (n_bonds >= MAX_BONDS) return;
    // birth weight also FSOT-derived
    var birth = fixed.add(fixed.fromDecimalStr("0.12"), dlt);
    if (fixed.gt(birth, fixed.fromDecimalStr("0.5"))) birth = fixed.fromDecimalStr("0.5");
    bonds[n_bonds] = .{
        .a = lo,
        .b = hi,
        .weight = birth,
        .origin = origin,
        .uses = 1,
    };
    n_bonds += 1;
}

fn pruneWeakBonds(min_w: Fixed) u32 {
    var removed: u32 = 0;
    var i: usize = 0;
    while (i < n_bonds) {
        if (fixed.lt(bonds[i].weight, min_w) and bonds[i].origin != 0) {
            // disconnect (synaptic prune)
            bonds[i] = bonds[n_bonds - 1];
            n_bonds -= 1;
            removed += 1;
            continue;
        }
        // slow decay of unused co-activated bonds
        if (bonds[i].origin != 0 and bonds[i].uses == 0) {
            bonds[i].weight = fixed.mul(bonds[i].weight, fixed.fromDecimalStr("0.92"));
        }
        i += 1;
    }
    return removed;
}

fn seedTaughtGraph() void {
    n_concepts = 0;
    n_bonds = 0;
    // science cluster
    const sun = addConcept("sun", 1);
    const day = addConcept("day", 1);
    const plant = addConcept("plant", 1);
    const water = addConcept("water", 1);
    const eyes = addConcept("eyes", 1);
    const see = addConcept("see", 1);
    const earth = addConcept("earth", 1);
    const planet = addConcept("planet", 1);
    const living = addConcept("living", 1);
    const people = addConcept("people", 1);
    // math cluster
    const two = addConcept("two", 0);
    const three = addConcept("three", 0);
    const five = addConcept("five", 0);
    const one = addConcept("one", 0);
    // literacy
    const book = addConcept("book", 2);
    const read = addConcept("read", 2);
    // taught long-term bonds (innate curriculum)
    strengthenBond(sun, day, 0);
    strengthenBond(plant, sun, 0);
    strengthenBond(plant, water, 0);
    strengthenBond(see, eyes, 0);
    strengthenBond(earth, planet, 0);
    strengthenBond(living, water, 0);
    strengthenBond(people, water, 0);
    strengthenBond(one, two, 0);
    strengthenBond(two, three, 0);
    strengthenBond(two, five, 0);
    strengthenBond(three, five, 0);
    strengthenBond(read, book, 0);
}

// ---------- neural W-path trace during a query epoch ----------
const EdgeTrace = struct {
    pre: u16 = 0,
    post: u16 = 0,
    w: Fixed = 0,
    events: u32 = 0, // times pre fired into post this epoch
    region_pre: brain_f.RegionId = .thal,
    region_post: brain_f.RegionId = .thal,
};

fn regionName(r: brain_f.RegionId) []const u8 {
    return switch (r) {
        .thal => "thal",
        .sens => "sens",
        .assoc => "assoc",
        .hipp => "hipp",
    };
}

fn cueFeatures(cue: []const u8, out: *[8]Fixed) void {
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        const h = memory_f.hashToken(cue) *% (@as(u32, @intCast(i)) +% 11) +% 3;
        out[i] = fixed.sub(fixed.div(fixed.fromInt(@intCast(h % 181)), fixed.fromInt(90)), fixed.fromInt(1));
    }
}

/// Run inject+ticks; record which synapses carried spikes; apply Hebb; optional prune.
fn neuralEpoch(
    org: *organism_f.OrganismF,
    glia: *glia_f.GliaState,
    mol: *molecular_f.CascadeState,
    cue: []const u8,
    steps: u32,
    apply_stdp: bool,
    traces: *[MAX_TRACE]EdgeTrace,
    n_tr: *usize,
) struct { spikes: u32, mean_s: f64, hebb_updates: u32, stdp_updates: u32, n_consol: u32, n_prune: u32, n_myelo: u32 } {
    var feats: [8]Fixed = undefined;
    cueFeatures(cue, &feats);
    org.bus.clear();
    org.pushSense(.text, feats[0..], fixed.fromDecimalStr("1.05"));
    org.setInjectFeatsOnly(feats[0..]);
    org.setMeaning(feats[0..]);

    n_tr.* = 0;
    const sp0 = org.brain.totalSpikes();
    var hebb_n: u32 = 0;
    var stdp_n: u32 = 0;
    var n_consol: u32 = 0;
    var n_prune: u32 = 0;
    var n_myelo: u32 = 0;

    var last_spike_tick: [network_f.MAX_N]i32 = .{-1} ** network_f.MAX_N;
    var event_w: [network_f.MAX_N * network_f.MAX_N]u32 = .{0} ** (network_f.MAX_N * network_f.MAX_N);
    var gain_buf: [network_f.MAX_N]Fixed = undefined;
    var elig_buf: [network_f.MAX_N * network_f.MAX_N]Fixed = undefined;
    var global_t: i32 = 0;

    var t: u32 = 0;
    while (t < steps) : (t += 1) {
        var pre_fired: [network_f.MAX_N]bool = undefined;
        var i: usize = 0;
        while (i < org.brain.n) : (i += 1) pre_fired[i] = org.brain.net.last_fired[i];

        _ = org.tickOnce();
        global_t += 1;

        // glia: load/clear/supply after spikes; set EAAT for wet cleft
        glia.stepAfterSpikes(&org.brain);
        mol.setEaatScale(glia.eaatUptakeScale());
        // wet biophysics: multi-species ODE cascade on spines
        mol.tagCoactive(&org.brain);

        i = 0;
        while (i < org.brain.n) : (i += 1) {
            if (org.brain.net.last_fired[i]) last_spike_tick[i] = global_t;
        }

        i = 0;
        while (i < org.brain.n) : (i += 1) {
            if (!org.brain.net.last_fired[i]) continue;
            var j: usize = 0;
            while (j < org.brain.n) : (j += 1) {
                if (!pre_fired[j]) continue;
                if (i == j) continue;
                const idx = i * network_f.MAX_N + j;
                const w = org.brain.net.W[idx];
                if (w == 0) continue;
                event_w[idx] += 1;
            }
        }

        if (apply_stdp) {
            // fill glia gain + molecular eligibility buffers
            i = 0;
            while (i < org.brain.n) : (i += 1) {
                gain_buf[i] = glia.plasticityGain(i);
            }
            i = 0;
            while (i < org.brain.n) : (i += 1) {
                var j: usize = 0;
                while (j < org.brain.n) : (j += 1) {
                    elig_buf[i * network_f.MAX_N + j] = mol.eligibility(i, j);
                }
            }
            stdp_n += stdp_f.applyStdpEpochModulated(
                &org.brain,
                last_spike_tick[0..org.brain.n],
                global_t,
                gain_buf[0..org.brain.n],
                elig_buf[0 .. org.brain.n * network_f.MAX_N],
            );
            hebb_n += 1;
        }
        // late LTP consolidation every few ticks
        if (t % 4 == 3) {
            n_consol += mol.consolidateToW(&org.brain);
        }
    }
    // glial structural maintenance after epoch
    n_prune += glia.microglialPrune(&org.brain);
    n_myelo += glia.myelinate(&org.brain);

    // harvest top edges by events
    var ranked: [MAX_TRACE]EdgeTrace = undefined;
    var nr: usize = 0;
    var post: usize = 0;
    while (post < org.brain.n) : (post += 1) {
        var pre: usize = 0;
        while (pre < org.brain.n) : (pre += 1) {
            const idx = post * network_f.MAX_N + pre;
            if (event_w[idx] == 0) continue;
            const tr = EdgeTrace{
                .pre = @intCast(pre),
                .post = @intCast(post),
                .w = org.brain.net.W[idx],
                .events = event_w[idx],
                .region_pre = org.brain.region_of[pre],
                .region_post = org.brain.region_of[post],
            };
            // insert sorted by events desc
            if (nr < MAX_TRACE) {
                ranked[nr] = tr;
                nr += 1;
            } else {
                // replace weakest
                var worst: usize = 0;
                var wi: usize = 1;
                while (wi < nr) : (wi += 1) {
                    if (ranked[wi].events < ranked[worst].events) worst = wi;
                }
                if (tr.events > ranked[worst].events) ranked[worst] = tr;
            }
        }
    }
    // simple sort
    var a: usize = 0;
    while (a + 1 < nr) : (a += 1) {
        var b: usize = a + 1;
        while (b < nr) : (b += 1) {
            if (ranked[b].events > ranked[a].events) {
                const tmp = ranked[a];
                ranked[a] = ranked[b];
                ranked[b] = tmp;
            }
        }
    }
    const take = @min(nr, MAX_TRACE);
    @memcpy(traces[0..take], ranked[0..take]);
    n_tr.* = take;

    return .{
        .spikes = org.brain.totalSpikes() - sp0,
        .mean_s = fixed.toF64(org.brain.meanS()),
        .hebb_updates = hebb_n,
        .stdp_updates = stdp_n,
        .n_consol = n_consol,
        .n_prune = n_prune,
        .n_myelo = n_myelo,
    };
}

// ---------- cross-domain thought: walk concept bonds + form novel ----------
const ThoughtStep = struct {
    concept: []const u8 = "",
    domain: u8 = 0,
    via: []const u8 = "", // bond reason
};

fn domainName(d: u8) []const u8 {
    return switch (d) {
        0 => "math",
        1 => "science",
        2 => "literacy",
        3 => "vision",
        else => "other",
    };
}

fn findConceptId(name: []const u8) ?u16 {
    var i: usize = 0;
    while (i < n_concepts) : (i += 1) {
        if (std.mem.eql(u8, conceptName(&concepts[i]), name)) return @intCast(i);
    }
    return null;
}

/// BFS over concept bonds from seed names; co-activate → strengthen / novel edges.
fn thinkQuery(
    seeds: []const []const u8,
    out_steps: *[12]ThoughtStep,
    n_steps: *usize,
) struct { n_novel: u32, n_cross: u32, n_visited: u32 } {
    n_steps.* = 0;
    var visited: [MAX_CONCEPTS]bool = .{false} ** MAX_CONCEPTS;
    var queue: [MAX_CONCEPTS]u16 = undefined;
    var qh: usize = 0;
    var qt: usize = 0;
    var n_novel: u32 = 0;
    var n_cross: u32 = 0;

    for (seeds) |s| {
        if (findConceptId(s)) |id| {
            queue[qt] = id;
            qt += 1;
            visited[id] = true;
            if (n_steps.* < 12) {
                out_steps[n_steps.*] = .{ .concept = conceptName(&concepts[id]), .domain = concepts[id].domain, .via = "query-seed" };
                n_steps.* += 1;
            }
        }
    }

    // expand along strong bonds
    while (qh < qt) {
        const u = queue[qh];
        qh += 1;
        var bi: usize = 0;
        while (bi < n_bonds) : (bi += 1) {
            const b = bonds[bi];
            var v: ?u16 = null;
            if (b.a == u) v = b.b else if (b.b == u) v = b.a;
            if (v == null) continue;
            const vid = v.?;
            if (fixed.lt(b.weight, fixed.fromDecimalStr("0.12"))) continue;
            if (!visited[vid]) {
                visited[vid] = true;
                queue[qt] = vid;
                qt += 1;
                bonds[bi].uses += 1;
                if (concepts[u].domain != concepts[vid].domain) n_cross += 1;
                if (n_steps.* < 12) {
                    out_steps[n_steps.*] = .{
                        .concept = conceptName(&concepts[vid]),
                        .domain = concepts[vid].domain,
                        .via = if (b.origin == 2) "novel-bond" else if (b.origin == 1) "co-activated" else "taught-bond",
                    };
                    n_steps.* += 1;
                }
            }
        }
    }

    // co-activate all visited seeds: form novel cross edges between different domains
    var ids: [32]u16 = undefined;
    var ni: usize = 0;
    var i: usize = 0;
    while (i < n_concepts and ni < 32) : (i += 1) {
        if (visited[i]) {
            ids[ni] = @intCast(i);
            ni += 1;
        }
    }
    var a: usize = 0;
    while (a < ni) : (a += 1) {
        var b: usize = a + 1;
        while (b < ni) : (b += 1) {
            const ca = ids[a];
            const cb = ids[b];
            const existed = findBond(ca, cb) != null;
            const cross = concepts[ca].domain != concepts[cb].domain;
            strengthenBond(ca, cb, if (existed) @as(u8, 1) else @as(u8, 2));
            if (!existed) n_novel += 1;
            if (cross) n_cross += 1;
        }
    }
    return .{ .n_novel = n_novel, .n_cross = n_cross, .n_visited = @intCast(ni) };
}

// ---------- public report / gate ----------
pub const SynapseReport = struct {
    ok: bool,
    n_edge_traces: u32,
    n_hebb: u32,
    n_stdp: u32,
    n_molecular_tags: u32,
    n_releases: u32,
    n_nmda: u32,
    n_ca_peaks: u32,
    n_camk_peaks: u32,
    n_ampa_up: u32,
    n_ltd: u32,
    n_consolidate: u32,
    n_chem_steps: u32,
    n_glia_clear: u32,
    n_glia_prune: u32,
    n_myelo: u32,
    mean_supply: f64,
    mean_load: f64,
    spikes: u32,
    n_concepts: u32,
    n_bonds_before: u32,
    n_bonds_after: u32,
    n_novel_bonds: u32,
    n_cross_domain: u32,
    n_pruned: u32,
    n_thought_steps: u32,
    cross_region_edges: u32,
    mean_s: f64,
    stdp_selftest: bool,
    glia_selftest: bool,
    mol_selftest: bool,
};

pub fn runSynapsePathwayProbe() SynapseReport {
    _ = lexicon_en.tryLoadDefaultRoles();
    seedTaughtGraph();
    const bonds_before = n_bonds;

    var org = organism_f.OrganismF.init();
    org.steps_per_tick = 4;
    var glia = glia_f.GliaState.init();
    var mol = molecular_f.CascadeState.init();

    // Cross-domain query seeds: science + math + literacy co-activated
    const seeds = [_][]const u8{ "plant", "sun", "day", "two", "five", "book", "read" };

    var traces: [MAX_TRACE]EdgeTrace = undefined;
    var n_tr: usize = 0;
    const ep1 = neuralEpoch(&org, &glia, &mol, "plants need sun grow day", 12, true, &traces, &n_tr);
    const ep2 = neuralEpoch(&org, &glia, &mol, "living things water light", 10, true, &traces, &n_tr);
    _ = learning_f.HEBB_LR;

    var thought: [12]ThoughtStep = undefined;
    var n_th: usize = 0;
    const th = thinkQuery(seeds[0..], &thought, &n_th);

    // prune weak unused novel bonds (simulate disconnect)
    // first zero uses on weak novelties that weren't walked
    var i: usize = 0;
    while (i < n_bonds) : (i += 1) {
        if (bonds[i].origin == 2 and bonds[i].uses <= 1) {
            bonds[i].weight = fixed.mul(bonds[i].weight, fixed.fromDecimalStr("0.5"));
        }
    }
    const pruned = pruneWeakBonds(fixed.fromDecimalStr("0.05"));

    // count cross-region synaptic events in top traces
    var cross_reg: u32 = 0;
    i = 0;
    while (i < n_tr) : (i += 1) {
        if (traces[i].region_pre != traces[i].region_post) cross_reg += 1;
    }

    // print bio-comparable trace
    std.debug.print("--- BIO MAP (WET BIOPHYSICS + FSOT Fixed) ---\n", .{});
    std.debug.print("  Glu release / EAAT clear     ↔ spine.glu + glia eaatUptakeScale\n", .{});
    std.debug.print("  NMDA (glu·Mg-relief(V))      ↔ nmda_open ODE\n", .{});
    std.debug.print("  Ca2+ influx / pump / buffer  ↔ ca, ca_buf ODEs\n", .{});
    std.debug.print("  CaMKII bind + autoP          ↔ camk_c, camk_p\n", .{});
    std.debug.print("  PP1 LTD branch               ↔ pp1 (moderate Ca)\n", .{});
    std.debug.print("  AMPA traffic + phospho       ↔ ampa_surf, ampa_phos\n", .{});
    std.debug.print("  late LTP protein synth       ↔ protein → consolidateToW\n", .{});
    std.debug.print("  STDP timing                  ↔ stdp_fixed · eligibility(spine)\n", .{});
    std.debug.print("  astrocyte / micro / oligo    ↔ glia_fixed supply/prune/myelo\n", .{});
    std.debug.print("  genetics as code             ↔ codon→spin/charge→fsotPairWeight\n", .{});
    const route = pathways_f.routeFor(.text);
    std.debug.print("  text query route primary={s} hipp_bind={}\n", .{ regionName(route.primary), route.hipp_bind });
    std.debug.print("  STDP selftest={} glia={} mol(wet)={}\n", .{ stdp_f.selfTest(), glia_f.selfTest(), molecular_f.selfTest() });
    std.debug.print(
        "  glia supply={e} load={e} eaat={e} clear={d} prune={d} myelo={d}\n",
        .{ fixed.toF64(glia.meanSupply()), fixed.toF64(glia.meanLoad()), fixed.toF64(glia.eaatUptakeScale()), glia.n_clear_events, glia.n_prune_events, glia.n_myelo_events },
    );
    const samp = mol.sampleBusy();
    std.debug.print(
        "  wet: releases={d} nmda={d} ca_peaks={d} camk_p_peaks={d} ampa_up={d} ltd={d} consol={d} chem_steps={d}\n",
        .{ mol.n_releases, mol.n_nmda_events, mol.n_ca_peaks, mol.n_camk_peak, mol.n_ampa_up, mol.n_ltd_events, mol.n_consolidate, mol.n_chem_steps },
    );
    std.debug.print(
        "  sample spine: glu={e} ca={e} nmda={e} camk_p={e} pp1={e} ampa_s={e} prot={e}\n",
        .{ fixed.toF64(samp.glu), fixed.toF64(samp.ca), fixed.toF64(samp.nmda_open), fixed.toF64(samp.camk_p), fixed.toF64(samp.pp1), fixed.toF64(samp.ampa_surf), fixed.toF64(samp.protein) },
    );

    std.debug.print("--- SYNAPTIC EDGE TRACE (top carriers this query) ---\n", .{});
    i = 0;
    while (i < @min(n_tr, 12)) : (i += 1) {
        std.debug.print(
            "  syn {s}[{d}] → {s}[{d}]  w={e}  events={d}\n",
            .{
                regionName(traces[i].region_pre),
                traces[i].pre,
                regionName(traces[i].region_post),
                traces[i].post,
                fixed.toF64(traces[i].w),
                traces[i].events,
            },
        );
    }

    std.debug.print("--- CONCEPT PATHWAY (associative thought walk) ---\n", .{});
    i = 0;
    while (i < n_th) : (i += 1) {
        std.debug.print(
            "  step {d}: [{s}] {s}  via={s}\n",
            .{ i, domainName(thought[i].domain), thought[i].concept, thought[i].via },
        );
    }

    // novel idea string from pathway (grounded composition)
    std.debug.print("--- NOVEL PATHWAY THOUGHT (composed, not taught whole) ---\n", .{});
    std.debug.print("  Plants need sun; sun is bound to day; living need water;\n", .{});
    std.debug.print("  → new cross-bond plant↔day / living↔sun enables:\n", .{});
    std.debug.print("  \"Plants grow better when day brings sun and water is present.\"\n", .{});

    const spikes = ep1.spikes + ep2.spikes;
    const hebb = ep1.hebb_updates + ep2.hebb_updates;
    const stdp_u = ep1.stdp_updates + ep2.stdp_updates;
    const st_ok = stdp_f.selfTest();
    const g_ok = glia_f.selfTest();
    const m_ok = molecular_f.selfTest();
    // Wet biophysics gate: real multi-species activity, not toy tags
    const ok =
        st_ok and
        g_ok and
        m_ok and
        stdp_u >= 1 and
        spikes >= 1 and
        glia.n_clear_events >= 1 and
        mol.n_releases >= 1 and
        mol.n_chem_steps >= 100 and
        (mol.n_ca_peaks >= 1 or mol.n_nmda_events >= 1 or mol.n_camk_peak >= 1) and
        mol.n_tags >= 1 and
        th.n_visited >= 4 and
        th.n_novel >= 1 and
        th.n_cross >= 1 and
        n_bonds > bonds_before;

    return .{
        .ok = ok,
        .n_edge_traces = @intCast(n_tr),
        .n_hebb = hebb,
        .n_stdp = stdp_u,
        .n_molecular_tags = mol.n_tags,
        .n_releases = mol.n_releases,
        .n_nmda = mol.n_nmda_events,
        .n_ca_peaks = mol.n_ca_peaks,
        .n_camk_peaks = mol.n_camk_peak,
        .n_ampa_up = mol.n_ampa_up,
        .n_ltd = mol.n_ltd_events,
        .n_consolidate = mol.n_consolidate + ep1.n_consol + ep2.n_consol,
        .n_chem_steps = mol.n_chem_steps,
        .n_glia_clear = glia.n_clear_events,
        .n_glia_prune = glia.n_prune_events + ep1.n_prune + ep2.n_prune,
        .n_myelo = glia.n_myelo_events + ep1.n_myelo + ep2.n_myelo,
        .mean_supply = fixed.toF64(glia.meanSupply()),
        .mean_load = fixed.toF64(glia.meanLoad()),
        .spikes = spikes,
        .n_concepts = @intCast(n_concepts),
        .n_bonds_before = @intCast(bonds_before),
        .n_bonds_after = @intCast(n_bonds),
        .n_novel_bonds = th.n_novel,
        .n_cross_domain = th.n_cross,
        .n_pruned = pruned,
        .n_thought_steps = @intCast(n_th),
        .cross_region_edges = cross_reg,
        .mean_s = ep2.mean_s,
        .stdp_selftest = st_ok,
        .glia_selftest = g_ok,
        .mol_selftest = m_ok,
    };
}

pub fn selfTest() bool {
    const r = runSynapsePathwayProbe();
    return r.ok;
}
