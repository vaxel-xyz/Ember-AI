# Ember-AI — Design Spec

**Date:** 2026-09-14
**Repo:** `vaxel-xyz/Ember-AI` (fork of `Osmantic/ODS`, upstream at `v2.6.0` / `21f4b3a64`)
**Status:** Approved in chat 2026-09-14 (sections 1–8, dashboard approach A, STT via oMLX). Amended same day for Jon's "Vaxel Service URLs, Ownership and Network Architecture" ADR: gateway = `llm.vaxel.xyz/v1`, dashboard = `ember.vaxel.xyz`, `ai.vaxel.xyz` = OpenWork (not Ember), aliases `ember-*`, TTS model under evaluation (not hard-coded Kokoro).

### Canonical public namespace (from ADR)

| URL | Service | Ember-owned? |
|---|---|---|
| `https://ai.vaxel.xyz` | OpenWork / Vaxel human UI → Hermes | no — **never** a raw inference endpoint |
| `https://ember.vaxel.xyz` | Ember-AI admin dashboard | yes |
| `https://llm.vaxel.xyz/v1` | LiteLLM OpenAI-compatible gateway | yes |
| `https://omlx.vaxel.xyz` | oMLX direct admin/API | no (existing) |
| `https://hermes-dashboard.vaxel.xyz` | Hermes | no (existing) |
| `https://n8n.vaxel.xyz`, `n8n-mcp.vaxel.xyz`, `portainer.vaxel.xyz` | existing | no |

### Logical model aliases (from ADR)

`ember-auto`, `ember-fast`, `ember-think`, `ember-code`, `ember-local` — plus capability aliases Ember needs for non-chat routes: `ember-embed`, `ember-rerank`, `ember-stt`, `ember-tts`, `ember-vision`. Alias → backend mapping is `.env`-driven; clients never couple to a concrete model. Any `vaxel/*` alias in this document is superseded by the `ember-*` name of the same role.
**Personal project (Vaxel homelab). Not Pax8 work.**

---

## 1. Purpose

Ember-AI is Vaxel's **shared AI infrastructure layer**. It provides model routing, local and cloud inference access, speech-to-text, text-to-speech, model/provider management, observability and an administrative dashboard. It is consumed over standards-compatible (OpenAI-shaped) APIs by independent applications.

Ember-AI is **not**: a chat UI, an agent, a RAG application, an MCP host, a workflow engine or a home-automation integration.

### 1.1 Vaxel four-way split

| Role | Owner | Ember's relationship |
|---|---|---|
| Human-facing UI | OpenWork | consumer of Ember APIs |
| Reasoning, memory, skills, tools, MCP, HA, scheduling, RAG logic | Hermes Agent (existing, on `jons-mac-mini`) | required first-class consumer |
| Interactive software engineering | OpenCode (launched locally by Jon per repo) | optional consumer, never deployed by Ember |
| Model routing, inference access, STT, TTS, provider mgmt, observability, admin | **Ember-AI** | this spec |

### 1.2 Upstream posture

ODS is a **donor/reference implementation**, not an architecture to preserve. Lean rebuild inside the fork: keep git history and the `upstream` remote for cherry-picks; aggressively delete everything that does not serve Ember. Prefer deletion and plain replacement over compatibility shims.

---

## 2. Environment (fixed facts)

- **Prox01** (Proxmox). Existing **Docker VM** runs n8n (Postgres+Redis+workers, `n8n.vaxel.xyz`), Portainer (`portainer.vaxel.xyz`). Ember control plane deploys here as another Compose stack. Home Assistant is a separate VM. Neither is touched.
- **jons-mac-mini** (Apple M4, 16 GB). Runs **oMLX 0.6.4** (`omlx.vaxel.xyz`, default port 8000, bearer-key auth on `/v1/*`, `/health` public) and **Hermes Agent** (`hermes-dashboard.vaxel.xyz`) under launchd, with its own `cloudflared`. **No Docker on the mini.**
- Prox01 → mini traffic over **LAN hostname/IP**, not via Cloudflare, not Tailscale.
- Cloud provider: **OpenRouter**, model `z-ai/glm-5.3` (verified slug, 1.3M ctx).
- Jon's workstation is a MacBook Pro (M4 Pro, 24 GB), not the mini. SSH to both hosts available once keys are provisioned.
- oMLX live `/health` today: 4 models known, 1 loaded (`Ornith-1.5-9B-MLX-4bit`, ~5.3 GB), engine ceiling ~11.1 GB.

