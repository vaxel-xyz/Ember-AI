# Branch 2 plan — Frontend/Routing ADR applied to Ember-AI

**Goal:** Ember publishes the gateway at `ai.vaxel.xyz/v1`, adds human-facing aliases `local-fast`/`local-smart`/`heavy`, represents Open WebUI (separate stack) as a consumer, ships a reference Open WebUI deployment, records ADR 0010, and is re-validated live.
**Branch:** `feature/frontend-routing-adr` from `feature/ember-lean-rebuild` (`b44d98123`). PR #2 = draft against `main`, body says "stacks on #1".
**Spec:** `SPEC.md` (this folder). Rules: `HANDOFF.md`.
**Run tests as:** `source .venv/bin/activate; (cd ember-api && python3 -m pytest -q && ruff check .); (cd dashboard && npm test --silent && npm run lint && npm run build); bash tests/run.sh`.

Each task: implement → tests green → one commit with the given message → push → `gh run watch --exit-status` on the `ci` run → append to `REPORT.md`.

---

## Task 0 — branch + handoff docs
```bash
git fetch -q && git checkout -q feature/ember-lean-rebuild && git pull -q --ff-only
git checkout -b feature/frontend-routing-adr
```
The handoff folder already lives at `docs/handoff/2026-09-16-openwork/` on this branch (committed by Claude). Nothing else to do.

## Task 1 — gateway hostname → `ai.vaxel.xyz/v1`
Files: `.env.example`, `ember-api/ember_api/settings.py`, `docs/cloudflare.md`, `docs/litellm.md`, `docs/architecture.md`, `docs/deployment.md`, `docs/hermes-cutover.md`, `README.md`, `docs/adr/0001-*.md`, `docs/adr/0004-*.md` (if it names the hostname), `ember-api/tests/conftest.py`, `ember-api/tests/test_api.py` (if asserting the URL).
1. `.env.example`: `LLM_PUBLIC_URL=https://ai.vaxel.xyz/v1` (edit via python3 script if `.env*` is tooling-guarded — see HANDOFF rule 9):
   ```bash
   python3 - <<'EOF'
   import re,pathlib; p=pathlib.Path('.env.example'); s=p.read_text()
   s=re.sub(r'^LLM_PUBLIC_URL=.*$','LLM_PUBLIC_URL=https://ai.vaxel.xyz/v1',s,flags=re.M); p.write_text(s)
   EOF
   ```
2. `settings.py`: default `llm_public_url="https://ai.vaxel.xyz/v1"`.
3. `grep -rn "llm\.vaxel\.xyz" --include=*.md --include=*.py --include=*.jsx --include=*.yml --include=*.json . | grep -v node_modules | grep -v docs/handoff` → replace every hit with `ai.vaxel.xyz` except inside `docs/adr/0001-*.md` (history) and `docs/adr/0010-*.md`.
4. `docs/adr/0001-vaxel-service-urls-ownership-network.md`: add directly under the Status line: `**Superseded in part (2026-09-16):** §1 and §3 hostnames are superseded by [ADR 0010](0010-frontend-routing-voice.md) — the LLM gateway is `https://ai.vaxel.xyz/v1` and Open WebUI is the human frontend at `https://chat.vaxel.xyz`. All other sections stand.`
5. `docs/cloudflare.md` ingress:
   ```yaml
   ingress:
     - hostname: ai.vaxel.xyz
       service: http://172.20.142.7:4000
     - hostname: chat.vaxel.xyz
       service: http://172.20.142.7:3003
     - hostname: ember.vaxel.xyz
       service: http://172.20.142.7:3001
   ```
   plus a sentence: `ai.vaxel.xyz` was previously reserved for a separate OpenWork frontend; that plan is dropped (ADR 0010).
6. Tests: `grep -rn "llm.vaxel" ember-api/tests` — update fixtures to the new URL. Run suite.
7. Commit: `feat: gateway public hostname is ai.vaxel.xyz/v1 (ADR 0010)`.

