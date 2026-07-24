const std = @import("std");

pub fn build(b: *std.Build) void {
    const target_host = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // --- Host self-test (fast, no QEMU) ---
    const host = b.addExecutable(.{
        .name = "fsot_trit_host",
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/main_host.zig"),
            .target = target_host,
            .optimize = optimize,
        }),
    });
    b.installArtifact(host);

    const run_host = b.addRunArtifact(host);
    const host_step = b.step("host", "Run trinary self-test on host");
    host_step.dependOn(&run_host.step);

    // --- Freestanding Multiboot kernel for QEMU ---
    // QEMU -kernel Multiboot1 path wants a 32-bit image (not x86_64 ELF).
    const kernel_target = b.resolveTargetQuery(.{
        .cpu_arch = .x86,
        .os_tag = .freestanding,
        .abi = .none,
    });

    const kernel = b.addExecutable(.{
        .name = "fsot_trit_kernel",
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/main_kernel.zig"),
            .target = kernel_target,
            .optimize = .ReleaseSafe,
            .code_model = .kernel,
            .red_zone = false,
        }),
    });
    kernel.entry = .{ .symbol_name = "_start" };
    kernel.setLinkerScript(b.path("linker.ld"));
    // Multiboot / QEMU -kernel expects ELF; disable PIE if needed
    kernel.pie = false;
    kernel.link_eh_frame_hdr = false;
    b.installArtifact(kernel);

    const kernel_step = b.step("kernel", "Build freestanding QEMU kernel");
    kernel_step.dependOn(&b.addInstallArtifact(kernel, .{}).step);
}
