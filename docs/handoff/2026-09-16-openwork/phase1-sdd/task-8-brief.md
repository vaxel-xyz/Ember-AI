### Task 8: docker-compose.yml, .env.example, .env.schema.json, compose test

**Files:**
- Create: `docker-compose.yml`, `.env.example`, `tests/test-compose.sh`
- Modify: `.env.schema.json` (rewrite)

**Interfaces:**
- Produces env contract consumed by ember-api, LiteLLM renderer, dashboard, `bin/ember`.

- [ ] **Step 1: .env.example**

```dotenv
# ---- Ember-AI (copy to .env; never commit .env) ----
BIND_ADDRESS=0.0.0.0               # Docker01 LAN interface; keep off the internet (Cloudflare tunnel fronts it)
LITELLM_PORT=4000
EMBER_DASHBOARD_PORT=3001
EMBER_API_PORT=3002
QDRANT_PORT=6333

# Public / internal identities
LLM_PUBLIC_URL=https://llm.vaxel.xyz/v1
LLM_INTERNAL_URL=http://172.20.142.7:4000/v1
EMBER_PUBLIC_URL=https://ember.vaxel.xyz
OMLX_PUBLIC_URL=https://omlx.vaxel.xyz

# oMLX on jons-mac-mini (LAN)
OMLX_HOST=172.20.142.184
OMLX_BASE_URL=http://172.20.142.184:8000
OMLX_API_KEY=CHANGE_ME
OMLX_CHAT_MODEL=Ornith-1.5-9B-MLX-4bit
OMLX_FAST_MODEL=Qwen2.5-3B-Instruct-4bit
OMLX_CODE_MODEL=gemma-4-12B-agentic-fable5-composer2.5-v2-nvfp4
OMLX_VISION_MODEL=gemma-4-12B-agentic-fable5-composer2.5-v2-nvfp4
OMLX_EMBED_MODEL=bge-m3-mlx-8bit
OMLX_STT_MODEL=parakeet-tdt-0.6b-v3
OMLX_TTS_MODEL=Kokoro-82M-bf16
# OMLX_RERANK_MODEL=            # set once a SequenceClassification reranker is loaded in oMLX (see docs/adr/0006)

# Cloud
OPENROUTER_API_KEY=CHANGE_ME
OPENROUTER_THINK_MODEL=z-ai/glm-5.3

# Gateway
LITELLM_MASTER_KEY=sk-CHANGE_ME          # generate: openssl rand -hex 24
LITELLM_DB_PASSWORD=CHANGE_ME
LITELLM_TURN_OFF_MESSAGE_LOGGING=true    # prompts/responses are NOT stored in spend logs by default

# Ember control plane
EMBER_API_KEY=CHANGE_ME                  # generate: openssl rand -hex 24
EMBER_POLL_INTERVAL_S=15
```

- [ ] **Step 2: docker-compose.yml**

```yaml
name: ember

x-logging: &logging
  logging: { driver: json-file, options: { max-size: "10m", max-file: "3" } }

services:
  litellm-postgres:
    image: postgres:17-alpine
    container_name: ember-litellm-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: litellm
      POSTGRES_USER: litellm
      POSTGRES_PASSWORD: ${LITELLM_DB_PASSWORD}
    volumes: [litellm-pgdata:/var/lib/postgresql/data]
    healthcheck: { test: ["CMD-SHELL", "pg_isready -U litellm -d litellm"], interval: 10s, timeout: 5s, retries: 10 }
    <<: *logging

  litellm:
    image: ghcr.io/berriai/litellm:v1.81.3-stable
    container_name: ember-litellm
    restart: unless-stopped
    depends_on: { litellm-postgres: { condition: service_healthy } }
    env_file: .env
    environment:
      LITELLM_DATABASE_URL: postgresql://litellm:${LITELLM_DB_PASSWORD}@litellm-postgres:5432/litellm
      DATABASE_URL: postgresql://litellm:${LITELLM_DB_PASSWORD}@litellm-postgres:5432/litellm
    volumes:
      - ./config/litellm/ember.yaml.tmpl:/app/ember.yaml.tmpl:ro
      - ./config/litellm/render-config.py:/app/render-config.py:ro
    ports: ["${BIND_ADDRESS:-127.0.0.1}:${LITELLM_PORT:-4000}:4000"]
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        python3 /app/render-config.py /app/ember.yaml.tmpl /tmp/config.yaml
        exec litellm --config /tmp/config.yaml --port 4000
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4000/health/readiness', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    deploy: { resources: { limits: { memory: 1500M } } }
    <<: *logging

  ember-api:
    build: ./ember-api
    image: ghcr.io/vaxel-xyz/ember-api:local
    container_name: ember-api
    restart: unless-stopped
    env_file: .env
    environment:
      LITELLM_BASE_URL: http://litellm:4000
      EMBER_SERVICES_DIR: /app/services
    volumes: ["./services:/app/services:ro"]
    ports: ["${BIND_ADDRESS:-127.0.0.1}:${EMBER_API_PORT:-3002}:3002"]
    deploy: { resources: { limits: { memory: 256M } } }
    <<: *logging

  ember-dashboard:
    build: ./dashboard
    image: ghcr.io/vaxel-xyz/ember-dashboard:local
    container_name: ember-dashboard
    restart: unless-stopped
    depends_on: [ember-api]
    environment: { EMBER_API_KEY: "${EMBER_API_KEY}" }
    ports: ["${BIND_ADDRESS:-127.0.0.1}:${EMBER_DASHBOARD_PORT:-3001}:3001"]
    deploy: { resources: { limits: { memory: 64M } } }
    <<: *logging

  qdrant:
    image: qdrant/qdrant:v1.16.3
    container_name: ember-qdrant
    profiles: [qdrant]
    restart: unless-stopped
    volumes: [qdrant-data:/qdrant/storage]
    ports: ["${BIND_ADDRESS:-127.0.0.1}:${QDRANT_PORT:-6333}:6333"]
    deploy: { resources: { limits: { memory: 1G } } }
    <<: *logging

volumes:
  litellm-pgdata: {}
  qdrant-data: {}
```

- [ ] **Step 3: .env.schema.json**

Rewrite to list every key from `.env.example` with `type`, `description`, `secret: true` where applicable, `required` = `[OMLX_BASE_URL, OMLX_API_KEY, OMLX_CHAT_MODEL, OMLX_FAST_MODEL, OMLX_CODE_MODEL, OMLX_VISION_MODEL, OMLX_EMBED_MODEL, OMLX_STT_MODEL, OMLX_TTS_MODEL, OPENROUTER_API_KEY, OPENROUTER_THINK_MODEL, LITELLM_MASTER_KEY, LITELLM_DB_PASSWORD, EMBER_API_KEY]`, `additionalProperties: true`.

- [ ] **Step 4: Compose test**

`tests/test-compose.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
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
```

Run: `bash tests/test-compose.sh` → Expected: `compose OK`.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml .env.example .env.schema.json tests/test-compose.sh
git commit -m "feat: Ember compose stack, env contract and compose validation"
```

---

