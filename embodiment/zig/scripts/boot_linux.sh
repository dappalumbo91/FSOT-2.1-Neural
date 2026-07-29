#!/usr/bin/env bash
# Boot FSOT mind on Linux / WSL (plant metrics + mind; display/mic when available).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# WSL: if run from Windows path with spaces, prefer known mount
if [ ! -f "$ROOT/src/main_mind.zig" ] && [ -f "/mnt/i/fsot nuron/embodiment/zig/src/main_mind.zig" ]; then
  ROOT="/mnt/i/fsot nuron/embodiment/zig"
fi
cd "$ROOT"
export PATH="/usr/local/bin:${PATH}"
OUT="${TMPDIR:-/tmp}/fsot_mind_boot"
CACHE="${TMPDIR:-/tmp}/fsot_zig_cache_boot"
echo "=== build fsot_mind (linux) ==="
zig build-exe -OReleaseFast -femit-bin="$OUT" --cache-dir "$CACHE" --name fsot_mind_boot src/main_mind.zig
echo "=== fixed ==="
"$OUT" fixed
echo "=== hardware ==="
"$OUT" hardware
echo "=== host-senses ==="
"$OUT" host-senses
echo "=== body ==="
"$OUT" body
echo "FSOT_BODY_BOOT_LINUX_OK"
