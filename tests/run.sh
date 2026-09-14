#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash tests/test-manifests.sh
bash tests/test-compose.sh
bash tests/test-doctor.sh
(cd ember-api && python3 -m pytest -q)
(cd dashboard && npm test --silent)
echo "ALL OK"
