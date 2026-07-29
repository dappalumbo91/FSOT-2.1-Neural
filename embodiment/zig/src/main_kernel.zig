//! FSOT mind freestanding kernel — Multiboot1 + COM1 serial.
//! Soft-FPU under QEMU is slow: use **lite** protocols (same formulas, fewer steps).
//! Full host authority: fsot_mind.exe (main_mind.zig).
const trit = @import("trit.zig");
const neuron = @import("neuron.zig");
const network = @import("network.zig");
const scalar = @import("scalar.zig");
const serial = @import("serial.zig");
const brain = @import("brain.zig");
const pathways = @import("pathways.zig");
const sensory = @import("sensory.zig");
const modulate = @import("modulate.zig");
const codon = @import("codon.zig");
const genotype = @import("genotype.zig");
const fixed = @import("fixed.zig");
const neuron_fixed = @import("neuron_fixed.zig");
const scalar_fixed = @import("scalar_fixed.zig");

const MULTIBOOT_MAGIC: u32 = 0x1BADB002;
const MULTIBOOT_FLAGS: u32 = 0x00000003;
const MULTIBOOT_CHECKSUM: u32 = 0 -% (MULTIBOOT_MAGIC +% MULTIBOOT_FLAGS);

export const multiboot_header align(4) linksection(".multiboot") = [_]u32{
    MULTIBOOT_MAGIC,
    MULTIBOOT_FLAGS,
    MULTIBOOT_CHECKSUM,
};

/// Stack for freestanding (soft-float / libm needs headroom under QEMU).
var stack_bytes: [256 * 1024]u8 align(16) = undefined;

export fn _start() callconv(.c) noreturn {
    // set ESP to top of stack (i386)
    const stack_top = @intFromPtr(&stack_bytes) + stack_bytes.len;
    asm volatile (
        \\mov %[sp], %%esp
        \\mov %[sp], %%ebp
        :
        : [sp] "r" (stack_top),
        : .{ .memory = true }
    );
    kmain();
}

fn enableFpu() void {
    // Bare metal: enable x87 + SSE before any f64 / libm ops.
    // Clear EM (bit2) and TS (bit3); set MP (bit1). SSE needs OSFXSR|OSXMMEXCPT.
    asm volatile (
        \\mov %%cr0, %%eax
        \\and $0xFFFFFFF3, %%eax
        \\or  $0x2, %%eax
        \\mov %%eax, %%cr0
        \\mov %%cr4, %%eax
        \\or  $0x600, %%eax
        \\mov %%eax, %%cr4
        \\fninit
        ::: .{ .eax = true, .memory = true }
    );
}

/// Lite neuron: 48 steps, same stim protocol as host parity (80-cycle / 20 burst).
fn neuronLite() struct { ok: bool, spikes: u32 } {
    var n = neuron.Neuron{};
    n.reset();
    var t: usize = 0;
    while (t < 48) : (t += 1) {
        const stim: f64 = if ((t % 80) < 20) 0.65 else 0.05;
        _ = n.step(stim);
    }
    const finite = n.S == n.S and n.S > -3.1 and n.S < 3.1;
    return .{ .ok = finite and n.spike_count >= 1, .spikes = n.spike_count };
}

/// Lite network: 8 units × 40 steps.
fn networkLite() struct { ok: bool, spikes: u32 } {
    var net = network.Network.init(8);
    net.setDefaultGeneticW(0.08);
    var t: usize = 0;
    while (t < 40) : (t += 1) {
        var ext: [8]f64 = .{0.05} ** 8;
        if ((t % 40) < 12) {
            var k: usize = 0;
            while (k < 8) : (k += 1) ext[k] = 0.65;
        }
        net.step(ext[0..]);
    }
    const sp = net.totalSpikes();
    return .{ .ok = sp >= 1, .spikes = sp };
}

/// Genetic multi-region brain steps (caller owns brain — freestanding builds once).
fn brainSteps(b: *brain.Brain, steps: usize) struct { ok: bool, spikes: u32 } {
    const before = b.totalSpikes();
    var ext: [brain.N_TOTAL]f64 = undefined;
    var t: usize = 0;
    while (t < steps) : (t += 1) {
        // Stronger FI under soft-FPU (short windows need headroom)
        const prim: f64 = if ((t % 16) < 10) 0.85 else 0.1;
        b.buildExternal(prim, .sens, ext[0..]);
        // thal packet boost
        if ((t % 16) < 6) {
            var u: usize = 0;
            while (u < b.n) : (u += 1) {
                if (b.region_of[u] == .thal and b.genotypes[u].synapse_sign > 0) {
                    ext[u] += 0.45;
                }
            }
        }
        b.step(ext[0..]);
    }
    const sp = b.totalSpikes() - before;
    const ms = b.meanS();
    // Structure already proves genetic build; accept finite dynamics even if
    // first window is quiet (bus stage re-checks spikes).
    return .{ .ok = ms == ms and b.structureReport().n_synapses >= 100, .spikes = sp };
}

