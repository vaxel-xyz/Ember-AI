# ADR 0010: Ember Frontend, Routing and Voice Architecture

**Status:** Accepted — supersedes earlier assumptions that oMLX native web chat or ChatGPT would remain the primary long-term user interface. Supersedes ADR 0001 §1 and §3 (public hostname for the LLM gateway; `ai.vaxel.xyz` is no longer reserved for a separate OpenWork frontend).
**Date:** 2026-09-16
**Project:** `vaxel-xyz/Ember-AI`
**Author:** Jon Howard-Totham. Text reproduced verbatim except: the Home Assistant remote MCP URL is redacted (this repository is public) and ASCII arrows replace box-drawing characters.

## Context

The Ember platform is intended to become the primary AI interface for the Vaxel environment.

The original architecture focused on:

- oMLX for local inference
- LiteLLM as an API/gateway layer
- Hermes for long-running agent tasks
- n8n for orchestration
- Home Assistant for home automation
- ChatGPT as the primary conversational frontend

Further testing and design work has exposed two important constraints.

First, the built-in oMLX web chat is not suitable as the main cross-device user interface because conversation history is effectively browser/session scoped rather than a centrally persisted, authenticated conversation history that follows the user between Mac, iPhone and iPad.

Second, ChatGPT remains significantly ahead for realtime conversational voice, but its consumer application does not currently provide the level of custom MCP/tool integration required to make it the permanent frontend for Ember.

The architecture must therefore separate:

1. user interface and conversation persistence
2. model routing
3. inference providers
4. realtime voice
5. tools and agents

No individual frontend or model provider should become a hard dependency.

## Decision

### 1. Open WebUI becomes the primary Ember chat frontend

Deploy Open WebUI as the main cross-device conversational interface.

Target public endpoint: `https://chat.vaxel.xyz`

Open WebUI becomes responsible for: authenticated user access; server-side conversation persistence; cross-device chat history; PWA installation on iPhone and iPad; desktop/browser chat; model selection; attachments and multimodal UI where supported; tool/MCP presentation where supported.

Open WebUI replaces the oMLX built-in web chat as the normal user-facing chat interface. The oMLX native UI remains available for model administration, testing, diagnostics and direct inference troubleshooting. It must not be treated as the canonical conversation store.

### 2. LiteLLM becomes the canonical LLM control plane

The LiteLLM instance already deployed as part of the Ember stack should remain in that stack. Do not deploy a second standalone LiteLLM instance.

LiteLLM becomes the single OpenAI-compatible API endpoint consumed by Open WebUI and other Ember clients.

Canonical public endpoint: `https://ai.vaxel.xyz/v1`

```text
Open WebUI -> LiteLLM -> { oMLX | OpenRouter | OpenAI | future providers }
```

LiteLLM owns: model abstraction; provider credentials; model aliases; fallback/routing policy; usage accounting; API keys; model availability; cloud/local provider selection. Clients must not need to know individual provider URLs or credentials.

### 3. oMLX remains the local inference backend

oMLX continues to run on the Mac Mini and remains the preferred local inference provider. Existing endpoint: `https://omlx.vaxel.xyz/v1`.

oMLX should be registered in LiteLLM as one or more logical models. Initial logical aliases should favour human-readable roles rather than exposing raw model IDs. Suggested initial aliases: `local-fast`, `local-smart`. The exact underlying model associated with each alias may change without requiring Open WebUI or downstream clients to be reconfigured.

oMLX remains responsible for: local LLM inference; Apple Silicon / MLX acceleration; local model lifecycle; locally hosted speech or multimodal models where appropriate.

### 4. OpenRouter becomes the heavy cloud inference provider

OpenRouter should be configured behind LiteLLM for tasks where local inference is insufficient. Logical alias: `heavy`.

The initial heavy model may be GLM 5.x or another high-capability model selected during testing. The architecture must not hard-code GLM as the permanent provider. The alias should allow Ember to switch between GLM, Claude, Gemini, OpenAI and future models without changing Open WebUI configuration.

### 5. Introduce an optional `auto` routing model

