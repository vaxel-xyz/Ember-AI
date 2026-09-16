# ADR: Vaxel Service URLs, Ownership and Network Architecture

**Status:** Accepted  
**Date:** 2026-09-14  
**Project:** `vaxel-xyz/Ember-AI`

**Superseded in part (2026-09-16):** §1 and §3 hostnames are superseded by [ADR 0010](0010-frontend-routing-voice.md) — the LLM gateway is `https://ai.vaxel.xyz/v1` and Open WebUI is the human frontend at `https://chat.vaxel.xyz`. All other sections stand.

## Context

The Vaxel architecture has changed substantially from the original ODS-derived design.

The system is now explicitly separated into:

- **OpenWork / Vaxel UI** — primary human-facing interface.
- **Hermes / Ember** — persistent general-purpose agent.
- **Ember-AI** — shared inference, voice and AI infrastructure.
- **oMLX** — Apple Silicon local inference runtime.
- **LiteLLM** — LLM gateway/routing layer.
- **OpenCode** — independent, locally launched software-development agent.
- **n8n** — deterministic automation/workflow platform.

This requires a corresponding change to service URLs and network boundaries.

The previous intention to use `ai.vaxel.xyz/v1` for inference is superseded by this ADR.

---

# Decision

Adopt the following canonical public service namespace.

| URL | Service | Purpose |
|---|---|---|
| `https://ai.vaxel.xyz` | Vaxel/OpenWork | Primary human-facing Ember interface |
| `https://ember.vaxel.xyz` | Ember-AI | AI infrastructure administration/dashboard |
| `https://llm.vaxel.xyz/v1` | LiteLLM | OpenAI-compatible LLM inference gateway |
| `https://omlx.vaxel.xyz` | oMLX | Direct local inference administration/API |
| `https://hermes-dashboard.vaxel.xyz` | Hermes Dashboard | Hermes administration/debugging |
| `https://n8n.vaxel.xyz` | n8n | Workflow automation |
| `https://n8n-mcp.vaxel.xyz` | n8n MCP | MCP access to n8n |
| `https://portainer.vaxel.xyz` | Portainer | Container administration |

Existing service URLs should not be renamed unnecessarily where they already match this scheme.

---

# 1. `ai.vaxel.xyz` — Human Interface

`ai.vaxel.xyz` is reserved for the primary human-facing Vaxel AI experience.

Target:

```text
ai.vaxel.xyz
      │
      ▼
Vaxel/OpenWork
      │
      ▼
Hermes
   "Ember"
```

It MUST NOT be used as the primary raw model inference endpoint.

The previous proposed API:

```text
https://ai.vaxel.xyz/v1
```

is therefore deprecated as an architectural target.

The OpenAI-compatible LLM endpoint moves to:

```text
https://llm.vaxel.xyz/v1
```

This provides a clean distinction between:

```text
ai.vaxel.xyz       HUMAN
llm.vaxel.xyz      MACHINE
```

---

# 2. `ember.vaxel.xyz` — Ember-AI Administration

`ember.vaxel.xyz` hosts the Ember-AI infrastructure/admin interface.

It is NOT the primary conversational interface.

Its responsibilities include visibility and administration for:

- inference providers;
- model configuration;
- model aliases;
- oMLX connectivity;
- LiteLLM;
- STT;
- TTS;
- provider health;
- request latency;
- API usage;
- service health;
- authenticated API consumers;
- logs/observability where appropriate.

Example conceptual dashboard:

```text
EMBER AI

System
──────────────────────────
LiteLLM             Healthy
oMLX                Healthy
Parakeet STT        Healthy
TTS                 Healthy

Local Inference
──────────────────────────
Host                jons-mac-mini
Provider            oMLX

Models
──────────────────────────
ember-auto          ...
ember-fast          ...
ember-think         ...
ember-code          ...
ember-local         ...

Clients
──────────────────────────
Hermes              Active
OpenCode            ...
n8n                 ...
```

Consumer visibility should derive from generic API/gateway telemetry.

Do NOT implement bespoke OpenCode, n8n, Home Assistant or OpenWork integrations merely to populate this dashboard.

Hermes is the only required first-class consumer at present.

