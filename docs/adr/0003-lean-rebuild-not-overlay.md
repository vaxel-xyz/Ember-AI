# ADR 0003: Lean rebuild inside the fork, not overlay or fresh repo

**Status:** Accepted
**Date:** 2026-09-14
**Project:** `vaxel-xyz/Ember-AI`

## Context

Ember-AI starts from `Osmantic/ODS` (`v2.6.0` / `21f4b3a64`), a general-purpose self-hosted AI
platform with an installer, `ods-cli`, a host agent, a model switchboard/router, a remote-
provider egress tunnel, and around 27 bundled services (llama-server, Open WebUI, n8n, APE,
OpenClaw, SearXNG, Perplexica, brave-search, ComfyUI, TEI embeddings, Whisper, Kokoro
containers, privacy-shield, token-spy, ods-proxy, Tailscale, OpenCode, and more). Vaxel's
actual requirement is much narrower: a routing/inference/voice/observability layer consumed
by Hermes, OpenCode, n8n and OpenWork, sitting in front of a single LAN inference node
(`jons-mac-mini`, running oMLX) and one cloud provider (OpenRouter). ODS is a donor/reference
implementation, not an architecture Vaxel needs to preserve.

Three options were available: (a) overlay Ember configuration on top of the full ODS runtime,
keeping everything and adding Ember-specific bits; (b) start a brand-new repository with no
ODS history, hand-copying only what's useful; (c) rebuild leanly inside the existing fork,
keeping git history and the `upstream` remote, but aggressively deleting everything that does
not serve Ember.

## Decision

**Rebuild leanly inside the fork.** Keep the git history and the `upstream` remote (so
individual ODS fixes or schema changes can still be cherry-picked later), but delete the ODS
installer, `ods-cli`, host agent, model switchboard/router, remote-provider tunnel, all
`docker-compose.*.yml` variants, and the ~27 bundled service extensions that Ember does not
need. Retain only what is genuinely reusable: the service-manifest schema (extended with
`x_ember`), the dashboard React/Vite/Tailwind scaffold, secret-scanning config, and the
Apache-2.0 license/attribution. Prefer deletion and plain replacement over compatibility
shims — see `DOWNSTREAM.md` for the full removed/retained list.

## Alternatives

- **Overlay on the full ODS runtime.** Rejected: every ODS subsystem Ember doesn't use
  (installer, switchboard, 27 services) would still need to be understood, configured around,
  and kept from interfering, for zero benefit. It also keeps ODS's `dashboard-api` (20.8k
  lines) and host agent (12.8k lines) live, which directly contradicts the target of a thin,
  auditable control plane (ADR 0008).
- **Fresh repository, no ODS history.** Rejected: this would lose the ability to cherry-pick
  future ODS fixes to the schema or dashboard scaffold, and would require re-deriving the
  Apache-2.0 attribution chain from scratch rather than inheriting it cleanly via `LICENSE`/
  `NOTICE`.

## Consequences

Upstream divergence from ODS is total by design — nearly every ODS subsystem is gone. This is
recorded explicitly in `DOWNSTREAM.md` rather than treated as an oversight, along with the
cherry-pick procedure (`git fetch upstream`, `git log upstream/main -- <path>`,
`git cherry-pick -x <sha>`) for the small set of paths still worth tracking upstream (the
manifest schema and the dashboard scaffold). Anyone approaching this repo expecting an ODS
installation will be surprised — the README and `DOWNSTREAM.md` exist specifically to set
that expectation correctly on first contact.