## Task 2 — aliases `local-fast`, `local-smart`, `heavy`; schema `required` fix
Files: `config/litellm/ember.yaml.tmpl`, `ember-api/ember_api/aliases.py`, `ember-api/tests/test_render_litellm.py`, `ember-api/tests/test_api.py`, `.env.schema.json`, `docs/litellm.md`, `README.md`.
1. Template — append after the `ember-think` entry (same indentation as siblings):
   ```yaml
     # Human-facing aliases for Open WebUI's model picker (ADR 0010 §3–4). Same targets as the ember-* aliases above.
     - model_name: local-fast
       litellm_params: {model: "openai/${OMLX_FAST_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
     - model_name: local-smart
       litellm_params: {model: "openai/${OMLX_CHAT_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
     - model_name: heavy
       litellm_params: {model: "openrouter/${OPENROUTER_THINK_MODEL}", api_key: "os.environ/OPENROUTER_API_KEY"}
   ```
2. `aliases.py` — append to `ALIASES`: `("local-fast", "omlx", "OMLX_FAST_MODEL"), ("local-smart", "omlx", "OMLX_CHAT_MODEL"), ("heavy", "openrouter", "OPENROUTER_THINK_MODEL")`. (`ALIAS_NAMES` derives automatically; the gateway probe now expects 13.)
3. Tests: `test_render_litellm.py` alias-order assertion → 13 names in template order; add
   ```python
   def test_human_aliases_share_targets_with_ember_aliases():
       out = yaml.safe_load(render_config.render(TMPL, ENV))
       by = {m["model_name"]: m["litellm_params"] for m in out["model_list"]}
       assert by["local-fast"] == by["ember-fast"]
       assert by["local-smart"] == by["ember-auto"]
       assert by["heavy"] == by["ember-think"]
   ```
   and add `"local-fast", "local-smart", "heavy"` to the "chat routes carry no mode" loop. In `test_api.py` where `/model/info` is mocked for the gateway probe (search `model_info`/`aliases_registered`), extend the mocked list to all 13 names.
4. `.env.schema.json` `required` += `"OMLX_RERANK_MODEL"` (python3 json load/dump, indent 2). Add test in `ember-api/tests/test_config_validate.py`:
   ```python
   def test_schema_required_covers_template_identifiers():
       import json; from string import Template
       req = set(json.loads((ROOT / ".env.schema.json").read_text())["required"])
       ids = Template((ROOT / "config/litellm/ember.yaml.tmpl").read_text()).get_identifiers()
       assert set(ids) <= req
   ```
   (`ROOT` = repo root; reuse the existing conftest constant if present.)
5. Docs: alias table in `docs/litellm.md` and `README.md` gains the three rows with "same target as …".
6. Commit: `feat: add local-fast/local-smart/heavy aliases; require OMLX_RERANK_MODEL in schema`.

## Task 3 — Open WebUI as an external consumer in Ember
Files: `services/schema/service-manifest.v1.json`, `services/open-webui/manifest.yaml`, `.env.example`, `.env.schema.json`, `ember-api/ember_api/routers/services.py`, `ember-api/tests/test_manifests.py`, `ember-api/tests/test_api.py`, `dashboard/src/pages/Overview.jsx`, `dashboard/src/pages/Overview.test.jsx`.
1. Schema: `x_ember.role` enum += `"consumer"`.
2. `services/open-webui/manifest.yaml`:
   ```yaml
   schema_version: ods.services.v1
   service:
     id: open-webui
     name: Open WebUI (chat)
     host_env: OPENWEBUI_HOST
     default_host: 172.20.142.7
     port: 3003
     health: /health
     health_timeout: 5
     ui_path: /
     public_url_env: CHAT_PUBLIC_URL
     type: external
     category: optional
     x_ember:
       node: docker01
       role: consumer
       managed: false
       health_probe: http
   ```
3. `.env.example` (python3 edit) — new block:
   ```
   # Open WebUI — separate stack /opt/stacks/openwebui (see deploy/openwebui/). Ember only monitors it.
   OPENWEBUI_HOST=172.20.142.7
   CHAT_PUBLIC_URL=https://chat.vaxel.xyz
   ```
   Schema: add both properties (string, not secret, not required).
4. `routers/services.py` `/api/nodes`: keep node grouping but exclude `role == "consumer"` services from `docker01`'s list and add a third group `{"id": "consumers", "role": "consumers", "services": [ids with role consumer]}`.
5. Dashboard `Overview.jsx`: `NODES` += `{ id: 'consumers', title: 'Consumers' }`; filter: control-plane = `s.node === 'docker01' && s.role !== 'consumer'`; consumers = `s.role === 'consumer'`. Test: add an `open-webui` service (`node: 'docker01', role: 'consumer', state: 'unreachable'`) to the mock and assert it renders under `Consumers` and not under the control-plane heading.
6. Tests: `test_manifests.py` expects 7 services incl. `open-webui` with `role == "consumer"`; `test_api.py` nodes test asserts the `consumers` group contains `open-webui`. `bash tests/test-manifests.sh` passes.
7. Commit: `feat: represent Open WebUI as an external consumer tile`.