---

# 3. `llm.vaxel.xyz/v1` — LLM Gateway

LiteLLM owns the canonical Vaxel LLM API.

Public endpoint:

```text
https://llm.vaxel.xyz/v1
```

It should expose an OpenAI-compatible API wherever practical.

Architecture:

```text
                 llm.vaxel.xyz/v1
                        │
                        ▼
                     LiteLLM
                        │
             ┌──────────┼──────────┐
             │          │          │
             ▼          ▼          ▼
           oMLX       OpenAI    Anthropic/
                                  others
```

LiteLLM is responsible for:

- LLM provider abstraction;
- logical model aliases;
- model routing where required;
- authentication;
- fallback policies where configured;
- usage accounting;
- LLM request telemetry.

Logical Vaxel model aliases should be preferred over coupling clients to specific underlying models.

Examples:

```text
ember-auto
ember-fast
ember-think
ember-code
ember-local
```

The actual model behind an alias may change without requiring client configuration changes.

---

# 4. oMLX — Local Inference Runtime

oMLX remains the primary Apple-Silicon inference runtime on:

```text
jons-mac-mini
```

It is no longer considered merely an LLM server.

It should provide supported local inference capabilities including:

```text
oMLX
 ├── LLM inference
 ├── STT
 │    └── Parakeet v3
 └── TTS
      └── selected MLX TTS model
```

The selected TTS model is currently subject to benchmarking between suitable oMLX-supported options, including:

- Kokoro;
- Qwen3-TTS 0.6B;
- Qwen3-TTS 1.7B.

Do not hard-code Kokoro as the permanent architecture until this evaluation is complete.

Parakeet v3 is the selected STT engine and should be consumed through oMLX rather than deployed as an independent Parakeet service.

---

# 5. Voice API Boundary

Ember-AI owns the stable voice infrastructure/API boundary.

Conceptually:

```text
Voice Client
     │
     ▼
Ember-AI Voice API
     │
     ▼
    oMLX
 ┌────┴─────┐
 │          │
STT        TTS
 │          │
Parakeet   selected
v3         TTS model
```

Where practical, use standards/OpenAI-compatible APIs such as:

```text
POST /v1/audio/transcriptions
POST /v1/audio/speech
```

Do not introduce additional public DNS names merely because STT and TTS are internally separate capabilities.

A dedicated:

```text
voice.vaxel.xyz
```

is NOT currently required.

Add one later only if a genuine architectural requirement emerges.

---

# 6. Hermes — Persistent Ember Agent

Hermes remains the primary persistent general-purpose Vaxel agent.

Conceptual path:

```text
OpenWork
   │
   ▼
Hermes / Ember
   │
   ├── memory
   ├── skills
   ├── RAG
   ├── MCP
   ├── tools
   ├── Home Assistant
   ├── proactive tasks
   ├── scheduling
   └── general agent reasoning
```

Hermes consumes Ember-AI inference infrastructure but remains architecturally separate from it.

Ember-AI MUST NOT duplicate Hermes responsibilities such as:

- persistent agent memory;
- RAG behaviour;
- agent loops;
- MCP orchestration;
- Home Assistant agent logic;
- proactive jobs;
- browser agents;
- autonomous task execution.

The existing Hermes dashboard remains:

```text
https://hermes-dashboard.vaxel.xyz
```

This is an administrative/debug interface, not the intended primary Vaxel user experience.

---

# 7. OpenCode — Independent Developer Tool

OpenCode is NOT part of the always-on Ember-AI application stack.

OpenCode replaces or supplements the current Claude Code workflow.

Normal use:

```text
Jon
 │
 ▼
OpenCode
 │
 ▼
specific local project/repository
 │
 ├── filesystem
 ├── terminal
 ├── LSP
 ├── tests
 └── Git/GitHub
```

OpenCode is launched locally when software-development work is required.

It may use:

```text
https://llm.vaxel.xyz/v1
```

where beneficial, but MAY also use native model-provider integrations directly.

Do not force OpenCode through LiteLLM solely for architectural consistency.

Ember-AI SHALL NOT:

