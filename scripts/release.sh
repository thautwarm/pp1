#!/usr/bin/env bash
# Build the standalone setup binaries:
#
#   deno task release            # -> dist/pp1-setup-{os}-{arch}[.exe]
#
# Deno cross-compiles by downloading the target runtime, so this works from any
# host. Requires: deno, network.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/dist"
mkdir -p "$OUT"

targets=(
  "x86_64-unknown-linux-gnu:linux-x64"
  "aarch64-unknown-linux-gnu:linux-arm64"
  "x86_64-apple-darwin:darwin-x64"
  "aarch64-apple-darwin:darwin-arm64"
  "x86_64-pc-windows-msvc:windows-x64"
)

for entry in "${targets[@]}"; do
  target="${entry%%:*}"
  name="${entry##*:}"
  out="$OUT/pp1-setup-$name"
  [ "$name" = "windows-x64" ] && out="$out.exe"
  echo "== $name ($target)"
  deno compile --allow-all --target "$target" --output "$out" "$ROOT/scripts/onboard.ts"
done

ls -lh "$OUT"
