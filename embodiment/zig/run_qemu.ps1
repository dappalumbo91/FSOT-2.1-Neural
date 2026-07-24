# Build freestanding trinary kernel and run under QEMU (serial console).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$zigCmd = Get-Command zig -ErrorAction SilentlyContinue
$zig = $null
if ($zigCmd) { $zig = $zigCmd.Source }
if (-not $zig) {
    $cand = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Filter zig.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
    if ($cand) { $zig = $cand }
}
if (-not $zig) { throw "zig not found on PATH" }

Write-Host "=== zig build kernel ==="
& $zig build kernel

$kernel = Join-Path $PSScriptRoot "zig-out\bin\fsot_trit_kernel"
if (-not (Test-Path $kernel)) {
    Write-Host "FAIL: kernel binary not found"
    exit 2
}

$qemuCmd = Get-Command qemu-system-x86_64 -ErrorAction SilentlyContinue
$qemu = $null
if ($qemuCmd) { $qemu = $qemuCmd.Source }
if (-not $qemu -and (Test-Path "C:\Program Files\qemu\qemu-system-x86_64.exe")) {
    $qemu = "C:\Program Files\qemu\qemu-system-x86_64.exe"
}
if (-not $qemu) {
    Write-Host "WARN: qemu-system-x86_64 not found - kernel at $kernel"
    exit 0
}

$serialLog = Join-Path $PSScriptRoot "qemu_serial.log"
$errLog = Join-Path $PSScriptRoot "qemu_err.log"
Remove-Item $serialLog, $errLog -ErrorAction SilentlyContinue

Write-Host "=== QEMU (serial log, ~3s) ==="
$p = Start-Process -FilePath $qemu -ArgumentList @(
    "-display", "none",
    "-serial", "file:$serialLog",
    "-no-reboot",
    "-m", "32M",
    "-kernel", $kernel
) -PassThru -WindowStyle Hidden -RedirectStandardError $errLog

Start-Sleep -Seconds 3
if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }

Write-Host "--- serial output ---"
if (Test-Path $serialLog) {
    Get-Content $serialLog
    $txt = Get-Content $serialLog -Raw
    if ($txt -match "FSOT_TRIT PASS") {
        Write-Host "=== QEMU GATE PASS ==="
        exit 0
    }
    Write-Host "=== QEMU GATE FAIL (no PASS line) ==="
    exit 1
}
Write-Host "no serial log"
if (Test-Path $errLog) { Get-Content $errLog }
exit 1
