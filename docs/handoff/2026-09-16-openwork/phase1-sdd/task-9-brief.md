### Task 9: `bin/ember` CLI with doctor

**Files:**
- Create: `bin/ember`, `tests/test-doctor.sh`, `tests/run.sh`

**Interfaces:**
- Produces: `ember up|down|restart|status|logs [svc]|doctor|keys create <client> [--budget USD]`. `doctor` exit 0 = all checks pass.

- [ ] **Step 1: Failing doctor test (stub HTTP)**

`tests/test-doctor.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p tests/.tmp
python3 - <<'EOF' &
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = {"status":"healthy","engine_pool":{"loaded_count":1}} if self.path=="/health" else {"status":"connected"}
        if self.path.startswith("/api/health"): body={"status":"ok"}
        self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(json.dumps(body).encode())
    def do_POST(self):
        body = {"data":[{"embedding":[0.1,0.2]}]} if "embeddings" in self.path else {"choices":[{"message":{"content":"pong"}}]}
        self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(json.dumps(body).encode())
    def log_message(self,*a): pass
HTTPServer(("127.0.0.1", 18999), H).serve_forever()
EOF
srv=$!; trap 'kill $srv' EXIT; sleep 1
cat > tests/.tmp/doctor.env <<EOF
OMLX_BASE_URL=http://127.0.0.1:18999
OMLX_API_KEY=x
LITELLM_MASTER_KEY=x
EMBER_API_KEY=x
OMLX_CHAT_MODEL=m
OMLX_EMBED_MODEL=e
EOF
EMBER_ENV_FILE=tests/.tmp/doctor.env EMBER_LITELLM_URL=http://127.0.0.1:18999 EMBER_API_URL=http://127.0.0.1:18999 EMBER_SKIP_COMPOSE=1 bin/ember doctor
echo "doctor OK"
```

Run: `bash tests/test-doctor.sh` → Expected: FAIL (`bin/ember` missing).

- [ ] **Step 2: bin/ember**

```bash
#!/usr/bin/env bash
# Ember-AI operator CLI. Runs from the stack directory (default: /opt/stacks/ember or repo root).
set -euo pipefail
ROOT="${EMBER_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
ENV_FILE="${EMBER_ENV_FILE:-$ROOT/.env}"
COMPOSE=(docker compose --project-directory "$ROOT" --env-file "$ENV_FILE")

usage() { cat <<'EOF'
ember up|down|restart|status|logs [service]|doctor|keys create <client> [--budget USD]
EOF
}

load_env() { [ -f "$ENV_FILE" ] || { echo "missing $ENV_FILE (copy .env.example)"; exit 2; }; set -a; . "$ENV_FILE"; set +a; }

pass() { printf '  \033[32m✓\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m✗\033[0m %s\n' "$1"; FAILED=1; }

doctor() {
  load_env; FAILED=0
  local lite="${EMBER_LITELLM_URL:-http://127.0.0.1:${LITELLM_PORT:-4000}}"
  local api="${EMBER_API_URL:-http://127.0.0.1:${EMBER_API_PORT:-3002}}"
  echo "Ember doctor"
  for v in OMLX_BASE_URL OMLX_API_KEY LITELLM_MASTER_KEY EMBER_API_KEY OMLX_CHAT_MODEL OMLX_EMBED_MODEL; do
    [ -n "${!v:-}" ] && pass "env $v set" || fail "env $v missing"
  done
  if [ -z "${EMBER_SKIP_COMPOSE:-}" ]; then "${COMPOSE[@]}" config -q && pass "compose config renders" || fail "compose config invalid"; fi
  if out=$(curl -sf -m 5 "$OMLX_BASE_URL/health"); then
    loaded=$(printf '%s' "$out" | python3 -c 'import json,sys;print(json.load(sys.stdin)["engine_pool"]["loaded_count"])')
    pass "oMLX reachable (loaded models: $loaded)"
  else fail "oMLX unreachable at $OMLX_BASE_URL"; fi
  curl -sf -m 5 "$lite/health/readiness" >/dev/null && pass "LiteLLM readiness" || fail "LiteLLM readiness at $lite"
  curl -sf -m 5 "$api/api/health" >/dev/null && pass "ember-api health" || fail "ember-api health at $api"
  if out=$(curl -sf -m 300 "$lite/v1/chat/completions" -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H 'Content-Type: application/json' \
      -d '{"model":"ember-auto","messages":[{"role":"user","content":"Reply with the single word: pong"}],"max_tokens":8}'); then
    pass "ember-auto completion: $(printf '%s' "$out" | python3 -c 'import json,sys;print(json.load(sys.stdin)["choices"][0]["message"]["content"].strip()[:40])')"
  else fail "ember-auto completion failed"; fi
  if out=$(curl -sf -m 120 "$lite/v1/embeddings" -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H 'Content-Type: application/json' \
      -d '{"model":"ember-embed","input":"ember doctor"}'); then
    pass "ember-embed vector length $(printf '%s' "$out" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)["data"][0]["embedding"]))')"
  else fail "ember-embed failed"; fi
  [ "$FAILED" = 0 ] && echo "all checks passed" || { echo "some checks failed"; exit 1; }
}

keys_create() {
  load_env
  local client="$1"; shift; local budget=""
  while [ $# -gt 0 ]; do case "$1" in --budget) budget="$2"; shift 2;; *) shift;; esac; done
  local lite="${EMBER_LITELLM_URL:-http://127.0.0.1:${LITELLM_PORT:-4000}}"
  local payload
  payload=$(python3 -c 'import json,sys;c,b=sys.argv[1],sys.argv[2];d={"key_alias":c,"metadata":{"client":c}};b and d.update(max_budget=float(b));print(json.dumps(d))' "$client" "$budget")
  curl -sf "$lite/key/generate" -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H 'Content-Type: application/json' -d "$payload" \
    | python3 -c 'import json,sys;d=json.load(sys.stdin);print("client:",d.get("key_alias"));print("key:",d["key"])'
}

case "${1:-}" in
  up) load_env; "${COMPOSE[@]}" up -d --build ;;
  down) load_env; "${COMPOSE[@]}" down ;;
  restart) load_env; "${COMPOSE[@]}" up -d --build --force-recreate ;;
  status) load_env; "${COMPOSE[@]}" ps ;;
  logs) load_env; shift; "${COMPOSE[@]}" logs -f --tail=200 "$@" ;;
  doctor) doctor ;;
  keys) shift; [ "${1:-}" = create ] && [ -n "${2:-}" ] || { usage; exit 2; }; shift; keys_create "$@" ;;
  *) usage; exit 2 ;;
esac
```

`tests/run.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash tests/test-manifests.sh
bash tests/test-compose.sh
bash tests/test-doctor.sh
(cd ember-api && python3 -m pytest -q)
(cd dashboard && npm test --silent)
echo "ALL OK"
```

- [ ] **Step 3: Run, shellcheck, commit**

Run: `chmod +x bin/ember tests/*.sh && shellcheck -S error bin/ember tests/*.sh && bash tests/test-doctor.sh` → Expected: `doctor OK`.

```bash
git add bin tests
git commit -m "feat: ember CLI with doctor and virtual-key creation"
```

---