LiteLLM should eventually expose `auto`, routing on prompt complexity, latency sensitivity, context length, tool requirements, expected reasoning depth, local availability and cost.

```text
simple / fast                 -> local-fast
normal local work             -> local-smart
complex reasoning / large ctx -> heavy
```

This should not block initial deployment. Manual aliases should work first.

### 6. Realtime voice is a separate transport from normal text chat

Realtime voice must not be implemented as merely another model selected through a normal `/v1/chat/completions` request. ChatGPT Voice quality depends on realtime audio transport, voice activity detection, low latency, interruption / barge-in, simultaneous listening and response, conversational turn detection and streaming speech generation.

```text
TEXT:  Open WebUI -> LiteLLM -> { oMLX | OpenRouter }
VOICE: Open WebUI voice client or dedicated Ember voice surface
         -> OpenAI Realtime / GPT-Live -> { tools | LiteLLM | Hermes | MCP services }
```

OpenAI Realtime/GPT-Live is currently the preferred premium voice backend because it provides the closest available experience to ChatGPT Voice Mode. This is a replaceable component. The wider Ember architecture must not depend specifically on OpenAI Voice.

### 7. Local voice remains a parallel fallback path

Local speech components should continue to be developed independently. Preferred STT: Parakeet, served through oMLX where practical. Local TTS may use Qwen TTS, Kokoro or another lightweight local model depending on quality and resource usage. (Ember note: ADR 0007 already selected Kokoro-82M-bf16 by blind A/B on 2026-09-14.)

```text
Microphone -> Parakeet STT -> local LLM via LiteLLM -> local TTS
```

This does not need to match ChatGPT Voice immediately. The goal is to maintain a private/local fallback and progressively improve it.

### 8. MCP becomes the standard tool boundary

Ember should use MCP wherever practical for external capabilities. Primary planned MCP/tool domains: Home Assistant, Hermes, n8n, GitHub, infrastructure tooling, future personal services.

The AI frontend should not contain direct Home Assistant, Proxmox, TrueNAS or workflow-specific logic. Instead:

```text
Open WebUI / Voice -> Agent / model -> MCP / tool layer -> { Home Assistant | Hermes | n8n | infrastructure services }
```

This allows each frontend or model to be replaced without rebuilding integrations.

### 9. Home Assistant integration

The Home Assistant native MCP endpoint remains the preferred HA interface. The external Home Assistant MCP endpoint is a private remote-access URL and is **not recorded in this public repository**; it lives only in the `.env` of the host that consumes it.

Initially, expose Home Assistant in read-only mode where useful. Longer term, Ember may use full control capabilities once the agent/tool security model is mature. Sensitive actions (door locks, alarms, garage doors, security functions) must remain explicitly protected.

### 10. Hermes remains the agent/execution layer

Hermes should not compete with Open WebUI for ownership of normal conversations. Its role remains long-running tasks, delegated jobs, local execution, agent sessions and work that should continue independently of the frontend.

```text
Open WebUI -> model / agent -> Hermes -> long-running execution
```

Hermes should be treated as a backend capability, not the primary chat UI.

### 11. n8n remains the orchestration layer

n8n continues to own deterministic workflows and service orchestration: repeatable workflows, scheduled automation, multi-service integration, webhook flows, transformation pipelines. Do not use n8n as a substitute for the primary model router. LiteLLM owns model routing. n8n owns workflow routing.

### 12. Public endpoint ownership

```text
https://chat.vaxel.xyz              Open WebUI / Ember chat frontend
https://ai.vaxel.xyz/v1             LiteLLM canonical OpenAI-compatible API
https://ember.vaxel.xyz             Ember-AI administration dashboard (unchanged from ADR 0001)
https://omlx.vaxel.xyz/v1           direct local oMLX inference endpoint
https://n8n.vaxel.xyz               n8n workflow UI/API
https://hermes-dashboard.vaxel.xyz  Hermes administration/session dashboard
```

Where practical, public services should continue to use Cloudflare Tunnel rather than directly exposed inbound ports.

### 13. Client configuration