### 2.1 Verified on-host facts (SSH, 2026-09-14, read-only)

**jons-mac-mini** (`jtotham@172.20.142.184`, macOS 26.6.2, Mac16,10, 16 GB):
- oMLX runs as the **DMG menu-bar app** (launchd label `application.app.omlx.*`), settings at `~/.omlx/settings.json`, models in `~/.omlx/models`. Bound `127.0.0.1:8000` until P1; now `*:8000`. `server_aliases` already lists `172.20.142.184`. API key enforced.
- Models on disk: `srv-sngh/gemma-4-12B-agentic-fable5-composer2.5-v2-nvfp4` (6.8 G), `ornith-ai/Ornith-1.5-9B-MLX-4bit` (4.7 G, default), `mlx-community/Qwen2.5-3B-Instruct-4bit`, `mlx-community/parakeet-tdt-0.6b-v3` (STT). TTS (`Kokoro-82M-bf16`, `Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16`), embedding (`bge-m3-mlx-8bit`) and rerank candidate (`BAAI/bge-reranker-v2-m3`, unverified) added 2026-09-14.
- Hermes: launchd `ai.hermes.gateway` (LAN `:8642`) + `ai.hermes.dashboard` (`127.0.0.1:9119`), config `~/.hermes/config.yaml`. Primary provider **OpenRouter**; fallback provider `local-omlx` → `http://127.0.0.1:8000/v1`, model Ornith.
- cloudflared runs locally (system daemon) publishing `omlx.vaxel.xyz`, `hermes-dashboard.vaxel.xyz`.

**Docker01** (`root@172.20.142.7`, Debian 13, kernel 6.12, 4 vCPU, **3.8 GiB RAM**, 4 G swap, 63 G free disk, Docker 29.8.0, Compose v5.5.1):
- Stacks convention: `/opt/stacks/<name>/compose.yml` (n8n, portainer). Ember deploys to `/opt/stacks/ember/`.
- Running: n8n 2.38.5 (+worker, runners, Postgres 18, Redis), n8n-mcp on host `:3000`, Portainer `:9443`. Host ports 3001, 3002, 4000, 6333 free.
- No cloudflared here. **Cloudflare tunnel runs on the Proxmox host** and routes the `172.20.142.0/24` range; `llm.vaxel.xyz` becomes a public-hostname rule there → `http://172.20.142.7:4000`; `ember.vaxel.xyz` → `:3001`.

### 2.2 Prerequisites arising (need Jon's action / approval)

| # | Item | Why | Phase |
|---|---|---|---|
| P1 | ~~oMLX `server.host` → `0.0.0.0`~~ **DONE 2026-09-14 11:58** via SSH (`omlx restart`); Docker01 gets `/health` 200, unauth `/v1/models` 401; backup `settings.json.bak-ember-20260914` | Docker01 must reach oMLX | done |
| P2 | ~~Download one embedding model~~ **DONE** — `mlx-community/bge-m3-mlx-8bit` on the mini, registered in oMLX, probed: 1024 dims, 0.05 s first call, 0.07 s for 8 texts | `ember-embed` acceptance criterion | done |
| P3 | ~~Download the TTS model~~ **DONE** — `Kokoro-82M-bf16` chosen by blind A/B and registered in oMLX (Qwen3-TTS 0.6B also on disk, unloaded) | `ember-tts` | done |
| P4 | ~~Raise Docker01 VM RAM to ≥ 8 GB~~ **DONE — rebooted 2026-09-14, 7.8 GiB total, 6.5 GiB available** | Langfuse stack (ClickHouse) will not fit in 3.8 GiB alongside n8n; Phase 1 stack (~1–1.5 GB) fits today | before Phase 3 |
| P5 | Cloudflare: add `llm.vaxel.xyz → http://172.20.142.7:4000` on the Proxmox tunnel | public gateway endpoint | Phase 1 (LAN URL works without it) |

