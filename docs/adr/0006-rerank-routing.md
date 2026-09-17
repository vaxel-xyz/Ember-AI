# ADR 0006: Rerank routing

**Status:** Accepted
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

Task 12 (2026-09-14) resolved the two open questions:

1. **Model**: `bge-reranker-v2-m3` (a genuine `SequenceClassification` reranker, not
   `bge-m3-mlx-8bit`) is downloaded and loaded on `jons-mac-mini` as `OMLX_RERANK_MODEL`.
   oMLX's `/v1/rerank` serves it directly and correctly: `POST /v1/rerank` with
   `{"model":"bge-reranker-v2-m3","query":"when do bins go out","documents":["Bins go out
   tonight.","Coffee is ready."],"top_n":1}` returns the correct top result with
   `relevance_score: 0.408` (2.4 s cold, 0.04 s warm, 2.38 GB resident).
2. **Routing**: `ember-rerank` **does route through LiteLLM**, contrary to this ADR's original
   concern that LiteLLM's rerank passthrough was only partially compatible. Adding

   ```yaml
   - model_name: ember-rerank
     litellm_params: {model: "jina_ai/${OMLX_RERANK_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
   ```

   to `config/litellm/ember.yaml.tmpl` and restarting the stack was sufficient. `POST
   /rerank` on LiteLLM with `{"model":"ember-rerank", ...}` returned HTTP 200 on the first
   attempt, with a `relevance_score` identical to the direct oMLX call. The `jina_ai/`
   provider prefix maps LiteLLM's rerank request shape onto oMLX's Cohere/Jina-compatible
   `/v1/rerank` endpoint correctly; no `cohere/` prefix fallback was needed, and no
   `ember-api` proxy was built.

`OMLX_RERANK_MODEL=bge-reranker-v2-m3` is set in `.env.example`, `.env.schema.json`, and the
Docker01 `.env`. The `("ember-rerank", "omlx", "OMLX_RERANK_MODEL")` alias was added to
`ALIASES` in `ember-api/ember_api/routers/models.py` immediately after `ember-embed`, so
`GET /api/models` and the dashboard's Models page now show `ember-rerank`.

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

`GET /api/models` and the dashboard's Models page now show an `ember-rerank` row, resolved
against `OMLX_RERANK_MODEL`. Consumers should call `POST /rerank` on LiteLLM with
`{"model": "ember-rerank", ...}` using a virtual key (see `docs/litellm.md`), not the direct
oMLX endpoint — the LiteLLM route is authenticated, load-balanced consistently with every
other Ember model, and appears in spend logs/health checks. Ember still does not own RAG
behaviour (spec §4.8); this ADR only covers the transport, not who calls it or when.
