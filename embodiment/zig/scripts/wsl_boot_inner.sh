#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:${PATH:-}"
ROOT="/mnt/i/fsot nuron/embodiment/zig"
cd "$ROOT"
echo "=== zig $(zig version) ==="
echo "=== build linux ==="
zig build-exe -OReleaseFast -femit-bin=/tmp/fsot_mind_boot --cache-dir /tmp/zcb --name fsot_mind_boot src/main_mind.zig
echo "=== fixed ==="
/tmp/fsot_mind_boot fixed | sed -n '1,5p;/PASS/p;/FAIL/p;/STACK_OK/p'
echo "=== hardware ==="
/tmp/fsot_mind_boot hardware
echo "=== host-senses ==="
/tmp/fsot_mind_boot host-senses
echo "=== body (daemon) ==="
/tmp/fsot_mind_boot body
echo "FSOT_BODY_BOOT_LINUX_OK"
