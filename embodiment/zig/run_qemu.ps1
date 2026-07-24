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

$kernelSrc = Join-Path $PSScriptRoot "zig-out\bin\fsot_trit_kernel"
if (-not (Test-Path $kernelSrc)) {
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
    Write-Host "WARN: qemu-system-x86_64 not found - kernel at $kernelSrc"
    exit 0
}

# Copy artifacts to TEMP (no spaces) so QEMU path parsing is reliable on Windows
$kernel = Join-Path $env:TEMP "fsot_trit_kernel"
$serialLog = Join-Path $env:TEMP "fsot_trit_qemu_serial.log"
$errLog = Join-Path $env:TEMP "fsot_trit_qemu_err.log"
Copy-Item -Force $kernelSrc $kernel
Remove-Item $serialLog, $errLog -ErrorAction SilentlyContinue

Write-Host "=== QEMU (serial log, ~3s) ==="
$arg = "-display none -serial file:$serialLog -no-reboot -m 32M -kernel `"$kernel`""
$p = Start-Process -FilePath $qemu -ArgumentList $arg -PassThru -WindowStyle Hidden -RedirectStandardError $errLog

Start-Sleep -Seconds 3
if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }

Write-Host "--- serial output ---"
if (Test-Path $serialLog) {
    Get-Content $serialLog
    $txt = Get-Content $serialLog -Raw
    if (($txt -match "FSOT_STAGE_ZIG_NEURON_OK") -or (($txt -match "FSOT_TRIT PASS") -and ($txt -match "FSOT_NEURON PASS"))) {
        Write-Host "=== QEMU GATE PASS ==="
        exit 0
    }
    Write-Host "=== QEMU GATE FAIL (missing stage PASS lines) ==="
    exit 1
}
Write-Host "no serial log"
if (Test-Path $errLog) { Get-Content $errLog }
exit 1
