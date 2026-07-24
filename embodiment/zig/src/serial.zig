//! COM1 UART (0x3F8) — early bare-metal console.
//! Used under QEMU with: -serial stdio

const COM1: u16 = 0x3F8;

fn outb(port: u16, value: u8) void {
    // i386 / x86 freestanding port I/O
    asm volatile ("outb %[val], %[port]"
        :
        : [val] "{al}" (value),
          [port] "N{dx}" (port),
    );
}

fn inb(port: u16) u8 {
    return asm volatile ("inb %[port], %[ret]"
        : [ret] "={al}" (-> u8),
        : [port] "N{dx}" (port),
    );
}

pub fn init() void {
    // 16550-ish init: 38400 baud 8N1 (good enough for QEMU)
    outb(COM1 + 1, 0x00); // disable interrupts
    outb(COM1 + 3, 0x80); // DLAB on
    outb(COM1 + 0, 0x03); // divisor low (38400)
    outb(COM1 + 1, 0x00); // divisor high
    outb(COM1 + 3, 0x03); // 8N1
    outb(COM1 + 2, 0xC7); // FIFO
    outb(COM1 + 4, 0x0B); // IRQs enabled, RTS/DSR
}

fn isTransmitEmpty() bool {
    return (inb(COM1 + 5) & 0x20) != 0;
}

pub fn putc(c: u8) void {
    while (!isTransmitEmpty()) {}
    outb(COM1, c);
}

pub fn write(s: []const u8) void {
    for (s) |c| {
        if (c == '\n') putc('\r');
        putc(c);
    }
}

pub fn writeU32(n: u32) void {
    var buf: [10]u8 = undefined;
    var x = n;
    var i: usize = 0;
    if (x == 0) {
        putc('0');
        return;
    }
    while (x > 0) : (i += 1) {
        buf[i] = @intCast('0' + (x % 10));
        x /= 10;
    }
    while (i > 0) {
        i -= 1;
        putc(buf[i]);
    }
}