---

## 3. Architecture

```text
 consumers: Hermes | OpenCode | n8n | Home Assistant | voice satellites | OpenWork
        │   OpenAI-compatible HTTP, one LiteLLM virtual key per consumer
        ▼
 https://llm.vaxel.xyz/v1   (Cloudflare tunnel on Proxmox host → 172.20.142.7:4000; LAN clients use http://172.20.142.7:4000)
        ▼
 ┌──────────────────────── PROX01 · DOCKER VM · CONTROL PLANE ────────────────────────┐
 │  litellm (gateway, virtual keys, spend logs, Postgres)                              │
 │  ember-api (thin FastAPI: health, models, providers, usage, config validation)      │
 │  ember-dashboard (React, served static)                                             │
 │  [profile: observability] langfuse + worker + postgres + clickhouse + redis + minio │
 │  [profile: qdrant] qdrant  — infra only, no Ember RAG logic                         │
 │  [profile: comfyui] — placeholder manifest only, not built in MVP                   │
 └───────────────────────────────┬────────────────────────────────────────────────────┘
                                 │ LAN, bearer OMLX_API_KEY
                                 ▼
 ┌──────────────────── JONS-MAC-MINI · INFERENCE NODE (external, unmanaged) ──────────┐
 │  oMLX :8000   /v1/chat/completions  /v1/embeddings  /v1/rerank  vision             │
 │               /v1/audio/transcriptions (Parakeet v3)  /v1/audio/speech (TTS model) │
 │               /health  /v1/models  /v1/models/status                               │
 │  Hermes (consumer; cut over to ai.vaxel.xyz/v1 only after Phase 1 validated)       │
 └────────────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼  (cloud)
                     OpenRouter  z-ai/glm-5.3
```

**Governing principle:** Prox01 owns durable state, routing and control. The mini owns accelerated execution. If the mini is off, LiteLLM, ember-api, dashboard, Langfuse and Qdrant stay up; oMLX-backed aliases report unavailable, not the platform.

---

## 4. Components

### 4.1 LiteLLM gateway (`litellm`)

- Image `ghcr.io/berriai/litellm:v1.81.3-stable` (donor pin; bump allowed in plan).
- Backed by its own Postgres (`litellm-postgres`) for virtual keys + spend logs. This is the **generic client telemetry source**: each consumer gets a virtual key with `metadata.client=<name>`; dashboard "Clients" derives from `/spend/logs` and `/key/info`. No bespoke per-consumer integrations.
- Single config `config/litellm/ember.yaml` (no ODS mode files, no switchboard, no model-router):

```yaml
model_list:
  - model_name: ember-auto
    litellm_params: {model: "openai/${OMLX_CHAT_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
  - model_name: ember-vision
    litellm_params: {model: "openai/${OMLX_VISION_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
  - model_name: ember-embed
    litellm_params: {model: "openai/${OMLX_EMBED_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
  - model_name: ember-rerank
    litellm_params: {model: "openai/${OMLX_RERANK_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
  - model_name: ember-stt
    litellm_params: {model: "openai/${OMLX_STT_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
  - model_name: ember-tts
    litellm_params: {model: "openai/${OMLX_TTS_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
  - model_name: ember-think
    litellm_params: {model: "openrouter/z-ai/glm-5.3", api_key: "os.environ/OPENROUTER_API_KEY"}
  - model_name: ember-local        # pinned local model (Ornith / gemma-4-12B per .env)
    litellm_params: {model: "openai/${OMLX_CHAT_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
router_settings:
  num_retries: 1
  # fallbacks: [{"ember-auto": ["ember-think"]}]   # opt-in via EMBER_CLOUD_FALLBACK=true
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/LITELLM_DATABASE_URL
litellm_settings:
  drop_params: true
  request_timeout: 300
  # success_callback: ["langfuse"]   # appended by entrypoint when LANGFUSE_ENABLED=true
  # turn_off_message_logging: true   # when EMBER_LOG_PROMPTS=false (default false = prompts NOT logged)
```

