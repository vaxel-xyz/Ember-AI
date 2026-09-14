#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v docker >/dev/null 2>&1; then echo "SKIP: docker not available"; exit 0; fi
tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT
sed 's/CHANGE_ME/placeholder/g' .env.example > "$tmp"
docker compose --env-file "$tmp" config -q
docker compose --env-file "$tmp" --profile qdrant config | grep -q "ember-qdrant"
python3 - "$tmp" <<'EOF'
import json,sys
schema=json.load(open(".env.schema.json")); keys={l.split("=")[0] for l in open(sys.argv[1]) if "=" in l and not l.startswith("#")}
missing=[k for k in schema["required"] if k not in keys]; assert not missing, f".env.example lacks required {missing}"
EOF
echo "compose OK"
