# STATE — verified 2026-09-16 22:10 BST

## Repo `/Users/jtotham/Projects/Ember-AI` (origin vaxel-xyz/Ember-AI, PUBLIC; upstream Osmantic/ODS)
- `main` = `21f4b3a64` (pristine ODS v2.6.0).
- `feature/ember-lean-rebuild` = `b44d98123`, 31 commits, pushed, CI + secret-scan green, PR #1 open (do not merge).
- Working tree clean. `.superpowers/` (git-ignored) holds the Phase 1 SDD ledger and review packages.
- Layout: `docker-compose.yml`, `.env.example`, `.env.schema.json`, `config/litellm/{ember.yaml.tmpl,render-config.py}`, `services/<id>/manifest.yaml` (litellm, litellm-postgres, ember-api, ember-dashboard, omlx, qdrant) + `services/schema/service-manifest.v1.json`, `scripts/validate-manifests.py`, `ember-api/` (FastAPI; `ember_api/{aliases,health,main,manifests,omlx,litellm_client,security,settings}.py`, `routers/{services,models,providers,config}.py`; 52 tests), `dashboard/` (React/Vite/Tailwind; pages Overview/Models/Providers/Settings; 4 tests), `bin/ember`, `tests/{run,test-manifests,test-compose,test-doctor}.sh`, `docs/*.md`, `docs/adr/0001–0009`, `DOWNSTREAM.md`, `NOTICE`.
- Aliases (LiteLLM `model_name`s, in order): `ember-auto, ember-local, ember-fast, ember-code, ember-vision, ember-embed, ember-rerank, ember-stt, ember-tts, ember-think`. Source of truth `ember-api/ember_api/aliases.py` + `config/litellm/ember.yaml.tmpl`.
- Health states: `healthy, degraded, starting, reachable-unhealthy, unreachable`. Gateway probe = readiness + `/model/info` alias-set check (never `/health`).
- Manifest `x_ember.role` enum today: `gateway, control, inference, storage, observability`; `node` enum: `docker01, jons-mac-mini`.
- Public names today (to change in branch 2): `LLM_PUBLIC_URL=https://llm.vaxel.xyz/v1`, `EMBER_PUBLIC_URL=https://ember.vaxel.xyz`, `OMLX_PUBLIC_URL=https://omlx.vaxel.xyz`.

## Docker01 (`root@172.20.142.7`, Debian 13, 4 vCPU, 7.8 GiB RAM, Docker 29.8, Compose v5.5)
- Stacks: `/opt/stacks/n8n`, `/opt/stacks/portainer` (DO NOT TOUCH), `/opt/stacks/ember` (git clone of the branch, at `b44d98123`, `.env` populated with real secrets except `OPENROUTER_API_KEY=CHANGE_ME`).
- Ember containers healthy: `ember-litellm` (:4000), `ember-api` (:3002), `ember-dashboard` (:3001), `ember-litellm-postgres`. Host ports in use: 3000 (n8n-mcp), 3001, 3002, 4000, 5678, 9443. **3003 is free** (planned for Open WebUI).
- `bin/ember doctor` green (chat via `ember-auto`, embed via `ember-embed`, STT/TTS/rerank validated through LiteLLM). `bin/ember up` does NOT recreate `litellm` on template-only changes — use `bin/ember restart` or `docker compose restart litellm`.
- nginx in front of the dashboard is GET-only for `/api/`; the deep gateway check is `POST http://127.0.0.1:3002/api/services/refresh?deep=true` with the ember-api bearer (operator only).

## Mac mini (`jtotham@172.20.142.184`, macOS 26.6, 16 GB, shared desktop)
- oMLX 0.6.4, DMG app + CLI `~/.omlx/bin/omlx`, bound `*:8000`, bearer key in `~/.omlx/settings.json` → `.auth.api_key` (never print). Models registered: `Ornith-1.5-9B-MLX-4bit` (default chat), `Qwen2.5-3B-Instruct-4bit`, `gemma-4-12B-agentic-fable5-composer2.5-v2-nvfp4`, `bge-m3-mlx-8bit`, `bge-reranker-v2-m3`, `parakeet-tdt-0.6b-v3`, `Kokoro-82M-bf16`, `Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16`, `MarkItDown`. Model ids = folder names; rescanned only on restart.
- Hermes: launchd `ai.hermes.gateway` (:8642) — primary OpenRouter, fallback local oMLX. Untouched; cutover to Ember is a later phase (`docs/hermes-cutover.md`).
- An orphaned `omlx-server` (PID 66607, PPID 1) currently serves :8000; `omlx stop` is a no-op against it. Leave it.

## Cloudflare
- Tunnel on the Proxmox host routes 172.20.142.0/24. No `ai.`/`chat.`/`ember.`/`llm.` hostnames exist yet (Jon's task). LAN URLs work: gateway `http://172.20.142.7:4000/v1`, dashboard `http://172.20.142.7:3001`.

## Known open items carried from Phase 1 (not yours unless PLAN.md says)
- `.env.schema.json` `required` lacks `OMLX_RERANK_MODEL` (load-bearing) — PLAN Task 2 fixes it.
- `ember-think` unvalidated (no OpenRouter key).
- Inherited LiveKit credential in dead upstream history, annotated in `.gitleaks.toml`/`DOWNSTREAM.md` — Jon's decision, leave.
- Mini-off drill not re-run after the final fix wave (orphan omlx-server) — leave.
