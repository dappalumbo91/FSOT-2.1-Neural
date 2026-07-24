# Build freestanding trinary kernel and run under QEMU (serial console).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== zig build kernel ==="
zig build kernel

$kernel = Join-Path $PSScriptRoot "zig-out\bin\fsot_trit_kernel"
if (-not (Test-Path $kernel)) {
    # lake-style alternate install path
    $alt = Join-Path $PSScriptRoot "zig-out\bin\fsot_trit_kernel.elf"
    if (Test-Path $alt) { $kernel = $alt }
}

if (-not (Test-Path $kernel)) {
    Write-Host "FAIL: kernel binary not found under zig-out/bin"
    Get-ChildItem (Join-Path $PSScriptRoot "zig-out") -Recurse -ErrorAction SilentlyContinue | Select-Object FullName
    exit 2
}

$qemu = Get-Command qemu-system-x86_64 -ErrorAction SilentlyContinue
if (-not $qemu) {
    Write-Host "WARN: qemu-system-x86_64 not on PATH — kernel built at:"
    Write-Host "  $kernel"
    Write-Host "Install QEMU or add it to PATH, then re-run."
    exit 0
}

Write-Host "=== QEMU serial (30s max) ==="
# -no-reboot: halt after kernel hang; serial on stdio
& qemu-system-x86_64 `
    -display none `
    -serial stdio `
    -no-reboot `
    -device isa-debug-exit,iobase=0xf4,iosize=0x04 `
    -kernel $kernel `
    2>&1 | Select-Object -First 40

Write-Host "=== done ==="