## Task 4 — reference Open WebUI stack + docs + doctor
Files: `deploy/openwebui/compose.yml`, `deploy/openwebui/.env.example` (python3 write), `deploy/openwebui/README.md`, `docs/open-webui.md`, `bin/ember`, `tests/test-doctor.sh`.
1. `deploy/openwebui/compose.yml`:
   ```yaml
   name: openwebui
   services:
     open-webui:
       image: ghcr.io/open-webui/open-webui:v0.11.3
       container_name: open-webui
       restart: unless-stopped
       env_file: .env
       environment:
         ENABLE_OLLAMA_API: "false"
         ENABLE_OPENAI_API: "true"
         OPENAI_API_BASE_URL: ${LITELLM_BASE_URL:-http://172.20.142.7:4000/v1}
         OPENAI_API_KEY: ${LITELLM_VIRTUAL_KEY:?LITELLM_VIRTUAL_KEY must be a LiteLLM virtual key (bin/ember keys create open-webui)}
         WEBUI_AUTH: "true"
         ENABLE_SIGNUP: ${ENABLE_SIGNUP:-true}
         WEBUI_URL: ${WEBUI_URL:-https://chat.vaxel.xyz}
         WEBUI_SECRET_KEY: ${WEBUI_SECRET_KEY:?set WEBUI_SECRET_KEY (openssl rand -hex 32)}
         DEFAULT_MODELS: local-smart
         ENABLE_VERSION_UPDATE_CHECK: "false"
       ports: ["${BIND_ADDRESS:-0.0.0.0}:${OPENWEBUI_PORT:-3003}:8080"]
       volumes: [open-webui-data:/app/backend/data]
       healthcheck:
         test: ["CMD", "curl", "-fsS", "http://127.0.0.1:8080/health"]
         interval: 30s
         timeout: 10s
         retries: 5
         start_period: 60s
       deploy: { resources: { limits: { memory: 1536M } } }
       logging: { driver: json-file, options: { max-size: "10m", max-file: "3" } }
   volumes:
     open-webui-data: {}
   ```
   (If the image lacks `curl`, switch the healthcheck to `python3 -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=5)"` and note it.)
2. `deploy/openwebui/.env.example`:
   ```
   BIND_ADDRESS=0.0.0.0
   OPENWEBUI_PORT=3003
   LITELLM_BASE_URL=http://172.20.142.7:4000/v1
   LITELLM_VIRTUAL_KEY=CHANGE_ME      # bin/ember keys create open-webui --budget 20
   WEBUI_SECRET_KEY=CHANGE_ME         # openssl rand -hex 32
   WEBUI_URL=https://chat.vaxel.xyz
   ENABLE_SIGNUP=true                 # set false after the first admin account exists
   ```
3. `deploy/openwebui/README.md`: how to deploy on Docker01 (`git clone`-free: `scp -r deploy/openwebui vaxel-docker:/opt/stacks/openwebui` or copy from the Ember checkout at `/opt/stacks/ember/deploy/openwebui`), fill `.env`, `docker compose up -d`, first-admin flow, then `ENABLE_SIGNUP=false` + `docker compose up -d`. State that Open WebUI never receives provider keys (ADR 0010 §13).
4. `docs/open-webui.md`: role (ADR 0010 §1), where it runs, the consumer tile, model picker names, PWA install steps, backup = the `open-webui-data` volume.
5. `bin/ember doctor`: after the `ember-auto` check add an identical block for `local-smart` (pass text `local-smart completion: …`). Update `tests/test-doctor.sh` stub if it matches on model names (it does not — the stub answers any chat POST).
6. Commit: `feat: reference Open WebUI stack, docs, and local-smart doctor check`.