- `LLM_INTERNAL_URL` (`http://172.20.142.7:4000/v1`, LAN) and `LLM_PUBLIC_URL` (`https://llm.vaxel.xyz/v1`) are both surfaced by ember-api/dashboard; LAN consumers such as Hermes use the internal one (ADR §9, no Cloudflare hairpin).
- Exact alias → model mapping stays configurable via `.env`; model IDs are whatever oMLX `/v1/models` reports (never invented).
- **Verified 2026-09-14:** oMLX 0.6.4 serves `/v1/rerank` with raw `BAAI/bge-reranker-v2-m3` weights (id `bge-reranker-v2-m3`): correct ranking, 2.4 s cold / 0.04 s warm, **2.38 GB resident (fp32)** — heavy for the shared mini, so rely on LRU eviction and consider an 8-bit MLX conversion later.
- `/v1/rerank` on oMLX is Cohere/Jina-shaped. LiteLLM's rerank route supports `openai`-style rerank passthrough only partially; the plan must verify whether `ember-rerank` can route through LiteLLM or whether ember-api exposes `/v1/rerank` as a thin authenticated proxy to oMLX. Either is acceptable; document the result in ADR 0006.
- LiteLLM audio (`/v1/audio/transcriptions`, `/v1/audio/speech`) passes through to an OpenAI-compatible `api_base`; no Ember translation layer (per STT ADR).

### 4.2 ember-api (new, thin FastAPI)

Replaces ODS `dashboard-api` (20.8k lines) and `ods-host-agent.py` (12.8k). Target ≤ 2k lines. No Docker socket, no host agent, no GPU detection, no GGUF directory, no magic-link auth.

Auth: single `EMBER_API_KEY` bearer (dashboard passes it; dashboard itself is LAN/Cloudflare-Access protected — Ember does not implement user auth).

Endpoints:

| Route | Source | Purpose |
|---|---|---|
| `GET /api/health` | self | liveness |
| `GET /api/services` | manifests + HTTP probes (cached poll loop, 15 s) | per-service state machine (§4.4) |
| `GET /api/nodes` | manifests | control-plane vs inference-node grouping, host, managed flag |
| `GET /api/models` | oMLX `/v1/models/status` + LiteLLM `/model/info` | alias → provider → model → loaded/unloaded/memory |
| `GET /api/capabilities` | derived | llm / vision / embed / rerank / stt / tts availability per node (STT shows "Parakeet v3 · oMLX", not a fake service) |
| `GET /api/usage?window=` | LiteLLM `/spend/logs`, `/key/info` | requests, tokens, latency, errors, per alias and per client key |
| `GET /api/providers` | config + env presence | oMLX, OpenRouter (+ future) configured/reachable, no secrets echoed |
| `GET /api/config/validate` | config | same checks as `ember doctor` |
| `POST /api/models/{id}/load|unload` | oMLX admin/`/v1/models/{id}/load|unload` | **Phase 3, optional**; requires `EMBER_ALLOW_MODEL_CONTROL=true` |

### 4.3 Service manifests

Keep ODS `ods.services.v1` schema shape (readable, tested) but registry is a **static directory**: `services/<id>/manifest.yaml`. Add namespaced Ember fields (per upstream v2 guidance):

