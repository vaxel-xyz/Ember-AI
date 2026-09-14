# ADR 0008: `ember-api` replaces `dashboard-api` and the host agent

**Status:** Accepted
**Date:** 2026-09-14
**Project:** `vaxel-xyz/Ember-AI`

## Context

ODS's control-plane API surface is split across `dashboard-api` (20.8k lines) and
`ods-host-agent.py` (12.8k lines). Between them they implement Docker-socket access,
container start/stop/restart, GPU detection, a GGUF model-directory scanner, and magic-link
authentication — a large surface built for a general-purpose self-hosted platform managing an
arbitrary set of Docker services and local model files. Ember's actual control-plane needs are
narrow: report health for a small, fixed set of services (three Docker-managed, one external),
surface alias → model mappings, surface provider configuration presence, surface usage from
LiteLLM's own spend logs, and validate config — nothing here requires touching the Docker
socket, detecting GPUs, or scanning a GGUF directory.

## Decision

Replace both `dashboard-api` and the host agent with a single new thin FastAPI service,
`ember-api` (`ember-api/ember_api/`), targeting ≤ 2k lines. As built for Phase 1 it is
~470 lines across `main.py`, `health.py`, `manifests.py`, `omlx.py`, `litellm_client.py`,
`security.py`, `settings.py` and the four routers (`services`, `models`, `providers`,
`config`) — well inside the target. It has **no Docker socket access, no host agent process,
no GPU detection, no GGUF directory scanning, and no magic-link auth**. Authentication is a
single `EMBER_API_KEY` bearer, checked with `secrets.compare_digest` on every route
(`ember-api/ember_api/security.py`). Health, models, providers and config-validation logic is
built directly against the manifest files and two small typed clients (`OmlxClient`,
`LiteLLMClient`) that call oMLX's and LiteLLM's own HTTP APIs — there is no privileged
access to anything Docker- or host-level.

## Alternatives

- **Trim `dashboard-api` down in place.** Rejected: 20.8k lines of code built around a much
  larger feature surface (arbitrary service management, extensions, multiple auth modes)
  would need extensive deletion and re-verification to reach a state as auditable as a
  470-line service written for exactly Ember's five routes; a rewrite from the manifest and
  health-state-machine design (spec §4.2–§4.4) upward was faster and produced a smaller,
  easier-to-review result.
- **Keep the host agent for Docker-socket-based health checks.** Rejected: `ember-api`'s HTTP
  probes (`GET /api/health` on itself, `/health/readiness` on LiteLLM, `/health` on oMLX)
  give the same five-state signal without needing Docker-socket access at all — and Docker-
  socket access is a meaningfully larger privilege to grant a container than outbound HTTP.

## Consequences

`ember-api` cannot answer questions that require the Docker socket (e.g. container resource
usage independent of what a service's own health endpoint reports, or arbitrary container
start/stop). This is accepted: Phase 1's one gated exception,
`POST /api/models/{id}/load|unload` against oMLX's own admin API, is explicitly deferred to
Phase 3, planned to sit behind an `EMBER_ALLOW_MODEL_CONTROL=true` gate — that variable does
not exist in `.env.example` or the code yet — and is not built as part of this ADR. Any future
requirement for genuine container lifecycle control would need a new, separately-scoped
decision — it is not something `ember-api`'s current design accommodates by accident.
