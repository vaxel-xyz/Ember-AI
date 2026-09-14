# ADR 0005: External service model — manifests with `type: external`, HTTP-only probing

**Status:** Accepted
**Date:** 2026-09-14
**Project:** `vaxel-xyz/Ember-AI`

## Context

ODS's service model assumes every service is Docker-managed: compose-started, inspectable via
the Docker socket, and controllable through the ODS host agent (start/stop/restart,
GPU detection, GGUF directory scanning). oMLX runs on `jons-mac-mini`, which has no Docker at
all — it is a launchd-managed DMG app, entirely outside Ember's deployment and lifecycle
control, on a separate physical host reachable only over the LAN. Forcing oMLX into the
Docker-managed service model would be a fiction: there is no container to inspect, no socket
to call, and no agent process Ember is allowed to run on the mini
([ADR 0001](0001-vaxel-service-urls-ownership-network.md) §4, §9 — "No Docker on the mini").

## Decision

Extend the service-manifest schema (`services/schema/service-manifest.v1.json`) with a new
`service.type: external` value, alongside the existing `docker` value, and a namespaced
`x_ember` block carrying Ember-specific fields the upstream ODS schema doesn't have:

```yaml
service:
  id: omlx
  type: external
  x_ember:
    node: jons-mac-mini
    role: inference
    managed: false
    capabilities: [llm, vision, embeddings, rerank, stt, tts]
    health_probe: omlx
```

`type: external` + `x_ember.managed: false` means: no container, no `docker inspect`, no
socket access, no start/stop/restart control from Ember. The only thing Ember does with an
external service is **probe it over HTTP** — `health_probe: omlx` selects the oMLX-aware
probe in `ember-api/ember_api/health.py`, which parses `/health`'s `engine_pool` fields into
one of the five health states. There is no agent, daemon or any Ember-controlled process on
the mini at all.

## Alternatives

- **Run a lightweight Ember agent on the mini** (mirroring the ODS host agent, scoped down).
  Rejected: this reintroduces exactly the host-agent surface area ADR 0008 removes on the
  Docker side, on a machine Ember explicitly does not manage, for a capability (richer health
  detail) that oMLX's own `/health` and `/v1/models/status` already provide over HTTP.
- **Fake it as `type: docker` with a null container.** Rejected: this would either break
  schema validation assumptions elsewhere or require special-casing docker-specific fields
  (`container_name`, `container_uid`) to be optional in ways that make the schema harder to
  reason about than adding one new enum value.

## Consequences

Every capability Ember can offer for oMLX-backed services is bounded by what oMLX exposes over
HTTP — if oMLX doesn't expose it, Ember cannot show it, and Ember will never gain the ability
to restart or reconfigure oMLX itself. This is accepted as correct: the mini is Jon's inference
node, not Ember's infrastructure, and Ember's job is to route to it and report on it, not to
own its lifecycle. `scripts/validate-manifests.py` enforces that `x_ember.node` is one of the
known hosts (`docker01`, `jons-mac-mini`) so a manifest can't silently claim to be managed
when it isn't.