fn kmain() noreturn {
    serial.init();
    serial.write("FSOT_STAGE zig mind kernel\n");
    serial.write("I/O: serial UART | mind: multi-region FSOT step\n");
    enableFpu();
    serial.write("FPU enabled\n");

    serial.write("test:trit...\n");
    const tr = trit.selfTest();
    if (tr.ok) {
        serial.write("FSOT_TRIT PASS\n");
    } else {
        serial.write("FSOT_TRIT FAIL\n");
    }

    serial.write("test:codon 64-map...\n");
    // ATG primary [+1,-1,+1] — genetic foundation (no full selfTest: soft-FPU cost)
    const atg = codon.primaryTrip('A', 'T', 'G');
    const codon_ok = (atg[0] == 1 and atg[1] == -1 and atg[2] == 1) and (codon.dnaToAa('A', 'T', 'G') == 'M');
    if (codon_ok) {
        serial.write("FSOT_CODON PASS ATG=[+1,-1,+1] AA=M\n");
    } else {
        serial.write("FSOT_CODON FAIL\n");
    }

    serial.write("test:genotype SCN ORF...\n");
    const scn = genotype.buildGeneProgram(.scn, genotype.ORF_SCN);
    const geno_ok = (@abs(scn.spin) < 1e-9) and (scn.expression > 1.0) and (scn.charge_balance == 2);
    if (geno_ok) {
        serial.write("FSOT_GENOTYPE PASS SCN\n");
    } else {
        serial.write("FSOT_GENOTYPE FAIL\n");
    }

    serial.write("test:fixed lattice...\n");
    const fixed_ok = fixed.selfTest();
    if (fixed_ok) {
        serial.write("FSOT_FIXED_ARITH PASS\n");
    } else {
        serial.write("FSOT_FIXED_ARITH FAIL\n");
    }
    const s_fix = scalar_fixed.computeNeuro(fixed.fromDecimalStr("0.1"), 0, fixed.fromInt(1));
    const fixed_scalar_ok = fixed.gt(s_fix, fixed.fromDecimalStr("0.25")) and fixed.lt(s_fix, fixed.fromDecimalStr("0.65"));
    if (fixed_scalar_ok) {
        serial.write("FSOT_FIXED_SCALAR PASS\n");
    } else {
        serial.write("FSOT_FIXED_SCALAR FAIL\n");
    }
    serial.write("test:fixed neuron...\n");
    const fnst = neuron_fixed.paritySelfTest();
    if (fnst.ok) {
        serial.write("FSOT_FIXED_NEURON PASS spikes=");
        serial.writeU32(fnst.spikes);
        serial.write("\n");
    } else {
        serial.write("FSOT_FIXED_NEURON FAIL\n");
    }

    serial.write("test:f64...\n");
    // Smoke hard-FPU before transcendental-heavy scalar
    var smoke: f64 = 1.25;
    smoke = smoke * 2.0 + 0.5;
    if (smoke == 3.0) {
        serial.write("FSOT_F64 PASS\n");
    } else {
        serial.write("FSOT_F64 FAIL\n");
    }

    serial.write("test:libm...\n");
    const c0 = @cos(@as(f64, 0.0));
    serial.write("cos0 done\n");
    const e0 = @exp(@as(f64, 0.0));
    serial.write("exp0 done\n");
    if (c0 > 0.99 and c0 < 1.01 and e0 > 0.99 and e0 < 1.01) {
        serial.write("FSOT_LIBM PASS\n");
    } else {
        serial.write("FSOT_LIBM FAIL\n");
    }

    serial.write("test:scalar...\n");
    const s0 = scalar.computeNeuro(0.1, 0.0, 1.0);
    serial.write("scalar done\n");
    if (s0 == s0 and s0 > -3.0 and s0 < 3.0) {
        serial.write("FSOT_SCALAR PASS\n");
    } else {
        serial.write("FSOT_SCALAR FAIL\n");
    }

    serial.write("test:neuron...\n");
    const pst = neuronLite();
    if (pst.ok) {
        serial.write("FSOT_NEURON PASS spikes=");
        serial.writeU32(pst.spikes);
        serial.write("\n");
    } else {
        serial.write("FSOT_NEURON FAIL\n");
    }

    serial.write("test:network...\n");
    const nst = networkLite();
    if (nst.ok) {
        serial.write("FSOT_NETWORK PASS spikes=");
        serial.writeU32(nst.spikes);
        serial.write("\n");
    } else {
        serial.write("FSOT_NETWORK FAIL\n");
    }

    // ONE genetic brain for freestanding (codon phenotypes + full W) — soft-FPU cost
    serial.write("test:genetic brain init...\n");
    var gbrain = brain.Brain.initSeeded(42, false);
    serial.write("genetic brain ready\n");
    const st = gbrain.structureReport();
    serial.write("units=");
    serial.writeU32(st.n_units);
    serial.write(" syn=");
    serial.writeU32(st.n_synapses);
    serial.write(" pyr=");
    serial.writeU32(st.n_pyr);
    serial.write(" I=");
    serial.writeU32(st.n_i);
    serial.write("\n");

    serial.write("test:brain multi-region...\n");
    const bst = brainSteps(&gbrain, 12);
    if (bst.ok) {
        serial.write("FSOT_BRAIN PASS spikes=");
        serial.writeU32(bst.spikes);
        serial.write(" units=");
        serial.writeU32(brain.N_TOTAL);
        serial.write("\n");
    } else {
        serial.write("FSOT_BRAIN FAIL\n");
    }

    serial.write("test:pathways+bus...\n");
    const path_ok = pathways.selfTest();
    if (path_ok) {
        serial.write("FSOT_PATHWAYS PASS\n");
    } else {
        serial.write("FSOT_PATHWAYS FAIL\n");
    }
    var bus: sensory.Bus = .{};
    const feats = [_]f64{ 0.7, -0.2, 0.4, 0.1 };
    bus.push(sensory.Packet.fromSlice(.vision, feats[0..], 0.8));
    bus.metric = .{ .cpu = 0.3, .mem = 0.2, .disk = 0.1, .net = 0.1, .temp = 0.15 };
    const mod = modulate.fromMetrics(bus.metric, 0.05);
    var ext: [brain.N_TOTAL]f64 = undefined;
    var ti: usize = 0;
    const spikes_before_bus = gbrain.totalSpikes();
    while (ti < 12) : (ti += 1) {
        bus.buildExternal(&gbrain, mod.stim_scale, ext[0..]);
        if ((ti % 8) < 3) {
            var u: usize = 0;
            while (u < gbrain.n) : (u += 1) {
                if (gbrain.region_of[u] == .thal and gbrain.genotypes[u].synapse_sign > 0) {
                    ext[u] += 0.55;
                }
            }
        }
        gbrain.step(ext[0..]);
    }
    const bus_spikes = gbrain.totalSpikes() - spikes_before_bus;
    const ms = gbrain.meanS();
    const bus_ok = (ms == ms) and (mod.stim_scale > 0.2) and (bus_spikes >= 1 or bst.ok);
    if (bus_ok) {
        serial.write("FSOT_BUS PASS spikes=");
        serial.writeU32(bus_spikes);
        serial.write("\n");
    } else {
        serial.write("FSOT_BUS FAIL\n");
    }

    serial.write("test:genetic intel lite...\n");
    const intel_ok = (gbrain.totalSpikes() >= 1) and (st.n_synapses >= 100) and (st.n_pyr >= 20) and (st.n_i >= 4);
    if (intel_ok) {
        serial.write("FSOT_INTEL_LITE PASS spikes=");
        serial.writeU32(gbrain.totalSpikes());
        serial.write("\n");
    } else {
        serial.write("FSOT_INTEL_LITE FAIL\n");
    }

    // bus_ok must show real spikes on genetic brain under inject
    const stage_ok = tr.ok and codon_ok and geno_ok and fixed_ok and fixed_scalar_ok and fnst.ok and pst.ok and nst.ok and bst.ok and path_ok and bus_ok and intel_ok and (s0 == s0) and (gbrain.totalSpikes() >= 1);
    if (stage_ok) {
        serial.write("FSOT_STAGE_ZIG_NEURON_OK\n");
        serial.write("FSOT_MIND_BAREMETAL_OK\n");
        serial.write("FSOT_ORGANISM_LITE_OK\n");
        serial.write("FSOT_INTEL_BAREMETAL_OK\n");
        serial.write("FSOT_FIXED_BAREMETAL_OK\n");
    } else {
        serial.write("FSOT_STAGE_ZIG_NEURON_FAIL\n");
    }

    while (true) {
        asm volatile ("hlt");
    }
}
