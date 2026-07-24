# Build Zig trinary host + kernel from repo root.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "embodiment\zig")

zig build host
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& ".\zig-out\bin\fsot_trit_host.exe"
if ($LASTEXITCODE -ne 0) {
    # non-windows name
    if (Test-Path ".\zig-out\bin\fsot_trit_host") {
        & ".\zig-out\bin\fsot_trit_host"
    }
}

zig build kernel
Write-Host "kernel artifacts:"
Get-ChildItem ".\zig-out\bin" -ErrorAction SilentlyContinue
