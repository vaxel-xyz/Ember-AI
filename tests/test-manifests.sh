#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/validate-manifests.py services >/dev/null
# negative case: a manifest with a bad x_ember.node must fail
tmp=$(mktemp -d); mkdir -p "$tmp/bad"
sed 's/node: docker01/node: laptop/' services/litellm/manifest.yaml > "$tmp/bad/manifest.yaml"
if python3 scripts/validate-manifests.py "$tmp" >/dev/null 2>&1; then echo "FAIL: bad node accepted"; exit 1; fi
echo "manifests OK"
