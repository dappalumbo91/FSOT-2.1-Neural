# Boot FSOT mind body on Windows (live senses + loop + optional speakers).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$out = Join-Path $env:TEMP "fsot_mind_boot.exe"
$cache = Join-Path $env:TEMP "fsot_zig_cache_boot"
Write-Host "=== build fsot_mind (Windows host I/O) ==="
zig build-exe -OReleaseFast "-femit-bin=$out" --cache-dir $cache --name fsot_mind_boot src/main_mind.zig -lgdi32 -luser32 -lwinmm
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not (Test-Path $out)) { Write-Host "FAIL: binary missing $out"; exit 2 }

Write-Host "=== host-senses ==="
& $out host-senses
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== body (daemon 120 ticks) ==="
& $out body
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== speakers ==="
& $out speakers
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "FSOT_BODY_BOOT_OK"
