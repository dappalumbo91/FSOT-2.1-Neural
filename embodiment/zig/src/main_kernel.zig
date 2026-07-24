//! FSOT trinary freestanding kernel — Multiboot1 + COM1 serial self-test.
//! QEMU: qemu-system-x86_64 -display none -serial stdio -kernel fsot_trit_kernel

const trit = @import("trit.zig");
const serial = @import("serial.zig");

/// Multiboot1 header (QEMU -kernel / GRUB compatible).
const MULTIBOOT_MAGIC: u32 = 0x1BADB002;
const MULTIBOOT_FLAGS: u32 = 0x00000003; // align modules + memory map
const MULTIBOOT_CHECKSUM: u32 = uncheckedSub(0, MULTIBOOT_MAGIC +% MULTIBOOT_FLAGS);

fn uncheckedSub(a: u32, b: u32) u32 {
    return a -% b;
}

export const multiboot_header align(4) linksection(".multiboot") = [_]u32{
    MULTIBOOT_MAGIC,
    MULTIBOOT_FLAGS,
    MULTIBOOT_CHECKSUM,
};

export fn _start() callconv(.c) noreturn {
    serial.init();
    serial.write("FSOT_TRIT kernel boot (Zig freestanding)\n");
    serial.write("I/O: serial UART COM1 | datapath: parallel TritWord\n");

    const r = trit.selfTest();
    if (r.ok) {
        serial.write("FSOT_TRIT PASS\n");
        serial.write("ATG codon primary: +1 -1 +1\n");
        serial.write("parallel pairWords: ok\n");
    } else {
        serial.write("FSOT_TRIT FAIL fails=");
        serial.writeU32(r.fails);
        serial.write("\n");
    }

    // Hang (QEMU -no-reboot keeps serial output readable)
    while (true) {
        asm volatile ("hlt");
    }
}
