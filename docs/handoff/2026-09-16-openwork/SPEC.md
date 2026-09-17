# Ember-AI — Frontend, Routing and Voice ADR: Ember-side changes (branch 2)

**Date:** 2026-09-16
**Repo:** `vaxel-xyz/Ember-AI` (PUBLIC), new branch `feature/frontend-routing-adr` off `main` after PR #1 merges (or off `feature/ember-lean-rebuild` if PR #1 is still open)
**Inputs:** Jon's "ADR: Ember Frontend, Routing and Voice Architecture" (2026-09-16); Jon's decisions 2026-09-16: hostnames per new ADR; add human-facing aliases alongside `ember-*`; Open WebUI as a **separate** stack; Phase 1 PR first.
**Supersedes in ADR 0001:** §1 (`ai.vaxel.xyz` reserved for OpenWork) and §3 (`llm.vaxel.xyz/v1`). Everything else in ADR 0001 stands (dashboard `ember.vaxel.xyz`, LAN-first internal traffic, OpenCode independent, n8n outside the critical path).

## 1. Scope — what Ember-AI changes

| # | Change | Ember artefacts |
|---|---|---|
| 1 | Public gateway hostname → `https://ai.vaxel.xyz/v1` | `.env.example` `LLM_PUBLIC_URL`, `docs/cloudflare.md` ingress, README/docs/spec references, dashboard Providers copy, ADR 0001 amendment note |
| 2 | Human-facing aliases `local-fast`, `local-smart`, `heavy` added to the LiteLLM template, each pointing at the same target as `ember-fast`, `ember-auto`, `ember-think` | `config/litellm/ember.yaml.tmpl`, `ember_api/aliases.py` (13 names), render test, `/api/models` shows both names per target, docs/litellm.md alias table |
| 3 | `auto` alias — **deferred**; documented as future routing policy (ADR §5) | docs only |
| 4 | Open WebUI = external consumer, separate stack `/opt/stacks/openwebui` on Docker01 | `services/open-webui/manifest.yaml` (`type: external`, `host_env: OPENWEBUI_HOST`, port 8080→ host `${OPENWEBUI_PORT:-3003}`, health `/health`, `public_url_env: CHAT_PUBLIC_URL`, `x_ember: {node: docker01, role: consumer, managed: false}` — `role` enum gains `consumer`); reference stack `deploy/openwebui/compose.yml` + `deploy/openwebui/README.md` (Open WebUI pinned image, `OPENAI_API_BASE_URL=http://172.20.142.7:4000/v1` LAN, `OPENAI_API_KEY` = LiteLLM virtual key from `bin/ember keys create open-webui`, `WEBUI_AUTH=true`, persistent volume, `ENABLE_SIGNUP=false` after first admin); `docs/open-webui.md` |
| 5 | Dashboard shows Open WebUI tile under a new "Consumers" group (docker01 node, not managed) | `routers/services.py` nodes grouping unchanged; Overview shows role `consumer` badge |
| 6 | ADR 0010 = Jon's ADR text verbatim **minus the Home Assistant Nabu Casa MCP URL** (repo is public; replace with `<HA_MCP_URL — private, see .env on the Hermes/Open WebUI host>`) | `docs/adr/0010-frontend-routing-voice.md`; ADR 0001 gets a "Superseded in part by ADR 0010" header line |
| 7 | Spec/docs: remove OpenWork as UI owner; Open WebUI is the human UI; MCP is hosted by the frontend/agent layer (Open WebUI MCP config, Hermes), **still not by ember-api** | spec §1.1, README four-way table, docs/architecture.md |
| 8 | Cloudflare doc: `ai.vaxel.xyz → http://172.20.142.7:4000`, `chat.vaxel.xyz → http://172.20.142.7:3003`, `ember.vaxel.xyz → http://172.20.142.7:3001` (Access policy recommended on `ember.`; Open WebUI has its own auth) | `docs/cloudflare.md` |

Out of scope for branch 2 (roadmap in ADR 0010 / docs/roadmap.md): MCP reconnection (ADR Phase 5), OpenAI Realtime voice (Phase 6), local voice pipeline beyond `ember-stt`/`ember-tts` (Phase 7), `auto` routing.

## 2. Constraints
- No secrets in the repo; the Open WebUI reference compose reads everything from its own `.env` (gitignored) — placeholders only in `deploy/openwebui/.env.example`.
- Open WebUI never receives provider keys (ADR §13): one LiteLLM virtual key, LAN base URL.
- `ember-*` aliases unchanged (Hermes cutover doc and ember-api depend on them).
- Ember-api gains no MCP, chat, or conversation code.
- Public repo: the ADR's Nabu Casa URL and any other remote-access URLs stay out of git.

## 3. Verification
- Render test asserts 13 aliases and that `local-fast`/`ember-fast`, `local-smart`/`ember-auto`, `heavy`/`ember-think` resolve to identical `litellm_params`.
- `ember doctor` gains a check: `local-smart` completion via LiteLLM.
- Manifest validator accepts `role: consumer`; ember-api test covers the Open WebUI tile `unreachable` when `OPENWEBUI_HOST` is unset/down.
- Live: Open WebUI stack up on Docker01, logs in, lists `local-fast/local-smart/heavy`, one chat round-trip through LiteLLM→oMLX; receipt appended to `docs/deployment.md`.

## 4. Jon's items
- Cloudflare: add `ai.vaxel.xyz`, `chat.vaxel.xyz`, `ember.vaxel.xyz` hostnames on the Proxmox tunnel.
- OpenRouter key into `/opt/stacks/ember/.env` (validates `heavy`/`ember-think`).
- First Open WebUI admin account at `chat.vaxel.xyz`, then set `ENABLE_SIGNUP=false`.
