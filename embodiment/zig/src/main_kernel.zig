//! FSOT trinary + neuron freestanding kernel — Multiboot1 + COM1 serial.
const trit = @import("trit.zig");
const neuron = @import("neuron.zig");
const network = @import("network.zig");
const scalar = @import("scalar.zig");
const serial = @import("serial.zig");

const MULTIBOOT_MAGIC: u32 = 0x1BADB002;
const MULTIBOOT_FLAGS: u32 = 0x00000003;
const MULTIBOOT_CHECKSUM: u32 = 0 -% (MULTIBOOT_MAGIC +% MULTIBOOT_FLAGS);

export const multiboot_header align(4) linksection(".multiboot") = [_]u32{
    MULTIBOOT_MAGIC,
    MULTIBOOT_FLAGS,
    MULTIBOOT_CHECKSUM,
};

/// Tiny stack for freestanding (placed in bss).
var stack_bytes: [64 * 1024]u8 align(16) = undefined;

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
    // Bare metal: FPU may be disabled; enable before any f64 ops.
    asm volatile (
        \\fninit
        \\mov %%cr0, %%eax
        \\and $0xFFFFFFFB, %%eax
        \\or  $0x2, %%eax
        \\mov %%eax, %%cr0
        \\mov %%cr4, %%eax
        \\or  $0x200, %%eax
        \\mov %%eax, %%cr4
        ::: .{ .eax = true, .memory = true }
    );
}

fn kmain() noreturn {
    serial.init();
    serial.write("FSOT_STAGE zig neuron kernel\n");
    serial.write("I/O: serial UART | mind: parallel TritWord + FSOT step\n");
    enableFpu();
    serial.write("FPU enabled\n");

    serial.write("test:trit...\n");
    const tr = trit.selfTest();
    if (tr.ok) {
        serial.write("FSOT_TRIT PASS\n");
    } else {
        serial.write("FSOT_TRIT FAIL\n");
    }

    serial.write("test:scalar...\n");
    const s0 = scalar.computeNeuro(0.1, 0.0, 1.0);
    if (s0 == s0 and s0 > -3.0 and s0 < 3.0) {
        serial.write("FSOT_SCALAR PASS\n");
    } else {
        serial.write("FSOT_SCALAR FAIL\n");
    }

    serial.write("test:neuron...\n");
    const pst = neuron.paritySelfTest();
    if (pst.ok) {
        serial.write("FSOT_NEURON PASS spikes=");
        serial.writeU32(pst.spikes);
        serial.write("\n");
    } else {
        serial.write("FSOT_NEURON FAIL\n");
    }

    serial.write("test:network...\n");
    const nst = network.networkSelfTest();
    if (nst.ok) {
        serial.write("FSOT_NETWORK PASS spikes=");
        serial.writeU32(nst.spikes);
        serial.write("\n");
    } else {
        serial.write("FSOT_NETWORK FAIL\n");
    }

    if (tr.ok and pst.ok and nst.ok and (s0 == s0)) {
        serial.write("FSOT_STAGE_ZIG_NEURON_OK\n");
    } else {
        serial.write("FSOT_STAGE_ZIG_NEURON_FAIL\n");
    }

    while (true) {
        asm volatile ("hlt");
    }
}
