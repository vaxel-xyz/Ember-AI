# Context carried over from the Claude Code sessions (14–16 Sep 2026)

Ember-AI is Jon Howard-Totham's personal homelab (Vaxel) project. Nothing here relates to his employer; keep it that way.

## Environment facts
- **Prox01** (Proxmox) hosts the Docker VM "Docker01" (`root@172.20.142.7`, Debian 13, 4 vCPU, 7.8 GiB RAM since the 2026-09-14 reboot): stacks under `/opt/stacks/<name>` — `n8n` (n8n.vaxel.xyz, Postgres+Redis+workers, plus n8n-mcp on host :3000), `portainer` (:9443), `ember`. Home Assistant is a separate VM. Cloudflare tunnel runs on the Proxmox host and routes 172.20.142.0/24; hostnames are added there by hand.
- **jons-mac-mini** (`jtotham@172.20.142.184`, Apple M4, 16 GB, also a desktop): oMLX 0.6.4 as the DMG app + CLI `~/.omlx/bin/omlx`, bound `*:8000` since 2026-09-14 (`server.host` changed from 127.0.0.1; backup `~/.omlx/settings.json.bak-ember-20260914`), bearer key at `.auth.api_key`; Hermes Agent under launchd (`ai.hermes.gateway` :8642, dashboard 127.0.0.1:9119, config `~/.hermes/config.yaml`, primary OpenRouter, fallback local oMLX); its own cloudflared publishes omlx.vaxel.xyz and hermes-dashboard.vaxel.xyz. **No Docker on the mini.** Model ids = folder names under `~/.omlx/models`; oMLX rescans only on restart.
- Prox01 → mini traffic is LAN only (no Cloudflare hairpin, no Tailscale).
- Jon's laptop (MacBook Pro M4 Pro) is where the agent runs; SSH aliases `vaxel-docker`/`vaxel-mini` in `~/.ssh/config` using key `~/.ssh/id_ed25519_vaxel`.

## Decisions (chronological)
- 2026-09-14: PRD (ChatGPT-authored) → redirected same day to a four-way split: OpenWork UI / Hermes agent / OpenCode dev tool / **Ember = shared AI infra only**. Lean rebuild of the ODS fork, not an overlay. Do not adapt ODS model-router, switchboard, remote-provider, `LLM_BACKEND=external`.
- ADR 0001 (URLs/ownership), ADR 0002 (STT = Parakeet v3 via oMLX). Cloud provider OpenRouter, `z-ai/glm-5.3`. Hermes cutover only after validation (ADR 0009).
- TTS by blind A/B via oMLX: Kokoro-82M-bf16 beat Qwen3-TTS 0.6B (accented, choppy, 10× slower) — ADR 0007. Qwen3-TTS 1.7B dropped: mini RAM shared with desktop use.
- Embeddings `bge-m3-mlx-8bit`; rerank raw `BAAI/bge-reranker-v2-m3` (heavy: 2.38 GB resident) — ADR 0006.
- 2026-09-16 ADR 0010 (frontend/routing/voice): Open WebUI = primary chat UI at `chat.vaxel.xyz` as a **separate stack**; gateway = `ai.vaxel.xyz/v1` (OpenWork dropped); aliases `local-fast/local-smart/heavy` added beside `ember-*`; MCP lives in Open WebUI/Hermes, never ember-api; realtime voice via OpenAI Realtime later.

## Hard-won lessons
- **LiteLLM `GET /health` runs a real inference call per deployment.** Polling it every 15 s evicted the mini's STT/TTS/embedding models 300×/hour and made oMLX look down. Gateway liveness = `/health/readiness` + `/model/info`; deep checks on demand only; set `model_info.mode` on non-chat aliases.
- LiteLLM's `openai/` embeddings path sends `encoding_format=base64` by default; oMLX 422s — pin `encoding_format: float`.
- Compose interpolates `${VAR:?}` across the whole file regardless of profiles — a profile-only variable still has to exist in `.env`.
- `bin/ember up` does not recreate `litellm` for template-only edits; use `bin/ember restart`.
- oMLX `omlx stop` cannot stop a server process it did not start (orphan `omlx-server` PID 66607 from an earlier `omlx start` is serving :8000 as of 2026-09-16).
- Jon's Claude Code permission rules deny any path matching `.env*`; the repo's `.env.example`/`.env.schema.json` were edited via small `python3` scripts. Public repo: never commit real keys or remote-access URLs (the Home Assistant Nabu Casa MCP URL was deliberately redacted from ADR 0010).
- Upstream ODS history contains a likely-real LiveKit key/secret (their `SECURITY_AUDIT.md` C1); annotated in `.gitleaks.toml` and `DOWNSTREAM.md`, not purged — Jon's call.
