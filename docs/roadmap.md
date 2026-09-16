# Roadmap

Statuses and owners per [ADR 0010](adr/0010-frontend-routing-voice.md). Everything here is
**not started**; each item is one paragraph of intent, not a commitment.

## Phase 5 — MCP reconnection (owner: Jon)

Ember's Phase 1 rebuild dropped ODS's bundled MCP plumbing. MCP/tool capability returns at the
frontend/agent layer: Open WebUI's MCP configuration and Hermes's tool config are the hosts —
**never** ember-api (ADR 0010 §6). Planned MCP/tool domains: Home Assistant (native MCP
endpoint preferred; the external HA MCP endpoint stays a private remote-access URL in the
consuming host's `.env`), Hermes, n8n, GitHub and infrastructure tooling. Sensitive actions
(door locks, alarms, garage doors) stay explicitly protected.

## Phase 6 — OpenAI Realtime voice (owner: Jon)

Realtime voice via the OpenAI Realtime API through the gateway, as sketched in ADR 0010 §8.
The gateway would expose a realtime-capable route alongside the existing `ember-stt`/
`ember-tts` pipeline; the mini's Parakeet/Kokoro path remains the private/local fallback.
Goal: progressively close the gap with ChatGPT Voice while keeping a local fallback.

## Phase 7 — Local voice pipeline beyond STT/TTS (owner: Jon)

Beyond the existing `ember-stt` (Parakeet v3) and `ember-tts` (Kokoro) aliases: a fuller local
voice loop (VAD, turn-taking, streaming) served from the mini, so voice keeps working with the
internet — and the cloud realtime route — unavailable. Constrained by mini RAM shared with
desktop use.

## `auto` alias — routing policy (owner: Jon)

A future `auto` alias that picks local vs cloud per request (cost, latency, privacy,
availability) as a routing policy in front of `local-smart`/`heavy` (ADR 0010 §5). Deferred:
needs a policy spec and evaluation harness before it becomes API surface. The `ember-*` and
human-facing aliases stay stable regardless.