Open WebUI should only need one primary LLM connection: base URL `https://ai.vaxel.xyz/v1` (LAN: `http://172.20.142.7:4000/v1`) with a LiteLLM-issued API key. Open WebUI must not be given OpenRouter credentials, OpenAI credentials, direct oMLX credentials or provider-specific API keys. Those belong behind LiteLLM.

### 14. PWA strategy

Open WebUI should be deployed as an installable PWA for iPhone, iPad, Mac and desktop browsers: open Ember from the Home Screen, same authenticated account, same conversation history, same model/tool environment. Cross-device persistence is a core requirement.

### 15. ChatGPT becomes transitional rather than architectural

ChatGPT continues to be used where it provides materially better capability (Voice Mode, difficult reasoning, ad-hoc assistance), but no new Ember dependency should require ChatGPT-specific functionality unless unavoidable. Replace ChatGPT incrementally rather than rebuild everything at once. First functions to move: conversation storage, model routing, tool access, agent execution. Voice is expected to be one of the last dependencies replaced.

## Resulting target architecture

```text
iPhone / iPad / Mac / Browser
        |
        v
Open WebUI  (chat.vaxel.xyz: conversations, auth, PWA)
        |  normal text
        v
LiteLLM    (ai.vaxel.xyz/v1)
   |               |
   v               v
oMLX            OpenRouter
local inference heavy models

Realtime voice: Open WebUI / Ember Voice UI -> OpenAI Realtime / GPT-Live -> tools/MCP, LiteLLM
Tool / agent layer: MCP / APIs -> Home Assistant | Hermes | n8n
```

## Implementation priority

1. Reuse the LiteLLM instance already deployed in the Ember stack; expose it as `https://ai.vaxel.xyz/v1`; confirm health, authentication, database persistence, provider configuration. Do not deploy another LiteLLM stack. **(Done in Phase 1 except the hostname.)**
2. oMLX behind LiteLLM with aliases `local-fast`, `local-smart`; test Open WebUI client -> LiteLLM -> oMLX. **(oMLX routing done; aliases added in branch 2.)**
3. OpenRouter behind LiteLLM as `heavy`; test cloud routing and fallback. **(Route exists as `ember-think`; `heavy` added in branch 2; validation needs the key.)**
4. Deploy Open WebUI at `https://chat.vaxel.xyz` with persistent server-side history, authentication, PWA, LiteLLM as the single LLM API, aliases instead of raw provider model names. **(Branch 2.)**
5. Reconnect tools and MCP services: Home Assistant, Hermes, n8n, infrastructure/admin tools. **(Later.)**
6. Prototype premium realtime voice on OpenAI Realtime/GPT-Live: WebRTC, VAD, barge-in, interruption, tool calling, LiteLLM and MCP access, usable from the iPhone/iPad PWA. Do not block normal deployment on this. **(Later.)**
7. Local voice fallback: Parakeet + local model + local TTS, measured against OpenAI Realtime for latency, interruption quality, recognition accuracy, speech naturalness and resource usage. **(Later.)**

## Consequences

Positive: cross-device conversation history; frontend independent of model provider; replaceable providers; local and cloud inference coexist; oMLX stays useful without owning the UX; LiteLLM has a clear role; Hermes and n8n keep distinct responsibilities; incremental migration away from ChatGPT; voice evolves independently of text UI.

Negative: Open WebUI is another service; realtime voice is not fully local initially; separate text and voice execution paths; MCP/tool permissions need deliberate security design; more authentication and secrets management.

These trade-offs are accepted.

## Explicit non-goals

Do not: duplicate LiteLLM in a separate Docker stack; make oMLX native chat the canonical frontend; store provider API keys in Open WebUI; couple integrations directly to one model; force all workloads through n8n; replace ChatGPT Voice prematurely with an inferior experience; hard-code GLM/OpenRouter/OpenAI as permanent providers; make OpenAI Realtime mandatory for the broader Ember architecture.

## Final principle

Ember should own the conversations, the routing, the tools, the agents and the integrations. Model providers and voice providers are interchangeable components. The desired end state is not "a local copy of ChatGPT"; it is a provider-independent personal AI platform where ChatGPT-class services can be used when advantageous without owning the underlying system.