## Task 5 — ADR 0010 + roadmap + spec/doc alignment
Files: `docs/adr/0010-frontend-routing-voice.md`, `README.md`, `docs/architecture.md`, `docs/roadmap.md` (new), `DOWNSTREAM.md` (no change unless it names OpenWork).
1. Copy `docs/handoff/2026-09-16-openwork/adr-0010-source.md` → `docs/adr/0010-frontend-routing-voice.md` verbatim.
2. README four-way table: "Human-facing UI" owner = **Open WebUI** (`chat.vaxel.xyz`); remove OpenWork; MCP row: "MCP is configured in Open WebUI / Hermes, never in ember-api".
3. `docs/architecture.md`: same ownership update; consumer tile mention; link ADR 0010.
4. `docs/roadmap.md`: ADR 0010 phases 5–7 (MCP reconnect, OpenAI Realtime voice, local voice) + `auto` alias, each one paragraph, status "not started", owner Jon.
5. `grep -rn "OpenWork" --include=*.md . | grep -v handoff | grep -v adr/0001` must return nothing.
6. Commit: `docs: ADR 0010 frontend/routing/voice; roadmap; ownership updates`.

## Task 6 — live: gateway hostname env, Open WebUI stack, validation, PR
All remote work via `ssh vaxel-docker`. Never print secrets.
1. Ember `.env` on Docker01: `sed -i 's|^LLM_PUBLIC_URL=.*|LLM_PUBLIC_URL=https://ai.vaxel.xyz/v1|' /opt/stacks/ember/.env`; append `OPENWEBUI_HOST=172.20.142.7` and `CHAT_PUBLIC_URL=https://chat.vaxel.xyz` if absent; `OMLX_RERANK_MODEL` already present.
2. `cd /opt/stacks/ember && git fetch && git checkout feature/frontend-routing-adr && git pull --ff-only && bin/ember restart` (recreates litellm so the new aliases load). `bin/ember doctor` → green incl. `local-smart`. `curl -s -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://127.0.0.1:4000/model/info | python3 -c 'import json,sys;print(sorted(m["model_name"] for m in json.load(sys.stdin)["data"]))'` → 13 names.
3. Virtual key: `bin/ember keys create open-webui --budget 20` → capture the `key:` line into a shell variable only (`k=$(… | awk '/^key:/{print $2}')`), never echo it.
4. Open WebUI stack: `mkdir -p /opt/stacks/openwebui && cp /opt/stacks/ember/deploy/openwebui/compose.yml /opt/stacks/openwebui/ && cp /opt/stacks/ember/deploy/openwebui/.env.example /opt/stacks/openwebui/.env`; `sed -i` the virtual key and `WEBUI_SECRET_KEY=$(openssl rand -hex 32)` into `.env`; `chmod 600 .env`; `docker compose up -d`; wait for healthy (`docker ps`), `curl -s http://127.0.0.1:3003/health` → 200. Confirm `curl -s http://127.0.0.1:3001/api/services` shows `open-webui: healthy` under the consumers group and `litellm: healthy` with 13 aliases.
5. Chat round-trip through Open WebUI's API is only possible after the first admin exists (Jon). Instead prove the model list Open WebUI will see: `curl -s -H "Authorization: Bearer <virtual key via variable>" http://127.0.0.1:4000/v1/models | python3 -c 'import json,sys;print(sorted(m["id"] for m in json.load(sys.stdin)["data"]))'` — must include `local-fast`, `local-smart`, `heavy`; and one completion via `local-smart` with the virtual key. Leave `ENABLE_SIGNUP=true` for Jon.
6. Memory on Docker01: `free -m` and `docker stats --no-stream` — record.
7. Append to `docs/deployment.md`: "Branch 2 receipt (date)" table — hostname env, 13 aliases, Open WebUI container health, virtual key created (name only), model list seen by the virtual key, completion result, memory. Commit `docs: branch 2 validation receipt`; push; CI green.
8. `gh pr create --draft --base main --head feature/frontend-routing-adr --title "Ember-AI: frontend/routing ADR — ai.vaxel.xyz gateway, human aliases, Open WebUI consumer" --body-file docs/handoff/2026-09-16-openwork/REPORT.md` (put a "Stacks on #1" line at the top of the report first). Do not merge.

## Acceptance for the night
- All Task 1–6 commits pushed; `ci` + `secret-scan` green on the final head.
- Local suite green; ember-api ≥ 56 tests; dashboard tests green.
- Docker01: `bin/ember doctor` green; `/model/info` lists 13 aliases; `open-webui` container healthy; Ember dashboard shows the Open WebUI consumer tile healthy.
- No secret values anywhere in git, `REPORT.md`, or logs you leave behind.
- `REPORT.md` complete; draft PR #2 URL recorded.