```yaml
service:
  id: omlx
  name: oMLX
  host_env: OMLX_HOST            # LAN hostname/IP of jons-mac-mini
  port: 8000
  health: /health
  type: external                 # new value: not compose-managed, HTTP-only probing
  x_ember:
    node: jons-mac-mini
    role: inference
    managed: false
    capabilities: [llm, vision, embeddings, rerank, stt, tts]
    health_probe: omlx           # selects the oMLX-aware probe (§4.4)
```

Services in MVP: `litellm`, `ember-api`, `ember-dashboard`, `omlx` (external), `litellm-postgres`; profile-gated: `langfuse*`, `qdrant`. `hermes` may appear as an **external consumer tile** only if reachable via `HERMES_URL` (`/api/status`); optional, off by default.

### 4.4 Health state machine

Every service resolves to one of: `unreachable` (connect fail/DNS), `reachable-unhealthy` (HTTP ≥ 400 other than defined states), `starting` (oMLX 503 `loading`; container healthcheck starting), `degraded` (200 but backend not functional — oMLX `loaded_count == 0`; LiteLLM readiness ok but zero healthy deployments), `healthy`. Never green on TCP alone. Dashboard shows the distinct state and the reason string.

oMLX probe: `GET /health` (no auth) → parse `status`, `engine_pool.loaded_count`, `current_model_memory`, `final_ceiling`. Optional authed `GET /v1/models/status` for per-model detail.

LiteLLM probe: `GET /health/readiness` then `GET /model/info` (master key) to confirm the alias set is registered. **Never call LiteLLM `GET /health` from the poll loop** — it performs a live inference call per deployment and (found in the Phase 1 final review, 2026-09-14) thrashed the mini: ~10 requests every ~30 s, evicting Kokoro/Parakeet/bge-m3 to admit gemma-12B, 300 evictions/hour. Deep per-deployment checks run only on demand (`POST /api/services/refresh?deep=true`, `ember doctor`). Non-chat aliases carry `model_info.mode` so any deep check hits the right endpoint. Gateway `degraded` = zero healthy deployments (or readiness ok but `/model/info` missing aliases); `healthy` otherwise, with unhealthy deployments listed in `detail`.

### 4.5 ember-dashboard

Reuse ODS React/Vite/Tailwind scaffold (`App.jsx` shell, `ThemeContext`, layout, `ServiceMap`, `Usage`, `Settings` patterns). Delete `ODSTalk`, `FirstBoot`, `Invites`, `RemoteProvider`, `Extensions`, `GPUMonitor`, plugin registry. Pages:

1. **Overview** — Control plane vs Inference node columns, state badges (§4.4), oMLX memory bar.
2. **Models** — aliases table (alias → provider → model → loaded → memory), oMLX resident models.
3. **Clients / Usage** — from LiteLLM spend logs by virtual key; auto-populates for any consumer.
4. **Providers** — oMLX, OpenRouter configured/reachable; key presence only.
5. **Settings** — read-only view of effective config + validation results; theme.

Branding: "Ember AI", logo swap, no ODS strings in UI (repo keeps ODS attribution in LICENSE/DOWNSTREAM.md).

### 4.6 Observability (profile `observability`, Phase 3)

Donor: `extensions/services/langfuse/compose.yaml.disabled` (7 containers, pinned). LiteLLM entrypoint appends `success_callback: ["langfuse"]` when `LANGFUSE_ENABLED=true`. `EMBER_LOG_PROMPTS=false` default → `turn_off_message_logging: true` (metadata only). Request correlation: LiteLLM `x-litellm-call-id` returned to clients; clients may send `x-request-id`, forwarded as Langfuse `trace_id` where supported. Hermes-side tracing is Hermes's concern.

### 4.7 Speech

Per Jon's ADRs (STT: Parakeet v3 via oMLX; URLs/ownership §4–5): both STT and TTS are **oMLX capabilities**, exposed by Ember only as `ember-stt` / `ember-tts` through LiteLLM's OpenAI-compatible `/v1/audio/transcriptions` and `/v1/audio/speech` passthrough. No `voice.vaxel.xyz`, no separate voice service, no Ember translation layer.

