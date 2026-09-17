# ADR 0012: Hermes Agent as a Distinct Open WebUI Backend

**Status:** Accepted
**Date:** 2026-09-17
**Project:** `vaxel-xyz/Ember-AI`
**Source ADR:** Jon's "ADR: Shared Project Knowledge and Remote Hermes Access" (2026-09-17) —
§5–7 (Hermes is the remote execution agent; Open WebUI is its primary remote interface).

## Context

Hermes Agent runs on `jons-mac-mini` as a full agent platform (launchd `ai.hermes.gateway`
:8642 and `ai.hermes.dashboard` :9119; sessions, kanban, cron, skills, terminal, browser,
memories). Verified facts about the existing deployment:

- Gateway **0.20.4** serves an **OpenAI-compatible API** on `http://172.20.142.184:8642/v1`
  where the single advertised model is `hermes-agent` — the agent itself, not a raw model.
  Both streaming (SSE) and non-streaming chat completions work; the agent loop (tools,
  terminal, browser, skills) executes inside Hermes.
- Auth is a bearer `API_SERVER_KEY` (from the mini's `~/.hermes/.env`).
- The gateway is bound to the LAN IP, and the mini's PF firewall (`xyz.vaxel.hermes` anchor)
  already allows inbound TCP/8642 **from Docker01 (172.20.142.7) only** — exactly where Open
  WebUI runs. No firewall change is needed.
- Hermes's model routing is its own: primary OpenRouter (`z-ai/glm-5.2`), fallback local oMLX
  (`Ornith-1.5-9B-MLX-4bit`). This is deliberate and stays.
- A separate n8n MCP front (`https://n8n.vaxel.xyz/mcp/hermes`, six session tools) already
  exposes Hermes to ChatGPT. It is an independent consumer and stays untouched.

The source ADR is explicit: Hermes **MUST NOT** be treated merely as another inference model
behind LiteLLM if that obscures its agent/runtime capabilities. Open WebUI should expose it
as a distinct agent/backend alongside the normal Ember models.

## Decision

1. **Open WebUI gains a second, separate OpenAI-compatible connection** pointing directly at
   the Hermes gateway (`http://172.20.142.184:8642/v1`, bearer `API_SERVER_KEY`). Configured
   via `OPENAI_API_BASE_URLS` / `OPENAI_API_KEYS` (semicolon-separated lists; entry 1 =
   LiteLLM, entry 2 = Hermes). The model appears in the picker as `hermes-agent` beside the
   `local-*`/`cloud-*` aliases.
2. **Hermes is NOT routed through LiteLLM.** No alias, no LiteLLM config change, no
   ember-api change. The agent loop, tools and model routing remain entirely inside Hermes —
   satisfying the source ADR's requirement.
3. **Long-run timeout:** Open WebUI's `AIOHTTP_CLIENT_TIMEOUT` is raised to 1800 s to match
   Hermes's own `gateway_timeout`, because agent turns can legitimately run long.
4. **Nothing in the Hermes deployment changes.** See the preservation plan below.

## Preservation plan (existing Hermes config — reviewed, not replaced)

| Existing artefact | Disposition |
|---|---|
| `~/.hermes/config.yaml` (providers, fallbacks, toolsets, agent settings) | **Unchanged.** Its OpenRouter-primary / oMLX-fallback routing is orthogonal to who reaches the API. |
| launchd `ai.hermes.gateway` / `ai.hermes.dashboard` | **Unchanged.** |
| `API_SERVER_KEY` + LAN binding + PF anchor `xyz.vaxel.hermes` | **Unchanged.** The existing Docker01-only rule is exactly the access Open WebUI needs. |
| n8n MCP front (ChatGPT path, six session tools) | **Unchanged.** Independent consumer; Open WebUI talks to the gateway API directly, not through n8n. |
| Hermes sessions/memories/kanban state | **Unchanged.** Open WebUI chats create ordinary Hermes sessions via the same API the dashboard uses. |
| Hermes dashboard (:9119) | **Unchanged** — remains the administrative interface per the source ADR §8. |

The only changed system is **Open WebUI's own environment** (additive, reversible, our
stack). No Hermes file, service, or firewall rule is touched.

## Consequences

- **Remote flow achieved** (source ADR §7): phone/laptop → Open WebUI → Hermes API → mini →
  `~/Projects`, Git, MCPs, local tools — with Open WebUI as the conversational frontend and
  Hermes performing work from the trusted home environment.
- **Two histories, explicitly non-authoritative:** Open WebUI keeps the frontend transcript;
  Hermes keeps its own session store. Per the source ADR's knowledge model, both are
  non-authoritative; durable knowledge still gets promoted to the Projects workspace.
- **Agent turns can be slow** (multi-tool loops). The 1800 s timeout accommodates this;
  users should expect "thinking" pauses on `hermes-agent` that don't occur on plain model
  aliases.
- **Verification performed** (2026-09-17): from inside the Open WebUI container —
  `GET /v1/models` → `hermes-agent`; non-streaming completion → "pong"; streaming → SSE
  chunks + `[DONE]`. UI-side verification (model picker) lands with the first admin sign-up.
- **Out of scope here:** Projects-knowledge indexing into Open WebUI (source ADR §4) and the
  shared `~/Projects` root knowledge files — next milestone.