- deploy OpenCode;
- manage OpenCode projects;
- implement OpenCode orchestration;
- reproduce OpenCode's developer UI;
- make OpenCode availability a prerequisite for Ember operation.

---

# 8. n8n

n8n remains the deterministic workflow/automation platform.

Existing URLs remain:

```text
https://n8n.vaxel.xyz
https://n8n-mcp.vaxel.xyz
```

Its architectural role changes from mandatory ChatGPT/Hermes glue to an optional execution capability available to Hermes and other Vaxel systems.

Preferred relationship:

```text
Hermes
   │
   ├── direct tools/MCP
   │
   └── n8n
         │
         ▼
   deterministic workflow
```

Normal Ember conversation MUST NOT depend upon n8n being operational.

---

# 9. Internal vs Public Networking

Public Cloudflare-backed URLs provide remote access and stable external service identities.

However, local machine-to-machine communication SHOULD use LAN/service networking where practical.

Avoid unnecessary Cloudflare hairpinning.

Preferred:

```text
Hermes
   │
   │ LAN
   ▼
LiteLLM / Ember-AI
   │
   │ LAN
   ▼
oMLX
jons-mac-mini
```

Rather than:

```text
Hermes
   │
Cloudflare
   │
llm.vaxel.xyz
   │
Cloudflare
   │
oMLX
```

External and internal endpoint configuration may therefore differ while representing the same logical service.

Authentication should remain in place for sensitive internal services even where LAN transport is used.

---

# 10. Target System Architecture

The resulting Vaxel architecture is:

```text
                         VAXEL.XYZ


                     HUMAN INTERFACE

                     ai.vaxel.xyz
                           │
                           ▼
                    Vaxel/OpenWork
                           │
                           ▼
                     Hermes / Ember
                           │
              ┌────────────┼────────────┐
              │            │            │
             MCP          n8n      native tools
              │            │            │
              └────────────┼────────────┘
                           │
        HA / Proxmox / TrueNAS / Cloudflare /
             GitHub / Web / other services


                    AI INFRASTRUCTURE

                    ember.vaxel.xyz
                           │
                     Ember-AI Admin
                           │
                           ▼
                    LiteLLM Gateway
                           │
                  llm.vaxel.xyz/v1
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
           oMLX          OpenAI       Anthropic/
             │                         others
             │
       jons-mac-mini
             │
       ┌─────┼──────────────┐
       │     │              │
      LLM  Parakeet v3    TTS model
             STT          via oMLX


                    DEVELOPMENT

                         Jon
                          │
                          ▼
                      OpenCode
                          │
                          ▼
                  Project / Repository
```

---

# 11. Responsibility Summary

The architectural boundaries are:

**OpenWork = Vaxel's human-facing interface**

**Hermes = Ember's brain, memory and agency**

**Ember-AI = shared inference, voice, routing and observability infrastructure**

**oMLX = local Apple Silicon inference runtime**

**LiteLLM = LLM provider gateway**

**Parakeet v3 via oMLX = Ember's STT**

**Selected TTS model via oMLX = Ember's speech output**

**OpenCode = locally launched software-development agent**

**n8n = deterministic workflow automation**

These boundaries should be treated as deliberate architectural constraints.

---

# Consequences for Current Ember-AI Work

Fable should reconcile the current implementation against this ADR.

In particular:

1. Reserve `ai.vaxel.xyz` for the future Vaxel/OpenWork frontend.
2. Move the canonical LLM API design to `llm.vaxel.xyz/v1`.
3. Use `ember.vaxel.xyz` for Ember-AI administration.
4. Treat oMLX as a multi-capability local inference runtime rather than only an LLM backend.
5. Integrate Parakeet v3 through oMLX.
6. Keep TTS backend selection open pending Kokoro/Qwen3-TTS benchmarking.
7. Do not add OpenCode to the Ember-AI deployment.
8. Do not reproduce Hermes agent capabilities inside Ember-AI.
9. Keep n8n outside the critical conversational path.
10. Prefer direct LAN/service communication for internal traffic.
11. Continue the previously accepted lean-rebuild approach rather than adapting incompatible ODS routing abstractions.

Where this ADR conflicts with assumptions in the original ODS-derived PRD, **this ADR takes precedence**.