- **STT = Parakeet v3** (`mlx-community/parakeet-tdt-0.6b-v3`, already on the mini). Verify-first: exercise `/v1/audio/transcriptions` with a WAV through oMLX, then through LiteLLM.
- **TTS model = decided by blind A/B** between `mlx-community/Kokoro-82M-bf16` and `mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16` (Qwen3-TTS 1.7B dropped: the mini also carries desktop workloads, so the effective inference ceiling is below the nominal ~10 GB). Protocol (`tools/tts-blind-test.py`, runs on the mini, stdlib only, key read from `~/.omlx/settings.json`): 6 home-assistant-style sentences × each model via oMLX `/v1/audio/speech`; per model record load time, memory delta from `/health`, per-sentence latency and chars/s; clips relabelled A/B with a per-sentence shuffle; mapping sealed until Jon scores naturalness/clarity/prosody 1–5; `--reveal` prints mapping + median latency. Winner → `OMLX_TTS_MODEL`; loser stays on disk, unloaded. Result recorded in ADR 0007. **Run 1 (2026-09-14, oMLX 0.6.4, voices `af_heart` vs `serena`):** Kokoro 0.34 GB resident, 0.36–0.44 s per ~85-char sentence (~200 chars/s); Qwen3-TTS 0.6B 1.90 GB, 3.7–5.0 s (~19 chars/s, ≈ real-time). Both served cleanly via `/v1/audio/speech` (wav). Blind listen (Jon, same day): strong preference for Kokoro on s0/s1/s3/s5; Qwen3 `serena` described as accented and choppy. Confirmed across all sentences incl. inverted s2/s4. **Decided: `Kokoro-82M-bf16`** → `OMLX_TTS_MODEL=Kokoro-82M-bf16`, default voice `af_heart` (British `bf_*`/`bm_*` voices available). Qwen3-TTS 0.6B stays on disk, unloaded, as a future alias target. Original wording: pending benchmark of Kokoro vs Qwen3-TTS 0.6B vs 1.7B (`/v1/audio/voices` reads Kokoro-style voice dirs and Qwen3-TTS speaker tables, so both shapes are supported). `OMLX_TTS_MODEL` is a plain `.env` value; dashboard shows "TTS · <model> · oMLX". Ember ships no TTS model choice.
- Fallback to a native launchd service on the mini only if oMLX rejects a capability; recorded as a dated blocker in the ADR. ODS `whisper`/`tts` extensions are deleted (CPU containers, nothing Metal-capable).

### 4.8 Qdrant (profile `qdrant`)

Hosted for operational convenience only. Ember-api shows health. No collections, ingestion, retrieval or embedding orchestration in Ember. Hermes owns all RAG behaviour and calls `ember-embed` itself.

### 4.9 `bin/ember` CLI (bash, small)

`ember up|down|restart|status|logs|doctor|keys create <client>`. `doctor` validates: `.env` completeness against `.env.schema.json`, compose config renders, oMLX reachable + `/health` parsed, LiteLLM readiness, one real `ember-auto` completion, `ember-embed` returns a vector, optional Langfuse/Qdrant reachability. Exit non-zero on any failure with a plain reason.

---

## 5. Repository layout (post-strip)

