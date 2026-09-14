# ADR 0004: LiteLLM talks directly to LAN oMLX with a bearer key

**Status:** Accepted
**Date:** 2026-09-14
**Project:** `vaxel-xyz/Ember-AI`

## Context

ODS routes local inference through a model switchboard and a `remote_provider`/SSH-tunnel
abstraction, designed for a world where the inference host might be remote, might change, or
might need traffic shaping between multiple candidate backends. Ember-AI has exactly one local
inference host (`jons-mac-mini`, oMLX, on the same LAN as the Docker VM) and one cloud
provider (OpenRouter). There is no fleet of interchangeable local backends to switch between,
and Prox01-to-mini traffic is LAN hostname/IP, not Tailscale, not an SSH tunnel (per
[ADR 0001](0001-vaxel-service-urls-ownership-network.md) §9).

## Decision

**LiteLLM calls oMLX's OpenAI-compatible API directly**, over the LAN, authenticated with a
bearer key (`OMLX_API_KEY`) that LiteLLM injects via `api_key: os.environ/OMLX_API_KEY` in
`config/litellm/ember.yaml.tmpl`. There is no model-router, no switchboard, no
`bin/remote_provider/` egress/SSH-tunnel layer, and no `LLM_BACKEND=external` indirection —
`api_base` is simply `${OMLX_BASE_URL}/v1`, a LAN URL. Alias → model mapping (`ember-auto`,
`ember-fast`, `ember-code`, `ember-vision`, `ember-embed`, `ember-stt`, `ember-tts`,
`ember-local`) is entirely `.env`-driven; changing which oMLX model backs `ember-auto` is a
one-line `.env` edit and a restart, not a switchboard reconfiguration.

## Alternatives

- **Keep the ODS model switchboard.** Rejected: the switchboard exists to route between
  multiple interchangeable backends and apply policy (observe/enforce modes) across them.
  Ember has one LAN backend and one cloud backend, selected per-alias, not per-request
  policy — the switchboard's complexity buys nothing here.
- **Keep `remote_provider` (SSH tunnel/egress).** Rejected: oMLX is reachable directly over
  the LAN; an SSH tunnel would add a process to manage, a failure mode to debug, and latency,
  for no security benefit over a bearer key on a private `172.20.142.0/24` network.
- **`LLM_BACKEND=external` indirection layer.** Rejected: this would reintroduce a level of
  abstraction between LiteLLM and oMLX that the direct `api_base`/`api_key` pattern already
  provides more simply and more transparently.

## Consequences

LiteLLM's health and failure behaviour is now a direct function of oMLX's reachability — when
the mini is off, `oMLX` reports `unreachable` and oMLX-backed aliases return a clear LiteLLM
5xx, with no intermediate layer to obscure or delay that signal (see
`docs/architecture.md#failure-behaviour`). Adding a second local inference host in future
would require either a second manifest + a second set of aliases, or reintroducing some form
of routing — that is an explicit non-goal for Phase 1 (see spec §13, "multi-Mac inference" as
out of scope), not an oversight in this design.
