# ADR 0006: Rerank routing

**Status:** Proposed
**Date:** 2026-09-14
**Project:** `vaxel-xyz/Ember-AI`

## Context

The Phase 1 design (spec §4.1) reserves a logical alias, `ember-rerank`, for reranking, and
notes that LiteLLM's rerank route only partially supports the Cohere/Jina-shaped rerank API
that oMLX's `/v1/rerank` exposes — the plan explicitly leaves open whether `ember-rerank` can
route through LiteLLM directly, or whether `ember-api` needs to expose `/v1/rerank` as a thin
authenticated proxy to oMLX instead.

Separately, and more fundamentally: no reranker model is loaded in oMLX today. `bge-m3-mlx-8bit`
(`OMLX_EMBED_MODEL`) is an **embedding** model, not a reranker — attempting to use it for
reranking is a category error, and oMLX's own guidance for the rerank endpoint is explicit:
*"Use a SequenceClassification model."* No such model is present on `jons-mac-mini` as of
2026-09-14.

## Decision

`ember-rerank` is **not configured** in Phase 1. `config/litellm/ember.yaml.tmpl` has no
`ember-rerank` entry, `.env.example` carries `OMLX_RERANK_MODEL` only as a commented-out
placeholder with a note pointing at this ADR, and `services/omlx/manifest.yaml` lists
`rerank` in `x_ember.capabilities` as an oMLX-supported capability class, not as something
Ember currently routes to. Resolving whether `ember-rerank` routes through LiteLLM directly or
through an `ember-api` proxy — and choosing/loading a `SequenceClassification` reranker model
on the mini — is deferred to Task 12. This ADR's status stays **Proposed** until Task 12's
probe result is recorded here.

## Alternatives

- **Route `ember-rerank` through LiteLLM's partial rerank passthrough now, using `bge-m3`.**
  Rejected: this would silently misuse an embedding model as a reranker, likely producing
  scores that look plausible but are not meaningfully ranked — worse than clearly reporting
  the capability as unavailable.
- **Build an `ember-api` rerank proxy now, ahead of Task 12.** Rejected: without a
  `SequenceClassification` model loaded on the mini there is nothing correct to proxy to; the
  proxy-vs-LiteLLM-passthrough decision should be made once Task 12 has verified which path
  actually works against oMLX 0.6.4's rerank endpoint, not speculatively.

## Consequences

`GET /api/models` and the dashboard's Models page will show no `ember-rerank` row until this
ADR is updated. Any consumer needing reranking today must do so outside Ember (e.g. inside
Hermes's own RAG logic), consistent with Ember's boundary of not owning RAG behaviour (spec
§4.8). This ADR should be revisited — status changed to Accepted, decision section updated
with the chosen routing path and the model loaded — once Task 12 completes.