```text
Ember-AI/
  README.md                 Ember AI overview, quick start
  DOWNSTREAM.md             upstream ref (v2.6.0 / 21f4b3a64), what was removed and why, how to cherry-pick
  LICENSE                   Apache-2.0, retains Osmantic copyright + Ember notice
  docker-compose.yml        litellm, litellm-postgres, ember-api, ember-dashboard; profiles: observability, qdrant
  .env.example  .env.schema.json  .gitignore  .gitleaks.toml  .pre-commit-config.yaml
  config/litellm/ember.yaml
  services/<id>/manifest.yaml          (+ schema/service-manifest.v1.json with x_ember allowance)
  ember-api/                (FastAPI, pyproject, tests/)
  dashboard/                (Vite React, tests)
  bin/ember
  scripts/                  render-env.sh, validate-manifests.py (donor, trimmed)
  mac-mini/                 README + oMLX expectations; launchd fallback templates (only if §4.7 fallback triggers)
  tests/                    bash tests for ember doctor + compose lint
  docs/  architecture.md deployment.md prox01.md mac-mini.md omlx.md litellm.md speech.md observability.md
         security.md cloudflare.md troubleshooting.md upstream-sync.md hermes-cutover.md
  docs/adr/ 0001-vaxel-service-urls-ownership-network.md (Jon's ADR, moved from repo root)
            0002-stt-parakeet-via-omlx.md (Jon's ADR)
            0003-lean-rebuild-not-overlay.md 0004-litellm-direct-to-omlx.md 0005-external-service-model.md
            0006-rerank-routing.md 0007-tts-via-omlx-model-open.md 0008-ember-api-replaces-dashboard-api.md
            0009-hermes-cutover-after-validation.md
  .github/workflows/        lint-shell, lint-python, dashboard build, compose validate, secret-scan (trimmed donors)
```

### 5.1 Deleted from ODS (non-exhaustive, plan lists precisely)

`ods/install-core.sh`, `installers/`, `ods-cli`, `ods-*.sh`, `bin/ods-host-agent.py`, `bin/remote_provider/`, `bin/model_switchboard/`, all `docker-compose.*.yml`, `config/{backends,gpu-database*,hardware-classes,tier*,model-library,model-router,golden-paths,extensions-catalog,openclaw,ape,searxng,n8n,llama-server}`, `extensions/services/{llama-server,model-router,open-webui,hermes,hermes-proxy,n8n,ape,openclaw,searxng,perplexica,brave-search,comfyui,embeddings,whisper,tts,privacy-shield,token-spy,ods-proxy,tailscale,opencode,remote-provider-*}`, `extensions/library/`, `extensions/templates/`, `templates/`, `agents/`, `opencode/`, `memory-shepherd/`, `migrations/`, `installer/` (Tauri), `install.sh`, `install.ps1`, root `ods/` nesting (flatten), all ODS docs except those rewritten as Ember docs.

---

## 6. Security

- No secrets in git. `.env.example` lists: `OMLX_HOST`, `OMLX_BASE_URL`, `OMLX_API_KEY`, `OMLX_*_MODEL`, `OPENROUTER_API_KEY`, `LITELLM_MASTER_KEY`, `LITELLM_DATABASE_URL`, `EMBER_API_KEY`, `LANGFUSE_*`, `EMBER_LOG_PROMPTS`, `EMBER_CLOUD_FALLBACK`, `EMBER_ALLOW_MODEL_CONTROL`. gitleaks pre-commit retained.
- Bind all control-plane ports to the Docker VM's LAN interface (or `127.0.0.1` + cloudflared) — configurable `BIND_ADDRESS`.
- Public exposure only via Cloudflare: `ai.vaxel.xyz` → `litellm:4000`. Dashboard exposure optional (`ember.vaxel.xyz`), recommended behind Cloudflare Access. Langfuse, Qdrant, ember-api never public.
- Each consumer gets its own LiteLLM virtual key with optional budget/rate limits; master key never distributed.
- oMLX key lives only in `.env` on the Docker VM; LiteLLM injects it. Consumers never see it.

## 7. Cloudflare (documented, not automated)

