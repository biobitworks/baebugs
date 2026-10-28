#!/usr/bin/env bash
set -euo pipefail
# Isolate derived bytes outside the repository; copy only after success.
if [ -z "$VERCEL_GIT_COMMIT_SHA" ]; then
  echo "Missing source SHA" >&2
  exit 4
fi
if [[ ! "$VERCEL_GIT_COMMIT_SHA" =~ ^[a-f0-9]{40}$ ]]; then
  echo "Refusing unpinned source SHA" >&2
  exit 4
fi
command -v uv >/dev/null || { echo "uv required" >&2; exit 5; }
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
uv run --no-project --with pillow==13.0.0 python3 site/mvp/build_public_site.py \
  --out "$tmpdir/site" --ref "$VERCEL_GIT_COMMIT_SHA"
target="public"
if printenv BAEBUGS_VERCEL_OUTPUT_DIR >/dev/null 2>&1; then target="$(printenv BAEBUGS_VERCEL_OUTPUT_DIR)"; fi
if [ "$target" = "." ] || [ "$target" = "/" ] || [ -z "$target" ]; then exit 6; fi
rm -rf "$target"
cp -R "$tmpdir/site" "$target"
echo "Static source bundle prepared: $target"
