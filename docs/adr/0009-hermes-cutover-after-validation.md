# ADR 0009: Hermes cutover only after Phase 1 validation

**Status:** Accepted
**Date:** 2026-09-14
**Project:** `vaxel-xyz/Ember-AI`

## Context

Hermes is Ember's only required first-class consumer (spec §1.1,
[ADR 0001](0001-vaxel-service-urls-ownership-network.md) §6) and is already a working,
in-production agent on `jons-mac-mini`, talking to OpenRouter as its primary provider and to
oMLX directly (`local-omlx` → `http://127.0.0.1:8000/v1`) as its fallback. Ember-AI's control
plane (LiteLLM, ember-api, dashboard) is new and unproven on Docker01. Pointing Hermes at
Ember before Ember's own health, routing and failure behaviour have been validated would put
a working, relied-upon agent's fallback path behind an unproven system — any Ember bug would
become a Hermes outage, with no way to distinguish "Ember is broken" from "the fallback path
Hermes has always used is broken."

## Decision

**Hermes cutover is Phase 5**, a separate, explicitly approved step, only undertaken after
Phase 1's acceptance criteria are met: oMLX, Hermes and n8n untouched and functional; LiteLLM
running independently of the mini; `ember-auto` returning a real oMLX completion and
`ember-embed` returning real vectors through LiteLLM; the dashboard showing correct 5-state
health including an `unreachable` mini; `ember doctor` green on Docker01. Until that
validation is complete, Ember and Hermes run in **parallel** — Hermes keeps its existing direct
`local-omlx` path untouched, and Ember is validated independently by other consumers and by
`bin/ember doctor`'s own checks. Only once Phase 1 is validated does
[`docs/hermes-cutover.md`](../hermes-cutover.md) get executed: `~/.hermes/config.yaml`'s
`local-omlx.base_url` moves to `http://172.20.142.7:4000/v1` with a LiteLLM virtual key, model
`ember-local`, with a timestamped `config.yaml.bak-*` taken first and
`launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway` used to apply and, if needed, to
roll back.

## Alternatives

- **Cut Hermes over as part of Phase 1, to validate Ember against real traffic sooner.**
  Rejected: this makes Hermes's reliability contingent on a system that hasn't yet
  demonstrated its own failure modes are handled correctly (the five health states, the
  mini-off drill) — exactly the risk this ADR exists to avoid.
- **Never cut Hermes over; keep Ember and Hermes permanently independent.** Rejected: this
  leaves Hermes invisible to Ember's Clients/Usage telemetry indefinitely, and duplicates the
  oMLX-authentication surface (Hermes holds its own path to oMLX forever) when Ember's virtual-
  key model exists precisely to give every consumer, including Hermes, one accountable,
  budgetable identity.

## Consequences

Phase 1 through Phase 4 must be validated with consumers other than Hermes (manual `curl`
against `ember-auto`/`ember-embed`, `bin/ember doctor`, any other early adopter) — Hermes's
own usage cannot be used as Ember's proof of correctness before cutover, because Hermes isn't
using Ember yet. After cutover, a documented, timestamped-backup rollback exists
specifically so that if Ember misbehaves in a way Phase 1–4 testing missed, Hermes can be
restored to its pre-cutover direct-oMLX path in one command, without needing Ember itself to
be fixed first.