Tunnel lives on the **Proxmox host** (routes `172.20.142.0/24`); nothing cloudflared-related ships in the Ember stack. Required: public hostname `llm.vaxel.xyz → http://172.20.142.7:4000`. Optional `ember.vaxel.xyz → http://172.20.142.7:3001` behind a Cloudflare Access policy. `docs/cloudflare.md` gives the exact ingress fragment / dashboard steps. Existing `omlx.vaxel.xyz` and `hermes-dashboard.vaxel.xyz` (mini's own cloudflared) unchanged.

## 8. Failure behaviour

| Failure | Result |
|---|---|
| mini off | control plane up; oMLX `unreachable`; `vaxel/{chat,vision,embed,rerank,stt,tts,agent}` return LiteLLM 5xx with clear backend error; `ember-think` still works; optional fallback chat→strong if enabled |
| oMLX up, no model loaded | oMLX `degraded`; first request triggers on-demand load (oMLX LRU); dashboard shows loaded_count |
| Docker VM off | Ember unavailable; Hermes may still hit oMLX directly (until cutover, then documented rollback = revert Hermes base URL) |
| Internet off | local aliases work on LAN URL; cloud alias fails; Cloudflare path down |
| Langfuse down | LiteLLM continues (callback failures non-blocking); dashboard shows Langfuse unhealthy |

## 9. Testing

- `ember-api`: pytest, mocked oMLX/LiteLLM via `respx`/`httpx.MockTransport`; cover state machine (all 5 states × oMLX/LiteLLM), manifest loading incl. `x_ember`, usage aggregation, config validation.
- `dashboard`: Vitest for state rendering, no ODS strings.
- Config: `docker compose config` lint in CI; `validate-manifests.py`; `.env.schema.json` check.
- `ember doctor`: bash test with stub HTTP server.
- Live test procedure documented (`docs/deployment.md#validation`): client → LiteLLM → oMLX completion; embed; stt/tts probes; mini-off drill.

## 10. Phases

1. **Foundation** — strip repo; compose; LiteLLM→oMLX; ember-api health/models/providers; dashboard Overview+Models+Providers; `ember doctor`; docs + ADRs; CI. Proof: OpenAI client → `ai.vaxel.xyz/v1` (or LAN) → oMLX completion.
2. **Speech** — verify Parakeet + chosen TTS model in oMLX; `ember-stt`, `ember-tts`; capabilities view; fallback only if needed.
3. **Observability + clients** — Langfuse profile; prompt-logging toggle; Usage/Clients page; per-client virtual keys; `ember keys`.
4. **Optional infra** — Qdrant profile; ComfyUI placeholder manifest; model load/unload control (gated).
5. **Hermes cutover** — separate approved step: switch Hermes `OPENAI_BASE_URL` to Ember, rollback documented (`docs/hermes-cutover.md`).

## 11. Acceptance criteria (Phase 1)

1. oMLX, Hermes, n8n untouched and functional.
2. No duplicate n8n/Hermes/oMLX/OpenCode deployment.
3. LiteLLM runs on the Docker VM independently of the mini.
4. OpenAI-compatible request via `ember-auto` returns an oMLX completion; `ember-embed` returns vectors.
5. Dashboard shows control-plane + inference-node services with real 5-state health; mini shutdown shows `unreachable`, dashboard stays up.
6. No secrets committed; gitleaks passes.
7. `ember doctor` green on the target VM.
8. Docs + ADRs + `DOWNSTREAM.md` present; upstream divergence = "everything, by design", cherry-pick path documented.
9. Tests pass in CI.

## 12. Open items / verify-first

- Parakeet v3 + the benchmarked TTS model actually load and serve via oMLX 0.6.4 (§4.7).
- LiteLLM rerank passthrough to Cohere-shaped oMLX endpoint (§4.1 → ADR 0005).
- Mini LAN hostname/IP, oMLX key, SSH users/hosts — from Jon when keys provisioned.
- Whether `ai.vaxel.xyz` should also front ember-api under a path (`/api/*`) or stay LiteLLM-only. Default: LiteLLM-only.

## 13. Out of scope

Chat UI, agent orchestration, agent memory, MCP hosting, n8n/HA integration, RAG ingestion/retrieval, ComfyUI orchestration, OpenCode deployment, multi-Mac inference, automatic cloud failover by default, Alexa replacement hardware.
